"""Griffin pet: a legendary storm griffin. Built from scratch by script.

    python models/pets/griffin.py --review out/griffin.png      # render the review sheet
    python models/pets/griffin.py --export models/export/griffin.fbx

Style: the third legendary creature beside the dragon and the phoenix: cool, noble and powerful,
never cute, never creepy, never plastic. Must-haves, checked in every review:
  1. Reads as a griffin in outline: an eagle's head, neck and chest on a lion's body, big eagle
     wings raised in a proud V with long fingered primaries, a long lion tail ending in a tuft.
  2. Adult proportions: a smallish head on a deep chest and a powerful body, about 9 to 10 studs
     to the wing tips, the back at about 4.5. Standing proud: head raised, chest out, four feet planted.
  3. A fierce, noble face like a crest on a shield: an angular head, a deep hooked golden beak with
     a dark tip, glowing slanted eyes without pupils under a heavy brow.
  4. Storm palette: white and pale silver head and chest, slate-blue to deep-navy wing feathers with
     silver edges, a tawny-gold lion body, dark talons, and a little electric-blue glow (eyes,
     lightning streaks near the wing tips, the core of the tail tuft).
  5. Not plastic: streaked fur and drawn feather vanes, small scales on the shanks, colour that
     changes along every feather, soft shading in the creases baked into one image.

Round 12: grey hearts showed on the breast where, in the notch between two feather tips, the
feather below shows almost down to its root: the breast is now light from a fifth of the way up each
feather, the notches are shallower and the lift after the bake a little stronger, so the shading
between rows comes from soft creases, not dark roots.

Round 11: the tuft opened like a stiff crown: now a full flame of twelve locks that bulge out and
swirl round as they rise, of uneven lengths, and the tail darkens gradually over its last stretch. The
breast feathers vary more in length, width and slant.

Round 10: the breast still baked grey: each feather row is one long piece of the texture, and the
blurred crease shading of the hidden overlaps spread over the visible part of every feather. After
the bake, the dark values on the breast are now lifted towards a soft light grey (highlights and
creases keep their order), so it stays off-white with gentle shading between rows. The tail tuft
opens out into a brush instead of closing like a bud, and the tail darkens only near its end.

Round 9: the bake's crease shading reached without limit, so the two raised wings and the head
greyed the whole breast; it now reaches 0.9 studs, so creases stay shaded and open surfaces keep
their colour. The breast feathers lie a little flatter.

Round 8: the breast read as grey shingles once baked: now off-white from the middle of each
feather out, the cool grey only where it goes under the row above, with shallower notches so each
row reads as one soft scalloped layer. Coarser coat strands and clumps that survive the bake, the
muscles painted twice as strongly, a clearer dark spine. A slimmer crest laid back along the nape.

Round 7: soft plumage on the breast: single rounded feathers laid in staggered, jittered rows,
small at the throat and longer lower down, in a warm off-white with cool grey shadows between the
rows and a faint pale gold at the tips (it held no detail in strong light). A smaller, darker beak
of horn fading to a pale tip, behind a defined golden cere. Muscles on the lion: shoulder, ribcage,
flank hollow, the back muscles either side of a darker spine and a grooved thigh, in the shape and
painted into the coat, which now has strands combed back and down in clumps. A thicker tail ending
in a full navy tuft with lightning-blue glints. Shorter eagle shanks, arched toes, gripping talons.

Round 6: the tail end now lifts off the ground so the tuft stands up in the outline, its locks
splay open and the glowing core shows between them and at the tip (it was hidden before). A
slightly shorter beak and lower crest feathers. The breast no longer reads as a regular lattice:
the rings alternate in feather count and the feathers vary in length round each ring.

Round 5: a cleaner head: the cap of crown feathers stuck up like spikes and is gone, the neck
hackles lie flatter and broader so they frame the face instead of bristling. The breast read as a
pinecone: now more, longer feathers per ring that overlap more and stand less proud, white from root
to tip, with softer crease shading in the bake. A less orange, more golden coat.

Round 4: muscular hindquarters: wider, deeper thighs that bulge out past the hips, thicker lower
legs and bigger paws; the fur streaks are now coarse enough to survive the bake (the fine ones blurred
into flat tan), with a darker back and a cream belly; a cap of small feathers over the crown so it
no longer reads as a white helmet, and the crest feathers lie lower along the nape.

Round 3: a shorter, narrower beak, amber going dark over the whole hook (the long yellow one made
the face goofy); the crest feathers tucked close along the head instead of fanning out; each hind
leg is now one continuous muscular loft from hip to paw (no stacked tubes); a stronger tone on the
coat; the skin no longer folds at the withers, the rump or the throat.

Round 2: the two upright head plumes read as bunny ears, so the crest is now three long feathers
a side swept flat back over the nape; a rounder crown and a slightly larger head; a darker beak tip.
Thicker legs: a bigger haunch with a muscle bulge, a thicker gaskin, bigger paws, thicker shanks,
bigger eagle feet. A thicker neck, a dip behind the withers, a muted tawny coat instead of orange.
Less lightning: thin streaks on three primaries a wing, in a deeper blue. Broader, less spiky
breast feathers. The neck runs into the head without folding.

Round 1: the first build. Dragon-style skin for the trunk and neck, phoenix-style rows of blade
feathers, raised eagle wings, eagle forelegs and lion hind legs, a lion tail with a tuft.
"""
import argparse
import bisect
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, rounded_box  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

HEAD_AT = Vector((-0.10, -2.40, 6.40))   # the middle of the skull
HEAD_ROT = (7, 2, -16)                   # beak a little down, a small tilt, turned towards -X (the cameras)
HEAD_SIZE = 1.08

# The trunk and neck are one skin over these sections, from the rump to inside the head:
# centre x, y, z, then half width, height above the centre line (the back), depth below it, squareness.
BODY = [
    (0.00, 3.18, 3.74, 0.32, 0.26, 0.30, 2.0),    # 0  end of the rump, where the tail grows
    (0.00, 2.72, 3.88, 0.80, 0.66, 0.84, 2.15),   # 1  rump
    (0.00, 2.00, 3.92, 1.00, 0.74, 1.00, 2.2),    # 2  hips
    (0.00, 1.10, 3.80, 0.86, 0.62, 0.86, 2.2),    # 3  loins, the back dips a little
    (0.00, 0.20, 3.80, 0.88, 0.66, 0.92, 2.2),    # 4  waist
    (0.00, -0.70, 3.86, 1.04, 0.82, 1.16, 2.2),   # 5  shoulders
    (0.00, -1.35, 3.98, 0.98, 0.6, 1.18, 2.15),   # 6  deep chest, pushed out
    (-0.02, -1.78, 4.70, 0.66, 0.48, 0.70, 2.1),  # 7  base of the neck
    (-0.05, -1.96, 5.40, 0.48, 0.42, 0.50, 2.0),  # 8  neck
]
NECK_TOP = [(0, 0.40, -0.42), (0.36, 0.33, 0.36, 2.0), (0, 0.24, -0.10), (0.26, 0.25, 0.2, 2.0)]   # in head space
# the last two sections are worked out from the head, so the neck runs into it

# The skull, in its own space (beak towards -Y): y, crown z and half width, brow corner z and half
# width, cheek z and half width, jaw corner z and half width, throat z. Flat planes between corners.
SKULL = [
    (0.46, 0.10, 0.08, 0.04, 0.17, -0.10, 0.19, -0.22, 0.14, -0.27),   # into the neck
    (0.30, 0.24, 0.12, 0.13, 0.25, -0.08, 0.27, -0.26, 0.18, -0.33),   # back of the skull
    (0.08, 0.30, 0.14, 0.17, 0.29, -0.06, 0.29, -0.26, 0.18, -0.32),   # crown
    (-0.14, 0.28, 0.13, 0.17, 0.27, -0.05, 0.255, -0.21, 0.15, -0.25),  # over the eyes
    (-0.30, 0.23, 0.10, 0.13, 0.20, -0.05, 0.19, -0.15, 0.12, -0.18),
    (-0.42, 0.18, 0.07, 0.09, 0.14, -0.05, 0.14, -0.12, 0.09, -0.13),  # the root of the beak
]

# A wing, drawn flat: (outwards, up) in studs from the shoulder.
WING_ROOT = (0.58, -0.55, 4.42)
SWEEP, LEAN, WING_SIZE = 16.0, 12.0, 1.0
ARM = [(0.0, 0.0), (1.15, 0.85), (2.45, 1.95), (3.05, 2.5)]                       # shoulder, elbow, wrist, hand
PRIMARIES = [(74, 3.0), (65, 3.25), (56, 3.35), (47, 3.3), (38, 3.15), (29, 2.95), (20, 2.8), (11, 2.65), (3, 2.5)]
SECONDARIES = [(-6, 2.45), (-15, 2.45), (-24, 2.4), (-33, 2.35), (-42, 2.3), (-51, 2.2), (-60, 2.1), (-69, 1.95)]
TERTIALS = [(-78, 1.8), (-87, 1.6), (-95, 1.4)]

# Width of a feather along its length, as a fraction of its half width (0 root, 1 tip).
FINGER = [(0, 0.0), (0.02, 0.7), (0.12, 0.92), (0.4, 1.0), (0.55, 0.82), (0.7, 0.62), (0.88, 0.46), (0.97, 0.22), (1, 0.0)]
FLIGHT = [(0, 0.0), (0.02, 0.7), (0.12, 0.9), (0.35, 1.0), (0.62, 0.95), (0.82, 0.70), (0.94, 0.36), (1, 0.0)]
PLUME = [(0, 0.0), (0.08, 0.35), (0.35, 0.8), (0.6, 1.0), (0.85, 0.6), (1, 0.0)]
LOCK = [(0, 0.0), (0.1, 0.6), (0.4, 1.0), (0.75, 0.75), (1, 0.0)]

# Cross-sections, (side, up), going round.
P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]


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


LAYERS = ("g", "xn", "d", "f")


def _layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in LAYERS]


def paint(bm, g, feather=0.0):
    """Give every vertex of a shape the colour position g (a number or a function of the vertex)."""
    lg, lx, ld, lf = _layers(bm)
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
    it is (xn, -1 to 1), how far along it is in studs (d) and whether it is a feather (f)."""
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


def limb(points, radii, shape, n, up, g=0.05):
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
    return paint(loft(pts, n, prof, up=up), g)


def round_shape(k=10):
    return [(math.cos(2 * math.pi * j / k), math.sin(2 * math.pi * j / k)) for j in range(k)]


def blade(widths, W, h, cup=0.14, thin=0.35):
    """The cross-section of a feather: two sharp edges, a raised shaft on top and a keel under it,
    `W` to each side at its widest and `h` through, arched by `cup`, thinning towards the tip."""
    def prof(t):
        w = max(W * _table(widths, t), 0.004)
        hh = min(h * 0.8 * (1 - (1 - thin) * t), w * 0.25)
        c = cup * w
        return [(-w, -c), (0.0, hh), (w, -c), (0.0, -c - hh * 0.5)]
    return prof


def row(place, count, closed=False, cols=2, rows=3, depth=0.6, lift=0.08, sink=0.04, ridge=0.03, thick=0.03,
        g=(0.1, 0.4), gpow=1.0, L=0.6, point=1.0, crisp=True):
    """A row of pointed feathers as one closed sheet. place(u, v) gives the point and the outward
    normal of the surface the row lies on: u runs across the row (feather j spans j to j + 1), v
    from the roots (0) to the tips (1). Between two feathers the tips are cut back by `depth`, so
    each one ends in a sharp point. Each has a raised shaft (`ridge`), stands `lift` proud of the
    surface at its tip and is buried `sink` at its root, so the next row up covers its root.
    Without `crisp` the tips are shaded round instead of knife-edged."""
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
            up = -sink + (lift + sink) * v ** 1.2 + ridge * (1 - abs(q)) * min(1.0, 3 * v + 0.3)
            rim = r in (0, rows) or (not closed and c in (0, ncol - 1))
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
            bm.faces.new((bot[c][r + 1], bot[d][r + 1], bot[d][r], bot[c][r]))
        if crisp:
            bm.edges.get((top[c][rows], top[d][rows])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


BREAST_L, BREAST_W = (0.32, 0.8), (0.1, 0.16)    # feather length and half width at the throat, and added lower down
BREAST_STEP = 0.5                                  # row to row, in feather lengths
def soft_row(skin, s0, lo, hi, W_of, L_of, rnd, stagger=0.0, closed=False, jitter=0.28, tilt=9.0, **kw):
    """A row of soft feathers joined side by side round the skin at s0, from angle lo to hi (a whole
    ring when `closed`), pointing towards the rump. Each feather is about 2 * W_of(th) studs wide and
    L_of(th) long, but every one gets its own width, length and slant, so that the rows never line
    up into a lattice. Four columns a feather with a soft pointed-round tip, 32 triangles each."""
    steps = max(int(hi - lo), 8)
    cum = [0.0]
    for i in range(steps):
        th = lo + (hi - lo) * (i + 0.5) / steps
        per = (skin.bare(s0, th + 0.5) - skin.bare(s0, th - 0.5)).length * (hi - lo) / steps
        cum.append(cum[-1] + per / (2.0 * W_of(th)))
    count = max(2, round(cum[-1]))

    def angle_at(x):                                      # x in feathers from lo
        x = min(max(x * cum[-1] / count, 0.0), cum[-1])
        i = min(bisect.bisect_right(cum, x) - 1, steps - 1)
        f = (x - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
        return lo + (hi - lo) * (i + f) / steps
    if closed:
        B = [angle_at(j + stagger + (rnd.uniform(-jitter, jitter) if 0 < j + stagger < count else 0.0)) for j in range(count)]
        B.append(B[0] + 360.0)
    else:
        B = [lo] + [angle_at(j + stagger + rnd.uniform(-jitter, jitter)) for j in range(1, count)] + [hi]
    n = len(B) - 1
    Ls = [L_of(0.5 * (B[j] + B[j + 1])) * rnd.uniform(0.82, 1.18) for j in range(n)]
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
                i0, i1 = i0 % n if closed else max(i0, 0), i1 % n if closed else min(i1, n - 1)
                L, tl = 0.5 * (Ls[i0] + Ls[i1]), 0.5 * (Ts[i0] + Ts[i1])
            else:
                L, tl = Ls[j], Ts[j]
            cache[key] = (th, tl, skin.toward(s0, th, L))
        th, tl, s1 = cache[key]
        s = s0 + (s1 - s0) * v
        return skin.bare(s, th + tl * v), skin.normal(s, th + tl * v)
    kw.setdefault("L", sum(Ls) / n)
    return row(place, n, closed=closed, cols=4, crisp=False, **kw)


# Muscles of the lion, for the +X side (mirrored to the other): centre, radii, a lean about X in
# degrees (the long axis tips back as it rises), how far the surface swells out in studs (negative:
# a groove) and how strongly it is painted (lighter on a muscle, darker in a groove).
BODY_MUSCLES = [
    ((0.86, -0.95, 3.55), (0.36, 0.42, 0.55), 0, 0.075, 0.0),     # shoulder, under the breast feathers
    ((0.95, 0.12, 3.42), (0.34, 0.6, 0.5), 0, 0.06, 0.12),        # ribcage
    ((0.94, 1.0, 3.2), (0.34, 0.32, 0.42), 0, -0.075, -0.22),     # flank hollow in front of the thigh
    ((0.42, 1.0, 4.42), (0.24, 1.15, 0.2), 0, 0.035, 0.09),       # long back muscles either side of the spine
    ((0.62, 2.15, 4.38), (0.26, 0.3, 0.24), 0, 0.045, 0.1),       # point of the hip
    ((0.5, 2.75, 4.25), (0.32, 0.32, 0.3), 0, 0.035, 0.08),       # rump
]
PAINTED = [                                                       # painted only: too fine for the mesh
    ((0.98, -0.42, 3.35), (0.32, 0.08, 0.5), 15, 0.0, -0.22),    # back edge of the shoulder
    ((0.97, -0.05, 3.3), (0.3, 0.055, 0.36), 20, 0.0, -0.12),     # ribs
    ((0.97, 0.25, 3.28), (0.3, 0.055, 0.36), 20, 0.0, -0.12),
    ((0.96, 0.55, 3.26), (0.3, 0.055, 0.34), 20, 0.0, -0.1),
    ((0.6, 0.7, 2.98), (0.3, 0.9, 0.09), 0, 0.0, -0.1),          # line of the belly
]
THIGH_MUSCLES = [
    ((1.22, 1.92, 3.25), (0.34, 0.075, 0.78), -25, -0.045, -0.32),  # groove between the front and back of the thigh
    ((1.18, 1.55, 2.95), (0.32, 0.3, 0.5), -25, 0.05, 0.14),         # front of the thigh
    ((1.2, 2.32, 3.35), (0.32, 0.32, 0.6), -25, 0.05, 0.14),         # back of the thigh
    ((1.06, 1.45, 2.38), (0.3, 0.26, 0.11), 0, -0.02, -0.2),         # crease over the knee
]


def field(muscles):
    """The swelling, in studs, of a list of muscles at a point (mirrored)."""
    mats = [(Vector(c), Vector(r), Matrix.Rotation(math.radians(tilt), 3, 'X').transposed(), geo)
            for c, r, tilt, geo, _ in muscles if geo]

    def f(p):
        q = Vector((abs(p.x), p.y, p.z))
        total = 0.0
        for c, r, Ri, geo in mats:
            d = Ri @ (q - c)
            total += SWELL_GAIN * geo * math.exp(-((d.x / r.x) ** 2 + (d.y / r.y) ** 2 + (d.z / r.z) ** 2))
        return total
    return f


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


def ribbon(pts, nrms, half_w, half_t, lift=0.0, taper=None):
    """A flat strip along the straight segments between `pts` (sharp corners, mitred), lying on a
    surface whose normal at each point is in `nrms`: `half_w` to each side, `half_t` through."""
    bm = bmesh.new()
    n = len(pts)
    rings = []
    for i in range(n):
        p, nr = Vector(pts[i]), Vector(nrms[i]).normalized()
        d0 = (p - Vector(pts[i - 1])).normalized() if i > 0 else None
        d1 = (Vector(pts[i + 1]) - p).normalized() if i < n - 1 else None
        d = (d0 + d1).normalized() if d0 and d1 else (d0 or d1)
        k = 1.0
        if d0 and d1:
            k = 1.0 / max(math.cos(d0.angle(d1) / 2), 0.45)
        side = nr.cross(d).normalized()
        w = half_w * k * (taper[i] if taper else 1.0)
        c = p + nr * lift
        rings.append([bm.verts.new(c + side * sx * w + nr * sz * half_t) for sx, sz in ((-1, -1), (-1, 1), (1, 1), (1, -1))])
    for a, b in zip(rings, rings[1:]):
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges:
        e.smooth = False
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


def shell(sections, corners, per=3, back_cap=0.0, nose_cap=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives the outline of one
    section as (x, z) corner points going round. Straight sides between corners make flat planes."""
    k = len(sections) - 1
    width = len(sections[0])
    rings = []
    for i in range(k * per + 1):
        sec = [_cr([s[j] for s in sections], i / per) for j in range(width)]
        rings.append((sec[0], corners(sec)))
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
    return [(0, zt + 0.02), (-0.5 * wt, zt + 0.008), (-wt, zt - 0.015), (-wb, zb), (-wc, zc), (-wj, zj), (0, zk),
            (wj, zj), (wc, zc), (wb, zb), (wt, zt - 0.015), (0.5 * wt, zt + 0.008)]


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
    90 on the back (the back of the neck), -90 underneath (the breast), 0 on the +X side."""

    def __init__(self, sections, samples=24, swell=None):
        self.swell = swell
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
        p = c + side * (w * x) + u * ((a if y > 0 else b) * y)
        if self.swell:
            p = p + (p - c).normalized() * self.swell(p)
        return p

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

    def mesh(self, segs=20, k=0.42, lo=0.13, hi=0.42):
        """The skin as one mesh; each face stores the s of its ring in the face layer "s"."""
        ss, s = [0.0], 0.0
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            ss.append(s)
        ss.append(self.L)
        bm = bmesh.new()
        lay = bm.faces.layers.float.new("s")
        loops = [[bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)] for s in ss]
        folds = 0
        for (s0, a), (s1, b) in zip(zip(ss, loops), zip(ss[1:], loops[1:])):
            t = self.at((s0 + s1) / 2)[1]
            folds += sum(1 for p, q in zip(a, b) if (q.co - p.co).dot(t) <= 0)
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))[lay] = (s0 + s1) / 2
        if folds:
            print("warning: the skin folds over itself at %d points" % folds)
        for ring, s in ((loops[0], 0.0), (loops[-1], self.L)):
            c = bm.verts.new(self.at(s)[0])
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))[lay] = s
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm


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

    def mix(fac, a, b):
        m = new("ShaderNodeMix")
        m.data_type = 'RGBA'
        for sock, v in ((0, fac), (6, a), (7, b)):
            if isinstance(v, (int, float)):
                m.inputs[sock].default_value = v
            elif isinstance(v, tuple):
                m.inputs[sock].default_value = v
            else:
                link(v, m.inputs[sock])
        return m.outputs[2]
    return new, link, attr, op, remap, ramp, mix


def plumage(name, stops, rough=0.8, streak=None, edge=None, edge_mix=0.0, edge_dark=0.8, period=0.11, slant=0.16,
            shaft=0.07, vane=True):
    """A material whose colour runs along a ramp read from each vertex's colour position g, with
    kit.furry's short streaks over it so it is not flat plastic. On feathers (f = 1) it draws a pale
    shaft and fine barbs, and with `edge` the edges of each feather turn towards that colour."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **(streak or {}))
    tree = m.node_tree
    new, link, attr, op, remap, ramp, mix = _node_ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    colour = ramp(attr("g"), stops)
    ax = op('ABSOLUTE', attr("xn"))
    f = attr("f")
    if edge:
        fac = op('MULTIPLY', remap(ax, 0.6, 0.95, 0.0, edge_mix, smooth=True), f)
        colour = mix(fac, colour, (*kit.srgb(edge), 1.0))
    link(colour, hsv.inputs["Color"])
    if vane:
        phase = op('MULTIPLY_ADD', ax, -slant, attr("d"))
        wave = op('SINE', op('MULTIPLY', phase, 2 * math.pi / period))
        barbs = op('MULTIPLY_ADD', wave, 0.07, 1.0)
        lit = op('MULTIPLY_ADD', remap(ax, shaft, 0.0), 0.35, barbs)
        pattern = op('MULTIPLY', lit, remap(ax, 0.65, 1.0, 1.0, edge_dark))
        mixed = op('MULTIPLY_ADD', op('SUBTRACT', pattern, 1.0), f, 1.0)
        old = hsv.inputs["Value"].links[0].from_socket
        link(op('MULTIPLY', old, mixed), hsv.inputs["Value"])
    return m


PAINT_GAIN, SWELL_GAIN = 1.8, 1.4   # how strongly the muscles are painted, and how far they swell
STRAND_ANGLE = 126.87   # turns the strand pattern so the coat is combed back and down


def coat_material(name, stops, muscles, up=0.62, down=1.24, down_sat=0.55, keep=0.6, dorsal=0.38):
    """The lion's coat: a ramp read from g (tawny body to the dark end of the tail), painted strands
    combed back and down in clumps, the muscles painted in (lighter on a muscle, darker in the
    grooves), a darker line down the spine, a darker back and a paler, greyer belly."""
    m = kit.material(name, stops[0][1], rough=0.85)
    tree = m.node_tree
    new, link, attr, op, remap, ramp, mix = _node_ops(tree)
    b = kit.principled(m)
    g = attr("g")
    hsv = new("ShaderNodeHueSaturation")
    link(ramp(g, stops), hsv.inputs["Color"])
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    obj = new("ShaderNodeTexCoord").outputs["Object"]
    sep = new("ShaderNodeSeparateXYZ")
    link(obj, sep.inputs[0])
    ax = op('ABSOLUTE', sep.outputs[0])
    comb = new("ShaderNodeCombineXYZ")
    link(ax, comb.inputs[0])
    link(sep.outputs[1], comb.inputs[1])
    link(sep.outputs[2], comb.inputs[2])
    rot = new("ShaderNodeVectorRotate")
    rot.rotation_type = 'X_AXIS'
    rot.inputs["Angle"].default_value = math.radians(STRAND_ANGLE)
    link(obj, rot.inputs["Vector"])

    def stretched(scale, length):
        mp = new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale, scale / length)
        link(rot.outputs["Vector"], mp.inputs["Vector"])
        return mp.outputs["Vector"]
    fine = new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 1.0, 4.0
    link(stretched(8.0, 4.5), fine.inputs["Vector"])
    streak = remap(fine.outputs[0], 0.32, 0.68, 0.0, 1.0, smooth=True)
    clump = new("ShaderNodeTexVoronoi")
    clump.feature = 'DISTANCE_TO_EDGE'
    clump.inputs["Scale"].default_value = 1.0
    link(stretched(2.6, 2.6), clump.inputs["Vector"])
    edge = remap(clump.outputs["Distance"], 0.0, 0.2, 0.0, 1.0, smooth=True)
    blotch = new("ShaderNodeTexNoise")
    blotch.inputs["Scale"].default_value, blotch.inputs["Detail"].default_value = 1.6, 1.0
    link(obj, blotch.inputs["Vector"])
    val = op('MULTIPLY_ADD', streak, 0.34, 0.8)
    val = op('MULTIPLY', val, op('MULTIPLY_ADD', edge, 0.26, 0.8))
    val = op('MULTIPLY', val, op('MULTIPLY_ADD', blotch.outputs[0], 0.16, 0.92))
    total = None
    for c, r, tilt, _geo, amount in muscles:
        if not amount:
            continue
        mp = new("ShaderNodeMapping")
        mp.vector_type = 'TEXTURE'
        mp.inputs["Location"].default_value = c
        mp.inputs["Rotation"].default_value = (math.radians(tilt), 0.0, 0.0)
        mp.inputs["Scale"].default_value = r
        link(comb.outputs[0], mp.inputs["Vector"])
        dot = new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        link(mp.outputs[0], dot.inputs[0])
        link(mp.outputs[0], dot.inputs[1])
        term = op('MULTIPLY', op('EXPONENT', op('MULTIPLY', dot.outputs["Value"], -1.0)), amount * PAINT_GAIN)
        total = term if total is None else op('ADD', total, term)
    if total is not None:
        val = op('MULTIPLY', val, op('ADD', total, 1.0))
    geo = new("ShaderNodeNewGeometry")
    sn = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sn.inputs[0])
    nz = sn.outputs[2]
    body = remap(g, keep, keep + 0.15, 1.0, 0.0)
    upf = op('MULTIPLY', remap(nz, 0.1, 0.9, 0.0, 1.0 - up, smooth=True), body)
    dnf = op('MULTIPLY', remap(nz, -0.1, -0.85, 0.0, down - 1.0, smooth=True), body)
    val = op('MULTIPLY', val, op('ADD', op('SUBTRACT', 1.0, upf), dnf))
    spine = op('MULTIPLY', remap(ax, 0.42, 0.1, 0.0, 1.0, smooth=True), remap(nz, 0.35, 0.8, 0.0, 1.0, smooth=True))
    val = op('MULTIPLY', val, op('MULTIPLY_ADD', spine, -dorsal, 1.0))
    link(val, hsv.inputs["Value"])
    sat = op('SUBTRACT', 1.0, op('MULTIPLY', remap(nz, -0.1, -0.85, 0.0, 1.0 - down_sat, smooth=True), body))
    link(op('MULTIPLY_ADD', spine, 0.15, sat), hsv.inputs["Saturation"])
    return m


# ---- the griffin ---------------------------------------------------------------------------------------

def build():
    plume = plumage("Plume", [(0.0, "#252E40"), (0.16, "#4E5C74"), (0.34, "#A2AEBE"), (0.52, "#D2D8DE"),
                              (0.78, "#E2E5E8"), (1.0, "#B4C2D4")], 0.85,
                    dict(strength=0.12, mottle=0.08, fine=36.0, length=5.0), edge_dark=0.92)
    wing = plumage("Wing", [(0.0, "#D4DCE4"), (0.14, "#A8B6C8"), (0.3, "#6C84A6"), (0.48, "#435C86"),
                            (0.68, "#263860"), (0.86, "#172446"), (1.0, "#10182F")], 0.85,
                   dict(strength=0.12, mottle=0.08, fine=36.0, length=5.0), edge="#C4D0DE", edge_mix=0.8, edge_dark=1.0)
    fur = coat_material("Fur", [(0.0, "#B8955E"), (0.6, "#B08C58"), (0.75, "#6E5034"), (0.88, "#2C2A30"), (1.0, "#151B2E")],
                        BODY_MUSCLES + PAINTED + THIGH_MUSCLES)
    # the breast: warm off-white tips, cool grey where each feather goes under the row above, pale gold at the very tip
    breast = plumage("Breast", [(0.0, "#B4BBC4"), (0.2, "#CACFD5"), (0.5, "#D9DBDC"), (0.76, "#E3E1DA"), (0.93, "#E6DECB"),
                                (1.0, "#E0D1AC")], 0.85, dict(strength=0.1, mottle=0.07, fine=40.0, length=5.0),
                     edge="#E6D6AE", edge_mix=0.35, edge_dark=0.9, period=0.08, slant=0.22, shaft=0.06)
    # horn: dark at the base, fading to a pale tip; a golden cere behind it
    beak = plumage("Beak", [(0.0, "#2A2420"), (0.4, "#3A302A"), (0.65, "#5E5244"), (0.82, "#9C8C70"), (0.93, "#CFC3A3"), (1.0, "#E2D8BC")],
                   0.45, dict(strength=0.06, mottle=0.05, fine=70.0, length=3.0), vane=False)
    cere = kit.scaly(kit.material("Cere", "#D2A440"), size=0.03, joins=0.25, vary=0.1, rough=0.6)
    tuft = plumage("Tuft", [(0.0, "#2A2830"), (0.28, "#1C2644"), (0.6, "#2A3E6C"), (0.85, "#46669E"), (1.0, "#7EA2DA")], 0.8,
                   dict(strength=0.14, mottle=0.08, fine=40.0, length=5.0), edge="#9CC2FF", edge_mix=0.45, edge_dark=1.0, period=0.09)
    talon = plumage("Talon", [(0.0, "#3A3530"), (0.5, "#221F22"), (1.0, "#0B0B0E")], 0.5,
                    dict(strength=0.1, mottle=0.06, fine=50.0, length=2.0), vane=False)
    shank = kit.scaly(kit.material("Shank", "#C99A40"), size=0.065, joins=0.45, vary=0.18, rough=0.7)
    dark = kit.material("Dark", "#0A0B0E", rough=0.6)
    glow = kit.material("GLOW_Storm", "#2E8CFF", rough=0.4, emit=3.2)

    gr = Prop("Griffin")
    gr.tally = {}

    def add(part, bm, mat, at=None, crease=None):
        _layers(bm)
        pale = bm.verts.layers.float.get("pale") or bm.verts.layers.float.new("pale")
        for v in bm.verts:
            v[pale] = 1.0 if mat is breast else 0.0          # marks the breast for the lift after the bake
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if crease:
            sharpen(bm, crease)
        gr.tally[part] = gr.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        gr.add(bm, mat)

    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)

    def hs(p):
        return tuple(H @ Vector(p))

    # ---- trunk and neck: one skin; white under the feathers in front, tawny fur behind ------------------
    sections = BODY + [(*hs(NECK_TOP[0]), *NECK_TOP[1]), (*hs(NECK_TOP[2]), *NECK_TOP[3])]
    skin = Skin(sections, swell=field(BODY_MUSCLES))
    s_fur = skin.s_of(4.75)
    bm = skin.mesh(segs=20)
    lay = bm.faces.layers.float.get("s")
    front, back = kit.split(bm, lambda f: f[lay] > s_fur)
    add("skin", paint(front, 0.42), breast)
    add("skin", paint(back, 0.1), fur)

    def arc_of(s0, lo, hi, count, L_of, stagger=0.0):
        """place() for an open row of feathers round the skin from angle lo to hi at s0, pointing
        towards the rump."""
        dth = (hi - lo) / count
        cache = {}

        def place(u, v):
            th = lo + (u + stagger) * dth
            if th not in cache:
                cache[th] = skin.toward(s0, th, L_of(th))
            s = s0 + (cache[th] - s0) * v
            return skin.bare(s, th), skin.normal(s, th)
        return place

    # neck hackles: long pointed feathers round the back and sides of the neck, framing the face
    for i, idx in enumerate((9.55, 9.0, 8.4, 7.8)):
        s = skin.s_of(idx)
        L = 0.64 + 0.07 * i
        add("hackles", row(arc_of(s, -34.0, 214.0, 8, lambda th, L=L, i=i: L * (1 + 0.07 * math.sin(math.radians(th) * 3 + i)),
                                  0.5 * (i % 2) - 0.25), 8, rows=2, depth=0.5, lift=0.06 + 0.012 * i, sink=0.05, ridge=0.03,
                           thick=0.035, g=(0.52, 0.9), gpow=1.2, L=L, point=0.85), plume)
    # throat and breast: soft rounded feathers, small under the beak and longer lower down, in staggered,
    # jittered rows so that they overlap like plumage and never line up into a lattice
    rnd = random.Random(7)
    s_top, s_bot, s_chest = skin.s_of(9.2), s_fur - 0.1, skin.s_of(7.25)
    s, k = s_top, 0
    while s > s_bot:
        t = min((s_top - s) / (s_top - s_bot), 1.0)
        L, W = BREAST_L[0] + BREAST_L[1] * t, BREAST_W[0] + BREAST_W[1] * t
        W_of = lambda th, W=W: W * (1.0 + 0.7 * max(0.0, math.sin(math.radians(th))))     # broader on the back, under the wings
        L_of = lambda th, L=L: L * (1.0 + 0.15 * max(0.0, math.sin(math.radians(th))))
        common = dict(rows=2, depth=0.24, point=1.4, lift=0.022, sink=0.045, ridge=0.012, thick=0.02,
                      g=(0.0, 0.94 + 0.03 * (k % 3)))
        if s > s_chest:
            add("breast", soft_row(skin, s, -214.0, 34.0, W_of, L_of, rnd, stagger=0.5 * (k % 2), **common), breast)
        else:
            add("breast", soft_row(skin, s, -270.0, 90.0, W_of, L_of, rnd, stagger=0.5 * (k % 2), closed=True, **common), breast)
        s = skin.toward(s, -90.0, BREAST_STEP * L)
        k += 1

    # ---- wings: raised in a proud V, broad, with long fingered primaries ----------------------------------
    for sx in (-1, 1):
        A = Vector((sx * math.cos(math.radians(SWEEP)), math.sin(math.radians(SWEEP)), 0.0))
        B = Vector((0.0, math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))))
        B = (B - A * B.dot(A)).normalized()
        F = A.cross(B)
        F = F if F.y < 0 else -F
        R = Vector((WING_ROOT[0] * sx, WING_ROOT[1], WING_ROOT[2]))

        def P(a, b, c=0.0, R=R, A=A, B=B, F=F):
            """A point of the wing: `a` out and `b` up in the flat drawing, `c` in front of it; the
            wing is cupped so that its outer half sweeps back."""
            return R + (A * a + B * b) * WING_SIZE + F * (c - 0.03 * a * a)

        def Nw(a, b, P=P, F=F):
            n = (P(a + 0.05, b) - P(a - 0.05, b)).cross(P(a, b + 0.05) - P(a, b - 0.05)).normalized()
            return n if n.dot(F) > 0 else -n

        def flight(a0, b0, phi, L, W, c0, g, widths=FLIGHT, n=9, bend=-0.07, curl=0.10, h=0.05, bolt=False, P=P, Nw=Nw):
            d = Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi))))
            q = Vector((-d.y, d.x))
            ss = (0.0, 1 / 3, 2 / 3, 1.0)
            flat = [Vector((a0, b0)) + d * L * s + q * bend * L * s * s for s in ss]
            pts = [P(f.x, f.y, c0 - curl * L * s ** 2.5) for f, s in zip(flat, ss)]
            up = lambda t: Nw(*(Vector((a0, b0)) + d * L * t))
            add("flight feathers", loft(pts, n, blade(widths, W, h), up=up, g=g, feather=True, tip=True, root=True,
                                        sharp=(0, 2)), wing)
            if bolt:                                                   # a thin jagged streak of lightning near the tip
                zig = ((0.62, 0.0), (0.69, 0.4), (0.75, -0.28), (0.82, 0.32), (0.88, -0.16), (0.93, 0.05))
                bp, bn = [], []
                for s, off in zig:
                    w = W * _table(widths, s)
                    f = Vector((a0, b0)) + d * L * s + q * (bend * L * s * s + off * w)
                    bp.append(P(f.x, f.y, c0 - curl * L * s ** 2.5))
                    bn.append(Nw(f.x, f.y))
                add("glow", ribbon(bp, bn, 0.018, 0.04, lift=-0.008, taper=(0.4, 1.0, 1.0, 0.85, 0.6, 0.3)), glow)

        S, E, Wr, Hd = (Vector(p) for p in ARM)
        for i, (phi, L) in enumerate(PRIMARIES):
            r = Hd.lerp(Wr, i / (len(PRIMARIES) - 1))
            flight(r.x, r.y, phi, L, 0.3, -0.025 * i, (0.42, 1.0), widths=FINGER, n=10, bolt=i in (1, 3, 5))
        for j, (phi, L) in enumerate(SECONDARIES):
            r = Wr.lerp(E, (j + 0.4) / len(SECONDARIES))
            flight(r.x, r.y, phi, L, 0.3, -0.19 + 0.02 * j, (0.38, 0.92), n=7)
        for j, (phi, L) in enumerate(TERTIALS):
            r = E.lerp(S, 0.15 + 0.3 * j)
            flight(r.x, r.y, phi, L, 0.27, -0.05 + 0.02 * j, (0.32, 0.8), n=6)

        def arm_row(line, phis, lengths, c0, count, lift, g, depth=0.55, rows=2, back=False, P=P, Nw=Nw):
            """A row of coverts whose roots run along `line` (points of the drawing), pointing at the
            angles `phis` and as long as `lengths` (tables over 0..1 along the row). With `back`
            the row lies on the back of the wing."""
            curve = Curve([Vector((p.x, p.y, 0.0)) for p in line])
            sgn = -1.0 if back else 1.0

            def place(u, v):
                f = u / count
                root = curve.at(f)
                phi = math.radians(_table(phis, f))
                ab = Vector((root.x, root.y)) + Vector((math.cos(phi), math.sin(phi))) * _table(lengths, f) * v
                return P(ab.x, ab.y, c0), Nw(ab.x, ab.y) * sgn
            return row(place, count, rows=rows, depth=depth, lift=lift, sink=0.0, ridge=0.035, thick=0.035, g=g,
                       L=_table(lengths, 0.5))

        pc = [(i / 8, PRIMARIES[i][0]) for i in range(9)]
        add("coverts", arm_row([Hd + Vector((0.05, 0.08)), Wr + Vector((0.0, 0.08))], pc,
                               [(0, 1.3), (0.5, 1.25), (1, 1.05)], 0.07, 9, 0.05, (0.3, 0.62)), wing)
        add("coverts", arm_row([Wr + Vector((-0.02, 0.10)), E + Vector((0.05, 0.12))], [(0, -8), (0.5, -36), (1, -66)],
                               [(0, 1.15), (1, 1.0)], 0.07, 8, 0.05, (0.26, 0.55)), wing)
        add("coverts", arm_row([S + Vector((0.1, 0.25)), E + Vector((0.02, 0.32)), Wr + Vector((-0.02, 0.32))],
                               [(0, -80), (0.45, -52), (1, -20)], [(0, 0.85), (1, 0.8)], 0.14, 10, 0.05, (0.16, 0.42)), wing)
        add("coverts", arm_row([S + Vector((0.15, 0.42)), E + Vector((0.0, 0.52)), Wr + Vector((-0.08, 0.5)), Hd + Vector((-0.02, 0.3))],
                               [(0, -72), (0.3, -42), (0.7, -6), (1, 20)], [(0, 0.6), (1, 0.52)], 0.2, 12, 0.04, (0.03, 0.22)), wing)
        add("coverts", arm_row([S + Vector((0.1, 0.12)), E + Vector((0.0, 0.18)), Wr + Vector((0.0, 0.16)), Hd + Vector((0.0, 0.08))],
                               [(0, -80), (0.4, -48), (0.75, -12), (1, 18)], [(0, 0.9), (1, 0.7)], -0.1, 11, 0.04, (0.2, 0.5),
                               back=True), wing)
        arm = [S, E, Wr, Hd]
        add("wing arms", paint(loft([P(p.x, p.y, 0.05) for p in arm], 8, fixed([0.3, 0.2, 0.14, 0.09], round_shape(8)),
                                    up=F), 0.04), wing)

    # ---- forelegs: an eagle's, white feathered trousers over golden scaled shanks and big dark talons -----
    for sx in (-1, 1):
        top = Vector((0.62 * sx, -1.15, 3.15))
        knee = Vector((0.86 * sx, -1.42, 1.36))
        upper = [top, top.lerp(knee, 0.5) + Vector((0.04 * sx, 0.06, 0.0)), knee]
        add("legs", paint(loft(upper, 6, fixed([0.5, 0.42, 0.3], round_shape(10)), up=(0, -1, 0)), 0.5), breast)
        for k, (u0, L) in enumerate(((0.0, 0.64), (0.34, 0.62), (0.66, 0.6))):

            def place(u, v, u0=u0, k=k, upper=upper):
                C = Curve(upper)
                t = min(u0 + 0.42 * v, 1.0)
                c, T = C.at(t), C.tangent(t)
                ang = 2 * math.pi * (u + 0.5 * k) / 6
                x0 = T.cross(Vector((0, 1, 0))).normalized()
                y0 = x0.cross(T).normalized()
                radial = x0 * math.cos(ang) + y0 * math.sin(ang)
                rad = 0.5 + (0.3 - 0.5) * t + 0.08 * v
                return c + radial * rad, (radial - T * 0.35).normalized()
            add("trousers", row(place, 6, closed=True, cols=3, rows=2, depth=0.42, point=1.7, lift=0.07, sink=0.03, ridge=0.02,
                                thick=0.03, g=(0.3, 0.97), L=L), breast)
        shin = [Vector((0.86 * sx, -1.45, 1.5)), Vector((0.88 * sx, -1.58, 0.86)), Vector((0.9 * sx, -1.70, 0.25))]
        add("legs", paint(loft(shin, 6, fixed([0.27, 0.235, 0.255], round_shape(10)), up=(0, -1, 0)), 0.0), shank)
        for k in range(3):                                             # scutes down the front of the shank
            t = 0.3 + 0.21 * k
            C = Curve(shin)
            c = C.at(t)
            plate = [(math.cos(math.pi * j / 4) * 0.2, -0.04 + 0.12 * math.sin(math.pi * j / 4)) for j in range(5)] + [(-0.12, -0.09), (0.12, -0.09)]
            add("legs", lens(plate, 0.07, rows=((1.0, 0.0),)), shank, seat(c + Vector((0, -0.225, 0.0)), (0, -1, 0.1)))
        foot = Vector((0.9 * sx, -1.74, 0.0))
        add("feet", kit.ball((0.56, 0.56, 0.34), cuts=2), shank, M(foot + Vector((0, 0, 0.16))))
        for yaw, size in ((-34 + 6 * sx, 1.05), (6 * sx, 1.2), (34 + 6 * sx, 1.05), (180, 0.8)):
            F = M(foot, rot=(0, 0, yaw), scale=(1.12, size * 1.08, 1.12))
            toe = [(0, 0, 0.15), (0, -0.26, 0.2), (0, -0.5, 0.16), (0, -0.66, 0.11)]            # arched over the knuckles
            add("feet", loft(toe, 4, fixed([0.16, 0.15, 0.13, 0.11], round_shape(8)), up=(0, 0, 1)), shank, F)
            claw = [(0, -0.6, 0.14), (0, -0.82, 0.2), (0, -0.99, 0.12), (0, -1.05, -0.03)]     # hooked down into the ground
            add("talons", loft(claw, 5, fixed([0.115, 0.088, 0.05, 0.008], P_CLAW), up=(0, -0.3, 1), g=(0.0, 1.0),
                               tip=True), talon, F, crease=50)

    thigh = field(THIGH_MUSCLES)

    # ---- hind legs: a lion's, powerful haunches, the hock high and back, padded paws ---------------------
    for sx in (-1, 1):
        # one continuous leg: hip, the knee forward, the hock high and back, down to the paw
        leg = [(0.66 * sx, 2.12, 4.05), (0.98 * sx, 1.66, 3.05), (1.06 * sx, 1.32, 2.1), (1.08 * sx, 1.86, 1.52),
               (1.08 * sx, 2.42, 1.1), (1.06 * sx, 2.32, 0.62), (1.04 * sx, 2.2, 0.28)]
        add("legs", limb(leg, [(0.6, 1.12), (0.58, 1.04), (0.44, 0.56), (0.39, 0.48), (0.29, 0.33), (0.25, 0.28), (0.27, 0.3)],
                         P_LEG, 20, up=(0, -1, 0.05)), fur)
        # the big thigh muscle rounds the haunch out; a groove parts its front from its back
        hb = paint(kit.ball((0.62, 1.3, 1.45), cuts=3), 0.05)
        hb.transform(M((0.96 * sx, 1.95, 3.18), rot=(-26, 0, 6 * sx)))
        hb.normal_update()
        for v in hb.verts:
            v.co += v.normal * thigh(v.co)
        add("haunch", hb, fur)
        paw = Vector((1.04 * sx, 2.02, 0.0))
        add("paws", paint(rounded_box((0.72, 0.8, 0.5), n=3.0, cuts=2), 0.05), fur, M(paw + Vector((0, 0, 0.24))))
        for k, ox in enumerate((-0.27, -0.09, 0.09, 0.27)):
            dy = -0.05 if k in (1, 2) else 0.0
            add("paws", paint(kit.ball((0.24, 0.3, 0.27), cuts=1), 0.05), fur, M(paw + Vector((ox, -0.37 + dy, 0.125))))
            claw = [(ox, -0.49 + dy, 0.14), (ox, -0.57 + dy, 0.1), (ox, -0.61 + dy, 0.0)]
            add("talons", loft(claw, 4, fixed([0.05, 0.034, 0.006], P_CLAW), up=(0, -0.3, 1), g=(0.3, 1.0), tip=True),
                talon, M(paw), crease=50)

    # ---- tail: a thick lion's tail lying on the ground, the end lifting in a full navy tuft that glows inside
    tail = [(0, 2.95, 3.72), (0.05, 3.45, 3.46), (0.17, 3.95, 2.78), (0.28, 4.3, 1.88), (0.28, 4.56, 0.98), (0.13, 4.88, 0.36),
            (-0.25, 5.33, 0.21), (-0.62, 5.7, 0.55), (-0.82, 5.9, 1.08), (-0.88, 5.98, 1.45)]
    add("tail", loft(tail, 24, fixed([0.36, 0.3, 0.26, 0.23, 0.215, 0.205, 0.195, 0.185, 0.18, 0.19], round_shape(10)), up=(0, 0, 1),
                     g=(0.05, 0.84), gpow=3.0), fur)
    C = Curve(tail)
    end, T = C.at(1.0), C.tangent(1.0)
    X = T.cross(Vector((0, 0, 1))).normalized()
    Y = X.cross(T).normalized()
    frame = Matrix((X, Y, T)).transposed().to_4x4()
    frame.translation = end + T * 0.22
    add("tuft", paint(kit.ball((0.4, 0.4, 0.6), cuts=2), 0.3), tuft, frame)
    for k in range(12):
        outer = k >= 4
        ang = 2 * math.pi * ((k - 4 + 0.5) / 8 if outer else k / 4) + 0.15 * math.sin(3.1 * k)
        rad = X * math.cos(ang) + Y * math.sin(ang)
        swirl = rad.cross(T).normalized()                               # round the tail, so the locks twist like a flame
        if outer:                                                       # bulging out, then swirling in to uneven tips
            Lk, Wk = 0.98 + 0.13 * ((k * 5) % 3), 0.165
            pts = [end - T * 0.22 + rad * 0.06, end + T * 0.2 + rad * 0.34, end + T * 0.6 * Lk + rad * 0.42 + swirl * 0.1,
                   end + T * Lk + rad * 0.3 + swirl * 0.26]
        else:                                                           # the core of the tuft stands up
            Lk, Wk = 1.12 + 0.1 * (k % 2), 0.14
            pts = [end - T * 0.22 + rad * 0.05, end + T * 0.16 + rad * 0.16, end + T * 0.55 * Lk + rad * 0.2 + swirl * 0.05,
                   end + T * Lk + rad * 0.1 + swirl * 0.14]
        add("tuft", loft(pts, 7, blade(LOCK, Wk, 0.05, cup=0.25), up=rad, g=(0.0, 1.0), feather=True, tip=True, root=True,
                         sharp=(0, 2)), tuft)
        if k in (5, 9):                                                 # a lightning glint along two of the outer locks
            Ck = Curve(pts)
            bp, bn = [], []
            for sv, off in ((0.36, 0.0), (0.46, 0.45), (0.56, -0.3), (0.66, 0.35), (0.76, -0.2), (0.84, 0.05)):
                c, Tk = Ck.at(sv), Ck.tangent(sv)
                N = (rad - Tk * rad.dot(Tk)).normalized()
                Wd = Tk.cross(N)
                bp.append(c + Wd * off * Wk * _table(LOCK, sv) + N * 0.02)
                bn.append(N)
            add("glow", ribbon(bp, bn, 0.016, 0.03, taper=(0.4, 1.0, 1.0, 0.85, 0.6, 0.3)), glow)
    add("glow", loft([end - T * 0.05, end + T * 0.45, end + T * 0.9, end + T * 1.2], 8, fixed([0.08, 0.17, 0.12, 0.01], round_shape(6)),
                     up=Y, tip=True), glow)

    # ---- head: placed in its own space, then turned as one ---------------------------------------------
    skull = shell(SKULL, skull_corners, per=3, back_cap=0.05, nose_cap=0.0)
    face = Surface(skull)

    # the beak: deep and sharply hooked, gold going dark at the hook, over a smaller lower bill
    def bill(t):
        w = 0.096 * (1 - t) ** 0.55 + 0.005
        hh = 0.228 * (1 - 0.9 * t) + 0.007
        return [(0.0, hh * 0.62), (0.4 * w, hh * 0.46), (w, 0.0), (0.82 * w, -hh * 0.38), (0.0, -hh * 0.28),
                (-0.82 * w, -hh * 0.38), (-w, 0.0), (-0.4 * w, hh * 0.46)]
    upper = [(0, -0.33, 0.025), (0, -0.45, 0.02), (0, -0.555, -0.008), (0, -0.63, -0.056), (0, -0.667, -0.13),
             (0, -0.66, -0.2), (0, -0.625, -0.247)]
    add("beak", loft(upper, 16, bill, side=(1, 0, 0), ref=(0, 0, 1), g=(0.0, 1.0), gpow=2.2, sharp=(0, 3, 5), tip=True), beak, H)

    def jaw(t):
        w = 0.066 * (1 - t) ** 0.6 + 0.008
        hh = 0.064 * (1 - 0.6 * t) + 0.007
        return [(0.0, hh * 0.3), (w, 0.0), (0.6 * w, -hh * 0.6), (-0.6 * w, -hh * 0.6), (-w, 0.0)]
    lower = [(0, -0.3, -0.092), (0, -0.42, -0.108), (0, -0.505, -0.114), (0, -0.555, -0.114)]
    add("beak", loft(lower, 6, jaw, side=(1, 0, 0), ref=(0, 0, 1), g=(0.05, 0.5), sharp=(1, 4), tip=True), beak, H)

    # the cere: a waxy golden band where the beak leaves the face, a little proud of the horn so its edge is crisp
    def cere_ring(t):
        w = 0.11 - 0.009 * t
        hh = 0.236 - 0.022 * t
        return [(0.0, hh * 0.64), (0.42 * w, hh * 0.49), (w, 0.0), (0.84 * w, -hh * 0.36), (0.0, -hh * 0.26),
                (-0.84 * w, -hh * 0.36), (-w, 0.0), (-0.42 * w, hh * 0.49)]
    add("beak", loft([(0, -0.39, 0.024), (0, -0.45, 0.018), (0, -0.505, 0.009)], 3, cere_ring, side=(1, 0, 0), ref=(0, 0, 1)),
        cere, H, crease=50)

    for sx in (-1, 1):
        # brow: a heavy ridge from the root of the beak back over the eye, casting it into shadow
        brow = [(0.08 * sx, -0.46, 0.15), (0.17 * sx, -0.34, 0.205), (0.255 * sx, -0.2, 0.225), (0.29 * sx, -0.05, 0.215),
                (0.26 * sx, 0.1, 0.18)]
        add("brows", paint(loft(brow, 8, fixed([(0.03, 0.025), (0.065, 0.045), (0.09, 0.062), (0.075, 0.055), (0.035, 0.03)], P_BROW),
                                up=(0.75 * sx, 0, 1)), 0.6), plume, H, crease=38)
        # a dark slate stripe through the eye and back along the side of the head
        stripe = []
        for y, z in ((-0.27, 0.05), (-0.16, 0.07), (-0.02, 0.05), (0.14, 0.0), (0.3, -0.07)):
            p, nrm = face.hit((0.8 * sx, y, z), (-sx, 0, 0))
            stripe.append((p, nrm))

        def band(t):
            w = 0.07 * _table([(0, 0.5), (0.2, 1.0), (0.6, 0.9), (1, 0.35)], t)
            return [(-w, 0.0), (0.0, 0.012), (w, 0.0), (0.0, -0.012)]
        add("mask", loft([p for p, _ in stripe], 7, band, up=lambda t: stripe[min(int(t * 4.999), 4)][1], g=(0.04, 0.12)), plume, H)
        # the eye: a glowing almond, slanted down towards the beak, tucked under the brow
        p, nrm = face.hit((0.8 * sx, -0.17, 0.07), (-sx, 0.0, 0.0))
        eye = [(-0.5, -0.05), (-0.25, 0.05), (0.05, 0.11), (0.35, 0.15), (0.52, 0.16), (0.36, 0.04), (0.1, -0.05), (-0.22, -0.08)]
        add("eyes", lens([(a * 0.22, b * 0.34) for a, b in eye], 0.05, rows=((0.6, 0.85), (1.0, 0.0)), centre=(0.0, 0.03)),
            glow, H @ facing(p + nrm * 0.006, nrm, Vector((0, 1, 0.05))))
        # the gape: a dark line from the hook of the beak back to under the eye
        gape = [(0.064 * sx, -0.52, -0.088), (0.098 * sx, -0.455, -0.082), (0.155 * sx, -0.33, -0.075), (0.2 * sx, -0.2, -0.06)]
        add("mouth", loft(gape, 6, fixed([0.012, 0.014, 0.012, 0.008], round_shape(5)), up=(0, 0, 1)), dark, H)
        # nostril on the cere
        add("mouth", lens([(-0.5, 0), (0, 0.2), (0.5, 0.05), (0, -0.15)], 0.03), dark,
            H @ facing(Vector((0.08 * sx, -0.455, 0.075)), Vector((sx, -0.2, 0.45)), Vector((0, 1, 0.1))) @ M(scale=(0.06, 1, 0.07)))
        # a crest of long feathers swept flat back over the nape: a regal outline to the head
        crest = (((0.1, 0.0, 0.25), ((0.02, 0.36, -0.05), (0.04, 0.68, -0.14), (0.055, 0.94, -0.2)), 0.06, (0.3, 0, 1)),
                 ((0.18, 0.06, 0.16), ((0.03, 0.34, -0.09), (0.05, 0.6, -0.18), (0.065, 0.82, -0.24)), 0.055, (0.7, 0, 0.75)),
                 ((0.22, 0.12, 0.03), ((0.02, 0.3, -0.12), (0.04, 0.52, -0.2), (0.05, 0.7, -0.24)), 0.05, (1.0, 0, 0.3)))
        for r0, path, Wp, upv in crest:
            base = Vector((r0[0] * sx, r0[1], r0[2]))
            pts = [base] + [base + Vector((d[0] * sx, d[1], d[2])) for d in path]
            add("plumes", loft(pts, 7, blade(PLUME, Wp, 0.032, cup=0.12), up=Vector((upv[0] * sx, upv[1], upv[2])), g=(0.5, 0.98),
                               feather=True, tip=True, root=True, sharp=(0, 2)), plume, H)

        # a row of small swept feathers over each cheek, below and behind the eye
        def cheek(u, v, sx=sx):
            y = -0.2 + 0.07 * u + 0.3 * v
            z = -0.1 - 0.015 * u + 0.03 * v
            p, nrm = face.hit((0.8 * sx, y, z), (-sx, 0, 0))
            return p, nrm
        add("cheeks", row(cheek, 4, rows=2, depth=0.55, lift=0.03, sink=0.02, ridge=0.02, thick=0.02, g=(0.5, 0.7), L=0.4), plume, H)

    add("head", paint(skull, 0.62), plume, H, crease=55)

    gr.build()
    for ob in gr.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return gr


AO_REACH = 0.9
PALE_TARGET, PALE_LIFT = 0.85, 0.65     # on the breast, values below the target are pulled this far up to it


def lift_breast(ob, path, size=1024):
    """Bake the "pale" mask of the breast into the texture's layout and pull the dark values there up
    towards PALE_TARGET, so the white plumage keeps soft shading instead of going grey."""
    import bpy
    import numpy as np
    sc = bpy.context.scene
    keep = sc.cycles.samples
    sc.cycles.samples = 4
    baked = ob.data.materials[0]
    m = bpy.data.materials.new("PaleMask")
    kit.principled(m)
    tree = m.node_tree
    a = tree.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "pale"
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(a.outputs["Fac"], em.inputs["Color"])
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    tree.links.new(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new("pale_mask", size, size, alpha=False, float_buffer=True)
    tn = tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tree.nodes.active = tn
    ob.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='EMIT', margin=12)
    mask = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(mask)
    mask = np.clip(mask.reshape(size, size, 4)[..., :1], 0.0, 1.0)
    ob.data.materials[0] = baked
    sc.cycles.samples = keep
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    lum = px[..., :3].mean(axis=-1, keepdims=True)
    px[..., :3] = np.clip(px[..., :3] + mask * PALE_LIFT * np.clip(PALE_TARGET - lum, 0.0, None), 0.0, 1.0)
    tex.pixels.foreach_set(px.ravel())
    tex.filepath_raw, tex.file_format = path, 'PNG'
    tex.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)


def bake(griffin, texture):
    """Everything that does not glow becomes one textured mesh, Griffin_Body: the feather and fur
    patterns and soft shading in the creases are baked into its colour image. The glowing parts are
    joined into one mesh, Griffin_GLOW, that keeps its emissive material. Roblox gets two MeshParts."""
    import bpy
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("BakeWorld")
    sc.world.light_settings.distance = AO_REACH        # crease shading only from shapes within this reach
    glow = [ob for ob in griffin.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in griffin.objects if ob not in glow], texture, name="Griffin_Body",
                            shade=0.48, soften=3, rough=0.85, uv_angle=85.0, uv_margin=0.004, pack_margin=0.003)
    lift_breast(body, texture)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = "Griffin_GLOW"
    griffin.objects = [body, g]


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
    ap.add_argument("--title", default="Griffin review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "griffin_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    griffin = build()
    print("triangles by part:", dict(sorted(griffin.tally.items(), key=lambda kv: -kv[1])))
    head = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.25, 0.02))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(griffin, samples=samples, focus=(head.x, head.y + 1.3, head.z - 1.7))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.62, -1.0, 0.16)).normalized() * 4.6, head + Vector((0, 0.3, -0.05)), 30)
        chest = Vector((-0.05, -1.75, 4.55))
        rig.cams["breast"] = review._camera("C_breast", chest + Vector((-0.5, -1.0, 0.25)).normalized() * 6.2, chest, 30)
        rig.cams["head"] = review._camera("C_head", head + Vector((-0.75, -1.0, 0.12)).normalized() * 3.0, head + Vector((0, 0.32, -0.08)), 30)
        coat = Vector((-0.95, 1.0, 3.05))
        rig.cams["coat"] = review._camera("C_coat", coat + Vector((-1.0, 0.12, 0.04)).normalized() * 5.2, coat, 42)
        paw = Vector((-0.9, -1.85, 0.35))
        rig.cams["feet"] = review._camera("C_feet", paw + Vector((-0.8, -1.0, 0.45)).normalized() * 3.6, paw, 34)
        tip = Vector((-0.88, 5.98, 2.0))
        rig.cams["tuft"] = review._camera("C_tuft", tip + Vector((-1.0, -0.55, 0.25)).normalized() * 4.2, tip, 34)
        flank = Vector((0.0, 1.0, 2.9))
        rig.cams["flank"] = review._camera("C_flank", flank + Vector((-1.0, 0.25, 0.3)).normalized() * 12.5, flank, 34)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(griffin, os.path.abspath(a.texture))
    tris = griffin.triangles()
    lo, hi = griffin.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = griffin.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(griffin.objects, os.path.abspath(a.export))
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
