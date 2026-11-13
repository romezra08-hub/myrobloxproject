"""Unicorn pet: a moonlight unicorn, an elegant faceted low-poly sculpture. Built from scratch by script.

    python models/pets/unicorn.py --review out/unicorn.png      # render the review sheet
    python models/pets/unicorn.py --export models/export/unicorn.fbx

Style: a carved gem or papercraft sculpture of a real horse, never a toy pony. Must-haves, checked
in every review:
  1. A real horse: a long refined head with a tapering muzzle, flared nostrils, a defined jaw and
     cheek, small alert ears; an arched muscular neck, a deep chest, a sloping shoulder, a strong
     haunch; slim legs with knees, hocks, fetlocks and feathering over gold hooves.
  2. A proud, dynamic pose: prancing with one foreleg raised high, neck arched, face near vertical.
  3. Moonlight palette: pearl white to cool silver-lavender coat with a faint pale-gold dapple on the
     haunch; mane and tail in big swept locks of deep sapphire to violet with lighter tips.
  4. A twisted faceted crystal horn of pale moonstone blue (the glowing part, Unicorn_GLOW_Horn).
  5. Calm almond eyes under a defined brow; no lashes, no big round eyes. Never creepy.
  6. Deliberate facets: big planes on the body, finer at the head, mane and joints; matte, with a
     faint grain.

Round 9: a new design from scratch. The body is lofted from anatomical sections (trunk, arched neck,
head, four legs, shoulder, chest and haunch muscles), merged into one skin by a voxel remesh and
decimated with weights, so the facets are large on the barrel and small at the head and joints.

Round 10: the mane drapes down the neck in wide overlapping S-shaped locks with the tips flicking back
(they stuck out like fins), darker sapphire; the tail is a round bundle of locks that fans open (it was
a flat plank); a darker pearl coat with more lavender in the shade, so the facets show; a smaller brow,
a larger eye, a softer inner ear and slightly larger hooves.

Round 11: sturdier legs (forearm, gaskin, knees and cannons); the head turned further towards the
viewer, the far ear turned out as if listening; the forelock swept to the far side so the near eye
reads; a slightly greyer pearl coat with more lavender underneath and a clearer gold dapple.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop  # noqa: E402

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0
POLL = Vector((0.0, -1.30, 3.47))   # top of the head, behind the ears
PITCH = 70.0                        # the face line this many degrees below horizontal (20 off vertical)
YAW = -18.0                         # head turned towards -X, the side the cameras see
ROLL = 4.0
HEAD = 1.1                          # head size
BODY_TRIS = 2500                    # the sculpted skin after decimation


def V(x, y, z):
    return Vector((x, y, z))


def head_matrix():
    return (Matrix.Translation(POLL) @ Matrix.Rotation(math.radians(YAW), 4, 'Z')
            @ Matrix.Rotation(math.radians(PITCH), 4, 'X') @ Matrix.Rotation(math.radians(ROLL), 4, 'Y')
            @ Matrix.Scale(HEAD, 4))


H = head_matrix()


def hp(x, y, z):
    """A point given in head space (nose towards -Y, face towards +Z) in world space."""
    return H @ V(x, y, z)


def hd(x, y, z):
    """A direction in head space, in world space."""
    return (H.to_3x3() @ V(x, y, z)).normalized()


# ---- smooth sculpt shapes (they are merged and faceted later) ------------------------------------------

def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def ring_pts(c, side, up, hw, top, bot, wt, wb, n, segs):
    """A cross-section: half width hw at the middle, wt at the top and wb at the bottom, reaching
    `top` along `up` and `bot` the other way; n is the squareness (2 an ellipse)."""
    pts = []
    for j in range(segs):
        a = 2 * math.pi * j / segs
        ca, sa = math.cos(a), math.sin(a)
        u = math.copysign(abs(ca) ** (2 / n), ca)
        v = math.copysign(abs(sa) ** (2 / n), sa)
        w = hw + (wt - hw) * max(sa, 0) + (wb - hw) * max(-sa, 0)
        pts.append(c + side * (u * w) + up * (v * (top if sa > 0 else bot)))
    return pts


def skin(rings):
    """A closed smooth-ish skin over rings of equal size, capped with fans."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for a, b in zip(vr, vr[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    for r in (vr[0], vr[-1]):
        c = bm.verts.new(sum((v.co for v in r), Vector()) / n)
        for j in range(n):
            bm.faces.new((r[j], r[(j + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def sweep(points, secs, per=6, segs=20, side_ref=(1, 0, 0)):
    """Sections along a smooth path. secs: per point (hw, top, bot, wt, wb, n). `up` is the path's
    tangent crossed with the side, so along a path going forward it is up, going down it is forward."""
    pts = [Vector(p) for p in points]
    k = len(pts) - 1
    N = k * per
    path = [_cr(pts, i / N * k) for i in range(N + 1)]
    sref = Vector(side_ref)
    rings = []
    for i, c in enumerate(path):
        t = (path[min(i + 1, N)] - path[max(i - 1, 0)]).normalized()
        side = (sref - t * t.dot(sref)).normalized()
        up = t.cross(side).normalized()
        sec = [_cr([s[q] for s in secs], i / N * k) for q in range(6)]
        rings.append(ring_pts(c, side, up, *sec, segs=segs))
    return skin(rings)


def ell(c, r, rot=(0, 0, 0), cuts=5):
    """An ellipsoid with radii r at c."""
    bm = kit.ball((2 * r[0], 2 * r[1], 2 * r[2]), cuts)
    bm.transform(M(c, rot))
    return bm


# The trunk from the rump forwards: (y, top, belly, half width, squareness). Withers high, back dipping a
# little, broad square hips, belly tucked up to the flank, a deep girth.
TRUNK = [(1.46, 2.05, 1.84, 0.10, 2.2), (1.36, 2.21, 1.58, 0.33, 2.5), (1.16, 2.32, 1.42, 0.48, 2.6), (0.88, 2.33, 1.36, 0.50, 2.5),
         (0.55, 2.27, 1.32, 0.46, 2.3), (0.18, 2.22, 1.22, 0.47, 2.3), (-0.20, 2.28, 1.12, 0.49, 2.3), (-0.50, 2.37, 1.10, 0.46, 2.3),
         (-0.80, 2.24, 1.18, 0.40, 2.3), (-1.00, 2.00, 1.36, 0.32, 2.2), (-1.10, 1.80, 1.55, 0.18, 2.1)]

# The neck by its two outlines seen from the side: the crest (arched well above the straight line from
# withers to poll) and the throat (a little hollow, running back to the throatlatch behind the jaw).
CREST = [(-0.22, 2.30), (-0.42, 2.72), (-0.68, 3.10), (-0.95, 3.37), (-1.16, 3.50), (-1.30, 3.51)]
THROAT = [(-1.00, 1.74), (-1.12, 2.02), (-1.15, 2.30), (-1.13, 2.62), (-1.07, 2.86), (-0.99, 3.00)]
NECK_W = [0.29, 0.28, 0.25, 0.21, 0.18, 0.155]

# The head in head space, from behind the poll to the lips: (s, face line, jaw line, half width at the
# middle, at the top (forehead), at the bottom (jaw), squareness).
SKULL = [(-0.10, 0.06, -0.22, 0.13, 0.09, 0.12, 2.2), (0.02, 0.11, -0.30, 0.16, 0.13, 0.14, 2.4),
         (0.18, 0.14, -0.40, 0.19, 0.17, 0.15, 2.5), (0.32, 0.135, -0.37, 0.195, 0.18, 0.13, 2.6),
         (0.46, 0.115, -0.26, 0.155, 0.13, 0.10, 2.4), (0.62, 0.10, -0.19, 0.12, 0.095, 0.095, 2.3),
         (0.78, 0.092, -0.165, 0.112, 0.09, 0.095, 2.3), (0.90, 0.092, -0.16, 0.115, 0.095, 0.10, 2.3),
         (0.97, 0.07, -0.145, 0.10, 0.08, 0.085, 2.2), (1.00, 0.035, -0.105, 0.065, 0.045, 0.055, 2.0)]


def trunk():
    pts = [V(0, y, (t + b) / 2) for y, t, b, w, n in TRUNK]
    secs = [(w, (t - b) / 2, (t - b) / 2, w * 0.74, w * 0.66, n) for y, t, b, w, n in TRUNK]
    return sweep(pts, secs, per=5, segs=24)


def neck():
    k = len(CREST) - 1
    N = k * 5
    rings = []
    for i in range(N + 1):
        t = i / N * k
        c, th, w = V(0, *_cr([Vector(p) for p in CREST], t)), V(0, *_cr([Vector(p) for p in THROAT], t)), _cr(NECK_W, t)
        mid, half = (c + th) / 2, (c - th) / 2
        up = half.normalized()
        rings.append(ring_pts(mid, V(1, 0, 0), up, w, half.length, half.length, w * 0.55, w * 0.8, 2.3, 22))
    return skin(rings)


def head_parts():
    """The head and its muscles, in world space."""
    pts = [V(0, -s, (f + j) / 2) for s, f, j, *_ in SKULL]
    secs = [(w, (f - j) / 2, (f - j) / 2, wt, wb, n) for s, f, j, w, wt, wb, n in SKULL]
    parts = [sweep(pts, secs, per=5, segs=24)]
    for sx in (-1, 1):
        parts.append(ell(V(0.125 * sx, -0.24, -0.20), (0.065, 0.16, 0.15), (10, 0, 0)))      # the round cheek over the jaw
        parts.append(ell(V(0.140 * sx, -0.31, 0.105), (0.03, 0.085, 0.03), (-8, 0, 10 * sx)))  # brow ridge over the eye
        parts.append(ell(V(0.072 * sx, -0.87, 0.02), (0.038, 0.07, 0.05), (20, 0, 0)))       # flared nostril
    parts.append(ell(V(0, -0.925, -0.14), (0.07, 0.07, 0.045)))                               # chin
    for bm in parts:
        bm.transform(H)
    return parts


def leg(points, secs):
    return sweep([V(*p) for p in points], secs, per=5, segs=16)


# Legs, top down: points (x, y, z) and sections (half width, front, back, front width, back width, squareness).
FORE_SECS = [(0.16, 0.21, 0.21, 0.14, 0.14, 2.2), (0.155, 0.18, 0.18, 0.13, 0.14, 2.2), (0.115, 0.115, 0.10, 0.10, 0.09, 2.2),
             (0.092, 0.09, 0.08, 0.088, 0.075, 2.6), (0.068, 0.064, 0.07, 0.062, 0.064, 2.3), (0.062, 0.058, 0.068, 0.056, 0.058, 2.3),
             (0.074, 0.07, 0.09, 0.068, 0.07, 2.3), (0.058, 0.055, 0.058, 0.055, 0.055, 2.2), (0.068, 0.065, 0.065, 0.065, 0.065, 2.2)]
HIND_SECS = [(0.21, 0.31, 0.31, 0.19, 0.19, 2.3), (0.19, 0.27, 0.27, 0.17, 0.17, 2.3), (0.125, 0.13, 0.17, 0.11, 0.11, 2.2),
             (0.088, 0.09, 0.11, 0.08, 0.075, 2.5), (0.07, 0.068, 0.074, 0.064, 0.064, 2.3), (0.062, 0.06, 0.068, 0.057, 0.059, 2.3),
             (0.074, 0.07, 0.09, 0.068, 0.07, 2.3), (0.058, 0.055, 0.058, 0.055, 0.055, 2.2), (0.068, 0.065, 0.065, 0.065, 0.065, 2.2)]

FORE_PLANTED = [(0.27, -0.70, 1.75), (0.26, -0.66, 1.30), (0.25, -0.66, 1.00), (0.25, -0.67, 0.74), (0.25, -0.67, 0.62),
                (0.25, -0.67, 0.36), (0.25, -0.67, 0.25), (0.25, -0.71, 0.16), (0.25, -0.74, 0.11)]
FORE_RAISED = [(-0.27, -0.70, 1.75), (-0.26, -0.68, 1.32), (-0.255, -0.96, 1.21), (-0.25, -1.20, 1.10), (-0.25, -1.21, 0.98),
               (-0.25, -1.19, 0.76), (-0.25, -1.16, 0.65), (-0.25, -1.10, 0.58), (-0.25, -1.06, 0.55)]
HIND_FWD = [(-0.27, 1.06, 2.00), (-0.30, 0.88, 1.52), (-0.29, 0.84, 1.12), (-0.28, 0.92, 0.80), (-0.28, 0.90, 0.66),
            (-0.28, 0.86, 0.36), (-0.28, 0.85, 0.25), (-0.28, 0.81, 0.16), (-0.28, 0.78, 0.11)]
HIND_BACK = [(0.27, 1.08, 2.00), (0.30, 0.92, 1.52), (0.30, 0.94, 1.12), (0.29, 1.06, 0.80), (0.29, 1.05, 0.66),
             (0.29, 1.03, 0.36), (0.29, 1.02, 0.25), (0.29, 0.98, 0.16), (0.29, 0.95, 0.11)]


def body_parts():
    parts = [trunk(), neck()] + head_parts()
    parts.append(leg(FORE_PLANTED, FORE_SECS))
    parts.append(leg(FORE_RAISED, FORE_SECS))
    parts.append(leg(HIND_FWD, HIND_SECS))
    parts.append(leg(HIND_BACK, HIND_SECS))
    for sx in (-1, 1):
        parts.append(ell(V(0.37 * sx, -0.64, 1.92), (0.08, 0.20, 0.36), (-28, 0, 0)))       # shoulder, sloping
        parts.append(ell(V(0.13 * sx, -1.00, 1.62), (0.13, 0.10, 0.24), (-12, 0, 0)))       # chest muscle
        parts.append(ell(V(0.31 * sx, 0.70 + (0.04 if sx > 0 else 0), 1.46), (0.09, 0.10, 0.12)))  # stifle
    parts.append(sweep([V(0, 1.30, 2.02), V(0, 1.45, 2.10), V(0, 1.56, 2.16)],
                       [(0.08, 0.08, 0.08, 0.07, 0.07, 2.0)] * 3, per=3, segs=12))                # the dock of the tail
    for p in (HIND_FWD, HIND_BACK):                                                        # point of the hock
        x, y, z = p[3]
        parts.append(ell(V(x, y + 0.075, z + 0.03), (0.045, 0.05, 0.07)))
    return parts


def taubin(me, iters=20, lam=0.5, mu=-0.53):
    """Smooth a dense mesh without shrinking it: rounds the hard creases where parts meet."""
    import numpy as np
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    ed = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ed)
    a, b = ed[0::2], ed[1::2]
    deg = np.bincount(a, minlength=n) + np.bincount(b, minlength=n)
    deg = np.maximum(deg, 1)[:, None]
    for _ in range(iters):
        for k in (lam, mu):
            s = np.zeros_like(co)
            np.add.at(s, a, co[b])
            np.add.at(s, b, co[a])
            co += k * (s / deg - co)
    me.vertices.foreach_set("co", co.ravel())
    me.update()


def _phi(s):
    """1 near a warp's centre, falling smoothly to 0 at its edge."""
    if s <= 0.3:
        return 1.0
    if s >= 1.0:
        return 0.0
    u = (s - 0.3) / 0.7
    return 1.0 - u * u * (3 - 2 * u)


def _warp(co, c, R, a, back=False):
    d = co - c
    r = d.length
    if r < 1e-9:
        return co
    if not back:
        return c + d * (1 + a * _phi(r / R))
    lo, hi = 0.0, r / max(0.05, 1 + min(a, 0)) + 1e-6           # solve r0 * (1 + a phi(r0 / R)) = r
    for _ in range(50):
        mid = (lo + hi) / 2
        if mid * (1 + a * _phi(mid / R)) < r:
            lo = mid
        else:
            hi = mid
    return c + d * ((lo + hi) / 2 / r)


def warps():
    """Magnify the head and shrink the barrel while decimating, so that the facets come out small on
    the head and large on the body, with an even change in between and no seam."""
    return [(hp(0, -0.45, -0.05), 1.0, 0.7), (V(0, 0.15, 1.75), 1.15, -0.35)]


def facet(parts, voxel=0.02, smooth=20, target=BODY_TRIS):
    """Merge overlapping smooth parts into one skin (voxel remesh), round the joins, then decimate it to
    `target` triangles, finer where warps() magnifies."""
    whole = bmesh.new()
    for bm in parts:
        tmp = bpy.data.meshes.new("tmp")
        bm.to_mesh(tmp)
        bm.free()
        whole.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new("Sculpt")
    whole.to_mesh(me)
    whole.free()
    ob = bpy.data.objects.new("Sculpt", me)
    bpy.context.scene.collection.objects.link(ob)
    rm = ob.modifiers.new("Remesh", 'REMESH')
    rm.mode, rm.voxel_size, rm.adaptivity = 'VOXEL', voxel, 0.0
    dg = bpy.context.evaluated_depsgraph_get()
    dense = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    taubin(dense, smooth)
    W = warps()
    for v in dense.vertices:
        co = v.co.copy()
        for c, R, a in W:
            co = _warp(co, c, R, a)
        v.co = co
    ob = bpy.data.objects.new("Sculpt", dense)
    bpy.context.scene.collection.objects.link(ob)
    tris = sum(len(p.vertices) - 2 for p in dense.polygons)
    dm = ob.modifiers.new("Decimate", 'DECIMATE')
    dm.decimate_type, dm.ratio, dm.use_collapse_triangulate = 'COLLAPSE', target / tris, True
    dg = bpy.context.evaluated_depsgraph_get()
    low = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(dense)
    out = bmesh.new()
    out.from_mesh(low)
    bpy.data.meshes.remove(low)
    for v in out.verts:
        co = v.co.copy()
        for c, R, a in reversed(W):
            co = _warp(co, c, R, a, back=True)
        v.co = co
    bmesh.ops.triangulate(out, faces=out.faces[:])
    bmesh.ops.recalc_face_normals(out, faces=out.faces[:])
    print("  sculpt: %d triangles from %d" % (len(out.faces), tris))
    return out


# ---- materials -------------------------------------------------------------------------------------------

def _ops(tree):
    new, link = tree.nodes.new, tree.links.new

    def attr(name):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs["Fac"]

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

    def remap(src, a, b, lo=0.0, hi=1.0):
        r = new("ShaderNodeMapRange")
        r.interpolation_type = 'SMOOTHSTEP'
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b
        r.inputs["To Min"].default_value, r.inputs["To Max"].default_value = lo, hi
        link(src, r.inputs["Value"])
        return r.outputs["Result"]

    def ramp(src, stops):
        rp = new("ShaderNodeValToRGB")
        els = rp.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
        els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
        for pos, hexcode in stops[1:-1]:
            e = els.new(pos)
            e.color = (*kit.srgb(hexcode), 1.0)
        link(src, rp.inputs["Fac"])
        return rp.outputs["Color"]

    def mix(fac, a, b):
        m = new("ShaderNodeMix")
        m.data_type = 'RGBA'
        for sock, v in ((0, fac), (6, a), (7, b)):
            if isinstance(v, (int, float)):
                m.inputs[sock].default_value = v
            elif isinstance(v, str):
                m.inputs[sock].default_value = (*kit.srgb(v), 1.0)
            else:
                link(v, m.inputs[sock])
        return m.outputs[2]

    def xyz(kind="Object"):
        tc = new("ShaderNodeTexCoord")
        sep = new("ShaderNodeSeparateXYZ")
        link(tc.outputs[kind], sep.inputs[0])
        return tc.outputs[kind], sep.outputs

    def normal_z():
        geo = new("ShaderNodeNewGeometry")
        sep = new("ShaderNodeSeparateXYZ")
        link(geo.outputs["Normal"], sep.inputs[0])
        return sep.outputs[2]

    def dist(vec, point):
        d = new("ShaderNodeVectorMath")
        d.operation = 'DISTANCE'
        link(vec, d.inputs[0])
        d.inputs[1].default_value = tuple(point)
        return d.outputs["Value"]
    return new, link, attr, op, remap, ramp, mix, xyz, normal_z, dist


def _finish(m, colour, facet=0.05):
    """Feed a colour into the grain node kit.furry made, and vary the shade a little per facet."""
    tree = m.node_tree
    new, link, attr, op, *_ = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    link(colour, hsv.inputs["Color"])
    old = hsv.inputs["Value"].links[0].from_socket
    link(op('MULTIPLY', old, op('MULTIPLY_ADD', attr("facet"), 2 * facet, 1 - facet)), hsv.inputs["Value"])
    return m


def coat_material(muzzle):
    """Pearl white on the back to cool silver-lavender on the legs and underneath, a grey-lavender
    muzzle and a faint pale-gold dapple on each haunch."""
    m = kit.material("Coat", "#F2F0F6", rough=0.85)
    kit.furry(m, strength=0.06, mottle=0.05, fine=22.0, length=1.4)
    new, link, attr, op, remap, ramp, mix, xyz, normal_z, dist = _ops(m.node_tree)
    co, (x, y, z) = xyz()
    c = ramp(remap(z, 0.0, 2.3), [(0.0, "#8C85AE"), (0.10, "#9E98BE"), (0.30, "#BEB8D4"), (0.52, "#D2CEE0"), (0.75, "#DEDBE8"), (1.0, "#E4E2EC")])
    nz = normal_z()
    c = mix(remap(nz, -0.15, -0.9, 0.0, 0.6), c, "#ADA5CC")
    c = mix(remap(nz, 0.35, 0.95, 0.0, 0.45), c, "#F1F0F6")
    c = mix(remap(dist(co, muzzle), 0.10, 0.40, 0.8, 0.0), c, "#A29BBF")
    hx = new("ShaderNodeCombineXYZ")
    link(op('ABSOLUTE', x), hx.inputs[0])
    link(y, hx.inputs[1])
    link(z, hx.inputs[2])
    near = remap(dist(hx.outputs[0], (0.40, 1.00, 1.85)), 0.25, 0.62, 1.0, 0.0)
    vor = new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 6.0
    link(co, vor.inputs["Vector"])
    spot = remap(vor.outputs["Distance"], 0.14, 0.34, 1.0, 0.0)
    c = mix(op('MULTIPLY', op('MULTIPLY', near, spot), 0.85), c, "#D9C084")
    return _finish(m, c, 0.05)


def ramp_material(name, stops, rough=0.8, grain=None, facet=0.06, by="g"):
    """A colour ramp read from the vertex value g (0 at a lock's root, 1 at its tip)."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **(grain or dict(strength=0.07, mottle=0.05, fine=30.0, length=3.0)))
    new, link, attr, op, remap, ramp, mix, xyz, normal_z, dist = _ops(m.node_tree)
    src = attr("g") if by == "g" else remap(normal_z(), -0.6, 0.95)
    return _finish(m, ramp(src, stops), facet)


def flat_material(name, hexcode, rough=0.8, facet=0.04):
    m = kit.material(name, hexcode, rough=rough)
    kit.furry(m, strength=0.03, mottle=0.03, fine=30.0, length=1.0)
    new, link, *_ = _ops(m.node_tree)
    rgb = new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (*kit.srgb(hexcode), 1.0)
    return _finish(m, rgb.outputs[0], facet)


# ---- faceted detail parts ------------------------------------------------------------------------------------

def loft(rings, cap=True):
    """A closed faceted skin over rings (lists of points, or a single Vector for a point)."""
    bm = bmesh.new()
    vr = [[bm.verts.new(r)] if isinstance(r, Vector) else [bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vr, vr[1:]):
        if len(a) == 1:
            for j in range(len(b)):
                bm.faces.new((a[0], b[j], b[(j + 1) % len(b)]))
        elif len(b) == 1:
            for j in range(len(a)):
                bm.faces.new((a[j], a[(j + 1) % len(a)], b[0]))
        else:
            n = len(a)
            for j in range(n):
                bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    for r in (vr[0], vr[-1]):
        if cap and len(r) > 2:
            bm.faces.new(r)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    return bm


def paint(bm, g):
    """Store a colour position on every vertex: a number, or a function of the vertex."""
    lay = bm.verts.layers.float.get("g") or bm.verts.layers.float.new("g")
    for v in bm.verts:
        v[lay] = g(v) if callable(g) else g
    return bm


LOCK = [(1.0, 0.0), (0.0, 0.75), (-1.0, 0.0), (-0.45, -0.5), (0.45, -0.5)]     # a blade with a ridge on its face


def ribbon(points, normals, widths, thick, profile=LOCK, twist=0.0):
    """A lock of hair: a faceted blade along `points` ending in a point. normals give the broad face's
    normal at each point; g runs from 0 at the root to 1 at the tip."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = []
    for i in range(n - 1):
        t = (pts[i + 1] - pts[max(i - 1, 0)]).normalized()
        nr = Vector(normals[i]) if isinstance(normals, list) else Vector(normals)
        nr = (nr - t * t.dot(nr)).normalized()
        side = nr.cross(t).normalized()
        if twist:
            a = twist * i / (n - 1)
            side, nr = side * math.cos(a) + nr * math.sin(a), nr * math.cos(a) - side * math.sin(a)
        rings.append([pts[i] + side * (u * widths[i]) + nr * (v * thick[i]) for u, v in profile])
    rings.append(pts[-1])
    bm = loft(rings)
    lay = bm.verts.layers.float.new("g")
    run = [0.0]
    for a, b in zip(pts, pts[1:]):
        run.append(run[-1] + (b - a).length)
    for v in bm.verts:
        k = min(range(n), key=lambda i: (v.co - pts[i]).length_squared)
        v[lay] = run[k] / run[-1]
    return bm


def smooth_path(points, n):
    pts = [Vector(p) for p in points]
    k = len(pts) - 1
    return [_cr(pts, i / (n - 1) * k) for i in range(n)]


def frame(origin, x, y, z):
    m = Matrix.Identity(4)
    for i, axis in enumerate((x, y, z)):
        m[0][i], m[1][i], m[2][i] = axis
    m.translation = origin
    return m


def gem(r):
    return loft([V(0, 0, -r), [V(r, 0, 0), V(0, r, 0), V(-r, 0, 0), V(0, -r, 0)], V(0, 0, r)])


def almond(length, height, dome, back=0.012, k=1.0):
    """A flat almond, long axis along X, facing +Z: an eye or a nostril."""
    us = [-1.0, -0.62, -0.18, 0.3, 0.72, 1.0, 0.68, 0.22, -0.3, -0.7]
    outline = []
    for i, u in enumerate(us):
        upper = i <= 5 and i not in (0, 5)
        if i in (0, 5):
            v = 0.0
        elif upper:
            v = 0.5 * (1 - u * u) ** 0.7 * (1 + 0.12 * u * k)
        else:
            v = -0.42 * (1 - u * u) ** 0.8
        outline.append((u * length / 2, v * height))
    r0 = [V(x, y, -back) for x, y in outline]
    r1 = [V(x * 0.98, y * 0.98, 0.0) for x, y in outline]
    r2 = [V(x * 0.6, y * 0.6, dome * 0.75) for x, y in outline]
    return loft([r0, r1, r2, V(0.04 * length, 0.05 * height, dome)])


class Surface:
    def __init__(self, bm):
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, toward):
        o = Vector(origin)
        d = (Vector(toward) - o).normalized()
        loc, nrm, _, _ = self.bvh.ray_cast(o, d)
        return loc, nrm

    def side(self, y, z, sx, fallback=0.0):
        """How far out the body's surface is on side sx at (y, z) of the side view."""
        loc, _ = self.hit(V(sx * 3.0, y, z), V(0, y, z))
        return abs(loc.x) if loc is not None else fallback


def crest_at(u):
    """Point on the crest of the neck (u 0 at the withers, 1 at the poll) and its outward normal."""
    pts = [Vector(p) for p in CREST]
    k = len(pts) - 1
    t = min(max(u, 0.0), 1.0) * k
    c = _cr(pts, t)
    tn = (_cr(pts, min(t + 0.02, k)) - _cr(pts, max(t - 0.02, 0))).normalized()
    return V(0, c.x, c.y), V(0, tn.y, -tn.x).normalized()


def mane_lock(srf, u, sx, length, back, width, wave=0.04, out=0.0, flick=0.14, thick=0.05):
    """A lock from the crest at u, over the top to side sx and draped down that side of the neck in a
    gentle S (`wave`), a little back (`back`), standing `out` off the neck, its tip flicking back by `flick`."""
    C, n = crest_at(u)
    X = V(sx, 0, 0)
    D = V(0, back, -1.0).normalized()
    pts = [C - n * 0.05, C + n * 0.075 + X * 0.045]
    x = srf.side(C.y, C.z - 0.05, sx, 0.12)
    for f in (0.2, 0.42, 0.64, 0.84, 1.0):
        p = C + D * (f * length) + V(0, flick * f ** 3 + wave * math.sin(f * math.pi * 1.7), flick * 0.35 * f ** 3)
        x = srf.side(p.y, p.z, sx, x)
        pts.append(V(sx * (x + 0.035 + out * f + 0.05 * f * f), p.y, p.z))
    pts = smooth_path(pts, 8)
    nrm = [X + n * 0.25 for _ in pts]
    w = [width * f for f in (0.45, 0.85, 1.0, 1.0, 0.9, 0.75, 0.5)]
    th = [thick * f for f in (0.8, 1.0, 1.0, 0.95, 0.85, 0.7, 0.5)]
    return ribbon(pts, nrm, w, th)


def on_lock(bm, g, out):
    """A point on the outer face of a lock at g along it, for a star."""
    lay = bm.verts.layers.float.get("g")
    v = max((v for v in bm.verts if abs(v[lay] - g) < 0.2), key=lambda v: v.co.dot(Vector(out)))
    return v.co + Vector(out).normalized() * 0.008


def leg_frame(path, i):
    p = [Vector(q) for q in path]
    t = (p[min(i + 1, len(p) - 1)] - p[max(i - 1, 0)]).normalized()
    side = (V(1, 0, 0) - t * t.dot(V(1, 0, 0))).normalized()
    return p[i], t, side, t.cross(side).normalized()


def hoof(path, planted):
    """A faceted gold hoof below the coronet of a leg, the front wall sloping, the toe forward."""
    c, t, side, front = leg_frame(path, len(path) - 1)
    if planted:
        axis, front, side = V(0, 0, -1), V(0, -1, 0), V(1, 0, 0)
        top = V(c.x, c.y - 0.01, 0.135)
        h = 0.135
    else:
        axis = t
        top = c - t * 0.02
        h = 0.13
    def ring(r_side, r_front, r_back, shift, d):
        pts = []
        for j in range(8):
            a = 2 * math.pi * j / 8 + math.pi / 8
            ca, sa = math.cos(a), math.sin(a)
            fr = r_front if sa > 0 else r_back
            pts.append(top + axis * d + side * (ca * r_side) + front * (sa * fr + shift))
        return pts
    k = 1.12
    return loft([ring(0.072 * k, 0.075 * k, 0.072 * k, 0.0, 0.0), ring(0.082 * k, 0.092 * k, 0.08 * k, 0.015, h * 0.55),
                 ring(0.088 * k, 0.104 * k, 0.084 * k, 0.03, h * 0.9), ring(0.084 * k, 0.098 * k, 0.08 * k, 0.03, h)])


def feathering(path):
    """Long hair falling from the back of the fetlock over the heel."""
    c, t, side, front = leg_frame(path, 6)
    out = []
    for ang, ln in ((-85, 0.12), (-45, 0.145), (0, 0.16), (45, 0.145), (85, 0.12)):
        a = math.radians(ang)
        d = -front * math.cos(a) + side * math.sin(a)
        pts = [c + d * 0.045 - t * 0.04, c + d * 0.075 + t * 0.04, c + d * 0.088 + t * (ln * 0.75), c + d * 0.09 + t * ln]
        out.append(ribbon(pts, d, [0.032, 0.034, 0.024], [0.016, 0.016, 0.012], profile=[(1, 0), (0, 0.7), (-1, 0), (0, -0.6)]))
    return out


def spiral_horn(length, r0, rings=15, turns=2.2, groove=0.5, ridges=3):
    """A twisted crystal: `ridges` sharp ridges winding round a cone, deep grooves between them.
    Base at the origin, pointing up +Z."""
    k = ridges * 2
    rr = []
    for i in range(rings):
        f = i / rings
        r = r0 * (1 - f) ** 0.85
        rr.append([V(r * (1 if j % 2 == 0 else groove) * math.cos(2 * math.pi * (j / k + turns * f)),
                     r * (1 if j % 2 == 0 else groove) * math.sin(2 * math.pi * (j / k + turns * f)), length * f) for j in range(k)])
    rr.append(V(0, 0, length))
    return loft(rr)


def tail_lock(base, offs, width, length_f=1.0, out=None):
    """A tail lock following the base path, pushed off it by `offs` (growing towards the tip), its broad
    face turned to `out`, so that the locks together make a round bundle that fans open."""
    n = len(base)
    m = max(3, int(round(n * length_f)))
    pts = [base[i] + Vector(offs) * ((i / (n - 1)) ** 1.1) for i in range(m)]
    w = [width * min(1.0, 0.55 + 1.6 * i / m) * (1 - 0.55 * (i / m) ** 2) for i in range(m - 1)]
    th = [0.045 * (1 - 0.4 * i / m) for i in range(m - 1)]
    o = Vector(out or offs)
    return ribbon(pts, [o] * m, w, th)


# ---- build ----------------------------------------------------------------------------------------------

def build(args=None):
    muzzle = hp(0, -0.97, -0.03)
    coat = coat_material(muzzle)
    mane = ramp_material("Mane", [(0.0, "#070A2E"), (0.32, "#111C5E"), (0.62, "#231E6E"), (0.86, "#463A9A"), (1.0, "#9A8ED8")],
                         grain=dict(strength=0.08, mottle=0.06, fine=30.0, length=4.0), facet=0.08)
    feather = ramp_material("Feather", [(0.0, "#C3BDD8"), (1.0, "#F4F3F9")], facet=0.05)
    gold = ramp_material("Gold", [(0.0, "#9C7128"), (0.45, "#CFA443"), (1.0, "#F4DA8C")], rough=0.6, by="nz", facet=0.1)
    eye = flat_material("Eye", "#1A1832", rough=0.4, facet=0.0)
    shine = flat_material("Shine", "#F2F5FF", rough=0.3, facet=0.0)
    nostril = flat_material("Nostril", "#4E4670", facet=0.0)
    inner = flat_material("InnerEar", "#ABA4C6", facet=0.05)
    glow = kit.material("GLOW_Horn", "#86C4FF", rough=0.35, emit=0.55)
    uni = Prop("Unicorn")
    print("sculpting the body")
    body = facet(body_parts())
    srf = Surface(body)
    paint(body, 0.0)
    uni.add(body, coat)

    # ---- hooves and feathering ---------------------------------------------------------------------
    for path, planted in ((FORE_PLANTED, True), (FORE_RAISED, False), (HIND_FWD, True), (HIND_BACK, True)):
        uni.add(paint(hoof(path, planted), 0.0), gold)
        for bm in feathering(path):
            uni.add(bm, feather)

    # ---- ears: small, alert, pricked forwards ------------------------------------------------------
    fwd = hd(0, -0.342, 0.94)
    for sx in (-1, 1):
        base = hp(0.10 * sx, 0.0, 0.085)
        Z = hd(0.16 * sx, 0.68, 0.72) if sx < 0 else hd(0.30, 0.74, 0.58)
        F = (fwd - Z * Z.dot(fwd)).normalized()
        F = (F + V(sx, 0, 0) * (0.35 if sx < 0 else 0.9)).normalized()
        F = (F - Z * Z.dot(F)).normalized()
        Y = -F
        X = Y.cross(Z)
        E = frame(base, X, Y, Z)
        prof = [(0.5, 0.45), (1.0, 0.0), (0.6, -0.4), (0.0, -0.08), (-0.6, -0.4), (-1.0, 0.0), (-0.5, 0.45), (0.0, 0.55)]
        rings = [[V(u * a, v * b, z) for u, v in prof] for a, b, z in ((0.058, 0.048, -0.04), (0.07, 0.055, 0.10), (0.05, 0.04, 0.2))]
        ear = loft(rings + [V(0, -0.012, 0.29)])
        cup, outside = kit.split(ear, lambda f: f.normal.y < -0.35 and f.calc_center_median().y > -0.03 and f.calc_center_median().z > 0.0)
        S = E @ Matrix.Scale(HEAD * 0.82, 4)
        uni.add(paint(outside, 0.0), coat, S)
        uni.add(paint(cup, 0.0), inner, S)

    # ---- eyes: almond, calm, under the brow --------------------------------------------------------
    for sx in (-1, 1):
        loc, nrm = srf.hit(hp(0.55 * sx, -0.37, 0.30), hp(0.10 * sx, -0.36, 0.0))
        if loc is None:
            continue
        N = (nrm + hd(sx, 0, 0.5)).normalized()
        L = hd(0, 0.92, -0.38)
        L = (L - N * N.dot(L)).normalized()
        if L.dot(hd(0, 1, 0)) < 0:
            L = -L
        Y = N.cross(L)
        E = frame(loc + N * 0.004, L, Y, N)
        uni.add(paint(almond(0.13 * HEAD, 0.062 * HEAD, 0.013), 0.0), eye, E)
        uni.add(paint(gem(0.012), 0.0), shine, E @ M((0.022, 0.014, 0.013), scale=(1.3, 1.0, 0.5)))
        # nostril: a dark comma on the front of the flare
        loc, nrm = srf.hit(hp(0.3 * sx, -0.99, 0.30), hp(0.04 * sx, -0.88, 0.0))
        if loc is not None:
            Nn = nrm.normalized()
            Ln = hd(0, 1, 0.2)
            Ln = (Ln - Nn * Nn.dot(Ln)).normalized()
            uni.add(paint(almond(0.07 * HEAD, 0.024 * HEAD, 0.004, back=0.01), 0.0), nostril, frame(loc + Nn * 0.002, Ln, Nn.cross(Ln), Nn))

    # ---- horn: a twisted crystal from the forehead, with a thin gold band ---------------------------
    loc, nrm = srf.hit(hp(0, -0.20, 0.7), hp(0, -0.20, 0.0))
    hz = hd(0, 0.80, 0.60)
    hx = V(1, 0, 0)
    hy = hz.cross(hx).normalized()
    hx = hy.cross(hz).normalized()
    HN = frame(loc - hz * 0.03, hx, hy, hz)
    uni.add(spiral_horn(0.82, 0.075), glow, HN)
    band = [[V(r * math.cos(2 * math.pi * j / 8), r * math.sin(2 * math.pi * j / 8), z) for j in range(8)]
            for r, z in ((0.084, -0.02), (0.088, 0.02), (0.08, 0.045))]
    uni.add(paint(loft(band), 0.0), gold, HN)

    # ---- mane: big swept locks on the near side, a few on the far side, a forelock -------------------
    for u, ln, back, w, wave in ((0.98, 0.55, 0.55, 0.15, 0.03), (0.90, 0.75, 0.5, 0.19, -0.04), (0.81, 0.92, 0.45, 0.21, 0.05),
                                 (0.72, 1.02, 0.42, 0.22, -0.05), (0.63, 1.08, 0.40, 0.22, 0.05), (0.54, 1.05, 0.42, 0.22, -0.04),
                                 (0.45, 0.98, 0.45, 0.21, 0.05), (0.36, 0.86, 0.5, 0.20, -0.04), (0.27, 0.72, 0.55, 0.18, 0.04),
                                 (0.18, 0.58, 0.65, 0.16, -0.03), (0.10, 0.42, 0.8, 0.13, 0.03)):
        uni.add(mane_lock(srf, u, -1, ln, back, w, wave, out=0.0), mane)
    stars = []
    for u, ln, back, w, wave in ((0.86, 0.55, 0.6, 0.16, 0.05), (0.68, 0.7, 0.5, 0.17, -0.05), (0.50, 0.68, 0.55, 0.17, 0.05),
                                 (0.32, 0.55, 0.6, 0.15, -0.04)):
        lock = mane_lock(srf, u, -1, ln, back, w, wave, out=0.05, flick=0.2, thick=0.045)
        stars.append(on_lock(lock, 0.62, (-1, 0.1, 0.1)))
        uni.add(lock, mane)
    for u, ln, back, w, wave in ((0.92, 0.5, 0.6, 0.16, 0.03), (0.76, 0.62, 0.5, 0.18, -0.04), (0.60, 0.66, 0.5, 0.18, 0.04),
                                 (0.44, 0.6, 0.55, 0.17, -0.04), (0.28, 0.5, 0.65, 0.15, 0.03)):
        uni.add(mane_lock(srf, u, 1, ln, back, w, wave), mane)
    # forelock, in head space: from between the ears, past the horn, over the near temple
    for pts, w in (([(0.0, 0.03, 0.12), (0.05, -0.06, 0.20), (0.12, -0.17, 0.19), (0.18, -0.27, 0.12), (0.20, -0.34, 0.03)], 0.08),
                   ([(-0.02, 0.03, 0.12), (-0.06, -0.04, 0.19), (-0.11, -0.10, 0.18), (-0.15, -0.16, 0.12)], 0.055)):
        P = [hp(*q) for q in pts]
        nrm = [hd(q[0] * 2.5, 0, 1) for q in pts]
        uni.add(ribbon(smooth_path(P, 6), [nrm[0]] * 6, [w * f * HEAD for f in (0.7, 1.0, 1.0, 0.85, 0.6)],
                       [0.035 * f for f in (0.9, 1.0, 0.9, 0.8, 0.6)]), mane)

    # ---- tail: high at the dock, arching up and back, then cascading down in big locks ------------------
    base = smooth_path([(0, 1.42, 2.08), (0, 1.66, 2.38), (-0.03, 1.97, 2.42), (-0.08, 2.22, 2.18), (-0.13, 2.32, 1.78),
                        (-0.17, 2.30, 1.36), (-0.21, 2.40, 0.98), (-0.25, 2.58, 0.68), (-0.28, 2.76, 0.52)], 9)
    uni.add(tail_lock(base, (-0.04, 0.02, 0.0), 0.17, 1.0, (-1, 0.3, 0)), mane)
    for k in range(8):
        ang = 2 * math.pi * k / 8 + 0.4
        radial = V(math.cos(ang), 1.1 * math.sin(ang), 0.0)
        spread = (0.15, 0.22, 0.18, 0.26)[k % 4]
        lf = (0.95, 0.8, 0.9, 0.72)[k % 4]
        lock = tail_lock(base, radial * spread + V(0, 0, 0.06 * (k % 3)), (0.15, 0.13, 0.14, 0.12)[k % 4], lf, radial)
        if k in (1, 4):
            stars.append(on_lock(lock, 0.7, radial))
        uni.add(lock, mane)

    # ---- stars: a few tiny glowing facets in the mane and tail ------------------------------------------
    for i, p in enumerate(stars[::2] + stars[-2:]):
        uni.add(gem(0.02), glow, M(p, rot=(30 + 20 * i, 45, 10 * i)))

    uni.build(SCALE)
    import random
    rnd = random.Random(9)
    for ob in uni.objects:
        me = ob.data
        a = me.attributes.new("facet", 'FLOAT', 'FACE')
        a.data.foreach_set("value", [rnd.random() for _ in me.polygons])
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
        me.update()
    for ob in uni.objects:
        print("  %-24s %5d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return uni


def bake(uni, texture):
    glow = [ob for ob in uni.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in uni.objects if ob not in glow], texture, name="Unicorn_Body", shade=0.45,
                            soften=2, rough=0.9, uv_angle=66.0, uv_margin=0.006, pack_margin=0.003)
    uni.objects = [body] + glow


def make_rig(uni, samples):
    import review
    rig = review.Rig(uni, samples=samples, focus=tuple(hp(0, -0.4, 0) + V(0, 0.3, -0.5)))
    face = hp(0, -0.45, 0.0)
    rig.cams["face"] = review._camera("C_face", face + Vector((-0.75, -1.0, 0.10)).normalized() * 3.4, face, 30)
    rig.cams["face front"] = review._camera("C_facefront", face + Vector((-0.1, -1.0, 0.0)).normalized() * 3.4, face, 30)
    return rig, review


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--peek", help="quick look while building: these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,side,face,front", help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views instead of all eight")
    ap.add_argument("--title", default="Unicorn review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "unicorn_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    uni = build(a)

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    if a.peek:
        rig, _ = make_rig(uni, min(a.samples, 16))
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        tris = uni.triangles()
        lo, hi = uni.bounds()
        print("triangles:", tris, "total", sum(tris.values()))
        print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(uni, os.path.abspath(a.texture))
    tris = uni.triangles()
    lo, hi = uni.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    for ob in uni.objects:
        zs = [v.co.z for v in ob.data.vertices]
        print("  %-22s z %.3f to %.3f" % (ob.name, min(zs), max(zs)))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(uni.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        rig, review = make_rig(uni, a.samples)
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig.sheet(os.path.abspath(a.review), shots("full") if a.quick else review.STANDARD, px=a.px, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
