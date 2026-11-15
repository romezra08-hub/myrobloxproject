"""TreeDeer pet: a forest-spirit deer whose bark-skinned antlers grow into leafy branches, remade from the game's
brown deer with tree antlers, a leafy back with red berries and green spots. Built from scratch by script.

    python models/pets/treedeer.py --review out/treedeer.png      # render the review sheet
    python models/pets/treedeer.py --export models/export/treedeer.fbx

Must-haves, checked in every review:
  1. The same pet: a dark brown deer whose antlers are branches with green leaves, with a leafy back, a few
     red berries and green spots on its legs.
  2. Clearly not the Stag: sturdier, darker, a shorter neck, bark-grained skin, moss on the back, branch
     antlers ending in leaf clusters instead of bone tines.
  3. A leafy mound with moss along the spine, a few glossy red berries tucked in it.
  4. Soft green glowing spots on the legs and flanks (GLOW); a calm face with dark eyes, a pale muzzle and
     moss-lined ears; never creepy.
  5. Matte bark, moss and leaf textures with roughness variation; 3-4.5 studs tall; Body under 12k.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 3: bark worked out in the shader, long plates split by dark grooves running down the body, so the bake keeps them sharp (the vertex-painted grooves blurred into plain brown); more of the single leaves on the back mound.

Round 2: single pointed leaves breaking out of the clumps (they read as smooth green blobs); no moss on the face (it looked like dirt); greener, softer glow spots; lighter berries and spots, to bring the glow part down from 1,080 triangles.

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

# ---- the forest-spirit deer ----------------------------------------------------------------------------

NAME = "TreeDeer"
COL = {"bark": hexc("#5E3F28"), "bark_lt": hexc("#8A6444"), "bark_dk": hexc("#36231A"), "groove": hexc("#2A1A12"),
       "muzzle": hexc("#C9AE88"), "nose": hexc("#1C1412"), "moss": hexc("#5E8A34"), "moss_lt": hexc("#8DB54A"),
       "moss_dk": hexc("#38561E"), "leaf": hexc("#4E9A3A"), "leaf_lt": hexc("#8CCB5A"), "leaf_dk": hexc("#2C6026"),
       "berry": hexc("#C42A2A"), "berry_lt": hexc("#F06450"), "hoof": hexc("#241A16"), "hoof_lt": hexc("#463A34"),
       "white": hexc("#FFFFFF"), "lash": hexc("#1E140E"), "wood": hexc("#6E4A30"), "wood_dk": hexc("#3E281A")}
SCALE = 1.25
BAKE = {"shade": 0.5, "rough": 0.88}
GRAIN = [("streak", 50.0, 0.06), ("noise", 9.0, 0.04)]
HEAD = Vector((0, -0.78, 1.8))
HEAD_M = M(HEAD, rot=(-6, 0, 0))
FACE = HEAD + Vector((0, -0.2, -0.02))
FOCUS = FACE * SCALE
FACE_DIST = 3.8
FRONT = [(-0.18, -0.42), (0.18, -0.42)]
HIND = [(-0.19, 0.56), (0.19, 0.56)]


def leafy(name, rough=0.75):
    """The vertex paint 'col' under leaf-sized cells with darker gaps between them, for the foliage clumps."""
    return grained(name, [("cells", 18.0, 0.14), ("edges", 18.0, -0.22), ("noise", 40.0, 0.05)], rough=rough)


def barky(name, rough=0.92):
    """The vertex paint 'col' under bark: long plates split by dark grooves running down the body, with fine
    grain, worked out in the shader so the bake keeps the grooves sharper than the mesh could."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    new, link, attr = _ops(t)
    co = new("ShaderNodeTexCoord")
    warp = new("ShaderNodeTexNoise")
    warp.inputs["Scale"].default_value, warp.inputs["Detail"].default_value = 3.0, 2.0
    link(co.outputs["Object"], warp.inputs["Vector"])
    mixv = new("ShaderNodeMix")
    mixv.data_type = 'VECTOR'
    mixv.inputs[0].default_value = 0.15
    link(co.outputs["Object"], mixv.inputs[4])
    link(warp.outputs["Color"], mixv.inputs[5])
    mp = new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (11.0, 11.0, 2.2)                          # plates taller than wide
    link(mixv.outputs[1], mp.inputs["Vector"])
    edge = new("ShaderNodeTexVoronoi")
    edge.feature = 'DISTANCE_TO_EDGE'
    link(mp.outputs["Vector"], edge.inputs["Vector"])
    cell = new("ShaderNodeTexVoronoi")
    link(mp.outputs["Vector"], cell.inputs["Vector"])
    rng = new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.0, 0.12
    rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.45, 1.0
    link(edge.outputs["Distance"], rng.inputs["Value"])
    st = new("ShaderNodeMapping")
    st.inputs["Scale"].default_value = (60.0, 60.0, 6.0)
    link(co.outputs["Object"], st.inputs["Vector"])
    fib = new("ShaderNodeTexNoise")
    fib.inputs["Scale"].default_value, fib.inputs["Detail"].default_value = 1.0, 3.0
    link(st.outputs["Vector"], fib.inputs["Vector"])
    v = _math(t, 'MULTIPLY', rng.outputs["Result"], _math(t, 'MULTIPLY_ADD', cell.outputs["Color"], 0.24, 0.88))
    v = _math(t, 'MULTIPLY', v, _math(t, 'MULTIPLY_ADD', fib.outputs[0], 0.3, 0.85))
    return _value_to_paint(m, v, rough)


def build():
    bark_m = barky("Bark")
    leaf_m = leafy("Leaves")
    eye_m = kit.material("Eyes", "#1C120C", rough=0.05)
    glow_m = kit.material("GLOW_Spirit", "#52DC7C", rough=0.4, emit=1.6)
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

    # ---- one fused skin: a sturdy deer with a shorter neck ----------------------------------------------
    clay = [ell((0, 0.08, 1.06), (0.34, 0.62, 0.33)),
            ell((0, -0.34, 1.08), (0.35, 0.32, 0.38)),                           # chest
            ell((0, 0.5, 1.1), (0.33, 0.3, 0.34)),                               # rump
            loft([(0, -0.42, 1.2), (0, -0.6, 1.5), (0, -0.72, 1.72)], lambda t: lerp(0.24, 0.15, t ** 0.7), segs=14, rings=8),
            ell(hd((0, 0, 0)), (0.18, 0.21, 0.17)),                              # skull
            loft([hd((0, -0.06, -0.03)), hd((0, -0.2, -0.06)), hd((0, -0.32, -0.1))], lambda t: lerp(0.13, 0.085, t), segs=14, rings=8),
            loft([(0, 0.78, 1.24), (0, 0.88, 1.28), (0, 0.94, 1.22)], lambda t: lerp(0.08, 0.05, t), segs=10, rings=6)]
    for (x, y) in FRONT:
        clay += [ell((x * 1.12, y + 0.02, 0.96), (0.14, 0.18, 0.26)),
                 loft([(x, y, 0.86), (x, y - 0.01, 0.52), (x, y - 0.03, 0.3), (x, y - 0.02, 0.08)],
                      lambda t: 0.09 - 0.02 * t + 0.014 * math.exp(-((t - 0.38) / 0.07) ** 2), segs=10, rings=12)]
    for (x, y) in HIND:
        clay += [ell((x * 1.15, y, 0.96), (0.15, 0.26, 0.3)),
                 loft([(x, y + 0.02, 0.84), (x, y + 0.13, 0.52), (x, y + 0.09, 0.4), (x, y + 0.02, 0.08)],
                      lambda t: 0.1 - 0.035 * t + 0.012 * math.exp(-((t - 0.4) / 0.07) ** 2), segs=10, rings=12)]
    skin = fuse(join(clay), voxel=0.017, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    up_h = R @ Vector((0, 0, 1))
    fwd = R @ Vector((0, 1, 0))
    eyes = []
    for s in (-1, 1):
        d = (R @ Vector((-0.7 * s, 1, 0.05))).normalized()
        eyes.append(hit(hd((0.12 * s, -0.08, 0.04)) - d * 1.0, d))
    nose_at, _ = hit(hd((0, -1.5, -0.1)), fwd)
    NQ = HINV @ nose_at

    def carve(co, n):
        d = n * 0.014 * noise.noise(Vector((co.x * 10, co.y * 10, co.z * 2.5)))      # bark ridges running down
        for e, en in eyes:
            d -= en * 0.016 * (1 - smooth((co - e).length, 0.045, 0.075))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5800, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.15, -0.03))).length, 0.18, 0.32)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["bark_dk"], COL["bark"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["bark_lt"], 0.35 * smooth(noise.noise(Vector((co.x * 7, co.y * 7, co.z * 1.4))), 0.1, 0.6))
        col = mix(col, COL["groove"], 0.6 * smooth(noise.noise(Vector((co.x * 13, co.y * 13, co.z * 2.2)) + Vector((3, 1, 2))), 0.25, 0.45))
        moss = smooth(n.z, 0.45, 0.8) * smooth(co.z, 1.15, 1.3) * smooth(co.y, -0.55, -0.4) * smooth(co.y, 0.85, 0.7)
        moss = max(moss, 0.6 * smooth(noise.noise(co * 5.0 + Vector((9, 2, 4))), 0.35, 0.55) * smooth(n.z, 0.2, 0.6) * smooth(co.z, 0.9, 1.1))
        moss *= smooth((co - HEAD).length, 0.3, 0.45)                                # none on the face
        col = mix(col, mix(COL["moss_dk"], COL["moss_lt"], smooth(noise.noise(co * 14.0), -0.3, 0.5)), moss)
        q = HINV @ co
        if q.length < 0.45:
            col = mix(col, COL["muzzle"], 0.85 * smooth(q.y, NQ.y + 0.12, NQ.y + 0.06) * smooth(q.z, NQ.z + 0.06, NQ.z - 0.0))
            nz = 1 - smooth(((q - NQ - Vector((0, 0.01, -0.01))) * Vector((1.0, 1.6, 1.3))).length, 0.05, 0.07)
            col = mix(col, COL["nose"], nz)
        return col

    def rough(co, n, g=0.0):
        q = HINV @ co
        return 0.92 - 0.4 * (1 - smooth(((q - NQ - Vector((0, 0.01, -0.01))) * Vector((1.0, 1.6, 1.3))).length, 0.05, 0.075))
    add("skin", skin, bark_m, colour, rough)

    # ---- calm dark eyes under soft lids -------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.048, 0.04, 0.03), cuts=3), e - en * 0.004, en), eye_m)
        add("glints", ell(e + en * 0.022 + R @ Vector((-0.006, -0.012, -0.002)), (0.009, 0.009, 0.009), cuts=1), bark_m, COL["white"], 0.3)
        lid = facing(ell((0, 0, 0), (0.054, 0.046, 0.038), cuts=4), e - en * 0.003, en)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if (v.co - e).dot(up_h) < 0.014], context='VERTS')
        add("lids", lid, bark_m, lambda co, n, g, e=e: mix(COL["bark"], COL["lash"], 1 - smooth((co - e).dot(up_h), 0.016, 0.024)))

    # ---- leaf ears, lined with moss -------------------------------------------------------------------------
    for s in (-1, 1):
        ear = ell((0, 0, 0), (0.06, 0.035, 0.15), cuts=3)
        for v in ear.verts:
            v.co.x *= 1 - 0.7 * smooth(v.co.z, 0.02, 0.15)
            if v.co.y < 0:
                v.co.y *= 0.25
        paint(ear, lambda co, n, g: mix(COL["bark"], COL["moss"], 0.8 * smooth(-n.y, 0.3, 0.7) * smooth(abs(co.x), 0.05, 0.02)))
        ear.transform(M(hd((0.16 * s, 0.08, 0.1)), rot=(-20, 0, -62 * s)))
        add("ears", ear, bark_m)

    # ---- branch antlers ending in leaf clusters ---------------------------------------------------------------
    tips = []

    def branch(pts, r0, r1):
        b = loft(pts, lambda t: lerp(r0, r1, t) + 0.004, segs=7, rings=max(5, 3 * (len(pts) - 1)))
        add("antlers", b, bark_m, lambda co, n, g: mix(COL["wood_dk"], COL["wood"], 0.6 * smooth(n.z, -0.3, 0.7) * smooth(noise.noise(co * 25.0), -0.2, 0.4)))
        tips.append(pts[-1])
    for s in (-1, 1):
        root = hd((0.08 * s, 0.04, 0.13))
        P = [root + R @ Vector(v) for v in ((0, 0, -0.03), (0.07 * s, 0.04, 0.16), (0.18 * s, 0.1, 0.34), (0.3 * s, 0.06, 0.52), (0.38 * s, 0.0, 0.7))]
        branch(P, 0.05, 0.018)
        for t, dirn, L in ((0.3, (0.15 * s, -1.0, 0.6), 0.26), (0.55, (0.5 * s, 0.4, 0.8), 0.24), (0.78, (-0.1 * s, -0.5, 1.0), 0.22)):
            p = kit._spline(P, t * (len(P) - 1))
            d = (R @ Vector(dirn)).normalized()
            mid = p + d * L * 0.5 + up_h * L * 0.12 + (R @ Vector((0.05 * s, 0, 0)))
            branch([p - d * 0.01, mid, p + d * L + up_h * L * 0.1], 0.028, 0.012)

    # ---- the leafy mound on the back and leaf clusters at the branch tips -------------------------------------
    blobs = []
    for k, (y, x, r) in enumerate(((-0.28, 0.0, 0.2), (-0.05, 0.08, 0.22), (0.18, -0.06, 0.21), (0.4, 0.04, 0.19), (0.0, -0.17, 0.15),
                                   (0.25, 0.17, 0.15), (-0.18, 0.17, 0.14), (0.52, -0.12, 0.13))):
        p, nn = hit(Vector((x, y, 2.5)), (0, 0, -1))
        if p is None:
            continue
        ctr = p + Vector((0, 0, r * 0.45))
        blobs.append(ell(ctr, (r, r * 1.05, r * 0.8)))
        for j in range(4):                                                         # lumpy leaf clumps round each
            a = 2 * math.pi * j / 4 + k
            blobs.append(ell(ctr + Vector((math.cos(a) * r * 0.75, math.sin(a) * r * 0.75, r * 0.15)), (r * 0.5,) * 3))
    for t in tips:
        blobs.append(ell(t, (0.12, 0.12, 0.1)))
        for j in range(3):
            a = 2 * math.pi * j / 3
            blobs.append(ell(t + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.03)), (0.07,) * 3))
    foliage = fuse(join(blobs), voxel=0.022, iterations=1)
    sculpt(foliage, lambda co, n: n * 0.025 * noise.noise(co * 9.0))
    foliage = decimate(foliage, 2000)
    ftree = BVHTree.FromBMesh(foliage)

    def leaf_col(co, n, g):
        col = mix(COL["leaf_dk"], COL["leaf"], smooth(n.z, -0.5, 0.4))
        return mix(col, COL["leaf_lt"], 0.45 * smooth(noise.noise(co * 6.0), 0.0, 0.6) * smooth(n.z, 0.0, 0.8))
    add("leaves", foliage, leaf_m, leaf_col, 0.75)

    # ---- single pointed leaves breaking out of the clumps, so they read as leaves and not as green blobs ---------
    import random
    rnd = random.Random(3)
    back = [Vector((x, y, 1.5)) for (y, x) in ((-0.28, 0.0), (-0.05, 0.08), (0.18, -0.06), (0.4, 0.04), (0.25, 0.17), (-0.18, 0.17))]
    centres = [t for t in tips for _ in range(1)] + back + back
    n_leaf = 0
    for k in range(60):
        if n_leaf >= 34:
            break
        cen = centres[k % len(centres)]
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 1))).normalized()
        loc, nn, _, _ = ftree.ray_cast(cen + d * 0.6, -d)
        if loc is None:
            continue
        leaf = ell((0, 0, 0), (0.04, 0.012, 0.085), cuts=1)
        for v in leaf.verts:
            v.co.x *= 1 - 0.8 * smooth(v.co.z, 0.0, 0.085) - 0.3 * smooth(-v.co.z, 0.03, 0.085)
            v.co.z += 0.085
        out = (nn * 0.7 + d * 0.3 + Vector((0, 0, 0.3))).normalized()
        q = out.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        leaf.transform(Matrix.Translation(loc - out * 0.03) @ q @ M(rot=(rnd.uniform(-30, 30), 0, rnd.uniform(0, 180))))
        tone = rnd.random()
        add("leaflets", leaf, leaf_m, lambda co, n, g, tone=tone: mix(COL["leaf"], COL["leaf_lt"], 0.3 + 0.6 * tone), 0.7)
        n_leaf += 1

    # ---- glossy red berries tucked into the leaves ---------------------------------------------------------------
    for k in range(9):
        a = k * 2.4
        o = Vector((0.4 * math.cos(a), -0.3 + 0.85 * ((k * 0.618) % 1.0), 2.4))
        loc, nn, _, _ = ftree.ray_cast(o, Vector((-0.25 * math.cos(a), 0, -1)).normalized())
        if loc is None:
            continue
        for j in range(2 if k % 3 == 0 else 1):
            b = ell(loc + nn * 0.03 + Vector((0.045 * j, 0.02 * j, 0)), (0.045,) * 3, cuts=1)
            add("berries", b, leaf_m, lambda co, n, g: mix(COL["berry"], COL["berry_lt"], 0.5 * smooth(n.z, 0.5, 1.0)), 0.35)

    # ---- soft glowing spirit spots on the legs and flanks --------------------------------------------------------
    spots = []
    for (x, y) in FRONT + HIND:
        for z in (0.32, 0.58):
            s = 1 if x > 0 else -1
            spots.append(hit(Vector((x + s * 1.0, y - 0.02, z)), (-s, 0, 0)))
    for s in (-1, 1):
        for (y, z) in ((0.45, 1.05), (0.6, 1.18), (-0.3, 1.0)):
            spots.append(hit(Vector((s * 1.0, y, z)), (-s, 0, 0)))
    for k, (p, nn) in enumerate(spots):
        if p is None:
            continue
        r = 0.04 + 0.012 * _rnd(k)
        d = facing(ell((0, 0, 0), (r, r, 0.012), cuts=1), p + nn * 0.004, nn)
        add("GLOW", d, glow_m)

    # ---- dark hooves --------------------------------------------------------------------------------------------
    for (x, y) in FRONT + HIND:
        yy = y - 0.03 if y < 0 else y + 0.01
        hoof = lathe([(0.0, 0.0), (0.072, 0.0), (0.074, 0.028), (0.066, 0.08), (0.06, 0.11), (0.0, 0.11)], segs=12)
        for v in hoof.verts:
            if v.co.y < 0:
                v.co.y *= 1.25
                v.co.y += 0.02 * (1 - smooth(abs(v.co.x), 0.0, 0.015)) * smooth(-v.co.y, 0.045, 0.08)
        hoof.transform(M((x, yy, 0)))
        add("hooves", hoof, bark_m, lambda co, n, g: mix(COL["hoof"], COL["hoof_lt"], 0.4 * smooth(n.z, -0.2, 0.6)), 0.5)

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
