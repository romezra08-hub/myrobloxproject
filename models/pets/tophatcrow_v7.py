"""TopHatCrow pet: a plump, stylish violet-black crow in a little top hat, remade from the game's dark purple crow
with a top hat, pink eyes and violet wing tips. Built from scratch by script.

    python models/pets/tophatcrow.py --review out/tophatcrow.png      # render the review sheet
    python models/pets/tophatcrow.py --export models/export/tophatcrow.fbx

Must-haves, checked in every review:
  1. The same pet: a dark purple crow in a black top hat with a pink band, with violet wing tips.
  2. Clearly not the Raven remake: plump, round and fluffy; violet-black; short legs; wings folded at the sides;
     a raised fan tail; bright pink-lilac eyes.
  3. Plumage that reads as feathers, not a smooth ball (sent back after round 5): layered breast scallops built in
     the geometry, each with an iridescent violet-blue rim and a shadow under it.
  4. Wings folded neatly along the sides in clear layers (coverts, secondaries, long violet-tipped primaries),
     with blue-violet sheen on the feather edges; a fan tail.
  5. A chunky, gently curved crow beak with nasal bristles, not a cone; big bright curious eyes; classy.
  6. A rakish top hat with a pink ribbon and a violet feather in the band.
  7. Matte painted textures with crease shading; about 3 studs tall; Body under 12k triangles.

Round 7: the wing feathers bent to follow the round body, so the folded wings lie along the sides instead of standing out as flaps, and made longer to cover the sides; scallops on the back too; the fan tail set outside the body and raised.

Round 6 (sent back for: a smooth plasticky ball body, wings drooping like arms, a cone beak): eight rows of
overlapping breast scallops built into the skin, painted with a blue-violet rim and a shadow under each; the wings
folded flat along the sides in three layers with iridescent edges and violet-tipped primaries running back past
the tail; a raised seven-feather fan tail; a chunky beak with a curved ridge, a hooked tip, a lower mandible and
nasal bristles; soft belly fluff.

Round 5: the breast feathers taken off again; the plumage painted with streaks, soft patch-to-patch shade changes and mottling instead, without dark joins.

Round 4: four staggered rows of breast feathers (they stuck out like thorns) and stronger streaks.

Round 3: soft velvet plumage streaks instead of feather cells (they looked like cracked scales on the head); the beak set higher and tilted up so it reads as a beak, not a drooping nose.

Round 2: no bib tufts (they read as a lumpy band across the chest); no raised rim round the eyes (goggle-eyed); a slightly smaller pink iris; a shorter, darker, more level beak; thicker legs; bolder feather scales.

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

# ---- the top hat crow -----------------------------------------------------------------------------

NAME = "TopHatCrow"
COL = {"black": hexc("#1C1624"), "deep": hexc("#0F0B14"), "violet": hexc("#4E2E80"), "blue": hexc("#2B3C8C"),
       "plum": hexc("#3A2050"), "tip": hexc("#8E58E2"), "tip_lt": hexc("#B48CF2"), "beak": hexc("#26222E"),
       "beak_lt": hexc("#5E566E"), "leg": hexc("#2C2833"), "iris": hexc("#E9A0D2"), "iris_dk": hexc("#B866A8"),
       "white": hexc("#FFFFFF"), "hat": hexc("#141218"), "hat_hi": hexc("#3A3546"), "ribbon": hexc("#E276B4"),
       "ribbon_dk": hexc("#B24C8A"), "sheen_b": hexc("#5468E0"), "sheen_v": hexc("#9A62F0")}
SCALE = 1.1
BAKE = {"shade": 0.42, "rough": 0.7}
GRAIN = [("streak", 70.0, 0.06), ("noise", 40.0, 0.04)]
HEAD = Vector((0, -0.3, 1.86))
HEAD_M = M(HEAD, rot=(-4, 0, 0))
BODY = Vector((0, 0.05, 1.08))
FACE = Vector((0, -0.75, 1.95)) * SCALE
FOCUS = FACE
FACE_DIST = 4.4


def leaf(length, width, thick=0.022, rings=7):
    """A flat feather along +Z from the origin: rings of four points (two edges, top and bottom), widest a third of
    the way, round at the root and pointed at the tip. About 54 triangles."""
    bm = bmesh.new()
    loops = []
    for i in range(rings):
        t = i / (rings - 1) * 0.96
        w = leaf_w(t, width)
        th = thick * (1 - 0.6 * t) + 0.003
        loops.append([bm.verts.new(p) for p in ((w, 0, t * length), (0, th, t * length), (-w, 0, t * length), (0, -th, t * length))])
    for a, b in zip(loops, loops[1:]):
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    tip = bm.verts.new((0, 0, length))
    for j in range(4):
        bm.faces.new((loops[-1][j], loops[-1][(j + 1) % 4], tip))
    bm.faces.new(list(reversed(loops[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def leaf_w(t, width):
    return width * (math.sin(math.pi * min(0.15 + t * 1.4, 1.0) * 0.5) ** 0.7) * (1 - t ** 3) ** 0.6 + 0.004


def sheen(co, n):
    """Violet-black plumage with an oil-slick sheen: purple where it faces up, blue at the sides."""
    col = mix(COL["deep"], COL["black"], smooth(n.z, -0.8, 0.0))
    col = mix(col, COL["violet"], 0.6 * smooth(n.z, 0.15, 0.85))
    col = mix(col, COL["blue"], 0.5 * smooth(abs(n.x), 0.45, 0.95) * smooth(n.z, -0.4, 0.35))
    return mix(col, COL["plum"], 0.3 * smooth(noise.noise(co * 4.0 + Vector((2, 7, 1))), 0.1, 0.6))


def feather_col(length, width, tipcol, row=0.0):
    """Paint for a leaf(): violet-black, a darker shaft, an iridescent blue-violet edge and (tipcol) violet tips."""
    def f(co, n, g):
        tt = min(max(co.z / length, 0.0), 1.0)
        col = mix(COL["black"], COL["plum"], 0.35 * smooth(tt, 0.2, 0.7) + 0.15 * row)
        edge = smooth(abs(co.x) / max(leaf_w(tt, width), 1e-3), 0.55, 0.95)
        col = mix(col, mix(COL["sheen_b"], COL["sheen_v"], smooth(tt, 0.2, 0.9)), 0.55 * edge)
        col = mix(col, COL["tip"], tipcol * smooth(tt, 0.55, 0.88))
        col = mix(col, COL["tip_lt"], 0.4 * tipcol * smooth(tt, 0.88, 1.0))
        return mix(col, COL["deep"], 0.5 * (1 - smooth(abs(co.x), 0.004, 0.012)) * smooth(tt, 0.95, 0.7))
    return f


def beak_shape(length, width, height, droop, lower=False):
    """A chunky crow beak along -Y from the origin: deep and wide at the base, a curved ridge and a hooked tip."""
    bm = kit.ball((2, 2, 2), cuts=3)
    for v in bm.verts:
        p = v.co.copy()
        t = (1 - p.y) / 2                                                   # 0 at the base, 1 at the tip
        w = width * (1 - t) ** 0.75 + 0.008
        h = height * (1 - t) ** (0.6 if not lower else 1.0) + 0.008
        z = p.z * h * (1.15 if p.z > 0 and not lower else 1.0)              # a raised ridge on the upper beak
        v.co = Vector((p.x * w, -t * length, z - droop * t * t))
    return bm


def build():
    plume_m = grained("Plumage", [("streak", 55.0, 0.1), ("cells", 16.0, 0.05), ("noise", 7.0, 0.05)], rough=0.6)
    feather_m = grained("Feather", [("streak", 110.0, 0.07), ("noise", 14.0, 0.04)], rough=0.55)
    cloth_m = painted("Cloth", dict(strength=0.18, mottle=0.08, fine=90.0, length=3.0), rough=0.6)
    eye_m = kit.material("Eyes", "#0E0A12", rough=0.05)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.6):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def tuft(at, d, length=0.12, r=0.05):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.02))], lambda t: r * (1 - 0.7 * t ** 1.5), segs=8, rings=5)

    def lay(bm, at, n, d):
        """Lay a shape built along +Z (flat in XZ) on a surface: +Z along d (tangent), +Y along the normal n."""
        n = Vector(n).normalized()
        d = (Vector(d) - n * Vector(d).dot(n)).normalized()
        x = n.cross(d).normalized()
        bm.transform(Matrix.Translation(at) @ Matrix((x, n, d)).transposed().to_4x4())
        return bm

    # ---- a plump round body and head ---------------------------------------------------------------------
    base = [ell(BODY, (0.62, 0.66, 0.7)),
            ell((0, -0.2, 1.2), (0.54, 0.5, 0.56)),                             # full chest
            ell(hd((0, 0, 0)), (0.42, 0.41, 0.41)),
            ell((0, -0.15, 1.55), (0.43, 0.41, 0.3))]                           # neck ruff
    for s in (-1, 1):
        base.append(ell(hd((0.2 * s, -0.17, -0.08)), (0.17, 0.16, 0.15)))       # cheeks
    joined = join([b.copy() for b in base])
    tree0 = BVHTree.FromBMesh(joined)

    def surf(d, origin=BODY):
        """Where a ray from inside the body along d leaves it, with the outward normal."""
        far = Vector(origin) + Vector(d).normalized() * 3.0
        loc, nrm, _, _ = tree0.ray_cast(far, -Vector(d).normalized())
        return loc, nrm

    # layered breast feathers: overlapping scallops, each lower edge lifted a little off the one below
    clay = list(base)
    scallops = []
    for row in range(8):
        el = math.radians(-38 + 10.5 * row)                                  # bottom of the belly up to the throat
        per = 9 if row < 6 else 7
        for k in range(per):
            az = math.radians(-62 + 124 * (k + 0.5 * (row % 2)) / (per - 0.5))
            d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
            loc, nrm = surf(d, BODY + Vector((0, -0.1, 0.12)))
            if loc is None:
                continue
            down = Vector((0, 0, -1))
            sc = ell((0, 0, 0), (0.11, 0.04, 0.1), cuts=3)
            sc.transform(M(rot=(-18, 0, 0)))                                   # the lower edge tips out
            lay(sc, loc + nrm * 0.005, nrm, down)
            clay.append(sc)
            dd = (down - nrm * down.dot(nrm)).normalized()
            scallops.append((loc, nrm, dd))
    for row in range(5):                                                     # and on the back, under the wing tips
        el = math.radians(-10 + 11 * row)
        for k in range(6):
            az = math.radians(135 + 90 * (k + 0.5 * (row % 2)) / 5.5)
            d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
            loc, nrm = surf(d, BODY + Vector((0, 0, 0.1)))
            if loc is None:
                continue
            down = Vector((0, 0.5, -1))
            sc = ell((0, 0, 0), (0.11, 0.04, 0.1), cuts=3)
            sc.transform(M(rot=(-15, 0, 0)))
            lay(sc, loc + nrm * 0.005, nrm, down)
            clay.append(sc)
            dd = (down - nrm * down.dot(nrm)).normalized()
            scallops.append((loc, nrm, dd))
    for k in range(9):                                                       # a soft rounded fluff at the belly
        az = math.radians(-80 + 160 * k / 8)
        loc, nrm = surf(Vector((math.sin(az) * 0.8, -math.cos(az) * 0.8, -0.6)))
        if loc is not None:
            clay.append(tuft(loc - nrm * 0.02, nrm + Vector((0, 0, -0.6)), length=0.08, r=0.06))
    for s in (-1, 1):
        for k in range(3):                                                   # soft cheek feathers
            clay.append(tuft(hd((0.3 * s, -0.08 + 0.08 * k, -0.18 - 0.03 * k)), R @ Vector((s, 0.2, -0.7)), length=0.1, r=0.05))
    joined.free()
    skin = fuse(join(clay), voxel=0.018, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = []
    for s in (-1, 1):
        d = R @ Vector((-0.55 * s, 1.0, 0.0))
        eyes.append(hit(hd((0.0, 0.0, 0.08)) - d.normalized() * 1.5, d))
    beak_at, beak_n = hit(hd((0, -1.5, -0.03)), R @ Vector((0, 1, 0)))

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 9.0)
        for e, en in eyes:
            d -= en * 0.025 * (1 - smooth((co - e).length, 0.08, 0.14))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6400, keep=lambda co: max(0.7 * (1 - smooth((Vector(co) - hd((0, -0.3, 0.0))).length, 0.25, 0.5)),
                                                    0.35 * smooth(Vector(co).y, -0.2, -0.5) * smooth(Vector(co).z, 1.7, 1.5)), factor=1.0)

    def plume(co, n, g=0.0):
        col = sheen(co, n)
        best, info = 0.2, None
        for loc, nrm, dd in scallops:
            dist = (co - loc).length
            if dist < best:
                best, info = dist, (loc, dd)
        if info is not None:
            loc, dd = info
            v = (co - loc).dot(dd) / 0.1                                    # 0 at a scallop's middle, 1 at its lower rim
            col = mix(col, mix(COL["sheen_b"], COL["sheen_v"], 0.5 + 0.5 * math.sin(co.x * 9)), 0.5 * smooth(v, 0.35, 0.8) * smooth(v, 1.15, 0.9))
            col = mix(col, COL["deep"], 0.5 * smooth(v, 1.0, 1.25))         # the shadow under the rim
            col = mix(col, COL["deep"], 0.25 * smooth(v, -0.2, -0.9))
        return col
    add("skin", skin, plume_m, plume, lambda co, n, g: 0.55 + 0.15 * smooth(-n.z, 0.0, 0.8))

    # ---- big bright eyes ---------------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        iris = facing(ell((0, 0, 0), (0.095, 0.095, 0.03), cuts=3), e + en * 0.004, en)
        add("iris", iris, cloth_m, lambda co, n, g, e=e: mix(COL["iris"], COL["iris_dk"], smooth((co - e).length, 0.06, 0.095)), 0.3)
        add("eyes", facing(ell((0, 0, 0), (0.072, 0.072, 0.04), cuts=3), e + en * 0.012, en), eye_m)
        up = R @ Vector((0, 0, 1))
        side = en.cross(up).normalized()
        add("glints", ell(e + en * 0.05 + up * 0.03 - side * 0.02 * s, (0.024, 0.024, 0.018), cuts=1), cloth_m, COL["white"], 0.3)
        add("glints", ell(e + en * 0.05 - up * 0.03 + side * 0.025 * s, (0.01, 0.01, 0.008), cuts=1), cloth_m, COL["white"], 0.3)

    # ---- a chunky, gently curved crow beak with nasal bristles -------------------------------------------
    BK = M(beak_at - beak_n * 0.05) @ R.to_4x4()

    def beak_col(lower):
        def f(co, n, g):
            col = mix(COL["beak"], COL["beak_lt"], 0.45 * smooth(n.z, 0.2, 0.95))
            return mix(col, COL["violet"], 0.25 * smooth(n.z, 0.6, 0.95)) if not lower else col
        return f
    upper = beak_shape(0.3, 0.12, 0.085, 0.07)
    upper.transform(BK @ M((0, 0, 0.015)))
    add("beak", upper, cloth_m, beak_col(False), 0.4)
    lower = beak_shape(0.22, 0.1, 0.045, 0.03, lower=True)
    lower.transform(BK @ M((0, 0, -0.06)))
    add("beak", lower, cloth_m, beak_col(True), 0.45)
    for k, x in enumerate((-0.05, 0.0, 0.05)):                               # bristle feathers over the base of the beak
        br = leaf(0.13, 0.04, thick=0.012, rings=5)
        paint(br, feather_col(0.13, 0.04, 0.0))
        br.transform(BK @ M((x, 0.03, 0.09), rot=(100 - 8 * abs(k - 1), 0, -15 * (k - 1))))
        add("beak", br, feather_m, None, 0.5)

    # ---- wings folded neatly along the sides: coverts over secondaries over the long violet-tipped primaries ----
    for s in (-1, 1):
        def wing_feather(y, z, d, length, width, lift, tipcol, row):
            loc, nrm = surf(Vector((s, 0, 0)), Vector((0, y, z)))
            if loc is None:
                return
            bm = leaf(length, width)
            paint(bm, feather_col(length, width, tipcol, row))
            lay(bm, loc + nrm * lift, nrm, d)
            plane = loc + nrm * lift
            for v in bm.verts:                                               # follow the round body, keeping the layering
                off = (v.co - plane).dot(nrm)
                near, nn, _, _ = tree0.find_nearest(v.co)
                if near is not None:
                    v.co = near + nn * (lift + off)
            add("wings", bm, feather_m, None, 0.5)
        for i in range(5):                                                   # primaries, longest, running back past the tail
            t = i / 4
            wing_feather(lerp(0.12, 0.34, t), lerp(1.2, 1.02, t), Vector((0.12 * s, 1.0, -0.32 - 0.08 * t)), lerp(0.95, 0.8, t), 0.11, 0.035 + 0.004 * i, 1.0, 0)
        for i in range(6):                                                   # secondaries along the fold
            t = i / 5
            wing_feather(lerp(-0.3, 0.12, t), lerp(1.3, 1.16, t), Vector((0.05 * s, 1.0, -0.62)), lerp(0.66, 0.72, t), 0.13, 0.055, 0.35, 0.3)
        for row, (zz, ln) in enumerate(((1.44, 0.42), (1.33, 0.36))):         # two rows of coverts at the shoulder
            for i in range(5):
                t = i / 4
                wing_feather(lerp(-0.34, 0.14, t), zz - 0.06 * t, Vector((0.0, 1.0, -0.75)), ln, 0.12, 0.075 + 0.015 * row, 0.0, 0.6)

    # ---- a raised fan tail ----------------------------------------------------------------------------------
    for k in range(7):
        a = math.radians(-45 + 15 * k)
        dirn = Vector((math.sin(a) * 0.7, math.cos(a), 0.42)).normalized()
        side = Vector((0, 0, 1)).cross(dirn).normalized()
        N = dirn.cross(side).normalized()
        ln = 0.74 - 0.06 * abs(k - 3)
        bm = leaf(ln, 0.12)
        paint(bm, feather_col(ln, 0.12, 0.7))
        bm.transform(Matrix.Translation(Vector((0, 0.64, 0.72)) + N * 0.008 * abs(k - 3)) @ Matrix((side, N, dirn)).transposed().to_4x4())
        add("tail", bm, feather_m, None, 0.5)

    # ---- short legs and feet ---------------------------------------------------------------------------
    for s in (-1, 1):
        hip = Vector((0.2 * s, -0.02, 0.5))
        foot = Vector((0.22 * s, -0.08, 0.04))
        add("legs", loft([hip, (hip + foot) / 2 + Vector((0, -0.02, 0)), foot], lambda t: lerp(0.08, 0.055, t), segs=8, rings=6), cloth_m,
            lambda co, n, g: mix(COL["leg"], COL["beak_lt"], 0.25 * smooth(n.z, 0.3, 0.9)), 0.5)
        for a in (-28, 0, 28, 180):
            d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
            ln = 0.12 if a == 180 else 0.2
            toe = loft([foot, foot + d * ln * 0.6 + Vector((0, 0, -0.01)), foot + d * ln + Vector((0, 0, -0.03))], lambda t: lerp(0.042, 0.022, t), segs=6, rings=5)
            add("legs", toe, cloth_m, COL["leg"], 0.5)

    # ---- a rakish little top hat with a pink ribbon and a violet feather ----------------------------
    HAT = M(hd((0.04, 0.04, 0.33)), rot=(-12, -14, 0))
    hat = lathe([(0, 0.03), (0.22, 0.03), (0.36, 0.0), (0.4, 0.02), (0.39, 0.05), (0.26, 0.055), (0.235, 0.1),
                 (0.24, 0.42), (0.262, 0.54), (0.24, 0.57), (0, 0.575)], segs=36)
    hat.transform(HAT)
    HR = HAT.to_3x3()

    def hat_col(co, n, g):
        ln = HR.inverted() @ n
        col = mix(COL["hat"], COL["hat_hi"], 0.5 * smooth(ln.z, 0.3, 0.95) + 0.25 * smooth(abs(ln.x), 0.7, 1.0))
        return mix(col, COL["hat"], 0.6 * smooth(-ln.z, 0.2, 0.8))
    add("hat", hat, cloth_m, hat_col, 0.5)
    band = lathe([(0.237, 0.07), (0.256, 0.075), (0.258, 0.17), (0.239, 0.175)], segs=36, closed=True)
    band.transform(HAT)
    add("hat", band, cloth_m, lambda co, n, g: mix(COL["ribbon"], COL["ribbon_dk"], 0.5 * smooth(n.z, 0.3, -0.6)), 0.45)
    plume = leaf(0.42, 0.06)
    paint(plume, lambda co, n, g: mix(COL["violet"], COL["tip_lt"], smooth(co.z, 0.1, 0.42)))
    plume.transform(HAT @ M((0.235, 0.05, 0.1), rot=(0, 22, 0)) @ M(rot=(0, 0, 0)))
    add("hat", plume, feather_m, None, 0.5)


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
