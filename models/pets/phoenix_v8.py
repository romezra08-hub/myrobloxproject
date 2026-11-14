"""Phoenix pet: a big legendary firebird, sleek, proud and fiery. Built from scratch by script.

    python models/pets/phoenix.py --review out/phoenix.png      # render the review sheet
    python models/pets/phoenix.py --export models/export/phoenix.fbx

Style: a stylised game creature, not a plush toy and not a realistic bird. Every feather is a
sharp, closed blade with a raised shaft, laid in overlapping rows. Must-haves, checked in every review:
  1. Reads as a phoenix in outline: wings raised and spread wide, a swept-back crest of flame
     plumes, a long train of tail feathers that sweeps to the ground and curls up at the ends.
  2. Big and proud: about 9 studs to the wing tips, 11 to 12 across, standing tall on strong
     golden talons, chest out, head raised and turned a little. Head in proportion, not a chick.
  3. A fierce, noble face: an angular head, a hooked golden beak, glowing almond eyes without
     pupils under a strong brow. Not cute, not goofy, not creepy.
  4. Layered blade feathers, deep crimson at the root going to orange and gold at the tip.
  5. Not plastic: streaked feather texture and soft shading in the creases baked into one image.
     Only the eyes, the crest tips, the longest wing and tail tips and the chest ember glow.

Round 8: a shorter, deeper beak with a tight hook; the crest plumes flow back low over the nape
instead of standing up like candles; the ember sits down among the breast feathers; bolder drawn
shafts and darker feather edges; the undersides of the train get a smaller share of the texture.

Round 7: a raptor head (tapering skull, a hard brow shelf over calm slanted eyes, a sharp hooked
beak running from dark at the root to gold, flame cheek feathers, a crest of seven plumes that flows
back over the nape); layered coverts on the backs of the wings over a slimmer wing arm; the breast in
staggered rows of varied flame feathers, small at the throat and larger lower down, lit gold round a
bigger ember; bolder drawn shafts and edges, and hidden surfaces (the skin under the feathers and
the undersides of the feather rows) get a smaller share of the texture.

Round 6: a crisp orange brow line along each brow ridge, bright over the dark mask and glowing eye;
flatter feathers on the forehead; slimmer crest plumes with pointed, dark roots; a larger ember.

Round 5: deeper, less pink reds (no sheen in the bake), a slightly larger head so the face reads
in game, crest plumes dark at the root, blunter feather roots (hidden under the coverts) so their
texture islands pack better, and a tighter face camera for the review.

Round 4: the train ends in one true scroll in the middle and lower flame flicks to the sides (no
more coiled-spring look); a darker amber beak with a dark hook, a dark mask through the glowing eyes
and a harder brow; flatter blades and four hackle rings (fewer, larger texture islands).

Round 3: a rounder head with a slimmer, higher beak; the crest sweeps back in S-curved flames with
thin glowing tips (not crystals); strong legs (thick scaled shanks, longer feathered trousers,
bigger talons); a fuller train of nine feathers; a wider span.

Round 2: the small feathers are laid as rows (one sheet of pointed blades per row) instead of
hundreds of loose pieces: they read as layered plumage, not a pinecone, and the texture gets
far fewer, larger islands. A longer, angular head with swept-back brow plumes and a deeper hook to
the beak; pointed wings that spread wider; the glowing tips are flame-shaped inlays, not hard cuts.
"""
import argparse
import bisect
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

SCALE = 1.0
HEAD_AT = Vector((-0.15, -1.00, 6.32))
HEAD_ROT = (-4, 4, -18)            # nose a little up, a small tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.38

# The trunk and neck are one skin over these sections, from the rump to inside the head:
# centre x, y, z, then half width, height above the centre line (the back), depth below it (the
# breast), squareness.
BODY = [
    (0.00, 1.30, 2.05, 0.34, 0.24, 0.28, 2.0),    # 0  rump, where the train grows
    (0.00, 0.88, 2.30, 0.70, 0.46, 0.60, 2.1),    # 1  hips
    (0.00, 0.30, 2.85, 0.84, 0.62, 0.92, 2.15),   # 2  belly
    (0.00, -0.22, 3.62, 0.82, 0.60, 0.95, 2.15),  # 3  breast, pushed out
    (0.00, -0.50, 4.38, 0.58, 0.46, 0.58, 2.1),   # 4  base of the neck
    (-0.03, -0.66, 5.10, 0.42, 0.36, 0.40, 2.0),  # 5  neck
    (-0.08, -0.78, 5.72, 0.34, 0.30, 0.31, 2.0),  # 6  throat
    (-0.12, -0.88, 6.12, 0.27, 0.24, 0.24, 2.0),  # 7  inside the head
]

# The head, in its own space (nose towards -Y), the same kind of sections from the back of the
# skull to the root of the beak. Long, low and squarish: sleek and angular, not a ball.
HEAD = [
    (0.0, 0.52, 0.00, 0.14, 0.12, 0.15, 2.1),     # into the neck
    (0.0, 0.38, 0.02, 0.22, 0.22, 0.25, 2.2),
    (0.0, 0.17, 0.02, 0.26, 0.235, 0.27, 2.3),    # crown
    (0.0, -0.03, 0.00, 0.25, 0.205, 0.25, 2.4),   # behind the eyes
    (0.0, -0.19, -0.02, 0.205, 0.16, 0.215, 2.5), # the eyes
    (0.0, -0.32, -0.03, 0.15, 0.12, 0.175, 2.45),
    (0.0, -0.42, -0.03, 0.11, 0.095, 0.145, 2.3), # root of the beak
]

# A wing, drawn flat: (outwards, up) in studs from the shoulder.
WING_ROOT = (0.66, 0.20, 3.90)
SWEEP, LEAN, WING_SIZE = 18.0, 14.0, 1.15
ARM = [(0.0, 0.0), (1.1, 0.7), (2.3, 1.8), (2.85, 2.3)]                     # shoulder, elbow, wrist, hand
PRIMARIES = [(62, 3.0), (52, 3.1), (43, 2.85), (35, 2.6), (27, 2.4), (19, 2.25), (11, 2.1), (3, 2.0)]   # angle, length
SECONDARIES = [(-4, 2.2), (-14, 2.2), (-24, 2.15), (-34, 2.1), (-44, 2.0), (-54, 1.9), (-64, 1.8)]
TERTIALS = [(-74, 1.7), (-84, 1.55), (-92, 1.4)]

# Width of a feather along its length, as a fraction of its half width (0 root, 1 tip).
FLIGHT = [(0, 0.0), (0.02, 0.7), (0.12, 0.9), (0.35, 1.0), (0.62, 0.95), (0.82, 0.70), (0.94, 0.36), (1, 0.0)]
FLAME = [(0, 0.0), (0.03, 0.45), (0.3, 0.65), (0.55, 0.95), (0.7, 1.0), (0.84, 0.72), (0.95, 0.3), (1, 0.0)]
TIP = [(0, 0.0), (0.3, 1.0), (0.65, 0.75), (1, 0.0)]
CREST_L = (1.25, 1.12, 0.98, 0.82)      # crest plume lengths, middle to outside
CREST = [(0, 0.0), (0.08, 0.3), (0.35, 0.7), (0.68, 1.0), (0.86, 0.62), (1, 0.0)]


# ---- helpers that the kit does not have ------------------------------------------------------------

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


def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def _layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in ("g", "xn", "d", "f")]


def hide(bm, w=1.0):
    """Mark every face of a shape as mostly hidden (under other shapes): the unwrap gives it a
    smaller share of the texture."""
    lh = bm.faces.layers.float.get("hid") or bm.faces.layers.float.new("hid")
    for f in bm.faces:
        f[lh] = w
    return bm


def paint(bm, g, feather=0.0):
    """Give every vertex of a shape the colour position g on its material's ramp."""
    lg, lx, ld, lf = _layers(bm)
    for v in bm.verts:
        v[lg] = g(v) if callable(g) else g
        v[lf] = feather
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


def loft(points, n, profile, up=None, side=None, ref=None, g=(0.0, 0.0), gpow=1.0, feather=True, sharp=(),
         tip=True, root=True, ends=None, under=0.0):
    """A closed shape lofted along a smooth curve through `points`, in n steps. profile(t) gives the
    cross-section at t (0 at the root, 1 at the tip) as (across, through) pairs. The through
    direction follows `up`, or is square to the across direction `side`; `ref` picks which way it
    faces. With tip (root) the shape closes to a point at its tip (root). Each vertex stores its
    colour position g (g[0] at the root to g[1] at the tip), how far across the blade it is (xn,
    -1 to 1), how far along it is in studs (d) and whether it is a feather (f): the plumage shader
    draws the vane from these. `ends` (t0, t1) lofts only that part of the curve."""
    C = Curve(points)
    t0, t1 = ends or (0.0, 1.0)
    bm = bmesh.new()
    lg, lx, ld, lf = _layers(bm)
    rings, sign = [], None
    for i in range(n + 1):
        t = i / n
        tc = t0 + (t1 - t0) * t
        p, T = C.at(tc), C.tangent(tc)
        if side is not None:
            s = Vector(side(t) if callable(side) else side)
            W = (s - T * s.dot(T)).normalized()
            N = W.cross(T)
        else:
            u = Vector(up(tc) if callable(up) else up)
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
            v[lg], v[lx], v[ld], v[lf] = gv, 0.0, C.L * tc, fv
            rings.append([v])
            continue
        prof = profile(t)
        wmax = max(abs(x) for x, _ in prof) or 1.0
        ring = []
        for x, y in prof:
            v = bm.verts.new(p + W * x + N * y)
            v[lg], v[lx], v[ld], v[lf] = gv, x / wmax, C.L * tc, fv
            ring.append(v)
        rings.append(ring)
    m = max(len(r) for r in rings)
    lh = bm.faces.layers.float.new("hid")
    for a, b in zip(rings, rings[1:]):
        for j in range(m):
            if len(a) == 1:
                f = bm.faces.new((a[0], b[(j + 1) % m], b[j]))
            elif len(b) == 1:
                f = bm.faces.new((a[j], a[(j + 1) % m], b[0]))
            else:
                f = bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
            if under and m == 4 and j >= 2:                             # the underside of a blade
                f[lh] = under
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


def blade(widths, W, h, cup=0.14, thin=0.35):
    """The cross-section of a feather: two sharp edges, a raised shaft on top and a keel under it,
    `W` to each side at its widest and `h` through, arched by `cup`, thinning towards the tip."""
    def prof(t):
        w = max(W * _table(widths, t), 0.004)
        hh = min(h * 0.8 * (1 - (1 - thin) * t), w * 0.25)             # no thicker than its width allows, so the ends stay flat
        c = cup * w
        return [(-w, -c), (0.0, hh), (w, -c), (0.0, -c - hh * 0.5)]
    return prof


def flame_tip(points, W, h, start=0.7, reach=0.12, n=6, up=None, side=None, ref=None):
    """A glowing flame laid over the end of a feather: it starts as a point on the shaft at `start`,
    swells to most of the feather's width and runs out past its tip by `reach` studs. It is thicker
    than the feather, so it shows on both faces."""
    C = Curve(points)
    end = C.at(1.0) + C.tangent(1.0) * reach
    pts = [C.at(start + (1 - start) * k / 4) for k in range(5)] + [end]

    def prof(t):
        w = W * _table(TIP, t)
        return [(-w, 0.0), (0.0, h), (w, 0.0), (0.0, -h)]

    if up is not None:
        f = up if callable(up) else (lambda t: up)
        return loft(pts, n, prof, up=lambda t: f(min(start + (1 - start) * t * 1.05, 1.0)), feather=False)
    return loft(pts, n, prof, side=side, ref=ref, feather=False)


def row(place, count, closed=False, cols=2, rows=3, depth=0.6, lift=0.08, sink=0.04, ridge=0.03, thick=0.03,
        g=(0.1, 0.4), gpow=1.0, L=0.6, point=1.0, under=1.0):
    """A row of pointed feathers as one closed sheet. place(u, v) gives the point and the outward
    normal of the surface the row lies on: u runs across the row (feather j spans j to j + 1), v
    from the roots (0) to the tips (1). Between two feathers the tips are cut back by `depth`, so
    each one ends in a sharp point. Each has a raised shaft (`ridge`), stands `lift` proud of the
    surface at its tip and is buried `sink` at its root, so the next row up covers its root."""
    bm = bmesh.new()
    lg, lx, ld, lf = _layers(bm)
    lh = bm.faces.layers.float.new("hid")
    ncol = count * cols + (0 if closed else 1)
    top, bot = [], []
    for c in range(ncol):
        u = c / cols
        q = 2.0 * (c % cols) / cols - 1.0                                  # -1 between feathers, 0 on a shaft
        vt = 1.0 - depth * abs(q) ** point
        tc, bc = [], []
        for r in range(rows + 1):
            v = vt * r / rows
            p, nrm = place(u, v)
            up = -sink + (lift + sink) * v ** 1.2 + ridge * (1 - abs(q)) * min(1.0, 3 * v + 0.3)
            rim = r in (0, rows) or (not closed and c in (0, ncol - 1))   # the outline: top and bottom meet in a sharp edge
            for lst, off in ((tc, up), (bc, up - thick * (0.5 + 0.5 * v))):
                if rim and lst is bc:
                    bc.append(tc[-1])
                    continue
                vert = bm.verts.new(p + nrm * off)
                vert[lg], vert[lx], vert[ld], vert[lf] = g[0] + (g[1] - g[0]) * v ** gpow, q, v * L, 1.0
                lst.append(vert)
        top.append(tc)
        bot.append(bc)
    pairs = [(c, (c + 1) % ncol) for c in range(ncol if closed else ncol - 1)]
    for c, d in pairs:
        for r in range(rows):
            bm.faces.new((top[c][r], top[d][r], top[d][r + 1], top[c][r + 1]))
            bm.faces.new((bot[c][r + 1], bot[d][r + 1], bot[d][r], bot[c][r]))[lh] = under      # the underside is hidden
        bm.edges.get((top[c][rows], top[d][rows])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def flame_row(skin, s0, lo, hi, W_of, L_of, rnd, stagger=0.0, closed=False, jitter=0.3, tilt=11.0, bow=0.0, **kw):
    """A row of flame feathers side by side round the skin at s0, from angle lo to hi (a whole ring
    when `closed`), pointing towards the rump. Each is about 2 * W_of(th) studs wide and L_of(th)
    long, but every one gets its own width, length and a slant that grows towards its tip, like a
    flickering flame, so that the rows overlap like plumage and never line up into a lattice. With
    `bow` the row rises that far towards the head at the sides, so the rows make chevrons down the
    breast. Four columns a feather (a shaft down the middle), 32 triangles each."""
    steps = max(int(hi - lo), 8)
    cum = [0.0]
    for i in range(steps):
        th = lo + (hi - lo) * (i + 0.5) / steps
        per = (skin.bare(s0, th + 0.5) - skin.bare(s0, th - 0.5)).length * (hi - lo) / steps
        cum.append(cum[-1] + per / (2.0 * W_of(th)))
    count = max(2, round(cum[-1]))

    def angle_at(x):
        x = min(max(x * cum[-1] / count, 0.0), cum[-1])
        i = min(bisect.bisect_right(cum, x) - 1, steps - 1)
        f = (x - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
        return lo + (hi - lo) * (i + f) / steps
    if closed:
        B = [angle_at(j + stagger + rnd.uniform(-jitter, jitter)) for j in range(count)]
        B.append(B[0] + 360.0)
    else:
        B = [lo] + [angle_at(j + stagger + rnd.uniform(-jitter, jitter)) for j in range(1, count)] + [hi]
    n = len(B) - 1
    Ls = [L_of(0.5 * (B[j] + B[j + 1])) * rnd.uniform(0.8, 1.2) for j in range(n)]
    Ts = [rnd.uniform(-tilt, tilt) for j in range(n)]
    cache = {}

    def place(u, v):
        key = round(u * 8)
        if key not in cache:
            j, f = int(u), u - int(u)
            if j >= n:
                j, f = n - 1, 1.0
            th = B[j] + f * (B[j + 1] - B[j])
            if f < 1e-6 or f > 1 - 1e-6:                      # a column two feathers share
                i0, i1 = (j - 1, j) if f < 0.5 else (j, j + 1)
                i0, i1 = (i0 % n, i1 % n) if closed else (max(i0, 0), min(i1, n - 1))
                L, tl = 0.5 * (Ls[i0] + Ls[i1]), 0.5 * (Ts[i0] + Ts[i1])
            else:
                L, tl = Ls[j], Ts[j]
            r0 = min(s0 + bow * (1.0 - abs(math.sin(math.radians(th)))), skin.L)
            cache[key] = (th, tl, r0, skin.toward(r0, th, L))
        th, tl, r0, s1 = cache[key]
        s = r0 + (s1 - r0) * v
        a = th + tl * v ** 1.6
        return skin.bare(s, a), skin.normal(s, a)
    kw.setdefault("L", sum(Ls) / n)
    return row(place, n, closed=closed, cols=4, **kw)


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


def seat(p, normal, up=(0, 0, 1)):
    """A transform that seats a shape at p on a surface: its front (-Y) looks out along `normal`
    and its top is as near `up` as it can be."""
    y = -Vector(normal).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(p)
    return m


class Skin:
    """A smooth skin over sections along a path. Positions on it are (s, angle): s is the distance
    along the path from its first section, the angle goes round the section in degrees, 90 on the
    back (or the top of the head), -90 underneath, 0 on the +X side."""

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
        start (sgn -1) or the end (sgn 1)."""
        p0, s1 = self.bare(s0, th), s0 + sgn * dist
        for _ in range(3):
            d = (self.bare(min(max(s1, 0.0), self.L), th) - p0).length
            s1 = s0 + (s1 - s0) * dist / max(d, 1e-6)
        return min(max(s1, 0.0), self.L)

    def mesh(self, segs=20, k=0.42, lo=0.13, hi=0.42):
        ss, s = [0.0], 0.0
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            ss.append(s)
        ss.append(self.L)
        bm = bmesh.new()
        loops = [[bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)] for s in ss]
        for a, b in zip(loops, loops[1:]):
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
        for ring, s in ((loops[0], 0.0), (loops[-1], self.L)):
            c = bm.verts.new(self.at(s)[0])
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm


BREAST_L, BREAST_W = (0.3, 0.55), (0.1, 0.15)   # feather length and half width at the throat, and added lower down
BREAST_STEP, BREAST_BOW = 0.58, 0.35
EMBER_AT, EMBER_SIZE, EMBER_OUT = 2.75, 0.95, 0.0      # where on the breast (a section index), how big, how proud
EMBER_REACH, EMBER_WARM = 0.95, 0.6                    # how far the ember lights the feathers round it, and how much

EYE_Y = -0.2
EYE_TH, BROW_TH = 10.0, 36.0          # where round the head the eyes and the brow ridges sit (degrees up from the side)


class HeadSkin(Skin):
    """The head's skin, with a hard brow ridge over each eye and a socket under it for the eye."""

    def s_at(self, y):
        """The s of the head skin at the depth y (the head runs straight along -Y)."""
        return min(max(HEAD[0][1] - y, 0.0), self.L)

    def bare(self, s, th):
        p = Skin.bare(self, s, th)
        c = self.at(s)[0]
        y = HEAD[0][1] - s
        th = th % 360.0

        def near(a):
            return min(abs(th - a), abs(th - (180.0 - a)))
        ridge = _table([(-0.44, 0.0), (-0.36, 0.04), (-0.24, 0.07), (-0.04, 0.06), (0.14, 0.02), (0.3, 0.0)], y)
        socket = _table([(-0.34, 0.0), (-0.22, 0.05), (-0.1, 0.045), (0.04, 0.0)], y)
        bump = ridge * math.exp(-(near(BROW_TH) / 11.0) ** 2) - socket * math.exp(-(near(EYE_TH - 4.0) / 13.0) ** 2)
        return p + (p - c).normalized() * bump


# ---- materials --------------------------------------------------------------------------------------

def ramp_material(name, stops, rough, streak):
    """A material whose colour runs along a ramp, read from each vertex's colour position g, with
    kit.furry's short streaks over it so it is not flat plastic."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **streak)
    tree = m.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    attr = new("ShaderNodeAttribute")
    attr.attribute_name = "g"
    ramp = new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
    for pos, hexcode in stops[1:-1]:
        e = els.new(pos)
        e.color = (*kit.srgb(hexcode), 1.0)
    link(attr.outputs["Fac"], ramp.inputs["Fac"])
    link(ramp.outputs["Color"], hsv.inputs["Color"])
    return m, hsv


def vane(mat, hsv, period=0.2, slant=0.22, shaft=0.17, barb=0.12, pale=0.8, rim=(0.45, 0.42)):
    """Draw a feather on every feather blade: a pale shaft down the middle and fine barbs that
    sweep out from it towards the tip, both read from the vertex values that loft() stores."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new

    def attr(name):
        a = new("ShaderNodeAttribute")
        a.attribute_name = name
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

    ax = op('ABSOLUTE', attr("xn"))
    f = attr("f")
    phase = op('MULTIPLY_ADD', ax, -slant, attr("d"))                     # d - slant |x|
    wave = op('SINE', op('MULTIPLY', phase, 2 * math.pi / period))
    barbs = op('MULTIPLY_ADD', wave, barb, 1.0)                           # 1 - barb .. 1 + barb
    rmp = new("ShaderNodeMapRange")                                       # 1 on the shaft, 0 off it
    rmp.inputs["From Min"].default_value, rmp.inputs["From Max"].default_value = shaft, 0.0
    link(ax, rmp.inputs["Value"])
    lit = op('MULTIPLY_ADD', rmp.outputs["Result"], pale, barbs)          # the shaft is paler
    edge = new("ShaderNodeMapRange")                                      # darker towards the edges
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = rim[0], 1.0
    edge.inputs["To Min"].default_value, edge.inputs["To Max"].default_value = 1.0, rim[1]
    link(ax, edge.inputs["Value"])
    pattern = op('MULTIPLY', lit, edge.outputs["Result"])
    mixed = op('MULTIPLY_ADD', op('SUBTRACT', pattern, 1.0), f, 1.0)      # only where f is 1
    old = hsv.inputs["Value"].links[0].from_socket
    link(op('MULTIPLY', old, mixed), hsv.inputs["Value"])


# ---- the phoenix -------------------------------------------------------------------------------------

def build():
    # Four materials. The plumage runs from deep crimson at a feather's root through orange to gold
    # at its tip (a ramp read from each vertex), with short streaks and a drawn vane on top.
    plum, plum_hsv = ramp_material("Plumage", [(0.0, "#2E040C"), (0.18, "#720A16"), (0.38, "#AE1214"), (0.58, "#E44A12"),
                                               (0.78, "#FF8E1A"), (1.0, "#FFD050")], 0.8,
                                   dict(strength=0.14, mottle=0.10, fine=34.0, length=5.0))
    vane(plum, plum_hsv)
    beak_m, _ = ramp_material("Beak", [(0.0, "#1E0A08"), (0.22, "#4A1A0C"), (0.5, "#B8661A"), (0.78, "#FFBE40"), (1.0, "#FFE48C")], 0.5,
                              dict(strength=0.08, mottle=0.06, fine=70.0, length=3.0))
    talon, _ = ramp_material("Talon", [(0.0, "#FFD060"), (0.45, "#E8A030"), (0.8, "#5A2A10"), (1.0, "#1C0C08")], 0.6,
                             dict(strength=0.12, mottle=0.08, fine=40.0, length=2.0))
    glow = kit.material("GLOW_Flame", "#FFB020", rough=0.5, emit=4.0)
    ph = Prop("Phoenix")
    ph.tally = {}

    def add(part, bm, mat, at=None):
        ph.tally[part] = ph.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        ph.add(bm, mat, at)

    # ---- trunk and neck: one smooth skin, then rows of blade feathers over it ------------------------
    skin = Skin(BODY)
    add("skin", hide(paint(skin.mesh(segs=14), 0.12)), plum)

    def ring_of(s0, count, L_of, stagger=0.0):
        """place() for a ring of feathers right round the skin from s0 towards the rump."""
        dth = 360.0 / count
        cache = {}

        def place(u, v):
            th = 90.0 + (u - 0.5 + stagger) * dth
            if th not in cache:
                cache[th] = skin.toward(s0, th, L_of(th))
            s = s0 + (cache[th] - s0) * v
            return skin.bare(s, th), skin.normal(s, th)
        return place

    def front(th):
        return max(0.0, -math.sin(math.radians(th)))                    # 1 on the breast, 0 on the back

    ember_s = skin.s_of(EMBER_AT)
    ember_at, ember_n = skin.point(ember_s, -90.0), skin.normal(ember_s, -90.0)

    def warmed(bm, reach=EMBER_REACH, k=EMBER_WARM):
        """Feathers near the ember take on its light: their colour runs further up the ramp, to gold."""
        lg = bm.verts.layers.float.get("g")
        for v in bm.verts:
            d = (v.co - ember_at).length
            w = min(max((reach - d) / (reach * 0.6), 0.0), 1.0) ** 1.4
            v[lg] = v[lg] + (0.97 - v[lg]) * k * w
        return bm

    def arc_of(s0, lo, hi, count, L_of, stagger=0.0):
        """place() for a row of `count` feathers from angle lo to hi round the skin at s0."""
        cache = {}

        def place(u, v):
            th = lo + (hi - lo) * (u + stagger) / count
            if th not in cache:
                cache[th] = skin.toward(s0, th, L_of(th))
            s = s0 + (cache[th] - s0) * v
            return skin.bare(s, th), skin.normal(s, th)
        return place

    rnd = random.Random(11)
    # the back and the tops of the flanks: rows of broad blades, deep crimson to ember
    s, k = skin.s_of(4.0), 0
    while s > skin.s_of(0.85):
        L_of = lambda th: 0.7 + 0.08 * math.sin(math.radians(th) * 3 + k)
        add("back feathers", row(arc_of(s, -24.0, 204.0, 8, L_of, 0.5 * (k % 2) - 0.25), 8, rows=2, depth=0.6,
                                 lift=0.05, sink=0.05, ridge=0.04, thick=0.03, g=(0.05, 0.46), L=0.75, point=0.9), plum)
        s -= 0.37
        k += 1
    # throat and breast: flame feathers, small under the beak and larger lower down, in staggered,
    # jittered rows that bow up at the sides
    s_top, s_bot = skin.s_of(6.45), skin.s_of(1.0)
    s, k = s_top, 0
    while s > s_bot:
        t = min((s_top - s) / (s_top - s_bot), 1.0)
        L, W = BREAST_L[0] + BREAST_L[1] * t, BREAST_W[0] + BREAST_W[1] * t
        lo, hi = (-160.0, -20.0) if s > skin.s_of(4.1) else (-202.0, 22.0)
        add("breast", warmed(flame_row(skin, s, lo, hi, lambda th, W=W: W, lambda th, L=L: L, rnd, stagger=0.5 * (k % 2),
                                       bow=BREAST_BOW * L, rows=2, depth=0.42, point=1.35, lift=0.035 + 0.02 * t, sink=0.05,
                                       ridge=0.03, thick=0.025, g=(0.04, 0.5 + 0.06 * (k % 3)), gpow=1.2)), plum)
        s = skin.toward(s, -90.0, BREAST_STEP * L)
        k += 1
    # neck hackles over the back and sides of the neck: longer, narrower feathers that flare like a mane of flame
    for i, idx in enumerate((6.55, 5.75, 4.95, 4.15)):
        s = skin.s_of(idx)
        L = 0.7 + 0.11 * i
        add("hackles", row(arc_of(s, -22.0 - 6 * i, 202.0 + 6 * i, 8, lambda th, L=L: L, 0.5 * (i % 2) - 0.25), 8, rows=3,
                           depth=0.78, lift=0.11 + 0.03 * i, sink=0.05, ridge=0.04, thick=0.035, g=(0.16, 0.66), gpow=1.3, L=L,
                           point=0.8), plum)
    # the ember at the heart of the breast: a flame-shaped coal set in among the feathers
    flame = [(0.0, 1.0), (0.1, 0.62), (0.2, 0.3), (0.24, 0.0), (0.17, -0.24), (0.0, -0.36), (-0.17, -0.24), (-0.24, 0.0),
             (-0.2, 0.3), (-0.1, 0.62)]
    add("glow", lens([(a * EMBER_SIZE, b * EMBER_SIZE) for a, b in flame], 0.2, centre=(0.0, 0.1)), glow,
        seat(ember_at + ember_n * EMBER_OUT, ember_n, up=skin.at(ember_s)[1]))

    # ---- legs: feathered thighs, golden scaled shanks, big taloned feet ------------------------------
    for sx in (-1, 1):
        thigh = [Vector((0.44 * sx, 0.44, 2.30)), Vector((0.50 * sx, 0.30, 1.75)), Vector((0.54 * sx, 0.16, 1.22))]
        add("legs", hide(paint(tube(thigh, [0.40, 0.34, 0.25], segs=12, rings=6), 0.14)), plum)
        for rown, (u0, L) in enumerate(((0.15, 0.55), (0.5, 0.6), (0.85, 0.6))):

            def place(u, v, u0=u0, L=L):
                ang = 2 * math.pi * (u + 0.5 * rown) / 8
                radial = Vector((math.cos(ang), math.sin(ang), 0.0))
                c = _cr(thigh, min(2.0, (u0 + 0.45 * v) * 2))
                rad = 0.40 + (0.25 - 0.40) * min(1.0, u0 + 0.45 * v)
                return c + radial * rad, (radial + Vector((0, 0, -0.25))).normalized()

            add("thigh feathers", row(place, 8, closed=True, rows=2, depth=0.6, lift=0.06, sink=0.03, ridge=0.03,
                                      thick=0.03, g=(0.10, 0.40), L=L), plum)
        shank = [Vector((0.54 * sx, 0.16, 1.32)), Vector((0.555 * sx, 0.06, 0.78)), Vector((0.57 * sx, -0.02, 0.24))]
        add("legs", paint(tube(shank, [0.23, 0.2, 0.21], segs=10, rings=6), 0.25), talon)
        for k in range(5):                                              # scutes down the front of the shank
            z = 0.42 + 0.16 * k
            c = _cr(shank, (1.32 - z) / (1.32 - 0.24) * 2)
            plate = [(math.cos(math.pi * j / 5) * 0.2, -0.05 + 0.13 * math.sin(math.pi * j / 5)) for j in range(6)] + [(-0.12, -0.09), (0.12, -0.09)]
            add("legs", paint(lens(plate, 0.07, rows=((1.0, 0.0),)), 0.12 + 0.03 * k), talon, seat(c + Vector((0, -0.19, 0.0)), (0, -1, 0.15)))
        foot = Vector((0.57 * sx, -0.04, 0.0))
        add("feet", paint(grounded(ball((0.5, 0.5, 0.32), cuts=2), M(foot + Vector((0, 0, 0.15)))), 0.25), talon)
        for yaw, size in ((-32 + 8 * sx, 1.05), (8 * sx, 1.2), (32 + 8 * sx, 1.05), (180, 0.65)):
            F = M(foot, rot=(0, 0, yaw), scale=(1.0, size, 1.0))
            toe = [(0, 0, 0.15), (0, -0.28, 0.155), (0, -0.55, 0.125), (0, -0.72, 0.1)]
            add("feet", paint(grounded(tube(toe, [0.15, 0.135, 0.115, 0.095], segs=6, rings=4), F), 0.3), talon)
            claw = [(0, -0.68, 0.12), (0, -0.88, 0.15), (0, -1.02, 0.08), (0, -1.08, 0.0)]
            add("claws", paint(grounded(tube(claw, [0.09, 0.07, 0.04, 0.01], segs=6, rings=4), F), 1.0), talon)

    # ---- wings: raised high and spread wide ---------------------------------------------------------
    for sx in (-1, 1):
        A = Vector((sx * math.cos(math.radians(SWEEP)), math.sin(math.radians(SWEEP)), 0.0))
        B = Vector((0.0, math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))))
        B = (B - A * B.dot(A)).normalized()
        F = A.cross(B)
        F = F if F.y < 0 else -F                                          # the front face of the wing
        R = Vector((WING_ROOT[0] * sx, WING_ROOT[1], WING_ROOT[2]))

        def P(a, b, c=0.0, R=R, A=A, B=B, F=F):
            """A point of the wing: `a` out and `b` up in the flat drawing, `c` in front of it; the
            wing is cupped so that its outer half sweeps back."""
            return R + (A * a + B * b) * WING_SIZE + F * (c - 0.03 * a * a)

        def Nw(a, b, P=P, F=F):
            n = (P(a + 0.05, b) - P(a - 0.05, b)).cross(P(a, b + 0.05) - P(a, b - 0.05)).normalized()
            return n if n.dot(F) > 0 else -n

        def flight(a0, b0, phi, L, W, c0, g, widths=FLIGHT, n=9, bend=-0.07, curl=0.10, h=0.05, glowing=False):
            d = Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi))))
            q = Vector((-d.y, d.x))
            ss = (0.0, 1 / 3, 2 / 3, 1.0)
            flat = [Vector((a0, b0)) + d * L * s + q * bend * L * s * s for s in ss]
            pts = [P(f.x, f.y, c0 - curl * L * s ** 2.5) for f, s in zip(flat, ss)]
            up = lambda t: Nw(*(Vector((a0, b0)) + d * L * t))
            add("flight feathers", loft(pts, n, blade(widths, W, h), up=up, g=g, sharp=(0, 2)), plum)
            if glowing:
                add("glow", flame_tip(pts, W * 0.78, h * 0.75, start=0.64, reach=0.2 * L / 3, up=up), glow)

        S, E, Wr, Hd = (Vector(p) for p in ARM)
        for i, (phi, L) in enumerate(PRIMARIES):
            r = Hd.lerp(Wr, i / (len(PRIMARIES) - 1))
            flight(r.x, r.y, phi, L, 0.27, -0.025 * i, (0.28, 0.97), n=10, glowing=i <= 5)
        for j, (phi, L) in enumerate(SECONDARIES):
            r = Wr.lerp(E, (j + 0.4) / len(SECONDARIES))
            flight(r.x, r.y, phi, L, 0.28, -0.19 + 0.02 * j, (0.22, 0.88), n=8)
        for j, (phi, L) in enumerate(TERTIALS):
            r = E.lerp(S, 0.15 + 0.3 * j)
            flight(r.x, r.y, phi, L, 0.26, -0.05 + 0.02 * j, (0.18, 0.72), n=7)

        def arm_row(line, phis, lengths, c0, count, lift, g, depth=0.55, rows=2):
            """place() for a row of coverts whose roots run along `line` (points of the drawing),
            pointing at the angles `phis` and as long as `lengths` (tables over 0..1 along the row).
            A negative c0 puts the row on the back of the wing."""
            curve = Curve([Vector((p.x, p.y, 0.0)) for p in line])
            back = -1.0 if c0 < 0 else 1.0

            def place(u, v):
                f = u / count
                root = curve.at(f)
                phi = math.radians(_table(phis, f))
                ab = Vector((root.x, root.y)) + Vector((math.cos(phi), math.sin(phi))) * _table(lengths, f) * v
                return P(ab.x, ab.y, c0), Nw(ab.x, ab.y) * back
            return row(place, count, rows=rows, depth=depth, lift=lift, sink=0.0, ridge=0.04, thick=0.035, g=g,
                       L=_table(lengths, 0.5))

        pc = [(i / 7, PRIMARIES[i][0]) for i in range(8)]
        add("coverts", arm_row([Hd + Vector((0.05, 0.08)), Wr + Vector((0.0, 0.08))], pc,
                               [(0, 1.2), (0.5, 1.15), (1, 0.95)], 0.07, 8, 0.05, (0.20, 0.62)), plum)
        sc = [(0, -6), (0.5, -32), (1, -62)]
        add("coverts", arm_row([Wr + Vector((-0.02, 0.10)), E + Vector((0.05, 0.12))], sc,
                               [(0, 1.0), (1, 0.9)], 0.07, 7, 0.05, (0.18, 0.58)), plum)
        mc = [(0, -78), (0.45, -50), (1, -18)]
        add("coverts", arm_row([S + Vector((0.1, 0.25)), E + Vector((0.02, 0.32)), Wr + Vector((-0.02, 0.32))], mc,
                               [(0, 0.8), (1, 0.75)], 0.17, 9, 0.05, (0.14, 0.48)), plum)
        lc = [(0, -70), (0.3, -40), (0.7, -5), (1, 20)]
        add("coverts", arm_row([S + Vector((0.15, 0.42)), E + Vector((0.0, 0.52)), Wr + Vector((-0.08, 0.5)), Hd + Vector((-0.02, 0.3))], lc,
                               [(0, 0.55), (1, 0.5)], 0.24, 11, 0.04, (0.10, 0.36), rows=2), plum)
        # the back of the wing: the same rows again, deep crimson at the root to ember at the tip
        add("back coverts", arm_row([Hd + Vector((0.05, 0.1)), Wr + Vector((0.0, 0.1))], pc,
                                    [(0, 1.2), (0.5, 1.12), (1, 0.95)], -0.22, 8, 0.05, (0.08, 0.6)), plum)
        add("back coverts", arm_row([Wr + Vector((-0.02, 0.12)), E + Vector((0.05, 0.14))], sc,
                                    [(0, 1.0), (1, 0.9)], -0.22, 7, 0.05, (0.08, 0.58)), plum)
        add("back coverts", arm_row([S + Vector((0.1, 0.27)), E + Vector((0.02, 0.34)), Wr + Vector((-0.02, 0.34))], mc,
                                    [(0, 0.8), (1, 0.75)], -0.27, 9, 0.05, (0.06, 0.5)), plum)
        add("back coverts", arm_row([S + Vector((0.15, 0.44)), E + Vector((0.0, 0.54)), Wr + Vector((-0.08, 0.52)), Hd + Vector((-0.02, 0.32))],
                                    lc, [(0, 0.55), (1, 0.5)], -0.31, 11, 0.04, (0.05, 0.42)), plum)
        arm = [S, E, Wr, Hd]
        add("wing arms", hide(paint(tube([P(p.x, p.y, 0.0) for p in arm], [0.17, 0.12, 0.09, 0.06], segs=8, rings=10), 0.22), 0.6), plum)

    # ---- the train: long flame feathers that sweep to the ground and curl up at the ends ---------------
    root = Vector((0.0, 1.15, 2.12))
    sweep = [(0, 0, 0), (0, 1.0, -0.8), (0, 2.3, -1.85), (0, 3.5, -2.12), (0, 4.6, -2.1)]
    ends = [[(0, 5.6, -1.75), (0, 6.25, -1.0), (0, 6.35, -0.2), (0, 5.95, 0.2), (0, 5.6, -0.05)],   # the middle: a full scroll
            [(0, 5.5, -1.85), (0, 6.15, -1.3), (0, 6.45, -0.6), (0, 6.35, -0.15)],                 # rising flames
            [(0, 5.35, -2.0), (0, 6.0, -1.72), (0, 6.38, -1.22)],
            [(0, 5.1, -2.08), (0, 5.7, -1.96), (0, 6.12, -1.7)]]                                   # low flicks at the sides
    for i in (-3, 3, -2, 2, -1, 1, 0):                                  # outer ones first, the middle on top
        a = abs(i)
        yaw = 12.5 * i
        shrink = 1.0 - 0.06 * a
        lift = 0.035 * (3 - a)
        pts = []
        for k, (x, y, z) in enumerate(sweep + ends[a]):
            p = Vector((x, y * shrink, z))
            if k >= 3:
                p.z += lift
                p.x += 0.13 * i * (k - 2) ** 0.8                           # the ends flare outwards
            p = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ p
            pts.append(root + Vector((0.07 * i, 0, 0)) + p)
        sidev = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((1, 0, 0))
        W = 0.42 - 0.025 * a
        add("train", grounded(loft(pts, 24 - 2 * a, blade(FLAME, W, 0.06, cup=0.12), side=sidev, ref=(0, 0, 1),
                                   g=(0.16, 0.98), gpow=0.8, sharp=(0, 2), under=0.7)), plum)
        add("glow", grounded(flame_tip(pts, W * 0.78, 0.04, start=0.8, reach=0.2, side=sidev, ref=(0, 0, 1))), glow)
    for i in (-2, 2, -1, 1):                                            # shorter feathers over the root of the train
        yaw = 15.0 * i
        pts = [root + Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector(p) for p in
               ((0, -0.1, 0.12), (0, 0.9, -0.42), (0, 1.9, -1.15), (0, 2.75, -1.7), (0, 3.3, -1.95))]
        sidev = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((1, 0, 0))
        add("train", loft(pts, 12, blade(FLAME, 0.30, 0.05, cup=0.12), side=sidev, ref=(0, 0, 1), g=(0.14, 0.85), sharp=(0, 2), under=1.0), plum)

    def fan(u, v):                                                      # coverts fanned over the root of the train
        yaw = math.radians(-50 + 100 * u / 7)
        d = Vector((math.sin(yaw), math.cos(yaw), 0.0))
        p = root + Vector((0, -0.4, 0.34)) + d * 1.3 * v + Vector((0, 0, -0.55 * v * v))
        n = Vector((0, -0.25, 1)) + d * 0.5 * v
        return p, n.normalized()
    add("train", row(fan, 7, rows=3, depth=0.6, lift=0.05, sink=0.0, ridge=0.04, thick=0.04, g=(0.10, 0.45), L=1.3), plum)

    # ---- head: placed in its own space, then turned as one ---------------------------------------------
    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    hs = HeadSkin(HEAD, samples=16)
    hs_at = hs.s_at

    def mask(v):
        """Colour position on the head: crimson, with a dark mask through the eyes that sweeps back."""
        x, y, z = v.co
        th = math.degrees(math.atan2(z - hs.at(hs_at(y))[0].z, abs(x)))
        centre = EYE_TH - 2.0 - 40.0 * max(y + 0.17, 0.0)
        half = 17.0 * (max(0.0, 1 - (y + 0.17) / 0.62) ** 1.1 if y > -0.17 else max(0.0, 1 - (-0.17 - y) / 0.24))
        m = min(max((half + 4.0 - abs(th - centre)) / 6.0, 0.0), 1.0) if x * 0 == 0 else 0.0
        return 0.30 - 0.27 * m
    add("head", paint(hs.mesh(segs=32, k=0.3, lo=0.045, hi=0.09), mask), plum, H)

    def side(th, sx):
        """The angle th (measured on the +X side) mirrored onto the side sx."""
        return th if sx > 0 else 180.0 - th

    # the beak: short, deep and sharply hooked, over a smaller lower bill
    def bill(t):
        w = 0.105 * (1 - t) ** 0.55 + 0.004
        hh = 0.2 * (1 - 0.9 * t) + 0.006
        return [(0.0, hh * 0.66), (0.4 * w, hh * 0.46), (w, 0.0), (0.8 * w, -hh * 0.38), (0.0, -hh * 0.3),
                (-0.8 * w, -hh * 0.38), (-w, 0.0), (-0.4 * w, hh * 0.46)]

    upper = [(0, -0.33, 0.04), (0, -0.45, 0.045), (0, -0.55, 0.02), (0, -0.62, -0.035), (0, -0.655, -0.11), (0, -0.645, -0.19),
             (0, -0.6, -0.245)]
    add("beak", loft(upper, 16, bill, side=(1, 0, 0), ref=(0, 0, 1), g=(0.0, 1.0), gpow=0.8, feather=False, root=False,
                     sharp=(0, 2, 6)), beak_m, H)

    def jaw(t):
        w = 0.085 * (1 - t) ** 0.6 + 0.01
        hh = 0.065 * (1 - 0.6 * t) + 0.008
        return [(0.0, hh * 0.3), (w, 0.0), (0.6 * w, -hh * 0.6), (-0.6 * w, -hh * 0.6), (-w, 0.0)]

    lower = [(0, -0.32, -0.1), (0, -0.44, -0.13), (0, -0.53, -0.14)]
    add("beak", loft(lower, 6, jaw, side=(1, 0, 0), ref=(0, 0, 1), g=(0.0, 0.45), feather=False, root=False, sharp=(1, 4)), beak_m, H)

    for sx in (-1, 1):
        # the eye: a big glowing almond deep under the brow ridge, the back corner higher than the front
        s_eye, th_eye = hs_at(EYE_Y), side(EYE_TH, sx)
        p, nrm = hs.point(s_eye, th_eye), hs.normal(s_eye, th_eye)
        look = (nrm + Vector((0, -0.5, 0.0))).normalized()
        outline = []
        for k in range(16):                                             # a calm almond: flat lid, fuller underside
            ang = 2 * math.pi * k / 16
            a = math.cos(ang)
            b = math.sin(ang) * (0.26 if math.sin(ang) > 0 else 0.55) * (1 - a * a) ** 0.25
            outline.append((a * 0.165, b * 0.16 + sx * 0.045 * a))
        add("glow", lens(outline, 0.07), glow, H @ seat(p - nrm * 0.016, look))

        # the brow: a hard shelf from the root of the beak back over the eye, its lip overhanging the eye
        th_b = side(BROW_TH, sx)
        ys = (-0.41, -0.32, -0.21, -0.09, 0.03, 0.13)
        lifts = [(-0.41, -0.01), (-0.3, 0.005), (-0.1, 0.012), (0.13, -0.01)]
        pts = [hs.point(hs_at(y), th_b, _table(lifts, y)) for y in ys]

        def shelf(t, sx=sx):
            w = 0.085 * _table([(0, 0.3), (0.25, 0.95), (0.6, 1.0), (1, 0.35)], t)
            h = 0.06 * _table([(0, 0.35), (0.3, 1.0), (0.7, 0.9), (1, 0.25)], t)
            return [(-0.85 * w * sx, -0.012), (-0.25 * w * sx, h), (w * sx, h * 0.35), (0.55 * w * sx, -h * 0.35)]
        add("brows", loft(pts, 10, shelf, up=lambda t, th_b=th_b: hs.normal(hs_at(-0.41 + 0.54 * t), th_b), g=(0.5, 0.66),
                          feather=False, sharp=(1, 2)), plum, H)

        # the brow runs back past the skull as a swept flame plume
        r0 = hs.point(hs_at(0.1), side(BROW_TH - 4.0, sx), -0.02)
        n0 = hs.normal(hs_at(0.1), side(BROW_TH - 4.0, sx))
        pts = [r0, r0 + Vector((0.06 * sx, 0.35, 0.02)) + n0 * 0.05, r0 + Vector((0.16 * sx, 0.75, 0.1)), r0 + Vector((0.24 * sx, 1.05, 0.26)),
               r0 + Vector((0.26 * sx, 1.2, 0.42))]
        add("brows", loft(pts, 9, blade(FLAME, 0.095, 0.05, cup=0.1), up=n0 + Vector((0, 0, 0.6)), g=(0.4, 0.9), sharp=(0, 2)), plum, H)

        # flame feathers over each cheek, swept back below and behind the eye, their tips flaring out
        def cheek(u, v, sx=sx):
            th = side(-38.0 + 10.0 * u, sx)
            s = hs_at(-0.12) - (0.62 - 0.07 * abs(u - 2.5)) * v
            return hs.bare(s, th), hs.normal(s, th)
        add("cheeks", row(cheek, 5, rows=3, depth=0.62, lift=0.075, sink=0.02, ridge=0.025, thick=0.025, g=(0.1, 0.72), gpow=1.3,
                          L=0.6, point=0.85), plum, H)

    def forehead(u, v):                                                 # a cap of small feathers swept back from the beak
        th = 90.0 - 30.0 + 15.0 * u
        s = hs_at(-0.38) - 0.36 * v
        return hs.bare(s, th), hs.normal(s, th)
    add("cheeks", row(forehead, 4, rows=2, depth=0.45, lift=0.015, sink=0.02, ridge=0.012, thick=0.018, g=(0.24, 0.46), L=0.5), plum, H)

    # the crest: five flame plumes swept back from the crown in S-curves, fanned out, their tips glowing
    for k in (-3, 3, -2, 2, -1, 1, 0):
        a = abs(k)
        L = CREST_L[a]
        r0 = Vector((0.055 * k, -0.2 + 0.1 * a, 0.2 - 0.025 * a))
        pts = [r0 + Vector(d) * L for d in ((0, 0, 0), (0.05 * k, 0.3, 0.17), (0.1 * k, 0.72, 0.21), (0.16 * k, 1.12, 0.2),
                                            (0.21 * k, 1.46, 0.28), (0.24 * k, 1.66, 0.46))]
        tilt = math.radians(24 * a)
        upv = Vector((math.copysign(math.cos(tilt), k or 1), 0.0, math.sin(tilt)))
        W = 0.16 - 0.012 * a
        add("crest", loft(pts, 13, blade(CREST, W, 0.045, cup=0.1), up=upv, g=(0.14, 0.92), gpow=1.3, sharp=(0, 2)), plum, H)
        add("glow", flame_tip(pts, W * 0.8, 0.026, start=0.68, reach=0.1, up=upv), glow, H)

    ph.build(SCALE)
    return ph


UV_ANGLE, UV_MARGIN, PACK_MARGIN = 85.0, 0.004, 0.003
HIDDEN_SHARE = 0.3            # a hidden surface gets this much of the texture size a seen one gets (in each direction)


def weigh_islands(ob, keep=HIDDEN_SHARE):
    """In edit mode, after the unwrap: shrink every texture island that is mostly hidden (marked by
    the face value "hid") about its centre, so that the packing gives the seen surfaces more pixels."""
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    lh = bm.faces.layers.float.get("hid")
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
        w = sum(f[lh] * f.calc_area() for f in faces) / area if lh else 0.0
        if w <= 0.01:
            continue
        k = 1.0 - (1.0 - keep) * w
        loops = [l for f in faces for l in f.loops]
        c = sum((l[uvl].uv for l in loops), Vector((0.0, 0.0))) / len(loops)
        for l in loops:
            l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(me)
    return islands


def bake_body(objects, path, size=1024, shade=0.55, samples=48, rough=0.85, name=None, soften=2):
    """kit.bake_texture, with one step more: between the automatic unwrap and the packing the
    hidden islands are shrunk (weigh_islands), so the feathers that show get more of the image."""
    import bpy
    real_pack = bpy.ops.uv.pack_islands
    sel = list(objects)

    def pack(**kw):
        ob = bpy.context.view_layer.objects.active
        weigh_islands(ob)
        return real_pack(**kw)
    # kit.bake_texture calls bpy.ops.uv.pack_islands once, right after the unwrap
    saved = bpy.ops
    bpy.ops = _OpsProxy(saved, pack)
    try:
        return kit.bake_texture(sel, path, size=size, shade=shade, samples=samples, rough=rough, name=name, soften=soften,
                                sheen=0.0, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved


class _OpsProxy:
    """bpy.ops as the kit sees it, with uv.pack_islands replaced by `pack`."""

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


def bake(phoenix, texture):
    """Everything that does not glow becomes one textured mesh, its feather pattern and soft
    shading in the creases baked into one colour image. The glowing parts stay one mesh with their
    own bright material. Roblox gets two MeshParts."""
    glow = [ob for ob in phoenix.objects if "GLOW" in ob.name]
    body = bake_body([ob for ob in phoenix.objects if ob not in glow], texture, name="Phoenix_Body")
    me = body.data
    if "hid" in me.attributes:
        hid = [d.value for d in me.attributes["hid"].data]
        uv = me.uv_layers.active.data
        a2 = a3 = 0.0
        for pl, h in zip(me.polygons, hid):
            if h > 0.01:
                continue
            pts = [uv[i].uv for i in pl.loop_indices]
            a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
            a3 += pl.area
        print("seen surfaces: about %.0f pixels to a stud" % ((a2 * 1024 * 1024 / max(a3, 1e-9)) ** 0.5))
        me.attributes.remove(me.attributes["hid"])
    for ob in glow:
        ob.name = ob.data.name = "Phoenix_GLOW"
    phoenix.objects = [body] + glow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,side,face,back 3/4")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40, help="render samples for --review and --face")
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Phoenix review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "phoenix_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    phoenix = build()
    print("triangles by part:", dict(sorted(phoenix.tally.items(), key=lambda kv: -kv[1])))
    focus = (HEAD_AT.x * SCALE, (HEAD_AT.y + 0.2) * SCALE, (HEAD_AT.z - 0.9) * SCALE)

    def rig_for(samples):
        import review
        rig = review.Rig(phoenix, samples=samples, focus=focus)
        look = HEAD_AT * SCALE + Vector((0.0, 0.25, 0.25))                # one more camera, tight on the head
        rig.cams["face"] = review._camera("C_face", look + Vector((-0.5, -1.0, 0.12)).normalized() * 5.0, look, 30)
        rig.cams["head side"] = review._camera("C_headside", look + Vector((-1.0, 0.1, 0.1)).normalized() * 6.0, look + Vector((0, 0.5, 0)), 30)
        chest = Vector((0.0, -0.6, 4.0)) * SCALE                          # the breast and its ember
        rig.cams["chest"] = review._camera("C_chest", chest + Vector((-0.45, -1.0, 0.2)).normalized() * 6.5, chest, 30)
        wing = Vector((1.9, 0.9, 5.6)) * SCALE                            # the back of the +X wing, seen from behind
        rig.cams["wing back"] = review._camera("C_wingback", wing + Vector((0.55, 1.0, 0.35)).normalized() * 8.5, wing, 34)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), a.look) for v in a.views.split(",")], px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(phoenix, os.path.abspath(a.texture))
    tris = phoenix.triangles()
    lo, hi = phoenix.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = phoenix.objects[0].data                                          # how much of the image the texture uses
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(phoenix.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        rig, review = rig_for(a.samples)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            quick = [(v.strip(), "full") for v in a.views.split(",")]
            rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
