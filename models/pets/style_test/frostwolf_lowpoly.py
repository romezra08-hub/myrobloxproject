"""FrostWolf style test B: a stylised low-poly frost wolf. One of three versions of the same pet built to let the owner
pick a style (the remakes were called "cursed": human-like eyes, thin tube legs, long necks, lumpy bodies). Built
from scratch by script.

    python models/pets/style_test/frostwolf_lowpoly.py --review out/b.png
    python models/pets/style_test/frostwolf_lowpoly.py --export models/export/style_test/frostwolf_b.fbx

Must-haves, checked in every review:
  1. The same pet: a midnight-blue wolf with a pale ruff and chest, ice crystals on its back and a pale tail tip.
  2. Deliberately faceted: flat-shaded planes you can count, about 1.5-3k triangles; the look comes from the facets.
  3. Flat colour per facet with a slight per-face variation, no realistic texture.
  4. Sturdy: the head about 30% of the height, legs of medium length but thick, tapering into simple paw blocks.
  5. Eyes and nose as small dark faceted gems (no whites, no lids); faceted crystals that glow (GLOW).
  6. About 2.6-2.8 studs tall.

Final: round 2.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 2: thicker, shorter legs on bigger paw blocks with the body lower (the legs read long and thin); a bigger,
cleaner pale chest (dark facets broke into it); slightly bigger eye gems; scaled to about 2.7 studs.

Round 1: first build.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
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


def crusted(name, rough=0.9, size=0.17, joins=0.42, vary=0.2):
    """The vertex paint 'col' under kit.scaly's cells: scales, plates or a cracked crust, by size and joins."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=size, joins=joins, vary=vary, rough=rough)
    t = m.node_tree
    hsv = next(n for n in t.nodes if n.type == 'HUE_SAT')
    a = t.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "col"
    t.links.new(a.outputs["Color"], hsv.inputs["Color"])
    return m


def fan(root, rim, sags, rows=8, sub=4, th=0.01):
    """A thin two-sided skin fanned from `root` to the points of `rim` (a bat wing's membrane from the wrist to
    the finger tips and back to the body). Each rim edge k bows in towards the root by sags[k] at its middle, so
    the trailing edge is scalloped. 'g' runs 0 at the root to 1 at the rim; 'u' (in the layer 'u') runs along
    the rim, a whole number exactly on each spar."""
    root = Vector(root)
    rim = [Vector(p) for p in rim]
    nrm = Vector()
    for a, b in zip(rim, rim[1:]):
        nrm += (a - root).cross(b - root)
    nrm.normalize()
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    lu = bm.verts.layers.float.new("u")
    cols = []
    for k in range(len(rim) - 1):
        for j in range(sub if k < len(rim) - 2 else sub + 1):
            cols.append((k, j / sub))
    grid_f, grid_b = [], []
    for k, u in cols:
        a, b = rim[k], rim[min(k + 1, len(rim) - 1)]
        tip = a.lerp(b, u)
        tip = root + (tip - root) * (1 - sags[k] * math.sin(math.pi * u))
        f, bk = [], []
        for i in range(rows + 1):
            t = i / rows
            q = root.lerp(tip, t)
            for side, lst in ((1, f), (-1, bk)):
                v = bm.verts.new(q + nrm * th * side * (1 - 0.6 * t))
                v[lg], v[lu] = t, k + u
                lst.append(v)
        grid_f.append(f)
        grid_b.append(bk)
    for G, flip in ((grid_f, False), (grid_b, True)):
        for a, b in zip(G, G[1:]):
            for i in range(rows):
                q = (a[i], b[i], b[i + 1], a[i + 1])
                bm.faces.new(q[::-1] if flip else q)
    for k in range(len(grid_f) - 1):
        bm.faces.new((grid_f[k][-1], grid_f[k + 1][-1], grid_b[k + 1][-1], grid_b[k][-1]))
    for G in (0, -1):
        for i in range(rows):
            bm.faces.new((grid_f[G][i], grid_f[G][i + 1], grid_b[G][i + 1], grid_b[G][i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

# ---- the low-poly frost wolf ---------------------------------------------------------------------------

NAME = "FrostWolf"
TEXTURE = "frostwolf_b"
COL = {"navy": hexc("#253867"), "navy_lt": hexc("#3B5594"), "navy_dk": hexc("#18254A"), "white": hexc("#E9F0FA"),
       "white_sh": hexc("#C3D1E8"), "paw": hexc("#8FA6D2"), "ear_in": hexc("#9FB4DA")}
SCALE = 1.14
BAKE = {"shade": 0.28, "rough": 0.85}
GRAIN = []
HEAD = Vector((0, -0.8, 1.72))
FACE = HEAD + Vector((0, -0.3, -0.06))
FOCUS = FACE * SCALE
FACE_DIST = 3.8
LEGS = [(-0.25, -0.4), (0.25, -0.4), (-0.26, 0.48), (0.26, 0.48)]
TAIL = [Vector((0, 0.76, 1.12)), Vector((0, 1.0, 1.24)), Vector((0, 1.14, 1.5)), Vector((0, 1.08, 1.74))]


def build():
    flat_m = kit.material("Facets", "#808080", rough=0.85)
    _value_to_paint(flat_m, grain_value(flat_m.node_tree, []), 0.85)
    eye_m = kit.material("Eyes", "#10162C", rough=0.08)
    glow = kit.material("GLOW_Ice", "#8EE2FF", rough=0.3, emit=2.2)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, rough=0.85):
        roughen(bm, lambda co, n, g, r=rough: r)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- one sturdy shape, then cut down to a few big facets -----------------------------------------------------
    clay = [ell((0, 0.08, 0.98), (0.44, 0.68, 0.4)),
            ell((0, -0.36, 1.04), (0.47, 0.42, 0.45)),                             # deep chest
            ell((0, -0.6, 1.2), (0.42, 0.3, 0.36)),                               # the ruff
            ell(HEAD, (0.36, 0.36, 0.34)),                                         # head, about 30% of the height
            loft([HEAD + Vector((0, -0.18, -0.08)), HEAD + Vector((0, -0.36, -0.14)), HEAD + Vector((0, -0.5, -0.17))], lambda t: lerp(0.17, 0.1, t), segs=10, rings=6),
            loft(TAIL, lambda t: 0.12 + 0.07 * math.sin(math.pi * t), segs=10, rings=10)]
    for s in (-1, 1):
        clay.append(loft([HEAD + Vector((0.18 * s, 0.06, 0.2)), HEAD + Vector((0.22 * s, 0.07, 0.42)), HEAD + Vector((0.24 * s, 0.08, 0.6))],
                         lambda t: 0.12 * (1 - t) + 0.01, segs=8, rings=6, flat=0.55))       # pointed ears
        clay.append(ell(HEAD + Vector((0.2 * s, -0.06, -0.1)), (0.16, 0.16, 0.15)))         # cheeks
    for (x, y) in LEGS:
        clay += [loft([(x, y, 0.9), (x, y - 0.01, 0.5), (x, y - 0.02, 0.16)], lambda t: lerp(0.21, 0.16, t), segs=10, rings=6),
                 kit.rounded_box((0.33, 0.4, 0.17), n=3.0, cuts=2)]
        clay[-1].transform(M((x, y - 0.05, 0.08)))                                          # simple paw blocks
    skin = fuse(join(clay), voxel=0.03, iterations=3)
    skin = decimate(skin, 1700)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm

    # ---- flat colour per facet, a slight shift face to face -----------------------------------------------------------
    def face_col(co, n, i):
        col = mix(COL["navy_dk"], COL["navy"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["navy_lt"], 0.5 * smooth(n.z, 0.55, 1.0))
        q = co - HEAD
        if q.length < 0.7:
            col = mix(col, COL["white"], smooth(-q.z, 0.0, 0.06) * smooth(-q.y, 0.05, 0.15))      # pale under the muzzle and cheeks
            col = mix(col, COL["white"], smooth(abs(q.x), 0.24, 0.3) * smooth(-q.z, -0.02, 0.06))
        bib = ((co - Vector((0, -0.7, 1.1))) * Vector((1 / 0.4, 1 / 0.36, 1 / 0.5))).length
        col = mix(col, mix(COL["white_sh"], COL["white"], smooth(n.z, -0.6, 0.2)), 1 - smooth(bib, 0.85, 1.0))      # ruff and chest
        col = mix(col, COL["paw"], 1.0 if co.z < 0.2 else 0.0)                             # paws
        if co.y > 0.8 and (co - TAIL[-1]).length < 0.36:
            col = mix(col, COL["white"], 1 - smooth((co - TAIL[-1]).length, 0.24, 0.3))     # tail tip
        for s in (-1, 1):
            e = HEAD + Vector((0.22 * s, 0.03, 0.4))
            if (co - e).length < 0.18 and n.y < -0.3:
                col = mix(col, COL["ear_in"], 0.8)
        k = 1 + 0.07 * (_rnd(i, 3.1) - 0.5) * 2                                           # each facet a little different
        return tuple(min(1.0, x * k) for x in col)
    lay = skin.loops.layers.float_color.new("col")
    for i, f in enumerate(skin.faces):
        col = (*face_col(f.calc_center_median(), f.normal, i), 1.0)
        for l in f.loops:
            l[lay] = col
    add("skin", skin, flat_m)

    # ---- small dark faceted gems for eyes and nose -----------------------------------------------------------------------
    for s in (-1, 1):
        e, en = hit(HEAD + Vector((0.15 * s, -2.0, 0.06)), (0, 1, 0))
        gem = kit.ball((0.12, 0.07, 0.14), cuts=1)
        gem.transform(Matrix.Translation(e - en * 0.008) @ (en * 0.5 + Vector((0, -1, 0)) * 0.5).normalized().to_track_quat('Y', 'Z').to_matrix().to_4x4()
                      @ Matrix.Rotation(math.radians(180), 4, 'Z'))
        add("eyes", gem, eye_m)
    nose_at, nn = hit(HEAD + Vector((0, -2.0, -0.12)), (0, 1, 0))
    nose = kit.ball((0.11, 0.08, 0.08), cuts=1)
    nose.transform(M(nose_at + nn * 0.01))
    add("eyes", nose, eye_m)

    # ---- faceted ice crystals on the back -------------------------------------------------------------------------------
    for k, (y, h, r, lean) in enumerate(((-0.28, 0.34, 0.1, 0), (0.0, 0.46, 0.12, 5), (0.28, 0.4, 0.11, -5), (0.52, 0.28, 0.09, 4))):
        top, _ = hit((0, y, 3.0), (0, 0, -1))
        cr = crystal(r, h, sides=5)
        cr.transform(M(top - Vector((0, 0, 0.05)), rot=(-16, lean, k * 37)))
        add("GLOW", cr, glow)

    lowest = min(v.co.z for k, (bm, _) in c.parts.items() if not k.startswith("GLOW") for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    for ob in c.objects:                                                                       # flat shading: the facets are the look
        ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
        ob.data.update()
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
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "..", "export", "style_test", TEXTURE + "_colour.png"))
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
