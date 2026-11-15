"""RedPanda pet: a red panda with a russet coat, a white face mask and a thick ringed tail held up, remade from
the game's blocky orange-red animal with a white face, dark legs and a tall bushy tail. Built from scratch by
script.

    python models/pets/redpanda.py --review out/redpanda.png      # render the review sheet
    python models/pets/redpanda.py --export models/export/redpanda.fbx

Must-haves, checked in every review:
  1. The same pet: an orange-red animal on four dark legs with a white face and a tall bushy tail held up.
  2. A real red panda: russet coat, black-brown legs and belly, a thick tail ringed in russet and buff.
  3. A white face mask: white muzzle, cheeks and brow spots, with russet tear marks from the eyes down.
  4. A friendly face: round dark eyes with glints, a small black nose, big rounded ears with white rims.
  5. Matte soft-fur texture with roughness variation; about 3 studs tall; Body under 12k triangles.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

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

# ---- the red panda -----------------------------------------------------------------------------------

NAME = "RedPanda"
COL = {"rus": hexc("#B4471D"), "rus_lt": hexc("#D2662E"), "rus_dk": hexc("#7E2C12"), "face": hexc("#C9682F"),
       "white": hexc("#F5EEE4"), "white_dk": hexc("#D9CEC0"), "black": hexc("#2C1A14"), "black_lt": hexc("#4A2E22"),
       "buff": hexc("#DC9150"), "ring": hexc("#8C3416"), "nose": hexc("#161010"), "nose_lt": hexc("#3E3434"),
       "tear": hexc("#9A3A18"), "ear_in": hexc("#5A2A1A"), "mouth": hexc("#4A2A20"), "glint": hexc("#FFFFFF")}
SCALE = 1.5
BAKE = {"shade": 0.45, "rough": 0.9}
GRAIN = [("streak", 70.0, 0.05), ("noise", 7.0, 0.03)]
HEAD = Vector((0, -0.58, 1.1))
HEAD_M = M(HEAD, rot=(4, 0, 0))
FACE = HEAD + Vector((0, -0.28, -0.03))
FOCUS = FACE * SCALE
FACE_DIST = 3.2
LEGS = [(-0.17, -0.32), (0.17, -0.32), (-0.18, 0.44), (0.18, 0.44)]
TAIL = [Vector((0, 0.52, 0.8)), Vector((0, 0.76, 0.96)), Vector((0, 0.86, 1.3)), Vector((0, 0.8, 1.66)), Vector((0, 0.64, 1.9))]


def build():
    fur_m = painted("Fur", dict(strength=0.28, mottle=0.1, fine=58.0, length=7.0), rough=0.9)
    eye_m = kit.material("Eyes", "#1A100C", rough=0.05)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()
    HINV = HEAD_M.inverted()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.9):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def lock(at, d, length, r, droop=0.3, flat=0.8, segs=6, rings=5):
        at, d = Vector(at), Vector(d).normalized()
        end = at + d * length + Vector((0, 0, -length * droop))
        return loft([at - d * 0.02, at + d * length * 0.5, end], lambda t: r * (1 - t) ** 0.8 + 0.004, segs=segs, rings=rings, flat=flat)

    # ---- one fused skin: a long soft body, a broad round head with fluffy cheeks, short dark legs ----------
    clay = [ell((0, 0.08, 0.72), (0.29, 0.5, 0.29)),
            ell((0, -0.28, 0.78), (0.29, 0.27, 0.31)),                           # chest
            ell((0, 0.4, 0.76), (0.29, 0.26, 0.3)),                              # rump
            ell(hd((0, 0, 0)), (0.31, 0.27, 0.26)),                              # head
            ell(hd((0, -0.24, -0.09)), (0.12, 0.1, 0.08))]                       # short muzzle
    for s in (-1, 1):
        clay.append(ell(hd((0.21 * s, -0.1, -0.08)), (0.15, 0.15, 0.14)))         # cheeks
        for k in range(5):
            at = hd((0.29 * s, -0.08 + 0.04 * k, -0.06 - 0.03 * k))
            clay.append(lock(at, R @ Vector((s * 0.9, 0.2, -0.4)), 0.12, 0.055, droop=0.2))
    for (x, y) in LEGS:
        hind = y > 0
        clay += [ell((x * 1.12, y, 0.6), (0.14, 0.2 if hind else 0.16, 0.24)),
                 loft([(x, y, 0.62), (x, y - 0.01, 0.32), (x, y - 0.02, 0.08)], lambda t: lerp(0.1, 0.085, t), segs=12, rings=6),
                 ell((x, y - 0.05, 0.06), (0.09, 0.12, 0.06))]
    skin = fuse(join(clay), voxel=0.016, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.13 * s, -1.5, 0.04)), fwd) for s in (-1, 1)]
    nose_at, nose_n = hit(hd((0, -1.5, -0.06)), fwd)
    mouth = []
    for s in (-1, 1):
        mouth.append([hit(hd((s * x, -1.5, -0.14 + 12.0 * (x - 0.03) ** 2)), fwd)[0] for x in (0.0, 0.015, 0.03, 0.045, 0.06, 0.07)])
    mouth_top = hit(hd((0, -1.5, -0.1)), fwd)[0]
    tears = []
    for s in (-1, 1):
        tears.append([hit(hd((s * x, -1.5, z)), fwd)[0] for x, z in ((0.11, -0.01), (0.105, -0.06), (0.09, -0.11), (0.075, -0.15))])

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 9.0)
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.055, 0.09))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 7000, keep=lambda co: 0.85 * (1 - smooth((Vector(co) - hd((0, -0.22, -0.03))).length, 0.24, 0.42)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["rus_dk"], COL["rus"], smooth(n.z, -0.5, 0.2))
        col = mix(col, COL["rus_lt"], 0.3 * smooth(n.z, 0.4, 1.0))
        col = mix(col, COL["rus_dk"], 0.2 * smooth(noise.noise(co * 4.0), 0.0, 0.6))
        dark = max(smooth(co.z, 0.62, 0.45), smooth(-n.z, 0.3, 0.7) * smooth(co.z, 0.85, 0.7))   # black-brown legs and belly
        col = mix(col, mix(COL["black"], COL["black_lt"], 0.4 * smooth(n.z, -0.2, 0.6)), dark)
        q = HINV @ co
        if q.length < 0.5:
            col = mix(col, COL["face"], smooth(q.y, -0.05, -0.2))
            wm = 1 - smooth(((q - Vector((0, -0.26, -0.1))) * Vector((1.0, 0.9, 1.1))).length, 0.11, 0.15)    # muzzle
            for s in (-1, 1):
                wm = max(wm, 1 - smooth(((q - Vector((0.24 * s, -0.14, -0.1))) * Vector((0.9, 1.0, 1.0))).length, 0.09, 0.13))   # cheeks
                wm = max(wm, 1 - smooth(((q - Vector((0.12 * s, -0.22, 0.13))) * Vector((0.8, 1.0, 1.3))).length, 0.035, 0.055))  # brow spots
            col = mix(col, mix(COL["white_dk"], COL["white"], smooth(n.z, -0.6, 0.2)), wm)
            for line in tears:
                col = mix(col, COL["tear"], 0.9 * (1 - smooth(poly_dist(co, line), 0.014, 0.026)))
            for line in mouth:
                col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, line), 0.005, 0.012))
            col = mix(col, COL["mouth"], 1 - smooth(seg_dist(co, mouth_top, mouth[0][0]), 0.005, 0.012))
        return col
    add("skin", skin, fur_m, colour, 0.92)

    # ---- round dark eyes, a small black nose ----------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.06, 0.066, 0.036), cuts=3), e - en * 0.008, en), eye_m)
        add("glints", ell(e + en * 0.03 + R @ Vector((-0.02 * s, 0, 0.022)), (0.017, 0.01, 0.017), cuts=1), fur_m, COL["glint"], 0.3)
        add("glints", ell(e + en * 0.031 + R @ Vector((0.016 * s, 0, -0.02)), (0.008, 0.005, 0.008), cuts=1), fur_m, COL["glint"], 0.3)
    nose = ell((0, 0, 0), (0.06, 0.04, 0.042), cuts=2)
    for v in nose.verts:
        v.co.x *= 1 - 0.35 * smooth(-v.co.z, 0.0, 0.04)
    nose.transform(M(nose_at + nose_n * 0.018, rot=(6, 0, 0)))
    add("nose", nose, fur_m, lambda co, n, g: mix(COL["nose"], COL["nose_lt"], 0.6 * smooth(n.z, 0.5, 0.95)), 0.35)

    # ---- big rounded ears, white rims, dark insides ------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.21 * s, 0.03, 0.17))
        pts = [root, root + R @ Vector((0.07 * s, 0.0, 0.11)), root + R @ Vector((0.11 * s, 0.01, 0.2))]
        ear = loft(pts, lambda t: 0.12 * math.sin(math.pi * min(0.35 + t * 0.75, 1.0)) ** 0.6 + 0.02, segs=12, rings=9, flat=0.4)
        Ri = R.inverted()

        def ear_col(co, n, g, pts=pts):
            inside = smooth(-(Ri @ n).y, 0.35, 0.75)
            rim = smooth(poly_dist(co, pts), 0.07, 0.1) + smooth(g, 0.75, 0.95)
            col = mix(COL["rus"], COL["ear_in"], inside)
            return mix(col, COL["white"], min(1.0, rim))
        add("ears", ear, fur_m, ear_col)
        for k in range(3):
            at = pts[0] + R @ Vector((0.0, -0.025, 0.05 + 0.04 * k))
            add("ears", lock(at, R @ Vector((0.1 * s, -0.7, 0.7)), 0.08, 0.02, droop=0.0, segs=5, rings=3), fur_m, COL["white"])

    # ---- the thick ringed tail, held up ---------------------------------------------------------------------------
    parts = [loft(TAIL, lambda t: 0.1 + 0.07 * math.sin(math.pi * min(t * 1.15, 1.0)) ** 0.7, segs=14, rings=20)]
    for k in range(44):
        t = 0.08 + 0.8 * k / 43
        p = kit._spline(TAIL, t * (len(TAIL) - 1))
        a = k * 2.4
        d = Vector((math.cos(a), 0.5 * math.sin(a), 0.5 + 0.5 * math.sin(a)))
        parts.append(lock(p, d, 0.15, 0.08, droop=-0.1, flat=1.0))
    tail = fuse(join(parts), voxel=0.017, iterations=2)
    tail = decimate(tail, 2000)
    path = [kit._spline(TAIL, i / 60 * (len(TAIL) - 1)) for i in range(61)]

    def tail_col(co, n, g):
        i = min(range(61), key=lambda k: (path[k] - co).length_squared)
        t = i / 60
        ring = smooth(math.sin(t * math.pi * 9.0 + 0.6 + 0.25 * math.sin(co.x * 30.0)), -0.2, 0.25)
        col = mix(COL["ring"], mix(COL["buff"], COL["rus_lt"], 0.3), ring)
        col = mix(col, COL["ring"], smooth(t, 0.88, 1.0) * 0.6)
        return mix(col, COL["rus_dk"], 0.25 * smooth(-n.z, 0.0, 0.7))
    add("tail", tail, fur_m, tail_col)

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
