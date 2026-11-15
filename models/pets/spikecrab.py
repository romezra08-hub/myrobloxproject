"""SpikeCrab pet: a frost crab, remade from the game's pale ice-blue crab with a crown of white spikes,
big white claws and an angry face. Built from scratch by script.

    python models/pets/spikecrab.py --review out/spikecrab.png      # render the review sheet
    python models/pets/spikecrab.py --export models/export/spikecrab.fbx

Must-haves, checked in every review:
  1. The same creature: a pale ice-blue crab with a crown of white spikes on its shell and big white claws.
  2. An icy blue shell with frost and a crown of white crystal spikes.
  3. Big frosted claws held up, ready but not threatening.
  4. Calm, determined eyes on short stalks (level lids, no angry frown) and a small calm mouth.
  5. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 5: a deeper ice blue, icy mottling and a blue wrist band on the white claws, a wider calm mouth.

Round 4: thicker legs; the eyelids fitted to the eyes (they sat on top like caps).

Round 3: legs splayed out sideways with high knees; ice veins and a darker rim band; frosted tubercles on the shell.

Round 2: more saturated blue; the crab lowered on shorter legs (the long thin ones read spidery); bigger, clearer pincers; a calm mouth line.

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
COL = {"shell": hexc("#5C9FD2"), "shell_lt": hexc("#9CCDEE"), "shell_dk": hexc("#3A72A2"), "frost": hexc("#EEF8FF"),
       "under": hexc("#9CCBE8"), "claw": hexc("#E4F2FB"), "claw_dk": hexc("#7EB0D6"), "tip": hexc("#2F5C8C"),
       "crystal": hexc("#F7FCFF"), "crystal_bl": hexc("#BFE6F8"), "mouth": hexc("#2C3E5A"), "pupil": hexc("#0E1420"),
       "white": hexc("#FFFFFF")}
SCALE = 1.15
BAKE = {"shade": 0.45, "rough": 0.8}
BODY = Vector((0, 0, 1.05))
EYES = [Vector((0.3 * s, -0.8, 1.74)) for s in (-1, 1)]
FACE = Vector((0, -0.8, 1.5)) * SCALE
FOCUS = FACE
FACE_DIST = 4.4


def shard(h, r, sides=6, seed=0.0):
    """A faceted crystal: a prism with a pointed top, every face its own flat facet."""
    prof = [(0.0, -0.05), (r * 0.85, -0.05), (r, 0.1 * h), (r * 0.92, 0.68 * h), (0.0, h)]
    bm = lathe(prof, segs=sides)
    for v in bm.verts:
        v.co.x += 0.15 * r * noise.noise(Vector((v.co.z * 3 + seed, seed, 0)))
    bmesh.ops.split_edges(bm, edges=bm.edges[:])
    return bm


def build():
    shell_m = painted("Shell", dict(strength=0.08, mottle=0.14, fine=30.0, length=2.0), rough=0.8)
    claw_m = painted("Claws", dict(strength=0.06, mottle=0.12, fine=34.0, length=1.6), rough=0.8)
    eye_m = kit.material("Eyes", "#121A28", rough=0.08)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- the carapace: one fused skin ------------------------------------------------------------------
    clay = [ell(BODY, (1.05, 0.8, 0.46)), ell(BODY + Vector((0, 0.05, -0.22)), (0.85, 0.62, 0.3)),
            ell(BODY + Vector((0, -0.45, 0.02)), (0.7, 0.42, 0.36))]                       # the front brow
    for s in (-1, 1):
        clay.append(loft([Vector((0.24 * s, -0.62, 1.3)), Vector((0.28 * s, -0.74, 1.53)), EYES[0 if s < 0 else 1] + Vector((0, 0.02, -0.08))],
                         lambda t: lerp(0.09, 0.07, t), segs=10, rings=6))                   # eye stalks
        for k in range(4):                                                                     # rim teeth
            a = math.radians(-60 + 22 * k)
            at = BODY + Vector((math.sin(-a) * 0.0 + 0.98 * s * math.cos(a), -0.74 * abs(math.sin(a)) - 0.05, 0.08))
            at = BODY + Vector((s * 1.02 * math.cos(a), 0.78 * math.sin(a), 0.06))
            d = Vector((s * math.cos(a), math.sin(a), 0.15)).normalized()
            clay.append(loft([at - d * 0.08, at + d * 0.1], lambda t: 0.07 * (1 - t) + 0.008, segs=8, rings=3))
    for k in range(26):                                                       # little frosted tubercles on the shell
        a = k * 2.39996
        rr = 0.3 + 0.55 * math.sqrt((k + 0.5) / 26)
        x, y = rr * math.cos(a) * 1.0, rr * math.sin(a) * 0.72
        z = BODY.z + 0.46 * math.sqrt(max(0.0, 1 - (x / 1.05) ** 2 - (y / 0.8) ** 2)) - 0.02
        if y < -0.45 and abs(x) < 0.5:
            continue
        clay.append(ell((x, y, z), (0.07, 0.07, 0.05), cuts=2))
    skin = fuse(join(clay), voxel=0.024, iterations=3)

    def carve(co, n):
        d = n * 0.008 * noise.noise(co * 5)
        p = co - BODY
        # flatten the top a little and press the H-shaped grooves of a crab shell
        if n.z > 0.3:
            g1 = min(abs(abs(p.x) - 0.32 - 0.08 * p.y), 99) if -0.5 < p.y < 0.5 else 99
            g2 = abs(p.y - 0.02) if abs(p.x) < 0.32 else 99
            d -= n * 0.025 * (1 - smooth(min(g1, g2), 0.015, 0.05))
        if co.y < -0.6:
            d -= n * 0.022 * (1 - smooth(poly_dist(co, mouth), 0.007, 0.024))
        return d
    tree = BVHTree.FromBMesh(skin)
    mouth = []
    for x in (-0.17, -0.08, 0.0, 0.08, 0.17):
        z = BODY.z - 0.06 + 0.7 * x * x
        loc, _, _, _ = tree.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        mouth.append(loc)
    sculpt(skin, carve)
    skin = decimate(skin, 3400, keep=lambda co: 0.6 * (1 - smooth((Vector(co) - FACE).length, 0.3, 0.6)), factor=1.0)

    def shell_colour(co, n, g=0.0):
        p = co - BODY
        col = mix(COL["shell"], COL["shell_lt"], 0.5 * smooth(n.z, 0.3, 1.0))
        col = mix(col, COL["under"], smooth(-n.z, 0.1, 0.6))
        col = mix(col, COL["shell_dk"], 0.35 * smooth(abs(n.z), 0.4, 0.0) * smooth(p.z, 0.15, -0.1))
        fl = noise.noise(co * 9.0) + 0.5 * noise.noise(co * 23.0)
        col = mix(col, COL["frost"], 0.75 * smooth(fl, 0.4, 0.65) * smooth(n.z, 0.1, 0.6))     # frost flecks
        vein = abs(noise.noise(co * 3.2 + Vector((5, 1, 2))))                                 # ice veins
        col = mix(col, COL["frost"], 0.6 * (1 - smooth(vein, 0.015, 0.05)) * smooth(n.z, 0.0, 0.5))
        rim = (p.x / 1.05) ** 2 + (p.y / 0.8) ** 2
        col = mix(col, COL["shell_dk"], 0.45 * smooth(rim, 0.55, 0.8) * smooth(p.z, 0.0, 0.25) * (1 - smooth(rim, 0.9, 1.0)))
        col = mix(col, COL["frost"], 0.55 * smooth(rim, 0.75, 0.95) * smooth(abs(p.z), 0.25, 0.05))
        if co.y < -0.6:
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, mouth), 0.006, 0.018))
        return col
    add("shell", skin, shell_m, shell_colour)

    # ---- eyes with level lids ---------------------------------------------------------------------------
    for e, s in zip(EYES, (-1, 1)):
        fwd = Vector((0.15 * s, -1, 0.05)).normalized()
        add("eyes", ell(e, (0.13, 0.12, 0.14), cuts=3), eye_m)
        lid = ell((0, 0, 0), (0.142, 0.133, 0.152), cuts=3)
        for v in lid.verts:
            v.co.z = max(v.co.z, 0.045)
        lid.transform(M(e, rot=(-6, 0, 0)))
        add("lids", lid, shell_m, lambda co, n, g: mix(COL["shell"], COL["shell_lt"], smooth(n.z, 0.0, 0.9)))
        hi = e + fwd * 0.115 + Vector((-0.035, 0, 0.0))
        add("glints", ell(hi, (0.026, 0.02, 0.026), cuts=1), shell_m, COL["white"])
        add("glints", ell(e + fwd * 0.12 + Vector((0.04, 0, -0.05)), (0.012, 0.01, 0.012), cuts=1), shell_m, COL["white"])

    # ---- six walking legs ---------------------------------------------------------------------------------
    def leg_colour(co, n, g):
        col = mix(COL["shell"], COL["shell_lt"], 0.5 * smooth(n.z, 0.2, 1.0))
        col = mix(col, COL["frost"], 0.7 * (1 - smooth(abs(g - 0.42), 0.0, 0.06)))            # frosty knee
        return mix(col, COL["tip"], smooth(g, 0.82, 0.95))
    for s in (-1, 1):
        for k, y in enumerate((-0.32, 0.08, 0.46)):
            root = Vector((0.82 * s, y, 0.92))
            knee = Vector((1.32 * s, y * 1.3 + 0.05 * k, 1.16))
            ankle = Vector((1.68 * s, y * 1.5 + 0.08 * k, 0.5))
            tip = Vector((1.76 * s, y * 1.56 + 0.1 * k, 0.0))
            leg = loft([root, knee, ankle, tip], lambda t: (0.19 - 0.12 * t) * (1 + 0.25 * math.exp(-((t - 0.42) / 0.05) ** 2)) * (1 - smooth(t, 0.85, 1.0) * 0.8),
                       segs=8, rings=14)
            add("legs", leg, shell_m, leg_colour)

    # ---- two big frosted claws ---------------------------------------------------------------------------
    def claw_colour(co, n, g):
        col = mix(COL["claw"], COL["claw_dk"], 0.7 * smooth(-n.z, -0.1, 0.8))
        fl = noise.noise(co * 7.0) + 0.5 * noise.noise(co * 19.0)
        col = mix(col, COL["shell_lt"], 0.55 * smooth(fl, 0.15, 0.45))                     # icy blue mottling
        col = mix(col, COL["frost"], 0.6 * smooth(fl, -0.2, -0.45))
        return col

    for s in (-1, 1):
        shoulder = Vector((0.7 * s, -0.5, 0.95))
        elbow = Vector((1.25 * s, -0.9, 1.0))
        wrist = Vector((1.15 * s, -1.28, 1.45))
        add("arms", loft([shoulder, elbow, wrist], lambda t: lerp(0.15, 0.17, t) * (1 + 0.2 * math.exp(-((t - 0.5) / 0.08) ** 2)), segs=10, rings=10),
            claw_m, claw_colour)
        R = M(wrist, rot=(-38, 0, 16 * s))                       # claw space: fingers point along -y, up is +z
        palm = ell((0, -0.24, 0.04), (0.3, 0.38, 0.27), cuts=4)
        palm.transform(R)
        wr = wrist.copy()
        add("claws", palm, claw_m, lambda co, n, g, wr=wr: mix(claw_colour(co, n, g), COL["shell"], 0.8 * smooth((co - wr).length, 0.2, 0.12)))
        up = [Vector((0.03 * s, -0.48, 0.17)), Vector((0.02 * s, -0.74, 0.3)), Vector((-0.02 * s, -1.0, 0.27)), Vector((-0.04 * s, -1.14, 0.12))]
        lo = [Vector((0.0, -0.52, -0.1)), Vector((0.0, -0.82, -0.14)), Vector((-0.02 * s, -1.04, -0.08)), Vector((-0.03 * s, -1.13, 0.03))]
        for pts, r0 in ((up, 0.15), (lo, 0.14)):
            f = loft([R @ p for p in pts], lambda t: r0 * (1 - t) ** 0.7 + 0.012, segs=10, rings=10, flat=0.75)

            def finger_colour(co, n, g):
                return mix(claw_colour(co, n, g), COL["tip"], smooth(g, 0.72, 0.92))
            add("claws", f, claw_m, finger_colour)
            for k in range(3):                                   # little teeth on the inner edges
                t = 0.3 + 0.2 * k
                pt = R @ kit._spline(pts, t * 3)
                inward = R.to_3x3() @ Vector((0, 0, -1 if pts is up else 1))
                add("claws", ell(pt + inward * 0.06 * (1 - t), (0.035, 0.035, 0.035), cuts=1), claw_m, COL["claw"])

    # ---- the crown of crystal spikes -----------------------------------------------------------------------
    top = BODY + Vector((0, 0.08, 0.38))

    def crystal_colour(co, n, g):
        col = mix(COL["crystal_bl"], COL["crystal"], smooth(g, 0.1, 0.8))
        return mix(col, COL["shell_lt"], 0.35 * smooth(n.z, -0.2, -0.8))
    ring = 9
    for k in range(ring):
        a = 2 * math.pi * k / ring + 0.2
        h = 0.62 + 0.18 * math.sin(k * 2.7) + (0.12 if k in (2, 6) else 0)
        base = top + Vector((0.5 * math.cos(a), 0.36 * math.sin(a), -0.06))
        d = Vector((0.5 * math.cos(a), 0.4 * math.sin(a), 1.0)).normalized()
        add("crystals", facing(shard(h, 0.11 + 0.02 * math.sin(k), seed=k), base, d), shell_m, crystal_colour)
    for k, (dx, dy, h, r) in enumerate(((0.0, 0.0, 1.05, 0.16), (0.16, 0.12, 0.75, 0.12), (-0.17, 0.1, 0.8, 0.12), (0.02, -0.18, 0.62, 0.11))):
        d = Vector((dx * 1.2, dy * 1.2, 1.0)).normalized()
        add("crystals", facing(shard(h, r, seed=10 + k), top + Vector((dx, dy, 0.0)), d), shell_m, crystal_colour)
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow and ob not in eyes], texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
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
