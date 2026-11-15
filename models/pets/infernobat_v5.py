"""InfernoBat pet: a fierce-but-cute fire bat, remade from the game's original. Built from scratch by script.

    python models/pets/infernobat.py --review out/infernobat.png      # render the review sheet
    python models/pets/infernobat.py --export models/export/infernobat.fbx

The original is a dark-red round bat with a human-like devil face and big red-orange flame wings;
the face made it creepy. The remake keeps the dark-red round body, the horn points and the flame
wings, and gives it a proper bat head. Must-haves, checked in every review:
  1. A bat head: big pointed ears with cupped orange insides, a short snout with a small dark nose.
  2. Calm glowing amber eyes without pupils under a soft brow; a small closed mouth with one tiny fang.
  3. Fluffy dark crimson fur: tufts on the crown, cheeks, chest ruff and shoulders.
  4. The same red wings, raised in a V, fading to flame-orange tips with a glowing ember edge.
  5. Small horn nubs; little clawed feet on the ground; matte painted texture with crease shading.

Round 5: the head was smooth clay up close: fluff at the inner base of each ear and short tufts on
the forehead and the back of the head; a narrower unwrap angle so the bake cannot fold pieces of
the texture over each other.

Round 4: a narrower, longer fox-bat snout instead of a wide teddy muzzle, with a raised dark nose
pad and nostrils; tufts warm to a brighter red at their ends so the fur reads fluffy, not shaggy
brown; the body keeps little specular sheen (fur is matte in Roblox too).

Round 3: amber eyes that read amber, not lemon (deeper colour, less glow); more saturated crimson;
the crown tufts swept back into a soft cowlick instead of a spiky crest; a soft brow fluff over
each eye and lighter eye rims (the dark sockets read as a mask).

Round 2: Body was 12.8k triangles: fewer wing and bone segments, a lighter skin. The eyes were big
yellow slits tilted like a frown: smaller amber almonds sitting level under a flat calm lid. Deeper,
redder crimson fur (it read brown-pink), a lighter muzzle so the small mouth shows, a shorter fang.

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
from mathutils import Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402

NAME = "InfernoBat"


# ---- helpers: fused clay forms, sculpting and vertex paint -------------------------------------

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


def join(bms):
    out = bmesh.new()
    for b in bms:
        tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(tmp)
        b.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return out


def fuse(bms, voxel=0.022, factor=0.5, iterations=4):
    """Melt overlapping closed shapes into one skin (a voxel remesh), softened a little at the joins."""
    ob = _object(join(bms), "fuse")
    r = ob.modifiers.new("r", 'REMESH')
    r.mode, r.voxel_size, r.adaptivity = 'VOXEL', voxel, 0.0
    if iterations:
        s = ob.modifiers.new("s", 'SMOOTH')
        s.factor, s.iterations = factor, iterations
    return _evaluated(ob)


def decimate(bm, target):
    """Bring a dense skin down to about `target` triangles."""
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    ob = _object(bm, "dec")
    bm.free()
    if tris > target:
        d = ob.modifiers.new("d", 'DECIMATE')
        d.ratio = target / tris
        d.use_collapse_triangulate = True
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


def paint(bm, fn):
    """Give every vertex the colour fn(co, normal) -> (r, g, b) linear, in the attribute 'col'."""
    bm.normal_update()
    lay = bm.verts.layers.float_color.get("col") or bm.verts.layers.float_color.new("col")
    for v in bm.verts:
        v[lay] = (*fn(v.co, v.normal), 1.0)
    return bm


def flat_paint(bm, rgb):
    return paint(bm, lambda co, n: rgb)


def ray(bm):
    return BVHTree.FromBMesh(bm)


def hit(tree, origin, direction):
    loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
    return loc, nrm


def ell(c, r, rot=(0, 0, 0), cuts=5):
    """An ellipsoid with radii r (kit.ball takes the full size)."""
    bm = kit.ball(tuple(2 * x for x in r), cuts=cuts)
    bm.transform(M(c, rot=rot))
    return bm


def on_ell(c, r, az, el):
    """A point and the outward normal on an ellipsoid; az from -Y (front) towards +X, el up, degrees."""
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    p = Vector(c) + Vector((d.x * r[0], d.y * r[1], d.z * r[2]))
    n = Vector((d.x / r[0], d.y / r[1], d.z / r[2])).normalized()
    return p, n


def tuft(root, direction, length, radius, droop=0.0, segs=8):
    d = Vector(direction).normalized()
    r0 = Vector(root) - d * radius * 0.6
    mid = Vector(root) + d * length * 0.5 + Vector((0, 0, -droop * 0.4))
    tip = Vector(root) + d * length + Vector((0, 0, -droop))
    return kit.tube([r0, mid, tip], [radius, radius * 0.62, 0.008], segs=segs, rings=6)


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length, t


def poly_dist(p, pts):
    return min(seg_dist(p, a, b)[0] for a, b in zip(pts, pts[1:]))


def sheet(grid, thick, layer_fn=None):
    """A thin closed sheet from a grid of points (rows of equal length): two skins `thick` apart,
    stitched round the edge. layer_fn(i, j) gives each vertex a float 'g' (for the material)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    R, C = len(grid), len(grid[0])
    P = [[Vector(p) for p in row] for row in grid]

    def normal(i, j):
        du = P[min(i + 1, R - 1)][j] - P[max(i - 1, 0)][j]
        dv = P[i][min(j + 1, C - 1)] - P[i][max(j - 1, 0)]
        n = du.cross(dv)
        return n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))
    top, bot = [], []
    for i in range(R):
        tr, br = [], []
        for j in range(C):
            n = normal(i, j)
            edge = i in (0, R - 1) or j in (0, C - 1)
            h = thick * (0.35 if edge else 0.5)
            a, b = bm.verts.new(P[i][j] + n * h), bm.verts.new(P[i][j] - n * h)
            if layer_fn:
                a[lg] = b[lg] = layer_fn(i, j)
            tr.append(a)
            br.append(b)
        top.append(tr)
        bot.append(br)
    for i in range(R - 1):
        for j in range(C - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    ring = [(0, j) for j in range(C)] + [(i, C - 1) for i in range(1, R)] + \
           [(R - 1, j) for j in range(C - 2, -1, -1)] + [(i, 0) for i in range(R - 2, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((top[i0][j0], bot[i0][j0], bot[i1][j1], top[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def mirror_x(bm):
    """A copy of the shape mirrored across x=0 (normals fixed)."""
    m = bm.copy()
    m.transform(M(scale=(-1, 1, 1)))
    bmesh.ops.reverse_faces(m, faces=m.faces[:])
    return m


# ---- materials ----------------------------------------------------------------------------------

def _ops(tree):
    new, link = tree.nodes.new, tree.links.new

    def op(kind, a, b=None, c=None):
        m = new("ShaderNodeMath")
        m.operation = kind
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[k].default_value = v
            else:
                link(v, m.inputs[k])
        return m.outputs[0]

    def ramp(src, stops):
        rp = new("ShaderNodeValToRGB")
        els = rp.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*hexc(stops[0][1]), 1.0)
        els[1].position, els[1].color = stops[-1][0], (*hexc(stops[-1][1]), 1.0)
        for pos, h in stops[1:-1]:
            e = els.new(pos)
            e.color = (*hexc(h), 1.0)
        link(src, rp.inputs["Fac"])
        return rp.outputs["Color"]

    def attr(name, out="Fac"):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs[out]
    return new, link, op, ramp, attr


def painted(name, streak, rough=0.9):
    """Fur or hide: the vertex paint 'col' under kit.furry's fine streaks and mottling."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, **streak)
    new, link, op, ramp, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col", "Color"), hsv.inputs["Color"])
    return m


def membrane_material(name, stops, rough=0.8):
    """Wing skin: a colour ramp along the wing (g: 0 at the arm, 1 at the edge), its border broken
    into flame tongues by noise, with faint darker veins running out along the fingers."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, strength=0.06, mottle=0.08, fine=14.0, length=3.0)
    tree = m.node_tree
    new, link, op, ramp, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    coord = new("ShaderNodeTexCoord")
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 2.6, 3.0
    link(coord.outputs["Object"], nz.inputs["Vector"])
    g = op('MULTIPLY_ADD', op('SUBTRACT', nz.outputs[0], 0.5), 0.34, attr("g"))
    link(ramp(g, stops), hsv.inputs["Color"])
    return m


# ---- the bat ------------------------------------------------------------------------------------

BODY_C, BODY_R = (0, 0.04, 1.12), (0.74, 0.66, 0.8)
HEAD_C, HEAD_R = (0, -0.1, 2.22), (0.68, 0.6, 0.58)
SNOUT_C, SNOUT_R = (0, -0.64, 2.07), (0.24, 0.3, 0.19)
EYE_X, EYE_Z = 0.27, 2.31
FUR = {
    "back": hexc("#2E030A"), "fur": hexc("#560610"), "chest": hexc("#780B16"), "tip": hexc("#94141C"),
    "muzzle": hexc("#3A0A10"), "nose": hexc("#150608"), "line": hexc("#100405"), "ear_in": hexc("#C2341C"),
    "ear_deep": hexc("#FF7A26"), "rim": hexc("#2A040A"),
}
WING_STOPS = [(0.0, "#5E0B10"), (0.22, "#9A1216"), (0.48, "#D0241A"), (0.7, "#F25A1C"), (0.86, "#FF8E2A"),
              (1.0, "#FFB648")]


def ear_frame(side):
    base = Vector((0.36 * side, -0.02, 2.6))
    tipp = Vector((0.86 * side, 0.08, 3.5))
    a = (tipp - base).normalized()
    f = Vector((0.32 * side, -1.0, 0.18))
    f = (f - a * f.dot(a)).normalized()
    s = a.cross(f)
    return base, tipp, a, f, s


def build():
    fur_m = painted("Fur", dict(strength=0.42, mottle=0.14, fine=18.0, length=5.0), rough=0.92)
    horn_m = painted("Horn", dict(strength=0.12, mottle=0.08, fine=30.0, length=2.0), rough=0.6)
    bone_m = painted("Bone", dict(strength=0.2, mottle=0.08, fine=26.0, length=6.0), rough=0.8)
    wing_m = membrane_material("Membrane", WING_STOPS)
    glow_m = kit.material("GLOW_Ember", "#FF7E14", rough=0.4, emit=1.5)
    bat = Prop(NAME)
    bat.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        bat.tally[part] = bat.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        bat.add(bm, mat)

    # ---- the clay: body, head, snout, ears, fluff, legs, melted into one skin -------------------
    clay = [ell(BODY_C, BODY_R), ell(HEAD_C, HEAD_R), ell(SNOUT_C, SNOUT_R),
            ell((0, -0.56, 1.95), (0.2, 0.2, 0.1)),                      # chin
            ell((0, -0.32, 1.72), (0.44, 0.34, 0.3))]                     # throat into chest
    for s in (-1, 1):
        clay.append(ell((0.4 * s, -0.4, 2.02), (0.22, 0.2, 0.2)))        # cheeks
        clay.append(ell((0.17 * s, -0.6, 2.2), (0.12, 0.16, 0.1), rot=(0, 0, 0)))   # top of the snout, beside the bridge
        base, tipp, a, f, sd = ear_frame(s)
        L = (tipp - base).length
        pts = [base - a * 0.15, base + a * L * 0.35 + sd * 0.04 * s, base + a * L * 0.75, tipp]
        clay.append(kit.tube(pts, [0.27, 0.27, 0.15, 0.02], segs=14, rings=16, flat=0.42))
        # legs and feet
        clay.append(kit.tube([(0.32 * s, -0.02, 0.6), (0.34 * s, -0.08, 0.3), (0.36 * s, -0.16, 0.1)], [0.17, 0.13, 0.12], segs=10))
        clay.append(ell((0.37 * s, -0.24, 0.08), (0.15, 0.2, 0.08)))
        # wing roots on the shoulders
        clay.append(ell((0.62 * s, 0.12, 1.62), (0.2, 0.22, 0.26)))
    # fluff: crown, cheeks, chest ruff, shoulders, flanks
    rnd = 0.0
    for az, el, L in ((-10, 66, 0.2), (12, 70, 0.22), (0, 78, 0.18)):
        p, n = on_ell(HEAD_C, HEAD_R, az, el)
        clay.append(tuft(p, n * 0.4 + Vector((0.15 * (1 if az > 0 else -1), 1.0, 0.25)), L, 0.09, droop=0.05))
    for s in (-1, 1):
        # fluff at the inner base of the ear, and short tufts on the forehead and the back of the head
        base, tipp, a, f, sd = ear_frame(s)
        for k, (t, off) in enumerate(((0.12, -0.08), (0.2, 0.06))):
            root = base + a * (tipp - base).length * t + f * 0.02 + sd * off * s
            clay.append(tuft(root, a * 0.9 + f * 0.5 - sd * 0.2 * s, 0.2, 0.06, droop=0.0, segs=6))
        for az, el in ((14, 46), (34, 52), (150, 40), (125, 20), (165, 10)):
            p, n = on_ell(HEAD_C, HEAD_R, az * s, el)
            clay.append(tuft(p - n * 0.03, n * 0.5 + Vector((0, 0.8, 0.1 if az < 90 else -0.6)), 0.15, 0.06, droop=0.02, segs=6))
        # a soft fluff over each eye: the brow
        p, n = on_ell(HEAD_C, HEAD_R, 24 * s, 24)
        clay.append(tuft(p - n * 0.04, Vector((0.6 * s, -0.25, 0.35)), 0.15, 0.065, droop=0.0))
    for s in (-1, 1):
        for az, el, L in ((62, -18, 0.24), (74, -2, 0.22), (70, -32, 0.2)):
            p, n = on_ell(HEAD_C, HEAD_R, az * s, el)
            clay.append(tuft(p, n + Vector((0, 0.45, -0.35)), L, 0.09, droop=0.06))
    for k, (az, el, L) in enumerate([(a, e, l) for a, e, l in
                                     ((-50, 34, 0.26), (-30, 30, 0.3), (-10, 28, 0.32), (10, 29, 0.31), (30, 31, 0.29), (50, 35, 0.25),
                                      (-40, 14, 0.27), (-20, 11, 0.3), (0, 9, 0.31), (20, 12, 0.29), (40, 15, 0.26),
                                      (-28, -8, 0.22), (-6, -10, 0.24), (16, -9, 0.23), (36, -6, 0.2))]):
        rnd = noise.noise(Vector((k * 1.7, 0.3, 0.1)))
        p, n = on_ell(BODY_C, BODY_R, az + rnd * 6, el)
        clay.append(tuft(p, n + Vector((0, 0, -1.5)), L * (1 + 0.2 * rnd), 0.1, droop=0.04))
    for s in (-1, 1):
        for az, el, L in ((80, 30, 0.24), (96, 10, 0.24), (112, -12, 0.22), (130, 22, 0.22), (150, -2, 0.2)):
            p, n = on_ell(BODY_C, BODY_R, az * s, el)
            clay.append(tuft(p, n + Vector((0, 0.3, -1.2)), L, 0.1, droop=0.04))
    skin = fuse(clay, voxel=0.021, factor=0.5, iterations=4)
    tree = ray(skin)

    # ---- sculpt the face into the skin -------------------------------------------------------------
    eyes = []
    for s in (-1, 1):
        p, n = hit(tree, (EYE_X * s, -3, EYE_Z), (0, 1, 0))
        eyes.append((p, n))
    nose_p, _ = hit(tree, (0, -3, 2.13), (0, 1, 0))
    mouth_y = hit(tree, (0, -3, 1.99), (0, 1, 0))[0].y
    frames = [ear_frame(s) for s in (-1, 1)]

    def carve(co, n):
        d = Vector()
        for (p, en), s in zip(eyes, (-1, 1)):
            q = co - p
            # an almond socket, its outer corner lifted a little
            ang = math.radians(-3 * s)
            x = q.x * math.cos(ang) + q.z * math.sin(ang)
            z = -q.x * math.sin(ang) + q.z * math.cos(ang)
            r = math.sqrt((x / 0.15) ** 2 + (z / 0.105) ** 2 + (q.y / 0.2) ** 2)
            d -= en * 0.07 * (1 - smooth(r, 0.55, 1.15))
            # a soft brow above it
            br = math.sqrt((x / 0.2) ** 2 + ((z - 0.13) / 0.06) ** 2 + (q.y / 0.25) ** 2)
            d += n * 0.035 * (1 - smooth(br, 0.4, 1.0))
        # a raised nose pad, wider at the top
        q = co - nose_p
        r = math.sqrt((q.x / (0.075 + 0.25 * max(q.z, -0.05))) ** 2 + (q.z / 0.05) ** 2 + (q.y / 0.08) ** 2)
        d += n * 0.025 * (1 - smooth(r, 0.6, 1.1))
        # nostrils
        for s in (-1, 1):
            r = (co - (nose_p + Vector((0.045 * s, 0.0, -0.01)))).length
            d -= n * 0.02 * (1 - smooth(r, 0.0, 0.03))
        # the mouth: a short soft line under the nose, the corners a touch up
        if n.y < -0.2 and co.y < mouth_y + 0.12:
            pts = [Vector((x, 0, 1.995 + 0.9 * x * x)) for x in (-0.13, -0.07, 0.0, 0.07, 0.13)]
            q = Vector((co.x, 0, co.z))
            dd = poly_dist(q, pts)
            d -= n * 0.03 * (1 - smooth(dd, 0.0, 0.03))
            # the short groove from the nose down to the mouth
            dd2, _ = seg_dist(q, Vector((0, 0, 2.08)), Vector((0, 0, 2.0)))
            d -= n * 0.012 * (1 - smooth(dd2, 0.0, 0.02))
        # cup the ears
        for base, tipp, a, f, sd in frames:
            q = co - base
            L = (tipp - base).length
            t = q.dot(a) / L
            if 0.12 < t < 1.0:
                w = 0.27 * (1 - t) ** 0.9 + 0.01
                u = q.dot(sd) / w
                v = q.dot(f)
                if v > 0 and abs(u) < 1.0:
                    mask = (1 - u * u) * smooth(t, 0.12, 0.3) * smooth(t, 0.98, 0.8)
                    d -= f * v * 0.85 * mask
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5600)

    forms = [(Vector(BODY_C), Vector(BODY_R)), (Vector(HEAD_C), Vector(HEAD_R))]

    def outside(co):
        best = 9.0
        for c0, r0 in forms:
            q = co - c0
            k = Vector((q.x / r0.x, q.y / r0.y, q.z / r0.z)).length
            best = min(best, (k - 1.0) * min(r0))
        return best

    def fur_colour(co, n):
        c = FUR["fur"]
        c = mix(c, FUR["back"], smooth(n.y, 0.0, 0.8) * 0.8 + smooth(n.z, 0.5, 1.0) * 0.25)
        chest = smooth(co.z, 0.5, 0.9) * smooth(co.z, 1.95, 1.7) * smooth(-n.y, 0.0, 0.6)
        c = mix(c, FUR["chest"], chest)
        c = mix(c, FUR["tip"], chest * smooth(co.z, 1.2, 1.6) * 0.5)
        # tufts brighten towards their ends
        tip = smooth(outside(co), 0.06, 0.24) * smooth(co.z, 0.3, 0.6)
        c = mix(c, FUR["tip"], tip * 0.75)
        # darker muzzle
        mz = 1 - smooth((Vector((co.x / 1.1, co.y, co.z)) - Vector(SNOUT_C)).length, 0.2, 0.32)
        c = mix(c, FUR["muzzle"], mz * 0.7)
        # nose pad
        q = co - nose_p
        r = math.sqrt((q.x / (0.075 + 0.25 * max(q.z, -0.05))) ** 2 + (q.z / 0.05) ** 2 + (q.y / 0.08) ** 2)
        c = mix(c, FUR["nose"], 1 - smooth(r, 0.85, 1.15))
        # mouth line
        if n.y < -0.2 and co.y < mouth_y + 0.12:
            pts = [Vector((x, 0, 1.995 + 0.9 * x * x)) for x in (-0.13, -0.07, 0.0, 0.07, 0.13)]
            dd = poly_dist(Vector((co.x, 0, co.z)), pts)
            c = mix(c, FUR["line"], 1 - smooth(dd, 0.012, 0.03))
        # eye rims
        for p, en in eyes:
            r = (co - p).length
            c = mix(c, FUR["rim"], (1 - smooth(r, 0.1, 0.15)) * 0.6)
        # inside the ears
        for base, tipp, a, f, sd in frames:
            q = co - base
            L = (tipp - base).length
            t = q.dot(a) / L
            if 0.1 < t < 1.0:
                w = 0.27 * (1 - t) ** 0.9 + 0.01
                u = abs(q.dot(sd) / w)
                if n.dot(f) > 0.15 and u < 0.8:
                    k = smooth(u, 0.78, 0.55) * smooth(t, 0.12, 0.26)
                    inner = mix(FUR["ear_in"], FUR["ear_deep"], smooth(t, 0.2, 0.6) * smooth(u, 0.6, 0.1))
                    c = mix(c, inner, k)
        # feet darker
        c = mix(c, FUR["back"], smooth(co.z, 0.25, 0.05) * 0.7)
        return c
    paint(skin, fur_colour)
    tree = ray(skin)
    add("skin", skin, fur_m)

    # ---- eyes, fang, horns, claws -----------------------------------------------------------------
    for (p0, _), s in zip(eyes, (-1, 1)):
        p, n = hit(tree, (EYE_X * s, -3, EYE_Z), (0, 1, 0))
        e = kit.ball((0.2, 0.09, 0.15), cuts=4)
        # a calm, slightly lowered lid: the top of the almond is flattened, level
        for v in e.verts:
            if v.co.z > 0.03:
                v.co.z = 0.03 + (v.co.z - 0.03) * 0.25
        ang = math.degrees(math.atan2(n.x, -n.y))
        e.transform(M(p - n * 0.014, rot=(0, -3 * s, ang)))
        add("eyes", e, glow_m)
    # one tiny fang on the left of the mouth
    fp, fn = hit(tree, (-0.075, -3, 1.995), (0, 1, 0))
    fang = kit.tube([fp + Vector((0, 0.03, 0.02)), fp + Vector((0, -0.006, -0.015)), fp + Vector((0.004, -0.01, -0.05))],
                    [0.022, 0.016, 0.003], segs=6, rings=5)
    add("fang", flat_paint(fang, hexc("#F2E6D2")), bone_m)
    # horn nubs between the ears
    for s in (-1, 1):
        p, n = hit(tree, (0.2 * s, -0.3, 4.0), (0, 0, -1))
        horn = kit.tube([p - Vector((0, 0, 0.06)), p + Vector((0.04 * s, 0.02, 0.12)), p + Vector((0.1 * s, 0.08, 0.2))],
                        [0.075, 0.05, 0.006], segs=10, rings=8)
        paint(horn, lambda co, n_, p=p: mix(hexc("#1A1012"), hexc("#3D2224"), smooth(co.z, p.z, p.z + 0.2)))
        add("horns", horn, horn_m)
    # claws: three on each foot
    for s in (-1, 1):
        for k in (-1, 0, 1):
            root = Vector((0.37 * s + 0.07 * k, -0.36, 0.06))
            claw = kit.tube([root, root + Vector((0.015 * k, -0.07, -0.02)), root + Vector((0.02 * k, -0.12, -0.06))],
                            [0.035, 0.025, 0.004], segs=6, rings=4)
            add("claws", flat_paint(claw, hexc("#1A1214")), horn_m)

    # ---- the wings ------------------------------------------------------------------------------------
    for s in (-1, 1):
        sh = Vector((0.66 * s, 0.14, 1.66))
        el = Vector((1.18 * s, 0.3, 2.18))
        wr = Vector((1.62 * s, 0.38, 3.02))
        tips = [Vector((2.18 * s, 0.5, 4.02)), Vector((2.92 * s, 0.56, 3.66)), Vector((3.02 * s, 0.56, 2.72)),
                Vector((2.42 * s, 0.5, 1.72))]
        flank = Vector((0.66 * s, 0.24, 0.9))
        # arm and finger bones
        bones = [kit.tube([sh, sh.lerp(el, 0.5) + Vector((0, 0, 0.06)), el], [0.11, 0.075, 0.07], segs=8, rings=6),
                 kit.tube([el, el.lerp(wr, 0.5) + Vector((0.04 * s, 0, 0)), wr], [0.07, 0.05, 0.06], segs=8, rings=6)]
        for k, t in enumerate(tips):
            mid = wr.lerp(t, 0.5) + Vector((0, 0, 0.05 if k < 2 else -0.04))
            bones.append(kit.tube([wr, mid, t], [0.05, 0.03, 0.008], segs=6, rings=7))
        thumb = wr + Vector((0.02 * s, -0.12, 0.12))
        bones.append(kit.tube([wr, thumb, thumb + Vector((-0.02 * s, -0.08, -0.03))], [0.045, 0.03, 0.004], segs=6, rings=5))
        for b in bones:
            paint(b, lambda co, n: mix(hexc("#3A0A0F"), hexc("#6A1414"), smooth(abs(co.x), 1.0, 2.8)))
            add("bones", b, bone_m)
        # membrane: fan sectors from the wrist between the fingers, and from the wrist to the flank
        edges = tips + [flank]
        glow_rows = []
        for k in range(len(edges) - 1):
            a, b = edges[k], edges[k + 1]
            scallop = 0.26 * (a - b).length / 1.0
            nu, nv = 7, 6
            towards = (wr - (a + b) / 2).normalized()
            grid, gvals = [], []
            for i in range(nu + 1):
                u = i / nu
                row = []
                for j in range(nv + 1):
                    v = j / nv
                    e = a.lerp(b, v) + towards * scallop * math.sin(math.pi * v) ** 0.9
                    p = wr.lerp(e, u)
                    # a little billow backwards
                    p += Vector((0, 0.12, 0)) * math.sin(math.pi * u) * math.sin(math.pi * v)
                    row.append(p)
                grid.append(row)
            if k == len(edges) - 2:
                # last sector reaches the flank: let its inner edge follow the arm back to the shoulder
                for i in range(nu + 1):
                    u = i / nu
                    arm = wr.lerp(el, min(1, u * 2)) if u < 0.5 else el.lerp(sh, (u - 0.5) * 2)
                    grid[i][nv] = grid[i][nv].lerp(arm, 0.0)
            gfn = (lambda i, j, nu=nu: (i / nu) ** 1.1)
            add("membrane", sheet(grid, 0.022, gfn), wing_m)
            # the glowing ember edge: a thin strip just outside the trailing edge
            strip = []
            for i, off in ((0, -0.015), (1, 0.03)):
                row = []
                for j in range(nv * 2 + 1):
                    v = j / (nv * 2)
                    e = a.lerp(b, v) + towards * scallop * math.sin(math.pi * v) ** 0.9
                    e += Vector((0, 0.12, 0)) * 0.0
                    out = (e - wr).normalized()
                    row.append(e + out * off)
                strip.append(row)
            add("ember", sheet(strip, 0.03), glow_m)
        # the inner membrane between the arm and the flank
        grid = []
        nu, nv = 5, 5
        for i in range(nu + 1):
            u = i / nu
            arm = el.lerp(wr, u) if True else None
            low = flank.lerp(wr, u * 0.999)
            row = []
            for j in range(nv + 1):
                v = j / nv
                top = sh.lerp(el, 1 - u) if False else (sh.lerp(el, u * 2) if u < 0.5 else el.lerp(wr, (u - 0.5) * 2))
                p = top.lerp(flank.lerp(wr, u ** 1.5 * 0.0) if False else flank, v * (1 - u ** 3))
                p += Vector((0, 0.06, 0)) * math.sin(math.pi * v) * math.sin(math.pi * min(u * 1.2, 1))
                row.append(p)
            grid.append(row)
        add("membrane", sheet(grid, 0.022, lambda i, j: 0.05 + 0.1 * j / 5), wing_m)
    bat.build()
    return bat


def bake(bat, texture):
    """Everything that does not glow becomes one textured mesh, InfernoBat_Body; the eyes and the
    ember edges of the wings are joined into InfernoBat_GLOW, which keeps its emissive material."""
    glow = [ob for ob in bat.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in bat.objects if ob not in glow], texture, name=NAME + "_Body",
                            shade=0.5, soften=3, rough=0.9, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = NAME + "_GLOW"
    b = kit.principled(body.data.materials[0])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.2         # matte fur
    bat.objects = [body, g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,front,side,back 3/4,game distance")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default="InfernoBat review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "infernobat_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    bat = build()
    print("triangles by part:", dict(sorted(bat.tally.items(), key=lambda kv: -kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(bat, os.path.abspath(a.texture))
    tris = bat.triangles()
    lo, hi = bat.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(bat.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(bat, samples=a.samples, focus=(0, -0.3, 2.0))
        head = Vector((0, -0.55, 2.3))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.45, -1.0, 0.1)).normalized() * 3.4, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.05)).normalized() * 3.0, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face front", "full", a.px)


if __name__ == "__main__":
    main()
