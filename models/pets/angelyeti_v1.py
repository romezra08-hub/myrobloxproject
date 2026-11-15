"""AngelYeti pet: a fluffy white yeti cub with feathered angel wings and a glowing halo-crown, remade from the
game's stiff white ape with a gold crown and white feather wings. Built from scratch by script.

    python models/pets/angelyeti.py --review out/angelyeti.png      # render the review sheet
    python models/pets/angelyeti.py --export models/export/angelyeti.fbx

Must-haves, checked in every review:
  1. The same pet: a white ape standing upright with white feather wings raised behind it and a gold crown.
  2. A fluffy cub, not a stiff ape: a big head, a pear body, short legs, long arms, chunky fur clumps.
  3. Pale blue bare skin on the face, hands and soles; a kind face with gentle dark eyes and a small smile.
  4. Soft layered feather wings (primaries, secondaries and a row of coverts), painted shafts and tips.
  5. A small gold halo-crown floating over the head (GLOW).
  6. Matte painted fur with crease shading; about 3-3.5 studs tall; Body under 12k triangles.

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

# ---- the angel yeti cub ---------------------------------------------------------------------------

NAME = "AngelYeti"
COL = {"fur": hexc("#F6F6F2"), "shade": hexc("#D3DCE8"), "deep": hexc("#AEBACB"), "skin": hexc("#A9C6E2"),
       "skin_dk": hexc("#7E9EC4"), "skin_lt": hexc("#C6DBEE"), "nose": hexc("#2E3A56"), "mouth": hexc("#3A3E60"),
       "white": hexc("#FFFFFF"), "feather": hexc("#FBFAF6"), "feather_sh": hexc("#D9E0EA"), "feather_tip": hexc("#C3CFE0"),
       "shaft": hexc("#CFC8BA")}
SCALE = 1.0
BAKE = {"shade": 0.45, "rough": 0.9}
GRAIN = [("noise", 30.0, 0.05)]
HEAD = Vector((0, -0.18, 2.28))
HEAD_M = M(HEAD, rot=(-5, 0, 0))
FACE = Vector((0, -0.75, 2.2)) * SCALE
FOCUS = FACE
FACE_DIST = 4.8


def leaf(length, width, thick=0.025, cuts=2):
    """A flat feather along +Z from the origin, widest a third of the way, round at the root, pointed at the tip."""
    bm = kit.ball((2, 2, 2), cuts=cuts)
    for v in bm.verts:
        t = (v.co.z + 1) / 2                                   # 0 root .. 1 tip
        w = width * (math.sin(math.pi * min(t * 1.5, 1.0) * 0.5) ** 0.6) * (1 - t ** 3) ** 0.7 + 0.004
        v.co = Vector((v.co.x * w, v.co.y * thick * (1 - 0.6 * t), t * length))
    return bm


def build():
    fur_m = painted("Fur", dict(strength=0.34, mottle=0.1, fine=34.0, length=5.0), rough=0.95)
    skin_m = grained("Skin", [("noise", 24.0, 0.06), ("cells", 60.0, 0.03)], rough=0.6)
    feather_m = grained("Feather", [("streak", 90.0, 0.06), ("noise", 12.0, 0.03)], rough=0.8)
    eye_m = kit.material("Eyes", "#1A2030", rough=0.06)
    glow = kit.material("GLOW_Halo", "#FFD36A", rough=0.4, emit=2.5)
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

    def face_mask(co):
        """0..1: the bare pale-blue face (two lobes round the eyes and the muzzle), in head space."""
        p = HINV @ co
        if p.y > -0.12:
            return 0.0
        m = 0.0
        for s in (-1, 1):
            m = max(m, 1 - smooth(((p.x - 0.16 * s) / 0.165) ** 2 + ((p.z - 0.07) / 0.15) ** 2, 0.8, 1.05))
        m = max(m, 1 - smooth((p.x / 0.27) ** 2 + ((p.z + 0.14) / 0.19) ** 2, 0.8, 1.05))
        return m

    def tuft(at, d, length=0.14, r=0.06):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.035))], lambda t: r * (1 - t) ** 0.9 + 0.006, segs=8, rings=5)

    def fluff(c0, rad, rows, per, length, r, droop=0.7, skip=None, seed=0.0):
        """Rows of fur clumps round an ellipsoid, pointing out and down."""
        out = []
        c0 = Vector(c0)
        for i, lat in enumerate(rows):
            for k in range(per):
                a = 2 * math.pi * (k + 0.5 * (i % 2)) / per + seed
                dirn = Vector((math.cos(a) * math.cos(lat), math.sin(a) * math.cos(lat), math.sin(lat)))
                at = c0 + Vector((dirn.x * rad[0], dirn.y * rad[1], dirn.z * rad[2])) * 0.93
                if skip and skip(at):
                    continue
                jit = 0.2 * noise.noise(at * 7.0)
                out.append(tuft(at, dirn + Vector((0, 0, -droop - jit)), length=length * (1 + jit), r=r))
        return out

    # ---- one fused skin: pear body, short legs, long arms, big head, fur clumps ----------------------------
    clay = [ell((0, 0.02, 1.2), (0.68, 0.58, 0.72)),
            ell((0, -0.1, 1.72), (0.6, 0.5, 0.42)),                             # chest and shoulders
            ell(hd((0, 0, 0)), (0.55, 0.5, 0.52)),
            ell(hd((0, -0.36, -0.15)), (0.25, 0.19, 0.17)),                     # muzzle
            ell(hd((0, -0.3, 0.12)), (0.36, 0.16, 0.1))]                        # brow ridge
    for s in (-1, 1):
        clay += [ell(hd((0.16 * s, -0.38, 0.03)), (0.13, 0.08, 0.11)),           # eye beds
                 ell((0.3 * s, -0.04, 0.42), (0.27, 0.3, 0.4)),                  # legs
                 ell((0.32 * s, -0.17, 0.1), (0.24, 0.33, 0.11)),                # feet
                 loft([(0.6 * s, -0.05, 1.78), (0.82 * s, -0.1, 1.25), (0.8 * s, -0.26, 0.78)], lambda t: lerp(0.25, 0.2, t), segs=12, rings=8),
                 ell((0.8 * s, -0.3, 0.6), (0.2, 0.21, 0.2)),                   # hands
                 ell(hd((0.45 * s, 0.0, 0.32)), (0.12, 0.1, 0.14))]              # little round ears
    def not_face(at):
        return face_mask(at) > 0.01 or (HINV @ at).y < -0.3
    clay += fluff(HEAD, (0.55, 0.5, 0.52), (0.85, 0.45, 0.05, -0.35), 10, 0.16, 0.075, skip=not_face)
    clay += fluff((0, 0.02, 1.25), (0.68, 0.58, 0.72), (0.75, 0.35, -0.05, -0.45), 12, 0.17, 0.085, seed=0.3)
    for s in (-1, 1):
        for k in range(6):                                                   # arm clumps
            t = k / 5
            at = Vector((lerp(0.72, 0.98, smooth(t, 0, 0.4)) * s - 0.1 * s * t, lerp(-0.05, -0.28, t), lerp(1.75, 0.8, t)))
            clay.append(tuft(at, (s * 0.8, -0.2, -0.9), length=0.16, r=0.085))
            clay.append(tuft(at + Vector((0, 0.16, 0.05)), (s * 0.5, 0.6, -0.9), length=0.15, r=0.08))
        for k in range(4):                                                   # leg clumps
            a = -0.6 + 0.55 * k
            at = Vector((0.3 * s + 0.27 * math.cos(a) * s, -0.04 - 0.27 * math.sin(a), 0.45))
            clay.append(tuft(at, (math.cos(a) * s, -math.sin(a), -1.2), length=0.15, r=0.08))
        for k in range(3):                                                   # cheek ruffs framing the face
            clay.append(tuft(hd((0.36 * s, -0.24 + 0.08 * k, -0.18 - 0.06 * k)), R @ Vector((s, -0.2, -0.7)), length=0.16, r=0.07))
    clay.append(tuft(hd((0.0, -0.12, 0.5)), R @ Vector((0.2, -0.6, 0.7)), length=0.2, r=0.07))          # a cowlick
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.16 * s, -1.5, 0.04)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.08)), fwd)
    smile = [hit(hd((x, -1.5, -0.22 + 1.6 * x * x)), fwd)[0] for x in (-0.12, -0.08, -0.04, 0.0, 0.04, 0.08, 0.12)]
    philtrum = [hit(hd((0, -1.5, -0.12)), fwd)[0], hit(hd((0, -1.5, -0.21)), fwd)[0]]

    def carve(co, n):
        d = n * 0.014 * noise.noise(Vector((co.x * 9, co.y * 9, co.z * 2.5)))
        fm = face_mask(co)
        d *= 1 - fm
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.06, 0.11))
        if fm > 0:
            d -= n * 0.016 * (1 - smooth(min(poly_dist(co, smile), poly_dist(co, philtrum)), 0.006, 0.022))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.35, -0.05))).length, 0.25, 0.45)),
                                                    0.4 * (1 - smooth((Vector(co) - HEAD).length, 0.45, 0.65))), factor=1.0)

    def is_bare(co):
        hand = smooth((co - Vector((0.8 * (1 if co.x > 0 else -1), -0.32, 0.56))).length, 0.2, 0.15) * smooth(co.z, 0.7, 0.62)
        sole = smooth(co.z, 0.12, 0.06) * smooth(co.y, -0.25, -0.4)
        return max(face_mask(co), hand, sole)

    def colour(co, n, g=0.0):
        col = mix(COL["shade"], COL["fur"], smooth(n.z, -0.5, 0.45))
        col = mix(col, COL["deep"], 0.4 * smooth(co.z, 0.35, 0.05))
        col = mix(col, COL["shade"], 0.3 * smooth(noise.noise(Vector((co.x * 6, co.y * 6, co.z * 1.6))), 0.15, 0.55))
        b = is_bare(co)
        if b > 0:
            sk = mix(COL["skin_dk"], COL["skin"], smooth(n.z, -0.6, 0.3))
            sk = mix(sk, COL["skin_lt"], 0.5 * smooth(n.z, 0.4, 0.9))
            if (co - nose_at).length < 0.4:
                sk = mix(sk, COL["mouth"], 1 - smooth(min(poly_dist(co, smile), poly_dist(co, philtrum)), 0.006, 0.014))
            col = mix(col, sk, b)
        return col

    def rough(co, n, g=0.0):
        return lerp(0.92, 0.55, is_bare(co))
    paint(skin, colour)
    bare_f, fur_f = kit.split(skin, lambda f: is_bare(f.calc_center_median()) > 0.5)
    add("skin", fur_f, fur_m, None, rough)
    add("skin", bare_f, skin_m, None, rough)

    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.07, 0.08, 0.042), cuts=3), e - en * 0.016, en), eye_m)
        add("glints", ell(e + en * 0.024 + R @ Vector((-0.024, 0, 0.028)), (0.021, 0.015, 0.021), cuts=1), skin_m, COL["white"], 0.3)
        add("glints", ell(e + en * 0.026 + R @ Vector((0.02, 0, -0.026)), (0.009, 0.007, 0.009), cuts=1), skin_m, COL["white"], 0.3)
    nose = ell((0, 0, 0), (0.075, 0.05, 0.05), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.65 + 0.4 * smooth(v.co.z, -0.05, 0.05)
    nose.transform(M(nose_at) @ R.to_4x4())
    add("nose", nose, skin_m, lambda co, n, g: mix(COL["nose"], COL["skin_dk"], 0.4 * smooth(n.z, 0.3, 0.9)), 0.4)

    # ---- feathered angel wings, raised behind the shoulders --------------------------------------------
    for s in (-1, 1):
        root = Vector((0.24 * s, 0.42, 1.78))
        U = Vector((s * 1.0, 0.55, 0.1)).normalized()
        V = Vector((0, 0.3, 1.0)).normalized()
        N = U.cross(V).normalized() * s
        edge = [Vector((0, 0)), Vector((0.45, 0.32)), Vector((0.78, 0.78)), Vector((0.95, 1.2))]

        def at(t):
            return kit._spline(edge, t * (len(edge) - 1))

        def to3(p, lift=0.0):
            return root + U * p.x + V * p.y + N * lift

        def feather(t, ang, length, width, lift, row):
            base = at(t)
            d2 = Vector((math.cos(ang), math.sin(ang)))
            dirn = (U * d2.x + V * d2.y).normalized()
            side = dirn.cross(N).normalized()
            bm = leaf(length, width)

            def fcol(co, n, g, row=row, length=length):
                tt = co.z / length
                col = mix(COL["feather"], COL["feather_sh"], 0.45 * smooth(tt, 0.2, 1.0) + 0.2 * row)
                col = mix(col, COL["feather_tip"], 0.35 * smooth(tt, 0.75, 1.0))
                return mix(col, COL["shaft"], 0.6 * (1 - smooth(abs(co.x), 0.004, 0.012)) * smooth(tt, 0.05, 0.15) * smooth(tt, 0.95, 0.7))
            paint(bm, fcol)
            roughen(bm, lambda co, n, g: 0.82)
            mtx = Matrix((side, N, dirn)).transposed()
            bm.transform(Matrix.Translation(to3(base, lift)) @ mtx.to_4x4())
            add("wings", bm, feather_m)

        n_pr, n_sec = 7, 6
        for i in range(n_pr):                                                # primaries off the hand, fanning up and out
            t = 0.62 + 0.38 * i / (n_pr - 1)
            ang = math.radians(lerp(-10, 72, i / (n_pr - 1)))
            feather(t, ang, lerp(0.75, 0.95, math.sin(math.pi * i / (n_pr - 1) * 0.8)), 0.1, -0.012 * i, 0)
        for i in range(n_sec):                                               # secondaries along the forearm, hanging down and out
            t = 0.08 + 0.52 * i / (n_sec - 1)
            ang = math.radians(lerp(-80, -25, i / (n_sec - 1)))
            feather(t, ang, lerp(0.58, 0.72, i / (n_sec - 1)), 0.1, 0.02 - 0.004 * i, 0)
        for i in range(8):                                                   # coverts: a row of short soft feathers on top
            t = 0.04 + 0.9 * i / 7
            ang = math.radians(lerp(-75, 40, i / 7))
            feather(t, ang, lerp(0.3, 0.4, i / 7), 0.085, 0.05, 1)
        bone = loft([to3(at(t), 0.03) for t in (0.0, 0.33, 0.66, 1.0)], lambda t: lerp(0.08, 0.04, t), segs=8, rings=12)
        add("wings", bone, fur_m, lambda co, n, g: mix(COL["shade"], COL["fur"], smooth(n.z, -0.4, 0.5)), 0.9)

    # ---- a small glowing halo-crown -------------------------------------------------------------------
    HALO = M(hd((0, 0.06, 0.74)), rot=(-14, 0, 0))
    ring = lathe([(0.3 + 0.03 * math.cos(t), 0.03 * math.sin(t)) for t in (2 * math.pi * j / 8 for j in range(8))], segs=32, closed=True)
    ring.transform(HALO)
    roughen(ring, lambda co, n, g: 0.4)
    c.add(ring, glow)
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        pt = lathe([(0.03, 0.0), (0.022, 0.06), (0.0, 0.13)], segs=6)
        pt.transform(HALO @ M((0.3 * math.cos(a), 0.3 * math.sin(a), 0.01)))
        roughen(pt, lambda co, n, g: 0.4)
        c.add(pt, glow)
        pt = ell((0, 0, 0), (0.024, 0.024, 0.024), cuts=1)
        pt.transform(HALO @ M((0.3 * math.cos(a), 0.3 * math.sin(a), 0.14)))
        roughen(pt, lambda co, n, g: 0.4)
        c.add(pt, glow)

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
