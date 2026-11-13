"""Wolf pet: a legendary shadow wolf. Built from scratch by script.

    python models/pets/wolf.py --review out/wolf.png      # render the review sheet
    python models/pets/wolf.py --export models/export/wolf.fbx

Style: the fourth legendary creature beside the dragon, the phoenix and the griffin: cool, noble and
powerful, never cute, never creepy, never plastic. Must-haves, checked in every review:
  1. Reads as a wolf in outline, standing proud: four long legs planted, a deep chest, a narrow waist,
     the head raised on a thick neck framed by a layered mane, ears up, a bushy tail held low.
  2. Adult proportions: the head about a fifth of the body length; shoulder 4.5 to 5 studs, the top
     of the raised head 6.5 to 7.5, 8 to 10 studs long with the tail.
  3. A calm, noble face like a wolf on a knight's shield: a broad angular skull, a strong medium-length
     muzzle, the mouth closed (no teeth), slanted glowing eyes without pupils under a heavy brow.
  4. Shadow palette: charcoal-black to deep-indigo fur, a silver-grey underside, muzzle and ruff, and
     a modest violet glow (the eyes, four dark crystals on the spine, a faint tip to the tail).
  5. Not plastic: streaked fur, layered fur shards that shade each other, a matte finish, darker on
     the back and lighter underneath, crisp creases on the brow, cheekbones, claws and crystals.

Round 5: a broader outline from the front (the game camera's view), where it read as a tall narrow
column with a white beard: the mane now flares out sideways (its shards are longer and stand further
off at the sides), the silver narrows to a V at the throat, the chest and shoulders are broader, the
stance wider and the neck a little shorter. Bigger dark crystals with thinner glowing seams (they read
as glowing bars). A calmer texture on the face, and the cheek ruff swept back so it no longer pokes
out past the muzzle.

Round 4: a sculpted head instead of a brick: a wedge skull with a domed crown and flared cheekbones,
a narrow bridge to the muzzle widening to the lips, a rounded muzzle end, and a cheek ruff that flares
out sideways so the head reads as a wolf's from the front. Stronger legs: muscle at the top of the
forearm and the gaskin, thicker pasterns, bigger front paws, a slightly wider stance. Finer, shorter
fur streaks (they read as pinstripes on the legs), and finer still on the face.

Round 3: more mass and shape in the body: thicker legs, a lower hip muscle (it stood out as a lump)
and five tiers of shaggy fur along the back and upper flanks, so the trunk is no longer a smooth tube.
A separate lower jaw sits just inside the upper lip, so the closed mouth is a natural crease in shadow
and not a drawn line (that read as deadpan). The fur now shows on the dark coat: indigo-slate
highlights follow the streaks and the strands of each shard. A deeper violet in the glow.

Round 2: a calmer, nobler face: bigger open almond eyes with the brow level above them instead of
pressing down (it read as a sleepy, grumpy dog), a longer, tapered muzzle with a small angular nose, a
shorter lip line, darker fur in the ears. More mass: a deeper chest, a thicker neck under a much
fuller mane, thicker forearms, fur shards on the backs of the elbows and thighs and along the belly.
A darker coat (it read mid-grey) and a bluer violet glow (it read pink).

Round 1: the first build. A lofted skin from the rump into the head, continuous lofted legs, an
angular skull shell with a closed muzzle, rings of fur shards for the mane, ruff, bib and tail.
"""
import argparse
import bisect
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, rounded_box  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

HEAD_AT = Vector((-0.06, -3.30, 5.88))   # the middle of the skull, between the ears
HEAD_ROT = (2, 0, -10)                   # muzzle level, turned a little towards -X (the cameras)
HEAD_SIZE = 1.06

# The trunk and neck are one skin over these sections, from the rump to inside the head:
# centre x, y, z, then half width, height above the centre line (the back), depth below it, squareness.
BODY = [
    (0.00, 2.62, 3.98, 0.28, 0.26, 0.28, 2.0),    # 0  end of the rump, where the tail grows
    (0.00, 2.30, 3.92, 0.72, 0.54, 0.72, 2.1),    # 1  rump
    (0.00, 1.65, 3.94, 0.84, 0.58, 0.78, 2.2),    # 2  hips
    (0.00, 0.85, 3.92, 0.74, 0.48, 0.62, 2.2),    # 3  loins: the narrow waist, the belly tucked up
    (0.00, 0.05, 3.84, 0.88, 0.60, 1.02, 2.2),    # 4  back of the ribs
    (0.00, -0.75, 3.78, 1.00, 0.86, 1.34, 2.2),   # 5  ribcage, deep
    (0.00, -1.45, 3.80, 1.05, 1.00, 1.40, 2.15),  # 6  shoulders: withers at 4.8, brisket at 2.4
    (0.00, -2.05, 3.80, 0.88, 0.86, 1.08, 2.1),   # 7  chest, broad and pushed out
    (0.00, -2.38, 3.86, 0.42, 0.50, 0.55, 2.0),   # 8  the point of the chest
]
# The neck is a skin of its own, from inside the shoulders up into the head (the mane hides the join).
NECK = [
    (0.00, -1.70, 4.00, 0.70, 0.74, 0.80, 2.0),   # inside the shoulders
    (0.00, -2.20, 4.52, 0.70, 0.70, 0.78, 2.0),   # base of the neck, out of the chest
    (0.00, -2.56, 5.04, 0.58, 0.56, 0.60, 2.0),   # neck
]
NECK_TOP = [(0, 0.52, -0.26), (0.44, 0.40, 0.42, 2.0), (0, 0.28, -0.10), (0.30, 0.28, 0.26, 2.0)]   # in head space

# The skull, in its own space (muzzle towards -Y): y, crown z and half width, brow corner z and half
# width, cheek z and half width, jaw corner z and half width, chin z. Flat planes between corners.
SKULL = [
    (0.48, 0.18, 0.10, 0.06, 0.22, -0.14, 0.26, -0.34, 0.20, -0.42),      # into the neck
    (0.30, 0.31, 0.14, 0.19, 0.29, -0.07, 0.36, -0.34, 0.25, -0.42),      # back of the skull
    (0.08, 0.37, 0.15, 0.25, 0.31, -0.03, 0.42, -0.31, 0.26, -0.38),      # crown, the cheekbones flare widest
    (-0.14, 0.35, 0.12, 0.25, 0.28, -0.03, 0.36, -0.27, 0.24, -0.33),     # over the eyes
    (-0.32, 0.255, 0.08, 0.17, 0.18, -0.05, 0.25, -0.24, 0.205, -0.265),  # the stop
    (-0.56, 0.195, 0.05, 0.13, 0.12, -0.06, 0.185, -0.21, 0.17, -0.235),  # muzzle: a narrow bridge, broad lips
    (-0.82, 0.16, 0.04, 0.10, 0.10, -0.07, 0.15, -0.19, 0.14, -0.21),
    (-1.0, 0.125, 0.03, 0.075, 0.075, -0.08, 0.11, -0.165, 0.10, -0.185),
    (-1.06, 0.09, 0.02, 0.05, 0.05, -0.08, 0.07, -0.15, 0.065, -0.17),    # the rounded end of the muzzle
]
# The lower jaw, just inside the upper lip so that the closed mouth is a crease in shadow:
# y, top z, top half width, lip corner z and half width, chin z.
JAW = [
    (0.10, -0.24, 0.20, -0.32, 0.22, -0.40),
    (-0.14, -0.24, 0.19, -0.30, 0.20, -0.37),
    (-0.32, -0.22, 0.16, -0.27, 0.17, -0.33),
    (-0.56, -0.20, 0.13, -0.245, 0.142, -0.30),
    (-0.80, -0.185, 0.105, -0.225, 0.115, -0.27),
    (-0.95, -0.175, 0.075, -0.21, 0.08, -0.245),
]

# Cross-sections, (side, up), going round.
P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]

# Width of a fur shard along its length, as a fraction of its half width (0 root, 1 tip).
LOCK = [(0, 0.0), (0.1, 0.6), (0.4, 1.0), (0.75, 0.75), (1, 0.0)]

# The coat: charcoal-black, deep indigo, slate, silver-grey (read from each vertex's colour position g).
COAT = [(0.0, "#0B0B11"), (0.14, "#13131D"), (0.32, "#1F2139"), (0.52, "#3D4162"), (0.72, "#7A7F98"), (1.0, "#B4B8C6")]


# ---- small helpers ----------------------------------------------------------------------------------

def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _super(a, n):
    """A point on a unit superellipse (n=2 is a circle, larger is squarer)."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def _table(points, x):
    """Straight-line reading of a table of (x, value) pairs."""
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


LAYERS = ("g", "xn", "d", "f")


def _layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in LAYERS]


def paint(bm, g, feather=0.0):
    """Give every vertex of a shape the colour position g: a number, or a function of the vertex
    (its co and normal are up to date)."""
    lg, lx, ld, lf = _layers(bm)
    if callable(g):
        bm.normal_update()
    for v in bm.verts:
        v[lg] = g(v) if callable(g) else g
        v[lf] = feather
    return bm


def sharpen(bm, degrees):
    """Mark the edges where the surface turns by more than `degrees` as sharp: crisp creases."""
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


class Curve:
    """A smooth curve through `points`, read by the fraction t of its length (0 to 1)."""

    def __init__(self, points, n=160):
        pts = [Vector(p) for p in points]
        k = len(pts) - 1
        self.p = [_cr(pts, i / n * k) for i in range(n + 1)]
        self.run = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.run.append(self.run[-1] + (b - a).length)
        self.L = self.run[-1]

    def at(self, t):
        d = self.L * min(max(t, 0.0), 1.0)
        j = min(max(bisect.bisect_right(self.run, d) - 1, 0), len(self.p) - 2)
        f = (d - self.run[j]) / max(self.run[j + 1] - self.run[j], 1e-9)
        return self.p[j].lerp(self.p[j + 1], f)

    def tangent(self, t):
        e = 0.01
        return (self.at(min(t + e, 1.0)) - self.at(max(t - e, 0.0))).normalized()


def loft(points, n, profile, up=None, side=None, ref=None, g=(0.0, 0.0), gpow=1.0, feather=False, sharp=(),
         tip=False, root=False):
    """A closed shape lofted along a smooth curve through `points`, in n steps. profile(t) gives the
    cross-section at t (0 at the root, 1 at the tip) as (across, through) pairs. The through
    direction follows `up`, or is square to the across direction `side`; `ref` picks which way it
    faces. With tip (root) the shape closes to a point at its tip (root), else it is capped flat.
    Each vertex stores its colour position g (g[0] at the root to g[1] at the tip), how far across
    it is (xn, -1 to 1), how far along it is in studs (d) and whether it is a fur shard (f)."""
    C = Curve(points)
    bm = bmesh.new()
    lg, lx, ld, lf = _layers(bm)
    rings, sign = [], None
    for i in range(n + 1):
        t = i / n
        p, T = C.at(t), C.tangent(t)
        if side is not None:
            s = Vector(side(t) if callable(side) else side)
            W = (s - T * s.dot(T)).normalized()
            N = W.cross(T)
        else:
            u = Vector(up(t) if callable(up) else up)
            N = (u - T * u.dot(T)).normalized()
            W = T.cross(N)
        if sign is None:
            r = ref(t) if callable(ref) else ref
            sign = -1.0 if (r is not None and N.dot(Vector(r)) < 0) else 1.0
        N = N * sign
        gv = g[0] + (g[1] - g[0]) * t ** gpow
        fv = 1.0 if feather else 0.0
        if (tip and i == n) or (root and i == 0):
            v = bm.verts.new(p)
            v[lg], v[lx], v[ld], v[lf] = gv, 0.0, C.L * t, fv
            rings.append([v])
            continue
        prof = profile(t)
        wmax = max(abs(x) for x, _ in prof) or 1.0
        ring = []
        for x, y in prof:
            v = bm.verts.new(p + W * x + N * y)
            v[lg], v[lx], v[ld], v[lf] = gv, x / wmax, C.L * t, fv
            ring.append(v)
        rings.append(ring)
    m = max(len(r) for r in rings)
    for a, b in zip(rings, rings[1:]):
        for j in range(m):
            if len(a) == 1:
                bm.faces.new((a[0], b[(j + 1) % m], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[(j + 1) % m], b[0]))
            else:
                bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    if len(rings[0]) > 1:
        bm.faces.new(rings[0])
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    for j in sharp:
        for a, b in zip(rings, rings[1:]):
            if len(a) > 1 and len(b) > 1:
                bm.edges.get((a[j], b[j])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def fixed(radii, shape):
    """A cross-section of the given `shape`, scaled along the path by (side, up) radii (or one
    number), spread evenly from the root to the tip."""
    rs = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]

    def prof(t):
        u = t * (len(rs) - 1)
        rx = max(_cr([r[0] for r in rs], u), 1e-3)
        rz = max(_cr([r[1] for r in rs], u), 1e-3)
        return [(a * rx, b * rz) for a, b in shape]
    return prof


def limb(points, radii, shape, n, up):
    """One continuous limb lofted through `points`, with the (side, up) radius radii[k] at points[k]
    (read by the length along the path, so a joint gets its own thickness)."""
    pts = [Vector(p) for p in points]
    run = [0.0]
    for a, b in zip(pts, pts[1:]):
        run.append(run[-1] + (b - a).length)
    ts = [r / run[-1] for r in run]
    rx = list(zip(ts, [r[0] for r in radii]))
    rz = list(zip(ts, [r[1] for r in radii]))

    def prof(t):
        return [(a * _table(rx, t), b * _table(rz, t)) for a, b in shape]
    return loft(pts, n, prof, up=up)


def round_shape(k=10):
    return [(math.cos(2 * math.pi * j / k), math.sin(2 * math.pi * j / k)) for j in range(k)]


def blade(widths, W, h, cup=0.14, thin=0.35):
    """The cross-section of a fur shard: two sharp edges, a raised spine on top and a keel under it,
    `W` to each side at its widest and `h` through, arched by `cup`, thinning towards the tip."""
    def prof(t):
        w = max(W * _table(widths, t), 0.004)
        hh = min(h * 0.8 * (1 - (1 - thin) * t), w * 0.25)
        c = cup * w
        return [(-w, -c), (0.0, hh), (w, -c), (0.0, -c - hh * 0.5)]
    return prof


def row(place, count, closed=False, cols=2, rows=3, depth=0.6, lift=0.08, sink=0.04, ridge=0.03, thick=0.03,
        g=(0.1, 0.4), gpow=1.0, L=0.6, point=1.0):
    """A row of pointed fur shards as one closed sheet. place(u, v) gives the point and the outward
    normal of the surface the row lies on: u runs across the row (shard j spans j to j + 1), v from
    the roots (0) to the tips (1). Between two shards the tips are cut back by `depth`, so each one
    ends in a sharp point. Each has a raised spine (`ridge`), stands `lift` proud of the surface at its
    tip and is buried `sink` at its root, so the next row covers its root. g is (root, tip) or a
    function g(u, v); lift may be a function of u."""
    bm = bmesh.new()
    lg, lx, ld, lf = _layers(bm)
    ncol = count * cols + (0 if closed else 1)
    top, bot = [], []
    for c in range(ncol):
        u = c / cols
        q = 2.0 * (c % cols) / cols - 1.0
        vt = 1.0 - depth * abs(q) ** point
        tc, bc = [], []
        for r in range(rows + 1):
            v = vt * r / rows
            p, nrm = place(u, v)
            lifted = lift(u) if callable(lift) else lift
            up = -sink + (lifted + sink) * v ** 1.2 + ridge * (1 - abs(q)) * min(1.0, 3 * v + 0.3)
            rim = r in (0, rows) or (not closed and c in (0, ncol - 1))
            gv = g(u, v) if callable(g) else g[0] + (g[1] - g[0]) * v ** gpow
            for lst, off in ((tc, up), (bc, up - thick * (0.5 + 0.5 * v))):
                if rim and lst is bc:
                    bc.append(tc[-1])
                    continue
                vert = bm.verts.new(p + nrm * off)
                vert[lg], vert[lx], vert[ld], vert[lf] = gv, q, v * L, 1.0
                lst.append(vert)
        top.append(tc)
        bot.append(bc)
    pairs = [(c, (c + 1) % ncol) for c in range(ncol if closed else ncol - 1)]
    for c, d in pairs:
        for r in range(rows):
            bm.faces.new((top[c][r], top[d][r], top[d][r + 1], top[c][r + 1]))
            bm.faces.new((bot[c][r + 1], bot[d][r + 1], bot[d][r], bot[c][r]))
        bm.edges.get((top[c][rows], top[d][rows])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lens(outline, thick, rows=((0.55, 0.8), (1.0, 0.0)), centre=(0.0, 0.0)):
    """A pebble: flat, `thick` through the middle and thinning to its rim, with the outline given as
    (a, b) points going round `centre`. It lies in the XZ plane, a along X and b along Z."""
    bm = bmesh.new()
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
    """A transform for a shape lying on a surface: its X runs `along`, its Y looks out of the surface
    along `out` (a lens() lies flat on it), its Z completes the frame."""
    y = Vector(out).normalized()
    x = Vector(along)
    x = (x - y * x.dot(y)).normalized()
    z = x.cross(y)
    if z.z < 0:
        y, z = -y, -z
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def frame(origin, axis, hint=(1, 0, 0)):
    """A transform whose Z runs along `axis`, its X as near `hint` as it can be."""
    z = Vector(axis).normalized()
    x = Vector(hint)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def crystal(h, r, sides=6, rot=0.0, sink=0.14, shoulder=0.6, lean=0.0):
    """A pointed crystal standing on +Z: straight faceted sides from z=-sink up to `shoulder` of its
    height, then a faceted point (pushed `lean` along X, so it is not a perfect pyramid)."""
    bm = bmesh.new()
    rings = []
    for z, k in ((-sink, 0.9), (h * shoulder, 1.0)):
        rings.append([bm.verts.new((r * k * math.cos(math.radians(rot + 360.0 * j / sides)),
                                    r * k * math.sin(math.radians(rot + 360.0 * j / sides)), z)) for j in range(sides)])
    apex = bm.verts.new((lean * r, 0.0, h))
    a, b = rings
    for j in range(sides):
        bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        bm.faces.new((b[j], b[(j + 1) % sides], apex))
    bm.faces.new(a[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _layers(bm)
    return bm


def shell(sections, corners, per=3, m=2, back_cap=0.0, nose_cap=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives the outline of one
    section as (x, z) corner points going round. Straight sides between corners make flat planes,
    each split m times so the shading stays smooth across it."""
    k = len(sections) - 1
    width = len(sections[0])
    rings = []
    for i in range(k * per + 1):
        sec = [_cr([s[j] for s in sections], i / per) for j in range(width)]
        cs = corners(sec)
        pts = []
        for a, b in zip(cs, cs[1:] + cs[:1]):
            for f in range(m):
                pts.append((a[0] + (b[0] - a[0]) * f / m, a[1] + (b[1] - a[1]) * f / m))
        rings.append((sec[0], pts))
    bm = bmesh.new()
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


def skull_corners(sec):
    y, zt, wt, zb, wb, zc, wc, zj, wj, zk = sec
    dome = 0.2 * wt                                   # the crown and the bridge are gently rounded
    return [(0, zt + dome), (-0.5 * wt, zt + dome * 0.7), (-wt, zt), (-wb, zb), (-wc, zc), (-wj, zj),
            (-0.5 * wj, zk + 0.025), (0, zk), (0.5 * wj, zk + 0.025), (wj, zj), (wc, zc), (wb, zb),
            (wt, zt), (0.5 * wt, zt + dome * 0.7)]


def jaw_corners(sec):
    y, zt, wt, zl, wl, zk = sec
    return [(0, zt), (-wt, zt), (-wl, zl), (-0.5 * wl, zk + 0.02), (0, zk), (0.5 * wl, zk + 0.02), (wl, zl), (wt, zt)]


class Surface:
    """Finds points exactly on a mesh, so that details sit on it and neither float nor sink."""

    def __init__(self, bm):
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, direction, out=0.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


class Skin:
    """A smooth skin over sections along a path. Positions on it are (s, angle): s is the distance
    along the path from its first section (the rump), the angle goes round the section in degrees,
    90 on the back (the back of the neck), -90 underneath (the throat), 0 on the +X side."""

    def __init__(self, sections, samples=24):
        k = len(sections) - 1
        centres = [Vector(sec[:3]) for sec in sections]
        self.samples = samples
        self.pts = [_cr(centres, i / samples) for i in range(k * samples + 1)]
        self.par = [[_cr([sec[j] for sec in sections], i / samples) for j in range(3, 7)] for i in range(k * samples + 1)]
        self.len = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.len.append(self.len[-1] + (b - a).length)
        self.L = self.len[-1]
        n = len(self.pts)
        self.T = [(self.pts[min(i + 1, n - 1)] - self.pts[max(i - 1, 0)]).normalized() for i in range(n)]
        X = Vector((1, 0, 0))
        self.U = [t.cross(X).normalized() for t in self.T]

    def s_of(self, index):
        x = index * self.samples
        i = min(int(x), len(self.len) - 2)
        return self.len[i] + (self.len[i + 1] - self.len[i]) * (x - i)

    def at(self, s):
        s = min(max(s, 0.0), self.L)
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.pts) - 2)
        f = (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)
        c = self.pts[i].lerp(self.pts[i + 1], f)
        t = self.T[i].lerp(self.T[i + 1], f).normalized()
        u = self.U[i].lerp(self.U[i + 1], f)
        u = (u - t * u.dot(t)).normalized()
        w, a, b, n = (p + (q - p) * f for p, q in zip(self.par[i], self.par[i + 1]))
        return c, t, u, u.cross(t), w, a, b, n

    def bare(self, s, th):
        c, t, u, side, w, a, b, n = self.at(s)
        x, y = _super(math.radians(th), n)
        return c + side * (w * x) + u * ((a if y > 0 else b) * y)

    def normal(self, s, th):
        ds = self.bare(min(s + 0.02, self.L), th) - self.bare(max(s - 0.02, 0.0), th)
        dt = self.bare(s, th + 2.0) - self.bare(s, th - 2.0)
        nrm = dt.cross(ds).normalized()
        return nrm if nrm.dot(self.bare(s, th) - self.at(s)[0]) > 0 else -nrm

    def point(self, s, th, lift=0.0):
        p = self.bare(s, th)
        return p + self.normal(s, th) * lift if lift else p

    def toward(self, s0, th, dist, sgn=-1):
        """The s at which the skin at angle th lies `dist` studs from (s0, th), going towards the
        rump (sgn -1) or the head (sgn 1)."""
        p0, s1 = self.bare(s0, th), s0 + sgn * dist
        for _ in range(3):
            d = (self.bare(min(max(s1, 0.0), self.L), th) - p0).length
            s1 = s0 + (s1 - s0) * dist / max(d, 1e-6)
        return min(max(s1, 0.0), self.L)

    def mesh(self, segs=20, k=0.42, lo=0.13, hi=0.42, g=None):
        """The skin as one mesh, its vertices painted with g(s, angle)."""
        ss, s = [0.0], 0.0
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            ss.append(s)
        ss.append(self.L)
        bm = bmesh.new()
        lg = _layers(bm)[0]
        loops = []
        for s in ss:
            loop = []
            for j in range(segs):
                th = 90.0 + 360.0 * j / segs
                v = bm.verts.new(self.bare(s, th))
                v[lg] = g(s, th) if g else 0.0
                loop.append(v)
            loops.append(loop)
        folds = 0
        for (s0, a), (s1, b) in zip(zip(ss, loops), zip(ss[1:], loops[1:])):
            t = self.at((s0 + s1) / 2)[1]
            folds += sum(1 for p, q in zip(a, b) if (q.co - p.co).dot(t) <= 0)
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
        if folds:
            print("warning: the skin folds over itself at %d points" % folds)
        for ring, s in ((loops[0], 0.0), (loops[-1], self.L)):
            c = bm.verts.new(self.at(s)[0])
            c[lg] = sum(v[lg] for v in ring) / segs
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm


def ring_of(skin, s0, count, L_of, stagger=0.0, th0=None, span=360.0):
    """place() for a ring (or with th0 and span, an arc) of shards on the skin, from s0 towards the
    rump, and th_of(u), the angle of a point of the row."""
    dth = span / count
    cache = {}

    def th_of(u):
        if th0 is None:
            return 90.0 + (u - 0.5 + stagger) * dth
        return th0 + u * dth

    def place(u, v):
        th = th_of(u)
        key = round(th, 5)
        if key not in cache:
            cache[key] = skin.toward(s0, th, L_of(th))
        s = s0 + (cache[key] - s0) * v
        return skin.bare(s, th), skin.normal(s, th)
    return place, th_of


# ---- materials --------------------------------------------------------------------------------------

def _node_ops(tree):
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

    def remap(src, a, b, lo=0.0, hi=1.0, smooth=False):
        r = new("ShaderNodeMapRange")
        if smooth:
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
    return new, link, attr, op, remap, ramp


def coat_material(name, stops, streak, strands=2.5, strand_amt=0.16, rough=0.88, frost=0.0, frost_colour="#4A5080"):
    """Fur: a colour ramp read from each vertex's colour position g, kit.furry's streaks over it so it
    is not flat plastic, and on the fur shards (f = 1) light and dark strands running their length,
    a little darker at the edges."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **streak)
    tree = m.node_tree
    new, link, attr, op, remap, ramp = _node_ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    link(ramp(attr("g"), stops), hsv.inputs["Color"])
    old = hsv.inputs["Value"].links[0].from_socket
    xn, f = attr("xn"), attr("f")
    phase = op('MULTIPLY_ADD', attr("d"), 0.6, xn)
    lines = op('MULTIPLY_ADD', op('SINE', op('MULTIPLY', phase, strands * math.pi)), strand_amt, 1.0)
    pattern = op('MULTIPLY', lines, remap(op('ABSOLUTE', xn), 0.55, 1.0, 1.0, 0.78))
    mixed = op('MULTIPLY_ADD', op('SUBTRACT', pattern, 1.0), f, 1.0)
    link(op('MULTIPLY', old, mixed), hsv.inputs["Value"])
    if frost:
        # a near-black coat hides any streak made by darkening it, so the light streaks (and on a shard
        # its light strands) also screen in a cool indigo-slate, like the sheen on dark fur
        streak = next(n for n in tree.nodes if n.type == 'TEX_NOISE' and abs(n.inputs["Scale"].default_value - 1.0) < 1e-6)
        # kit.furry's streaks run down the shape, so on surfaces facing up they turn into blotches: there,
        # and on every shard, the sheen follows the shard's own strands instead
        geo = new("ShaderNodeNewGeometry")
        sep = new("ShaderNodeSeparateXYZ")
        link(geo.outputs["Normal"], sep.inputs[0])
        upright = remap(op('ABSOLUTE', sep.outputs[2]), 0.35, 0.8, 1.0, 0.0, smooth=True)
        fac = op('MULTIPLY', remap(streak.outputs[0], 0.5, 0.72, 0.0, frost, smooth=True), op('MULTIPLY', upright, op('SUBTRACT', 1.0, f)))
        fac = op('ADD', fac, op('MULTIPLY', remap(lines, 1.0, 1.0 + strand_amt, 0.0, frost * 0.8), f))
        b = kit.principled(m)
        sheen = new("ShaderNodeMix")
        sheen.data_type, sheen.blend_type = 'RGBA', 'SCREEN'
        link(fac, sheen.inputs[0])
        link(hsv.outputs["Color"], sheen.inputs[6])
        sheen.inputs[7].default_value = (*kit.srgb(frost_colour), 1.0)
        link(sheen.outputs[2], b.inputs["Base Color"])
    return m


def ramp_material(name, stops, rough=0.5, streak=None):
    """A hard surface (claws, crystals): a ramp read from g with a faint mottle."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **(streak or dict(strength=0.05, mottle=0.06, fine=40.0, length=2.0)))
    tree = m.node_tree
    new, link, attr, op, remap, ramp = _node_ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    link(ramp(attr("g"), stops), hsv.inputs["Color"])
    return m


# ---- the wolf ---------------------------------------------------------------------------------------

def build():
    coat = coat_material("Coat", COAT, dict(strength=0.36, mottle=0.14, fine=9.5, length=4.5), frost=0.42)
    facecoat = coat_material("Face", COAT, dict(strength=0.22, mottle=0.06, fine=17.0, length=3.0), frost=0.12)
    tipfur = coat_material("TipFur", [(0.0, "#1A1B2A"), (0.5, "#2E2852"), (1.0, "#6A4FB0")],
                           dict(strength=0.3, mottle=0.1, fine=7.0, length=6.0), frost=0.3, frost_colour="#5A4A9A")
    claw = ramp_material("Claw", [(0.0, "#2A2A34"), (0.6, "#16161D"), (1.0, "#0A0A0E")], rough=0.45)
    crystal_mat = ramp_material("Crystal", [(0.0, "#0F0E1C"), (0.55, "#231D40"), (1.0, "#4A3A85")], rough=0.3)
    dark = kit.material("Dark", "#0B0B10", rough=0.5)
    glow = kit.material("GLOW_Violet", "#6E44FF", rough=0.4, emit=2.2)

    wolf = Prop("Wolf")
    wolf.tally = {}

    def add(part, bm, mat, at=None, crease=None):
        _layers(bm)
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if crease:
            sharpen(bm, crease)
        wolf.tally[part] = wolf.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        wolf.add(bm, mat)

    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)

    def hs(p):
        return tuple(H @ Vector(p))

    # ---- trunk: a skin, dark on the back, silver underneath; the neck is a second skin into the head --
    skin = Skin(BODY)
    neck = Skin(NECK + [(*hs(NECK_TOP[0]), *NECK_TOP[1]), (*hs(NECK_TOP[2]), *NECK_TOP[3])])

    def skin_g(s, th):
        sn = math.sin(math.radians(th))
        if sn >= 0:
            return 0.18 - 0.13 * sn
        return 0.18 + 0.6 * smooth(sn, -0.3, -0.9)
    add("skin", skin.mesh(segs=20, g=skin_g), coat)
    add("skin", neck.mesh(segs=18, g=skin_g), coat)

    # ---- mane: rings of long shards round the neck, flaring out; dark over the nape, silver at the throat
    def mane_g(th, v, base=0.0):
        sn = math.sin(math.radians(th))
        g = 0.10 + 0.16 * (1 - sn) if sn >= 0 else 0.26 + 0.58 * smooth(sn, -0.45, -0.92)
        return min(g + base + 0.05 * v, 1.0)

    for i, idx in enumerate((3.25, 2.85, 2.45, 2.05, 1.65, 1.25)):
        s = neck.s_of(idx)
        L = 0.66 + 0.08 * i
        count = 13 if i % 2 == 0 else 14
        side = 0.12 + 0.06 * i                                   # the lower rings flare out to the sides

        def L_of(th, L=L, i=i, side=side):
            return L * (1 + 0.1 * math.sin(math.radians(th) * 3 + i)) * (1 + side * abs(math.cos(math.radians(th))) ** 1.2)
        place, th_of = ring_of(neck, s, count, L_of, 0.5 * (i % 2))

        def lift(u, th_of=th_of, i=i):
            th = math.radians(th_of(u))
            return 0.18 + 0.03 * i + (0.06 + 0.06 * i) * abs(math.cos(th)) ** 1.2 - 0.06 * max(0.0, -math.sin(th))
        add("mane", row(place, count, closed=True, rows=3, depth=0.55, lift=lift, sink=0.05, ridge=0.035,
                        thick=0.04, g=lambda u, v, th_of=th_of: mane_g(th_of(u), v), L=L, point=0.85), coat)
    # a mantle over the withers and the tops of the shoulders, the last of the mane
    for k, (idx, L) in enumerate(((7.25, 1.0), (6.75, 0.9))):
        place, th_of = ring_of(skin, skin.s_of(idx), 11, lambda th, L=L: L, th0=-25.0 - 5 * k, span=230.0 + 10 * k)
        add("mane", row(place, 11, rows=3, depth=0.55, lift=0.26 - 0.06 * k, sink=0.05, ridge=0.035, thick=0.04,
                        g=lambda u, v, th_of=th_of: mane_g(th_of(u), v), L=L, point=0.85), coat)
    # chest bib: arcs of silver shards down the front of the chest
    for k, (idx, L) in enumerate(((7.9, 0.85), (7.5, 0.75))):
        place, th_of = ring_of(skin, skin.s_of(idx), 7, lambda th, L=L: L, th0=-160.0 + 6 * k, span=140.0)
        add("bib", row(place, 7, rows=3, depth=0.5, lift=0.1, sink=0.05, ridge=0.03, thick=0.04,
                       g=lambda u, v, th_of=th_of: mane_g(th_of(u), v, 0.04), L=L, point=0.85), coat)
    # tiers of shaggy fur over the back and the upper flanks, each one lying over the roots of the next
    for k, idx in enumerate((6.25, 5.35, 4.45, 3.55, 2.65)):
        L = 0.78 - 0.02 * k
        count = 9 if k % 2 == 0 else 10
        place, th_of = ring_of(skin, skin.s_of(idx), count, lambda th, L=L, k=k: L * (1 + 0.1 * math.sin(math.radians(th) * 4 + k)),
                               th0=8.0 - 4 * (k % 2), span=164.0 + 8 * (k % 2))
        add("coat", row(place, count, rows=2, depth=0.55, lift=0.08, sink=0.04, ridge=0.03, thick=0.035,
                        g=lambda u, v, th_of=th_of: skin_g(0, th_of(u)) + 0.05 * v, L=L, point=0.85), coat)
    # a fringe of longer fur along the underside of the ribcage
    for k, (idx, L) in enumerate(((5.5, 0.6), (4.8, 0.55))):
        place, th_of = ring_of(skin, skin.s_of(idx), 7, lambda th, L=L: L, th0=-150.0 + 8 * k, span=120.0)
        add("fringe", row(place, 7, rows=2, depth=0.5, lift=0.1, sink=0.04, ridge=0.03, thick=0.035,
                          g=lambda u, v, th_of=th_of: skin_g(0, th_of(u)) + 0.06 * v, L=L, point=0.85), coat)

    def strip(roots, D, out, length, count, **kw):
        """A row of shards whose roots run along the curve through `roots`, pointing along D, lying on
        a surface that faces `out`."""
        C = Curve(roots)
        D, out = Vector(D).normalized(), Vector(out).normalized()

        def place(u, v):
            return C.at(u / count) + D * length * v, out
        return row(place, count, **kw)

    # ---- legs: long and powerful, each one continuous loft from the shoulder or hip to the paw --------
    def leg_g(sx):
        def g(v):
            n = v.normal
            return 0.17 + 0.42 * smooth(-n.x * sx, 0.1, 0.85) + 0.1 * smooth(n.y, 0.3, 0.9) + 0.25 * smooth(n.z, -0.3, -0.9)
        return g

    for sx in (-1, 1):
        fore = [(0.6 * sx, -1.38, 3.95), (0.68 * sx, -1.12, 2.85), (0.66 * sx, -1.2, 2.25), (0.62 * sx, -1.3, 1.5),
                (0.61 * sx, -1.36, 0.95), (0.61 * sx, -1.42, 0.6), (0.61 * sx, -1.5, 0.26)]
        add("legs", paint(limb(fore, [(0.46, 0.72), (0.42, 0.6), (0.37, 0.46), (0.3, 0.34), (0.25, 0.28), (0.25, 0.28), (0.26, 0.3)],
                               P_LEG, 20, up=(0, -1, 0.05)), leg_g(sx)), coat)
        add("legs", paint(kit.ball((0.56, 1.1, 1.4), cuts=3), leg_g(sx)), coat, M((0.71 * sx, -1.45, 3.45), rot=(18, 0, 0)))
        # feathering down the back of the forearm
        add("legs", strip([(0.68 * sx, -0.84, 2.75), (0.65 * sx, -0.9, 2.25), (0.63 * sx, -0.98, 1.75)], (0, 0.45, -1), (0.2 * sx, 1, 0),
                          0.42, 4, rows=2, depth=0.5, lift=0.06, sink=0.03, ridge=0.025, thick=0.03, g=(0.3, 0.42), L=0.42, point=0.85), coat)
        hind = [(0.62 * sx, 1.75, 4.05), (0.76 * sx, 1.30, 3.0), (0.75 * sx, 1.48, 2.3), (0.72 * sx, 1.85, 1.75),
                (0.69 * sx, 2.2, 1.3), (0.67 * sx, 2.12, 0.72), (0.66 * sx, 2.02, 0.27)]
        add("legs", paint(limb(hind, [(0.58, 1.1), (0.53, 0.9), (0.44, 0.62), (0.34, 0.44), (0.28, 0.34), (0.235, 0.27), (0.255, 0.29)],
                               P_LEG, 22, up=(0, -1, 0.05)), leg_g(sx)), coat)
        add("legs", paint(kit.ball((0.58, 1.22, 1.3), cuts=3), leg_g(sx)), coat, M((0.72 * sx, 1.7, 3.12), rot=(-28, 0, 5 * sx)))
        # breeches: long fur down the back of the thigh
        for k, (dy, L) in enumerate(((0.0, 0.62), (0.14, 0.5))):
            add("legs", strip([(0.71 * sx, 2.38 + dy, 3.75 - 0.1 * k), (0.75 * sx, 2.4 + dy, 3.25 - 0.1 * k), (0.73 * sx, 2.28 + dy, 2.75 - 0.1 * k)],
                              (0, 0.35, -1), (0.35 * sx, 1, 0), L, 4, rows=2, depth=0.5, lift=0.08, sink=0.03, ridge=0.025, thick=0.03,
                              g=(0.16 + 0.1 * k, 0.26 + 0.1 * k), L=L, point=0.85), coat)

        # paws: a broad pad, four toes, short dark claws touching the floor
        for paw, size in ((Vector((0.61 * sx, -1.58, 0.0)), 1.08), (Vector((0.66 * sx, 1.96, 0.0)), 0.98)):
            P = M(paw, scale=size)
            add("paws", paint(rounded_box((0.58, 0.66, 0.34), n=3.0, cuts=2), 0.15), coat, P @ M((0, 0, 0.17)))
            for k, ox in enumerate((-0.22, -0.074, 0.074, 0.22)):
                dy = -0.05 if k in (1, 2) else 0.0
                add("paws", paint(kit.ball((0.2, 0.26, 0.2), cuts=1), 0.17), coat, P @ M((ox, -0.28 + dy, 0.1)))
                cl = [(ox, -0.36 + dy, 0.12), (ox, -0.43 + dy, 0.08), (ox, -0.46 + dy, 0.0)]
                add("claws", loft(cl, 3, fixed([0.045, 0.03, 0.005], P_CLAW), up=(0, -0.3, 1), g=(0.2, 1.0), tip=True),
                    claw, P, crease=50)

    # ---- tail: bushy, held low, the end lifting a little; rings of shards round a core ---------------
    tail = [(0, 2.40, 4.18), (0.0, 2.90, 3.98), (0.04, 3.30, 3.42), (0.10, 3.60, 2.74), (0.14, 3.86, 2.12),
            (0.13, 4.16, 1.70), (0.08, 4.50, 1.60), (0.02, 4.80, 1.78)]
    core_r = [0.2, 0.26, 0.31, 0.34, 0.34, 0.3, 0.22, 0.08]
    add("tail", paint(loft(tail, 18, fixed(core_r, round_shape(10)), up=(0, 0, 1)),
                      lambda v: 0.08 + 0.6 * smooth(v.normal.z, -0.1, -0.85)), coat)
    TC = Curve(tail)

    def tail_place(t0, L, count, stagger):
        def place(u, v):
            t = min(t0 + L / TC.L * v * 0.95, 1.0)
            c, T = TC.at(t), TC.tangent(t)
            X = T.cross(Vector((0, 0, 1))).normalized()
            Y = X.cross(T).normalized()
            ang = 2 * math.pi * (u + stagger) / count
            radial = X * math.cos(ang) + Y * math.sin(ang)
            rad = _cr(core_r, t * (len(core_r) - 1)) * 0.95
            return c + radial * rad, radial
        return place

    for k in range(8):
        t0 = 0.1 + 0.092 * k
        L = 0.6 + 0.035 * k
        tip = k >= 7
        def tg(u, v, k=k, tip=tip):
            ang = 2 * math.pi * (u + 0.5 * (k % 2)) / 9
            if tip:
                return 0.25 + 0.6 * v
            return 0.08 + 0.55 * smooth(math.sin(ang), 0.1, -0.9) + 0.05 * v
        add("tail", row(tail_place(t0, L, 9, 0.5 * (k % 2)), 9, closed=True, rows=2, depth=0.5, lift=0.12 + 0.012 * k,
                        sink=0.04, ridge=0.03, thick=0.035, g=tg, L=L, point=0.85), tipfur if tip else coat)
    # the tip: a brush of long shards closing over a small glowing core
    end, T = TC.at(1.0), TC.tangent(1.0)
    X = T.cross(Vector((0, 0, 1))).normalized()
    Y = X.cross(T).normalized()
    for k in range(7):
        ang = 2 * math.pi * k / 7
        rad = X * math.cos(ang) + Y * math.sin(ang)
        Lk = 0.6 if k % 2 == 0 else 0.5
        pts = [end - T * 0.2 + rad * 0.06, end + T * 0.1 + rad * 0.16, end + T * (0.6 * Lk) + rad * 0.13, end + T * Lk + rad * 0.03]
        add("tail", loft(pts, 7, blade(LOCK, 0.1, 0.04, cup=0.25), up=rad, g=(0.4, 1.0), feather=True, tip=True, root=True,
                         sharp=(0, 2)), tipfur)
    add("glow", loft([end - T * 0.05, end + T * 0.2, end + T * 0.42], 5, fixed([0.07, 0.07, 0.01], round_shape(6)),
                     up=Y, tip=True), glow)

    # ---- crystals: four small dark shards along the spine, each with a violet core showing through ----
    for idx, h, r, lean in ((6.0, 0.72, 0.15, 22), (5.2, 0.56, 0.125, 26), (4.4, 0.44, 0.105, 30), (3.65, 0.34, 0.085, 34)):
        s = skin.s_of(idx)
        p, n = skin.point(s, 90.0), skin.normal(s, 90.0)
        t = skin.at(s)[1]
        axis = (n * math.cos(math.radians(lean)) - t * math.sin(math.radians(lean))).normalized()
        F = frame(p, axis, -t)
        add("crystals", paint(crystal(h, r, lean=0.25), lambda v, h=h: 0.15 + 0.85 * max(v.co.z, 0.0) / h), crystal_mat, F, crease=25)
        add("glow", crystal(h * 0.86, r * 0.93, rot=30.0, lean=0.25), glow, F)

    # ---- head: placed in its own space, then turned as one -------------------------------------------
    skull = shell(SKULL, skull_corners, per=3, m=2, back_cap=0.05, nose_cap=0.02)
    face = Surface(skull)

    def head_g(v):
        co = v.co
        low = smooth(co.z, 0.04, -0.12)
        muzzle = smooth(co.y, -0.22, -0.45)
        return lerp(lerp(0.1, 0.3, muzzle), 0.84, low)
    add("head", paint(skull, head_g), facecoat, H, crease=40)
    add("head", paint(shell(JAW, jaw_corners, per=2, m=2, back_cap=0.04, nose_cap=0.01), 0.8), facecoat, H, crease=40)

    # the nose: a dark, angular pad over the end of the muzzle
    nose = rounded_box((0.17, 0.13, 0.11), n=4.0, cuts=2)
    for v in nose.verts:
        v.co.x *= 1.0 - 0.35 * smooth(v.co.z, 0.05, -0.05)      # narrower underneath
        v.co.y += 0.03 * smooth(v.co.z, 0.0, -0.055)            # the underside tucked back
    add("nose", nose, dark, H @ M((0, -1.045, 0.068)), crease=35)

    for sx in (-1, 1):
        # the eye: a glowing almond, slanted up towards the temple, tucked under the brow
        p, nrm = face.hit((0.8 * sx, -0.25, 0.085), (-sx, 0.0, 0.0))
        eye = [(-0.5, -0.04), (-0.28, 0.08), (0.0, 0.15), (0.28, 0.18), (0.5, 0.16), (0.3, 0.0), (0.02, -0.08), (-0.26, -0.08)]
        add("eyes", lens([(a * 0.23, b * 0.38) for a, b in eye], 0.04, rows=((0.6, 0.85), (1.0, 0.0)), centre=(0.0, 0.04)),
            glow, H @ facing(p + nrm * 0.004, nrm, Vector((0, 1, 0.05))))
        # brow: a heavy ridge from the stop back over the eye, casting it into shadow
        brow = [(0.07 * sx, -0.38, 0.19), (0.15 * sx, -0.32, 0.205), (0.235 * sx, -0.235, 0.205), (0.29 * sx, -0.12, 0.2),
                (0.31 * sx, 0.02, 0.17)]
        add("brows", paint(loft(brow, 10, fixed([(0.022, 0.018), (0.045, 0.036), (0.058, 0.044), (0.05, 0.04), (0.022, 0.018)], P_BROW),
                                up=(0.6 * sx, 0, 1)), 0.12), facecoat, H, crease=38)
        # cheekbone: a hard ridge from under the eye back towards the ear
        cheek = [(0.2 * sx, -0.34, -0.035), (0.3 * sx, -0.16, -0.025), (0.385 * sx, 0.06, -0.02), (0.36 * sx, 0.24, 0.02)]
        add("cheeks", paint(loft(cheek, 8, fixed([(0.015, 0.012), (0.04, 0.03), (0.05, 0.04), (0.02, 0.015)], P_BROW),
                                 up=(1.0 * sx, 0, 0.35)), 0.5), facecoat, H, crease=38)
        # ears: up and alert, a cupped crescent with silver fur inside
        def ear_prof(t):
            w = 0.165 * (1 - t) ** 0.9 + 0.004
            d = 0.11 * (1 - 0.7 * t) + 0.01
            return [(0, -d * 0.55), (0.6 * w, -d * 0.4), (w, d * 0.1), (0.55 * w, d * 0.25), (0, d * 0.02),
                    (-0.55 * w, d * 0.25), (-w, d * 0.1), (-0.6 * w, -d * 0.4)]
        ear = [(0.2 * sx, 0.16, 0.24), (0.25 * sx, 0.19, 0.48), (0.295 * sx, 0.21, 0.71)]
        add("ears", loft(ear, 8, ear_prof, side=(1, 0, 0), g=(0.08, 0.04), tip=True), facecoat, H, crease=40)
        for k, (ox, ln) in enumerate(((-0.045, 0.18), (0.0, 0.25), (0.045, 0.18))):
            base = Vector((0.2 * sx + ox, 0.165, 0.29))
            pts = [base, base + Vector((0.02 * sx + ox * 0.4, 0.0, ln * 0.5)), base + Vector((0.035 * sx + ox * 0.6, 0.01, ln))]
            add("ears", loft(pts, 5, blade(LOCK, 0.035, 0.02, cup=0.2), up=(0, -1, 0), g=(0.3, 0.42), feather=True, tip=True,
                             root=True, sharp=(0, 2)), coat, H)
        # cheek ruff: two rows of shards sweeping back from behind the cheekbones, framing the face
        for layer, (y0, L, out, lift) in enumerate(((-0.06, 0.5, 0.8, 0.06), (0.08, 0.66, 0.95, 0.1))):
            D = Vector((0.75 * out * sx, 1.0, -0.45)).normalized()

            def place(u, v, y0=y0, L=L, D=D, sx=sx):
                f = u / 5.0
                z = lerp(0.12, -0.36, f)
                y = y0 + 0.08 * f
                q, qn = face.hit((0.8 * sx, y, z), (-sx, 0, 0))
                o = Vector((sx, 0.15, 0.0)).normalized()
                return q + D * L * v, (qn * (1 - v) + o * v).normalized()
            add("ruff", row(place, 5, rows=3, depth=0.5, lift=lift, sink=0.03, ridge=0.025, thick=0.035,
                            g=lambda u, v: lerp(0.3, 0.8, smooth(u / 5.0, 0.2, 0.8)) + 0.05 * v, L=L, point=0.85), coat, H)

    wolf.build()
    for ob in wolf.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    wolf.withers = skin.point(skin.s_of(6.0), 90.0).z
    return wolf


def bake(wolf, texture):
    """Everything that does not glow becomes one textured mesh, Wolf_Body: the fur pattern and soft
    shading in the creases are baked into its colour image. The glowing parts are joined into one
    mesh, Wolf_GLOW, that keeps its emissive material. Roblox gets two MeshParts."""
    glow = [ob for ob in wolf.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in wolf.objects if ob not in glow], texture, name="Wolf_Body",
                            shade=0.5, soften=3, rough=0.88, uv_angle=85.0, uv_margin=0.004, pack_margin=0.003)
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = "Wolf_GLOW"
    wolf.objects = [body, g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,side,game distance:silhouette",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Wolf review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "wolf_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    wolf = build()
    print("triangles by part:", dict(sorted(wolf.tally.items(), key=lambda kv: -kv[1])))
    head = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.3, 0.05))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(wolf, samples=samples, focus=(head.x, head.y + 1.4, head.z - 1.6))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.62, -1.0, 0.12)).normalized() * 4.2, head + Vector((0, 0.35, -0.1)), 30)
        rig.cams["spine"] = review._camera("C_spine", Vector((-3.0, -2.4, 6.9)), Vector((0.0, -0.3, 4.8)), 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(wolf, os.path.abspath(a.texture))
    tris = wolf.triangles()
    lo, hi = wolf.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; withers %.2f; lowest point z=%.4f"
          % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, wolf.withers, lo.z))
    me = wolf.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(wolf.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        rig, review = rig_for(40)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            rig.sheet(os.path.abspath(a.review), shots("full") if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
