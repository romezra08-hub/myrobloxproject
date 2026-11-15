"""SpikeCrab pet: a frost crab, remade from the game's pale ice-blue crab with a crown of white spikes,
big white claws and an angry face. Built from scratch by script.

    python models/pets/spikecrab.py --review out/spikecrab.png      # render the review sheet
    python models/pets/spikecrab.py --export models/export/spikecrab.fbx

Must-haves, checked in every review:
  1. The same creature: a pale ice-blue crab with a crown of white spikes on its shell and big white claws.
  2. A round domed shell in a deep icy blue with frost grain and sparkle, crowned by a few chunky,
     faceted ice-blue crystals (not white paper spikes).
  3. Short, thick, stubby legs tucked under the shell, so it sits low like a chubby crab, never on stilts.
  4. Big frosted claws in the same icy blue, held up, ready but not threatening.
  5. Calm, friendly eyes on short stalks (level lids, no angry frown) and a small smile seen from the front.
  6. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 8: eyelids fitted closer to the eyes.

Round 7: scaled to 3.9 studs wide; the frost sparkle made finer and sparser (it read as white spots); legs set a little further out.

Round 6 (sent back for: spidery legs, a flat pale plastic disc, white paper spikes): rebuilt low and chubby on six short, thick legs tucked under the shell with rounded toes; a round domed shell in a deep icy blue with frost grain, sparkle flecks and a grainy roughness map with glossy specks; the claws in the same blue with blunt fingertips; five chunky faceted ice-blue crystals instead of a ring of white spikes; the eyes closer together; a small open smile on the front.

Round 5: a deeper ice blue, icy mottling and a blue wrist band on the white claws, a wider calm mouth.

Round 4: thicker legs; the eyelids fitted to the eyes (they sat on top like caps).

Round 3: legs splayed out sideways with high knees; ice veins and a darker rim band; frosted tubercles on the shell.

Round 2: more saturated blue; the crab lowered on shorter legs; bigger, clearer pincers; a calm mouth line.

Round 1: first build.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402



# ---- helpers ------------------------------------------------------------------------------------

def smooth(x, a, b):
    """0 at a, 1 at b, smooth in between (a may be larger than b)."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def hexc(h):
    return kit.srgb(h)


def _object(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    old = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(me)
    return bm


def fuse(bm, voxel=0.025, factor=0.5, iterations=2):
    """Remesh a closed shape into an even skin of small faces (a voxel remesh), so it can be sculpted."""
    ob = _object(bm, "fuse")
    bm.free()
    r = ob.modifiers.new("r", 'REMESH')
    r.mode, r.voxel_size, r.adaptivity = 'VOXEL', voxel, 0.0
    if iterations:
        s = ob.modifiers.new("s", 'SMOOTH')
        s.factor, s.iterations = factor, iterations
    return _evaluated(ob)


def decimate(bm, target, keep=None, factor=2.0):
    """Bring a dense skin down to about `target` triangles. keep(co) -> 0..1 marks where to keep
    more of the detail (the face), so its small forms do not turn into polygons."""
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    ob = _object(bm, "dec")
    bm.free()
    if tris > target:
        d = ob.modifiers.new("d", 'DECIMATE')
        d.ratio = target / tris
        d.use_collapse_triangulate = True
        if keep:
            vg = ob.vertex_groups.new(name="keep")
            for v in ob.data.vertices:
                w = keep(v.co)
                if w > 0:
                    vg.add([v.index], w, 'REPLACE')
            d.vertex_group, d.invert_vertex_group, d.vertex_group_factor = "keep", True, factor
    out = _evaluated(ob)
    bmesh.ops.triangulate(out, faces=out.faces[:])
    return out


def sculpt(bm, fn):
    """Move every vertex by fn(co, normal) -> Vector."""
    bm.normal_update()
    moves = [fn(v.co.copy(), v.normal.copy()) for v in bm.verts]
    for v, d in zip(bm.verts, moves):
        if d is not None:
            v.co += d
    bm.normal_update()
    return bm


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length


def poly_dist(p, pts):
    return min(seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


def paint(bm, fn):
    """Give every vertex the colour fn(co, normal, g) -> linear rgb, in the attribute 'col'.
    g is the vertex float layer 'g' when the shape has one (0 root to 1 tip), else 0."""
    bm.normal_update()
    lay = bm.verts.layers.float_color.get("col") or bm.verts.layers.float_color.new("col")
    lg = bm.verts.layers.float.get("g")
    for v in bm.verts:
        v[lay] = (*fn(v.co, v.normal, v[lg] if lg else 0.0), 1.0)
    return bm


def flat_paint(bm, rgb):
    return paint(bm, lambda co, n, g: rgb)


def ell(c, r, rot=(0, 0, 0), cuts=4):
    """An ellipsoid with radii r."""
    bm = kit.ball(tuple(2 * x for x in r), cuts=cuts)
    bm.transform(M(c, rot=rot))
    return bm


def facing(bm, at, normal, up=(0, 0, 1)):
    """Turn a shape built round the origin so its local +Z points along `normal`, then move it to `at`."""
    n = Vector(normal).normalized()
    q = n.to_track_quat('Z', 'Y')
    bm.transform(M(at) @ q.to_matrix().to_4x4())
    return bm


def resample(profile, n):
    """Catmull-Rom through (r, z) points, n points out."""
    pts = [Vector(p) for p in profile]
    return [tuple(kit._spline(pts, i / (n - 1) * (len(pts) - 1))) for i in range(n)]


def lathe(profile, segs=48, closed=False):
    """A surface of revolution round the z axis through (r, z) points; r=0 at an end makes a pole.
    Each vertex keeps 'g', how far along the profile it is (0 to 1)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    rings = []
    n = len(profile)
    for i, (r, z) in enumerate(profile):
        if r <= 1e-6:
            v = bm.verts.new((0, 0, z))
            v[lg] = i / (n - 1)
            rings.append([v])
            continue
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), z))
            v[lg] = i / (n - 1)
            ring.append(v)
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for j in range(segs):
                bm.faces.new((a[0], b[(j + 1) % segs], b[j]))
        elif len(b) == 1:
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
        else:
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def loft(points, rfun, segs=12, rings=24, flat=1.0):
    """Circles along a smooth path through `points`; rfun(t) gives the radius at t (0 to 1).
    Each vertex keeps 'g' = t, for painting."""
    pts = [Vector(p) for p in points]
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    tangent = (path[1] - path[0]).normalized()
    normal = tangent.orthogonal().normalized()
    loops = []
    for i, p in enumerate(path):
        new = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        axis = tangent.cross(new)
        if axis.length > 1e-6:
            normal = Matrix.Rotation(tangent.angle(new), 3, axis.normalized()) @ normal
        tangent = new
        side = tangent.cross(normal).normalized()
        t = i / rings
        r = max(rfun(t), 1e-4)
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            v = bm.verts.new(p + (normal * math.cos(a) + side * math.sin(a) * flat) * r)
            v[lg] = t
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, t in ((loops[0], 0.0), (loops[-1], 1.0)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        c[lg] = t
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _ops(tree):
    new, link = tree.nodes.new, tree.links.new

    def attr(name, out="Color"):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs[out]
    return new, link, attr


def painted(name, streak, rough=0.9):
    """The vertex paint 'col' under kit.furry's fine streaks and mottling."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, **streak)
    new, link, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col"), hsv.inputs["Color"])
    return m


def join(bms):
    out = bmesh.new()
    for b in bms:
        tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(tmp)
        b.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return out




# ---- the frost crab --------------------------------------------------------------------------------

NAME = "SpikeCrab"
COL = {"shell": hexc("#3F7FBF"), "shell_lt": hexc("#79B3E2"), "shell_dk": hexc("#285A90"), "frost": hexc("#E6F4FF"),
       "under": hexc("#6FA2CF"), "claw": hexc("#5E9ED4"), "claw_lt": hexc("#A9D3F0"), "tip": hexc("#24507E"),
       "ice_dk": hexc("#5FA8DE"), "ice": hexc("#A6DCF6"), "ice_lt": hexc("#E8F8FF"),
       "mouth": hexc("#1C2A44"), "tongue": hexc("#E07E92"), "white": hexc("#FFFFFF")}
SCALE = 1.45
BAKE = {"shade": 0.45, "rough": 0.82}
BODY = Vector((0, 0, 0.62))
EYES = [Vector((0.22 * s, -0.66, 1.2)) for s in (-1, 1)]
MOUTH_Z = 0.5
FACE = Vector((0, -0.8, 0.85)) * SCALE
FOCUS = FACE
FACE_DIST = 4.6


def shard(h, r, sides=6, seed=0.0):
    """A chunky faceted ice crystal: a prism with a pointed top, every face its own flat facet."""
    prof = [(0.0, -0.08), (r * 0.9, -0.08), (r, 0.12 * h), (r * 0.94, 0.62 * h), (r * 0.25, 0.93 * h), (0.0, h)]
    bm = lathe(prof, segs=sides)
    for v in bm.verts:
        v.co.x += 0.12 * r * noise.noise(Vector((v.co.z * 3 + seed, seed, 0)))
        v.co.y += 0.12 * r * noise.noise(Vector((seed, v.co.z * 3 + seed, 1)))
    bmesh.ops.split_edges(bm, edges=bm.edges[:])
    return bm


def frosty(name, rough=0.85):
    """Vertex paint with fine frost grain (kit.scaly cells) and sparse white sparkle flecks."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=0.025, joins=0.12, vary=0.14, rough=rough)
    tree = m.node_tree
    new, link, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    link(attr("col"), hsv.inputs["Color"])
    coord = new("ShaderNodeTexCoord")
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 30.0, 2.0
    link(coord.outputs["Object"], nz.inputs["Vector"])
    rng = new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.71, 0.78
    link(nz.outputs[0], rng.inputs["Value"])
    mixn = new("ShaderNodeMix")
    mixn.data_type = 'RGBA'
    link(rng.outputs["Result"], mixn.inputs[0])
    link(hsv.outputs["Color"], mixn.inputs[6])
    mixn.inputs[7].default_value = (*COL["frost"], 1.0)
    link(mixn.outputs[2], kit.principled(m).inputs["Base Color"])
    return m


def after_bake(body):
    """Swap the flat roughness image for a frost grain: mostly matte with sparse glossy sparkles."""
    import numpy as np
    for slot in body.material_slots:
        for node in slot.material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image and node.image.name.endswith("_rough"):
                name, path = node.image.name, node.image.filepath_raw
                bpy.data.images.remove(node.image)                   # free the name, so the new image keeps it
                size = 256
                rs = np.random.RandomState(7)
                grain = BAKE["rough"] + rs.normal(0.0, 0.04, (size, size))
                grain[rs.random_sample((size, size)) < 0.035] = 0.38
                px = np.ones((size, size, 4), dtype=np.float32)
                px[..., :3] = np.clip(grain, 0.0, 1.0)[..., None]
                img = bpy.data.images.new(name, size, size, alpha=False)
                img.pixels.foreach_set(px.ravel())
                img.filepath_raw, img.file_format = path, 'PNG'
                img.save()
                img.colorspace_settings.name = 'Non-Color'
                node.image = img
                return


def build():
    shell_m = frosty("Shell")
    claw_m = frosty("Claws")
    ice_m = kit.material("Ice", "#808080", rough=0.5)
    _, link, attr = _ops(ice_m.node_tree)
    link(attr("col"), kit.principled(ice_m).inputs["Base Color"])
    eye_m = kit.material("Eyes", "#121A28", rough=0.08)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- a round, domed carapace sitting low: one fused skin ----------------------------------------------
    clay = [ell(BODY, (1.0, 0.8, 0.46)),
            ell(BODY + Vector((0, 0.05, 0.16)), (0.82, 0.64, 0.42)),            # the dome
            ell(BODY + Vector((0, 0.02, -0.22)), (0.84, 0.64, 0.28)),           # belly
            ell(BODY + Vector((0, -0.46, -0.04)), (0.62, 0.38, 0.34))]          # the front face
    for s, e in zip((-1, 1), EYES):
        clay.append(loft([Vector((0.2 * s, -0.5, 0.9)), Vector((0.21 * s, -0.6, 1.05)), e + Vector((0, 0.02, -0.08))],
                         lambda t: lerp(0.1, 0.08, t), segs=10, rings=5))        # short eye stalks
        for k in range(4):                                                        # rounded rim bumps
            a = math.radians(-58 + 24 * k)
            at = BODY + Vector((s * 0.98 * math.cos(a), 0.78 * math.sin(a), 0.06))
            clay.append(ell(at, (0.09, 0.09, 0.07), cuts=2))
    for k in range(22):                                                           # frosted tubercles on the dome
        a = k * 2.39996
        rr = 0.25 + 0.5 * math.sqrt((k + 0.5) / 22)
        x, y = rr * math.cos(a), rr * math.sin(a) * 0.75
        if y < -0.42 and abs(x) < 0.45:
            continue
        loc = BODY + Vector((x, y, 0.16 + 0.42 * math.sqrt(max(0.0, 1 - (x / 0.82) ** 2 - ((y - 0.05) / 0.64) ** 2)) - 0.02))
        clay.append(ell(loc, (0.065, 0.065, 0.045), cuts=2))
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def front(x, z):
        loc, _, _, _ = tree.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        return loc
    smile = [front(x, MOUTH_Z + 2.2 * x * x) for x in (-0.19, -0.1, 0.0, 0.1, 0.19)]
    mouth_y = front(0.0, MOUTH_Z - 0.03).y

    def mouth_in(co):
        """0..1: inside a small open D-shaped smile on the front face."""
        if co.y > mouth_y + 0.1:
            return 0.0
        u = co.x / 0.12
        if abs(u) > 1.05:
            return 0.0
        top, bot = MOUTH_Z + 0.02 + 0.03 * u * u, MOUTH_Z - 0.07 + 0.08 * u * u
        return smooth(co.z, bot - 0.004, bot + 0.012) * smooth(co.z, top + 0.004, top - 0.012) * smooth(abs(u), 1.02, 0.8)

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 6)
        p = co - BODY
        if n.z > 0.35:                                       # the H-shaped grooves of a crab shell
            g1 = abs(abs(p.x) - 0.3 - 0.08 * p.y) if -0.45 < p.y < 0.45 else 99
            g2 = abs(p.y - 0.05) if abs(p.x) < 0.3 else 99
            d -= n * 0.022 * (1 - smooth(min(g1, g2), 0.015, 0.05))
        if co.y < -0.6:
            d += Vector((0, 0.06, 0)) * mouth_in(co)
            d -= n * 0.02 * (1 - smooth(poly_dist(co, smile), 0.008, 0.026))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 3700, keep=lambda co: 0.65 * (1 - smooth((Vector(co) - Vector((0, -0.8, 0.6))).length, 0.25, 0.5)), factor=1.0)

    def shell_colour(co, n, g=0.0):
        p = co - BODY
        col = mix(COL["shell"], COL["shell_lt"], 0.55 * smooth(n.z, 0.35, 1.0))
        col = mix(col, COL["under"], 0.6 * smooth(-n.z, 0.1, 0.6))
        fl = noise.noise(co * 8.0) + 0.5 * noise.noise(co * 21.0)
        col = mix(col, COL["frost"], 0.4 * smooth(fl, 0.5, 0.8) * smooth(n.z, 0.2, 0.7))       # frost patches
        vein = abs(noise.noise(co * 3.0 + Vector((5, 1, 2))))
        col = mix(col, COL["shell_lt"], 0.5 * (1 - smooth(vein, 0.015, 0.05)) * smooth(n.z, 0.0, 0.5))
        rim = (p.x / 1.0) ** 2 + (p.y / 0.8) ** 2
        col = mix(col, COL["shell_dk"], 0.35 * smooth(rim, 0.6, 0.85) * smooth(p.z, -0.05, 0.15) * (1 - smooth(rim, 0.92, 1.0)))
        col = mix(col, COL["frost"], 0.45 * smooth(rim, 0.82, 0.97) * smooth(abs(p.z), 0.2, 0.04))
        if co.y < -0.6:
            col = mix(col, COL["mouth"], max(smooth(mouth_in(co), 0.1, 0.5), 1 - smooth(poly_dist(co, smile), 0.008, 0.02)))
        return col
    add("shell", skin, shell_m, shell_colour)
    tg = ell(Vector((0, mouth_y + 0.035, MOUTH_Z - 0.045)), (0.065, 0.04, 0.025), cuts=2)
    add("tongue", tg, shell_m, COL["tongue"])

    # ---- friendly eyes with level lids ------------------------------------------------------------------
    for e, s in zip(EYES, (-1, 1)):
        fwd = Vector((0.1 * s, -1, 0.05)).normalized()
        add("eyes", ell(e, (0.13, 0.12, 0.14), cuts=3), eye_m)
        lid = ell((0, 0, 0), (0.136, 0.127, 0.146), cuts=3)
        for v in lid.verts:
            v.co.z = max(v.co.z, 0.06)
        lid.transform(M(e, rot=(-6, 0, 0)))
        add("lids", lid, shell_m, lambda co, n, g: mix(COL["shell"], COL["shell_lt"], smooth(n.z, 0.0, 0.9)))
        add("glints", ell(e + fwd * 0.115 + Vector((-0.035, 0, 0.0)), (0.028, 0.02, 0.028), cuts=1), shell_m, COL["white"])
        add("glints", ell(e + fwd * 0.12 + Vector((0.04, 0, -0.05)), (0.012, 0.01, 0.012), cuts=1), shell_m, COL["white"])

    # ---- six short, stubby legs tucked under the shell ---------------------------------------------------
    def leg_colour(co, n, g):
        col = mix(COL["shell"], COL["shell_lt"], 0.5 * smooth(n.z, 0.2, 1.0))
        col = mix(col, COL["frost"], 0.55 * (1 - smooth(abs(g - 0.45), 0.0, 0.08)))           # frosty joint
        return mix(col, COL["shell_dk"], 0.6 * smooth(g, 0.8, 1.0))
    for s in (-1, 1):
        for k, y in enumerate((-0.3, 0.06, 0.4)):
            root = Vector((0.68 * s, y, 0.36))
            knee = Vector((1.02 * s, y * 1.18 + 0.03 * k, 0.42))
            tip = Vector((1.12 * s, y * 1.26 + 0.05 * k, 0.1))
            leg = loft([root, knee, tip], lambda t: (0.17 - 0.05 * t) * (1 + 0.18 * math.exp(-((t - 0.45) / 0.07) ** 2)), segs=8, rings=10)
            add("legs", leg, shell_m, leg_colour)
            add("legs", ell(tip + Vector((0, 0, -0.01)), (0.12, 0.12, 0.1), cuts=2), shell_m,
                lambda co, n, g: mix(COL["shell_dk"], COL["shell"], smooth(n.z, -0.5, 0.6)))         # rounded toe

    # ---- two big frosted blue claws ---------------------------------------------------------------------
    def claw_colour(co, n, g):
        col = mix(COL["claw"], COL["claw_lt"], 0.6 * smooth(n.z, 0.1, 0.9))
        col = mix(col, COL["shell_dk"], 0.35 * smooth(-n.z, 0.1, 0.8))
        fl = noise.noise(co * 7.0) + 0.5 * noise.noise(co * 19.0)
        return mix(col, COL["frost"], 0.35 * smooth(fl, 0.45, 0.75))

    for s in (-1, 1):
        shoulder = Vector((0.66 * s, -0.42, 0.48))
        elbow = Vector((1.02 * s, -0.72, 0.55))
        wrist = Vector((0.98 * s, -1.0, 0.85))
        add("arms", loft([shoulder, elbow, wrist], lambda t: 0.16 * (1 + 0.2 * math.exp(-((t - 0.5) / 0.08) ** 2)), segs=10, rings=8),
            claw_m, claw_colour)
        R = M(wrist, rot=(-30, 0, 14 * s))                       # claw space: fingers point along -y, up is +z
        palm = ell((0, -0.24, 0.04), (0.32, 0.4, 0.3), cuts=4)
        palm.transform(R)
        add("claws", palm, claw_m, claw_colour)
        up = [Vector((0.03 * s, -0.5, 0.18)), Vector((0.02 * s, -0.72, 0.28)), Vector((-0.02 * s, -0.92, 0.24)), Vector((-0.03 * s, -1.02, 0.12))]
        lo = [Vector((0.0, -0.54, -0.1)), Vector((0.0, -0.78, -0.13)), Vector((-0.02 * s, -0.96, -0.06)), Vector((-0.03 * s, -1.02, 0.04))]
        for pts, r0 in ((up, 0.16), (lo, 0.15)):
            f = loft([R @ p for p in pts], lambda t: r0 * (1 - t) ** 0.55 + 0.035, segs=10, rings=9, flat=0.8)

            def finger_colour(co, n, g):
                return mix(claw_colour(co, n, g), COL["tip"], smooth(g, 0.75, 0.95))
            add("claws", f, claw_m, finger_colour)
            add("claws", ell(R @ pts[-1], (0.045, 0.045, 0.045), cuts=1), claw_m, COL["tip"])      # rounded fingertip

    # ---- a few chunky ice crystals ----------------------------------------------------------------------
    top = BODY + Vector((0, 0.1, 0.52))
    L = Vector((-0.5, -0.6, 0.65)).normalized()

    def ice_colour(co, n, g):
        k = 0.5 + 0.5 * n.dot(L) + 0.25 * noise.noise(n * 6.0 + co * 2.0)
        col = mix(COL["ice_dk"], COL["ice"], smooth(k, 0.2, 0.7))
        col = mix(col, COL["ice_lt"], smooth(k, 0.75, 1.05))
        col = mix(col, COL["ice_lt"], 0.4 * smooth(g, 0.75, 1.0))                     # pale tips
        return mix(col, COL["ice_dk"], 0.4 * smooth(g, 0.25, 0.05))                   # deeper where it grows out
    for k, (dx, dy, h, r, lean) in enumerate(((0.0, 0.02, 0.88, 0.22, (0.0, 0.05)), (0.36, 0.1, 0.56, 0.16, (0.55, 0.15)),
                                              (-0.34, 0.14, 0.62, 0.17, (-0.55, 0.2)), (0.12, 0.42, 0.5, 0.15, (0.2, 0.6)),
                                              (-0.16, -0.26, 0.44, 0.14, (-0.25, -0.45)))):
        d = Vector((lean[0], lean[1], 1.0)).normalized()
        base = top + Vector((dx, dy, -0.08 - 0.25 * (dx * dx + dy * dy)))
        add("crystals", facing(shard(h, r, sides=6, seed=10 + k), base, d), ice_m, ice_colour)

    lowest = min(v.co.z for bm, _ in c.parts.values() for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    parts = [ob for ob in c.objects if ob not in glow and ob not in eyes]
    if "before_bake" in globals():
        before_bake(parts)
    body = kit.bake_texture(parts, texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
    if "after_bake" in globals():
        after_bake(body)
    out = [body]
    for group, label in ((glow, "GLOW"), (eyes, "Eyes")):
        if not group:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for ob in group:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = pre + label
        out.append(g)
    c.objects = out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,front,side,back 3/4")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default=NAME + " review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", NAME.lower() + "_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    c = build()
    print("triangles by part:", dict(sorted(c.tally.items(), key=lambda kv: -kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(c, os.path.abspath(a.texture))
    tris = c.triangles()
    lo, hi = c.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(c.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(c, samples=a.samples, focus=FOCUS)
        head = Vector(FACE)
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * FACE_DIST, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * FACE_DIST * 0.94, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
