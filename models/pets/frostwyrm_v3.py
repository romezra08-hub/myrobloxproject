"""FrostWyrm pet: a long eastern-style ice wyrm coiled in the air, remade from the game's ice-blue serpent dragon
with long thin wings and whiskers. Built from scratch by script.

    python models/pets/frostwyrm.py --review out/frostwyrm.png      # render the review sheet
    python models/pets/frostwyrm.py --export models/export/frostwyrm.fbx

Must-haves, checked in every review:
  1. The same pet: a long ice-blue serpent dragon with thin swept wings and long whiskers.
  2. An eastern wyrm: one long body coiling in an S, the head held high, no legs; a coil resting on the ground.
  3. Pale-to-deep blue scales with a pale banded belly; crystalline ice fins down the back that glow (GLOW).
  4. A calm, regal face: a long rounded snout, gold almond eyes under a level lid (outer corners up), swept-back
     antler horns, a flat swept-back mane at the cheeks and flowing whiskers.
  5. Unlike EmberSerpent (a red coiled snake) and the winged dragons: slender, airy and blue. Matte scales with
     varied roughness; lowest point at z=0; within about 6 studs long; Body under 12k triangles.

Final: round 3.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 3: the wings spread to the two sides of the body (laid along the coil, one hid behind the neck from the
front); the eyes set a little higher and facing more forwards, with a fainter dark rim (they glanced sideways and
looked unimpressed).

Round 2: whiskers flowing back along the head and trailing (stiff and sideways they read as a handlebar
moustache); lighter lids over bigger eyes (the heavy lids looked bored); no nose pad (it looked like a clown nose);
taller, thinner swept ice shards in a deeper cyan (the short white crystals read as teeth); bigger wings raised
higher so both read from the front; finer scales; fewer body faces.

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

# ---- the frost wyrm -------------------------------------------------------------------------------

NAME = "FrostWyrm"
COL = {"deep": hexc("#2A5EA6"), "mid": hexc("#4E8FD0"), "light": hexc("#8EC6EC"), "belly": hexc("#E2F3FB"),
       "belly_dk": hexc("#B4D8EE"), "horn": hexc("#EEF8FF"), "horn_dk": hexc("#8FBFE2"), "mane": hexc("#F2FAFF"),
       "mane_dk": hexc("#9FCFEF"), "whisker": hexc("#DDF2FF"), "line": hexc("#16304E"), "pupil": hexc("#1A1206"),
       "white": hexc("#FFFFFF"), "mem": hexc("#9ED2F2"), "mem_lt": hexc("#E2F4FF"), "spar": hexc("#F2FAFF")}
SCALE = 1.0
BAKE = {"shade": 0.4, "rough": 0.82}
GRAIN = [("cells", 30.0, 0.04), ("noise", 6.0, 0.03)]
HEAD = Vector((0, -1.42, 2.42))
HEAD_M = M(HEAD, rot=(8, 0, 0))
SPINE = [HEAD_M @ Vector((0, 0.2, -0.04)), Vector((0, -1.12, 2.12)), Vector((0.12, -0.86, 1.78)), Vector((0.5, -0.5, 1.44)),
         Vector((0.72, 0.02, 1.08)), Vector((0.38, 0.52, 0.76)), Vector((-0.34, 0.62, 0.56)), Vector((-0.76, 0.18, 0.4)),
         Vector((-0.56, -0.36, 0.26)), Vector((0.12, -0.42, 0.2)), Vector((0.72, -0.02, 0.18)), Vector((0.92, 0.66, 0.16)),
         Vector((0.66, 1.26, 0.22)), Vector((0.2, 1.5, 0.32))]
FACE = HEAD + Vector((0, -0.28, -0.02))
FOCUS = FACE * SCALE
FACE_DIST = 3.2


def body_r(t):
    return 0.17 + 0.07 * math.sin(math.pi * min(t / 0.55, 1.0)) * (1 - smooth(t, 0.4, 1.0)) - 0.14 * smooth(t, 0.35, 1.0) + 0.012


def path_at(t):
    return kit._spline(SPINE, t * (len(SPINE) - 1))


def frame_at(t):
    """Tangent (towards the tail), dorsal (world up made square to it) and side at t along the body."""
    a, b = path_at(max(t - 0.01, 0.0)), path_at(min(t + 0.01, 1.0))
    T = (b - a).normalized()
    up = Vector((0, 0, 1))
    D = (up - T * T.dot(up))
    D = D.normalized() if D.length > 1e-3 else Vector((0, -1, 0))
    return T, D, T.cross(D).normalized()


def build():
    scale_m = crusted("Scales", rough=0.82, size=0.04, joins=0.22, vary=0.12)
    soft_m = painted("Soft", dict(strength=0.12, mottle=0.08, fine=30.0, length=4.0), rough=0.85)
    eye_m = kit.material("Eyes", "#E8B23A", rough=0.06)
    glow = kit.material("GLOW_Ice", "#6CD6FF", rough=0.3, emit=1.7)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.82):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def snout():
        bm = kit.rounded_box((0.24, 0.56, 0.16), n=2.8, cuts=6)
        for v in bm.verts:
            t = smooth(-v.co.y, -0.28, 0.28)
            v.co.x *= 1 - 0.3 * t
            if v.co.z > 0:
                v.co.z *= 1 - 0.3 * t
        bm.transform(HEAD_M @ M((0, -0.3, -0.02)))
        return bm

    # ---- one fused skin: the long coiling body and a long, rounded eastern head ------------------------------------
    clay = [loft(SPINE, body_r, segs=14, rings=110),
            ell(hd((0, 0.04, 0.04)), (0.19, 0.24, 0.17)),                        # skull
            snout(),
            ell(hd((0, -0.24, -0.11)), (0.11, 0.26, 0.05))]                      # lower jaw
    for s in (-1, 1):
        clay.append(ell(hd((0.13 * s, 0.02, -0.05)), (0.08, 0.13, 0.08)))         # cheeks
    skin = fuse(join(clay), voxel=0.018, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = []
    for s in (-1, 1):
        tgt = hd((0.115 * s, -0.09, 0.075))
        o = tgt + R @ Vector((0.9 * s, -0.8, 0.12))
        eyes.append(hit(o, tgt - o))
    nostrils = [hit(hd((0.05 * s, -1.5, 0.02)), fwd) for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        pts = []
        for k in range(6):
            y = -0.52 + 0.09 * k
            z = -0.08 + 0.025 * smooth(k, 2.5, 5)
            p = hit(hd((0.6 * s, y, z)), R @ Vector((-s, 0, 0)))[0]
            if p is not None:
                pts.append(p)
        mouth.append(pts)
    samples = [path_at(i / 200) for i in range(201)]

    def along(co):
        i = min(range(201), key=lambda k: (samples[k] - co).length_squared)
        return i / 200

    def carve(co, n):
        d = n * 0.004 * noise.noise(co * 6.0)
        for e, en in eyes:
            d -= en * 0.016 * (1 - smooth((co - e).length, 0.045, 0.08))
        for e, en in nostrils:
            if e is not None:
                d -= en * 0.012 * (1 - smooth((co - e).length, 0.01, 0.026))
        if (co - HEAD).length < 0.6:
            md = min(poly_dist(co, m) for m in mouth if len(m) > 1)
            d -= n * 0.01 * (1 - smooth(md, 0.004, 0.012))
        elif n.z < -0.3:
            t = along(co)
            d -= n * 0.008 * smooth(0.5 + 0.5 * math.cos(t * 2 * math.pi * 46), 0.8, 1.0)      # belly scute grooves
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6600, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.2, 0.0))).length, 0.2, 0.42)), factor=1.0)

    def scale_colour(co, n, g=0.0):
        col = mix(COL["mid"], COL["deep"], smooth(n.z, 0.1, 0.85))                  # deep blue along the top
        col = mix(col, COL["light"], 0.6 * smooth(n.z, 0.0, -0.4))
        col = mix(col, COL["light"], 0.25 * smooth(noise.noise(co * 3.0), 0.0, 0.6))
        col = mix(col, mix(COL["belly_dk"], COL["belly"], smooth(-n.z, 0.5, 0.9)), smooth(-n.z, 0.3, 0.6))     # a pale belly
        if (co - HEAD).length < 0.62:
            q = HEAD_M.inverted() @ co
            col = mix(col, COL["light"], 0.5 * smooth(q.y, -0.2, -0.45))
            col = mix(col, COL["belly"], 0.6 * smooth(-n.z, 0.0, 0.5))
            for e, en in eyes:
                col = mix(col, COL["line"], 0.45 * (1 - smooth((co - e).length, 0.058, 0.072)))
            for e, en in nostrils:
                if e is not None:
                    col = mix(col, COL["line"], 0.7 * (1 - smooth((co - e).length, 0.01, 0.022)))
        return col
    add("skin", skin, scale_m, scale_colour, lambda co, n, g: 0.8 - 0.1 * smooth(-n.z, 0.3, 0.7))

    # ---- calm gold almond eyes, outer corners up, under a level lid ------------------------------------------------
    EW, EH, ED = 0.1, 0.064, 0.033
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.3 + R @ Vector((0, -1, 0)) * 0.7).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(12 * s), 4, Vector((0, -1, 0)))
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.01) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=4)
        for v in eb.verts:
            v.co.y *= 1 - 0.4 * (v.co.x / (EW / 2)) ** 2
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.01 + en * (ED - 0.005)
        pupil = kit.ball((0.026, 0.048, 0.012), cuts=2)
        pupil.transform(Matrix.Translation(front + up * 0.003) @ tilt @ basis)
        add("pupils", pupil, scale_m, COL["pupil"], 0.3)
        add("pupils", ell(front + en * 0.005 + up * 0.016 + ex * 0.013 * s, (0.01, 0.01, 0.005), cuts=2), scale_m, COL["white"], 0.3)
        lid = kit.ball((EW * 1.12, EH * 1.16, ED * 2.3), cuts=10)
        for v in lid.verts:
            v.co.y *= 1 - 0.4 * (v.co.x / (EW * 0.56)) ** 2
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.27 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, scale_m, COL["mid"])
    for m in mouth:
        if len(m) > 1:
            add("mouth", loft([p + (p - HEAD).normalized() * 0.002 for p in m], lambda t: 0.005 + 0.002 * t, segs=5, rings=3 * len(m)), scale_m, COL["line"])

    # ---- swept-back antler horns, a flat swept mane at the cheeks, flowing whiskers --------------------------------------
    def horn_col(co, n, g):
        return mix(COL["horn_dk"], COL["horn"], smooth(g, 0.0, 0.7))
    for s in (-1, 1):
        root = hd((0.09 * s, 0.12, 0.13))
        pts = [root, root + R @ Vector((0.04 * s, 0.16, 0.1)), root + R @ Vector((0.08 * s, 0.38, 0.16)), root + R @ Vector((0.1 * s, 0.6, 0.3))]
        add("horns", loft(pts, lambda t: 0.042 * (1 - t) ** 0.8 + 0.006, segs=8, rings=12), soft_m, horn_col, 0.6)
        b = pts[1].lerp(pts[2], 0.5)
        add("horns", loft([b, b + R @ Vector((0.04 * s, 0.02, 0.12)), b + R @ Vector((0.05 * s, 0.08, 0.2))], lambda t: 0.02 * (1 - t) + 0.004, segs=6, rings=6), soft_m, horn_col, 0.6)

        def mane_col(co, n, g):
            return mix(COL["mane"], COL["mane_dk"], smooth(g, 0.3, 1.0))
        for k in range(4):                                                         # flat swept-back cheek mane
            at = hd((0.15 * s, 0.0 + 0.07 * k, -0.04 + 0.05 * k))
            d = R @ Vector((0.35 * s, 1.0, 0.15 + 0.1 * k)).normalized()
            bl = blade(0.3 - 0.03 * k, 0.05, th=0.012, cuts=2, curve=0.06)
            frame_to(bl, at, d, R @ Vector((s, 0, 0.4)))
            add("mane", bl, soft_m, mane_col, 0.85)

        def wh_col(co, n, g):
            return mix(COL["whisker"], COL["mid"], 0.6 * smooth(g, 0.5, 1.0))
        root = hd((0.08 * s, -0.48, 0.0))
        pts = [root, root + R @ Vector((0.08 * s, 0.04, -0.02)), root + R @ Vector((0.17 * s, 0.25, -0.1)), root + R @ Vector((0.24 * s, 0.55, -0.24)),
               root + R @ Vector((0.27 * s, 0.85, -0.3)), root + R @ Vector((0.3 * s, 1.12, -0.24)), root + R @ Vector((0.33 * s, 1.32, -0.3))]
        add("whiskers", loft(pts, lambda t: 0.011 * (1 - t) + 0.003, segs=6, rings=30), soft_m, wh_col, 0.8)      # flowing back, not a moustache

    # ---- crystalline ice fins down the back, glowing ---------------------------------------------------------------------
    n_f = 22
    for k in range(n_f):
        t = 0.04 + 0.9 * k / (n_f - 1)
        T, D, S = frame_at(t)
        p = path_at(t)
        h = (0.24 if t < 0.5 else 0.24 - 0.18 * smooth(t, 0.5, 0.95)) * (0.7 + 0.3 * smooth(t, 0.0, 0.12))
        top, nrm = hit(p + D * 1.0, -D)
        if top is None:
            continue
        cr = crystal(0.06, h * 1.35, sides=4)
        for v in cr.verts:
            v.co.x *= 0.3
            v.co.y *= 1 + 0.4 * smooth(v.co.z, 0.0, h * 0.3) * (1 - smooth(v.co.z, h * 0.6, h * 1.35))   # a swept shard, not a block
        z = (D * 0.85 + T * 0.55).normalized()
        y = (T - z * z.dot(T)).normalized()
        cr.transform(Matrix.Translation(top - D * 0.03) @ Matrix((y.cross(z), y, z)).transposed().to_4x4())
        add("GLOW", cr, glow)
    T, D, S = frame_at(1.0)
    tip = path_at(1.0)
    for k in range(3):
        d = (T * 0.8 + D * (0.5 + 0.3 * (k - 1)) + S * 0.2 * (k - 1)).normalized()
        cr = crystal(0.05, 0.22 - 0.05 * abs(k - 1), sides=4)
        for v in cr.verts:
            v.co.x *= 0.4
        cr.transform(Matrix.Translation(tip) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        add("GLOW", cr, glow)

    # ---- small swept wings at the shoulders --------------------------------------------------------------------------------
    p = path_at(0.19)
    T, D, S = Vector((0, 0.85, -0.25)).normalized(), Vector((0, 0.25, 0.85)).normalized(), Vector((1, 0, 0))   # spread to the sides
    for s in (-1, 1):
        root = hit(p + S * s * 1.5 + D * 0.08, -S * s)[0] - S * s * 0.03
        tips = [root + S * s * 1.15 + D * 0.7 + T * 0.2, root + S * s * 1.05 + D * 0.38 + T * 0.62, root + S * s * 0.6 + D * 0.12 + T * 0.85]
        back = root + T * 0.42
        for tp in tips:
            add("wings", loft([root, root.lerp(tp, 0.5) + D * 0.04, tp], lambda u: 0.022 * (1 - u) + 0.005, segs=6, rings=10), soft_m, COL["spar"], 0.7)
        mem = fan(root, tips + [back], [0.14, 0.14, 0.16], rows=7, sub=4, th=0.006)
        lu, lg = mem.verts.layers.float.get("u"), mem.verts.layers.float.get("g")
        lay = mem.verts.layers.float_color.new("col")
        for v in mem.verts:
            u, g = v[lu], v[lg]
            col = mix(COL["mem"], COL["mem_lt"], smooth(g, 0.3, 1.0))
            col = mix(col, COL["mid"], 0.4 * (1 - smooth(abs(u - round(u)), 0.0, 0.3)) * (1 - g))
            v[lay] = (*col, 1.0)
        add("wings", mem, soft_m, None, 0.8)

    lowest = min(v.co.z for k, (bm, _) in c.parts.items() if not k.startswith("GLOW") for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    global FACE, FOCUS
    FACE = FACE - Vector((0, 0, lowest))
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
