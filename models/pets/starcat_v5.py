"""StarCat pet: a fluffy white cat with a small glowing golden star-crystal horn, remade from the game's blocky
white cat with a yellow crest and an upright white tail. Built from scratch by script.

    python models/pets/starcat.py --review out/starcat.png      # render the review sheet
    python models/pets/starcat.py --export models/export/starcat.fbx

Must-haves, checked in every review:
  1. The same pet: a white cat standing on four legs, a yellow-gold crest on its head, its tail held up.
  2. Clearly not the Cat or the DuneCat: long fluffy white fur, a chest ruff and fluffy cheeks, a big
     plume tail; pale gold ear tips and tail tip.
  3. A small golden star-crystal horn on the forehead that glows (GLOW), star-shaped in section.
  4. Big calm eyes (soft blue, relaxed upper lids), a small pink nose, a gentle mouth; never creepy.
  5. Matte long-fur texture with roughness variation; about 3 studs tall; Body under 12k triangles.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 5: the lid edge arched like the top of an open eye and covering only the top fifth (the flat half-lid looked bored); shallower sockets and the eyes less sunk (the sockets cast grey rings); the mouth corners turned up.

Round 4: the lids put on top of the eyes (a flipped axis had laid them along the bottom, as a grey band); rounder tail clumps kept off the tip (they made a spiky crown there).

Round 3: relaxed upper lids lying on the eyes over their top third, lifting towards the outer corners, with a soft lash edge (the round open eyes with grey rings looked startled); smaller pupils; a fluffier tail of longer clumps.

Round 2: calm eyes set into the face with a soft line over the top (heavy lids looked grumpy and the eyes bulged); round cheeks instead of flat cheek flaps; a ruff of round clumps (thin locks made a flat bib); a smaller four-point twisted star horn with no base (it read as a party hat); a fuller tail with a soft gold tip (the spiky tip looked like fingers); sturdier legs with fluffy britches and furry paws; softer pale gold.

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

# ---- the star cat ------------------------------------------------------------------------------------

NAME = "StarCat"
COL = {"white": hexc("#F5F2EC"), "white_dk": hexc("#D5D0CC"), "shadow": hexc("#BDB8B8"), "gold": hexc("#E6C98A"),
       "gold_lt": hexc("#F3E2B6"), "ear_in": hexc("#EDC4B8"), "nose": hexc("#E2949A"), "nose_dk": hexc("#B86A72"),
       "mouth": hexc("#9A7276"), "pupil": hexc("#141828"), "lash": hexc("#5E5660"), "glint": hexc("#FFFFFF"),
       "pad": hexc("#E8B4B0")}
SCALE = 1.45
BAKE = {"shade": 0.42, "rough": 0.9}
GRAIN = [("streak", 60.0, 0.05), ("noise", 7.0, 0.03)]
HEAD = Vector((0, -0.56, 1.36))
HEAD_M = M(HEAD, rot=(4, 0, 0))
FACE = HEAD + Vector((0, -0.3, 0.0))
FOCUS = FACE * SCALE
FACE_DIST = 3.2
LEGS = [(-0.16, -0.4), (0.16, -0.4), (-0.17, 0.48), (0.17, 0.48)]


def star_horn(r_out, r_in, h, points=5, rings=7, twist=35.0):
    """A pointed crystal with a star-shaped section, base at the origin pointing up +Z; g runs 0 base to 1 tip."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    n = points * 2
    loops = []
    for i in range(rings):
        t = i / rings
        s = (1 - t) ** 0.85
        a0 = math.radians(twist * t)
        ring = []
        for j in range(n):
            a = a0 + 2 * math.pi * j / n
            r = (r_out if j % 2 == 0 else r_in) * s
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), h * t))
            v[lg] = t
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    tip = bm.verts.new((0, 0, h))
    tip[lg] = 1.0
    base = bm.verts.new((0, 0, 0))
    base[lg] = 0.0
    for j in range(n):
        bm.faces.new((loops[-1][j], loops[-1][(j + 1) % n], tip))
        bm.faces.new((loops[0][(j + 1) % n], loops[0][j], base))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build():
    fur_m = painted("Fur", dict(strength=0.26, mottle=0.08, fine=52.0, length=8.0), rough=0.9)
    eye_m = kit.material("Eyes", "#6FAFD2", rough=0.06)
    glow_m = kit.material("GLOW_Star", "#FFC53D", rough=0.3, emit=3.0)
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

    def lock(at, d, length, r, droop=0.3, flat=0.6, segs=6, rings=5):
        at, d = Vector(at), Vector(d).normalized()
        end = at + d * length + Vector((0, 0, -length * droop))
        return loft([at - d * 0.02, at + d * length * 0.5, end], lambda t: r * (1 - t) ** 0.8 + 0.004, segs=segs, rings=rings, flat=flat)

    # ---- one fused skin: a soft body, a fluffy chest ruff and cheeks, slim legs with round paws ----------
    clay = [ell((0, 0.06, 0.82), (0.3, 0.56, 0.3)),
            ell((0, -0.34, 0.9), (0.31, 0.28, 0.34)),                            # chest
            ell((0, 0.42, 0.84), (0.29, 0.26, 0.3)),                             # haunches
            ell(hd((0, 0, 0)), (0.35, 0.31, 0.3)),                               # head
            ell(hd((0, -0.24, -0.1)), (0.13, 0.1, 0.08))]                        # muzzle
    for s in (-1, 1):
        clay += [ell(hd((0.12 * s, -0.25, -0.1)), (0.09, 0.08, 0.07))]            # whisker pads
    for (x, y) in LEGS:
        hind = y > 0
        if hind:
            clay.append(ell((x * 1.15, y, 0.64), (0.16, 0.23, 0.27)))
            for k in range(5):                                                    # fluffy britches
                a = math.radians(-40 + 25 * k)
                clay.append(lock((x * 1.4, y + 0.12 * math.sin(a), 0.55 + 0.1 * math.cos(a)), (x * 2, 0.6, -0.8), 0.17, 0.06, droop=0.2, flat=1.0))
        clay += [loft([(x, y, 0.8), (x, y + (0.03 if hind else -0.01), 0.42), (x, y - 0.02, 0.1)], lambda t: lerp(0.115, 0.09, t), segs=12, rings=6),
                 ell((x, y - 0.05, 0.07), (0.1, 0.125, 0.07))]                   # round paws
        for k in range(4):                                                        # fur over the paws
            a = 2 * math.pi * k / 4 + 0.4
            clay.append(lock((x + 0.08 * math.cos(a), y + 0.08 * math.sin(a), 0.2), (math.cos(a) * 0.5, math.sin(a) * 0.5, -1.0), 0.1, 0.045, droop=0.0, flat=1.0))
    for k in range(30):                                                           # the chest ruff: round soft clumps
        a = math.radians(-85 + 170 * ((k * 0.618) % 1.0))
        zz = 0.74 + 0.44 * ((k * 0.381) % 1.0)
        at = Vector((0.25 * math.sin(a), -0.4 - 0.1 * math.cos(a), zz))
        clay.append(lock(at, (math.sin(a) * 0.5, -0.7, -0.7), 0.14, 0.085, droop=0.3, flat=0.95))
    for s in (-1, 1):                                                             # round fluffy cheeks
        clay.append(ell(hd((0.22 * s, -0.08, -0.1)), (0.15, 0.15, 0.14)))
        for k in range(4):
            at = hd((0.28 * s, -0.04 + 0.04 * k, -0.12 - 0.03 * k))
            clay.append(lock(at, R @ Vector((s * 0.7, 0.3, -0.7)), 0.11, 0.06, droop=0.2, flat=0.95))
    for k in range(24):                                                           # long fur on the flanks and belly
        y = -0.25 + 0.65 * ((k * 0.618) % 1.0)
        s = 1 if k % 2 else -1
        ang = math.radians(-60 + 70 * ((k * 0.381) % 1.0))
        at = Vector((0.27 * s * math.cos(ang), y, 0.82 + 0.27 * math.sin(ang)))
        clay.append(lock(at, (s * 0.5, 0.4, -0.8), 0.16, 0.07, droop=0.2))
    skin = fuse(join(clay), voxel=0.017, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.14 * s, -1.5, 0.05)), fwd) for s in (-1, 1)]
    nose_at, nose_n = hit(hd((0, -1.5, -0.06)), fwd)
    mouth = []
    for s in (-1, 1):
        mouth.append([hit(hd((s * x, -1.5, -0.13 + 12.0 * (x - 0.028) ** 2)), fwd)[0] for x in (0.0, 0.014, 0.028, 0.042, 0.056, 0.068)])
    mouth_top = hit(hd((0, -1.5, -0.1)), fwd)[0]

    def carve(co, n):
        d = n * 0.01 * noise.noise(Vector((co.x * 8, co.y * 8, co.z * 3)))
        for e, en in eyes:
            d -= en * 0.024 * (1 - smooth((co - e).length, 0.075, 0.11))
        return d
    up_h = R @ Vector((0, 0, 1))
    lashes = []                                                                   # a soft line over the top of each eye
    for s in (-1, 1):
        e, en = eyes[0 if s < 0 else 1]
        side = en.cross(up_h).normalized()
        lashes.append([e + side * (0.088 * math.cos(a)) + up_h * (0.068 * math.sin(a) + 0.006) + en * 0.0 for a in
                       [math.radians(x) for x in (5, 30, 60, 90, 120, 150, 175)]])
    sculpt(skin, carve)
    skin = decimate(skin, 7600, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.25, 0.0))).length, 0.25, 0.45)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["white_dk"], COL["white"], smooth(n.z, -0.7, 0.1))
        col = mix(col, COL["shadow"], 0.12 * smooth(noise.noise(co * 5.0), 0.1, 0.6))
        q = HINV @ co
        if q.length < 0.6:
            for line in mouth:
                col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, line), 0.005, 0.012))
            col = mix(col, COL["mouth"], 1 - smooth(seg_dist(co, mouth_top, mouth[0][0]), 0.004, 0.01))
            col = mix(col, COL["gold_lt"], 0.35 * (1 - smooth((co - hd((0, -0.18, 0.2))).length, 0.04, 0.14)))
        return col
    add("skin", skin, fur_m, colour, 0.92)

    # ---- big calm eyes: soft blue glass set into the face, a tall pupil and a catchlight -------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.45 + R @ Vector((0.25 * s, -1, 0)).normalized() * 0.55).normalized()
        add("eyes", facing(ell((0, 0, 0), (0.084, 0.07, 0.04), cuts=3), e - en * 0.016, en), eye_m)
        pupil = facing(ell((0, 0, 0), (0.022, 0.04, 0.01), cuts=2), e + en * 0.012, en)
        add("pupils", pupil, fur_m, COL["pupil"], 0.2)
        add("glints", ell(e + en * 0.022 + R @ Vector((-0.024 * s, 0, 0.008)), (0.015, 0.008, 0.015), cuts=1), fur_m, COL["glint"], 0.2)
        # a relaxed upper lid lying on the eye, down over its top third, with a soft dark lash edge
        lid = ell((0, 0, 0), (0.084 * 1.06, 0.07 * 1.08, 0.04 * 1.25), cuts=5)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < 0.036 - 3.2 * v.co.x * v.co.x or v.co.z < -0.01], context='VERTS')
        # local frame: x across, y up, z out of the face
        xa = en.cross(up_h).normalized() * -1
        ya = en.cross(xa).normalized()
        frame = Matrix((xa, ya, en)).transposed().to_4x4()
        lid.transform(Matrix.Translation(e - en * 0.016) @ frame)
        cut_y = lambda co, e=e, ya=ya, xa=xa, s=s: (co - e).dot(ya) - (0.036 - 3.2 * (co - e).dot(xa) ** 2)
        add("lids", lid, fur_m, lambda co, n, g, f=cut_y: mix(COL["white"], COL["lash"], 1 - smooth(f(co), 0.004, 0.014)), 0.85)

    # ---- a small pink nose -------------------------------------------------------------------------------
    nose = ell((0, 0, 0), (0.05, 0.03, 0.035), cuts=2)
    for v in nose.verts:
        v.co.x *= 1 - 0.45 * smooth(-v.co.z, 0.0, 0.035)
    nose.transform(M(nose_at + nose_n * 0.015, rot=(8, 0, 0)))
    add("nose", nose, fur_m, lambda co, n, g: mix(COL["nose_dk"], COL["nose"], smooth(n.z, -0.3, 0.6)), 0.4)

    # ---- pointed ears with pale gold tips and fur tufts inside ---------------------------------------------
    for s in (-1, 1):
        root = hd((0.2 * s, 0.04, 0.2))
        pts = [root, root + R @ Vector((0.05 * s, 0.0, 0.14)), root + R @ Vector((0.08 * s, 0.02, 0.27))]
        ear = loft(pts, lambda t: 0.12 * (1 - t) ** 0.85 + 0.006, segs=10, rings=8, flat=0.42)

        def ear_col(co, n, g):
            inside = smooth(-(R.inverted() @ n).y, 0.3, 0.8) * smooth(g, 0.1, 0.3) * smooth(g, 0.85, 0.6)
            col = mix(COL["white"], COL["ear_in"], 0.8 * inside)
            return mix(col, COL["gold"], smooth(g, 0.55, 0.85))
        add("ears", ear, fur_m, ear_col)
        for k in range(4):
            at = root + R @ Vector((0.0, -0.02, 0.04 + 0.03 * k))
            add("ears", lock(at, R @ Vector((0.15 * s, -0.6, 0.8)), 0.09, 0.018, droop=0.0, segs=5, rings=3), fur_m, COL["white"])

    # ---- the big plume tail held up, with a pale gold tip --------------------------------------------------------
    path = [Vector((0, 0.56, 0.92)), Vector((0, 0.78, 1.08)), Vector((0, 0.86, 1.4)), Vector((0, 0.8, 1.7)), Vector((0, 0.66, 1.86))]
    plume = [loft(path, lambda t: 0.07 + 0.08 * math.sin(math.pi * min(t * 1.1, 1.0)) ** 0.7, segs=12, rings=16)]
    for k in range(36):
        t = 0.1 + 0.62 * k / 35
        p = kit._spline(path, t * (len(path) - 1))
        a = k * 2.4
        d = Vector((math.cos(a), 0.4 * math.sin(a), 0.6 + 0.4 * math.sin(a)))
        plume.append(lock(p, d, 0.15, 0.085, droop=-0.1, flat=1.0))
    plume = fuse(join(plume), voxel=0.016, iterations=1)
    plume = decimate(plume, 1900)
    top = path[-1]

    def tail_col(co, n, g):
        col = mix(COL["white_dk"], COL["white"], smooth(n.z, -0.6, 0.2))
        tip = smooth(co.z, 1.55, 1.8)
        return mix(col, mix(COL["gold"], COL["gold_lt"], smooth(n.z, -0.3, 0.6)), tip)
    add("tail", plume, fur_m, tail_col)

    # ---- the glowing star-crystal horn on the forehead --------------------------------------------------------
    hp, hn = hit(hd((0, -0.05, 1.0)), R @ Vector((0, -0.2, -1.0)))
    horn = star_horn(0.06, 0.026, 0.24, points=4, rings=4, twist=45.0)
    d = (hn * 0.4 + R @ Vector((0, -0.3, 1.0)).normalized() * 0.6).normalized()
    horn.transform(Matrix.Translation(hp - d * 0.02) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    add("GLOW", horn, glow_m)

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
