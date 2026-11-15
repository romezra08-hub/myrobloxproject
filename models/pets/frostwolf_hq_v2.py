"""FrostWolf pet, hero-quality remake: a midnight-blue frost wolf with a ridge of glowing ice crystals.
Built from scratch by script, on the Dragon's methods (models/pets/dragon.py).

    python models/pets/frostwolf_hq_v1.py --review out/frostwolf.png
    python models/pets/frostwolf_hq_v1.py --export models/export/frostwolf.fbx

Style: a believable fantasy creature in the same family as the Dragon, not a cartoon. The owner turned
down the big-eyed half-realistic look ("cursed"), a cute chibi ("simulator") and low-poly ("ruins it").
Must-haves:
  1. Real wolf anatomy, a little heroic: deep chest, strong shoulders, narrow waist, legs with upper
     muscle, a wrist and a hock, big paws with toes and claws. A long tapered muzzle, a brow, cheekbones,
     tall pointed ears, a strong jaw, a short neck set into a mane.
  2. Fur as modelled clumps: pointed locks that flow one way, layered like the Dragon's plates: a thick
     mane and chest ruff, cheek ruffs, back, haunch and elbow clumps, a bushy tail made of clumps.
  3. Clean painted gradients: midnight blue on the back to pale frost on the belly, chest and muzzle,
     darker tips. No blotches.
  4. Sharp faceted ice crystals of varied size along the spine from neck to mid-back (GLOW, pale cyan).
  5. Small glowing pale-cyan eyes in sockets under the brow, no whites, irises or lids. Mouth closed
     with a dark lip line. Calm and confident.
  6. Matte, a 1024 colour bake plus a baked roughness map. Body up to about 16k triangles. About 3 studs
     tall, up to about 5 long. Feet at z=0, facing -Y.

Round 2: the clumps read as paper shards: they are now narrower, thick with a round back and smoothly
shaded, lie flatter (only the tip lifts), and all follow one flow field (out from the head over the mane,
down the chest, back along the body); a lock whose flow ran straight into the surface used to point at
random. The head outline bows through its corners (it was a faceted box), lighter brows, the eye sat
behind its socket and was invisible, cheaper toes and claws.

Round 1: first build. Skin of neck and trunk (the Dragon's Skin), head from section tables (shell),
lofted legs with muscle masses, paws with toes and claws, about 230 draped fur clumps, ice crystals.
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

NAME = "FrostWolf"
SCALE = 0.94                       # the whole wolf is built a little large, then scaled to about 3 studs tall
HEAD_AT = (-0.04, -1.50, 2.62)     # the back of the skull
HEAD_ROT = (6, 2, -12)             # nose a little down, a slight tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.0
THREADS = 3

# The upper head as sections from the back of the skull to the nose (nose towards -y):
# y, top z, half width of the top plane, cheek z, cheek half width, lip z, lip half width.
SKULL = [
    (0.12, 0.10, 0.07, 0.00, 0.17, -0.14, 0.12),
    (0.02, 0.27, 0.13, 0.04, 0.28, -0.19, 0.21),
    (-0.12, 0.33, 0.16, 0.03, 0.34, -0.20, 0.25),
    (-0.28, 0.31, 0.16, 0.00, 0.30, -0.19, 0.23),
    (-0.42, 0.22, 0.12, -0.03, 0.21, -0.17, 0.18),
    (-0.58, 0.175, 0.095, -0.05, 0.155, -0.16, 0.145),
    (-0.76, 0.15, 0.08, -0.06, 0.125, -0.15, 0.12),
    (-0.92, 0.13, 0.065, -0.065, 0.105, -0.145, 0.10),
    (-1.00, 0.10, 0.05, -0.065, 0.08, -0.135, 0.075),
    (-1.04, 0.05, 0.03, -0.07, 0.045, -0.12, 0.04),
]
# The lower jaw: y, top z, top half width, jaw-corner z, jaw-corner half width, chin-keel z.
JAW = [
    (0.02, -0.16, 0.20, -0.30, 0.20, -0.34),
    (-0.10, -0.17, 0.22, -0.34, 0.20, -0.40),
    (-0.35, -0.17, 0.19, -0.31, 0.16, -0.36),
    (-0.60, -0.16, 0.14, -0.27, 0.12, -0.31),
    (-0.82, -0.15, 0.115, -0.24, 0.095, -0.27),
    (-0.95, -0.145, 0.09, -0.22, 0.07, -0.245),
    (-1.00, -0.14, 0.05, -0.20, 0.04, -0.215),
]

# colours (sRGB) along the coat: 0 the spine, 1 the belly; above 1 the tail tip
PAL = [(0.0, "#111933"), (0.3, "#1A2650"), (0.52, "#2C4177"), (0.74, "#88A2CC"), (0.95, "#C8D7EC"), (1.15, "#E6EEF8")]
DARK = "#0B0E1A"
GLOW_HEX = "#8FE3FF"


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


VERT_LAYERS = ("fu", "fq", "fs", "gloss", "grad")


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
    return [(0, zt + 0.035), (-wt, zt), (-wc, zc), (-wb, zb), (0, zb - 0.01), (wb, zb), (wc, zc), (wt, zt)]


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


def clump(surf, p, n, flow, length, width, lift=0.07, thick=0.045, tuck=0.03, bend=0.0, seed=0.0, hug=1.0):
    """A pointed lock of fur lying on `surf` from its root `p` (surface normal `n`) along `flow`: a closed
    blade with a ridge down its middle, its root buried, rising like a roof tile towards a free tip.
    `bend` curves it sideways; `hug` (0 to 1) is how closely it follows the surface (0: a straight plane).
    Vertex layers: fu (0 root to 1 tip), fq (-1 to 1 across), fs (a random number for this clump)."""
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
        flat = p + d * (u * length) + side * (q * width * _clump_width(u) + bend * length * u * u)
        sp, sn = flat, n
        if hug > 0:
            loc, nrm = surf.ray(flat + n * 0.5, -n, 1.0)
            if loc is not None and (loc - flat).length < 0.16 and nrm.dot(n) > 0.3:
                sp = flat.lerp(loc, hug)
                sn = n.lerp(nrm, hug * 0.7).normalized()
        base = -tuck + (lift + tuck) * u ** 2.2
        h = base
        if top:
            h += thick * max(1.0 - q * q, 0.0) ** 0.6 * math.sin(math.pi * min(u, 1.0) ** 0.6)
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


def fur_material(name, scale=(30.0, 30.0, 4.0), strength=0.12, rough=0.9):
    """Short fur: the vertex colour 'col' under fine streaks running along the axis with the smallest scale."""
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
    t.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    return m


def clump_material(name, strength=0.16, tipdark=0.3, rough=0.9):
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
    edge = _math(t, 'MULTIPLY_ADD', q4, -0.14, 1.0)
    v = _math(t, 'MULTIPLY', _math(t, 'MULTIPLY', v, tip), edge)
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    t.links.new(_attr(t, "col", "Color"), hsv.inputs["Color"])
    t.links.new(v, hsv.inputs["Value"])
    t.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
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


# ---- the frost wolf ----------------------------------------------------------------------------------

def head_matrix():
    return M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)


SPINE = None      # filled by build(): the Skin, used by the colour rules


def body_band(p):
    k, ang = SPINE.angle_of(p)
    return 1.0 - smooth(ang, -70.0, 58.0)


EYE_H = []        # the eyes in head space, filled by build()


def head_band(hl):
    """The band value on the head, from head-space coordinates: a midnight crown fading to a frost
    muzzle and pale cheeks, a dark mask round each eye and a dark line from it back towards the ear."""
    top, cz = skull_at(hl.y)[1], skull_at(hl.y)[3]
    v = smooth(hl.z, top - 0.02, cz - 0.07)
    b_top = lerp(0.1, 0.5, smooth(hl.y, -0.38, -0.8))
    b = lerp(b_top, 0.92, v)
    for e in EYE_H:
        if (hl.x > 0) != (e.x > 0):
            continue
        d = ((hl - e) * Vector((1.0, 0.8, 1.3))).length
        b = lerp(b, 0.08, 1.0 - smooth(d, 0.05, 0.12))
        a2, b2 = e + Vector((0.01 if e.x > 0 else -0.01, 0.08, 0.02)), e + Vector((0.03 if e.x > 0 else -0.03, 0.26, 0.09))
        ab = b2 - a2
        t = max(0.0, min(1.0, (hl - a2).dot(ab) / ab.length_squared))
        b = lerp(b, 0.12, 0.85 * (1.0 - smooth((a2 + ab * t - hl).length, 0.025, 0.065)) * (1.0 - 0.5 * t))
    return b


def build():
    global SPINE
    fur_body = fur_material("FurBody", scale=(34.0, 6.0, 34.0), strength=0.1)      # streaks run along the body (y)
    fur_leg = fur_material("FurLeg", scale=(34.0, 34.0, 6.0), strength=0.1)        # streaks run down the legs (z)
    fur_face = fur_material("FurFace", scale=(48.0, 9.0, 48.0), strength=0.07)
    clump_m = clump_material("Clump")
    dark = kit.material("Dark", DARK, rough=0.6)
    nose_m = kit.material("Nose", "#0D101B", rough=0.45)
    claw_m = kit.material("Claw", "#1C1F2B", rough=0.5)
    glow = kit.material("GLOW_Frost", GLOW_HEX, rough=0.25, emit=1.4)

    w = Prop(NAME)
    w.tally = {}
    H = head_matrix()
    Hinv = H.inverted()
    HR = H.to_3x3().normalized()
    rnd = random.Random(7)

    def hs(p):
        return tuple(H @ Vector(p))

    def colour(region, co, n):
        if region == "head":
            return band(head_band(Hinv @ co))
        if region == "jaw":
            return band(0.93)
        if region == "leg":
            return band(leg_band(co, n))
        if region == "tail":
            return band(tail_band(co))
        if region == "ear":
            return band(0.06)
        if region == "paw":
            return band(0.24)
        return band(body_band(co))

    base = []          # (part, bm, material, region, boost) in world space: the surfaces the fur lies on

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
        if crease:
            sharpen(bm, crease)
        w.tally[part] = w.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        w.add(bm, mat)

    # ---- neck and trunk: one skin ----------------------------------------------------------------------
    spine = [
        (*hs((0, -0.15, -0.02)), 0.20, 0.22, 0.24, 2.2, 0.0),     # 0 inside the head
        (*hs((0, 0.18, -0.10)), 0.27, 0.27, 0.32, 2.2, 0.0),      # 1 behind the skull
        (0.0, -1.24, 2.36, 0.40, 0.36, 0.48, 2.25, 0.0),          # 2 the neck, thick with the mane
        (0.0, -1.02, 2.05, 0.50, 0.44, 0.62, 2.3, 0.01),          # 3 neck base, the chest below
        (0.0, -0.76, 1.84, 0.52, 0.46, 0.68, 2.35, 0.02),         # 4 withers and deep chest
        (0.0, -0.32, 1.80, 0.46, 0.42, 0.56, 2.4, 0.02),          # 5 behind the shoulders
        (0.0, 0.15, 1.82, 0.37, 0.36, 0.38, 2.4, 0.02),           # 6 narrow waist
        (0.0, 0.62, 1.85, 0.42, 0.37, 0.44, 2.4, 0.02),           # 7 hips
        (0.0, 1.02, 1.80, 0.37, 0.33, 0.42, 2.3, 0.01),           # 8 rump
        (0.0, 1.28, 1.76, 0.22, 0.21, 0.25, 2.2, 0.0),            # 9 tail root
        (0.0, 1.36, 1.76, 0.08, 0.08, 0.08, 2.2, 0.0),            # 10
    ]
    skin = Skin(spine, 4)
    SPINE = skin
    add_base("skin", skin.mesh(segs=24, cuts=(2.6, 5.2, 7.6)), fur_body, "body", crease=0)

    # ---- legs --------------------------------------------------------------------------------------------
    legs = []          # (sx, front, key points) for the clump placement

    def leg_band_fn(co, n):
        sx = 1.0 if co.x > 0 else -1.0
        inner = smooth(-n.x * sx, 0.1, 0.75)
        b = 0.30 + 0.40 * inner
        b += 0.12 * smooth(-n.y, 0.35, 0.9) * smooth(co.z, 0.95, 0.5)
        top = smooth(co.z, 1.05, 1.65)
        return lerp(b, body_band(co), top)

    global leg_band
    leg_band = leg_band_fn

    def paw(x, y, yaw, size):
        F = M((x, y, 0), rot=(0, 0, yaw), scale=size)
        pad = rounded_box((0.27, 0.30, 0.17), n=3.2, cuts=2)
        pad.transform(F @ M((0, 0.02, 0.085)))
        add_base("paws", pad, fur_leg, "paw", crease=0)
        for tx, ty, s in ((-0.105, -0.105, 0.92), (-0.04, -0.15, 1.0), (0.04, -0.15, 1.0), (0.105, -0.105, 0.92)):
            toe = kit.ball((0.09 * s, 0.13 * s, 0.11 * s), cuts=1)
            ensure_layers(toe)
            toe.transform(F @ M((tx, ty, 0.052)))
            add_base("toes", toe, fur_leg, "paw", crease=0)
            claw = [(tx * 1.05, ty - 0.055 * s, 0.065), (tx * 1.08, ty - 0.095 * s, 0.045), (tx * 1.1, ty - 0.118 * s, 0.0)]
            bm = loft(claw, [0.024, 0.017, 0.003], P_CLAW5, up=(0, -0.3, 1), rings=3)
            bm.transform(F)
            set_layer(bm, "gloss", 0.35)
            add_base("claws", bm, claw_m, "paw", crease=50)

    for sx in (-1, 1):
        step = 0.16 if sx < 0 else 0.0
        elbow = V((0.39 * sx, -0.76, 1.04))
        wrist = V((0.37 * sx, -0.90 - step, 0.36))
        foot = V((0.37 * sx, -0.95 - step, 0.12))
        arm = [(0.27 * sx, -0.82, 2.05), (0.40 * sx, -1.08, 1.62), tuple(elbow), tuple(elbow.lerp(wrist, 0.45) + V((0, -0.02, 0))),
               tuple(wrist), tuple(foot)]
        add_base("legs", loft(arm, [(0.21, 0.31), (0.21, 0.27), (0.17, 0.2), (0.135, 0.155), (0.095, 0.11), (0.1, 0.11)],
                              P_LEG, up=(0, -1, 0), rings=16), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * sx, -0.92, 2.0), (0.47 * sx, -1.02, 1.70), (0.47 * sx, -0.98, 1.40), (0.43 * sx, -0.90, 1.20)],
                                [(0.16, 0.20), (0.17, 0.22), (0.12, 0.15), (0.04, 0.05)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.38 * sx, -0.62, 1.72), (0.45 * sx, -0.66, 1.38), (0.43 * sx, -0.72, 1.10)],
                                [(0.16, 0.17), (0.15, 0.16), (0.05, 0.05)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.42 * sx, -0.86, 1.0), (0.42 * sx, -0.88 - 0.4 * step, 0.75), (0.39 * sx, -0.90 - 0.8 * step, 0.48)],
                                [(0.10, 0.12), (0.09, 0.10), (0.03, 0.03)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        carpal = kit.ball((0.10, 0.10, 0.10), cuts=2)
        carpal.transform(M(wrist + V((0, 0.08, 0.03))))
        add_base("wrists", ensure_layers(carpal), fur_leg, "leg", crease=0)
        paw(foot.x, foot.y - 0.06, 4 * sx, 1.15)
        legs.append((sx, True, elbow, wrist))

        stifle = V((0.43 * sx, 0.50, 1.06))
        hock = V((0.41 * sx, 1.08, 0.50))
        foot = V((0.41 * sx, 1.00, 0.12))
        thigh = [(0.28 * sx, 0.82, 1.98), (0.40 * sx, 0.64, 1.50), tuple(stifle), (0.42 * sx, 0.80, 0.78), tuple(hock),
                 (0.41 * sx, 1.05, 0.34), tuple(foot)]
        add_base("legs", loft(thigh, [(0.29, 0.41), (0.26, 0.36), (0.16, 0.19), (0.125, 0.155), (0.09, 0.11), (0.09, 0.105), (0.095, 0.105)],
                              P_LEG, up=(0, -1, 0), rings=22), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.30 * sx, 1.05, 2.05), (0.42 * sx, 1.00, 1.70), (0.45 * sx, 0.92, 1.35), (0.42 * sx, 0.82, 1.05)],
                                [(0.20, 0.26), (0.22, 0.28), (0.17, 0.22), (0.05, 0.06)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * sx, 0.62, 1.85), (0.47 * sx, 0.52, 1.50), (0.46 * sx, 0.48, 1.20), (0.43 * sx, 0.50, 1.04)],
                                [(0.16, 0.20), (0.18, 0.22), (0.13, 0.15), (0.04, 0.04)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.43 * sx, 0.62, 1.0), (0.43 * sx, 0.80, 0.86), (0.42 * sx, 0.98, 0.66), (0.41 * sx, 1.07, 0.54)],
                                [(0.10, 0.12), (0.10, 0.12), (0.06, 0.07), (0.03, 0.03)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        hk = kit.ball((0.09, 0.10, 0.10), cuts=2)
        hk.transform(M(hock + V((0, 0.05, 0.0))))
        add_base("hocks", ensure_layers(hk), fur_leg, "leg", crease=0)
        paw(foot.x, foot.y - 0.05, 3 * sx, 1.12)
        legs.append((sx, False, stifle, hock))

    # chest muscle: two pectoral masses under the ruff, between the front legs
    for sx in (-1, 1):
        add_base("muscle", mass([(0.12 * sx, -1.08, 1.95), (0.22 * sx, -1.20, 1.60), (0.26 * sx, -1.05, 1.28), (0.27 * sx, -0.9, 1.15)],
                                [(0.2, 0.2), (0.22, 0.22), (0.16, 0.16), (0.04, 0.04)], up=(0, -1, 0)), fur_body, "body", crease=0)

    # ---- tail: a thick core, covered in clumps later ------------------------------------------------------
    TAIL = [(0.0, 1.22, 1.86), (0.0, 1.52, 2.0), (0.05, 1.84, 1.98), (0.12, 2.1, 1.8), (0.16, 2.24, 1.54), (0.18, 2.28, 1.32),
            (0.18, 2.28, 1.2)]
    tail_r = [0.15, 0.19, 0.22, 0.21, 0.16, 0.09, 0.02]
    tail_bm = loft(TAIL, tail_r, profile_round(12), up=(0, 0, 1), rings=30)
    tail_path = [_cr([V(p) for p in TAIL], i / 60 * (len(TAIL) - 1)) for i in range(61)]

    def tail_t(co):
        k = min(range(len(tail_path)), key=lambda i: (tail_path[i] - co).length_squared)
        return k / 60.0, tail_path[k]

    def tail_band_fn(co):
        t, c = tail_t(co)
        r = co - c
        up = r.z / max(r.length, 1e-6)
        b = 0.18 + 0.45 * smooth(-up, -0.2, 0.9)
        return lerp(b, 1.12, smooth(t, 0.5, 0.85))

    global tail_band
    tail_band = tail_band_fn
    add_base("tail core", tail_bm, fur_body, "tail", crease=0)

    # ---- head: built in head space, then turned into place ------------------------------------------------
    skull = shell(SKULL, skull_corners, per=3, m=3, back_cap=0.05, nose_cap=0.01, soft=0.75)
    face = Surface(skull)
    jaw = shell(JAW, jaw_corners, per=2, m=3, back_cap=0.04, nose_cap=0.01, soft=0.7)
    head_parts = [("head", skull, fur_face, "head"), ("head", jaw, fur_face, "jaw")]
    eyes = []
    for sx in (-1, 1):
        pe, _ = face.hit((0.55 * sx, -0.62, 0.15), (-0.75 * sx, 0.6, -0.04))
        brow = [face.hit((0.6 * sx, pe.y + dy, pe.z + dz), (-sx, 0.0, -0.25))[0] for dy, dz in ((-0.1, 0.035), (-0.05, 0.06), (0.02, 0.07), (0.1, 0.065))]
        head_parts.append(("brows", loft(brow, [(0.012, 0.01), (0.03, 0.022), (0.034, 0.024), (0.02, 0.014)], P_BROW,
                                         up=(0.7 * sx, 0, 1), rings=10), fur_face, "head"))
        cheek = [face.hit((0.6 * sx, pe.y + dy, pe.z + dz), (-sx, 0.0, 0.1))[0] for dy, dz in ((-0.08, -0.1), (0.02, -0.12), (0.14, -0.12), (0.26, -0.1))]
        head_parts.append(("cheeks", loft(cheek, [(0.015, 0.012), (0.035, 0.028), (0.04, 0.03), (0.025, 0.02)], P_BROW,
                                          up=(1.0 * sx, 0, 0.3), rings=8), fur_face, "head"))
        # cheek ruff volume behind the jaw, for the cheek clumps
        head_parts.append(("ruff", mass([(0.20 * sx, -0.22, -0.13), (0.29 * sx, 0.02, -0.12), (0.28 * sx, 0.22, -0.06)],
                                        [(0.11, 0.12), (0.15, 0.16), (0.10, 0.12)], up=(0, 0, 1)), fur_face, "jaw"))
        # the eye: a small glowing almond in a dark socket under the brow
        p, nrm = face.hit((0.55 * sx, -0.62, 0.15), (-0.75 * sx, 0.6, -0.04))
        eyes.append((p, nrm))
        EYE_H.append(p.copy())
        along = Vector((0.0, 1.0, 0.18))
        eye = [(-0.5, -0.02), (-0.28, 0.11), (0.05, 0.17), (0.33, 0.15), (0.5, 0.05), (0.3, -0.08), (0.0, -0.12), (-0.3, -0.09)]
        sock = lens([(a * 0.17, b * 0.21) for a, b in eye], 0.03, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        sock.transform(facing(p - nrm * 0.02, nrm, along))
        head_parts.append(("socket", sock, dark, None))
        e = lens([(a * 0.12, b * 0.15) for a, b in eye], 0.024, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        e.transform(facing(p - nrm * 0.001, nrm, along))
        head_parts.append(("eyes", e, glow, None))
        # the closed mouth: a dark lip line along the upper lip, back to the corner under the eye
        lip = [(skull_at(y)[6] * 0.99 * sx, y, skull_at(y)[5] - 0.004) for y in (-0.9, -0.8, -0.7, -0.61, -0.53, -0.46)]
        head_parts.append(("lips", loft(lip, [0.005, 0.009, 0.01, 0.01, 0.009, 0.005], profile_round(5), up=(0, 0, 1), rings=10),
                           dark, None))
    # nose: a dark wedge on the tip of the muzzle
    nose = rounded_box((0.12, 0.10, 0.085), n=2.6, cuts=2)
    for v in nose.verts:
        v.co.x *= 1.0 - 0.25 * smooth(v.co.z, 0.04, -0.04)
    nose.transform(M((0, -1.02, 0.07), rot=(-12, 0, 0)))
    set_layer(nose, "gloss", 0.5)
    head_parts.append(("nose", nose, nose_m, None))
    # ears: tall and pointed, cupped, angled a little out
    ears = []
    for sx in (-1, 1):
        ear = ear_shape()
        E = M((0.15 * sx, -0.02, 0.22), rot=(-10, 14 * sx, 22 * sx))
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

    # ---- every base surface is in place: the fur lies on them --------------------------------------------
    surf = Surface(*[bm for _, bm, mat, _, _ in base if mat is not glow and mat is not dark])
    n_clumps = [0]

    def put(origin, toward, flow, L, W, region, lift=0.07, thick=0.045, bend=0.0, hug=1.0, boost=0.0, var=0.05, shade=1.0):
        o = Vector(origin)
        dvec = Vector(toward) - o
        p, nrm = surf.ray(o, dvec, dvec.length * 1.5)
        if p is None:
            return None
        bm = clump(surf, p, nrm, flow, L, W, lift=lift, thick=thick, bend=bend, seed=rnd.random(), hug=hug)
        c = colour(region, p, nrm) * (shade * (1.0 + var * (rnd.random() - 0.5) * 2))
        paint(bm, lambda co, n, c=c: c)
        add("clumps", bm, clump_m, crease=75, boost=boost)
        n_clumps[0] += 1
        return p

    O = H @ V((0, -0.3, -0.05))     # the mane's fur radiates from here, in the middle of the head

    def flow_at(p):
        """Which way the fur runs at p: out from the head and back over the mane, down the throat and
        chest, backwards along the back, back and down on the flanks."""
        if p.y < -0.3:
            f = (p - O).normalized()
            f.y = max(f.y, 0.35)                    # never forwards
            f = f.normalized() * 0.75 + V((0, 0.45, -0.55))
            front = smooth(-p.y, 0.85, 1.3) * smooth(p.z, 2.15, 1.65)
            return f.lerp(V((0, 0.2, -1)), front)
        k, ang = skin.angle_of(p)
        return V((0, 1, -0.15 - 0.95 * smooth(ang, 40, -40)))

    def on_skin(index, th, L, W, lift=0.05, thick=0.06, bend=0.0, region="body"):
        s = skin.s_of(index)
        c = skin.at(s)[0]
        o = skin.point(s, th, lift=0.9)
        return put(o, c, flow_at(skin.point(s, th)), L, W, region, lift=lift, thick=thick, bend=bend)

    # the mane: staggered rings of locks round the neck and chest, longest at the bottom (the bib)
    rings = [(1.2, 0.36, 15), (1.65, 0.4, 15), (2.1, 0.43, 15), (2.55, 0.46, 15), (3.0, 0.48, 14), (3.45, 0.48, 14),
             (3.9, 0.45, 13), (4.35, 0.4, 12)]
    for r, (idx, L, m) in enumerate(rings):
        for j in range(m):
            th = 90.0 + 360.0 * (j + 0.5 * (r % 2)) / m + rnd.uniform(-4, 4)
            low = -math.sin(math.radians(th))          # 1 at the belly side, -1 on the spine
            Lk = L * (1.0 + 0.3 * smooth(low, 0.0, 1.0)) * rnd.uniform(0.9, 1.1)
            on_skin(idx + rnd.uniform(-0.06, 0.06), th, Lk, 0.105 * rnd.uniform(0.9, 1.12),
                    lift=0.05 + 0.02 * r / len(rings), thick=0.065, bend=rnd.uniform(-0.12, 0.12))
    # the back: short locks either side of the spine, behind the mane
    for side_th in (90 - 22, 90 + 22, 90 - 50, 90 + 50):
        idx = 4.7 + 0.1 * (side_th % 5)
        while idx < 8.1:
            on_skin(idx, side_th + rnd.uniform(-4, 4), 0.25 * rnd.uniform(0.9, 1.1), 0.09, lift=0.03, thick=0.045,
                    bend=rnd.uniform(-0.08, 0.08))
            idx += 0.4
    # lower flanks and belly fringe, and the haunches
    for th in (-30.0, 210.0):
        for k in range(5):
            on_skin(4.75 + 0.42 * k, th + rnd.uniform(-5, 5), 0.3, 0.1, lift=0.04, thick=0.05)
    for th in (10.0, 170.0, 36.0, 144.0):
        for k in range(3):
            on_skin(6.9 + 0.45 * k, th + rnd.uniform(-5, 5), 0.28, 0.1, lift=0.04, thick=0.05)

    # legs: feathering behind the elbows, britches down the back of the thighs
    for sx, front, a, b in legs:
        if front:
            for k in range(3):
                z = a.z - 0.05 - 0.13 * k
                o = V((a.x + 0.02 * sx, a.y + 0.6, z))
                put(o, V((a.x, a.y - 0.05, z)), (0, 0.35, -1), 0.24 - 0.03 * k, 0.085, "leg", lift=0.035, thick=0.045)
        else:
            for k in range(5):
                z = 1.75 - 0.17 * k
                y = 0.95 + 0.06 * k
                o = V((a.x + 0.05 * sx * (k % 2), y + 0.8, z))
                put(o, V((a.x * 0.8, y - 0.2, z)), (0, 0.3, -1), 0.28, 0.1, "leg", lift=0.04, thick=0.05)

    # head: cheek ruff locks sweeping back, and a crest of locks off the back of the skull
    for sx in (-1, 1):
        for k, (y, z, L) in enumerate(((-0.24, -0.14, 0.22), (-0.08, -0.17, 0.25), (0.08, -0.14, 0.26), (-0.12, -0.03, 0.2),
                                       (0.06, -0.01, 0.22), (0.2, -0.08, 0.24))):
            o = H @ V((0.75 * sx, y, z))
            tgt = H @ V((0.0, y, z))
            flow = HR @ V((0.3 * sx, 1.0, -0.3))
            put(o, tgt, flow, L, 0.08, "head" if z > -0.05 else "jaw", lift=0.035, thick=0.045, boost=HEAD_BOOST)

    # tail: rings of locks running to the tip, the last ones closing into a point
    rings_t = 9
    for r in range(rings_t):
        t = 0.04 + 0.86 * r / (rings_t - 1)
        i = t * (len(TAIL) - 1)
        c = _cr([V(p) for p in TAIL], i)
        tan = (_cr([V(p) for p in TAIL], min(i + 0.05, len(TAIL) - 1)) - c).normalized()
        ref = V((0, 0, 1)) - tan * tan.z
        ref.normalize()
        sd = tan.cross(ref)
        m = 8 if r < rings_t - 1 else 6
        for j in range(m):
            a = 2 * math.pi * (j + 0.5 * (r % 2)) / m + rnd.uniform(-0.15, 0.15)
            out = ref * math.cos(a) + sd * math.sin(a)
            L = 0.36 + 0.08 * math.sin(math.pi * t)
            flow = tan - out * (0.35 if r >= rings_t - 2 else 0.0)
            put(c + out * 0.8, c, flow, L, 0.12, "tail", lift=0.04 + 0.02 * math.sin(math.pi * t), thick=0.06,
                bend=rnd.uniform(-0.1, 0.1))

    # ---- ice crystals: a ridge along the spine from the neck to mid back ----------------------------------
    for k, (idx, h) in enumerate(((1.7, 0.2), (2.25, 0.3), (2.85, 0.42), (3.45, 0.5), (4.05, 0.46), (4.65, 0.36), (5.2, 0.26), (5.7, 0.17))):
        s = skin.s_of(idx)
        c, t, u = skin.at(s)[:3]
        p, nrm = surf.hit(skin.point(s, 90.0, 1.0), -u)
        lean = (u * 0.85 + t * 0.5).normalized()
        cr = crystal(0.055 + 0.07 * h, h, seed=k)
        q = lean.to_track_quat('Z', 'Y')
        cr.transform(M(p - u * 0.04) @ q.to_matrix().to_4x4())
        add("ice", cr, glow, crease=15)
        for sx in (-1, 1):
            if h < 0.25 and sx > 0:
                continue
            s2, th2 = s + 0.08 * sx, 90.0 - 26 * sx
            o2 = skin.point(s2, th2, 1.0)
            p2, n2 = surf.ray(o2, skin.at(s2)[0] - o2)
            if p2 is None:
                continue
            lean2 = (n2 * 0.8 + t * 0.35 + skin.at(s)[3] * (0.25 * -sx)).normalized()
            h2 = h * rnd.uniform(0.45, 0.6)
            cr = crystal(0.04 + 0.06 * h2, h2, seed=k * 3 + sx)
            cr.transform(M(p2 - n2 * 0.03) @ lean2.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("ice", cr, glow, crease=15)

    # the base surfaces join the prop last, so the clumps above could be draped on them
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


def ear_shape():
    """A tall pointed ear in its own space: base on z=0, x across, front facing -y, cupped."""
    outline = [(-0.5, 0.0), (-0.47, 0.32), (-0.32, 0.66), (0.0, 1.0), (0.24, 0.7), (0.42, 0.36), (0.5, 0.0), (0.0, -0.06)]
    W, Hh = 0.25, 0.44
    rings = [(1.0, 0.0, 0.0), (0.85, -0.016, 0.032), (0.6, 0.016, 0.052), (0.3, 0.032, 0.066)]
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
    for loops, cy, gv in ((fronts, 0.035, 0.0), (backs, 0.07, 1.0)):
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


def ear_colour(H, ears):
    """Ears: midnight on the back and rim, frost-grey in the cup, darker towards the tip."""
    inv = [((H @ E).inverted(), (H @ E).to_3x3().normalized().inverted()) for sx, E in ears]

    def fn(co, n):
        loc, nl = min(((m @ co, r @ n) for m, r in inv), key=lambda ln: abs(ln[0].x) + abs(ln[0].y))
        h = loc.z / 0.44
        inner = smooth(-nl.y, 0.25, 0.7) * smooth(loc.y, -0.012, 0.012) * (1.0 - smooth(h, 0.62, 0.9))
        return band(lerp(0.06, 0.66, inner)) * (1.0 - 0.3 * smooth(h, 0.7, 1.0))
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


def threads():
    r = bpy.context.scene.render
    r.threads_mode, r.threads = 'FIXED', THREADS


def bake(wolf, texture):
    """Everything that does not glow becomes one textured mesh, FrostWolf_Body (colour and soft crease
    shading baked into a 1024 image, 512 under PETS_FAST, packed by real outlines, barely seen surfaces
    given less of it, plus a baked roughness image). The glowing parts (crystals and eyes) join into
    FrostWolf_GLOW. Objects are matched by name prefix, since Blender renames shared materials
    ("GLOW_Frost.001") when several pets share a scene."""
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
                                shade=0.5, soften=2, rough=0.88, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved
    rough_map(body, texture, 0.88, 0.08)
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
    junk = ("hid", "boost", "grad", "fu", "fq", "fs", "gloss", "col")
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
    return head_matrix() @ Vector((0, -0.5, 0.05)) * SCALE


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
