"""GoldSlug pet: a dapper little golden slug gentleman, remade from the game's lumpy gold blob with a black
moustache, a purple mouth and sparkles. Built from scratch by script.

    python models/pets/goldslug.py --review out/goldslug.png      # render the review sheet
    python models/pets/goldslug.py --export models/export/goldslug.fbx

Must-haves, checked in every review:
  1. The same pet: a gold blob-slug with a black moustache, a purple mouth and sparkles round it.
  2. A smooth, rich gold body that looks like hammered metal, not plastic: dents in the colour, a
     roughness map with variation, a dark horizon line and pale highlights painted in.
  3. A neat curled black moustache, friendly eyes, a monocle and a tiny top hat with a violet ribbon.
  4. A slug, not a blob: an upright front, a mantle saddle, a tapering tail and a paler foot fringe.
  5. A few floating sparkles (GLOW).
  6. Matte painted textures with crease shading; about 3 studs tall; Body under 12k triangles.

Round 3: a bigger head on a slight neck, so it is not a bean; feelers peeking out under the hat brim; a narrower, golden foot fringe; a darker mouth.

Round 2: one smooth body lofted along the spine (the stacked balls read as a snowman); a richer, deeper gold with a stronger dark horizon line and lower roughness; a slim foot fringe instead of a flat plate; a small open plum smile; golden sparkles.

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

# ---- the gold slug --------------------------------------------------------------------------------

NAME = "GoldSlug"
COL = {"gold": hexc("#CF8E16"), "gold_lt": hexc("#F5CF5C"), "gold_hi": hexc("#FFF0BC"), "gold_dk": hexc("#74440A"),
       "gold_deep": hexc("#4A2A06"), "foot": hexc("#E8BF62"), "foot_dk": hexc("#B4842E"), "blush": hexc("#E88A52"),
       "tache": hexc("#1A1416"), "tache_hi": hexc("#4A3E44"), "mouth": hexc("#3A1230"), "tongue": hexc("#9A4078"),
       "hat": hexc("#1D1A21"), "hat_hi": hexc("#3B3644"), "ribbon": hexc("#6D3CA8"), "ribbon_dk": hexc("#472676"),
       "white": hexc("#FFFFFF"), "brass": hexc("#B8862C"), "brass_lt": hexc("#EAC468")}
SCALE = 1.15
BAKE = {"shade": 0.5, "rough": 0.45}
GRAIN = [("cells", 16.0, 0.1), ("noise", 45.0, 0.05)]
HEAD = Vector((0, -0.42, 1.62))
HEAD_M = M(HEAD, rot=(-4, 0, 0))
FACE = Vector((0, -0.95, 1.65)) * SCALE
FOCUS = FACE
FACE_DIST = 4.6
SPARKLES = [((0.82, -0.62, 1.95), 0.13, 10), ((-0.86, -0.3, 1.25), 0.1, -15), ((0.78, 0.55, 0.95), 0.085, 25),
            ((-0.6, -0.8, 2.45), 0.075, 5), ((-0.35, 1.25, 0.85), 0.08, -30)]


def star(r, thick=0.25):
    """A four-pointed sparkle in the XZ plane, puffed out to the front and back."""
    bm = bmesh.new()
    ring = []
    for k in range(8):
        a = math.pi * k / 4
        rr = r if k % 2 == 0 else r * 0.3
        ring.append(bm.verts.new((rr * math.cos(a), 0, rr * math.sin(a))))
    f, b = bm.verts.new((0, -r * thick, 0)), bm.verts.new((0, r * thick, 0))
    for k in range(8):
        bm.faces.new((ring[k], ring[(k + 1) % 8], f))
        bm.faces.new((ring[(k + 1) % 8], ring[k], b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build():
    gold_m = grained("Gold", [("cells", 16.0, 0.09), ("edges", 16.0, 0.14), ("noise", 50.0, 0.04)], rough=0.32)
    cloth_m = painted("Cloth", dict(strength=0.25, mottle=0.1, fine=70.0, length=3.0), rough=0.85)
    eye_m = kit.material("Eyes", "#1C130E", rough=0.06)
    glow = kit.material("GLOW_Sparkle", "#FFD45C", rough=0.4, emit=2.0)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.5):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- one fused skin: upright front, low body, tapering tail, foot fringe -------------------------
    spine = [(0, 2.05, 0.09), (0, 1.45, 0.2), (0, 0.75, 0.38), (0, 0.12, 0.56), (0, -0.28, 0.95), (0, -0.42, 1.35), HEAD]
    clay = [loft(spine, lambda t: 0.06 + 0.5 * smooth(t, 0.0, 0.55) - 0.09 * smooth(t, 0.7, 0.88), segs=20, rings=36),
            ell(hd((0, 0.02, 0.02)), (0.56, 0.5, 0.52)),
            ell(hd((0, -0.33, -0.14)), (0.22, 0.15, 0.13)),                     # muzzle under the moustache
            ell((0, 0.1, 0.42), (0.6, 0.85, 0.4)),                              # a wide low belly, so it sits flat
            ell((0, 0.45, 0.07), (0.64, 1.2, 0.075)),                           # foot fringe
            ell((0, -0.22, 0.07), (0.6, 0.48, 0.075))]
    for s in (-1, 1):                                                        # feelers peeking out under the hat brim
        clay.append(loft([hd((0.26 * s, 0.0, 0.3)), hd((0.42 * s, -0.04, 0.36)), hd((0.56 * s, -0.08, 0.36))],
                         lambda t: lerp(0.075, 0.045, t), segs=10, rings=8))
        clay.append(ell(hd((0.57 * s, -0.085, 0.36)), (0.055, 0.055, 0.055)))
    for s in (-1, 1):
        clay.append(ell(hd((0.24 * s, -0.26, -0.12)), (0.17, 0.15, 0.14)))       # cheeks
    skin = fuse(join(clay), voxel=0.02, factor=0.6, iterations=6)
    kit.lumpy(skin, amount=0.012, freq=3.0, seed=2.0)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.2 * s, -1.5, 0.1)), fwd) for s in (-1, 1)]
    smile = [hit(hd((x, -1.5, -0.25 + 0.9 * x * x)), fwd)[0] for x in (-0.14, -0.1, -0.05, 0.0, 0.05, 0.1, 0.14)]
    HINV = HEAD_M.inverted()

    def mouth_in(co):
        """0..1 inside the small open smile under the moustache."""
        p = HINV @ co
        if p.y > -0.2 or abs(p.x) > 0.13:
            return 0.0
        top, bot = -0.255 + 0.8 * p.x * p.x, -0.33 + 3.2 * p.x * p.x
        return smooth(p.z, bot - 0.003, bot + 0.012) * smooth(p.z, top + 0.003, top - 0.01)
    brows = [[hit(hd((s * x, -1.5, 0.27 + 0.05 * math.sin(math.pi * (x - 0.1) / 0.2))), fwd)[0] for x in (0.1, 0.15, 0.2, 0.25, 0.3)]
             for s in (-1, 1)]

    def carve(co, n):
        d = Vector()
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.07, 0.13))
        if (co - HEAD).length < 0.8:
            d -= n * 0.014 * (1 - smooth(poly_dist(co, smile), 0.008, 0.026))
            d -= n * 0.035 * mouth_in(co)
        if co.z < 0.24:                                                          # fine grooves round the foot fringe
            a = math.atan2(co.y - 0.2, co.x)
            d -= n * 0.006 * (0.5 + 0.5 * math.sin(a * 60)) * smooth(co.z, 0.24, 0.12)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 7000, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.35, -0.05))).length, 0.25, 0.5)), factor=1.0)

    def gold_colour(co, n, g=0.0):
        col = mix(COL["gold_deep"], COL["gold"], smooth(n.z, -0.9, -0.15))
        col = mix(col, COL["gold_dk"], 0.8 * smooth(n.z, -0.12, 0.06) * smooth(n.z, 0.36, 0.18))   # the dark horizon line of polished metal
        col = mix(col, COL["gold_lt"], smooth(n.z, 0.3, 0.8))
        col = mix(col, COL["gold_hi"], 0.45 * smooth(n.z, 0.82, 0.97))
        col = mix(col, COL["gold_dk"], 0.25 * smooth(noise.noise(co * 3.5 + Vector((4, 1, 0))), 0.15, 0.6))   # soft tarnish
        foot = smooth(co.z, 0.24, 0.16)
        col = mix(col, mix(COL["foot"], COL["foot_dk"], 0.5 * smooth(n.z, 0.2, -0.6)), foot)
        for s in (-1, 1):
            col = mix(col, COL["blush"], 0.35 * (1 - smooth((co - hd((0.3 * s, -0.36, -0.1))).length, 0.05, 0.14)))
        if (co - HEAD).length < 0.8:
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.01, 0.018))
            m_in = mouth_in(co)
            if m_in > 0:
                p = HINV @ co
                inner = mix(COL["mouth"], COL["tongue"], smooth(p.z, -0.28, -0.31))
                col = mix(col, inner, smooth(m_in, 0.05, 0.5))
            for b in brows:
                col = mix(col, COL["tache"], 1 - smooth(poly_dist(co, b), 0.012, 0.02))
        return col

    def gold_rough(co, n, g=0.0):
        r = 0.3 + 0.14 * smooth(noise.noise(co * 3.5 + Vector((4, 1, 0))), 0.15, 0.6)
        return lerp(r, 0.75, smooth(co.z, 0.24, 0.16))
    add("skin", skin, gold_m, gold_colour, gold_rough)

    # ---- eyes, with a monocle on the right ------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.088, 0.1, 0.05), cuts=3), e - en * 0.02, en), eye_m)
        add("glints", ell(e + en * 0.028 + R @ Vector((-0.03, 0, 0.035)), (0.026, 0.018, 0.026), cuts=1), cloth_m, COL["white"], 0.3)
        add("glints", ell(e + en * 0.03 + R @ Vector((0.028, 0, -0.032)), (0.011, 0.008, 0.011), cuts=1), cloth_m, COL["white"], 0.3)
    e, en = eyes[1]
    ring = lathe([(0.135 + 0.018 * math.cos(t), 0.018 * math.sin(t)) for t in (2 * math.pi * j / 8 for j in range(8))], segs=28, closed=True)
    facing(ring, e + en * 0.035, en)
    add("monocle", ring, gold_m, lambda co, n, g: mix(COL["brass"], COL["brass_lt"], smooth(n.z, -0.2, 0.7)), 0.3)
    q = en.to_track_quat('Z', 'Y').to_matrix()
    a0 = e + en * 0.035 + q @ Vector((0.1, -0.09, 0))
    chain = loft([a0, a0 + Vector((0.12, 0.02, -0.12)), a0 + Vector((0.2, 0.12, -0.32)), Vector((0.56, -0.2, 1.0))],
                 lambda t: 0.011, segs=6, rings=16)
    add("monocle", chain, gold_m, COL["brass"], 0.3)

    # ---- a curled moustache ------------------------------------------------------------------------------
    for s in (-1, 1):
        base = [hit(hd((s * x, -1.5, -0.13 - 0.25 * x * x)), fwd) for x in (0.0, 0.08, 0.16, 0.24)]
        pts = [p + nn * 0.035 for p, nn in base]
        tip = pts[-1]
        pts += [tip + Vector((0.09 * s, 0.05, 0.0)), tip + Vector((0.15 * s, 0.08, 0.07)), tip + Vector((0.14 * s, 0.07, 0.15)),
                tip + Vector((0.08 * s, 0.05, 0.15)), tip + Vector((0.075 * s, 0.04, 0.09))]
        tache = loft(pts, lambda t: 0.018 + 0.045 * math.sin(math.pi * min(t * 1.6, 1.0)) ** 0.8 * (1 - t) ** 0.6, segs=10, rings=22, flat=0.7)
        add("moustache", tache, cloth_m, lambda co, n, g: mix(COL["tache"], COL["tache_hi"], 0.5 * smooth(n.z, 0.2, 0.9)), 0.7)

    # ---- a little top hat with a violet ribbon ------------------------------------------------------------
    HAT = M(hd((0.05, 0.03, 0.42)), rot=(-8, 12, 0))
    hat = lathe([(0, 0.03), (0.26, 0.03), (0.4, 0.0), (0.445, 0.02), (0.435, 0.05), (0.3, 0.06), (0.262, 0.11),
                 (0.265, 0.4), (0.285, 0.52), (0.26, 0.555), (0, 0.56)], segs=36)
    hat.transform(HAT)
    HR = HAT.to_3x3()

    def hat_col(co, n, g):
        ln = HR.inverted() @ n
        col = mix(COL["hat"], COL["hat_hi"], 0.6 * smooth(ln.z, 0.3, 0.95))
        return mix(col, COL["hat"], 0.6 * smooth(-ln.z, 0.2, 0.8))
    add("hat", hat, cloth_m, hat_col, 0.88)
    band = lathe([(0.262, 0.07), (0.282, 0.075), (0.284, 0.18), (0.264, 0.185)], segs=36, closed=True)
    band.transform(HAT)
    add("hat", band, cloth_m, lambda co, n, g: mix(COL["ribbon"], COL["ribbon_dk"], 0.5 * smooth(n.z, 0.3, -0.6)), 0.7)
    for k in (-1, 1):                                                       # a small bow on the side
        loop = loft([HAT @ Vector((0.27, -0.03, 0.13)), HAT @ Vector((0.33, -0.08 * k - 0.03, 0.13 + 0.05 * k)),
                     HAT @ Vector((0.3, -0.03 - 0.14 * k, 0.13 + 0.03 * k))], lambda t: 0.035 * math.sin(math.pi * (0.2 + 0.8 * t)) + 0.01,
                    segs=8, rings=8, flat=0.45)
        add("hat", loop, cloth_m, COL["ribbon"], 0.7)

    # ---- sparkles ---------------------------------------------------------------------------------------
    for at, r, spin in SPARKLES:
        sp = star(r)
        sp.transform(M(at, rot=(0, spin, 0)))
        roughen(sp, lambda co, n, g: 0.4)
        c.tally["sparkles"] = c.tally.get("sparkles", 0) + sum(len(f.verts) - 2 for f in sp.faces)
        c.add(sp, glow)

    lowest = min(v.co.z for k, (bm, _) in c.parts.items() if not k.startswith("GLOW") for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
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
