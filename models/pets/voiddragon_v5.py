"""VoidDragon pet: a dark violet dragon with magenta bat wings and a glowing amethyst ridge, remade from the game's
blocky dark purple dragon with magenta wings. Built from scratch by script.

    python models/pets/voiddragon.py --review out/voiddragon.png      # render the review sheet
    python models/pets/voiddragon.py --export models/export/voiddragon.fbx

Must-haves, checked in every review:
  1. The same pet: a dark purple four-legged dragon with magenta bat wings.
  2. A proper dragon, not childish: a wedge head with swept horns, a short thick neck, a muscular low stance on
     thick clawed legs, big bat wings half spread with magenta membranes, a long tail.
  3. Dark violet scales with a paler mauve belly, and a ridge of amethyst crystals from the head to the tail tip
     that glows (GLOW).
  4. A confident, calm face: lilac eyes with the outer corners up under a level lid, no brow ledge shading them.
  5. Clearly not the obsidian Dragon (tall, long neck, red) or the SunDragon (gold, folded wings): low and broad,
     violet and magenta, crystals instead of blades. Matte scales with varied roughness; up to about 4.5 studs
     tall and under 6 long; Body under 12k triangles.

Final: round 5.

Export: the empty texels of the roughness map are filled with its median, so mipmapping does not bleed gloss
into the seams.

Round 5: almond eyes with a level upper lid over their top third (the round lidless discs stared).

Round 4: the head tipped a little nose-down and raised (from the front its underside merged with the throat and the
face read as a column); bigger eyes facing more forwards with less lid (they read as sleepy slits head-on); a
slimmer upper neck.

Round 3: the head rebuilt as one wedge, broad at the cheeks and tapering in width and height to a blunt nose
(a small skull with a tube snout still read as a duck or a seal); a slimmer neck so the head stands clear of the
chest; bigger scales with darker joins (the fine ones read as felt); deeper violet crystals (they glowed pink).

Round 2: a boxy snout tapering to a blunt wedge (the rounded one read as a duck bill or a hippo); the head raised
and further forward on a short neck leaning forward (it sat sunk in the chest); a smaller chest (it read as a fat
bear); the crystal ridge starts small behind the head and peaks at the shoulders (a big cluster on the head read as
a tiara); darker violet scales and a deeper magenta membrane (it read pastel).

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

# ---- the void dragon ------------------------------------------------------------------------------

NAME = "VoidDragon"
COL = {"violet": hexc("#2E1B50"), "violet_dk": hexc("#170C2A"), "violet_lt": hexc("#4A2F7A"), "plum": hexc("#542A72"),
       "belly": hexc("#6E5788"), "belly_dk": hexc("#47355E"), "mem": hexc("#A82AA6"), "mem_lt": hexc("#DC6AD8"),
       "mem_dk": hexc("#7E2280"), "bone": hexc("#D8C8EA"), "horn": hexc("#2A1C3C"), "line": hexc("#160C22"),
       "pupil": hexc("#1A0A24"), "white": hexc("#FFFFFF"), "claw": hexc("#D9CCE6")}
SCALE = 1.0
BAKE = {"shade": 0.42, "rough": 0.84}
GRAIN = [("cells", 26.0, 0.05), ("noise", 6.0, 0.03)]
HEAD = Vector((0, -1.46, 1.9))
HEAD_M = M(HEAD, rot=(5, 0, 0))
NECK = [Vector((0, -0.5, 1.22)), Vector((0, -0.86, 1.48)), Vector((0, -1.14, 1.74)), Vector((0, -1.32, 1.86))]
TAIL = [Vector((0, 0.95, 1.0)), Vector((0, 1.45, 0.78)), Vector((0.2, 1.98, 0.48)), Vector((0.55, 2.4, 0.26)), Vector((0.98, 2.62, 0.18)),
        Vector((1.36, 2.62, 0.26))]
FACE = HEAD + Vector((0, -0.32, -0.02))
FOCUS = FACE * SCALE
FACE_DIST = 3.6
LEGS = [(-0.4, -0.5, True), (0.4, -0.5, True), (-0.42, 0.72, False), (0.42, 0.72, False)]


def build():
    scale_m = crusted("Scales", rough=0.84, size=0.062, joins=0.36, vary=0.16)
    mem_m = painted("Membrane", dict(strength=0.08, mottle=0.1, fine=20.0, length=2.0), rough=0.8)
    eye_m = kit.material("Eyes", "#E592FF", rough=0.06)
    glow = kit.material("GLOW_Amethyst", "#9440FF", rough=0.3, emit=2.0)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def add(part, bm, mat, col=None, rough=0.84):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def hd(p):
        return HEAD_M @ Vector(p)

    def head():
        """One wedge from the cheeks to the nose: broad at the back, tapering in width and height to a blunt tip."""
        bm = kit.rounded_box((0.46, 0.98, 0.32), n=2.7, cuts=8)
        for v in bm.verts:
            t = smooth(-v.co.y, -0.49, 0.49) ** 0.9                             # 0 at the back of the head, 1 at the nose
            v.co.x *= lerp(1.0, 0.36, t)
            if v.co.z > 0:
                v.co.z *= lerp(1.0, 0.42, t)                                      # a straight top line sloping to the nose
            else:
                v.co.z *= lerp(1.0, 0.6, t)
        bm.transform(HEAD_M @ M((0, -0.2, 0.0)))
        return bm

    # ---- one fused skin: deep chest, broad haunches, a short thick neck, a wedge head, thick legs, a long tail ------
    clay = [ell((0, 0.12, 0.98), (0.44, 0.78, 0.4)),
            ell((0, -0.42, 1.04), (0.43, 0.44, 0.44)),                          # deep chest
            ell((0, 0.72, 1.0), (0.46, 0.44, 0.42)),                           # haunches
            loft(NECK, lambda t: lerp(0.3, 0.18, t), segs=14, rings=12),
            loft(TAIL, lambda t: 0.33 * (1 - t) ** 1.1 + 0.035, segs=12, rings=34),
            head(),
            ell(hd((0, 0.12, 0.02)), (0.2, 0.2, 0.16)),                         # the back of the skull
            ell(hd((0, -0.24, -0.12)), (0.13, 0.36, 0.06))]                    # lower jaw
    for s in (-1, 1):
        clay += [ell(hd((0.1 * s, 0.04, 0.11)), (0.06, 0.12, 0.03), rot=(0, 8 * s, 0)),         # low brow ridges, behind the eyes
                 ell(hd((0.16 * s, 0.06, -0.07)), (0.09, 0.14, 0.09)),            # broad cheeks
                 ell((0.26 * s, -0.56, 1.14), (0.17, 0.22, 0.22))]                # chest muscle
    for x, y, front in LEGS:
        if front:
            clay += [ell((x * 0.95, y, 0.9), (0.22, 0.27, 0.34)),               # shoulders
                     loft([Vector((x * 0.98, y, 0.78)), Vector((x * 1.04, y - 0.06, 0.48)), Vector((x * 1.08, y - 0.05, 0.22)), Vector((x * 1.1, y - 0.1, 0.09))],
                          lambda t: 0.135 + 0.06 * (1 - smooth(t, 0.1, 0.6)), segs=14, rings=10)]
        else:
            clay += [ell((x * 0.96, y, 0.86), (0.25, 0.4, 0.38)),               # thighs
                     loft([Vector((x, y + 0.1, 0.66)), Vector((x * 1.03, y + 0.26, 0.42)), Vector((x * 1.06, y + 0.12, 0.2)), Vector((x * 1.08, y + 0.02, 0.09))],
                          lambda t: 0.13 + 0.08 * (1 - smooth(t, 0.05, 0.45)), segs=14, rings=10)]
        py = y - 0.18 if front else y - 0.08
        clay.append(ell((x * 1.09, py, 0.07), (0.16, 0.22, 0.075)))            # broad clawed feet
    skin = fuse(join(clay), voxel=0.02, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = []
    for s in (-1, 1):
        tgt = hd((0.15 * s, -0.08, 0.05))
        o = tgt + R @ Vector((0.9 * s, -0.9, 0.12))
        eyes.append(hit(o, tgt - o))
    nostrils = [hit(hd((0.045 * s, -1.5, 0.0)), fwd) for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        pts = []
        for k in range(6):
            y = -0.62 + 0.105 * k
            z = -0.085 + 0.035 * smooth(k, 2.5, 5)
            p = hit(hd((0.6 * s, y, z)), R @ Vector((-s, 0, 0)))[0]
            if p is not None:
                pts.append(p)
        mouth.append(pts)
    SPINE = [kit._spline(NECK, t) for t in (2.5, 1.85, 1.2, 0.55)] + [Vector((0, -0.25, 1.48)), Vector((0, 0.15, 1.38)), Vector((0, 0.6, 1.42))]

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 5.0)
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.05, 0.09))
        for e, en in nostrils:
            if e is not None:
                d -= en * 0.016 * (1 - smooth((co - e).length, 0.012, 0.032))
        if (co - HEAD).length < 0.7:
            md = min(poly_dist(co, m) for m in mouth if len(m) > 1)
            d -= n * 0.012 * (1 - smooth(md, 0.004, 0.014))
        if 0.55 < co.z < 1.3 and -0.9 < co.y < 0.8 and n.z < -0.25:                  # belly plate grooves
            d -= n * 0.01 * smooth(0.5 + 0.5 * math.cos(co.y * 26), 0.85, 1.0)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6400, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.2, -0.02))).length, 0.2, 0.42)),
                                                    0.3 * (1 - smooth((Vector(co) - HEAD).length, 0.3, 0.55))), factor=1.0)

    def scale_colour(co, n, g=0.0):
        col = mix(COL["violet_dk"], COL["violet"], smooth(n.z, -0.6, 0.1))
        col = mix(col, COL["violet_lt"], 0.4 * smooth(n.z, 0.3, 0.9) * smooth(noise.noise(co * 3.0), -0.2, 0.5))
        col = mix(col, COL["violet_dk"], 0.55 * smooth(poly_dist(co, SPINE), 0.2, 0.06) * smooth(n.z, 0.3, 0.8))   # a darker back
        col = mix(col, COL["plum"], 0.45 * smooth(n.x * n.x, 0.5, 0.9) * smooth(co.z, 0.5, 1.0))               # plum on the flanks
        col = mix(col, mix(COL["belly_dk"], COL["belly"], smooth(-n.z, 0.4, 0.9)), 0.9 * smooth(-n.z, 0.15, 0.55) * smooth(co.z, 0.5, 0.75))
        col = mix(col, COL["belly"], 0.75 * smooth(-n.y - n.z, 0.6, 1.2) * smooth(co.z, 0.9, 1.2) * smooth(co.y, -0.3, -0.7))   # throat
        col = mix(col, COL["violet_dk"], 0.5 * smooth(co.z, 0.35, 0.08))                                       # dark feet
        if (co - HEAD).length < 0.6:
            for e, en in eyes:
                col = mix(col, COL["line"], 0.8 * (1 - smooth((co - e).length, 0.062, 0.08)))
            for e, en in nostrils:
                if e is not None:
                    col = mix(col, COL["line"], 0.8 * (1 - smooth((co - e).length, 0.012, 0.025)))
        return col
    add("skin", skin, scale_m, scale_colour, lambda co, n, g: 0.82 - 0.12 * smooth(-n.z, 0.3, 0.7))

    # ---- lilac eyes, outer corners up as seen from the front, under a level lid ---------------------------------
    EW, EH, ED = 0.11, 0.072, 0.036
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(11 * s), 4, Vector((0, -1, 0)))       # outer corners up, as seen from the front
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.012) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=4)
        for v in eb.verts:
            v.co.y *= 1 - 0.4 * (v.co.x / (EW / 2)) ** 2                          # almond: pinched corners
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.012 + en * (ED - 0.005)
        pupil = kit.ball((0.032, 0.056, 0.012), cuts=2)
        pupil.transform(Matrix.Translation(front + up * 0.004) @ tilt @ basis)
        add("pupils", pupil, scale_m, COL["pupil"], 0.3)
        add("pupils", ell(front + en * 0.005 + up * 0.018 + ex * 0.014 * s, (0.011, 0.011, 0.005), cuts=2), scale_m, COL["white"], 0.3)
        lid = kit.ball((EW * 1.12, EH * 1.16, ED * 2.3), cuts=10)
        for v in lid.verts:
            v.co.y *= 1 - 0.4 * (v.co.x / (EW * 0.56)) ** 2
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.16 or v.co.z < -0.004], context='VERTS')    # a level upper lid over the top third
        lid.transform(place)
        add("lids", lid, scale_m, COL["violet"])

    for m in mouth:                                                                     # a calm closed smile line
        if len(m) > 1:
            add("mouth", loft([p + (p - HEAD).normalized() * 0.002 for p in m], lambda t: 0.006 + 0.002 * t, segs=5, rings=3 * len(m)), scale_m, COL["line"])

    # ---- swept-back horns, dark at the root and pale at the tips -----------------------------------------------------
    def horn_col(co, n, g):
        return mix(COL["horn"], COL["bone"], smooth(g, 0.35, 1.0))
    for s in (-1, 1):
        root = hd((0.12 * s, 0.12, 0.12))
        pts = [root, root + R @ Vector((0.06 * s, 0.18, 0.08)), root + R @ Vector((0.12 * s, 0.42, 0.12)), root + R @ Vector((0.15 * s, 0.68, 0.26))]
        add("horns", loft(pts, lambda t: 0.068 * (1 - t) ** 0.9 + 0.006, segs=10, rings=12), scale_m, horn_col, 0.55)
        root = hd((0.18 * s, 0.1, -0.02))
        pts = [root, root + R @ Vector((0.08 * s, 0.16, 0.0)), root + R @ Vector((0.13 * s, 0.34, 0.06))]
        add("horns", loft(pts, lambda t: 0.04 * (1 - t) ** 0.9 + 0.005, segs=8, rings=8), scale_m, horn_col, 0.55)

    # ---- a ridge of glowing amethyst crystals from the head to the tail tip ---------------------------------------------
    path = SPINE + [kit._spline(TAIL, t) for t in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5)]
    for k, p in enumerate(path):
        top, nrm = hit(p + Vector((0, 0, 1.5)), (0, 0, -1))
        if top is None:
            continue
        h = [0.12, 0.16, 0.2, 0.25, 0.28, 0.27, 0.25][k] if k < 7 else 0.23 - 0.017 * (k - 7)
        h = max(h, 0.09)
        cr = crystal(0.05 + 0.12 * h, h, sides=6)
        cr.transform(M(top - Vector((0, 0, 0.03)), rot=(-24, 0, 12 * math.sin(k * 1.7))))
        add("GLOW", cr, glow)
        if 1 < k < 12 and k % 2 == 1:
            for s in (-1, 1):
                small = crystal(0.035, h * 0.55, sides=5)
                small.transform(M(top + Vector((0.06 * s, 0.03, -0.03)), rot=(-20, 28 * s, 0)))
                add("GLOW", small, glow)
    tip, tang = TAIL[-1], (TAIL[-1] - TAIL[-2]).normalized()
    for k in range(3):                                                                     # a crystal cluster at the tail tip
        d = (tang + Vector((0.0, 0.0, 0.9)) + Vector((0.4 * (k - 1), 0.25 * (k - 1), 0))).normalized()
        cr = crystal(0.06, 0.3 - 0.06 * abs(k - 1), sides=6)
        cr.transform(Matrix.Translation(tip) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        add("GLOW", cr, glow)

    # ---- big bat wings, half spread, with magenta membranes -----------------------------------------------------------
    def bone_col(co, n, g):
        return COL["violet_dk"]

    for s in (-1, 1):
        shoulder, sn = hit(Vector((0.9 * s, -0.32, 1.32)), Vector((-s, 0, -0.2)))
        shoulder = shoulder - sn * 0.05
        elbow = Vector((0.95 * s, -0.12, 2.02))
        wrist = Vector((1.62 * s, 0.12, 2.5))
        tips = [wrist + Vector((0.9 * s, 0.22, -0.18)), wrist + Vector((0.78 * s, 0.82, -0.62)), wrist + Vector((0.4 * s, 1.22, -1.0))]
        hip = Vector((0.36 * s, 0.7, 1.28))
        add("wings", loft([shoulder, elbow, wrist], lambda t: 0.1 - 0.045 * t, segs=10, rings=14), scale_m, bone_col)
        for k, t in enumerate(tips):
            mid = wrist.lerp(t, 0.5) + Vector((0, 0, 0.06))
            add("wings", loft([wrist, mid, t], lambda u: 0.042 * (1 - u) + 0.008, segs=7, rings=12), scale_m, bone_col)
        claw = lathe([(0.0, 0.0), (0.035, 0.0), (0.0, 0.14)], segs=6)
        claw.transform(Matrix.Translation(wrist) @ Vector((0.15 * s, -0.5, 0.85)).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4())
        add("claws", claw, scale_m, COL["claw"], 0.5)
        rim = tips + [hip, shoulder]
        mem = fan(wrist, rim, [0.12, 0.12, 0.2, 0.0], rows=8, sub=4, th=0.008)
        lu = mem.verts.layers.float.get("u")
        lg = mem.verts.layers.float.get("g")
        lay = mem.verts.layers.float_color.new("col")
        for v in mem.verts:
            u, g = v[lu], v[lg]
            spar = 1 - smooth(abs(u - round(u)), 0.0, 0.3) if u < 2.5 else 0.0
            col = mix(COL["mem"], COL["mem_lt"], smooth(g, 0.35, 1.0) * 0.8)
            col = mix(col, COL["mem_dk"], 0.6 * spar * (1 - 0.5 * g))
            col = mix(col, COL["mem_dk"], 0.5 * smooth(g, 0.25, 0.0))
            v[lay] = (*col, 1.0)
        add("wings", mem, mem_m, None, 0.78)

    # ---- three pale claws on each foot ----------------------------------------------------------------------------------
    for x, y, front in LEGS:
        py = y - 0.18 if front else y - 0.08
        for dx in (-0.08, 0.0, 0.08):
            p, nrm = hit((x * 1.09 + dx, py - 1, 0.05), (0, 1, 0))
            if p is None:
                continue
            cl = lathe([(0.0, 0.0), (0.035, 0.0), (0.0, 0.12)], segs=6)
            cl.transform(M(p + Vector((0, 0.005, -0.01)), rot=(100, 0, 0)))
            add("claws", cl, scale_m, COL["claw"], 0.5)

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
