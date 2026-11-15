"""Ankylo pet: a sandy-tan ankylosaur, low and wide, with a domed back of rounded plates and a big club tail,
remade from the game's tan armoured dinosaur with white spikes and a club tail. Built from scratch by script.

    python models/pets/ankylo.py --review out/ankylo.png      # render the review sheet
    python models/pets/ankylo.py --export models/export/ankylo.fbx

Must-haves, checked in every review:
  1. The same pet: a tan armoured dinosaur on four stubby legs, pale spikes along its sides, a club tail.
  2. Clearly not the ArmorDino: sandy tan, not stone grey; low and wide; rows of rounded osteoderm plates
     over a domed back; short blunt cream side spikes; a big two-lobed tail club.
  3. A cheerful beak-like face: a broad darker beak with a smile line, small happy eyes, cheek horn nubs.
  4. Pebbly scaled skin with darker joins, a paler belly, cream toenails.
  5. Matte textures with roughness variation; 2.5-3.5 studs tall, under 6 long; Body under 12k triangles.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 2: no brow plates over the eyes (they read as worried eyebrows); a deeper, wider smile line so it survives the bake; smaller, flatter toenails (they looked like pebbles); a bigger two-lobed club on a shorter tail; a taller dome and a larger scale (it was 1.7 studs tall); plates and nails trimmed back under budget.

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
    used = px[..., 0] > 1e-4                              # texels the bake reached, with its margin
    rough = px[..., 0]
    rough[~used] = float(np.median(rough[used])) if used.any() else 0.6     # so mipmaps do not bleed gloss into the seams
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


def _rnd(i, k=0.0):
    """A repeatable pseudo-random number 0..1 for index i (and an optional second key)."""
    h = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return h - math.floor(h)


def aim(bm, at, d, up=(0, 0, 1)):
    """Turn a shape built along +Y (its front) so +Y points along d, keeping +Z near `up`, then move it to `at`."""
    d = Vector(d).normalized()
    q = d.to_track_quat('Y', 'Z')
    bm.transform(M(at) @ q.to_matrix().to_4x4())
    return bm


def fibonacci(n):
    """n directions spread evenly over a sphere."""
    out = []
    for k in range(n):
        z = 1 - 2 * (k + 0.5) / n
        a = k * 2.39996
        r = math.sqrt(max(0.0, 1 - z * z))
        out.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    return out

# ---- the ankylosaur ------------------------------------------------------------------------------------

NAME = "Ankylo"
COL = {"tan": hexc("#C79E68"), "tan_lt": hexc("#E2C08C"), "tan_dk": hexc("#8C6840"), "belly": hexc("#EAD6AE"),
       "plate": hexc("#A97F4C"), "plate_lt": hexc("#D2AA70"), "plate_dk": hexc("#6E5030"), "spike": hexc("#F1E6CE"),
       "spike_dk": hexc("#C2AC86"), "beak": hexc("#7E5E3E"), "beak_lt": hexc("#A07E58"), "mouth": hexc("#4A3220"),
       "nail": hexc("#DCC9A2"), "white": hexc("#FFFFFF"), "cheek": hexc("#D98E70")}
SCALE = 1.5
BAKE = {"shade": 0.5, "rough": 0.85}
GRAIN = [("cells", 26.0, 0.05), ("noise", 9.0, 0.03)]
BODY = Vector((0, 0.1, 0.78))
BODY_R = Vector((0.74, 0.95, 0.56))
HEAD = Vector((0, -1.12, 0.64))
HEAD_M = M(HEAD, rot=(4, 0, 0))
FACE = HEAD + Vector((0, -0.3, 0.0))
FOCUS = FACE * SCALE
FACE_DIST = 3.8
LEGS = [(-0.5, -0.5), (0.5, -0.5), (-0.52, 0.58), (0.52, 0.58)]
TAIL = [Vector((0, 0.85, 0.74)), Vector((0, 1.25, 0.64)), Vector((0, 1.65, 0.54)), Vector((0, 1.98, 0.48))]


def build():
    skin_m = scaled("Skin", rough=0.85, size=0.07, joins=0.3, vary=0.12)
    plate_m = grained("Plates", [("cells", 34.0, 0.07), ("noise", 14.0, 0.05)], rough=0.8)
    eye_m = kit.material("Eyes", "#1A120C", rough=0.05)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()
    HINV = HEAD_M.inverted()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.85):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- one fused skin: a low wide dome, a broad head with a beak, stubby legs, a tapering tail -----------
    body = ell(BODY, BODY_R)
    for v in body.verts:
        if v.co.z < 0.5:
            v.co.z = 0.5 - (0.5 - v.co.z) * 0.45                                  # a flatter belly
    clay = [body,
            ell((0, -0.75, 0.66), (0.5, 0.3, 0.32)),                             # neck and shoulders
            ell(hd((0, 0, 0)), (0.33, 0.33, 0.24)),                              # broad head
            ell(hd((0, -0.28, -0.05)), (0.22, 0.16, 0.14)),                      # beak
            loft(TAIL, lambda t: lerp(0.32, 0.09, t ** 0.8), segs=14, rings=16)]
    for s in (-1, 1):
        clay.append(ell(hd((0.24 * s, 0.02, -0.04)), (0.13, 0.17, 0.15)))        # cheeks
    for (x, y) in LEGS:
        hind = y > 0
        clay += [ell((x * 0.95, y, 0.5), (0.22, 0.26 if hind else 0.22, 0.26)),
                 loft([(x, y, 0.52), (x * 1.02, y - 0.01, 0.25), (x * 1.03, y - 0.02, 0.08)], lambda t: lerp(0.17, 0.15, t), segs=12, rings=6),
                 ell((x * 1.03, y - 0.05, 0.07), (0.17, 0.19, 0.07))]
    club = [ell(TAIL[-1] + Vector((0.16 * s, 0.14, -0.01)), (0.24, 0.24, 0.17)) for s in (-1, 1)] + [ell(TAIL[-1] + Vector((0, 0.12, 0.02)), (0.2, 0.24, 0.18))]
    clay += club
    skin = fuse(join(clay), voxel=0.022, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    up_h = R @ Vector((0, 0, 1))
    eyes = []
    for s in (-1, 1):
        d = (R @ Vector((-0.6 * s, 1, -0.1))).normalized()
        eyes.append(hit(hd((0.2 * s, -0.12, 0.08)) - d * 1.0, d))
    smile = []
    for s in (-1, 1):
        smile.append([hit(hd((s * x, -1.5, -0.1 + 0.6 * x * x + 0.05 * x)), fwd)[0] for x in (0.0, 0.05, 0.1, 0.14, 0.18, 0.21)])
    beak_tip = hit(hd((0, -1.5, -0.04)), fwd)[0]

    def carve(co, n):
        d = Vector()
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.05, 0.085))
        if (co - beak_tip).length < 0.5:
            for line in smile:
                d -= n * 0.018 * (1 - smooth(poly_dist(co, line), 0.008, 0.026))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5600, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.25, -0.02))).length, 0.25, 0.42)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["tan_dk"], COL["tan"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["tan_lt"], 0.3 * smooth(n.z, 0.5, 1.0))
        col = mix(col, COL["belly"], smooth(-n.z, 0.3, 0.7) * smooth(co.z, 0.55, 0.4))
        col = mix(col, COL["tan_dk"], 0.2 * smooth(noise.noise(co * 3.5), 0.0, 0.6))
        q = HINV @ co
        if q.length < 0.6:
            bk = smooth(q.y, -0.24, -0.32)
            col = mix(col, mix(COL["beak"], COL["beak_lt"], 0.5 * smooth(n.z, 0.0, 0.8)), bk)
            for line in smile:
                col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, line), 0.011, 0.022))
            for s in (-1, 1):
                col = mix(col, COL["cheek"], 0.3 * (1 - smooth((q - Vector((0.27 * s, -0.12, -0.08))).length, 0.03, 0.09)))
        return col
    add("skin", skin, skin_m, colour, 0.86)

    # ---- small happy eyes -----------------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.05, 0.054, 0.03), cuts=3), e - en * 0.006, en), eye_m)
        add("glints", ell(e + en * 0.024 + R @ Vector((-0.014 * s, 0, 0.016)), (0.013, 0.008, 0.013), cuts=1), skin_m, COL["white"], 0.3)
        low = facing(ell((0, 0, 0), (0.058, 0.06, 0.038), cuts=4), e - en * 0.004, en)       # a smiling lower lid
        bmesh.ops.delete(low, geom=[v for v in low.verts if (v.co - e).dot(up_h) > -0.024], context='VERTS')
        add("lids", low, skin_m, COL["tan"])

    # ---- rounded osteoderm plates over the dome, in rows ------------------------------------------------------
    def plate(r, h):
        return lathe([(0.0, h), (r * 0.55, h * 0.92), (r * 0.88, h * 0.6), (r, h * 0.15), (r * 0.98, -0.03)], segs=8)

    def plate_col(co, n, g):
        col = mix(COL["plate_dk"], COL["plate"], smooth(g, 0.95, 0.5))
        return mix(col, COL["plate_lt"], 0.5 * smooth(g, 0.4, 0.0))
    rows = 7
    for i in range(rows):
        ang = math.radians(-58 + 116 * i / (rows - 1))                          # across the back, side to side
        n_along = 7 if i in (0, rows - 1) else 8
        for k in range(n_along):
            yy = -0.6 + 1.25 * (k + 0.5 * (i % 2)) / n_along
            o = BODY + Vector((math.sin(ang) * 2.0, yy, math.cos(ang) * 2.0))
            p, nn = hit(o, BODY + Vector((0, yy, 0)) - o)
            if p is None:
                continue
            r = 0.12 - 0.025 * abs(math.sin(ang)) + 0.015 * _rnd(i, k)
            b = plate(r, 0.065 + 0.02 * _rnd(k, i))
            b.transform(Matrix.Translation(p - nn * 0.01) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("plates", b, plate_m, plate_col, 0.8)
    for k in range(5):                                                            # a neck collar of plates
        a = math.radians(-60 + 30 * k)
        o = Vector((math.sin(a) * 2, -0.78, 0.66 + math.cos(a) * 2))
        p, nn = hit(o, Vector((0, -0.78, 0.66)) - o)
        if p is not None:
            b = plate(0.1, 0.07)
            b.transform(Matrix.Translation(p - nn * 0.01) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("plates", b, plate_m, plate_col, 0.8)
    for k in range(5):                                                            # small plates down the tail
        t = 0.1 + 0.75 * k / 4
        p0 = kit._spline(TAIL, t * (len(TAIL) - 1))
        p, nn = hit(p0 + Vector((0, 0, 1)), (0, 0, -1))
        if p is not None:
            b = plate(0.09 - 0.03 * t, 0.05)
            b.transform(Matrix.Translation(p - nn * 0.01) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("plates", b, plate_m, plate_col, 0.8)

    # ---- short blunt cream spikes along the flanks and the tail -------------------------------------------------
    def spike(L, r):
        return lathe([(r, -0.02), (r * 0.8, L * 0.35), (r * 0.4, L * 0.8), (r * 0.15, L), (0.0, L * 1.03)], segs=8)
    spike_col = lambda co, n, g: mix(COL["spike_dk"], COL["spike"], smooth(g, 0.0, 0.5))
    for s in (-1, 1):
        for k in range(7):
            yy = -0.6 + 1.25 * k / 6
            o = BODY + Vector((s * 2.0, yy, 0.02))
            p, nn = hit(o, BODY + Vector((0, yy, 0.02)) - o)
            if p is None:
                continue
            d = (nn + Vector((0, 0.25, -0.15))).normalized()
            b = spike(0.18 + 0.04 * math.sin(math.pi * k / 6), 0.07)
            b.transform(Matrix.Translation(p - d * 0.02) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("spikes", b, plate_m, spike_col, 0.6)
        for k in range(3):
            t = 0.25 + 0.25 * k
            p0 = kit._spline(TAIL, t * (len(TAIL) - 1))
            p, nn = hit(p0 + Vector((s * 1.0, 0, 0.05)), (-s, 0, 0))
            if p is not None:
                d = (nn + Vector((0, 0.35, 0))).normalized()
                b = spike(0.13 - 0.02 * k, 0.05)
                b.transform(Matrix.Translation(p - d * 0.015) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
                add("spikes", b, plate_m, spike_col, 0.6)
        for k in range(2):                                                        # cheek horn nubs
            at = hd((0.3 * s, 0.1 + 0.1 * k, 0.06 - 0.06 * k))
            d = (R @ Vector((s * 1.0, 0.35, 0.15 - 0.2 * k))).normalized()
            b = spike(0.1, 0.05)
            b.transform(Matrix.Translation(at) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("spikes", b, plate_m, spike_col, 0.6)

    # ---- cream toenails ----------------------------------------------------------------------------------------
    for (x, y) in LEGS:
        for k in (-1, 0, 1):
            nail = ell((0, 0, 0), (0.035, 0.04, 0.026), cuts=1)
            nail.transform(M((x * 1.03 + 0.085 * k, y - 0.215 + 0.02 * abs(k), 0.028)))
            add("nails", nail, plate_m, COL["nail"], 0.55)

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
        head = Vector(FACE) * SCALE
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
