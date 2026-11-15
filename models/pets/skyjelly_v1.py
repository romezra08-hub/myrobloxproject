"""SkyJelly pet: a soft cloud-jellyfish, remade from the game's white cloud covered in grey bumps with
dangling tendrils. Built from scratch by script.

    python models/pets/skyjelly.py --review out/skyjelly.png      # render the review sheet
    python models/pets/skyjelly.py --export models/export/skyjelly.fbx

Must-haves, checked in every review:
  1. The same creature: a pale floating cloud-thing with tendrils hanging below, now a jellyfish bell
     with a soft cloud cap of puffs instead of a cluster of eye-like bumps.
  2. One cute face only: two big soft eyes with catchlights, a small smile and blush; nothing else on
     the bell that could read as more eyes.
  3. Pale blue to pink tint that looks translucent: a lighter scalloped rim, deeper blue under the
     bell, faint radial canals.
  4. A few flowing ribbon tentacles and frilly arms, with glowing beads on the scallops.
  5. Clearly not the CloudSpirit (white rain cloud) or the Ghost (white sheet): a bell shape, pastel
     colour, ribbons instead of rain or a hem.
  6. Matte-to-satin painted texture with roughness variation; about 3 studs tall; Body under 12k.

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


def glossy(bm, value):
    """Mark a shape as smoother than the fur (0 matte, 1 glossy) in the vertex layer 'gloss', which
    rough_map bakes into the roughness image."""
    lay = bm.verts.layers.float.get("gloss") or bm.verts.layers.float.new("gloss")
    for v in bm.verts:
        v[lay] = value
    return bm


def rough_map(body, texture, base, vary=0.1):
    """Replace the kit's plain grey roughness image with a baked one the same size as the colour image:
    `base` roughness, lower where a shape was marked glossy(), broken up by fine and broad noise so the
    surface never reads as one even plastic sheen. Written next to the colour image as <name>_rough.png."""
    import numpy as np
    baked = body.data.materials[0]
    nodes = baked.node_tree.nodes
    def feeding(socket):
        return next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == socket for l in n.outputs[0].links))
    colour_node, rough_node = feeding("Base Color"), feeding("Roughness")
    print("rough_map: colour image", colour_node.image.name, tuple(colour_node.image.size))
    size = colour_node.image.size[0]                        # the kit's own bake size (512 under PETS_FAST)
    m = bpy.data.materials.new("RoughBake")
    m.use_nodes = True
    t = m.node_tree
    new, link = t.nodes.new, t.links.new
    for n in list(t.nodes):
        t.nodes.remove(n)
    out = new("ShaderNodeOutputMaterial")
    em = new("ShaderNodeEmission")
    link(em.outputs[0], out.inputs[0])
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "gloss"
    co = new("ShaderNodeTexCoord")
    fine = new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 38.0, 3.0
    broad = new("ShaderNodeTexNoise")
    broad.inputs["Scale"].default_value, broad.inputs["Detail"].default_value = 3.5, 2.0
    link(co.outputs["Object"], fine.inputs["Vector"])
    link(co.outputs["Object"], broad.inputs["Vector"])

    def op(kind, x, y):
        n = new("ShaderNodeMath")
        n.operation = kind
        for i, v in enumerate((x, y)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]
    g = op('MULTIPLY', a.outputs["Fac"], -0.65 * base)
    r = op('ADD', g, base)
    r = op('ADD', r, op('MULTIPLY', op('SUBTRACT', fine.outputs["Fac"], 0.5), 2 * vary))
    r = op('ADD', r, op('MULTIPLY', op('SUBTRACT', broad.outputs["Fac"], 0.5), vary))
    r = op('MAXIMUM', op('MINIMUM', r, 1.0), 0.05)
    link(r, em.inputs["Color"])
    img = bpy.data.images.new(os.path.splitext(os.path.basename(texture))[0].replace("_colour", "") + "_rough", size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    tn = new("ShaderNodeTexImage")
    tn.image = img
    t.nodes.active = tn
    body.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    sc = bpy.context.scene
    old = sc.cycles.samples
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    sc.cycles.samples = old
    body.data.materials[0] = baked
    bpy.data.materials.remove(m)
    stem = os.path.splitext(texture)[0]
    img.filepath_raw = (stem[:-len("_colour")] if stem.endswith("_colour") else stem) + "_rough.png"
    img.file_format = 'PNG'
    img.save()
    grey = rough_node.image
    rough_node.image = img
    if grey and grey.users == 0:
        name = grey.name
        bpy.data.images.remove(grey)
        img.name = name
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return float(px[0::4].min()), float(px[0::4].max())
# ---- the sky jelly ---------------------------------------------------------------------------------

NAME = "SkyJelly"
COL = {"top": hexc("#CFE4FF"), "mid": hexc("#DCD6FF"), "rim": hexc("#FFCFE4"), "edge": hexc("#FFF1F7"),
       "under": hexc("#A9C2F2"), "under_dk": hexc("#8AA6E0"), "blush": hexc("#FF9EC0"), "mouth": hexc("#5A3260"),
       "white": hexc("#FFFFFF"), "rib_a": hexc("#F6B8D8"), "rib_b": hexc("#BFD2FF"), "rib_edge": hexc("#FFF0F8"),
       "ten_a": hexc("#C9DBFF"), "ten_b": hexc("#F2B6D6")}
SCALE = 1.0
BAKE = {"shade": 0.32, "rough": 0.62, "vary": 0.12}
SCALLOPS = 8
RIM_Z = 2.0
FACE = Vector((0, -0.95, 2.42))
FOCUS = FACE
FACE_DIST = 4.2


def ribbon(points, width, thick, outward, twist=0.0, segs=10, rings=28, wave=0.0):
    """A thin flowing ribbon along a smooth path: width(t) across, `thick` deep, its broad side facing
    `outward` (turned `twist` turns along its length), its edges rippling by `wave`. g = t for painting."""
    pts = [Vector(p) for p in points]
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    loops = []
    for i, p in enumerate(path):
        t = i / rings
        tan = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        side = Vector(outward).cross(tan)
        side = (side - tan * side.dot(tan)).normalized()
        side = Matrix.Rotation(2 * math.pi * twist * t, 3, tan) @ side
        nrm = tan.cross(side).normalized()
        w = width(t)
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            ca, sa = math.cos(a), math.sin(a)
            ripple = wave * math.sin(t * 22 + ca * 2) * abs(ca) ** 2
            v = bm.verts.new(p + side * ca * w + nrm * (sa * thick * (1 - 0.6 * abs(ca)) + ripple))
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


def build():
    jelly_m = painted("Jelly", dict(strength=0.1, mottle=0.08, fine=18.0, length=2.0), rough=0.6)
    eye_m = kit.material("Eyes", "#1C2246", rough=0.05)
    glow = kit.material("GLOW_Jelly", "#9FE8FF", rough=0.4, emit=2.5)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- the bell: a soft dome with a scalloped rim curling under, a cloud cap of puffs on top -------
    prof = resample([(0.0, 2.95), (0.4, 2.9), (0.72, 2.74), (0.93, 2.5), (1.03, 2.25), (1.04, 2.07), (0.99, 1.97),
                     (0.9, 1.97), (0.8, 2.04), (0.6, 2.12), (0.3, 2.18), (0.0, 2.2)], 40)
    bell = lathe(prof, segs=64)
    for v in bell.verts:
        a = math.atan2(v.co.y, v.co.x)
        lobe = 0.5 + 0.5 * math.cos(SCALLOPS * a + math.pi / SCALLOPS * 0)
        k = smooth(v.co.z, 2.3, 2.02)
        v.co.z -= 0.09 * lobe * k
        r = math.hypot(v.co.x, v.co.y)
        if r > 1e-6:
            f = 1 + 0.035 * lobe * k
            v.co.x *= f
            v.co.y *= f
    clay = [bell]
    for k in range(6):                                                      # a ring of soft puffs: a cloud cap
        a = 2 * math.pi * (k + 0.5) / 6
        clay.append(ell((0.48 * math.cos(a), 0.48 * math.sin(a), 2.68), (0.36, 0.36, 0.26)))
    clay.append(ell((0, 0.05, 2.86), (0.42, 0.42, 0.22)))
    skin = fuse(join(clay), voxel=0.022, iterations=4)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit((0.27 * s, -3, 2.44)) for s in (-1, 1)]
    smile = [hit((x, -3, 2.27 + 2.2 * x * x))[0] for x in (-0.1, -0.05, 0.0, 0.05, 0.1)]
    blush = [hit((0.45 * s, -3, 2.3))[0] for s in (-1, 1)]

    def carve(co, n):
        d = n * 0.01 * noise.noise(Vector((co.x * 5, co.y * 5, co.z * 5)))
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.08, 0.15))
        if co.y < -0.6:
            d -= n * 0.016 * (1 - smooth(poly_dist(co, smile), 0.008, 0.024))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - FACE).length, 0.3, 0.55)), factor=1.0)

    def bell_colour(co, n, g=0.0):
        col = mix(COL["mid"], COL["top"], smooth(co.z, 2.35, 2.85))
        col = mix(col, COL["rim"], smooth(co.z, 2.35, 2.08))
        col = mix(col, COL["edge"], 0.7 * smooth(co.z, 2.08, 1.96) * smooth(n.z, 0.2, -0.3))
        # underside: deeper blue, as if seen through the jelly
        col = mix(col, COL["under"], smooth(-n.z, 0.3, 0.8) * smooth(co.z, 2.1, 2.2))
        col = mix(col, COL["under_dk"], 0.5 * smooth(-n.z, 0.6, 0.95) * smooth(math.hypot(co.x, co.y), 0.6, 0.2))
        # faint radial canals, like a real jelly's, from the crown to each scallop
        a = math.atan2(co.y, co.x)
        canal = 1 - smooth(abs(((a * SCALLOPS / (2 * math.pi)) % 1.0) - 0.5), 0.0, 0.06)
        col = mix(col, COL["edge"], 0.35 * canal * smooth(co.z, 2.75, 2.45) * smooth(co.z, 2.05, 2.2) * smooth(n.z, -0.2, 0.2))
        col = mix(col, COL["white"], 0.25 * smooth(n.z, 0.6, 1.0) * smooth(co.z, 2.7, 2.9))
        for b in blush:
            col = mix(col, COL["blush"], 0.55 * (1 - smooth(((co - b) * Vector((1, 1, 1.5))).length, 0.04, 0.13)))
        if co.y < -0.6:
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.007, 0.016))
        return col
    add("bell", glossy(skin, 0.35), jelly_m, bell_colour)

    # ---- one face: two big soft eyes ---------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.085, 0.11, 0.05), cuts=3), e - en * 0.012, en), eye_m)
        add("glints", ell(e + en * 0.04 + Vector((-0.03, 0, 0.045)), (0.03, 0.012, 0.032), cuts=2), jelly_m, COL["white"])
        add("glints", ell(e + en * 0.035 + Vector((0.03, 0, -0.04)), (0.014, 0.008, 0.014), cuts=1), jelly_m, COL["white"])

    # ---- frilly oral arms from the centre, and ribbon tentacles from between the scallops -------------
    for k in range(4):
        a = 2 * math.pi * (k + 0.25) / 4
        out = Vector((math.cos(a), math.sin(a), 0))
        root = Vector((0, 0, 2.15)) + out * 0.18
        pts = [root, root + out * 0.15 + Vector((0, 0, -0.45)), root + out * 0.05 + Vector((0, 0, -0.95)),
               root + out * 0.22 + Vector((0, 0, -1.35)), root + out * 0.1 + Vector((0, 0, -1.6))]
        arm = ribbon(pts, lambda t: (0.13 * (1 - t) ** 0.7 + 0.025) * (1 + 0.22 * math.sin(t * 30)), 0.022, out,
                     twist=0.35, segs=10, rings=26, wave=0.02)

        def arm_col(co, n, g):
            col = mix(COL["rib_a"], COL["rib_b"], smooth(g, 0.1, 0.9))
            return mix(col, COL["rib_edge"], 0.3 * smooth(abs(n.z), 0.5, 1.0))
        add("arms", glossy(arm, 0.4), jelly_m, arm_col)
    for k in range(SCALLOPS):
        a = 2 * math.pi * (k + 0.5) / SCALLOPS
        out = Vector((math.cos(a), math.sin(a), 0))
        root = out * 0.9 + Vector((0, 0, 2.02))
        ln = 1.55 + 0.3 * math.sin(k * 2.7)
        sway = Vector((-out.y, out.x, 0)) * 0.12
        pts = [root, root + out * 0.1 + sway + Vector((0, 0, -ln * 0.3)), root + out * 0.05 - sway + Vector((0, 0, -ln * 0.62)),
               root + out * 0.18 + sway * 0.6 + Vector((0, 0, -ln))]
        if k % 2 == 0:                                                       # broad ribbons
            ten = ribbon(pts, lambda t: 0.07 * (1 - t) ** 0.6 + 0.012, 0.016, out, twist=0.5, segs=8, rings=24, wave=0.012)
        else:                                                                # fine tendrils between them
            ten = loft(pts, lambda t: 0.03 * (1 - t) + 0.008, segs=6, rings=20)
        add("tentacles", glossy(ten, 0.4), jelly_m, lambda co, n, g: mix(COL["ten_a"], COL["ten_b"], smooth(g, 0.2, 1.0)))

    # ---- little glowing beads on the scallops ------------------------------------------------------
    for k in range(SCALLOPS):
        a = 2 * math.pi * k / SCALLOPS
        p = Vector((1.03 * math.cos(a), 1.03 * math.sin(a), 1.93))
        add("glow", ell(p, (0.04, 0.04, 0.04), cuts=2), glow)
    for k in range(4):                                                        # a few sparks drifting below
        a = 2 * math.pi * k / 4 + 0.6
        add("glow", ell((0.55 * math.cos(a), 0.55 * math.sin(a), 1.2 - 0.25 * k), (0.03, 0.03, 0.03), cuts=1), glow)

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
    rough_map(body, texture, BAKE["rough"], BAKE.get("vary", 0.1))
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
