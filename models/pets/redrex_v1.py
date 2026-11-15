"""RedRex pet: a powerful but likeable red horned dinosaur, remade from the game's chunky red dinosaur with
horns, a green spine stripe and dark spots. Built from scratch by script.

    python models/pets/redrex.py --review out/redrex.png      # render the review sheet
    python models/pets/redrex.py --export models/export/redrex.fbx

Must-haves, checked in every review:
  1. The same pet: a chunky red four-legged dinosaur with cream horns, a green row down its back and dark spots.
  2. A big creature, not childish: a sturdy body on pillar legs, a big deep head, a thick tail.
  3. Small cream horns (two over the brows, one on the nose, small cheek horns): an original mix of a
     horned dinosaur and a big-headed one, not any known character.
  4. A friendly, confident face: warm eyes with glints, a closed mouth whose corners lift.
  5. A crimson scaly hide with darker bands and spots, a paler throat and belly; a row of leaf-green plates.
  6. Matte painted textures with crease shading; up to about 4.5 studs tall; Body under 12k triangles.

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





# ---- helpers: painted roughness and patterned materials ------------------------------------------

def roughen(bm, fn):
    """Give every vertex a roughness fn(co, normal, g) -> 0..1 in the attribute 'rgh'. bake_rough() bakes it,
    with a fine grain on top, into the <name>_rough.png image beside the colour image."""
    bm.normal_update()
    lay = bm.verts.layers.float_color.get("rgh") or bm.verts.layers.float_color.new("rgh")
    lg = bm.verts.layers.float.get("g")
    for v in bm.verts:
        r = fn(v.co, v.normal, v[lg] if lg else 0.0)
        v[lay] = (r, r, r, 1.0)
    return bm


def _value_to_paint(m, value, rough):
    """Multiply the vertex paint 'col' by the brightness pattern `value` (a socket) into Base Color."""
    tree = m.node_tree
    new, link, attr = _ops(tree)
    hsv = new("ShaderNodeHueSaturation")
    link(attr("col"), hsv.inputs["Color"])
    link(value, hsv.inputs["Value"])
    b = kit.principled(m)
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def scaled(name, rough=0.8, **kw):
    """The vertex paint 'col' under kit.scaly's small scales with darker joins."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, rough=rough, **kw)
    new, link, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col"), hsv.inputs["Color"])
    return m


def _math(tree, op, a, b=None, c=None):
    n = tree.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, x in enumerate((a, b, c)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            tree.links.new(x, n.inputs[i])
    return n.outputs[0]


def grain_value(tree, grain):
    """A brightness socket round 1.0 from a list of patterns worked out in 3D (no seams):
    ("cells", scale, amount)  each small cell a slightly different shade (hammered metal, pebbled skin)
    ("edges", scale, amount)  bright thin rims between the cells (the ridges between hammer dents)
    ("noise", scale, amount)  soft mottling
    ("streak", scale, amount) fine streaks stretched along z (brushed metal, feather barbs)"""
    new, link = tree.nodes.new, tree.links.new
    coord = new("ShaderNodeTexCoord").outputs["Object"]
    total = None
    for kind, scale, amount in grain:
        vec = coord
        if kind == "streak":
            mp = new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (scale, scale, scale / 8.0)
            link(coord, mp.inputs["Vector"])
            vec, scale = mp.outputs["Vector"], 1.0
        if kind in ("cells", "edges"):
            t = new("ShaderNodeTexVoronoi")
            t.feature = 'F1' if kind == "cells" else 'DISTANCE_TO_EDGE'
            t.inputs["Scale"].default_value = scale
            link(vec, t.inputs["Vector"])
            if kind == "cells":
                s = _math(tree, 'MULTIPLY_ADD', t.outputs["Color"], 2 * amount, -amount)    # -amount..+amount
            else:
                rng = new("ShaderNodeMapRange")
                rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.0, 0.09
                rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = amount, 0.0
                link(t.outputs["Distance"], rng.inputs["Value"])
                s = rng.outputs["Result"]
        else:
            t = new("ShaderNodeTexNoise")
            t.inputs["Scale"].default_value, t.inputs["Detail"].default_value = scale, 2.0
            link(vec, t.inputs["Vector"])
            s = _math(tree, 'MULTIPLY_ADD', t.outputs[0], 2 * amount, -amount)
        total = s if total is None else _math(tree, 'ADD', total, s)
    return _math(tree, 'ADD', total, 1.0) if total is not None else _math(tree, 'ADD', 1.0, 0.0)


def grained(name, grain, rough=0.6):
    """The vertex paint 'col' under a grain_value() pattern."""
    m = kit.material(name, "#808080", rough=rough)
    return _value_to_paint(m, grain_value(m.node_tree, grain), rough)


def bake_rough(body, grain=()):
    """Replace the flat grey roughness image kit.bake_texture writes with the painted roughness 'rgh'
    plus a fine grain, baked into the same UVs. It is 512 px under PETS_FAST (as kit bakes) else 1024."""
    import numpy as np
    size = 512 if os.environ.get("PETS_FAST") else 1024
    mat = body.data.materials[0]
    node = next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and "_rough" in n.image.name)
    name, path = node.image.name, node.image.filepath_raw
    tmp = bpy.data.materials.new(NAME + "_RoughBake")
    try:
        tmp.use_nodes = True
    except Exception:
        pass
    tree = tmp.node_tree
    new, link, attr = _ops(tree)
    for n in list(tree.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            tree.nodes.remove(n)
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    em = new("ShaderNodeEmission")
    sep = new("ShaderNodeSeparateColor")
    link(attr("rgh"), sep.inputs[0])
    val = sep.outputs[0]
    if grain:
        g = grain_value(tree, grain)
        val = _math(tree, 'ADD', val, _math(tree, 'SUBTRACT', g, 1.0))
    link(val, em.inputs["Color"])
    link(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new(NAME + "_rough_bake", size, size, alpha=False, float_buffer=True)
    tex = new("ShaderNodeTexImage")
    tex.image = img
    tree.nodes.active = tex
    body.data.materials[0] = tmp
    sc = bpy.context.scene
    keep = sc.cycles.samples
    sc.cycles.samples = 1
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.bake(type='EMIT', margin=12)
    sc.cycles.samples = keep
    body.data.materials[0] = mat
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    px[..., :3] = np.clip(px[..., :1], 0.05, 1.0)
    px[..., 3] = 1.0
    bpy.data.images.remove(img)
    bpy.data.materials.remove(tmp)
    bpy.data.images.remove(node.image)
    final = bpy.data.images.new(name, size, size, alpha=False)
    final.pixels.foreach_set(px.ravel())
    final.filepath_raw, final.file_format = path, 'PNG'
    final.save()
    final.colorspace_settings.name = 'Non-Color'
    node.image = final
    return float(px[..., 0].mean())


def two_threads():
    """The machine is shared: render and bake on two threads."""
    r = bpy.context.scene.render
    r.threads_mode, r.threads = 'FIXED', 2

# ---- the red horned dinosaur ----------------------------------------------------------------------

NAME = "RedRex"
COL = {"red": hexc("#8E1A1A"), "red_lt": hexc("#B02E26"), "band": hexc("#4E0C10"), "spot": hexc("#3E0A0E"),
       "belly": hexc("#D49478"), "belly_dk": hexc("#A8644E"), "mouth": hexc("#360A0C"), "horn": hexc("#EEDFC2"),
       "horn_dk": hexc("#B39C7A"), "pupil": hexc("#140A06"), "white": hexc("#FFFFFF"),
       "plate": hexc("#6AA638"), "plate_lt": hexc("#9CCB5A"), "plate_dk": hexc("#36621E")}
SCALE = 1.55
BAKE = {"shade": 0.5, "rough": 0.82}
GRAIN = [("cells", 24.0, 0.06), ("noise", 50.0, 0.04)]
HEAD = Vector((0, -1.3, 1.38))
HEAD_M = M(HEAD, rot=(4, 0, 0))
FACE = Vector((-0.1, -1.7, 1.42)) * SCALE
FOCUS = FACE
FACE_DIST = 6.0
SPINE = [Vector((0, -0.95, 1.62)), Vector((0, -0.4, 1.72)), Vector((0, 0.3, 1.72)), Vector((0, 0.9, 1.6)),
         Vector((0, 1.5, 1.2)), Vector((0, 2.1, 0.8)), Vector((0, 2.6, 0.5))]


def build():
    scale_m = scaled("Scales", rough=0.8, size=0.07, joins=0.5, vary=0.16)
    bone_m = grained("Bone", [("streak", 60.0, 0.06), ("noise", 30.0, 0.04)], rough=0.55)
    plate_m = grained("Plates", [("streak", 40.0, 0.07), ("cells", 30.0, 0.05)], rough=0.7)
    eye_m = kit.material("Eyes", "#3A2412", rough=0.06)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()
    HINV = HEAD_M.inverted()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.8):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def snout(at, r, front):
        """An ellipsoid in head space that narrows towards its front end (-y) to `front` of its width."""
        bm = kit.ball(tuple(2 * x for x in r), cuts=4)
        kit.taper(bm, axis=1, lo=front, hi=1.05)
        bm.transform(HEAD_M @ M(at))
        return bm

    # ---- one fused skin: a sturdy body on pillar legs, a big head, a thick tail -------------------------
    clay = [ell((0, 0.15, 1.12), (0.66, 1.05, 0.6)),
            ell((0, -0.55, 1.15), (0.6, 0.55, 0.58)),                           # chest
            ell((0, 0.75, 1.1), (0.58, 0.55, 0.55)),                            # hips
            loft([(0, -0.75, 1.25), (0, -1.0, 1.33), (0, -1.15, 1.38)], lambda t: lerp(0.46, 0.4, t), segs=14, rings=6),
            loft([(0, 1.1, 1.05), (0, 1.8, 0.8), (0, 2.5, 0.5), (0.1, 3.0, 0.32), (0.25, 3.3, 0.22)],
                 lambda t: 0.44 * (1 - t) ** 1.0 + 0.04, segs=14, rings=18),
            ell(hd((0, 0.05, 0.05)), (0.42, 0.46, 0.38)),                       # skull
            snout(Vector((0, -0.45, -0.02)), (0.3, 0.42, 0.26), 0.7),           # snout
            snout(Vector((0, -0.32, -0.22)), (0.31, 0.44, 0.15), 0.72)]         # lower jaw
    for s in (-1, 1):
        clay += [ell(hd((0.2 * s, -0.12, 0.2)), (0.12, 0.18, 0.08)),            # brows
                 ell(hd((0.3 * s, 0.1, -0.1)), (0.18, 0.24, 0.22)),             # cheeks
                 ell((0.45 * s, -0.6, 0.98), (0.27, 0.32, 0.34)),               # shoulders
                 loft([(0.47 * s, -0.62, 0.85), (0.5 * s, -0.66, 0.45), (0.5 * s, -0.68, 0.14)], lambda t: lerp(0.23, 0.2, t), segs=12, rings=8),
                 ell((0.5 * s, -0.74, 0.08), (0.23, 0.26, 0.09)),               # front feet
                 ell((0.5 * s, 0.75, 0.95), (0.32, 0.46, 0.44)),                # thighs
                 loft([(0.52 * s, 0.8, 0.7), (0.54 * s, 0.9, 0.4), (0.53 * s, 0.82, 0.14)], lambda t: lerp(0.24, 0.2, t), segs=12, rings=8),
                 ell((0.53 * s, 0.72, 0.08), (0.24, 0.3, 0.09))]                # hind feet
    skin = fuse(join(clay), voxel=0.026, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = []
    for s in (-1, 1):
        d = R @ Vector((-0.55 * s, 1.0, -0.05))
        eyes.append(hit(hd((0.0, 0.0, 0.1)) - d.normalized() * 1.5, d))
    nostrils = [hit(hd((0.09 * s, -1.5, 0.08)), R @ Vector((0, 1, -0.2)))[0] for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        line = []
        for k in range(9):
            t = k / 8
            y = lerp(-0.85, 0.12, t)
            z = -0.14 + 0.08 * smooth(t, 0.55, 1.0)                           # the corners lift: a friendly smile
            p, _ = hit(hd((0.9 * s, y, z)), R @ Vector((-s, 0, 0)))
            if p is not None:
                line.append(p)
        mouth.append(line)
    front, _ = hit(hd((0, -1.5, -0.15)), R @ Vector((0, 1, 0)))
    if front is not None:
        mouth.append([mouth[0][0], front, mouth[1][0]])

    def carve(co, n):
        d = n * 0.01 * noise.noise(co * 7.0)
        for e, en in eyes:
            d -= en * 0.035 * (1 - smooth((co - e).length, 0.06, 0.12))
        if (co - HEAD).length < 1.2:
            d -= n * 0.022 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.008, 0.03))
            for nn in nostrils:
                if nn is not None:
                    d -= n * 0.025 * (1 - smooth((co - nn).length, 0.015, 0.04))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6600, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.35, 0))).length, 0.4, 0.75)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["red"], COL["red_lt"], 0.45 * smooth(n.z, 0.2, 0.9))
        band = 0.5 + 0.5 * math.sin(co.y * 7.0 + 0.5 * math.sin(co.x * 4))
        col = mix(col, COL["band"], 0.8 * smooth(band, 0.6, 0.82) * smooth(n.z, 0.15, 0.65) * smooth(co.y, -0.9, -0.6))
        spot = noise.noise(co * 5.5 + Vector((3, 1, 7)))
        col = mix(col, COL["spot"], 0.75 * smooth(spot, 0.42, 0.5) * smooth(abs(n.x), 0.3, 0.7) * smooth(co.z, 0.4, 0.7))
        belly = smooth(-n.z, -0.1, 0.5) * smooth(co.z, 0.95, 0.6)
        col = mix(col, mix(COL["belly"], COL["belly_dk"], 0.3 * smooth(co.z, 0.6, 0.2)), belly)
        throat = (1 - smooth(((co - hd((0, -0.3, -0.33))) * Vector((1, 0.7, 1.4))).length, 0.18, 0.32))
        col = mix(col, COL["belly"], 0.7 * throat * smooth(-n.z, -0.2, 0.4))
        if (co - HEAD).length < 1.2:
            col = mix(col, COL["mouth"], 1 - smooth(min(poly_dist(co, m) for m in mouth), 0.009, 0.018))
            for nn in nostrils:
                if nn is not None:
                    col = mix(col, COL["mouth"], 1 - smooth((co - nn).length, 0.02, 0.035))
        return col
    add("skin", skin, scale_m, colour, lambda co, n, g: 0.78 + 0.1 * smooth(-n.z, 0.0, 0.6))

    # ---- warm eyes ---------------------------------------------------------------------------------------
    up = (R @ Vector((0, 0, 1))).normalized()
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.085, 0.09, 0.05), cuts=3), e - en * 0.014, en), eye_m)
        add("glints", ell(e + en * 0.035 + up * 0.03 - en.cross(up).normalized() * 0.02 * s, (0.022, 0.022, 0.016), cuts=1), bone_m, COL["white"], 0.2)
        add("glints", ell(e + en * 0.035 - up * 0.028 + en.cross(up).normalized() * 0.022 * s, (0.01, 0.01, 0.008), cuts=1), bone_m, COL["white"], 0.2)

    # ---- small cream horns: two over the brows, one on the nose, one on each cheek -------------------
    def horn(at, d, length, r, curve=0.0):
        d = Vector(d).normalized()
        bm = loft([at, at + d * length * 0.5 + up * curve * 0.5, at + d * length + up * curve], lambda t: r * (1 - t) ** 0.8 + 0.006, segs=10, rings=7)
        add("horns", bm, bone_m, lambda co, n, g: mix(COL["horn_dk"], COL["horn"], smooth(g, 0.0, 0.5)), 0.5)
    for s in (-1, 1):
        horn(hd((0.2 * s, -0.1, 0.24)), R @ Vector((0.25 * s, -0.7, 0.6)), 0.34, 0.075, 0.06)
        horn(hd((0.38 * s, 0.05, -0.14)), R @ Vector((s, -0.2, -0.15)), 0.16, 0.05)
    nose_top, _ = hit(hd((0, -0.62, 1.0)), R @ Vector((0, 0, -1)))
    horn(nose_top - up * 0.02, R @ Vector((0, -0.35, 1.0)), 0.2, 0.065, -0.02)

    # ---- toenails ----------------------------------------------------------------------------------------
    for fx, fy in ((0.5, -0.74), (0.53, 0.72)):
        for sx in (-1, 1):
            for dx in (-0.11, 0.0, 0.11):
                base, _ = hit(Vector((sx * (fx + dx), fy - 0.8, 0.06)), Vector((0, 1, 0)))
                if base is None:
                    continue
                nail = ell((0, 0, 0), (0.055, 0.04, 0.05), cuts=2)
                nail.transform(M(base + Vector((0, 0.01, 0.0))))
                add("nails", nail, bone_m, lambda co, n, g: mix(COL["horn_dk"], COL["horn"], smooth(n.z, -0.3, 0.6)), 0.5)

    # ---- leaf-green back plates ----------------------------------------------------------------------
    n_pl = 12
    for k in range(n_pl):
        t = k / (n_pl - 1)
        at = kit._spline(SPINE, t * (len(SPINE) - 1))
        top, _ = hit(at + Vector((0, 0, 1.5)), Vector((0, 0, -1)))
        if top is None:
            continue
        size = 0.2 + 0.24 * math.sin(math.pi * min(t * 1.15, 1.0)) ** 0.8
        plate = kit.ball((0.07, size * 1.1, size * 2), cuts=3)
        for v in plate.verts:
            u = (v.co.z / size + 1) / 2                                        # 0 base .. 1 tip
            v.co.y *= 1 - 0.75 * smooth(u, 0.45, 1.0)                          # a pointed leaf
            v.co.y += 0.12 * size * u * u                                      # tips lean back a little
            v.co.x *= 1 - 0.5 * u
        paint(plate, lambda co, n, g, size=size: mix(mix(COL["plate"], COL["plate_lt"], smooth(co.z / size, -0.2, 0.8)),
                                                      COL["plate_dk"], 0.6 * smooth(abs(co.y) / (size * 0.55), 0.6, 1.0)))
        x = 0.07 * (1 if k % 2 else -1) * (1 - t * 0.5)
        plate.transform(M(Vector((x, top.y, top.z + size * 0.75)), rot=(0, 6 * (1 if k % 2 else -1), 0)))
        add("plates", plate, plate_m, None, 0.7)

    lowest = min(v.co.z for k, (bm_, _) in c.parts.items() if not k.startswith("GLOW") for v in bm_.verts)
    for bm_, _ in c.parts.values():
        bm_.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    two_threads()
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    parts = [ob for ob in c.objects if ob not in glow and ob not in eyes]
    if "before_bake" in globals():
        before_bake(parts)
    body = kit.bake_texture(parts, texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
    bake_rough(body, GRAIN)
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
    two_threads()
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
