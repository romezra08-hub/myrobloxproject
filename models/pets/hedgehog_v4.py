"""Hedgehog pet: a round, cute hedgehog with soft clumped spines, remade from the game's blocky hedgehog with grey
spines and a cream face. Built from scratch by script.

    python models/pets/hedgehog.py --review out/hedgehog.png      # render the review sheet
    python models/pets/hedgehog.py --export models/export/hedgehog.fbx

Must-haves, checked in every review:
  1. The same pet: a hedgehog standing on four small legs, a spiny coat and a cream face.
  2. Round and cute: a ball of a body, a pointy cream face, a black button nose, beady glossy eyes.
  3. Lots of short spines in soft clumps, banded cream, brown and cream, swept back; under budget.
  4. Small paws, round ears peeking out, an autumn leaf and a small mushroom caught in the spines.
  5. Matte painted textures with crease shading; about 3 studs tall; Body under 12k triangles.

Round 4: fewer clumps to come back under budget; spines swept further back (beside the face they stuck out sideways like a mane).

Round 3: the spines are spread over the whole coat (the sampling stopped at the top half, so the sides stayed bald).

Round 2: the spiny coat carried down the sides (bald brown sides showed under it); thicker, shorter spines in tight clumps of three, so the coat reads soft, and within budget; a bigger leaf.

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

# ---- the hedgehog ---------------------------------------------------------------------------------

NAME = "Hedgehog"
COL = {"cream": hexc("#F1E2C6"), "cream_dk": hexc("#D4BC98"), "fur": hexc("#7A5638"), "fur_dk": hexc("#4E3422"),
       "spine_root": hexc("#E8D6B6"), "spine_mid": hexc("#7C5532"), "spine_tip": hexc("#F4E8D2"),
       "nose": hexc("#17110F"), "blush": hexc("#EBA08E"), "mouth": hexc("#5A3426"), "ear_in": hexc("#E3A898"),
       "paw": hexc("#E7B9A4"), "white": hexc("#FFFFFF"), "leaf": hexc("#E0782A"), "leaf_dk": hexc("#B2481C"),
       "leaf_vein": hexc("#F2B060"), "cap": hexc("#C28A55"), "cap_dk": hexc("#8E5A30"), "stem": hexc("#F2E6D0")}
SCALE = 1.35
BAKE = {"shade": 0.5, "rough": 0.9}
GRAIN = [("noise", 30.0, 0.05)]
BODY = Vector((0, 0.12, 0.78))
BODY_R = (0.8, 0.92, 0.72)
HEAD = Vector((0, -0.55, 0.72))
HEAD_M = M(HEAD, rot=(4, 0, 0))
FACE = Vector((0, -1.0, 0.75)) * SCALE
FOCUS = FACE
FACE_DIST = 4.4


def build():
    fur_m = painted("Fur", dict(strength=0.3, mottle=0.1, fine=55.0, length=4.0), rough=0.92)
    spine_m = grained("Spines", [("streak", 140.0, 0.08)], rough=0.75)
    eye_m = kit.material("Eyes", "#120C0A", rough=0.05)
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

    # ---- one fused skin: a round body, a pointy face, small legs ----------------------------------------
    clay = [ell(BODY, BODY_R),
            ell(hd((0, 0, 0)), (0.44, 0.42, 0.42)),
            ell(hd((0, -0.36, -0.08)), (0.22, 0.3, 0.2)),                       # snout
            ell(hd((0, -0.62, -0.1)), (0.11, 0.14, 0.1))]                       # snout tip
    for s in (-1, 1):
        clay += [ell(hd((0.2 * s, -0.22, -0.14)), (0.17, 0.17, 0.15)),           # cheeks
                 ell((0.36 * s, -0.48, 0.16), (0.13, 0.15, 0.18)),              # front legs
                 ell((0.37 * s, -0.56, 0.06), (0.12, 0.15, 0.07)),              # front paws
                 ell((0.42 * s, 0.5, 0.18), (0.15, 0.18, 0.18)),                # hind legs
                 ell((0.43 * s, 0.42, 0.06), (0.13, 0.17, 0.07))]               # hind paws
    skin = fuse(join(clay), voxel=0.02, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.17 * s, -1.5, 0.1)), fwd) for s in (-1, 1)]
    nose_at, nose_n = hit(hd((0, -1.5, -0.1)), fwd)
    smile = [hit(hd((x, -1.5, -0.25 + 2.2 * x * x)), fwd)[0] for x in (-0.1, -0.06, -0.03, 0.0, 0.03, 0.06, 0.1)]

    def spiny(co):
        """0..1: the spiny coat on the back and sides, not on the face or belly."""
        p = co - BODY
        q = HINV @ co
        face = smooth(q.y, 0.05, -0.2) * smooth(q.z, 0.42, 0.3)
        return smooth(co.z, 0.16, 0.3) * (1 - face) * smooth(p.y, -0.95, -0.6)

    def carve(co, n):
        d = n * 0.01 * noise.noise(co * 9.0)
        for e, en in eyes:
            d -= en * 0.025 * (1 - smooth((co - e).length, 0.06, 0.1))
        if (co - nose_at).length < 0.4:
            d -= n * 0.012 * (1 - smooth(poly_dist(co, smile), 0.006, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 4000, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.35, -0.05))).length, 0.25, 0.5)), factor=1.0)

    def colour(co, n, g=0.0):
        cream = mix(COL["cream_dk"], COL["cream"], smooth(n.z, -0.5, 0.4))
        fur = mix(COL["fur_dk"], COL["fur"], smooth(n.z, -0.3, 0.6))
        col = mix(cream, fur, spiny(co))
        paw = smooth(co.z, 0.1, 0.04)
        col = mix(col, COL["paw"], 0.8 * paw)
        if (co - nose_at).length < 0.5:
            for s in (-1, 1):
                col = mix(col, COL["blush"], 0.45 * (1 - smooth((co - hd((0.24 * s, -0.3, -0.12))).length, 0.04, 0.1)))
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.006, 0.014))
        return col
    add("skin", skin, fur_m, colour, 0.92)

    # ---- face: beady eyes, button nose, round ears ------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.075, 0.085, 0.045), cuts=3), e - en * 0.012, en), eye_m)
        add("glints", ell(e + en * 0.03 + R @ Vector((-0.024, 0, 0.03)), (0.022, 0.016, 0.022), cuts=1), fur_m, COL["white"], 0.3)
        add("glints", ell(e + en * 0.032 + R @ Vector((0.02, 0, -0.026)), (0.009, 0.007, 0.009), cuts=1), fur_m, COL["white"], 0.3)
    nose = ell((0, 0, 0), (0.07, 0.055, 0.055), cuts=2)
    nose.transform(M(nose_at + nose_n * 0.02))
    add("nose", nose, fur_m, lambda co, n, g: mix(COL["nose"], hexc("#4A3E3A"), 0.6 * smooth(n.z, 0.5, 0.95)), 0.25)
    for s in (-1, 1):
        ear = ell((0, 0, 0), (0.1, 0.05, 0.11), cuts=2)
        for v in ear.verts:
            if v.co.y < 0:
                v.co.y *= 0.3                                                # cupped to the front
        ear.transform(M(hd((0.3 * s, -0.02, 0.33)), rot=(-10, 25 * s, -20 * s)))
        add("ears", ear, fur_m, lambda co, n, g: mix(COL["cream_dk"], COL["ear_in"], smooth(-n.y, 0.2, 0.7)), 0.9)

    # ---- spines in soft clumps, swept back ---------------------------------------------------------------
    import random
    rnd = random.Random(5)
    N_CLUMP = 120
    spines = []
    TOTAL = int(N_CLUMP * 2.0)                                               # directions over the whole sphere; about half land on the coat
    for k in range(TOTAL):
        z = 1 - 2 * (k + 0.5) / TOTAL
        a = k * 2.39996
        d = Vector((math.sqrt(1 - z * z) * math.cos(a), math.sqrt(1 - z * z) * math.sin(a), z))
        p, nn = hit(BODY + d * 0.05, d)
        if p is None or spiny(p) < 0.6:
            continue
        spines.append((p, nn))
    back = Vector((0, 1, 0.15))
    for p, nn in spines:
        base_dir = (nn * 0.6 + back * 0.8).normalized()
        side = base_dir.cross(Vector((0, 0, 1))).normalized() if abs(base_dir.z) < 0.95 else Vector((1, 0, 0))
        up = side.cross(base_dir).normalized()
        low = smooth(p.z, 0.25, 0.6)                                         # shorter spines low on the sides
        for j in range(3):
            a = 2 * math.pi * j / 3 + rnd.random()
            spread = 0.12 + 0.06 * rnd.random()
            dirn = (base_dir + (side * math.cos(a) + up * math.sin(a)) * spread).normalized()
            L = (0.2 + 0.1 * low) + 0.08 * rnd.random()
            sp = lathe([(0.045, 0.0), (0.03, 0.5 * L), (0.0, L)], segs=4)
            sp.transform(Matrix.Translation(p - nn * 0.04 + (side * math.cos(a) + up * math.sin(a)) * 0.03) @ dirn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("spines", sp, spine_m, lambda co, n, g: mix(mix(COL["spine_root"], COL["spine_mid"], smooth(g, 0.0, 0.5)), COL["spine_tip"], smooth(g, 0.5, 1.0)), 0.75)

    # ---- an autumn leaf and a small mushroom caught in the spines -------------------------------------
    lp, ln = hit(BODY + Vector((0.3, 0.1, 0.0)), Vector((0.45, 0.1, 1.0)))
    leaf = ell((0, 0, 0), (0.22, 0.38, 0.02), cuts=3)
    for v in leaf.verts:
        v.co.x *= 1 - 0.75 * smooth(v.co.y, -0.05, 0.3) - 0.3 * smooth(-v.co.y, 0.1, 0.3)    # pointed tip
        v.co.z += 0.06 * (v.co.x / 0.17) ** 2 - 0.05 * (v.co.y / 0.3) ** 2                   # gently curled
    paint(leaf, lambda co, n, g: mix(mix(COL["leaf"], COL["leaf_dk"], smooth(abs(co.x), 0.02, 0.15) * 0.6 + 0.3 * smooth(co.y, 0.0, 0.3)),
                                     COL["leaf_vein"], 1 - smooth(abs(co.x), 0.004, 0.012)))
    q = ln.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    leaf.transform(Matrix.Translation(lp + ln * 0.22) @ q @ M(rot=(-15, 10, 40)))
    add("leaf", leaf, fur_m, None, 0.7)
    mp, mn = hit(BODY + Vector((-0.2, 0.2, 0.0)), Vector((-0.5, 0.25, 1.0)))
    stem = lathe([(0.045, 0.0), (0.04, 0.12), (0.035, 0.2)], segs=10)
    cap = lathe([(0.0, 0.17), (0.13, 0.17), (0.15, 0.19), (0.12, 0.25), (0.06, 0.29), (0.0, 0.3)], segs=14)
    q = mn.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    for b, col in ((stem, COL["stem"]), (cap, None)):
        b.transform(Matrix.Translation(mp + mn * 0.18) @ q)
        if col is None:
            add("mushroom", b, fur_m, lambda co, n, g: mix(COL["cap_dk"], COL["cap"], smooth(g, 0.0, 0.6)), 0.8)
        else:
            add("mushroom", b, fur_m, col, 0.85)

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
