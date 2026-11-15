"""LavaWolf pet, hero-quality remake: a heavy wolf of cooled lava, dark basalt plates and coarse fur
with magma glowing in the seams, and a mane and tail of flame-shaped locks whose tips run hot.
Built from scratch by script, on the methods of the Dragon (models/pets/dragon.py) and the FrostWolf
(models/pets/frostwolf.py), which is its sibling.

    python models/pets/lavawolf.py --review out/lavawolf.png
    python models/pets/lavawolf.py --export models/export/lavawolf.fbx

Style: a believable fantasy creature in the same family as the Dragon and FrostWolf, not a cartoon and
not a recolour of FrostWolf. Must-haves:
  1. A heavier, more powerful build than FrostWolf: broad shoulders, a low head carriage, a thick neck, a
     deep chest; legs with upper muscle, wrists, hocks, dewclaws, big paws with claws.
  2. Surface: dark basalt. Rock plates down the back and on the shoulders and thighs, coarse short fur
     clumps with rough edges elsewhere. Plates are darkest in their middles and warm towards their rims;
     magma glows in the seams between them (the Dragon's ember seams). Restrained: seams and a few hot
     spots, not a lit-up body.
  3. A mane and tail of flame-shaped locks whose tips heat to orange and yellow; a smouldering tail tip.
  4. A calm, confident face: small glowing ember eyes in sockets (no whites, lids or irises), thin brows
     set above the eye with a gap, a mouth line level or a little raised at the back.
  5. Charcoal and basalt blacks with warm brown-grey, magma orange to yellow in the seams. Matte rock with
     baked roughness variation. Body up to about 16k triangles, about 3 to 3.5 studs tall, under 5 long.
"""
import argparse
import bisect
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, rounded_box  # noqa: E402

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

NAME = "LavaWolf"
SCALE = 1.0
HEAD_AT = (-0.04, -1.64, 2.56)    # the back of the skull: lower and further forward than FrostWolf's
HEAD_ROT = (9, 2, -13)             # nose a little down, a slight tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.04
THREADS = 4
LEG_DROP = 0.14                    # the lower legs are shortened by this much after building

# The upper head as sections from the back of the skull to the nose (nose towards -y):
# y, top z, half width of the top plane, cheek z, cheek half width, lip z, lip half width.
SKULL = [
    (0.12, 0.10, 0.08, 0.00, 0.20, -0.14, 0.13),
    (0.02, 0.27, 0.15, 0.04, 0.33, -0.19, 0.24),
    (-0.12, 0.33, 0.185, 0.03, 0.40, -0.20, 0.28),
    (-0.28, 0.31, 0.18, 0.00, 0.35, -0.20, 0.26),
    (-0.41, 0.235, 0.14, -0.03, 0.245, -0.185, 0.205),
    (-0.55, 0.195, 0.115, -0.05, 0.18, -0.175, 0.17),
    (-0.70, 0.17, 0.10, -0.06, 0.15, -0.17, 0.145),
    (-0.83, 0.15, 0.085, -0.065, 0.125, -0.165, 0.12),
    (-0.91, 0.115, 0.065, -0.065, 0.095, -0.155, 0.09),
    (-0.95, 0.06, 0.038, -0.07, 0.055, -0.135, 0.05),
]
# The lower jaw: y, top z, top half width, jaw-corner z, jaw-corner half width, chin-keel z.
JAW = [
    (0.02, -0.16, 0.23, -0.31, 0.23, -0.35),
    (-0.10, -0.175, 0.25, -0.35, 0.23, -0.42),
    (-0.33, -0.18, 0.21, -0.33, 0.18, -0.385),
    (-0.56, -0.175, 0.155, -0.29, 0.135, -0.33),
    (-0.73, -0.165, 0.125, -0.25, 0.105, -0.275),
    (-0.83, -0.16, 0.095, -0.22, 0.075, -0.24),
    (-0.88, -0.155, 0.05, -0.195, 0.04, -0.205),
]

# colours (sRGB) along the coat: 0 the spine, 1 the belly
PAL = [(0.0, "#131113"), (0.3, "#1B1819"), (0.55, "#272120"), (0.8, "#41352E"), (1.0, "#5A493D"), (1.15, "#6A5546")]
DARK = "#0B0909"
GLOW_HEX = "#FF9A2E"
ROCK_MID, ROCK_RIM = "#121011", "#4A3326"      # a plate darkest in its middle, warm towards its rim
# the heat ramp of the flame tips: (position, sRGB, alpha = how much it covers the coat colour)
HEAT = [(0.0, "#4A1306", 0.0), (0.28, "#8A240B", 0.85), (0.55, "#E0500F", 1.0), (0.8, "#FF8E22", 1.0), (1.0, "#FFCB55", 1.0)]

# ---- small helpers ----------------------------------------------------------------------------------

def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _super(a, n):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def _table(points, x):
    if x <= points[0][0]:
        return points[0][1]
    for (x0, v0), (x1, v1) in zip(points, points[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def smooth(x, a, b):
    """0 at a, 1 at b, smooth in between (a may be larger than b)."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


V = Vector

_PAL = [(p, Vector(kit.srgb(h))) for p, h in PAL]


def band(b):
    """The coat colour (linear RGB) at band value b: 0 midnight spine ... 1 pale belly, 1.15 tail tip."""
    if b <= _PAL[0][0]:
        return _PAL[0][1].copy()
    for (p0, c0), (p1, c1) in zip(_PAL, _PAL[1:]):
        if b <= p1:
            return c0.lerp(c1, smooth(b, p0, p1))
    return _PAL[-1][1].copy()


VERT_LAYERS = ("fu", "fq", "fs", "gloss", "grad", "heat", "ember", "pr", "crack")


def ensure_layers(bm):
    for name in VERT_LAYERS:
        if bm.verts.layers.float.get(name) is None:
            bm.verts.layers.float.new(name)
    if bm.verts.layers.float_color.get("col") is None:
        bm.verts.layers.float_color.new("col")
    if bm.faces.layers.float.get("boost") is None:
        bm.faces.layers.float.new("boost")
    return bm


def set_layer(bm, name, value):
    ensure_layers(bm)
    lay = bm.verts.layers.float[name]
    for v in bm.verts:
        v[lay] = value(v) if callable(value) else value
    return bm


def paint(bm, fn):
    """Vertex colour 'col' = fn(co, normal) (linear RGB)."""
    ensure_layers(bm)
    bm.normal_update()
    lay = bm.verts.layers.float_color["col"]
    for v in bm.verts:
        c = fn(v.co, v.normal)
        v[lay] = (c[0], c[1], c[2], 1.0)
    return bm


def sharpen(bm, degrees):
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def profile_round(k=10, n=2.0):
    return [_super(math.pi / 2 + 2 * math.pi * j / k, n) for j in range(k)]


P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]
P_LIMB = [(0.0, 1.0), (0.5, 0.86), (0.86, 0.48), (1.0, 0.0), (0.88, -0.5), (0.5, -0.88), (0.0, -1.0), (-0.5, -0.88),
          (-0.88, -0.5), (-1.0, 0.0), (-0.86, 0.48), (-0.5, 0.86)]
P_CLAW5 = [(0, 1.0), (0.6, 0.15), (0.35, -0.7), (-0.35, -0.7), (-0.6, 0.15)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]


def loft(points, radii, profile, up=(0, 0, 1), rings=None):
    """The 2D `profile` carried along a smooth path through `points`, its up side turned towards `up`.
    Radii are numbers or (side, up) pairs. Each vertex stores how far along it is in 'grad'."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = rings or (n - 1) * 4
    ups = [Vector(u) for u in up] if isinstance(up[0], (tuple, list, Vector)) else [Vector(up)] * n
    rad = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]
    bm = ensure_layers(bmesh.new())
    lay = bm.verts.layers.float["grad"]
    path = [_cr(pts, i / rings * (n - 1)) for i in range(rings + 1)]
    loops, m = [], len(profile)
    for i, p in enumerate(path):
        u = i / rings * (n - 1)
        t = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        z = _cr(ups, u)
        z = z - t * z.dot(t)
        z = z.normalized() if z.length > 1e-6 else t.orthogonal().normalized()
        x = z.cross(t)
        rx = max(_cr([r[0] for r in rad], u), 1e-3)
        rz = max(_cr([r[1] for r in rad], u), 1e-3)
        ring = []
        for a, b in profile:
            v = bm.verts.new(p + x * (a * rx) + z * (b * rz))
            v[lay] = i / rings
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    for ring, tip in ((loops[0], path[0]), (loops[-1], path[-1])):
        c = bm.verts.new(tip)
        c[lay] = ring[0][lay]
        for j in range(m):
            bm.faces.new((ring[j], ring[(j + 1) % m], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def mass(points, radii, up, rings=None):
    """A muscle: a smooth teardrop mass along `points`."""
    return loft(points, radii, profile_round(10, 2.2), up=up, rings=rings or (len(points) - 1) * 3)


def lens(outline, thick, rows=((0.55, 0.8), (1.0, 0.0)), centre=(0.0, 0.0)):
    """A flat blade or pebble in the XZ plane: `thick` through the middle, thinning to a sharp rim."""
    bm = ensure_layers(bmesh.new())
    cx, cz = centre
    n = len(outline)
    rim = [bm.verts.new((a, 0.0, b)) for a, b in outline]
    for sgn in (1, -1):
        mid = bm.verts.new((cx, sgn * thick / 2, cz))
        prev = None
        for rho, k in rows:
            loop = rim if k == 0.0 else [bm.verts.new((cx + (a - cx) * rho, sgn * thick / 2 * k, cz + (b - cz) * rho)) for a, b in outline]
            for j in range(n):
                if prev is None:
                    bm.faces.new((mid, loop[j], loop[(j + 1) % n]))
                else:
                    bm.faces.new((prev[j], loop[j], loop[(j + 1) % n], prev[(j + 1) % n]))
            prev = loop
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def facing(origin, out, along):
    """A transform for a shape lying on a surface: X runs `along`, Y looks out along `out`."""
    y = Vector(out).normalized()
    x = Vector(along)
    x = (x - y * x.dot(y)).normalized()
    z = x.cross(y)
    if z.z < 0:
        y, z = -y, -z
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


class Skin:
    """A smooth skin over sections along a path (the Dragon's): positions are (s, angle), s along the
    path from the head end, the angle round the section in degrees, 90 at the spine, -90 at the belly.
    Each section is x, y, z, half width, height above, depth below, squareness, keel."""

    def __init__(self, sections, shoulders, samples=40):
        k = len(sections) - 1
        centres = [Vector(sec[:3]) for sec in sections]
        self.samples = samples
        self.pts = [_cr(centres, i / samples) for i in range(k * samples + 1)]
        self.par = [[_cr([sec[j] for sec in sections], i / samples) for j in range(3, 8)] for i in range(k * samples + 1)]
        self.len = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.len.append(self.len[-1] + (b - a).length)
        self.L = self.len[-1]
        n = len(self.pts)
        self.T = [(self.pts[min(i + 1, n - 1)] - self.pts[max(i - 1, 0)]).normalized() for i in range(n)]
        up = Vector((0, 0, 1))
        self.U = [(up - t * up.dot(t)).normalized() for t in self.T]
        for i in range(shoulders * samples - 1, -1, -1):
            u, axis = self.U[i + 1], self.T[i + 1].cross(self.T[i])
            if axis.length > 1e-9:
                u = Matrix.Rotation(self.T[i + 1].angle(self.T[i]), 3, axis.normalized()) @ u
            self.U[i] = (u - self.T[i] * u.dot(self.T[i])).normalized()
        self.kd = KDTree(n)
        for i, p in enumerate(self.pts):
            self.kd.insert(p, i)
        self.kd.balance()

    def s_of(self, index):
        x = index * self.samples
        i = min(int(x), len(self.len) - 2)
        return self.len[i] + (self.len[i + 1] - self.len[i]) * (x - i)

    def index_of(self, s):
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.len) - 2)
        return (i + (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)) / self.samples

    def at(self, s):
        s = min(max(s, 0.0), self.L)
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.pts) - 2)
        f = (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)
        c = self.pts[i].lerp(self.pts[i + 1], f)
        t = self.T[i].lerp(self.T[i + 1], f).normalized()
        u = self.U[i].lerp(self.U[i + 1], f)
        u = (u - t * u.dot(t)).normalized()
        w, a, b, n, keel = (p + (q - p) * f for p, q in zip(self.par[i], self.par[i + 1]))
        return c, t, u, t.cross(u), w, a, b, n, keel

    def bare(self, s, th):
        c, t, u, side, w, a, b, n, keel = self.at(s)
        x, y = _super(math.radians(th), n)
        h = (a * y + keel * y ** 16) if y > 0 else b * y
        return c + side * (w * x) + u * h

    def normal(self, s, th):
        ds = self.bare(min(s + 0.02, self.L), th) - self.bare(max(s - 0.02, 0.0), th)
        dt = self.bare(s, th + 2.0) - self.bare(s, th - 2.0)
        nrm = dt.cross(ds).normalized()
        return nrm if nrm.dot(self.bare(s, th) - self.at(s)[0]) > 0 else -nrm

    def point(self, s, th, lift=0.0):
        p = self.bare(s, th)
        return p + self.normal(s, th) * lift if lift else p

    def angle_of(self, p):
        """(index along the skin, angle round it) of the skin section nearest the point p."""
        _, k, _ = self.kd.find(p)
        c, t, u = self.pts[k], self.T[k], self.U[k]
        side = t.cross(u)
        r = p - c
        return k / self.samples, math.degrees(math.atan2(r.dot(u), abs(r.dot(side)) + 1e-9))

    def rings(self, k=0.4, lo=0.08, hi=0.2):
        s, out = 0.0, [0.0]
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            out.append(s)
        return out + [self.L]

    def mesh(self, segs=24, cuts=()):
        bm = ensure_layers(bmesh.new())
        ss = self.rings()
        loops = [[bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)] for s in ss]
        for a, b in zip(loops, loops[1:]):
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
        for ring, s in ((loops[0], 0.0), (loops[-1], self.L)):
            c = bm.verts.new(self.at(s)[0])
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        edges = []
        for cut in cuts:
            i = min(range(len(ss)), key=lambda k: abs(ss[k] - self.s_of(cut)))
            ring = loops[i]
            for j in range(segs):
                e = bm.edges.get((ring[j], ring[(j + 1) % segs]))
                if e:
                    edges.append(e)
        if edges:
            bmesh.ops.split_edges(bm, edges=edges)
        return bm


def shell(sections, corners, per=3, m=2, back_cap=0.0, nose_cap=0.0, soft=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives its outline. With
    `soft` above 0 the outline bows out through the corners (a closed spline) instead of running
    straight between them: rounded, but the planes still read."""
    k = len(sections) - 1
    width = len(sections[0])
    rings = []
    for i in range(k * per + 1):
        sec = [_cr([s[j] for s in sections], i / per) for j in range(width)]
        cs = corners(sec)
        pts = []
        nc = len(cs)
        for i0 in range(nc):
            a, b = Vector(cs[i0]), Vector(cs[(i0 + 1) % nc])
            p0, p3 = Vector(cs[i0 - 1]), Vector(cs[(i0 + 2) % nc])
            for f in range(m):
                u = f / m
                straight = a.lerp(b, u)
                curve = 0.5 * ((2 * a) + (b - p0) * u + (2 * p0 - 5 * a + 4 * b - p3) * u * u + (3 * a - p0 - 3 * b + p3) * u ** 3)
                q = straight.lerp(curve, soft)
                pts.append((q.x, q.y))
        rings.append((sec[0], pts))
    bm = ensure_layers(bmesh.new())
    loops = [[bm.verts.new((x, y, z)) for x, z in pts] for y, pts in rings]
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    for ring, dy in ((loops[0], -back_cap), (loops[-1], nose_cap)):
        c = sum((v.co for v in ring), Vector()) / n
        tip = bm.verts.new((c.x, c.y - dy, c.z))
        for j in range(n):
            bm.faces.new((ring[j], ring[(j + 1) % n], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def skull_at(y):
    rows = SKULL
    for a, b in zip(rows, rows[1:]):
        if b[0] <= y <= a[0]:
            f = (y - a[0]) / (b[0] - a[0])
            return tuple(p + (q - p) * f for p, q in zip(a, b))
    return rows[0] if y > rows[0][0] else rows[-1]


def skull_corners(sec):
    y, zt, wt, zc, wc, zb, wb = sec
    furrow = 0.045 * smooth(y, -0.1, -0.24) * smooth(y, -0.52, -0.38)       # a furrow down the forehead between the brows
    return [(0, zt + 0.035 - furrow), (-wt, zt), (-wc, zc), (-wb, zb), (0, zb - 0.01), (wb, zb), (wc, zc), (wt, zt)]


def jaw_corners(sec):
    y, zt, wt, zj, wj, zk = sec
    return [(0, zt), (-wt, zt), (-wj, zj), (0, zk), (wj, zj), (wt, zt)]


class Surface:
    """Finds points exactly on a set of meshes, so that details sit on them."""

    def __init__(self, *bms):
        verts, polys = [], []
        for bm in bms:
            base = len(verts)
            bm.verts.index_update()
            verts += [v.co.copy() for v in bm.verts]
            polys += [[base + v.index for v in f.verts] for f in bm.faces]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def ray(self, origin, direction, dist=10.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), dist)
        return loc, nrm

    def hit(self, origin, direction, out=0.0):
        loc, nrm = self.ray(origin, direction)
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


# ---- fur clumps ---------------------------------------------------------------------------------------

CLUMP_U = (0.0, 0.26, 0.52, 0.76)          # rows from the root; the tip is a single point at 1
CLUMP_Q = (-1.0, -0.45, 0.0, 0.45, 1.0)    # across


def _clump_width(u):
    grow = 0.66 + 0.34 * math.sin(0.5 * math.pi * min(u / 0.3, 1.0))
    return grow * (1.0 if u <= 0.3 else ((1.0 - u) / 0.7) ** 0.8)


def clump(surf, p, n, flow, length, width, lift=0.07, thick=0.045, tuck=0.03, bend=0.0, seed=0.0, hug=1.0, groove=0.45, jag=0.0, wave=0.0):
    """A pointed lock of fur lying on `surf` from its root `p` (surface normal `n`) along `flow`: a closed
    blade with a ridge down its middle, its root buried, rising like a roof tile towards a free tip.
    `bend` curves it sideways; `hug` (0 to 1) is how closely it follows the surface (0: a straight plane);
    `groove` sinks a furrow down its middle, so each lock reads as two strands joining at the tip.
    `jag` breaks the outline: each row a different width and the tip pushed aside (coarse, chipped
    locks); `wave` bends the lock one way then the other along its length, like a flame.
    Vertex layers: fu (0 root to 1 tip), fq (-1 to 1 across), fs (a random number for this clump)."""
    jr = random.Random(int(seed * 1e6))
    wj = {u: 1.0 + jag * jr.uniform(-1.0, 1.0) for u in CLUMP_U}
    wj[1.0] = 1.0
    tip_off = jag * jr.uniform(-1.0, 1.0) * 0.5
    n = Vector(n).normalized()
    d = Vector(flow)
    d = d - n * d.dot(n)
    if d.length < 0.25 * Vector(flow).length:            # flow almost straight into the surface: fall back to backwards
        d = Vector((0, 1, -0.3)) - n * Vector((0, 1, -0.3)).dot(n)
    d.normalize()
    side = n.cross(d)
    bm = ensure_layers(bmesh.new())
    lu, lq, ls = (bm.verts.layers.float[k] for k in ("fu", "fq", "fs"))

    def place(u, q, top):
        flat = p + d * (u * length) + side * (q * width * _clump_width(u) * wj.get(u, 1.0) + bend * length * u * u
                                              + wave * length * math.sin(2.0 * math.pi * u) * u + tip_off * width * u ** 3)
        sp, sn = flat, n
        if hug > 0:
            loc, nrm = surf.ray(flat + n * 0.5, -n, 1.0)
            if loc is not None and (loc - flat).length < 0.28 and nrm.dot(n) > 0.4:
                sp = flat.lerp(loc, hug)
                sn = n.lerp(nrm, hug * 0.7).normalized()
            else:                                          # off the edge of the surface: droop rather than stick out
                sp = flat - n * (0.16 * hug * u * u * length)
        base = -tuck + (lift + tuck) * u ** 2.2
        h = base
        if top:
            lobe = max(1.0 - q * q, 0.0) ** 0.6 * (1.0 - groove * math.exp(-(q / 0.3) ** 2) * min(u / 0.2, 1.0) * (1.0 - u))
            h += thick * lobe * math.sin(math.pi * min(u, 1.0) ** 0.6)
        v = bm.verts.new(sp + sn * h)
        v[lu], v[lq], v[ls] = u, q, seed
        return v

    top, bot = [], []
    for u in CLUMP_U:
        rt, rb = [], []
        for j, q in enumerate(CLUMP_Q):
            if u == 0.0 or j in (0, len(CLUMP_Q) - 1):        # the root row and the rim are shared
                v = place(u, q, False)
                rt.append(v)
                rb.append(v)
            else:
                rt.append(place(u, q, True))
                rb.append(place(u, q, False))
        top.append(rt)
        bot.append(rb)
    tip = place(1.0, 0.0, False)
    for sheet, flip in ((top, False), (bot, True)):
        for a, b in zip(sheet, sheet[1:]):
            for j in range(len(CLUMP_Q) - 1):
                f = (a[j], a[j + 1], b[j + 1], b[j])
                bm.faces.new(f[::-1] if flip else f)
        last = sheet[-1]
        for j in range(len(CLUMP_Q) - 1):
            f = (last[j], last[j + 1], tip)
            bm.faces.new(f[::-1] if flip else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def drape(bm, surf, p, n, base):
    """Lay a flat shape built on the plane through p (normal n) onto the curve of `surf`: each vertex keeps
    its height above that plane, measured from the surface instead, plus `base`."""
    n = Vector(n).normalized()
    for v in bm.verts:
        h = (v.co - p).dot(n)
        flat = v.co - n * h
        loc, nrm = surf.ray(flat + n * 0.3, -n, 0.6)
        if loc is not None:
            v.co = loc + n * (base + h)
    return bm


def crystal(r, h, sides=6, seed=0.0, chisel=0.3):
    """A sharp ice crystal: a slightly tapering prism with a faceted point, base buried below z=0."""
    rnd = random.Random(seed)
    bm = ensure_layers(bmesh.new())
    rings = []
    turn = rnd.uniform(0, math.pi)
    for z, k in ((-0.12 * h, 1.0), (0.6 * h, 0.82)):
        ring = []
        for j in range(sides):
            a = turn + 2 * math.pi * j / sides
            rr = r * k * rnd.uniform(0.85, 1.12)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z + rnd.uniform(-0.04, 0.04) * h)))
        rings.append(ring)
    tip = bm.verts.new((r * chisel * rnd.uniform(-0.5, 0.5), r * chisel * rnd.uniform(-0.5, 0.5), h))
    a, b = rings
    for j in range(sides):
        bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        bm.faces.new((b[j], b[(j + 1) % sides], tip))
    bm.faces.new(a[::-1])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- materials ---------------------------------------------------------------------------------------

def _math(tree, op, a, b, c=None):
    n = tree.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b) if c is None else (a, b, c)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            tree.links.new(v, n.inputs[i])
    return n.outputs[0]


def _attr(tree, name, out="Fac"):
    a = tree.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', name
    return a.outputs[out]


def fur_material(name, scale=(30.0, 30.0, 4.0), strength=0.12, rough=0.9, lip=None):
    """Short fur: the vertex colour 'col' under fine streaks running along the axis with the smallest scale.
    With `lip` (see lip_line) a short soft dark line is painted along each upper lip, per pixel, so it is
    a crisp colour change and not a groove in the mesh."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    b = kit.principled(m)
    coord = t.nodes.new("ShaderNodeTexCoord")
    mp = t.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    t.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 1.0, 3.0
    t.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    v = _math(t, 'MULTIPLY_ADD', nz.outputs["Fac"], 2 * strength, 1 - strength)
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    t.links.new(_attr(t, "col", "Color"), hsv.inputs["Color"])
    t.links.new(v, hsv.inputs["Value"])
    out = hsv.outputs["Color"]
    if lip:
        out = lip_line(t, coord, out, **lip)
    t.links.new(out, b.inputs["Base Color"])
    return m


def lip_line(t, coord, colour, H, a, b, w=(0.005, 0.013), dark=DARK, amount=0.85):
    """Shader nodes: darken `colour` along the segment a-b ((y, z) in head space, on both sides of the
    muzzle). The baked object's coordinates are the built ones, scaled by SCALE and lowered by LEG_DROP,
    so they are taken back into head space first."""
    new, link = t.nodes.new, t.links.new
    loc, rot, sca = H.decompose()
    m1 = new("ShaderNodeMapping")
    m1.inputs["Scale"].default_value = (1.0 / SCALE,) * 3
    m1.inputs["Location"].default_value = Vector((0, 0, LEG_DROP)) - loc
    link(coord.outputs["Object"], m1.inputs["Vector"])
    m2 = new("ShaderNodeMapping")
    m2.inputs["Rotation"].default_value = rot.to_matrix().inverted().to_euler('XYZ')
    m2.inputs["Scale"].default_value = (1.0 / sca.x,) * 3
    link(m1.outputs["Vector"], m2.inputs["Vector"])
    sep = new("ShaderNodeSeparateXYZ")
    link(m2.outputs["Vector"], sep.inputs[0])
    comb = new("ShaderNodeCombineXYZ")
    link(sep.outputs[1], comb.inputs[1])
    link(sep.outputs[2], comb.inputs[2])
    A, B = Vector((0, a[0], a[1])), Vector((0, b[0], b[1]))
    ab = B - A

    def vec(op, x, y=None):
        n = new("ShaderNodeVectorMath")
        n.operation = op
        for i, val in enumerate((x, y)):
            if val is None:
                continue
            if isinstance(val, Vector):
                n.inputs[i].default_value = val
            else:
                link(val, n.inputs[i])
        return n
    ap = vec('SUBTRACT', comb.outputs[0], A)
    dot = vec('DOT_PRODUCT', ap.outputs[0], ab)
    tt = _math(t, 'MINIMUM', _math(t, 'MAXIMUM', _math(t, 'DIVIDE', dot.outputs["Value"], ab.length_squared), 0.0), 1.0)
    sc = vec('SCALE', ab)
    sc.inputs["Scale"].default_value = 1.0
    link(tt, sc.inputs["Scale"])
    near = vec('SUBTRACT', ap.outputs[0], sc.outputs[0])
    dist = vec('LENGTH', near.outputs[0])

    def ramp(x, lo, hi):
        r = new("ShaderNodeMapRange")
        r.interpolation_type = 'SMOOTHSTEP'
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = lo, hi
        link(x, r.inputs["Value"])
        return r.outputs["Result"]
    k = _math(t, 'SUBTRACT', 1.0, ramp(dist.outputs["Value"], w[0], w[1]))
    k = _math(t, 'MULTIPLY', k, ramp(tt, 0.0, 0.35))                                   # fades in from the front
    k = _math(t, 'MULTIPLY', k, ramp(_math(t, 'ABSOLUTE', sep.outputs[0], 0.0), 0.05, 0.09))
    mix = new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    link(_math(t, 'MULTIPLY', k, amount), mix.inputs[0])
    link(colour, mix.inputs[6])
    mix.inputs[7].default_value = (*kit.srgb(dark), 1.0)
    return mix.outputs[2]


def clump_material(name, strength=0.16, tipdark=0.3, rough=0.9, edge=0.14):
    """A fur clump: its colour 'col', fine strands along it, darker towards its tip and rim."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    b = kit.principled(m)
    comb = t.nodes.new("ShaderNodeCombineXYZ")
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fq"), 9.0), comb.inputs[0])
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fu"), 1.3), comb.inputs[1])
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fs"), 13.0), comb.inputs[2])
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 1.0, 2.0
    t.links.new(comb.outputs[0], nz.inputs["Vector"])
    v = _math(t, 'MULTIPLY_ADD', nz.outputs["Fac"], 2 * strength, 1 - strength)
    fu = _attr(t, "fu")
    tip = _math(t, 'MULTIPLY_ADD', _math(t, 'MULTIPLY', fu, fu), -tipdark, 1.0)
    fq = _attr(t, "fq")
    q4 = _math(t, 'POWER', _math(t, 'ABSOLUTE', fq, 0.0), 4.0)
    edge = _math(t, 'MULTIPLY_ADD', q4, -edge, 1.0)
    v = _math(t, 'MULTIPLY', _math(t, 'MULTIPLY', v, tip), edge)
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    t.links.new(_attr(t, "col", "Color"), hsv.inputs["Color"])
    t.links.new(v, hsv.inputs["Value"])
    # heat: flame locks (vertex value "heat") run hot towards their tips, along a flickering edge
    flick = t.nodes.new("ShaderNodeTexNoise")
    flick.inputs["Scale"].default_value, flick.inputs["Detail"].default_value = 1.6, 2.0
    c2 = t.nodes.new("ShaderNodeCombineXYZ")
    t.links.new(_math(t, 'MULTIPLY', fq, 2.5), c2.inputs[0])
    t.links.new(_math(t, 'MULTIPLY', fu, 2.0), c2.inputs[1])
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fs"), 17.0), c2.inputs[2])
    t.links.new(c2.outputs[0], flick.inputs["Vector"])
    up = _math(t, 'ADD', fu, _math(t, 'MULTIPLY', _math(t, 'SUBTRACT', flick.outputs["Fac"], 0.5), 0.5))
    up = _math(t, 'ADD', up, _math(t, 'MULTIPLY', q4, -0.25))
    k = _math(t, 'MULTIPLY', _attr(t, "heat"), _math(t, 'POWER', _math(t, 'MAXIMUM', _math(t, 'MINIMUM', up, 1.0), 0.0), 1.6))
    ramp = t.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    for i, (pos, hexc, alpha) in enumerate(HEAT):
        el = els[i] if i < len(els) else els.new(pos)
        el.position = pos
        el.color = (*kit.srgb(hexc), alpha)
    t.links.new(k, ramp.inputs[0])
    mix = t.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    t.links.new(ramp.outputs["Alpha"], mix.inputs[0])
    t.links.new(hsv.outputs["Color"], mix.inputs[6])
    t.links.new(ramp.outputs["Color"], mix.inputs[7])
    t.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m


# ---- hidden faces and the texture layout (the Dragon's) ---------------------------------------------

def _hemisphere():
    out = [Vector((0, 0, 1))]
    for tilt, n in ((25, 6), (50, 9), (72, 12), (86, 14)):
        t = math.radians(tilt)
        for j in range(n):
            a = 2 * math.pi * (j + 0.5 * (tilt // 25 % 2)) / n
            out.append(Vector((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))))
    return out


OPEN_FULL = 0.4


def cull_and_weigh(parts, keep=("GLOW",)):
    """Delete the faces no camera can see (buried in another shape, under a clump, flat on the floor)
    and mark barely seen ones with the face value "hid", so the unwrap gives them less texture."""
    verts, polys = [], []
    for bm, _ in parts.values():
        base = len(verts)
        bm.verts.index_update()
        verts += [v.co.copy() for v in bm.verts]
        polys += [[base + v.index for v in f.verts] for f in bm.faces]
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = _hemisphere()
    removed = 0
    for key, (bm, _) in parts.items():
        lh = bm.faces.layers.float.get("hid") or bm.faces.layers.float.new("hid")
        lb = bm.faces.layers.float.get("boost")
        if any(k in key for k in keep):
            continue
        bm.normal_update()
        dead = []
        for f in bm.faces:
            n = f.normal
            if n.length < 0.5:
                continue
            c = f.calc_center_median()
            if c.z < 0.02 and n.z < -0.9:
                dead.append(f)
                continue
            rot = n.to_track_quat('Z', 'Y').to_matrix()
            world = [rot @ d for d in dirs]
            o = c + n * 0.003
            free = sum(1 for d in world if bvh.ray_cast(o, d, 60.0)[0] is None)
            if free == 0:
                seen = False
                for p in [c.lerp(v.co, 0.8) for v in f.verts[:8]]:
                    o = p + n * 0.003
                    if any(bvh.ray_cast(o, d, 60.0)[0] is None for d in world):
                        seen = True
                        break
                if not seen:
                    o = c - n * 0.003
                    if sum(1 for d in world if bvh.ray_cast(o, -d, 60.0)[0] is None) < len(dirs) // 3:
                        dead.append(f)
                        continue
            f[lh] = max(0.0, min(1.0, 1.0 - free / len(dirs) / OPEN_FULL)) - (f[lb] if lb else 0.0)
        removed += sum(len(f.verts) - 2 for f in dead)
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return removed


UV_ANGLE, UV_MARGIN, PACK_MARGIN = 85.0, 0.004, 0.003
HIDDEN_SHARE = 0.25
HEAD_BOOST = 0.6


def weigh_islands(ob, keep=HIDDEN_SHARE):
    """After the unwrap: shrink texture islands that are mostly hidden, grow the boosted (head) ones."""
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    lh = bm.faces.layers.float.get("hid")
    if lh is None:
        return
    bm.faces.ensure_lookup_table()
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            continue
        f0, f1 = lf
        same = True
        for v in e.verts:
            u0 = next(l[uvl].uv for l in f0.loops if l.vert is v)
            u1 = next(l[uvl].uv for l in f1.loops if l.vert is v)
            if (u0 - u1).length_squared > 1e-12:
                same = False
                break
        if same:
            parent[find(f0.index)] = find(f1.index)
    islands = {}
    for f in bm.faces:
        islands.setdefault(find(f.index), []).append(f)
    for faces in islands.values():
        area = sum(f.calc_area() for f in faces) or 1.0
        w = sum(f[lh] * f.calc_area() for f in faces) / area
        if abs(w) <= 0.01:
            continue
        k = 1.0 - (1.0 - keep) * w
        loops = [l for f in faces for l in f.loops]
        c = sum((l[uvl].uv for l in loops), Vector((0.0, 0.0))) / len(loops)
        for l in loops:
            l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(me)


class _OpsProxy:
    def __init__(self, ops, pack):
        self._ops, self._pack = ops, pack

    def __getattr__(self, k):
        if k == "uv":
            return _UvProxy(self._ops.uv, self._pack)
        return getattr(self._ops, k)


class _UvProxy:
    def __init__(self, uv, pack):
        self._uv, self._pack = uv, pack

    def __getattr__(self, k):
        return self._pack if k == "pack_islands" else getattr(self._uv, k)


# ---- rock -------------------------------------------------------------------------------------------

def rock_plate(skin, s0, s1, half, centre=90.0, lift=(0.03, 0.1), tuck=-0.025, bow=0.05, pinch=0.3, seed=0, jag=0.2,
               vs=(0, 0.14, 0.5, 0.86, 1), qs=(-1, -0.72, -0.25, 0.25, 0.72, 1)):
    """A basalt plate lying on the skin from s0 to s1, `half` degrees each side of the angle `centre`,
    rising like a roof tile towards its tail end, its rim tucked into the skin and chipped unevenly
    (`jag`). Vertex value "pr": 0 in its middle, 1 on its rim."""
    rnd = random.Random(seed)
    bm = ensure_layers(bmesh.new())
    lpr = bm.verts.layers.float["pr"]
    ds = s1 - s0
    grid = []
    for i, v in enumerate(vs):
        row = []
        for j, q in enumerate(qs):
            rim = i in (0, len(vs) - 1) or j in (0, len(qs) - 1)
            s = s0 + ds * v + bow * (1 - q * q) * v * ds
            th = centre + half * (1 - pinch * abs(2 * v - 1) ** 3) * q
            if rim:
                s += rnd.uniform(-jag, jag) * ds * 0.3
                th += rnd.uniform(-jag, jag) * half * 0.3
                h = tuck
            else:
                h = lift[0] + (lift[1] - lift[0]) * v ** 1.3 + rnd.uniform(-0.01, 0.01)
            vert = bm.verts.new(skin.point(s, th, h))
            vert[lpr] = 1.0 if rim else max(abs(2 * v - 1), abs(q)) * 0.8
            row.append(vert)
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(len(qs) - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bm.normal_update()
    out = skin.normal((s0 + s1) / 2, centre)
    if sum((f.normal for f in bm.faces), Vector()).dot(out) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def rock_colour(bm, var=0.08, rnd=None, warm=1.0):
    """Paint a plate by its "pr" value: darkest in the middle, warm brown towards the rim."""
    ensure_layers(bm)
    lpr = bm.verts.layers.float["pr"]
    lay = bm.verts.layers.float_color["col"]
    mid, rim = Vector(kit.srgb(ROCK_MID)), Vector(kit.srgb(ROCK_RIM))
    f = 1.0 + var * ((rnd.random() if rnd else 0.5) - 0.5) * 2
    for v in bm.verts:
        c = mid.lerp(rim, smooth(v[lpr], 0.25, 1.0) * warm) * f
        v[lay] = (c[0], c[1], c[2], 1.0)
    return bm


def rock_material(name, rough=0.9):
    """Basalt: the vertex colour 'col' under a fine grain and small pits, with a few thin magma cracks
    (a Voronoi edge network in object space, shown only in patches and only where "crack" is set)."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    b = kit.principled(m)
    new, link = t.nodes.new, t.links.new
    coord = new("ShaderNodeTexCoord")
    grain = new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value, grain.inputs["Detail"].default_value = 16.0, 6.0
    link(coord.outputs["Object"], grain.inputs["Vector"])
    v = _math(t, 'MULTIPLY_ADD', grain.outputs["Fac"], 0.5, 0.75)
    pits = new("ShaderNodeTexVoronoi")
    pits.inputs["Scale"].default_value = 34.0
    link(coord.outputs["Object"], pits.inputs["Vector"])
    v = _math(t, 'MULTIPLY', v, _math(t, 'MINIMUM', _math(t, 'MULTIPLY_ADD', pits.outputs["Distance"], 3.0, 0.55), 1.0))
    hsv = new("ShaderNodeHueSaturation")
    link(_attr(t, "col", "Color"), hsv.inputs["Color"])
    link(v, hsv.inputs["Value"])
    cr = new("ShaderNodeTexVoronoi")
    cr.feature = 'DISTANCE_TO_EDGE'
    cr.inputs["Scale"].default_value = 5.5
    link(coord.outputs["Object"], cr.inputs["Vector"])
    patch = new("ShaderNodeTexNoise")
    patch.inputs["Scale"].default_value, patch.inputs["Detail"].default_value = 2.2, 1.0
    link(coord.outputs["Object"], patch.inputs["Vector"])
    mask = _math(t, 'MULTIPLY', _attr(t, "crack"), _math(t, 'MINIMUM', _math(t, 'MAXIMUM', _math(t, 'MULTIPLY_ADD', patch.outputs["Fac"], 6.0, -3.1), 0.0), 1.0))
    d = cr.outputs["Distance"]
    line = _math(t, 'MULTIPLY', mask, _math(t, 'MAXIMUM', _math(t, 'MULTIPLY_ADD', d, -1.0 / 0.022, 1.0), 0.0))
    halo = _math(t, 'MULTIPLY', mask, _math(t, 'MAXIMUM', _math(t, 'MULTIPLY_ADD', d, -1.0 / 0.07, 1.0), 0.0))
    m1 = new("ShaderNodeMix")
    m1.data_type = 'RGBA'
    link(_math(t, 'MULTIPLY', halo, 0.55), m1.inputs[0])
    link(hsv.outputs["Color"], m1.inputs[6])
    m1.inputs[7].default_value = (*kit.srgb("#4A1C0E"), 1.0)
    m2 = new("ShaderNodeMix")
    m2.data_type = 'RGBA'
    link(_math(t, 'MINIMUM', _math(t, 'MULTIPLY', line, 1.4), 1.0), m2.inputs[0])
    link(m1.outputs[2], m2.inputs[6])
    m2.inputs[7].default_value = (*kit.srgb("#FF7418"), 1.0)
    link(m2.outputs[2], b.inputs["Base Color"])
    return m


# ---- the lava wolf -----------------------------------------------------------------------------------

def head_matrix():
    return M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)


SPINE = None      # filled by build(): the Skin, used by the colour rules
EYE_H = []        # the eyes in head space, filled by build()


def body_band(p):
    k, ang = SPINE.angle_of(p)
    b = 1.0 - smooth(ang, -78.0, 25.0)         # 0 high on the back, 1 under the belly
    return 0.04 + 0.8 * b


def head_band(hl):
    """The band value on the head, from head-space coordinates: a charcoal crown fading to a warm
    brown-grey muzzle and jaw, a dark mask round each eye."""
    top, cz = skull_at(hl.y)[1], skull_at(hl.y)[3]
    v = smooth(hl.z, top - 0.02, cz - 0.08)
    b_top = lerp(0.06, 0.5, smooth(hl.y, -0.4, -0.86))
    b = lerp(b_top, 0.86, v)
    for e in EYE_H:
        if (hl.x > 0) != (e.x > 0):
            continue
        d = ((hl - e) * Vector((1.0, 0.8, 1.3))).length
        b = lerp(b, 0.03, 1.0 - smooth(d, 0.05, 0.12))
        a2, b2 = e + Vector((0.01 if e.x > 0 else -0.01, 0.08, 0.02)), e + Vector((0.03 if e.x > 0 else -0.03, 0.26, 0.09))
        ab = b2 - a2
        t = max(0.0, min(1.0, (hl - a2).dot(ab) / ab.length_squared))
        b = lerp(b, 0.06, 0.8 * (1.0 - smooth((a2 + ab * t - hl).length, 0.025, 0.065)) * (1.0 - 0.5 * t))
    return b


def build():
    global SPINE
    EYE_H[:] = []
    fur_body = fur_material("FurBody", scale=(26.0, 5.0, 26.0), strength=0.17)       # coarse streaks along the body
    fur_leg = fur_material("FurLeg", scale=(26.0, 26.0, 5.0), strength=0.15)         # ... and down the legs
    ya, yb = -0.66, -0.45           # the mouth: short, along the upper lip, level in head space (a touch raised at the back as held)
    fur_face = fur_material("FurFace", scale=(44.0, 8.0, 44.0), strength=0.12,
                            lip=dict(H=head_matrix(), a=(ya, skull_at(ya)[5] + 0.006), b=(yb, skull_at(yb)[5] + 0.02)))
    clump_m = clump_material("Clump", strength=0.22, tipdark=0.22, edge=0.12)        # coarse basalt fur
    flame_m = clump_material("Flame", strength=0.18, tipdark=0.0, edge=0.08)         # flame locks: their tips run hot
    rock = rock_material("Rock")
    dark = kit.material("Dark", DARK, rough=0.6)
    nose_m = kit.material("Nose", "#0E0B0B", rough=0.45)
    claw_m = kit.material("Claw", "#2E2826", rough=0.4)
    glow = kit.material("GLOW_Lava", GLOW_HEX, rough=0.3, emit=2.0)

    w = Prop(NAME)
    w.tally = {}
    H = head_matrix()
    Hinv = H.inverted()
    HR = H.to_3x3().normalized()
    rnd = random.Random(11)

    def hs(p):
        return tuple(H @ Vector(p))

    def colour(region, co, n):
        if region == "head":
            return band(head_band(Hinv @ co))
        if region == "jaw":
            return band(0.86)
        if region == "ruff":
            hl = Hinv @ co
            return band(lerp(0.12, 0.6, smooth(hl.z, 0.02, -0.2)))
        if region == "leg":
            return band(leg_band(co, n))
        if region == "tail":
            return band(tail_band(co))
        if region == "paw":
            return band(0.1)
        if region == "mane":
            return band(0.1)
        return band(body_band(co))

    base = []          # (part, bm, material, crease, boost) in world space: the surfaces the fur lies on

    def add_base(part, bm, mat, region, crease=40.0, boost=0.0, colour_fn=None):
        ensure_layers(bm)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
        paint(bm, colour_fn or (lambda co, n: colour(region, co, n)))
        base.append((part, bm, mat, crease, boost))

    def add(part, bm, mat, crease=40.0, boost=0.0):
        ensure_layers(bm)
        lb = bm.faces.layers.float["boost"]
        for f in bm.faces:
            f[lb] = boost
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
            v.co.z -= LEG_DROP * smooth(v.co.z, 0.3, 1.15)       # shorter, sturdier legs
        if crease:
            sharpen(bm, crease)
        w.tally[part] = w.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        w.add(bm, mat)

    # ---- neck and trunk: one skin; a thick neck, a deep chest and a heavy front ---------------------------
    spine = [
        (*hs((0, -0.15, -0.02)), 0.22, 0.24, 0.26, 2.2, 0.0),     # 0 inside the head
        (*hs((0, 0.16, -0.14)), 0.33, 0.31, 0.37, 2.2, 0.0),      # 1 behind the skull
        (0.0, -1.27, 2.27, 0.47, 0.41, 0.53, 2.25, 0.0),          # 2 the neck, thick
        (0.0, -1.03, 2.0, 0.57, 0.49, 0.70, 2.3, 0.01),           # 3 neck base, the chest below
        (0.0, -0.78, 1.86, 0.63, 0.51, 0.80, 2.4, 0.02),          # 4 withers (a hump of muscle) and deep chest
        (0.0, -0.33, 1.82, 0.53, 0.46, 0.66, 2.45, 0.02),         # 5 behind the shoulders
        (0.0, 0.12, 1.80, 0.43, 0.39, 0.46, 2.45, 0.02),          # 6 waist
        (0.0, 0.55, 1.82, 0.45, 0.39, 0.46, 2.4, 0.02),           # 7 hips
        (0.0, 0.92, 1.77, 0.39, 0.35, 0.42, 2.3, 0.01),           # 8 rump
        (0.0, 1.16, 1.73, 0.23, 0.22, 0.26, 2.2, 0.0),            # 9 tail root
        (0.0, 1.24, 1.73, 0.08, 0.08, 0.08, 2.2, 0.0),            # 10
    ]
    skin = Skin(spine, 4)
    SPINE = skin
    add_base("skin", skin.mesh(segs=24, cuts=(2.6, 5.2, 7.6)), fur_body, "body", crease=0)

    # ---- legs --------------------------------------------------------------------------------------------
    legs = []          # (sx, front, key points) for the clump and plate placement

    def leg_band_fn(co, n):
        sx = 1.0 if co.x > 0 else -1.0
        inner = smooth(-n.x * sx, 0.1, 0.75)
        b = 0.18 + 0.3 * inner
        b = lerp(b, 0.08, smooth(co.z, 0.55, 0.2))            # darker socks down to the paws
        top = smooth(co.z, 1.05, 1.65)
        return lerp(b, min(body_band(co), max(b, 0.45)), top)

    global leg_band
    leg_band = leg_band_fn

    def paw(x, y, yaw, size):
        F = M((x, y, 0), rot=(0, 0, yaw), scale=size)
        pad = rounded_box((0.28, 0.31, 0.17), n=3.2, cuts=2)
        pad.transform(F @ M((0, 0.02, 0.085)))
        add_base("paws", pad, fur_leg, "paw", crease=0)
        for tx, ty, s in ((-0.108, -0.105, 0.92), (-0.04, -0.152, 1.0), (0.04, -0.152, 1.0), (0.108, -0.105, 0.92)):
            toe = kit.ball((0.095 * s, 0.135 * s, 0.11 * s), cuts=1)
            ensure_layers(toe)
            toe.transform(F @ M((tx, ty, 0.052)))
            add_base("toes", toe, fur_leg, "paw", crease=0)
            claw = [(tx * 1.05, ty - 0.055 * s, 0.07), (tx * 1.08, ty - 0.1 * s, 0.048), (tx * 1.1, ty - 0.13 * s, 0.0)]
            bm = loft(claw, [0.027, 0.019, 0.003], P_CLAW5, up=(0, -0.3, 1), rings=3)
            bm.transform(F)
            set_layer(bm, "gloss", 0.4)
            add_base("claws", bm, claw_m, "paw", crease=50)

    for sx in (-1, 1):
        step = 0.16 if sx < 0 else 0.0
        fx = sx * 1.2                                  # the forelegs stand wide under broad shoulders
        elbow = V((0.39 * fx, -0.78, 1.04))
        wrist = V((0.37 * fx, -0.92 - step, 0.36))
        foot = V((0.37 * fx, -0.97 - step, 0.12))
        arm = [(0.27 * fx, -0.84, 2.05), (0.40 * fx, -1.1, 1.62), tuple(elbow), tuple(elbow.lerp(wrist, 0.45) + V((0, -0.02, 0))),
               tuple(wrist), tuple(foot)]
        add_base("legs", loft(arm, [(0.25, 0.34), (0.25, 0.31), (0.2, 0.235), (0.17, 0.185), (0.115, 0.13), (0.125, 0.135)],
                              P_LIMB, up=(0, -1, 0), rings=18), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * fx, -0.94, 2.02), (0.48 * fx, -1.05, 1.70), (0.48 * fx, -1.0, 1.40), (0.44 * fx, -0.92, 1.20)],
                                [(0.19, 0.23), (0.2, 0.25), (0.14, 0.17), (0.04, 0.05)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.38 * fx, -0.62, 1.74), (0.46 * fx, -0.66, 1.38), (0.44 * fx, -0.74, 1.10)],
                                [(0.18, 0.19), (0.17, 0.18), (0.05, 0.05)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.42 * fx, -0.88, 1.0), (0.42 * fx, -0.9 - 0.4 * step, 0.75), (0.39 * fx, -0.92 - 0.8 * step, 0.48)],
                                [(0.115, 0.135), (0.1, 0.115), (0.03, 0.03)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        carpal = kit.ball((0.11, 0.11, 0.11), cuts=2)
        carpal.transform(M(wrist + V((0, 0.08, 0.03))))
        add_base("wrists", ensure_layers(carpal), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.4 * fx, -0.68, 1.0), (0.39 * fx, -0.74 - 0.3 * step, 0.76), (0.375 * fx, -0.82 - 0.7 * step, 0.5)],
                                [(0.11, 0.11), (0.095, 0.1), (0.03, 0.03)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        dew = [tuple(wrist + V((-0.08 * sx, 0.02, -0.04))), tuple(wrist + V((-0.11 * sx, -0.02, -0.1))), tuple(wrist + V((-0.11 * sx, -0.05, -0.15)))]
        bm = loft(dew, [0.032, 0.022, 0.004], P_CLAW5, up=(-sx, -0.3, 0), rings=3)
        set_layer(bm, "gloss", 0.4)
        add_base("claws", bm, claw_m, "paw", crease=50)
        paw(foot.x, foot.y - 0.07, 4 * fx, 1.36)
        legs.append((sx, True, elbow, wrist))

        stifle = V((0.44 * sx, 0.44, 1.06))
        hock = V((0.42 * sx, 1.02, 0.50))
        foot = V((0.42 * sx, 0.94, 0.12))
        thigh = [(0.28 * sx, 0.76, 1.98), (0.41 * sx, 0.58, 1.50), tuple(stifle), (0.43 * sx, 0.74, 0.78), tuple(hock),
                 (0.42 * sx, 0.99, 0.34), tuple(foot)]
        add_base("legs", loft(thigh, [(0.31, 0.43), (0.28, 0.38), (0.19, 0.22), (0.155, 0.185), (0.115, 0.135), (0.11, 0.125), (0.12, 0.13)],
                              P_LIMB, up=(0, -1, 0), rings=24), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.30 * sx, 0.99, 2.03), (0.43 * sx, 0.94, 1.70), (0.46 * sx, 0.86, 1.35), (0.43 * sx, 0.76, 1.05)],
                                [(0.18, 0.23), (0.2, 0.25), (0.15, 0.19), (0.04, 0.05)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * sx, 0.56, 1.85), (0.48 * sx, 0.46, 1.50), (0.47 * sx, 0.42, 1.20), (0.44 * sx, 0.44, 1.04)],
                                [(0.17, 0.21), (0.19, 0.23), (0.14, 0.16), (0.04, 0.04)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.44 * sx, 0.56, 1.0), (0.44 * sx, 0.74, 0.86), (0.43 * sx, 0.92, 0.66), (0.42 * sx, 1.01, 0.54)],
                                [(0.11, 0.13), (0.11, 0.13), (0.065, 0.075), (0.03, 0.03)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        hk = kit.ball((0.1, 0.11, 0.11), cuts=2)
        hk.transform(M(hock + V((0, 0.05, 0.0))))
        add_base("hocks", ensure_layers(hk), fur_leg, "leg", crease=0)
        dew = [tuple(foot + V((-0.11 * sx, 0.1, 0.16))), tuple(foot + V((-0.13 * sx, 0.06, 0.1))), tuple(foot + V((-0.13 * sx, 0.03, 0.06)))]
        bm = loft(dew, [0.028, 0.019, 0.004], P_CLAW5, up=(-sx, -0.3, 0), rings=3)
        set_layer(bm, "gloss", 0.4)
        add_base("claws", bm, claw_m, "paw", crease=50)
        paw(foot.x, foot.y - 0.06, 3 * sx, 1.32)
        legs.append((sx, False, stifle, hock))

    # chest muscle: two pectoral masses between the front legs
    for sx in (-1, 1):
        add_base("muscle", mass([(0.13 * sx, -1.1, 1.95), (0.24 * sx, -1.24, 1.60), (0.28 * sx, -1.08, 1.28), (0.29 * sx, -0.92, 1.15)],
                                [(0.22, 0.22), (0.25, 0.25), (0.18, 0.18), (0.04, 0.04)], up=(0, -1, 0)), fur_body, "body", crease=0)

    # ---- tail: a thick core hanging in a low curve, covered in flame locks later ----------------------------
    TAIL = [(0.0, 1.10, 1.82), (0.0, 1.40, 1.92), (0.05, 1.70, 1.84), (0.11, 1.93, 1.60), (0.15, 2.04, 1.34), (0.17, 2.07, 1.12),
            (0.18, 2.04, 0.98), (0.18, 2.0, 0.88)]
    tail_r = [0.17, 0.22, 0.24, 0.22, 0.18, 0.12, 0.06, 0.01]
    tail_bm = loft(TAIL, tail_r, profile_round(12), up=(0, 0, 1), rings=30)
    tail_path = [_cr([V(p) for p in TAIL], i / 60 * (len(TAIL) - 1)) for i in range(61)]

    def tail_t(co):
        k = min(range(len(tail_path)), key=lambda i: (tail_path[i] - co).length_squared)
        return k / 60.0, tail_path[k]

    def tail_band_fn(co):
        t, c = tail_t(co)
        r = co - c
        up = r.z / max(r.length, 1e-6)
        return 0.08 + 0.3 * smooth(-up, -0.2, 0.9)

    global tail_band
    tail_band = tail_band_fn
    add_base("tail core", tail_bm, fur_body, "tail", crease=0)

    # ---- head: built in head space, then turned into place ------------------------------------------------
    skull = shell(SKULL, skull_corners, per=3, m=3, back_cap=0.05, nose_cap=0.01, soft=0.75)
    face = Surface(skull)
    jaw = shell(JAW, jaw_corners, per=2, m=3, back_cap=0.04, nose_cap=0.01, soft=0.7)
    head_parts = [("head", skull, fur_face, "head"), ("head", jaw, fur_face, "jaw")]
    EYE_RAY = ((0.55, -0.62, 0.15), (-0.75, 0.6, -0.04))
    for sx in (-1, 1):
        o, d = V((EYE_RAY[0][0] * sx, EYE_RAY[0][1], EYE_RAY[0][2])), V((EYE_RAY[1][0] * sx, EYE_RAY[1][1], EYE_RAY[1][2]))
        p, nrm = face.hit(o, d)
        EYE_H.append(p.copy())
        # thin level brows set above the eye with a gap, the inner end a touch higher (calm, never a scowl)
        brow = [face.hit(p + Vector((0, dy, dz)) + nrm * 0.3, -nrm, out=0.007)[0]
                for dy, dz in ((-0.07, 0.16), (-0.015, 0.152), (0.055, 0.138), (0.125, 0.12))]
        head_parts.append(("brows", loft(brow, [(0.006, 0.004), (0.018, 0.012), (0.02, 0.013), (0.012, 0.008)], P_BROW,
                                         up=(0.7 * sx, 0, 1), rings=10), fur_face, "head"))
        head_parts.append(("ruff", mass([(0.21 * sx, -0.22, -0.14), (0.31 * sx, 0.02, -0.13), (0.30 * sx, 0.22, -0.07)],
                                        [(0.12, 0.13), (0.16, 0.17), (0.11, 0.13)], up=(0, 0, 1)), fur_face, "ruff"))
        along = Vector((0.0, 1.0, 0.22))
        eye = [(-0.5, -0.02), (-0.3, 0.14), (0.0, 0.205), (0.3, 0.175), (0.5, 0.06), (0.3, -0.1), (0.0, -0.14), (-0.3, -0.11)]
        sock = lens([(a * 0.15, b * 0.185) for a, b in eye], 0.02, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        sock.transform(facing(p, nrm, along))
        head_parts.append(("socket", drape(sock, face, p, nrm, 0.0), dark, None))
        e = lens([(a * 0.126, b * 0.155) for a, b in eye], 0.02, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        e.transform(facing(p, nrm, along))
        head_parts.append(("eyes", drape(e, face, p, nrm, 0.007), glow, None))
    nose = rounded_box((0.125, 0.105, 0.088), n=2.6, cuts=2)
    for v in nose.verts:
        v.co.x *= 1.0 - 0.25 * smooth(v.co.z, 0.04, -0.04)
    nose.transform(M((0, -0.935, 0.07), rot=(-12, 0, 0)))
    set_layer(nose, "gloss", 0.5)
    head_parts.append(("nose", nose, nose_m, None))
    ears = []
    for sx in (-1, 1):
        ear = ear_shape(W=0.27, Hh=0.37)
        E = M((0.16 * sx, -0.0, 0.21), rot=(-14, 12 * sx, 26 * sx))
        ear.transform(E)
        head_parts.append(("ears", ear, fur_face, "earcol"))
        ears.append((sx, E))
    for part, bm, mat, region in head_parts:
        ensure_layers(bm)
        bm.transform(H)
        if region == "earcol":
            paint(bm, ear_colour(H, ears))
            base.append((part, bm, mat, 40.0, HEAD_BOOST))
        elif region is None:
            if mat is not glow:
                paint(bm, lambda co, n: Vector(kit.srgb(DARK)))
            base.append((part, bm, mat, 0.0 if mat is glow else 40.0, HEAD_BOOST))
        else:
            add_base(part, bm, mat, region, crease=38.0, boost=HEAD_BOOST)

    # ---- every base surface is in place: the plates and fur lie on them ------------------------------------
    surf = Surface(*[bm for _, bm, mat, _, _ in base if mat is not glow and mat is not dark])
    n_clumps = [0]

    def put(origin, toward, flow, L, W, region, lift=0.07, thick=0.045, bend=0.0, hug=1.0, boost=0.0, var=0.06, shade=1.0, mat=None,
            groove=0.45, heat=0.0, ember=0.0, jag=0.0, wave=0.0):
        o = Vector(origin)
        dvec = Vector(toward) - o
        p, nrm = surf.ray(o, dvec, dvec.length * 1.5)
        if p is None:
            return None
        under = smooth(-nrm.z, 0.1, 0.6)                  # on the underside: run back along the belly, never hang
        if under > 0:
            flow = Vector(flow).normalized().lerp(V((0, 1, -0.15)).normalized(), under)
        bm = clump(surf, p, nrm, flow, L, W, lift=lift, thick=thick, bend=bend, seed=rnd.random(), hug=hug, groove=groove, jag=jag, wave=wave)
        f = shade * (1.0 + var * (rnd.random() - 0.5) * 2)
        paint(bm, lambda co, n, f=f: colour(region, co, nrm) * f)
        set_layer(bm, "gloss", 0.1 * rnd.random())
        set_layer(bm, "heat", heat)
        set_layer(bm, "ember", ember)
        add("flames" if heat > 0 else "clumps", bm, mat or clump_m, crease=60 if jag else 75, boost=boost)
        n_clumps[0] += 1
        return p

    O = H @ V((0, -0.3, -0.05))     # the mane's locks radiate from here, in the middle of the head

    def flow_at(p):
        """Which way the fur runs at p: out from the head and back over the mane, down the throat and
        chest, backwards along the back, back and down on the flanks."""
        if p.y < -0.45:
            f = (p - O).normalized()
            f.y = max(f.y, 0.35)
            f = f.normalized() * 0.5 + V((0, 0.5, -0.5))
            front = smooth(-p.y, 0.95, 1.4) * smooth(p.z, 2.0, 1.55)
            return f.lerp(V((0, 0.2, -1)), front)
        k, ang = skin.angle_of(p)
        return V((0, 1, -0.15 - 0.95 * smooth(ang, 40, -40)))

    def on_skin(index, th, L, W, region="body", floor=None, **kw):
        s = skin.s_of(index)
        c = skin.at(s)[0]
        bare = skin.bare(s, th)
        if floor is not None:
            L = min(L, (bare.z - floor) / 0.9)
            if L < 0.12:
                return None
        o = bare + (bare - c).normalized() * 0.9
        return put(o, c, flow_at(bare), L, W, region, **kw)

    def plate_on_skin(i0, i1, half, centre, lift, seed, **kw):
        bm = rock_plate(skin, skin.s_of(i0), skin.s_of(i1), half, centre=centre, lift=lift, seed=seed, **kw)
        rock_colour(bm, rnd=rnd)
        set_layer(bm, "ember", 1.0)
        set_layer(bm, "crack", 1.0)
        set_layer(bm, "gloss", 0.05 * rnd.random())
        add("plates", bm, rock, crease=35)

    # ---- basalt plates: a ridge down the spine from the withers to the rump, a row each side -----------------
    idx, k = 3.35, 0
    while idx < 8.6:
        size = _table([(3.3, 0.42), (4.5, 0.55), (6.0, 0.5), (7.5, 0.52), (8.6, 0.4)], idx)
        half = _table([(3.3, 20), (4.5, 24), (6.0, 21), (7.5, 23), (8.6, 18)], idx)
        plate_on_skin(idx, idx + size * 1.25, half, 90.0 + rnd.uniform(-3, 3), (0.03, 0.11), seed=100 + k)
        idx += size
        k += 1
    for sxo in (-1, 1):
        idx = 3.65
        while idx < 8.3:
            size = _table([(3.6, 0.42), (4.5, 0.5), (6.0, 0.46), (7.5, 0.48), (8.3, 0.36)], idx)
            half = _table([(3.6, 17), (4.5, 20), (6.0, 18), (7.5, 20), (8.3, 15)], idx)
            plate_on_skin(idx, idx + size * 1.2, half, 90.0 + sxo * (half * 1.85 + 4) + rnd.uniform(-3, 3), (0.025, 0.09), seed=200 + k)
            idx += size * rnd.uniform(0.95, 1.1)
            k += 1

    # ---- the mane: flame locks round the neck, rising and sweeping back, their tips hot ----------------------
    rings = [(1.6, 0.36, 12), (2.05, 0.42, 12), (2.5, 0.46, 13), (2.95, 0.48, 13), (3.4, 0.46, 12), (3.85, 0.4, 11)]
    for r, (idx, L, m) in enumerate(rings):
        for j in range(m):
            th = 90.0 + 360.0 * (j + 0.5 * (r % 2)) / m + rnd.uniform(-5, 5)
            low = -math.sin(math.radians(th))          # 1 at the belly side, -1 on the spine
            if low > 0.35:
                # the chest: short coarse basalt clumps, a little warmer
                on_skin(idx + rnd.uniform(-0.05, 0.05), th, 0.26 * rnd.uniform(0.85, 1.1), 0.1, region="body", floor=1.2,
                        lift=0.02, thick=0.045, jag=0.25, groove=0.35, ember=0.25, var=0.1)
                continue
            top = smooth(-low, 0.0, 0.9)
            Lk = L * (1.0 + 0.35 * top) * rnd.uniform(0.8, 1.15)
            on_skin(idx + rnd.uniform(-0.06, 0.06), th, Lk, 0.13 * rnd.uniform(0.85, 1.15), region="mane",
                    lift=0.06 + 0.05 * top, thick=0.055, bend=rnd.uniform(-0.12, 0.12), mat=flame_m, groove=0.4,
                    heat=lerp(0.55, 1.0, top) * rnd.uniform(0.85, 1.0), ember=0.7, wave=rnd.choice((-1, 1)) * rnd.uniform(0.05, 0.1), hug=0.85)

    # ---- coarse fur on the flanks and belly, under the plates ------------------------------------------------
    for th0 in (28.0, 0.0, -32.0):
        for sxo in (-1, 1):
            th = th0 if sxo > 0 else 180.0 - th0
            idx = 4.3 + (0.2 if th0 == 0.0 else 0.0)
            while idx < 8.5:
                on_skin(idx + rnd.uniform(-0.05, 0.05), th + rnd.uniform(-5, 5), 0.26 * rnd.uniform(0.85, 1.15), 0.105, lift=0.02, thick=0.05,
                        jag=0.28, groove=0.35, ember=0.35, var=0.1, bend=rnd.uniform(-0.1, 0.1))
                idx += 0.42

    # legs: coarse tufts behind the elbows, britches behind the thighs, tufts behind wrists and hocks
    for sx, front, a, b in legs:
        if front:
            for k in range(3):
                z = a.z - 0.05 - 0.13 * k
                o = V((a.x + 0.02 * sx, a.y + 0.6, z))
                put(o, V((a.x, a.y - 0.05, z)), (0, 0.35, -1), 0.2 - 0.02 * k, 0.09, "leg", lift=0.03, thick=0.05, jag=0.25)
        else:
            for k in range(4):
                z = 1.7 - 0.18 * k
                y = 0.9 + 0.06 * k
                o = V((a.x + 0.05 * sx * (k % 2), y + 0.8, z))
                put(o, V((a.x * 0.8, y - 0.2, z)), (0, 0.3, -1), 0.24, 0.1, "leg", lift=0.035, thick=0.05, jag=0.25)
        c = b + V((0, 0.4, 0.05 if front else 0.12))
        put(c, b + V((0, 0, 0.05 if front else 0.12)), (0, 0.5, -1), 0.15, 0.08, "leg", lift=0.025, thick=0.04, jag=0.25)

    # ---- rock plates on the outer shoulders and thighs: armour scales draped over the muscle ---------------
    scute = [(-0.5, 0.0), (-0.36, 0.34), (0.05, 0.47), (0.42, 0.3), (0.5, -0.05), (0.36, -0.4), (-0.06, -0.47), (-0.4, -0.3)]
    for sx, front, a, b in legs:
        spots = (((-1.0, 1.72, 0.3), (-1.12, 1.45, 0.27), (-0.84, 1.5, 0.25), (-1.02, 1.22, 0.22)) if front else
                 ((0.78, 1.78, 0.3), (0.56, 1.52, 0.28), (0.86, 1.48, 0.27), (0.66, 1.25, 0.23)))
        for y, z, size in spots:
            origin = V((1.4 * sx, y, z))
            p, nrm = surf.ray(origin, V((-sx, 0, 0)), 3.0)
            if p is None:
                continue
            jag = random.Random(int(y * 100 + z * 10 + sx))
            outline = [(x * size * jag.uniform(0.85, 1.12), zz * size * 0.8 * jag.uniform(0.85, 1.12)) for x, zz in scute]
            bm = lens(outline, 0.1, rows=((0.4, 1.0), (1.0, 0.0)))
            lpr = bm.verts.layers.float["pr"]
            for v in bm.verts:
                v[lpr] = min(math.hypot(v.co.x, v.co.z) / (0.5 * size), 1.0)
            T = facing(p, nrm, V((0, 0.35 if front else -0.35, -1)))
            sign = 1.0 if T.col[1].xyz.dot(nrm) > 0 else -1.0
            for v in bm.verts:
                flat = T @ Vector((v.co.x, 0.0, v.co.z))
                q, _ = surf.ray(flat + nrm * 1.0, -nrm, 2.0)
                q = q if q is not None else flat
                rise = 0.06 * max(0.0, 0.5 + v.co.x / size)          # roof tiles: the lower end stands proud
                rim = abs(v.co.y) < 1e-6
                if rim:
                    v[lpr] = 1.0
                v.co = q + nrm * (-0.02 if rim else v.co.y * sign + 0.02 + rise)
            rock_colour(bm, rnd=rnd)
            set_layer(bm, "ember", 1.0)
            set_layer(bm, "crack", 1.0)
            add("scutes", bm, rock, crease=35)

    # ---- head: cheek ruff of flame locks sweeping back, a few short locks on the crown ----------------------
    for sx in (-1, 1):
        for k, (y, z, L) in enumerate(((-0.24, -0.15, 0.17), (-0.08, -0.18, 0.2), (0.08, -0.15, 0.21), (-0.12, -0.04, 0.16),
                                       (0.06, -0.02, 0.18), (0.2, -0.09, 0.2))):
            o = H @ V((0.75 * sx, y, z))
            tgt = H @ V((0.0, y, z))
            flow = HR @ V((0.2 * sx, 1.0, -0.35))
            put(o, tgt, flow, L, 0.085, "ruff", lift=0.04, thick=0.05, boost=HEAD_BOOST, mat=flame_m, heat=0.55, ember=0.5,
                wave=0.06 * sx)
    for k, (xx, yy) in enumerate(((-0.07, -0.2), (0.07, -0.18), (0.0, -0.08))):
        o = H @ V((xx, yy, 0.9))
        put(o, H @ V((xx, yy, 0.0)), HR @ V((xx * 1.5, 1.0, -0.2)), 0.16, 0.07, "head", lift=0.01, thick=0.025, boost=HEAD_BOOST,
            var=0.03, jag=0.2)

    # ---- tail: rings of flame locks, hotter towards the tip, the last ones closing into a smouldering point -
    rings_t = 9
    for r in range(rings_t):
        t = 0.04 + 0.74 * r / (rings_t - 2) if r < rings_t - 1 else 0.84
        i = t * (len(TAIL) - 1)
        c = _cr([V(p) for p in TAIL], i)
        tan = (_cr([V(p) for p in TAIL], min(i + 0.05, len(TAIL) - 1)) - c).normalized()
        ref = V((0, 0, 1)) - tan * tan.z
        ref.normalize()
        sd = tan.cross(ref)
        m = 7 if r < rings_t - 1 else 6
        tip = r == rings_t - 1
        for j in range(m):
            a = 2 * math.pi * (j + 0.5 * (r % 2)) / m + rnd.uniform(-0.15, 0.15)
            out = ref * math.cos(a) + sd * math.sin(a)
            L = 0.2 if tip else 0.34 + 0.08 * math.sin(math.pi * t)
            put(c + out * 0.8, c, tan, L, 0.11 if tip else 0.14, "tail", lift=0.0 if tip else 0.04 + 0.02 * math.sin(math.pi * t),
                thick=0.04 if tip else 0.05, bend=rnd.uniform(-0.1, 0.1), hug=0.85 if tip else 1.0, mat=flame_m,
                heat=smooth(t, 0.25, 0.8) * (0.85 + 0.15 * max(out.z, 0.0)), ember=0.6, wave=rnd.uniform(-0.06, 0.06))
    for idx in (8.35, 8.75):
        for th in (40.0, 70.0, 110.0, 140.0, 90.0):
            on_skin(idx + rnd.uniform(-0.05, 0.05), th + rnd.uniform(-6, 6), 0.3, 0.11, region="tail", lift=0.02, thick=0.045, jag=0.25)
    # the smouldering tip: a small glowing coal inside the last locks
    c = _cr([V(p) for p in TAIL], 0.88 * (len(TAIL) - 1))
    tan = (_cr([V(p) for p in TAIL], 0.95 * (len(TAIL) - 1)) - c).normalized()
    cr = crystal(0.06, 0.2, seed=3, sides=5)
    cr.transform(M(c - tan * 0.04) @ tan.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    add("glow", cr, glow, crease=15)

    for part, bm, mat, crease, boost in base:
        add(part, bm, mat, crease=crease, boost=boost)

    print("  fur clumps: %d" % n_clumps[0])
    lowest = min(v.co.z for bm, _ in w.parts.values() for v in bm.verts)
    cut = cull_and_weigh(w.parts)
    print("  hidden faces removed: %d triangles (lowest point %.3f)" % (cut, lowest))
    w.build(scale=SCALE)
    for ob in w.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return w


def leg_band(co, n):          # replaced in build()
    return 0.3


def tail_band(co):            # replaced in build()
    return 0.3


def ear_shape(W=0.25, Hh=0.44):
    """A pointed ear in its own space: base on z=0, x across, front facing -y, cupped."""
    outline = [(-0.5, 0.0), (-0.47, 0.32), (-0.32, 0.66), (0.0, 1.0), (0.24, 0.7), (0.42, 0.36), (0.5, 0.0), (0.0, -0.06)]
    rings = [(1.0, 0.0, 0.0), (0.85, -0.016, 0.034), (0.6, 0.016, 0.056), (0.3, 0.032, 0.07)]
    cx, cz = 0.0, 0.33
    bm = ensure_layers(bmesh.new())
    lg = bm.verts.layers.float["grad"]
    n = len(outline)
    rim = [bm.verts.new((a * W, 0.0, b * Hh)) for a, b in outline]
    for v in rim:
        v[lg] = 1.0
    fronts, backs = [rim], [rim]
    for rho, fy, by in rings[1:]:
        f, b = [], []
        for a, z in outline:
            x, zz = (cx + (a - cx) * rho) * W, (cz + (z - cz) * rho) * Hh
            vf, vb = bm.verts.new((x, fy, zz)), bm.verts.new((x, by, zz))
            vf[lg], vb[lg] = 0.0 + rho * 0.8, 1.0
            f.append(vf)
            b.append(vb)
        fronts.append(f)
        backs.append(b)
    for loops, cy, gv in ((fronts, 0.035, 0.0), (backs, 0.075, 1.0)):
        c = bm.verts.new((cx * W, cy, cz * Hh))
        c[lg] = gv
        for a, b in zip(loops, loops[1:]):
            for j in range(n):
                bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
        last = loops[-1]
        for j in range(n):
            bm.faces.new((last[j], last[(j + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


EAR_H = 0.37


def ear_colour(H, ears):
    """Ears: charcoal on the back and rim, a dark warm red-brown in the cup, darker towards the tip."""
    inv = [((H @ E).inverted(), (H @ E).to_3x3().normalized().inverted()) for sx, E in ears]
    cup = Vector(kit.srgb("#4A2418"))

    def fn(co, n):
        loc, nl = min(((m @ co, r @ n) for m, r in inv), key=lambda ln: abs(ln[0].x) + abs(ln[0].y))
        h = loc.z / EAR_H
        inner = smooth(-nl.y, 0.25, 0.7) * smooth(loc.y, -0.012, 0.012) * (1.0 - smooth(h, 0.6, 0.9))
        return band(0.05).lerp(cup, inner) * (1.0 - 0.3 * smooth(h, 0.7, 1.0))
    return fn


def rough_map(body, texture, base, vary=0.1):
    """A baked roughness image the size of the colour image: `base`, lower where a shape was marked
    glossy (vertex layer 'gloss'), broken up by fine and broad noise. Saved as <name>_rough.png."""
    import numpy as np
    baked = body.data.materials[0]
    nodes = baked.node_tree.nodes

    def feeding(socket):
        return next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == socket for l in n.outputs[0].links))
    colour_node, rough_node = feeding("Base Color"), feeding("Roughness")
    size = colour_node.image.size[0]
    m = bpy.data.materials.new("RoughBake")
    kit.principled(m)
    t = m.node_tree
    new, link = t.nodes.new, t.links.new
    for nd in list(t.nodes):
        t.nodes.remove(nd)
    out = new("ShaderNodeOutputMaterial")
    em = new("ShaderNodeEmission")
    link(em.outputs[0], out.inputs[0])
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "gloss"
    co = new("ShaderNodeTexCoord")
    fine = new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 38.0, 3.0
    broad = new("ShaderNodeTexNoise")
    broad.inputs["Scale"].default_value, broad.inputs["Detail"].default_value = 3.5, 2.0
    link(co.outputs["Object"], fine.inputs["Vector"])
    link(co.outputs["Object"], broad.inputs["Vector"])
    r = _math(t, 'ADD', _math(t, 'MULTIPLY', a.outputs["Fac"], -0.65 * base), base)
    r = _math(t, 'ADD', r, _math(t, 'MULTIPLY', _math(t, 'SUBTRACT', fine.outputs["Fac"], 0.5), 2 * vary))
    r = _math(t, 'ADD', r, _math(t, 'MULTIPLY', _math(t, 'SUBTRACT', broad.outputs["Fac"], 0.5), vary))
    r = _math(t, 'MAXIMUM', _math(t, 'MINIMUM', r, 1.0), 0.05)
    link(r, em.inputs["Color"])
    img = bpy.data.images.new(os.path.splitext(os.path.basename(texture))[0].replace("_colour", "") + "_rough", size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    tn = new("ShaderNodeTexImage")
    tn.image = img
    t.nodes.active = tn
    body.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    sc = bpy.context.scene
    old = sc.cycles.samples
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    sc.cycles.samples = old
    body.data.materials[0] = baked
    bpy.data.materials.remove(m)
    stem = os.path.splitext(texture)[0]
    img.filepath_raw = (stem[:-len("_colour")] if stem.endswith("_colour") else stem) + "_rough.png"
    img.file_format = 'PNG'
    img.save()
    grey = rough_node.image
    rough_node.image = img
    if grey and grey.users == 0:
        name = grey.name
        bpy.data.images.remove(grey)
        img.name = name
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return float(px[0::4].min()), float(px[0::4].max())


BAKE_SHADE = 0.42             # how dark the deepest crease gets in the bake

EMBER = "#FF6A14"             # the magma in the seams between plates and locks
EMBER_HOT = "#FFB845"         # ... the deepest, hottest part of a seam
EMBER_WARM = "#3E2116"        # the rock warms to this just beside a seam
EMBER_REACH = 0.13
EMBER_FROM, EMBER_TO, EMBER_MAX = 0.16, 0.6, 0.9


def ember_seams(ob, path, size):
    """After the bake (the Dragon's ember seams): where the plates and locks (vertex value "ember") sink
    into a tight crevice, turn the colour towards glowing magma, hotter where the crevice is deeper, and
    warm the rock just beside it. Two quick bakes in the texture's own layout: the mask and a short reach
    crevice shading."""
    import numpy as np
    sc = bpy.context.scene
    keep_samples = sc.cycles.samples
    world = sc.world
    if world is None:
        world = sc.world = bpy.data.worlds.new("BakeWorld")
    keep_reach = world.light_settings.distance
    world.light_settings.distance = EMBER_REACH
    baked = ob.data.materials[0]
    m = bpy.data.materials.new("EmberMask")
    kit.principled(m)
    tree = m.node_tree
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(_attr(tree, "ember"), em.inputs["Color"])
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    tree.links.new(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new("ember_mask", size, size, alpha=False, float_buffer=True)
    tn = tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tree.nodes.active = tn
    ob.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    def grab():
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        return px.reshape(size, size, 4)[..., :1].copy()
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    mask = np.clip(grab(), 0.0, 1.0)
    sc.cycles.samples = 24
    bpy.ops.object.bake(type='AO', margin=12)
    ao = grab()
    ao = (ao + np.roll(ao, 1, 0) + np.roll(ao, -1, 0) + np.roll(ao, 1, 1) + np.roll(ao, -1, 1)) / 5.0
    ob.data.materials[0] = baked
    sc.cycles.samples = keep_samples
    world.light_settings.distance = keep_reach

    def ss(x, a, b):
        t = np.clip((x - a) / (b - a), 0.0, 1.0)
        return t * t * (3 - 2 * t)
    occ = 1.0 - ao
    warm = mask * 0.6 * ss(occ, EMBER_FROM * 0.45, EMBER_FROM * 1.2)
    k = mask * EMBER_MAX * ss(occ, EMBER_FROM, EMBER_TO)
    hot = ss(occ, (EMBER_FROM + EMBER_TO) / 2, EMBER_TO + 0.15)
    glow = np.array(kit.srgb(EMBER), dtype=np.float32) * (1 - hot) + np.array(kit.srgb(EMBER_HOT), dtype=np.float32) * hot
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    rgb = px[..., :3]
    rgb = rgb * (1 - warm) + np.array(kit.srgb(EMBER_WARM), dtype=np.float32) * warm
    rgb = rgb * (1 - k) + glow * k
    px[..., :3] = rgb
    tex.pixels.foreach_set(px.ravel())
    tex.filepath_raw, tex.file_format = path, 'PNG'
    tex.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)


def threads():
    r = bpy.context.scene.render
    r.threads_mode, r.threads = 'FIXED', THREADS


def bake(wolf, texture):
    """Everything that does not glow becomes one textured mesh, LavaWolf_Body (colour and soft crease
    shading baked into a 1024 image, 512 under PETS_FAST, packed by real outlines, barely seen surfaces
    given less of it; then the magma seams; plus a baked roughness image). The glowing parts (eyes and
    the tail-tip coal) join into LavaWolf_GLOW. Objects are matched by name prefix, since Blender renames
    shared materials ("GLOW_Lava.001") when several pets share a scene."""
    threads()
    pre = NAME + "_"
    glow = [ob for ob in wolf.objects if ob.name.startswith(pre + "GLOW")]
    real_pack = bpy.ops.uv.pack_islands

    def pack(**kw):
        weigh_islands(bpy.context.view_layer.objects.active)
        return real_pack(**kw)
    saved = bpy.ops
    bpy.ops = _OpsProxy(saved, pack)
    try:
        body = kit.bake_texture([ob for ob in wolf.objects if ob not in glow], texture, name=pre + "Body",
                                shade=BAKE_SHADE, soften=3, rough=0.9, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved
    size = 512 if os.environ.get("PETS_FAST") else 1024
    ember_seams(body, texture, size)
    rough_map(body, texture, 0.9, 0.12)
    me = body.data
    if "hid" in me.attributes:
        hid = [dd.value for dd in me.attributes["hid"].data]
        uv = me.uv_layers.active.data
        a2 = a3 = 0.0
        for pl, h in zip(me.polygons, hid):
            if h > 0.01:
                continue
            pts = [uv[i].uv for i in pl.loop_indices]
            a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
            a3 += pl.area
        print("seen surfaces: about %.0f pixels to a stud" % ((a2 * 1024 * 1024 / max(a3, 1e-9)) ** 0.5))
    junk = ("hid", "boost", "grad", "fu", "fq", "fs", "gloss", "col", "heat", "ember", "pr", "crack")
    for name in junk:
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = pre + "GLOW"
    for name in junk:
        if name in g.data.attributes:
            g.data.attributes.remove(g.data.attributes[name])
    wolf.objects = [body, g]


def face_point():
    return (head_matrix() @ Vector((0, -0.5, 0.05)) - Vector((0, 0, LEG_DROP))) * SCALE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--peek", help="quick look while building: these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,side")
    ap.add_argument("--look", default="full")
    ap.add_argument("--px", type=int, default=480)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--title", default=NAME + " review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", NAME.lower() + "_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    threads()
    wolf = build()
    print("triangles by part:", dict(sorted(wolf.tally.items(), key=lambda kv: -kv[1])))
    head = face_point()

    def rig_for(samples):
        import review
        lo, hi = wolf.bounds()
        rig = review.Rig(wolf, samples=samples, focus=(head.x * 0.5, head.y + 0.9, head.z - 0.7))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.72, -0.9, 0.16)).normalized() * 3.3, head + Vector((0, 0.15, 0.02)), 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0.0, -1.0, 0.07)).normalized() * 3.3, head + Vector((0, 0.15, 0.0)), 30)
        threads()
        return rig, review

    if a.peek:
        rig, _ = rig_for(a.samples)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), a.look) for v in a.views.split(",")], px=a.px, cols=a.cols, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(wolf, os.path.abspath(a.texture))
    tris = wolf.triangles()
    lo, hi = wolf.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(wolf.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        rig, review = rig_for(a.samples)
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        shots = review.STANDARD + [("face", "full"), ("face front", "full")]
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
