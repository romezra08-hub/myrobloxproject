"""MoonJelly pet: a pale aqua moon jellyfish with a small gentle face, remade from the game's pale aqua jellyfish
with a little face and pink trailing tentacles. Built from scratch by script.

    python models/pets/moonjelly.py --review out/moonjelly.png      # render the review sheet
    python models/pets/moonjelly.py --export models/export/moonjelly.fbx

Must-haves, checked in every review:
  1. The same pet: a pale aqua dome jellyfish with a small face low on the front and pink trailing tentacles.
  2. A frosted-glass bell: matte, with soft colour depth painted in (deeper aqua at the sides, a frosted rim,
     fine radial canals and the four pale rings of a moon jelly seen through the top), never glossy plastic.
  3. A gentle face: small eyes with a soft upper lid line lifting at the outer corners, glints high, a tiny
     smile and blush.
  4. Frilly oral arms under the bell and long, thin, curling pink tentacles; glowing spots on the rim (GLOW).
  5. Unlike SkyJelly (a pastel cloud) and SpiritBlob (a flame wisp); floats with the lowest tentacle tip at
     z=0; about 3 studs tall; Body under 12k triangles.

Final: round 3.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 3: bigger, darker lilac rings that show from the front three-quarter view, radial canals wide enough to
bake, a less washed-out top; pinker oral arms; the bell and tentacles lighter on faces (Body was 13k).

Round 2: the four rings and radial canals worked out in the shader (as vertex paint they were too coarse to
show); a smile drawn as a fine raised line (the painted one vanished); a taller, rounder dome with more aqua and a
lilac heart (the flat white top read as a mushroom cap); paler, shorter, more frilled oral arms; thinner
tentacles, and fewer faces to stay in budget.

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



def blade(L, w, th=0.02, cuts=3, curve=0.0, tip=1.0):
    """A pointed leaf along +X from the origin (width along Z, thickness along Y); g runs root 0 to tip 1."""
    bm = kit.ball((1, 1, 1), cuts=cuts)
    lg = bm.verts.layers.float.new("g")
    for v in bm.verts:
        u = min(max(v.co.x + 0.5, 0.0), 1.0)
        f = math.sin(math.pi * (0.06 + 0.94 * u ** 0.8)) ** (0.6 * tip) * (1 - 0.15 * u) + 0.03
        v.co = Vector((u * L, v.co.y * 2 * th * (0.4 + 0.6 * f) + curve * L * u * u, v.co.z * 2 * w * f))
        v[lg] = u
    return bm


def frame_to(bm, at, d, n):
    """Local X -> d, local Y -> n (made perpendicular), local Z -> their cross."""
    d = Vector(d).normalized()
    n = (Vector(n) - d * d.dot(Vector(n))).normalized()
    bm.transform(M(at) @ Matrix((d, n, d.cross(n))).transposed().to_4x4())
    return bm


def crystal(r, h, sides=6):
    """A pointed crystal prism, base at the origin, pointing up +Z. g runs 0 at the base to 1 at the tip."""
    return lathe([(0.0, -0.02), (r * 0.9, -0.02), (r, h * 0.12), (r * 0.95, h * 0.72), (0.0, h)], segs=sides)


def membrane(pts, rows=6, th=0.012, sag=0.0, up=(0, 0, 1)):
    """A thin skin over a fan of points: pts[0] is the root, pts[1:] the rim. Rows of quads from root to rim,
    both faces, with 'g' running 0 at the root to 1 at the rim; `sag` bows the middle of each rim edge inwards."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    root = Vector(pts[0])
    rim = [Vector(p) for p in pts[1:]]
    cols = []
    for k, p in enumerate(rim):
        col = []
        for i in range(rows + 1):
            t = i / rows
            q = root.lerp(p, t)
            col.append(q)
        cols.append(col)
    # bow the rim between spars
    fine = []
    for k in range(len(cols) - 1):
        for j in range(3):
            u = j / 3
            col = []
            for i in range(rows + 1):
                t = i / rows
                q = cols[k][i].lerp(cols[k + 1][i], u)
                q = root + (q - root) * (1 - sag * t * t * math.sin(math.pi * u))
                col.append(q)
            fine.append(col)
    fine.append(cols[-1])
    n = Vector(up).normalized()
    front, back = [], []
    for col in fine:
        f, b = [], []
        for i, q in enumerate(col):
            v1 = bm.verts.new(q + n * th)
            v2 = bm.verts.new(q - n * th)
            v1[lg] = v2[lg] = i / rows
            f.append(v1)
            b.append(v2)
        front.append(f)
        back.append(b)
    for a, b in zip(front, front[1:]):
        for i in range(rows):
            bm.faces.new((a[i], b[i], b[i + 1], a[i + 1]))
    for a, b in zip(back, back[1:]):
        for i in range(rows):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    for k in range(len(front) - 1):                                   # the rim edge
        bm.faces.new((front[k][-1], front[k + 1][-1], back[k + 1][-1], back[k][-1]))
    for side in (0, -1):
        f, b = front[side], back[side]
        for i in range(rows):
            bm.faces.new((f[i], f[i + 1], b[i + 1], b[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

# ---- the moon jelly -----------------------------------------------------------------------------------

NAME = "MoonJelly"
COL = {"aqua": hexc("#A9E8E4"), "aqua_lt": hexc("#E4FBF7"), "aqua_dk": hexc("#7FD3D2"), "teal": hexc("#5DB9BF"),
       "frost": hexc("#F4FFFD"), "canal": hexc("#E9FFFB"), "ring": hexc("#E2B4E4"), "ring_dk": hexc("#C796CF"),
       "pink": hexc("#F4B6D2"), "pink_lt": hexc("#FBE0EC"), "pink_dk": hexc("#DE86B4"), "blush": hexc("#F7A9C4"),
       "mouth": hexc("#7A4A78"), "lash": hexc("#3C3060"), "iris": hexc("#9C8AE0"), "lilac": hexc("#E6D8F6"), "glint": hexc("#FFFFFF")}
SCALE = 1.0
BAKE = {"shade": 0.32, "rough": 0.62}
GRAIN = [("noise", 11.0, 0.05), ("cells", 34.0, 0.03)]
TOP, RIM_Z, RIM_R = 3.12, 1.98, 1.0
FACE = Vector((0, -1.06, 2.28))
FOCUS = FACE * SCALE
FACE_DIST = 3.4
LOBES = 16


def ribbon(path, width, th, twist=1.0, frill=0.03, freq=7.0, segs=12, rings=36):
    """A flat ribbon along `path`, twisting `twist` half turns, its two long edges ruffled in and out of phase
    like the frilled oral arm of a jellyfish. Each vertex keeps 'g' (0 root to 1 tip) and 'e' (0 middle, 1 edge)."""
    pts = [Vector(p) for p in path]
    P = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    tangent = (P[1] - P[0]).normalized()
    normal = tangent.orthogonal().normalized()
    loops = []
    for i, p in enumerate(P):
        new = (P[min(i + 1, rings)] - P[max(i - 1, 0)]).normalized()
        axis = tangent.cross(new)
        if axis.length > 1e-6:
            normal = Matrix.Rotation(tangent.angle(new), 3, axis.normalized()) @ normal
        tangent = new
        t = i / rings
        n2 = Matrix.Rotation(math.pi * twist * t, 3, tangent) @ normal
        side = tangent.cross(n2).normalized()
        w = width(t)
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            ca, sa = math.cos(a), math.sin(a)
            ruff = frill * math.sin(t * freq * 2 * math.pi + (0.0 if ca > 0 else math.pi)) * ca * ca * min(1.0, t * 6)
            v = bm.verts.new(p + n2 * ca * w + side * (sa * th + ruff))
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


def bell_glass(name, rough=0.58):
    """The frosted bell: the vertex paint 'col', with the four pale rings of a moon jelly and fine radial canals
    worked out in the shader (finer than the mesh could carry as paint), where the vertex paint 'mk' allows them
    (red: rings, green: canals), all under the grain. bake_texture bakes it into the colour image."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    new, link, attr = _ops(t)
    co = new("ShaderNodeTexCoord").outputs["Object"]
    sep = new("ShaderNodeSeparateXYZ")
    link(co, sep.inputs[0])
    x, y = sep.outputs[0], sep.outputs[1]
    mk = new("ShaderNodeSeparateColor")
    link(attr("mk"), mk.inputs[0])
    ring = None
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        dx = _math(t, 'SUBTRACT', x, 0.4 * math.cos(a))
        dy = _math(t, 'SUBTRACT', y, 0.4 * math.sin(a))
        r = _math(t, 'SQRT', _math(t, 'ADD', _math(t, 'MULTIPLY', dx, dx), _math(t, 'MULTIPLY', dy, dy)))
        d = _math(t, 'ABSOLUTE', _math(t, 'SUBTRACT', r, 0.2))
        mr = new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.03, 0.055
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
        link(d, mr.inputs["Value"])
        ring = mr.outputs["Result"] if ring is None else _math(t, 'MAXIMUM', ring, mr.outputs["Result"])
    ring = _math(t, 'MULTIPLY', ring, mk.outputs[0])
    rr = _math(t, 'SQRT', _math(t, 'ADD', _math(t, 'MULTIPLY', x, x), _math(t, 'MULTIPLY', y, y)))
    th = _math(t, 'ARCTAN2', y, x)
    fr = _math(t, 'FRACT', _math(t, 'MULTIPLY', th, LOBES / (2 * math.pi)))
    dc = _math(t, 'MULTIPLY', _math(t, 'ABSOLUTE', _math(t, 'SUBTRACT', fr, 0.5)), rr)
    mc = new("ShaderNodeMapRange")
    mc.inputs["From Min"].default_value, mc.inputs["From Max"].default_value = 0.014, 0.034
    mc.inputs["To Min"].default_value, mc.inputs["To Max"].default_value = 1.0, 0.0
    link(dc, mc.inputs["Value"])
    canal = _math(t, 'MULTIPLY', mc.outputs["Result"], mk.outputs[1])
    m1 = new("ShaderNodeMix")
    m1.data_type = 'RGBA'
    link(_math(t, 'MULTIPLY', canal, 0.5), m1.inputs[0])
    link(attr("col"), m1.inputs[6])
    m1.inputs[7].default_value = (*COL["canal"], 1.0)
    m2 = new("ShaderNodeMix")
    m2.data_type = 'RGBA'
    link(_math(t, 'MULTIPLY', ring, 0.8), m2.inputs[0])
    link(m1.outputs[2], m2.inputs[6])
    m2.inputs[7].default_value = (*COL["ring_dk"], 1.0)
    hsv = new("ShaderNodeHueSaturation")
    link(m2.outputs[2], hsv.inputs["Color"])
    link(grain_value(t, GRAIN), hsv.inputs["Value"])
    b = kit.principled(m)
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def build():
    glass_m = grained("Glass", GRAIN, rough=0.6)
    bell_m = bell_glass("BellGlass")
    eye_m = kit.material("Eyes", "#2A2250", rough=0.06)
    glow_m = kit.material("GLOW_Moon", "#C8FFF6", rough=0.3, emit=3.0)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None, rough=0.6):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- the bell: a smooth dome, a frosted scalloped rim, a shallow hollow underneath --------------------------
    outer = resample([(0.0, TOP), (0.34, TOP - 0.03), (0.64, TOP - 0.13), (0.86, TOP - 0.32), (1.0, TOP - 0.58), (1.05, TOP - 0.82),
                      (1.04, TOP - 1.0), (RIM_R, RIM_Z)], 26)
    inner = resample([(RIM_R - 0.06, RIM_Z + 0.02), (0.84, RIM_Z + 0.1), (0.56, RIM_Z + 0.2), (0.0, RIM_Z + 0.25)], 8)
    bell = lathe(outer + inner, segs=72)
    lg = bell.verts.layers.float.get("g")
    for v in bell.verts:
        th = math.atan2(v.co.y, v.co.x)
        w = smooth(v.co.z, RIM_Z + 0.25, RIM_Z) * smooth(math.hypot(v.co.x, v.co.y), 0.7, 0.95)
        lobe = 0.5 - 0.5 * math.cos(LOBES * th)                                 # 0 in a gap, 1 on a lobe
        v.co.z += 0.05 * (1 - lobe) * w
        rr = 1 + 0.02 * lobe * w
        v.co.x *= rr
        v.co.y *= rr
    tree = BVHTree.FromBMesh(bell)

    def hit_at(theta, z):
        d = Vector((math.cos(theta), math.sin(theta), 0))
        o = Vector((0, 0, z)) + d * 3
        loc, nrm, _, _ = tree.ray_cast(o, -d)
        return loc, nrm

    eyes = [hit_at(-math.pi / 2 + 0.2 * s, FACE.z + 0.02) for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        mouth.append([hit_at(-math.pi / 2 + s * a, FACE.z - 0.115 + 2.2 * a * a)[0] for a in (0.0, 0.02, 0.04, 0.06, 0.075)])
    blush = [hit_at(-math.pi / 2 + 0.29 * s, FACE.z - 0.07)[0] for s in (-1, 1)]
    rings = [Vector((0.34 * math.cos(math.pi / 4 + k * math.pi / 2), 0.34 * math.sin(math.pi / 4 + k * math.pi / 2), 0)) for k in range(4)]

    def bell_col(co, n, g):
        rr = math.hypot(co.x, co.y)
        th = math.atan2(co.y, co.x)
        if n.z < -0.25 and co.z < RIM_Z + 0.3 and rr < RIM_R - 0.03:                  # the hollow underneath
            col = mix(COL["teal"], COL["aqua_dk"], smooth(rr, 0.0, 0.9))
            col = mix(col, COL["aqua"], 0.35 * smooth(math.cos(LOBES * th), 0.6, 1.0))
            return col
        col = mix(COL["aqua_dk"], COL["aqua"], smooth(n.z, -0.1, 0.6))               # deeper at the sides, as through thicker glass
        col = mix(col, COL["aqua_lt"], 0.15 * smooth(n.z, 0.75, 1.0))
        col = mix(col, COL["lilac"], 0.25 * smooth(n.z, 0.85, 1.0))                  # a soft lilac heart seen through the top
        col = mix(col, COL["frost"], 0.75 * smooth(co.z, RIM_Z + 0.2, RIM_Z + 0.04))  # frosted rim
        col = mix(col, COL["aqua_dk"], 0.12 * smooth(noise.noise(co * 3.0), 0.0, 0.6))
        if co.y < -0.6:
            for b in blush:
                col = mix(col, COL["blush"], 0.6 * (1 - smooth((co - b).length, 0.04, 0.085)))
        return col
    mk = bell.verts.layers.float_color.new("mk")
    for v in bell.verts:
        top = smooth(v.co.z, TOP - 0.62, TOP - 0.4)
        v[mk] = (top, smooth(v.co.z, RIM_Z + 0.3, RIM_Z + 0.55) * smooth(math.hypot(v.co.x, v.co.y), 0.15, 0.4), 0.0, 1.0)
    add("bell", bell, bell_m, bell_col, lambda co, n, g: 0.55 + 0.08 * smooth(co.z, RIM_Z + 0.2, RIM_Z))

    # ---- small gentle eyes: dark violet, a lavender lower glow, glints high, a soft lid line lifting outwards --------
    EW, EH, ED = 0.062, 0.074, 0.03
    up_w = Vector((0, 0, 1))
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.6 + Vector((0, -1, 0)) * 0.4).normalized()
        xa = -en.cross(up_w).normalized()
        ya = en.cross(xa).normalized()
        frame = Matrix((xa, ya, en)).transposed().to_4x4()
        ctr = e - en * 0.008

        def shape_y(x, y):
            return y * (1 - 0.25 * (x / EW) ** 2) + 0.1 * x * s                     # outer corner lifted
        eye = ell((0, 0, 0), (EW, EH, ED), cuts=4)
        for v in eye.verts:
            v.co.y = shape_y(v.co.x, v.co.y)
        eye.transform(Matrix.Translation(ctr) @ frame)
        add("eyes", eye, eye_m)
        iris = ell((0, 0, 0), (EW * 0.62, EH * 0.36, 0.006), cuts=2)
        iris.transform(Matrix.Translation(ctr + en * (ED - 0.004) - ya * EH * 0.42 + xa * 0.004 * s) @ frame)
        add("iris", iris, glass_m, COL["iris"], 0.3)
        for (dx, dy, r) in ((-0.022, 0.03, 0.017), (0.018, -0.006, 0.008)):
            gl = ell((0, 0, 0), (r, r, 0.005), cuts=1)
            gl.transform(Matrix.Translation(ctr + en * (ED + 0.002) + xa * dx * s + ya * dy) @ frame)
            add("glints", gl, glass_m, COL["glint"], 0.3)
        line = []
        for i in range(9):
            x = -EW * 1.08 + 2.16 * EW * i / 8
            yt = shape_y(x, EH * math.sqrt(max(0.0, 1 - (x / (EW * 1.08)) ** 2)))
            zt = ED * math.sqrt(max(0.0, 1 - (x / EW) ** 2 - 0.6 * (yt / EH) ** 2)) * 0.5
            line.append(ctr + xa * x + ya * (yt + 0.004) + en * (zt + 0.004))
        add("lids", loft(line, lambda t: 0.005 + 0.003 * math.sin(math.pi * t), segs=6, rings=16), glass_m, COL["lash"], 0.6)

    for line in mouth:                                                            # a tiny smile, drawn as a fine line
        add("mouth", loft([p + Vector((0, -1, 0)) * 0.003 for p in line], lambda t: 0.0075 - 0.002 * t, segs=5, rings=8), glass_m, COL["mouth"], 0.6)

    # ---- glowing spots in the rim gaps ---------------------------------------------------------------------------
    for k in range(8):
        th = (4 * k + 1) * math.pi / LOBES                                          # every other gap between lobes
        p = Vector((math.cos(th) * (RIM_R + 0.025), math.sin(th) * (RIM_R + 0.025), RIM_Z + 0.07))
        add("GLOW", ell(p, (0.045, 0.045, 0.045), cuts=2), glow_m)

    # ---- four frilly oral arms --------------------------------------------------------------------------------------
    def arm_col(co, n, g):
        col = mix(COL["aqua_lt"], COL["pink_lt"], smooth(g, 0.0, 0.2))
        return mix(col, COL["pink"], 0.85 * smooth(g, 0.25, 0.9))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2 + 0.15
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        L = 0.85 + 0.12 * _rnd(k)
        path = [Vector((0, 0, RIM_Z + 0.22)) + d * 0.08, Vector((0, 0, RIM_Z - 0.15)) + d * 0.2 + side * 0.04,
                Vector((0, 0, RIM_Z - 0.55)) + d * 0.3 - side * 0.05, Vector((0, 0, RIM_Z - L)) + d * 0.36 + side * 0.06]
        arm = ribbon(path, lambda t: 0.12 * (1 - 0.6 * t) + 0.02, 0.016, twist=1.0, frill=0.04, freq=8.0, segs=10, rings=26)
        add("arms", arm, glass_m, arm_col, 0.7)

    # ---- long, thin, curling pink tentacles ------------------------------------------------------------------------
    def ten_col(co, n, g):
        return mix(COL["pink"], COL["pink_dk"], 0.5 * smooth(g, 0.3, 1.0))
    NT = 10
    for k in range(NT):
        th = 2 * math.pi * (k + 0.3 * _rnd(k, 1)) / NT + 0.2
        d = Vector((math.cos(th), math.sin(th), 0))
        side = Vector((-d.y, d.x, 0))
        drop = 1.55 + 0.4 * _rnd(k, 2)
        if k == 2:
            drop = 2.05
        root = Vector((d.x * (RIM_R - 0.05), d.y * (RIM_R - 0.05), RIM_Z + 0.03))
        pts = [root]
        n_ = 6
        for i in range(1, n_ + 1):
            t = i / n_
            sway = 0.12 * math.sin(t * 5.0 + k * 1.7)
            pts.append(root + Vector((0, 0, -drop * t * 0.85)) + d * (0.12 * math.sin(t * 2.6)) + side * sway)
        end = pts[-1]
        curl = 0.1 + 0.04 * _rnd(k, 3)
        cdir = side if k % 2 else -side
        for i in range(1, 6):                                                     # a curl at the tip
            a = math.pi * 1.6 * i / 5
            pts.append(end + cdir * curl * (1 - math.cos(a)) + Vector((0, 0, -curl * math.sin(a) * 1.2)) * (1 - 0.3 * i / 5))
        ten = loft(pts, lambda t: 0.019 * (1 - t) ** 0.8 + 0.005, segs=5, rings=34)
        add("tentacles", ten, glass_m, ten_col, 0.65)

    lowest = min(v.co.z for k, (bm, _) in c.parts.items() if not k.startswith("GLOW") for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    global FACE, FOCUS
    FACE = FACE - Vector((0, 0, lowest))                                          # the review cameras follow the drop
    FOCUS = FACE * SCALE
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
