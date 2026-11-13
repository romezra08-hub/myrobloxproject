"""Turtle pet: an old forest tortoise, painted like a naturalist's storybook illustration.
Built from scratch by script.

    python models/pets/turtle.py --review out/turtle.png      # render the review sheet
    python models/pets/turtle.py --export models/export/turtle.fbx

Must-haves, checked in every review:
  1. Reads as an old tortoise in outline: a high domed shell with a flared, serrated rim, four
     sturdy elephant legs mid-step, a long neck lifting the head clear of the shell, a short tail.
  2. Real scutes: five down the spine, four down each side and a ring of marginals, each a raised
     plate with stepped growth rings and deep grooves between them; dark umber edges fading to
     amber-ochre centres, weathered.
  3. A gentle, wise old face: a slightly hooked horn beak, a calm closed mouth line, kind dark
     glossy eyes under heavy, slightly drooping lids. No grin, nothing cartoon.
  4. Leathery olive-brown to dusty sage skin with scales, bigger plates on the forelegs and the
     head, wrinkles at the neck and the leg joints. Matte; the texture carries the detail.
  5. A story on its back: a patch of moss with tiny mushrooms and a fern sprig.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, rounded_box, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0
SHELL_C = Vector((0.0, 0.10, 0.92))   # the middle of the dome's base
SA, SB, SH = 1.16, 1.40, 1.30         # half width, half length and height of the dome
SP = 2.3                              # above 2 the dome's sides are steeper and its top broader
GW = 0.022                            # half the width of a groove between scutes, in map units
HEAD_AT = Vector((-0.14, -2.12, 1.70))
HEAD_ROT = (-5, 4, -20)               # nose a touch up, a small tilt, turned towards -X (where the cameras are)


# ---- small helpers ----------------------------------------------------------------------------------

def layer(bm, name="grad"):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def bump(x, c, w):
    return math.exp(-((x - c) / w) ** 2)


def smooth01(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def fix_normals(bm, outward):
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(outward) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def seat(p, normal, up=(0, 0, 1)):
    """A transform that seats a shape at p: its front (-Y) looks out along `normal` and its top is
    as near `up` as it can be."""
    y = -Vector(normal).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(p)
    return m


def frame_from(origin, y, z):
    """A transform with its Y along `y` and its Z as near `z` as it can be."""
    y = Vector(y).normalized()
    z = Vector(z)
    z = (z - y * z.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def lathe(profile, segs=8):
    """A closed surface of revolution round Z through (radius, z) pairs, top to bottom; a radius of
    0 at either end closes it to a point."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z))
                          for j in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            if len(a) == 1:
                bm.faces.new((a[0], b[(j + 1) % segs], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
            else:
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def limb(points, radii, segs=10, rings=None, folds=None, seed=0.0, flat=1.0):
    """Like kit.tube, but its skin can fold: `folds(t, angle)` returns how much to swell the radius
    at that point (t from 0 to 1 along the limb), for wrinkles at the joints."""
    pts = [Vector(p) for p in points]
    rings = rings or (len(pts) - 1) * 4
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    rad = [max(1e-3, kit._spline(list(radii), i / rings * (len(pts) - 1))) for i in range(rings + 1)]
    bm = bmesh.new()
    layer(bm)
    tangent = (path[1] - path[0]).normalized()
    normal = Vector((0, 0, 1))
    normal = (normal - tangent * normal.dot(tangent))
    normal = normal.normalized() if normal.length > 1e-4 else tangent.orthogonal().normalized()
    loops = []
    for i, p in enumerate(path):
        new = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        axis = tangent.cross(new)
        if axis.length > 1e-6:
            normal = Matrix.Rotation(tangent.angle(new), 3, axis.normalized()) @ normal
        tangent = new
        side = tangent.cross(normal).normalized()
        t = i / rings
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            r = rad[i] * (1.0 + (folds(t, a, i) if folds else 0.0))
            r *= 1.0 + 0.035 * noise.noise(p * 3.0 + Vector((seed, a, 0)))
            ring.append(bm.verts.new(p + (normal * math.cos(a) + side * math.sin(a) * flat) * r))
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring in (loops[0], loops[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def wrinkles(zones):
    """Folds for limb(): in each zone (t0, t1, amount, side) every other ring of the limb swells, the
    next one is pulled in a little, strongest on the side `side` (an angle round the limb; 0 is the
    top) or all round for None."""
    def f(t, a, i):
        out = 0.0
        for t0, t1, amount, side in zones:
            if t0 <= t <= t1:
                k = math.sin(math.pi * (t - t0) / (t1 - t0))
                w = 1.0 if side is None else 0.4 + 0.6 * (0.5 + 0.5 * math.cos(a - side))
                out += amount * k * w * (1.0 if i % 2 else -0.35)
        return out
    return f


def plate_on(bvh, centre, normal, along, w, l, h=0.03, nu=4, nv=4, shingle=False, sink=0.012):
    """A raised scale plate lying on a surface (found with `bvh`), `w` wide and `l` long, its long
    side along `along`. A shingle has its free edge (towards `along`) raised with a lip, so that it
    overlaps the next plate like a roof tile; otherwise every edge is tucked into the surface."""
    n = Vector(normal).normalized()
    y = Vector(along)
    y = (y - n * y.dot(n)).normalized()
    x = y.cross(n)
    bm = bmesh.new()
    g = layer(bm)
    us = [-1 + 2 * i / (nu - 1) for i in range(nu)]
    vs = [-1 + 2 * i / (nv - 1) for i in range(nv)]
    rows = []

    def put(u, v, lift):
        uu = u * (1 - 0.3 * max(0.0, v) ** 2) if shingle else u * (1 - 0.18 * abs(v) ** 3)
        vv = v * (1 - 0.18 * abs(u) ** 3)
        q = Vector(centre) + x * uu * w / 2 + y * vv * l / 2
        hit, hn, _, _ = bvh.ray_cast(q + n * 0.35, -n)
        if hit is None:
            hit, hn = q, n
        vert = bm.verts.new(hit + hn * lift)
        vert[g] = 1.0 - max(abs(u), abs(v))
        return vert

    for v in vs:
        row = []
        for u in us:
            edge = max(abs(u), abs(v))
            if shingle:
                lift = -sink if (abs(u) > 0.999 or v < -0.999) else h * (1 - 0.55 * u * u) * (0.35 + 0.65 * (v + 1) / 2)
            else:
                lift = -sink if edge > 0.999 else h * (1 - edge ** 4)
            row.append(put(u, v, lift))
        rows.append(row)
    if shingle:
        rows.append([put(u, 1.0, -sink) for u in us])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(nu - 1):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
    return fix_normals(bm, n)


# ---- the dome and its scutes ----------------------------------------------------------------------
# The shell is laid out on a flat round map: (0, 0) is the top of the dome, radius 1 its base. A
# map point's angle (0 in front, 90 at +X) and distance from the middle give a point on the dome.

def dome_pt(mu, mv):
    rho = math.hypot(mu, mv)
    s = math.sin(min(rho, 1.0) * math.pi / 2)
    cx, cy = (mu / rho, mv / rho) if rho > 1e-9 else (0.0, 0.0)
    z = SH * max(0.0, 1.0 - s ** SP) ** (1.0 / SP)
    w = SA * (1.0 + 0.05 * cy)                                   # a little broader behind
    return SHELL_C + Vector((w * s * cx, SB * s * cy + 0.10 * (1.0 - s), z))


def dome_nrm(mu, mv, e=1e-3):
    du = dome_pt(mu + e, mv) - dome_pt(mu - e, mv)
    dv = dome_pt(mu, mv + e) - dome_pt(mu, mv - e)
    n = du.cross(dv)
    if n.length < 1e-12:
        return Vector((0, 0, 1))
    n.normalize()
    if n.dot(dome_pt(mu, mv) - SHELL_C) < 0:
        n = -n
    return n


def on_dome(m, lift=0.0):
    return dome_pt(m.x, m.y) + dome_nrm(m.x, m.y) * lift


def phi_of(m):
    return math.degrees(math.atan2(m.x, -m.y))


def map_at(rho, phi):
    p = math.radians(phi)
    return Vector((rho * math.sin(p), -rho * math.cos(p)))


def rim_rho(phi):
    """Where the dome ends: higher over the neck (an arch for it to come out under) and a little
    over the tail."""
    a = abs(phi)
    return 1.0 - 0.15 * bump(a, 0, 36) - 0.035 * bump(a, 180, 26)


def inner_rho(phi):
    """The seam between the big scutes and the ring of marginals round the edge."""
    return rim_rho(phi) - 0.17


def clip_half(poly, mid, n):
    out = []
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        da, db = (a - mid).dot(n), (b - mid).dot(n)
        if da <= 0:
            out.append(a)
        if (da <= 0) != (db <= 0):
            out.append(a + (b - a) * (da / (da - db)))
    return out


# a scute's profile from its middle (q=0) to its edge (q=1): stepped growth rings, a groove at the edge
RINGS = [(0.22, 0.128), (0.29, 0.104), (0.46, 0.098), (0.53, 0.074), (0.70, 0.067), (0.77, 0.044), (1.0, -0.035)]
TOP = 0.135


def scute(i, sites, segs=14, areola=(0.0, 0.0), seed=0.0):
    """One big scute: the cell of the map nearer to sites[i] than to any other site, shrunk by the
    groove, raised in steps from its edge to its middle."""
    ci = sites[i]
    c0 = ci + Vector(areola)
    halves = []
    for j, cj in enumerate(sites):
        if j != i:
            n = (cj - ci).normalized()
            halves.append(((ci + cj) / 2 - n * GW, n))
    poly = [Vector((-3, -3)), Vector((3, -3)), Vector((3, 3)), Vector((-3, 3))]
    for mid, n in halves:
        poly = clip_half(poly, mid, n)

    def reach(d):
        best = 9.0
        for mid, n in halves:
            dn = d.dot(n)
            if dn > 1e-9:
                best = min(best, (mid - c0).dot(n) / dn)
        s, step = 0.0, 0.01
        while s < best:
            p = c0 + d * (s + step)
            if p.length > inner_rho(phi_of(p)) - GW:
                lo, hi = s, s + step
                for _ in range(20):
                    md = (lo + hi) / 2
                    q = c0 + d * md
                    if q.length > inner_rho(phi_of(q)) - GW:
                        hi = md
                    else:
                        lo = md
                return min(best, lo)
            s += step
        return best

    angs = [2 * math.pi * k / segs + 0.3 for k in range(segs)]
    used = set()
    for cn in poly:                                             # put a vertex on every corner
        if cn.length >= inner_rho(phi_of(cn)) - GW:
            continue
        a = math.atan2((cn - c0).y, (cn - c0).x)
        k = min((k for k in range(segs) if k not in used),
                key=lambda k: abs((angs[k] - a + math.pi) % (2 * math.pi) - math.pi))
        used.add(k)
        angs[k] = a
    angs.sort()
    dirs = [Vector((math.cos(a), math.sin(a))) for a in angs]
    reaches = [reach(d) for d in dirs]

    bm = bmesh.new()
    g = layer(bm)
    centre = bm.verts.new(on_dome(c0, TOP))
    centre[g] = 1.0
    loops = []
    for q, h in RINGS:
        ring = []
        for d, s in zip(dirs, reaches):
            qq = q if q >= 1.0 else q * (1.0 + 0.06 * noise.noise(Vector((d.x * 2, d.y * 2, seed + q * 3))))
            m = c0 + d * s * qq
            wob = 0.0 if q >= 1.0 else 0.005 * noise.noise(Vector((m.x * 9, m.y * 9, seed)))
            v = bm.verts.new(on_dome(m, h + wob))
            v[g] = 1.0 - q
            ring.append(v)
        loops.append(ring)
    for j in range(segs):
        bm.faces.new((centre, loops[0][j], loops[0][(j + 1) % segs]))
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], b[j], b[(j + 1) % segs], a[(j + 1) % segs]))
    return fix_normals(bm, dome_nrm(c0.x, c0.y))


def flare(phi):
    """How far the rim's edge reaches out beyond the dome, and how far it rises (or drops)."""
    a = abs(phi)
    out = 0.07 + 0.11 * bump(a, 52, 24) + 0.13 * bump(a, 135, 28) + 0.05 * bump(a, 180, 22) + 0.04 * bump(a, 0, 20)
    up = -0.05 + 0.10 * bump(a, 52, 24) + 0.10 * bump(a, 135, 28) + 0.05 * bump(a, 0, 25)
    return out, up


def marginal(k, n=24, gap=0.9):
    """One plate of the rim: from the seam with the big scutes down to the dome's edge, then out
    over the legs with a pointed tip, so that the rim is gently serrated."""
    phc = 360.0 * k / n
    half = 180.0 / n
    cols = [phc - half + gap, phc, phc + half - gap]
    bm = bmesh.new()
    g = layer(bm)
    grid = []
    for ci, ph in enumerate(cols):
        ph = (ph + 180.0) % 360.0 - 180.0
        tip = 1.0 if ci == 1 else 0.0
        ri, rr = inner_rho(ph) + GW, rim_rho(ph) - 0.01
        n_rim = dome_nrm(*map_at(rr, ph))
        out = Vector((n_rim.x, n_rim.y, 0)).normalized()
        up = Vector((0, 0, 1))
        p2 = on_dome(map_at(rr, ph), 0.06)
        fo, fu = flare(ph)
        p3 = p2 + out * (fo + 0.055 * tip) + up * (fu - 0.015 * tip)
        col = [(on_dome(map_at(ri, ph), -0.03), 0.0),
               (on_dome(map_at(ri + 0.035, ph), 0.045), 0.2 + 0.15 * tip),
               (p2, 0.45 + 0.3 * tip),
               (p3, 0.4 + 0.45 * tip),
               (p3 - up * 0.065 - out * 0.012, 0.25 + 0.2 * tip),
               (on_dome(map_at(rr, ph), -0.07) - up * 0.06, 0.0)]
        verts = []
        for p, gv in col:
            v = bm.verts.new(p)
            v[g] = gv
            verts.append(v)
        grid.append(verts)
    for c in range(2):
        for r in range(5):
            bm.faces.new((grid[c][r], grid[c + 1][r], grid[c + 1][r + 1], grid[c][r + 1]))
    bm.faces.new(list(reversed(grid[0])))
    bm.faces.new(grid[2])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m = map_at(0.95, phc)
    return fix_normals(bm, dome_nrm(m.x, m.y))


def base_dome(az=28, rings=7):
    """The dark shell under the scutes, seen in the grooves between them."""
    bm = bmesh.new()
    layer(bm)
    top = bm.verts.new(on_dome(Vector((0, 0)), -0.01))
    loops = []
    for j in range(1, rings + 1):
        ring = []
        for k in range(az):
            ph = 360.0 * k / az - 180.0
            rho = rim_rho(ph) * (j / rings) ** 0.9 - (0.006 if j == rings else 0.0)
            ring.append(bm.verts.new(on_dome(map_at(rho, ph), -0.01)))
        loops.append(ring)
    for k in range(az):
        bm.faces.new((top, loops[0][k], loops[0][(k + 1) % az]))
    for a, b in zip(loops, loops[1:]):
        for k in range(az):
            bm.faces.new((a[k], b[k], b[(k + 1) % az], a[(k + 1) % az]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def leaflet(length, width, fold=0.012, thick=0.006):
    """A small pointed leaf, stalk at the origin, tip at +Y, folded along its middle; closed, so it
    shows from both sides even where back faces are hidden."""
    bm = bmesh.new()
    layer(bm)
    b = bm.verts.new((0, 0, 0))
    t = bm.verts.new((0, length, -0.01))
    lft = bm.verts.new((-width / 2, length * 0.42, -fold))
    rgt = bm.verts.new((width / 2, length * 0.42, -fold))
    up = bm.verts.new((0, length * 0.42, thick))
    dn = bm.verts.new((0, length * 0.42, -thick))
    for a, c in ((b, lft), (lft, t), (t, rgt), (rgt, b)):
        bm.faces.new((a, c, up))
        bm.faces.new((c, a, dn))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- materials ----------------------------------------------------------------------------------------

class Nodes:
    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new
        self._co = None

    @property
    def co(self):
        if self._co is None:
            self._co = self.new("ShaderNodeTexCoord").outputs["Object"]
        return self._co

    def attr(self, name="grad"):
        a = self.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs["Fac"]

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        n.inputs["Roughness"].default_value = rough
        self.link(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(self, src, a, b, c=0.0, d=1.0):
        r = self.new("ShaderNodeMapRange")
        r.interpolation_type = 'SMOOTHSTEP'
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b
        r.inputs["To Min"].default_value, r.inputs["To Max"].default_value = c, d
        self.link(src, r.inputs["Value"])
        return r.outputs["Result"]

    def math(self, op, a, b=None, c=None):
        m = self.new("ShaderNodeMath")
        m.operation = op
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                m.inputs[i].default_value = x
            else:
                self.link(x, m.inputs[i])
        return m.outputs[0]

    def mix(self, fac, a, b):
        m = self.new("ShaderNodeMix")
        m.data_type = 'RGBA'
        for sock, x in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, str):
                sock.default_value = (*kit.srgb(x), 1.0)
            elif isinstance(x, tuple):
                sock.default_value = x
            else:
                self.link(x, sock)
        return m.outputs[2]

    def value(self, colour, v):
        h = self.new("ShaderNodeHueSaturation")
        if isinstance(colour, str):
            h.inputs["Color"].default_value = (*kit.srgb(colour), 1.0)
        else:
            self.link(colour, h.inputs["Color"])
        if isinstance(v, (int, float)):
            h.inputs["Value"].default_value = v
        else:
            self.link(v, h.inputs["Value"])
        return h.outputs["Color"]

    def gradient(self, src, stops):
        r = self.new("ShaderNodeValToRGB")
        els = r.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
        els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
        for pos, hexcode in stops[1:-1]:
            els.new(pos).color = (*kit.srgb(hexcode), 1.0)
        self.link(src, r.inputs["Fac"])
        return r.outputs["Color"]

    def up(self, lo, hi):
        geo = self.new("ShaderNodeNewGeometry")
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(geo.outputs["Normal"], sep.inputs[0])
        return self.ramp(sep.outputs[2], lo, hi)

    def edge(self, radius=0.02, lo=0.997, hi=0.93):
        bev = self.new("ShaderNodeBevel")
        bev.samples = 6
        bev.inputs["Radius"].default_value = radius
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(bev.outputs["Normal"], dot.inputs[0])
        self.link(geo.outputs["Normal"], dot.inputs[1])
        return self.ramp(dot.outputs["Value"], lo, hi)

    def cavity(self, distance=0.15, lo=0.95, hi=0.45):
        ao = self.new("ShaderNodeAmbientOcclusion")
        ao.only_local = True
        ao.samples = 8
        ao.inputs["Distance"].default_value = distance
        return self.ramp(ao.outputs["AO"], lo, hi)

    def island(self):
        return self.new("ShaderNodeNewGeometry").outputs["Random Per Island"]

    def near(self, points, r0, r1):
        out = None
        for p in points:
            d = self.new("ShaderNodeVectorMath")
            d.operation = 'DISTANCE'
            self.link(self.co, d.inputs[0])
            d.inputs[1].default_value = tuple(p)
            f = self.ramp(d.outputs["Value"], r0, r1, 1.0, 0.0)
            out = f if out is None else self.math('MAXIMUM', out, f)
        return out

    def out(self, mat, col):
        self.link(col, kit.principled(mat).inputs["Base Color"])


def base_colour_socket(mat):
    b = kit.principled(mat)
    return b.inputs["Base Color"].links[0].from_socket


def tones(mat, up=None, down=None, up_mix=0.5, down_mix=0.4):
    """Where the surface faces up the colour turns towards `up`, where it faces down towards `down`."""
    N = Nodes(mat)
    hsv = next(n for n in mat.node_tree.nodes if n.type == 'HUE_SAT')
    base = tuple(hsv.inputs["Color"].default_value)
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    N.link(geo.outputs["Normal"], sep.inputs[0])
    colour = None
    for hexcode, amount, lo, hi in ((up, up_mix, 0.15, 0.95), (down, down_mix, -0.10, -0.90)):
        if not hexcode:
            continue
        fac = N.ramp(sep.outputs[2], lo, hi, 0.0, amount)
        colour = N.mix(fac, base if colour is None else colour, hexcode)
    if colour is not None:
        N.link(colour, hsv.inputs["Color"])
    return mat


def skin_material(name, hexcode, up, down, size=0.085, nostrils=()):
    """Leathery skin: kit.scaly's small scales, darker on top and paler below, mottled, darker in
    every fold and crease."""
    m = kit.scaly(kit.material(name, hexcode), size=size, joins=0.34, vary=0.16, shade_down=0.08, rough=0.88)
    tones(m, up=up, down=down, up_mix=0.55, down_mix=0.55)
    N = Nodes(m)
    col = base_colour_socket(m)
    blot = N.ramp(N.noise(N.co, 3.2, 3.0, 0.6), 0.45, 0.75, 0.0, 0.35)
    col = N.mix(blot, col, "#4E4630")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.12, 0.97, 0.55), 0.85), col, "#231D13")
    if nostrils:
        col = N.mix(N.near(nostrils, 0.012, 0.026), col, "#1A140D")
    N.out(m, col)
    return m


def scute_material(name):
    """Horn plates: dark umber at the edges warming to amber-ochre in the middle, fine wavy growth
    lines, sun-bleached and scuffed on top, grime in the grooves."""
    m = kit.material(name, "#A8702F", rough=0.85)
    N = Nodes(m)
    g = N.attr()
    wav = N.math('MULTIPLY_ADD', N.math('SUBTRACT', N.noise(N.co, 4.0, 2.0), 0.5), 0.18, g)
    base = N.gradient(wav, [(0.0, "#24160D"), (0.16, "#3E2614"), (0.4, "#7A4A1F"), (0.68, "#B07A34"), (1.0, "#CF9C4E")])
    lines = N.ramp(N.math('SINE', N.math('MULTIPLY', wav, 2 * math.pi * 9.0)), 0.55, 0.95, 0.0, 0.22)
    col = N.value(base, N.math('MULTIPLY', N.math('SUBTRACT', 1.0, lines), N.math('MULTIPLY_ADD', N.island(), 0.22, 0.88)))
    streak = N.ramp(N.noise(N.co, 7.0, 4.0, 0.65), 0.35, 0.7, 0.75, 1.1)
    col = N.value(col, streak)
    bleach = N.math('MULTIPLY', N.up(0.35, 0.95), N.ramp(N.noise(N.co, 2.6, 4.0, 0.6), 0.42, 0.68, 0.0, 0.55))
    col = N.mix(bleach, col, "#A99A7E")
    col = N.mix(N.math('MULTIPLY', N.edge(0.02, 0.998, 0.94), 0.45), col, "#E2C185")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.1, 0.97, 0.5), 0.8), col, "#160E08")
    N.out(m, col)
    return m


def build_materials():
    H = M(HEAD_AT, rot=HEAD_ROT)
    nostrils = [H @ Vector((s * 0.05, -0.405, 0.075)) for s in (-1, 1)]
    mats = {
        "skin": skin_material("Skin", "#7E7556", up="#5E563A", down="#A3A386", nostrils=nostrils),
        "plate": skin_material("ScalePlate", "#8A8160", up="#6E6646", down="#A9A88C", size=0.3),
        "scute": scute_material("Scute"),
    }
    groove = kit.material("Groove", "#1E130B", rough=0.9)
    N = Nodes(groove)
    N.out(groove, N.value("#24170E", N.ramp(N.noise(N.co, 6.0, 3.0), 0.3, 0.7, 0.7, 1.15)))
    mats["groove"] = groove
    pl = kit.scaly(kit.material("Plastron", "#B39A66"), size=0.4, joins=0.4, vary=0.1, rough=0.85)
    mats["plastron"] = pl
    horn = kit.material("Horn", "#4D4535", rough=0.75)
    N = Nodes(horn)
    g = N.attr()
    col = N.gradient(g, [(0.0, "#3A3227"), (0.6, "#5E5541"), (1.0, "#A49773")])
    col = N.mix(N.math('MULTIPLY', N.edge(0.015, 0.998, 0.94), 0.5), col, "#B8AC8A")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.06, 0.97, 0.6), 0.7), col, "#17130D")
    N.out(horn, col)
    mats["horn"] = horn
    moss = kit.furry(kit.material("Moss", "#566E2B"), strength=0.32, mottle=0.22, fine=70.0, length=1.4)
    N = Nodes(moss)
    col = base_colour_socket(moss)
    col = N.mix(N.ramp(N.noise(N.co, 9.0, 3.0), 0.55, 0.75, 0.0, 0.6), col, "#8E9A3E")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.06, 0.97, 0.6), 0.7), col, "#1F2810")
    N.out(moss, col)
    mats["moss"] = moss
    cap = kit.material("MushroomCap", "#9A5A33", rough=0.8)
    N = Nodes(cap)
    g = N.attr()
    N.out(cap, N.gradient(g, [(0.0, "#E6D6B2"), (0.3, "#D2B07C"), (0.65, "#A4643A"), (1.0, "#6E3B20")]))
    mats["cap"] = cap
    mats["stem"] = kit.furry(kit.material("MushroomStem", "#E4D8BC"), strength=0.12, mottle=0.05, fine=40.0, length=4.0)
    fern = kit.material("Fern", "#5E8A34", rough=0.8)
    N = Nodes(fern)
    g = N.attr()
    col = N.gradient(g, [(0.0, "#3F5E22"), (0.6, "#5F8A33"), (1.0, "#8DB04C")])
    col = N.value(col, N.math('MULTIPLY_ADD', N.island(), 0.25, 0.85))
    N.out(fern, col)
    mats["fern"] = fern
    mats["eye"] = kit.material("Eye", "#140D0A", rough=0.12, coat=1.0)
    return mats


# ---- the tortoise -----------------------------------------------------------------------------------

def build():
    rnd = random.Random(7)
    mats = build_materials()
    t = Prop("Turtle")
    t.tally = {}

    def add(part, bm, mat, at=None):
        layer(bm)
        if at is not None:
            bm.transform(at)
        t.tally[part] = t.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        t.add(bm, mats[mat] if isinstance(mat, str) else mat)

    # ---- shell: dark base dome, 13 stepped scutes, 24 marginals, plastron underneath ---------------------
    sites = [(0.0, -0.52), (0.0, -0.245), (0.0, 0.03), (0.0, 0.30), (0.0, 0.565)]
    sites += [(sx * 0.47, v) for sx in (-1, 1) for v in (-0.37, -0.09, 0.19, 0.46)]
    sites = [Vector((x + rnd.uniform(-0.012, 0.012), y + rnd.uniform(-0.012, 0.012))) for x, y in sites]
    shell_bm = bmesh.new()
    add("shell base", base_dome(), "groove")
    for i, s in enumerate(sites):
        areola = (0.0, 0.03) if abs(s.x) < 0.1 else (-0.06 * math.copysign(1, s.x), 0.02)
        bm = scute(i, sites, segs=14, areola=areola, seed=i * 1.7)
        tmp = bpy_mesh_copy(bm)
        shell_bm.from_mesh(tmp)
        free_mesh(tmp)
        add("scutes", bm, "scute")
    for k in range(24):
        add("marginals", marginal(k), "scute")
    pl = rounded_box((2 * SA - 0.26, 2 * SB - 0.2, 0.5), n=2.8, cuts=3)
    for v in pl.verts:
        v.co.x *= 1.0 - 0.12 * smooth01(abs(v.co.y) / (SB - 0.1)) ** 2
    add("plastron", pl, "plastron", M((0, SHELL_C.y + 0.02, 0.70)))
    add("body", kit.ball((1.9, 2.3, 0.75), cuts=3), "skin", M((0, SHELL_C.y, 0.95)))
    shell = BVHTree.FromBMesh(shell_bm)

    # ---- legs: sturdy columns mid-step, big scales down the front of the forelegs ---------------------------
    def foreleg(sx, step):
        y0 = -0.78
        pts = [(0.60 * sx, y0, 1.02), (0.95 * sx, y0 - 0.25 + step * 0.3, 0.80), (1.10 * sx, y0 - 0.45 + step * 0.6, 0.55),
               (1.06 * sx, y0 - 0.62 + step, 0.24), (1.04 * sx, y0 - 0.66 + step, 0.10)]
        rad = [0.25, 0.25, 0.26, 0.22, 0.24]
        bm = limb(pts, rad, segs=10, rings=12, seed=sx * 3 + step,
                  folds=wrinkles([(0.38, 0.62, 0.07, None)]))
        grounded(bm)
        bvh = BVHTree.FromBMesh(bm)
        V = [Vector(p) for p in pts]
        for r, tt in enumerate((2.12, 2.36, 2.6, 2.84)):
            p = kit._spline(V, tt)
            tan = (kit._spline(V, tt + 0.02) - kit._spline(V, tt - 0.02)).normalized()
            face = Vector((0.45 * sx, -1.0, 0.0))
            face = (face - tan * face.dot(tan)).normalized()
            for c in (-1, 0, 1):
                ang = math.radians(48 * c + (24 if r % 2 else 0) - 12)
                d = (Matrix.Rotation(ang, 3, tan) @ face).normalized()
                add("leg scales", plate_on(bvh, p + d * 0.24, d, tan, 0.15, 0.15, h=0.03, nu=3, nv=3, shingle=True), "plate")
        add("legs", bm, "skin")
        foot(Vector((1.04 * sx, y0 - 0.72 + step, 0.0)), 8 * sx, (0.50, 0.52, 0.26), 4)

    def hindleg(sx, step):
        pts = [(0.62 * sx, 0.95 + step * 0.3, 0.98), (0.90 * sx, 1.06 + step * 0.6, 0.58), (0.92 * sx, 1.02 + step, 0.22),
               (0.92 * sx, 1.0 + step, 0.10)]
        rad = [0.28, 0.28, 0.27, 0.28]
        bm = limb(pts, rad, segs=10, rings=9, seed=sx * 5 + step, folds=wrinkles([(0.3, 0.55, 0.06, None)]))
        add("legs", grounded(bm), "skin")
        foot(Vector((0.92 * sx, 0.98 + step, 0.0)), 14 * sx, (0.56, 0.56, 0.26), 4)

    def foot(at, yaw, size, claws):
        F = M(at, rot=(0, 0, yaw))
        fb = rounded_box(size, n=2.6, cuts=2)
        for v in fb.verts:
            v.co.x *= 1.0 + 0.12 * (0.5 - v.co.z / size[2])        # a little wider at the sole
        add("feet", grounded(fb, F @ M((0, -0.04, size[2] / 2 - 0.03))), "skin")
        for c in range(claws):
            a = (c - (claws - 1) / 2) * 0.42
            base = Vector((math.sin(a) * size[0] * 0.40, -math.cos(a) * size[1] * 0.44 - 0.04, 0.075))
            cl = tube([(0, 0, 0), (0, -0.06, -0.005), (0, -0.105, -0.045)], [0.046, 0.036, 0.014], segs=5, rings=2)
            gl = layer(cl)
            for v in cl.verts:
                v[gl] = min(1.0, max(0.0, -v.co.y / 0.105))
            add("claws", grounded(cl, F @ M(base, rot=(0, 0, math.degrees(a)))), "horn")

    foreleg(-1, -0.22)             # the near foreleg steps forward
    foreleg(1, 0.12)
    hindleg(-1, 0.14)
    hindleg(1, -0.16)              # the far hind leg steps forward with it

    # ---- tail: short, pointed, tucked under the back of the rim ------------------------------------------------
    add("tail", limb([(0.0, 1.25, 0.78), (0.05, 1.62, 0.55), (0.12, 1.80, 0.32)], [0.13, 0.08, 0.02], segs=6, rings=4), "skin")

    # ---- neck: long and wrinkled, lifting the head clear of the shell --------------------------------------------
    H = M(HEAD_AT, rot=HEAD_ROT)
    joint = H @ Vector((0, 0.22, -0.10))
    neck = limb([(0.0, -0.75, 1.02), (-0.02, -1.25, 1.12), (-0.07, -1.70, 1.36), joint], [0.31, 0.28, 0.24, 0.21],
                segs=12, rings=14, folds=wrinkles([(0.12, 0.8, 0.06, math.pi), (0.18, 0.32, 0.10, None)]))
    add("neck", neck, "skin")

    # ---- head: cranium, hooked horn beak, lower jaw, eyes under heavy lids, head plates ------------------------------
    cran = rounded_box((0.58, 0.78, 0.48), n=2.5, cuts=5)
    for v in cran.verts:
        f = smooth01(-v.co.y / 0.39)
        v.co.x *= 1.0 - 0.22 * f
        v.co.z *= 1.0 - (0.2 if v.co.z > 0 else 0.1) * f
        for sx in (-1, 1):                                          # brow ridges over the eyes
            d = (v.co - Vector((0.22 * sx, -0.10, 0.16))).length
            v.co.z += 0.035 * bump(d, 0, 0.1)
    face = BVHTree.FromBMesh(cran)
    plates = [((0.0, -0.06, 0.3), 0.22, 0.20), ((-0.07, -0.25, 0.3), 0.11, 0.12), ((0.07, -0.25, 0.3), 0.11, 0.12),
              ((-0.09, 0.15, 0.3), 0.15, 0.16), ((0.09, 0.15, 0.3), 0.15, 0.16)]
    for (x, y, z), w, l in plates:
        hit, nrm, _, _ = face.ray_cast(Vector((x, y, z + 0.4)), Vector((0, 0, -1)))
        add("head plates", plate_on(face, hit, nrm, (0, 1, 0), w, l, h=0.022), "plate", H)
    add("head", cran, "skin", H)
    beak = rounded_box((0.40, 0.25, 0.25), n=2.4, cuts=3)
    for v in beak.verts:
        f = smooth01(-v.co.y / 0.125)
        v.co.x *= 1.0 - 0.28 * f
        if v.co.z < 0:
            v.co.z -= 0.05 * max(0.0, 1 - abs(v.co.x) / 0.12) ** 2 * f
    gb = layer(beak)
    for v in beak.verts:
        v[gb] = smooth01(-v.co.z / 0.16)
    add("beak", beak, "horn", H @ M((0, -0.305, -0.065)))
    jaw = rounded_box((0.47, 0.52, 0.19), n=2.4, cuts=3)
    for v in jaw.verts:
        v.co.x *= 1.0 - 0.32 * smooth01(-v.co.y / 0.26)
    add("jaw", jaw, "skin", H @ M((0, -0.08, -0.17)))

    for sx in (-1, 1):
        c = Vector((0.232 * sx, -0.11, 0.065))
        gaze = Vector((0.62 * sx, -0.76, 0.06)).normalized()
        E = seat(c, gaze)
        re = 0.088
        add("eyes", kit.ball((2 * re, 2 * re, 2 * re), cuts=3), "eye", H @ E)
        outer = 1.0 if (E.to_3x3() @ Vector((1, 0, 0))).y > 0 else -1.0
        add("lids", eyelid(re, outer, upper=True), "skin", H @ E)
        add("lids", eyelid(re, outer, upper=False), "skin", H @ E)

    # ---- moss on top, with mushrooms and a fern --------------------------------------------------------------
    mc = Vector((-0.06, 0.13))
    moss = moss_patch(shell, mc, 0.26, seed=3.0)
    tmp = bpy_mesh_copy(moss)
    mbm = bmesh.new()
    mbm.from_mesh(tmp)
    free_mesh(tmp)
    mossy = BVHTree.FromBMesh(mbm)
    add("moss", moss, "moss")

    def on_moss(m, sink=0.02):
        p, n = dome_pt(m.x, m.y), dome_nrm(m.x, m.y)
        hit, hn, _, _ = mossy.ray_cast(p + n * 0.8, -n)
        return (hit if hit is not None else p) - n * sink, n

    for m, h, r, lean in ((mc + Vector((-0.12, -0.07)), 0.17, 0.075, (-8, -10)), (mc + Vector((-0.17, 0.0)), 0.11, 0.05, (6, -14)),
                          (mc + Vector((-0.06, -0.14)), 0.075, 0.034, (-12, 4))):
        p, n = on_moss(m)
        R = frame_from(p, Vector((0, 1, 0)), n) @ M(rot=(lean[0], lean[1], 0))
        add("mushrooms", lathe([(0, h + 0.005), (r * 0.18, h), (r * 0.18, h * 0.45), (r * 0.24, 0.0), (0, -0.02)], segs=6), "stem", R)
        cp = lathe([(0, r * 0.75), (r * 0.6, r * 0.66), (r * 0.92, r * 0.36), (r, r * 0.08), (r * 0.8, 0.0), (r * 0.2, r * 0.06), (0, r * 0.06)], segs=8)
        gc = layer(cp)
        for v in cp.verts:
            v[gc] = smooth01(v.co.z / (r * 0.75)) if math.hypot(v.co.x, v.co.y) > r * 0.25 or v.co.z > r * 0.2 else 0.0
        add("mushrooms", cp, "cap", R @ M((0, 0, h * 0.94)))

    root, rn = on_moss(mc + Vector((0.05, 0.06)), sink=0.03)
    fern(add, root, rn, height=0.46, lean=Vector((-0.55, -0.6, 0)), pairs=6, size=0.11, seed=1)
    fern(add, root + Vector((0.03, 0.03, 0)), rn, height=0.30, lean=Vector((0.7, 0.2, 0)), pairs=4, size=0.085, seed=2)
    fiddle = [root + Vector((0.0, 0.03, 0.0)), root + Vector((0.0, 0.04, 0.14)), root + Vector((0.02, 0.0, 0.22))]
    for k in range(6):
        a = k * 0.9
        rr = 0.05 * (1 - k / 7)
        fiddle.append(root + Vector((0.02 + rr * math.sin(a) * 0.4, -0.02 - rr * math.sin(a), 0.24 + rr * math.cos(a) - 0.04)))
    fb = tube(fiddle, [0.016, 0.014, 0.013] + [0.012 - 0.0012 * k for k in range(6)], segs=5, rings=18)
    gl = layer(fb)
    for v in fb.verts:
        v[gl] = 0.3
    add("fern", fb, "fern")

    t.build(SCALE)
    return t


def bpy_mesh_copy(bm):
    import bpy
    me = bpy.data.meshes.new("tmp_copy")
    bm.to_mesh(me)
    return me


def free_mesh(me):
    import bpy
    bpy.data.meshes.remove(me)


def eyelid(re, outer, upper=True):
    """A heavy lid round an eyeball of radius `re` that looks along -Y: it arches over the eye and
    droops a little at the outer corner; its edge is thick and rolls in to touch the eye."""
    us = [-80, -55, -28, 0, 28, 55, 80]
    bm = bmesh.new()
    layer(bm)

    def edge(u):
        k = u / 80.0
        if upper:
            return 17.0 - 22.0 * k * k - 9.0 * max(0.0, outer * k)
        return -30.0 + 9.0 * (1 - k * k) - 3.0 * max(0.0, outer * k)

    sgn = 1.0 if upper else -1.0
    rows = []
    for r_fac, dv in ((0.99, -3.0), (1.17, 0.0), (1.22, 20.0), (1.14, 48.0), (0.8, 88.0)):
        row = []
        for u in us:
            v = edge(u) + sgn * dv
            v = max(-89.0, min(89.0, v))
            if dv >= 88.0:
                v = 89.0 * sgn
            ur, vr = math.radians(u), math.radians(v)
            d = Vector((math.sin(ur) * math.cos(vr), -math.cos(ur) * math.cos(vr), math.sin(vr)))
            row.append(bm.verts.new(d * re * r_fac))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for j in range(len(us) - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    return fix_normals(bm, Vector((0, -1, 0.6 * sgn)))


def moss_patch(bvh, c, radius, seed=0.0, segs=16, rings=4):
    """A lumpy cushion of moss lying over the scutes (found with `bvh`), with a ragged outline."""
    bm = bmesh.new()
    layer(bm)

    def place(m, thick):
        p, n = dome_pt(m.x, m.y), dome_nrm(m.x, m.y)
        hit, _, _, _ = bvh.ray_cast(p + n * 0.6, -n)
        if hit is None:
            hit = p + n * 0.1
        return hit + n * thick

    top = bm.verts.new(place(c, 0.075))
    loops = []
    for j in range(1, rings + 1):
        q = j / rings
        ring = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            rr = radius * (0.72 + 0.45 * (noise.noise(Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, seed))) + 0.5))
            m = c + Vector((math.cos(a), math.sin(a))) * rr * q
            th = -0.012 if j == rings else 0.075 * (1 - q ** 2.4) + 0.02 * noise.noise(Vector((m.x * 14, m.y * 14, seed)))
            ring.append(bm.verts.new(place(m, th)))
        loops.append(ring)
    for k in range(segs):
        bm.faces.new((top, loops[0][k], loops[0][(k + 1) % segs]))
    for a, b in zip(loops, loops[1:]):
        for k in range(segs):
            bm.faces.new((a[k], b[k], b[(k + 1) % segs], a[(k + 1) % segs]))
    return fix_normals(bm, dome_nrm(c.x, c.y))


def fern(add, root, n, height, lean, pairs, size, seed):
    """A fern frond: a stalk rising from `root` and arching over towards `lean`, with pairs of
    leaflets that shrink towards the tip."""
    n = Vector(n)
    lean = Vector(lean)
    pts = [root, root + n * height * 0.35, root + n * height * 0.75 + lean * height * 0.25,
           root + n * height * 0.95 + lean * height * 0.6, root + n * height * 0.85 + lean * height * 0.95]
    st = tube(pts, [0.016, 0.014, 0.011, 0.008, 0.004], segs=5, rings=10)
    gl = layer(st)
    for v in st.verts:
        v[gl] = 0.2
    add("fern", st, "fern")
    rnd = random.Random(seed)
    for k in range(pairs):
        tt = 1.3 + 2.6 * k / max(1, pairs - 1)
        p = kit._spline(pts, tt)
        tan = (kit._spline(pts, min(3.999, tt + 0.03)) - kit._spline(pts, tt - 0.03)).normalized()
        up = n - tan * n.dot(tan)
        up = up.normalized() if up.length > 1e-4 else Vector((0, 0, 1))
        side = tan.cross(up).normalized()
        s = size * (1.0 - 0.55 * k / max(1, pairs - 1))
        for sgn in (-1, 1):
            d = (side * sgn * 0.85 + tan * 0.5).normalized()
            d = (d + up * rnd.uniform(-0.15, 0.1)).normalized()
            lf = leaflet(s, s * 0.36)
            gl = layer(lf)
            for v in lf.verts:
                v[gl] = 0.4 + 0.6 * v.co.y / s
            add("fern", lf, "fern", frame_from(p, d, up))
    tip = leaflet(size * 0.5, size * 0.2)
    gl = layer(tip)
    for v in tip.verts:
        v[gl] = 0.8
    add("fern", tip, "fern", frame_from(pts[-1], (pts[-1] - pts[-2]).normalized(), n))


def bake(turtle, texture, samples=48):
    """Everything but the glossy eyes becomes one textured mesh: the patterns, the tones and soft
    shading in the creases are baked into its colour image. Roblox gets two MeshParts."""
    eyes = [ob for ob in turtle.objects if ob.name.endswith("_Eye")]
    body = kit.bake_texture([ob for ob in turtle.objects if ob not in eyes], texture, name="Turtle_Body",
                            shade=0.55, soften=2, rough=0.85, samples=samples, uv_angle=70.0, uv_margin=0.004,
                            pack_margin=0.003)
    for ob in eyes:
        ob.name = ob.data.name = "Turtle_Eyes"
    turtle.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write --views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,front,face,side",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--bake-samples", type=int, default=48)
    ap.add_argument("--quick", action="store_true", help="with --review: only --views instead of all eight")
    ap.add_argument("--title", default="Turtle review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "turtle_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    turtle = build()
    print("triangles by part:", dict(sorted(turtle.tally.items(), key=lambda kv: -kv[1])))
    print("triangles before baking:", sum(turtle.tally.values()))
    H = M(HEAD_AT, rot=HEAD_ROT)
    head = H @ Vector((0, -0.1, 0.0))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(turtle, samples=samples, focus=(head.x, head.y + 0.4, head.z - 0.35))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.48, -1.0, 0.16)).normalized() * 3.6, head + Vector((0.05, 0.12, -0.08)), 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(min(a.samples, 16))
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        print("peek", a.peek)
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(turtle, os.path.abspath(a.texture), a.bake_samples)
    tris = turtle.triangles()
    lo, hi = turtle.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = turtle.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(turtle.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        rig, review = rig_for(a.samples)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            rig.sheet(os.path.abspath(a.review), shots("full") if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
