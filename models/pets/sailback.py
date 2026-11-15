"""SailBack pet: a handsome sail-backed lizard, remade from the game's blocky dark red sail-backed reptile. Built
from scratch by script.

    python models/pets/sailback.py --review out/sailback.png      # render the review sheet
    python models/pets/sailback.py --export models/export/sailback.fbx

Must-haves, checked in every review:
  1. The same pet: a dark red, four-legged reptile with a tall sail along its back.
  2. A big creature, never childish: a long low body on a strong sprawling stance, a deep skull with brow
     ridges, a small calm eye under a heavy lid and a closed mouth whose corner lifts a little.
  3. A ribbed sail: bone ribs with a membrane between them that dips between the ribs, painted in warm
     sunset stripes (crimson at the base through orange and amber to gold, a rust rim).
  4. Rust-red scaly hide with darker saddle bands and a paler belly; cream claws.
  5. Matte painted textures with crease shading; up to about 4.5 studs tall; Body under 12k triangles.

Export: the empty texels of the roughness map are filled with its median (they were 0.05, which
mipmapping would bleed into the seams as gloss).

Round 5 (tried, not kept): the lids cut back to a thin cap and a narrower snout; wide open, the eyes
looked surprised and childish, so this file is round 4.

Round 4: a slightly bigger eye under a smaller brow ridge set further back (the brow made the look worried); a redder hide with bolder scales and saddle bands.

Round 3: the snout and jaw taper forward (the round snout read as a hippo nose); flatter brow ridges and lids, so the look is calm instead of sad; a much darker rust hide.

Round 2: a bigger, longer head on a thicker neck (it read as a small hippo head); a wider, lower sail (it was a tall narrow comb); a darker rust-red hide (it looked salmon pink); the eyelids raised a little (the face looked grumpy).

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

# ---- the sail-backed lizard -----------------------------------------------------------------------

NAME = "SailBack"
COL = {"rust": hexc("#701A0E"), "rust_lt": hexc("#922C18"), "band": hexc("#360E08"), "belly": hexc("#B06A42"),
       "belly_dk": hexc("#84442A"), "deep": hexc("#4A1A10"), "mouth": hexc("#3A120C"), "claw": hexc("#E8D7B8"),
       "claw_dk": hexc("#9C876A"), "pupil": hexc("#160C08"), "white": hexc("#FFFFFF"),
       "s0": hexc("#741A16"), "s1": hexc("#B8401C"), "s2": hexc("#E2802A"), "s3": hexc("#F2BC52"), "s_rim": hexc("#7A2C18"),
       "rib": hexc("#5A1C12"), "rib_tip": hexc("#E4C9A0")}
SCALE = 1.35
BAKE = {"shade": 0.5, "rough": 0.82}
GRAIN = [("cells", 26.0, 0.06), ("noise", 50.0, 0.04)]
HEAD = Vector((0, -1.72, 0.95))
HEAD_M = M(HEAD, rot=(6, 0, 0)) @ M(scale=1.3)
FACE = Vector((-0.2, -2.25, 0.98)) * SCALE
FOCUS = FACE
FACE_DIST = 5.4
SAIL = (-0.95, 1.25, 1.3)                         # from y, to y, peak height


def build():
    scale_m = scaled("Scales", rough=0.8, size=0.065, joins=0.5, vary=0.16)
    sail_m = grained("Sail", [("streak", 30.0, 0.08), ("noise", 9.0, 0.06)], rough=0.7)
    bone_m = grained("Bone", [("noise", 40.0, 0.05)], rough=0.6)
    eye_m = kit.material("Eyes", "#D49432", rough=0.08)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()
    HINV = HEAD_M.inverted()

    def hd(p):
        return HEAD_M @ Vector(p)

    def add(part, bm, mat, col=None, rough=0.8):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        roughen(bm, rough if callable(rough) else (lambda co, n, g, r=rough: r))
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def snout(at, r, front):
        """An ellipsoid in head space that narrows towards its front end (-y) to `front` of its width."""
        bm = kit.ball(tuple(2 * x for x in r), cuts=4)
        kit.taper(bm, axis=1, lo=front, hi=1.05)
        bm.transform(HEAD_M @ M(at))
        return bm

    # ---- one fused skin: long low body, sprawling legs, deep head, long tail ----------------------------
    clay = [ell((0, 0.1, 0.75), (0.55, 1.15, 0.44)),
            ell((0, -0.72, 0.76), (0.5, 0.5, 0.44)),                            # chest and shoulders
            ell((0, 0.9, 0.74), (0.5, 0.5, 0.42)),                              # hips
            loft([(0, -0.95, 0.8), (0, -1.2, 0.86), (0, -1.45, 0.92)], lambda t: lerp(0.38, 0.32, t), segs=14, rings=6),
            loft([(0, 1.15, 0.74), (0, 1.9, 0.56), (0, 2.6, 0.33), (0.15, 3.2, 0.16), (0.38, 3.6, 0.08)],
                 lambda t: 0.37 * (1 - t) ** 1.1 + 0.035, segs=14, rings=20),
            ell(hd((0, 0.02, 0.02)), (0.3, 0.36, 0.27)),                        # skull
            snout(Vector((0, -0.42, -0.02)), (0.21, 0.46, 0.17), 0.55),           # snout, tapering forward
            snout(Vector((0, -0.3, -0.15)), (0.22, 0.44, 0.11), 0.6)]            # lower jaw
    for s in (-1, 1):
        clay += [ell(hd((0.14 * s, -0.04, 0.15)), (0.08, 0.13, 0.045)),         # brow ridges
                 ell(hd((0.19 * s, 0.06, -0.05)), (0.14, 0.18, 0.15)),          # jaw muscles
                 ell((0.45 * s, -0.7, 0.66), (0.24, 0.28, 0.26)),               # shoulders
                 loft([(0.5 * s, -0.7, 0.62), (0.8 * s, -0.72, 0.44), (0.82 * s, -0.84, 0.12)], lambda t: lerp(0.19, 0.13, t), segs=12, rings=8),
                 ell((0.84 * s, -0.95, 0.065), (0.17, 0.25, 0.075)),            # front feet
                 ell((0.52 * s, 0.86, 0.58), (0.26, 0.34, 0.3)),                # thighs
                 loft([(0.6 * s, 0.86, 0.52), (0.85 * s, 0.8, 0.4), (0.84 * s, 0.9, 0.12)], lambda t: lerp(0.2, 0.14, t), segs=12, rings=8),
                 ell((0.86 * s, 0.78, 0.065), (0.18, 0.28, 0.075))]             # hind feet
    skin = fuse(join(clay), voxel=0.024, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = []
    for s in (-1, 1):
        d = R @ Vector((-0.8 * s, 0.45, -0.1))
        eyes.append(hit(hd((0.0, -0.06, 0.06)) - d.normalized() * 1.0, d))
    nostrils = [hit(hd((0.06 * s, -0.78, 0.4)), R @ Vector((0, 0.3, -1)))[0] for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        line = []
        for k in range(8):
            t = k / 7
            y = lerp(-0.8, 0.05, t)
            z = -0.1 + 0.05 * smooth(t, 0.55, 1.0)                           # the corner lifts: a calm, sure smile
            p, _ = hit(hd((0.6 * s, y, z)), R @ Vector((-s, 0, 0)))
            if p is not None:
                line.append(p)
        mouth.append(line)
    front, _ = hit(hd((0, -1.2, -0.1)), R @ Vector((0, 1, 0)))
    if front is not None:
        mouth.append([mouth[0][0], front, mouth[1][0]])

    def carve(co, n):
        d = n * 0.01 * noise.noise(co * 8.0)
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.05, 0.1))
        if (co - HEAD).length < 1.0:
            d -= n * 0.02 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.008, 0.028))
            for nn in nostrils:
                d -= n * 0.02 * (1 - smooth((co - nn).length, 0.012, 0.03))
        if co.z < 0.12:                                                       # toe grooves
            for fx, fy in ((0.84, -0.95), (0.86, 0.78)):
                for sx in (-1, 1):
                    for dx in (-0.06, 0.0, 0.06):
                        if abs(co.x - sx * (fx + dx)) < 0.02 and (co.y - fy) < -0.12:
                            d -= n * 0.02 * (1 - smooth(abs(co.x - sx * (fx + dx)), 0.004, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6800, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.3, 0))).length, 0.35, 0.65)), factor=1.0)

    def colour(co, n, g=0.0):
        col = mix(COL["rust"], COL["rust_lt"], 0.4 * smooth(n.z, 0.2, 0.9))
        band = 0.5 + 0.5 * math.sin(co.y * 8.5 + 0.6 * math.sin(co.x * 5))           # dark saddle bands across the back
        col = mix(col, COL["band"], 0.85 * smooth(band, 0.55, 0.8) * smooth(n.z, 0.1, 0.6) * smooth(co.y, -1.1, -0.8))
        col = mix(col, COL["deep"], 0.25 * smooth(noise.noise(co * 3.0), 0.2, 0.6))
        belly = smooth(-n.z, -0.1, 0.5) * smooth(co.z, 0.6, 0.35)
        col = mix(col, mix(COL["belly"], COL["belly_dk"], 0.3 * smooth(co.z, 0.4, 0.1)), belly)
        if (co - HEAD).length < 1.0:
            col = mix(col, COL["mouth"], 1 - smooth(min(poly_dist(co, m) for m in mouth), 0.008, 0.016))
            for nn in nostrils:
                col = mix(col, COL["mouth"], 1 - smooth((co - nn).length, 0.015, 0.025))
        return col
    add("skin", skin, scale_m, colour, lambda co, n, g: 0.78 + 0.1 * smooth(-n.z, 0.0, 0.6))

    # ---- calm amber eyes under heavy lids ------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.08, 0.08, 0.05), cuts=3), e - en * 0.012, en), eye_m)
        add("pupil", facing(ell((0, 0, 0), (0.036, 0.04, 0.012), cuts=2), e + en * 0.034, en), bone_m, COL["pupil"], 0.2)
        up = R @ Vector((0, 0, 1))
        add("pupil", ell(e + en * 0.04 + up * 0.025, (0.012, 0.012, 0.01), cuts=1), bone_m, COL["white"], 0.2)
        lid = ell((0, 0, 0), (0.095, 0.095, 0.065), cuts=3)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < -0.012], context='VERTS')     # the top half of a shell
        side = up.cross(en).normalized()
        upv = en.cross(side).normalized()
        mtx = Matrix((side, upv, en)).transposed()
        lid.transform(Matrix.Translation(e - en * 0.012) @ mtx.to_4x4() @ M(rot=(-16, 0, 0)))
        add("lids", lid, scale_m, lambda co, n, g: mix(COL["rust"], COL["band"], 0.3), 0.8)

    # ---- claws ------------------------------------------------------------------------------------------
    for fx, fy in ((0.84, -0.95), (0.86, 0.78)):
        for sx in (-1, 1):
            for k, dx in enumerate((-0.09, -0.03, 0.03, 0.09)):
                base, _ = hit(Vector((sx * (fx + dx), fy - 0.6, 0.05)), Vector((0, 1, 0)))
                if base is None:
                    continue
                cl = lathe([(0.028, 0.0), (0.02, 0.04), (0.0, 0.09)], segs=6)
                cl.transform(Matrix.Translation(base - Vector((0, -0.01, 0))) @ Vector((0, -1, -0.5)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
                add("claws", cl, bone_m, lambda co, n, g: mix(COL["claw_dk"], COL["claw"], smooth(g, 0.0, 0.7)), 0.5)

    # ---- the sail: bone ribs with a sunset-striped membrane between them -----------------------------
    y0, y1, top = SAIL
    n_ribs = 11
    per = 4
    cols = (n_ribs - 1) * per + 1
    rows = 9

    def base_z(y):
        p, _ = hit(Vector((0, y, 3.0)), Vector((0, 0, -1)))
        return p.z - 0.06

    def height(u):
        return top * math.sin(math.pi * min(max(u, 0.0), 1.0) ** 0.9) ** 0.75 + 0.06

    ribs = []
    grid = []
    for j in range(cols):
        u = j / (cols - 1)
        y = lerp(y0, y1, u)
        frac = (j % per) / per
        h = height(u) * (1 - 0.07 * math.sin(math.pi * frac))                 # the edge dips between the ribs
        bz = base_z(y)
        grid.append([(Vector((0, y + 0.12 * v * h, bz + v * h)), v) for v in (i / (rows - 1) for i in range(rows))])
        if j % per == 0:
            ribs.append((Vector((0, y, bz)), Vector((0, y + 0.12 * h, bz + h)) + Vector((0, 0.01, 0.05))))
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    sheets = []
    for side in (1, -1):
        sheet = []
        for j, column in enumerate(grid):
            ring = []
            for p, v in column:
                vv = bm.verts.new(p + Vector((side * 0.022 * (1 - 0.6 * v), 0, 0)))
                vv[lg] = v
                ring.append(vv)
            sheet.append(ring)
        sheets.append(sheet)
    a, b = sheets
    for j in range(cols - 1):
        for i in range(rows - 1):
            bm.faces.new((a[j][i], a[j + 1][i], a[j + 1][i + 1], a[j][i + 1]))
            bm.faces.new((b[j][i + 1], b[j + 1][i + 1], b[j + 1][i], b[j][i]))
        bm.faces.new((a[j][-1], a[j + 1][-1], b[j + 1][-1], b[j][-1]))         # the top rim
    for j in (0, cols - 1):
        for i in range(rows - 1):
            bm.faces.new((a[j][i], a[j][i + 1], b[j][i + 1], b[j][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    def sail_col(co, n, g):
        v = g + 0.035 * math.sin(co.y * 9.0)
        col = mix(COL["s0"], COL["s1"], smooth(v, 0.18, 0.38))
        col = mix(col, COL["s2"], smooth(v, 0.42, 0.6))
        col = mix(col, COL["s3"], smooth(v, 0.66, 0.84))
        col = mix(col, COL["s_rim"], smooth(g, 0.93, 0.995))
        rib_d = min(abs(co.y - 0.12 * g * 1.5 - r[0].y) for r in ribs)
        return mix(col, COL["s0"], 0.25 * (1 - smooth(rib_d, 0.0, 0.07)))
    add("sail", bm, sail_m, sail_col, lambda co, n, g: 0.72 - 0.1 * g)
    for r0, r1 in ribs:
        rib = loft([r0, r0 + (r1 - r0) * 0.5 + Vector((0, 0.01, 0)), r1], lambda t: lerp(0.045, 0.022, t), segs=7, rings=7)
        add("ribs", rib, bone_m, lambda co, n, g: mix(COL["rib"], COL["rib_tip"], smooth(g, 0.55, 1.0)), 0.6)

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
