"""Wolf pet: a noble shadow alpha wolf, a legendary pet. Rebuilt from a new design by script.

    python models/pets/wolf.py --review out/wolf.png      # render the review sheet
    python models/pets/wolf.py --export models/export/wolf.fbx

Style: a legendary creature beside the dragon, the phoenix and the griffin: heroic and calm like a
wolf on a shield, never cute, never creepy, never plastic. Must-haves, checked in every review:
  1. A proper wolf head: a long tapering wedge muzzle with a nose pad and a clear jaw line, a strong
     brow and cheek ruff, tall pointed ears with pale inner fur, glowing violet almond eyes without
     pupils under the brow, the mouth closed.
  2. An athletic body: deep chest, tucked waist, shoulder and haunch masses, real legs with elbow,
     wrist, hock and big padded paws, standing proud with the head up.
  3. A thick mane and ruff for a broad front outline, and a big full brush of a tail.
  4. Fur as large sculpted locks, varied and flowing back, on the ruff, shoulders, back, haunches
     and tail; smooth sculpted fur with painted strands elsewhere.
  5. Slate blue-grey on top, a silver-white ruff, chest and belly, a charcoal-indigo saddle, muzzle
     tip and paws; light enough to read at game distance. Dark crystals with a violet glow along
     the spine and shoulders.

Round 17: forked locks. The tail and the biggest locks of the mane split into two tips of unequal
length, so they read as clumps of hair and not as leaves or the scales of a pine cone; the tail
has fewer, larger clumps.

Round 16: the smooth fur no longer reads as plastic: besides the fine streaks, the coat between the
locks is painted with larger strokes of darker and lighter fur running down the body, and the
streaks are stronger. Pale fronts to the forelegs, as on a real wolf, break up the legs.

Round 15: the face again, which still looked sleepy from the front: the separate brow ridge sat on
the eye like a heavy lid, so the brow is now a soft ridge raised out of the skull, with the pale mark
between it and the eye. The eyes are a little more open, the chin is smaller and tucked (it read as a
pout), and the lip line slopes gently down to its corner so it does not read as a smile from the
front. The head turns less (10 degrees), so the long muzzle shows in the three-quarter views.

Round 14: more presence. The near foreleg steps forward and the head turns towards the viewer, so
the stance reads proud rather than parked. Bigger crystals with more of the violet showing, the
largest at the withers; a darker saddle so the back reads against the slate sides and silver ruff.

Round 13: fur and face that read up close. Stronger painted strands on the locks, darker roots
and frosted tips, the edges of each lock in shadow and no dark midrib (it made them read as leaves).
A clearer face mask: a dark bridge and muzzle tip over pale muzzle sides and cheeks. The brow lifted
clear of the eye. Longer, curving tail locks.

Round 12: a broader front outline and less regular fur. The mane and the tail are no longer rings
of locks (they read as pine cones) but a spiral scatter, the mane's lower side locks long and
flaring out over the shoulders; broader shoulders. Coarser painted strands that survive the bake, a
brighter silver ruff and a darker saddle; pale marks over the eyes; a crisper closed mouth.

Round 11: sturdier and more heroic. Shorter, much thicker legs on a wider stance with bigger paws
(the body is lowered and the chest deepened), a larger head, a thick neck under a mane of fewer,
longer locks of mixed widths that flare out at the sides, back locks that lie along the body
instead of standing up as spikes, a fuller tail. A muzzle without jowls and a brow lifted off the eye.

Round 10: the first build of the new design (v1 to v9 were the old shard-coat wolf).
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
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

HEAD_AT = Vector((-0.04, -3.24, 6.08))   # the middle of the skull, between the ears
HEAD_ROT = (-5, 2, -10)                  # muzzle a touch up (head held high), turned a little towards -X (the cameras)
HEAD_SIZE = 1.24
STEP = 0.45                              # how far the near (-X) foreleg steps forward
DROP = 0.32                              # everything is lowered by up to this much: shorter legs, a deeper chest
EYE_SLANT = 9.0                          # degrees the outer corner of the eye rises

# The trunk is one skin over these sections, from the rump to the point of the chest:
# centre x, y, z, then half width, height above the centre line (the back), depth below it, squareness.
BODY = [
    (0.00, 2.42, 3.96, 0.32, 0.28, 0.32, 2.0),    # 0  end of the rump, where the tail grows
    (0.00, 2.08, 3.94, 0.76, 0.52, 0.76, 2.1),    # 1  rump
    (0.00, 1.45, 3.92, 0.86, 0.58, 0.88, 2.2),    # 2  hips
    (0.00, 0.70, 3.94, 0.74, 0.46, 0.70, 2.2),    # 3  loins: the narrow waist, the belly tucked up
    (0.00, -0.05, 3.88, 0.88, 0.58, 1.08, 2.2),   # 4  back of the ribs
    (0.00, -0.80, 3.80, 1.08, 0.76, 1.42, 2.2),   # 5  ribcage, deep
    (0.00, -1.42, 3.84, 1.18, 0.84, 1.48, 2.15),  # 6  shoulders: withers at 4.68, brisket at 2.36
    (0.00, -2.00, 3.80, 0.98, 0.70, 1.26, 2.1),   # 7  chest, broad and pushed out
    (0.00, -2.42, 3.72, 0.50, 0.48, 0.62, 2.0),   # 8  the point of the chest
]
# The neck is a skin of its own, from inside the shoulders up into the head (the mane hides the join).
NECK = [
    (0.00, -1.60, 4.00, 0.92, 0.84, 0.96, 2.0),   # inside the shoulders
    (0.00, -2.22, 4.6, 0.86, 0.78, 0.9, 2.0),     # base of the neck, out of the chest
    (0.00, -2.66, 5.22, 0.7, 0.64, 0.7, 2.0),     # neck
]
NECK_TOP = [(0, 0.42, -0.24), (0.48, 0.44, 0.46, 2.0), (0, 0.18, -0.04), (0.30, 0.30, 0.26, 2.0)]   # in head space

# The head, one shell lofted along -Y, in its own space (muzzle towards -Y). For each section:
#   y, crown z, top half width, top edge z, side half width, side z, lip half width, lip z,
#   mouth groove depth, jaw half width, jaw z, chin z.
# The top plane, the sides and the jaw line are flat planes between the corners; the mouth is a
# groove just under the upper lip that fades out at its corner under the eye.
HEAD = [
    (0.55, 0.30, 0.20, 0.20, 0.34, -0.02, 0.32, -0.20, 0.000, 0.26, -0.40, -0.46),   # into the neck
    (0.32, 0.46, 0.26, 0.34, 0.47, 0.02, 0.42, -0.20, 0.000, 0.30, -0.42, -0.50),    # back of the skull
    (0.08, 0.52, 0.28, 0.40, 0.52, 0.04, 0.44, -0.18, 0.000, 0.30, -0.40, -0.48),    # crown: cheekbones widest
    (-0.18, 0.50, 0.25, 0.38, 0.42, 0.02, 0.33, -0.15, 0.000, 0.25, -0.33, -0.40),   # forehead, over the eyes
    (-0.40, 0.32, 0.17, 0.25, 0.27, -0.02, 0.235, -0.138, 0.014, 0.19, -0.25, -0.30),  # the stop, the mouth corner
    (-0.66, 0.25, 0.12, 0.18, 0.20, -0.03, 0.19, -0.128, 0.02, 0.155, -0.215, -0.255),  # bridge
    (-0.94, 0.19, 0.10, 0.13, 0.16, -0.04, 0.152, -0.118, 0.02, 0.118, -0.20, -0.23),  # muzzle
    (-1.14, 0.145, 0.085, 0.095, 0.13, -0.05, 0.12, -0.108, 0.012, 0.09, -0.178, -0.198),
    (-1.24, 0.07, 0.06, 0.03, 0.09, -0.06, 0.09, -0.10, 0.000, 0.06, -0.155, -0.172),  # the end of the muzzle
]

# Cross-sections, (side, up), going round.
P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.7, -0.2), (0, -0.8), (-0.7, -0.2)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]
# A sculpted lock of fur, rounded on top and a little lopsided, with a flat underside.
P_LOCK = [(-1.0, 0.0), (-0.45, 0.82), (0.42, 0.74), (1.0, 0.0), (0.0, -0.45)]
P_LOCK1 = [(-1.0, -0.1), (-0.5, 0.8), (0.5, 0.8), (1.0, -0.1), (0.0, -0.6)]
# Width of a lock along its length (0 root, 1 tip): full at the buried root, tapering to a point.
LOCKW = [(0, 1.0), (0.3, 0.9), (0.58, 0.62), (0.82, 0.3), (1, 0.0)]

# The coat, read from each vertex's colour position g: charcoal-indigo, saddle, slate blue-grey,
# light slate, silver, silver-white.
COAT = [(0.0, "#1C1F2E"), (0.14, "#272C40"), (0.26, "#353C57"), (0.42, "#535E78"), (0.55, "#69758E"),
        (0.7, "#99A2B6"), (0.84, "#D0D5DE"), (1.0, "#EEF0F4")]


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


LAYERS = ("g", "xn", "d", "f", "tip")


def _layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in LAYERS]


def paint(bm, g, feather=0.0):
    """Give every vertex of a shape the colour position g: a number, or a function of the vertex
    (its co and normal are up to date)."""
    lg, lx, ld, lf, lt = _layers(bm)
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
    it is (xn, -1 to 1), how far along it is in studs (d), whether it is a lock of fur (f) and how far
    along the lock it is (tip)."""
    C = Curve(points)
    bm = bmesh.new()
    lg, lx, ld, lf, lt = _layers(bm)
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
            v[lg], v[lx], v[ld], v[lf], v[lt] = gv, 0.0, C.L * t, fv, t * fv
            rings.append([v])
            continue
        prof = profile(t)
        wmax = max(abs(x) for x, _ in prof) or 1.0
        ring = []
        for x, y in prof:
            v = bm.verts.new(p + W * x + N * y)
            v[lg], v[lx], v[ld], v[lf], v[lt] = gv, x / wmax, C.L * t, fv, t * fv
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


def lock(root, D, N, L, W, rise=0.1, curl=0.0, flick=0.06, sink=0.07, thick=0.66, parted=True, n=5, g=(0.5, 0.56),
         widths=LOCKW):
    """One big sculpted lock of fur growing from `root` on a surface with normal N, flowing along D
    for L studs, W wide at its root. Its root is buried `sink` deep, so it grows out of the surface
    (or out from under the row before it); it rises off the surface by `rise` of its length, sways
    sideways by `curl` (an S-bend) and lifts its tip by `flick`."""
    N = Vector(N).normalized()
    D = Vector(D)
    D = (D - N * D.dot(N)).normalized()
    S = D.cross(N).normalized()
    pts = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        h = -sink + (sink + rise * L) * (1 - (1 - t) ** 2) + flick * L * t ** 3
        sway = curl * L * (math.sin(math.pi * t) * -0.35 + t * t)
        pts.append(Vector(root) + D * L * t + N * h + S * sway)
    shape = P_LOCK if parted else P_LOCK1

    def prof(t):
        w = max(W * _table(widths, t), 0.004)
        h = max(W * thick * _table(widths, t) ** 0.7, 0.003)
        return [(a * w, b * h) for a, b in shape]
    return loft(pts, n, prof, up=N, g=g, feather=True, tip=True)


def forked(root, D, N, L, W, split=0.42, fork_len=0.8, **kw):
    """A lock that splits into two tips of unequal length: two narrower locks from one root, their
    tips drifting apart sideways by `split` of the width. Reads as a clump of hair, not a leaf."""
    N = Vector(N).normalized()
    D = Vector(D)
    D = (D - N * D.dot(N)).normalized()
    S = D.cross(N).normalized()
    a = lock(Vector(root) + S * W * 0.22, D + S * split * W / L, N, L, W * 0.62, **kw)
    kw = dict(kw)
    kw["curl"] = -kw.get("curl", 0.0) * 0.6
    b = lock(Vector(root) - S * W * 0.22, D - S * split * W / L, N, L * fork_len, W * 0.6, **kw)
    tmp = bpy_mesh_join(a, b)
    return tmp


def bpy_mesh_join(a, b):
    """Two bmeshes as one (uses both up)."""
    import bpy
    me = bpy.data.meshes.new("tmp")
    b.to_mesh(me)
    b.free()
    a.from_mesh(me)
    bpy.data.meshes.remove(me)
    return a


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


def sheath(h, r, sides=6, sink=0.12, top=0.52):
    """The dark body of a crystal: straight faceted sides up to `top` of its height, then bevelled
    in to a flat top that the glowing point grows out of."""
    bm = bmesh.new()
    rings = []
    for z, k in ((-sink, 0.92), (h * top * 0.82, 1.0), (h * top, 0.8)):
        rings.append([bm.verts.new((r * k * math.cos(2 * math.pi * j / sides), r * k * math.sin(2 * math.pi * j / sides), z))
                      for j in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def crystal(h, r, sides=6, rot=0.0, base=0.0, shoulder=0.6, lean=0.0):
    """A pointed crystal standing on +Z: straight faceted sides from z=base up to `shoulder` of its
    height, then a faceted point (pushed `lean` along X, so it is not a perfect pyramid)."""
    bm = bmesh.new()
    rings = []
    for z, k in ((base, 0.95), (h * shoulder, 1.0)):
        rings.append([bm.verts.new((r * k * math.cos(math.radians(rot + 360.0 * j / sides)),
                                    r * k * math.sin(math.radians(rot + 360.0 * j / sides)), z)) for j in range(sides)])
    apex = bm.verts.new((lean * r, 0.0, h))
    a, b = rings
    for j in range(sides):
        bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        bm.faces.new((b[j], b[(j + 1) % sides], apex))
    bm.faces.new(a[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def shell(sections, corners, per=3, back_cap=0.0, nose_cap=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives the outline of one
    section as (x, z) points going round."""
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


def head_corners(sec):
    """The outline of one head section, going round from the crown: the top plane, the brow or
    bridge edge, the side, the upper lip, the mouth groove, the lower lip, the jaw line, the chin."""
    y, zt, wt, zt2, ws, zs, wl, zl, nd, wj, zj, zb = sec
    dome = 0.22 * wt
    half = [(0.5 * wt, zt + dome * 0.78), (wt, zt2), (ws, zs), (wl, zl), (wl - nd, zl - 0.014),
            (wl - 0.008 - 0.3 * nd, zl - 0.03), (wj, zj), (0.5 * wj, zb + 0.3 * (zj - zb))]
    return [(0.0, zt + dome)] + half + [(0.0, zb)] + [(-x, z) for x, z in reversed(half)]


class Surface:
    """Finds points exactly on one or more meshes, so that details sit on them and neither float nor sink."""

    def __init__(self, *bms):
        verts, polys = [], []
        for bm in bms:
            off = len(verts)
            bm.verts.index_update()
            verts += [v.co.copy() for v in bm.verts]
            polys += [[off + v.index for v in f.verts] for f in bm.faces]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def hit(self, origin, direction, out=0.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            loc, nrm, _, _ = self.bvh.find_nearest(Vector(origin))
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
        _layers(bm)
        loops = []
        for s in ss:
            loops.append([bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)])
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
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
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
    return new, link, attr, op, remap, ramp


def coat_material(name, stops, streak, strands=5.0, strand_amt=0.14, rough=0.9, top_light=0.1, tip_light=0.16, strokes=0.0):
    """Painted fur: a colour ramp read from each vertex's colour position g with kit.furry's fine
    streaks over it. On a lock (f = 1) the strands run along the lock instead: light and dark lines
    across its width, darker down the parting and at the edges, paler towards the tip. Fur facing up
    catches a little cool light, so the forms still read on the darker coat from far away."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **streak)
    tree = m.node_tree
    new, link, attr, op, remap, ramp = _node_ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    old = hsv.inputs["Value"].links[0].from_socket
    g, xn, f, tp, d = attr("g"), attr("xn"), attr("f"), attr("tip"), attr("d")
    # on a lock, g rises a little towards the tip: a lighter, frosted end to each clump
    gl = op('ADD', g, op('MULTIPLY', remap(tp, 0.35, 1.0, 0.0, tip_light, smooth=True), f))
    link(ramp(gl, stops), hsv.inputs["Color"])
    # strands along the lock, wavering a little along its length
    wav = op('MULTIPLY_ADD', op('SINE', op('MULTIPLY', d, 7.0)), 0.06, xn)
    lines = op('MULTIPLY_ADD', op('SINE', op('MULTIPLY', wav, strands * math.pi)), strand_amt, 1.0)
    ax = op('ABSOLUTE', xn)
    edge = remap(ax, 0.5, 1.0, 1.0, 0.68, smooth=True)
    spine = remap(ax, 0.0, 0.35, 1.07, 1.0, smooth=True)
    root = remap(tp, 0.0, 0.4, 0.74, 1.0, smooth=True)
    pattern = op('MULTIPLY', op('MULTIPLY', op('MULTIPLY', lines, edge), spine), root)
    on_lock = op('MULTIPLY_ADD', op('SUBTRACT', pattern, 1.0), f, 1.0)
    # the skin keeps kit.furry's streaks at full strength, a lock only a little of them
    streaky = op('MULTIPLY_ADD', op('SUBTRACT', old, 1.0), op('SUBTRACT', 1.0, op('MULTIPLY', f, 0.6)), 1.0)
    value = op('MULTIPLY', streaky, on_lock)
    if strokes:
        # larger painted strokes of fur on the smooth coat between the locks: long, soft, darker and
        # lighter bands that run down the body, wavering, so it reads as sculpted fur and not as plastic
        coord = new("ShaderNodeTexCoord")
        warp = new("ShaderNodeTexNoise")
        warp.inputs["Scale"].default_value, warp.inputs["Detail"].default_value = 0.9, 1.0
        link(coord.outputs["Object"], warp.inputs["Vector"])
        mix = new("ShaderNodeMix")
        mix.data_type = 'VECTOR'
        mix.inputs[0].default_value = 0.35
        link(coord.outputs["Object"], mix.inputs[4])
        link(warp.outputs["Color"], mix.inputs[5])
        stretch = new("ShaderNodeMapping")
        stretch.inputs["Scale"].default_value = (4.0, 4.0, 1.0)
        link(mix.outputs[1], stretch.inputs["Vector"])
        band = new("ShaderNodeTexNoise")
        band.inputs["Scale"].default_value, band.inputs["Detail"].default_value = 1.0, 3.0
        link(stretch.outputs["Vector"], band.inputs["Vector"])
        stroke = remap(band.outputs[0], 0.43, 0.6, 1.0 - strokes, 1.0 + 0.5 * strokes, smooth=True)
        value = op('MULTIPLY', value, op('MULTIPLY_ADD', op('SUBTRACT', stroke, 1.0), op('SUBTRACT', 1.0, f), 1.0))
    geo = new("ShaderNodeNewGeometry")
    sep = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])
    value = op('MULTIPLY', value, op('ADD', 1.0, remap(sep.outputs[2], 0.2, 0.95, 0.0, top_light, smooth=True)))
    link(value, hsv.inputs["Value"])
    return m


def ramp_material(name, stops, rough=0.5, streak=None):
    """A hard surface (claws, nose, crystals): a ramp read from g with a faint mottle."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **(streak or dict(strength=0.05, mottle=0.06, fine=40.0, length=2.0)))
    tree = m.node_tree
    new, link, attr, op, remap, ramp = _node_ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    link(ramp(attr("g"), stops), hsv.inputs["Color"])
    return m


def coat_g(p, n):
    """The colour position of the coat at world point p with normal n: a charcoal-indigo saddle on
    the back, slate blue-grey sides, a silver-white chest, throat and belly."""
    up = n.z
    saddle = smooth(up, 0.0, 0.6) * smooth(p.y, -2.2, -1.3) * smooth(p.y, 2.7, 1.9) * smooth(p.z, 3.5, 4.1)
    under = smooth(up, -0.1, -0.6) * smooth(p.z, 3.9, 3.2)
    chest = smooth(p.y, -1.75, -2.35) * smooth(-n.y, -0.1, 0.45) * smooth(p.z, 5.6, 4.9)
    g = 0.5 + 0.06 * smooth(up, 0.2, -0.4)
    g = lerp(g, 0.14, saddle)
    return lerp(g, 0.86, max(under, chest))




# ---- the wolf ---------------------------------------------------------------------------------------

def _ball_at(size, loc, rot=(0, 0, 0), cuts=2):
    bm = kit.ball(size, cuts=cuts)
    bm.transform(M(loc, rot=rot))
    return bm


def head_shell():
    """The head as one shell, painted as it is made: a slate crown and bridge going charcoal-indigo
    at the nose, silver-white lips, cheeks, jaw and chin, a dark lip line down the mouth groove."""
    k = len(HEAD) - 1
    per = 3
    rings = []
    for i in range(k * per + 1):
        sec = [_cr([s[j] for s in HEAD], i / per) for j in range(len(HEAD[0]))]
        rings.append((sec[0], head_corners(sec)))
    bm = bmesh.new()
    lg = _layers(bm)[0]
    loops = []
    for y, pts in rings:
        mz = smooth(y, -0.36, -0.62)                     # 1 on the muzzle
        tipdark = smooth(y, -0.8, -1.22)
        top = lerp(0.34, lerp(0.26, 0.08, tipdark), mz)
        mouth = smooth(y, -0.36, -0.46)                  # the lip line runs from the nose to below the front of the eye
        # outline index: 0 crown, 1 top, 2 brow/bridge edge, 3 side, 4 lip, 5 groove, 6 lower lip, 7 jaw, 8 under, 9 chin
        gs = [top, top, lerp(0.4, top + 0.06, mz), lerp(0.56, 0.8, mz), lerp(0.84, 0.9, mz),
              lerp(0.8, 0.07, mouth), lerp(0.82, 0.66, mz), 0.86, 0.9, 0.9]
        half = len(pts) // 2
        loop = []
        for j, (x, z) in enumerate(pts):
            jj = j if j <= half else len(pts) - j
            v = bm.verts.new((x, y, z))
            v[lg] = gs[jj]
            loop.append(v)
        loops.append(loop)
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    for ring, dy in ((loops[0], -0.05), (loops[-1], 0.012)):
        c = sum((v.co for v in ring), Vector()) / n
        tip = bm.verts.new((c.x, c.y - dy, c.z))
        tip[lg] = sum(v[lg] for v in ring) / n
        for j in range(n):
            bm.faces.new((ring[j], ring[(j + 1) % n], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # the lower jaw ends behind the nose: below the lip line the front of the muzzle is pulled back
    for v in bm.verts:
        x, y, z = v.co
        below = smooth(z, -0.11, -0.16)
        fr = smooth(y, -0.85, -1.25)
        v.co.y += 0.14 * below * fr
        v.co.z += 0.035 * below * fr
        v.co.x *= 1.0 - 0.3 * below * fr
    # the brow: a soft ridge raised out of the skull along the edge of the forehead, from the stop to the
    # temple (a separate ridge on top read as a heavy eyelid and made the wolf look sleepy)
    bm.normal_update()
    for v in bm.verts:
        for sx in (-1, 1):
            a, b = Vector((0.07 * sx, -0.46, 0.3)), Vector((0.37 * sx, -0.04, 0.41))
            ab = b - a
            t = min(max((v.co - a).dot(ab) / ab.length_squared, 0.0), 1.0)
            d = (v.co - (a + ab * t)).length
            if d < 0.09:
                v.co += v.normal * 0.034 * smooth(d, 0.09, 0.0) * math.sin(math.pi * (0.15 + 0.85 * t)) ** 0.6
    # pale marks over the eyes, as on a real wolf: they lift the face and make the brow read
    for v in bm.verts:
        x, y, z = v.co
        w = math.exp(-(((abs(x) - 0.2) / 0.1) ** 2 + ((y + 0.2) / 0.11) ** 2 + ((z - 0.38) / 0.1) ** 2))
        v[lg] = lerp(v[lg], 0.8, min(1.0, 1.3 * w))
    return bm


def build():
    coat = coat_material("Coat", COAT, dict(strength=0.46, mottle=0.1, fine=7.0, length=4.5), strands=3.0, strand_amt=0.3,
                         tip_light=0.22, strokes=0.42)
    facem = coat_material("Face", COAT, dict(strength=0.22, mottle=0.025, fine=12.0, length=4.0), strands=3.0, strand_amt=0.22,
                          top_light=0.06, tip_light=0.1, strokes=0.12)
    pawm = coat_material("Paw", COAT, dict(strength=0.18, mottle=0.06, fine=20.0, length=3.0), top_light=0.04)
    claw = ramp_material("Claw", [(0.0, "#2E2E3A"), (0.6, "#17171E"), (1.0, "#0B0B10")], rough=0.45)
    nosem = ramp_material("Nose", [(0.0, "#08080C"), (0.5, "#1E202B"), (1.0, "#3A3E52")], rough=0.4)
    crystm = ramp_material("Crystal", [(0.0, "#100E1C"), (0.55, "#1F1A38"), (1.0, "#3C3274")], rough=0.3)
    glow = kit.material("GLOW_Violet", "#6A30FF", rough=0.4, emit=1.6)

    wolf = Prop("Wolf")
    wolf.tally = {}

    def add(part, bm, mat, at=None, crease=None):
        _layers(bm)
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            v.co.z -= DROP * smooth(v.co.z, 0.0, 3.9)
            if v.co.z < 0.0:
                v.co.z = 0.0
        if crease:
            sharpen(bm, crease)
        wolf.tally[part] = wolf.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        wolf.add(bm, mat)

    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)

    def hs(p):
        return tuple(H @ Vector(p))

    def gpaint(bm, fn=None):
        """Paint a shape that is already in place from coat_g (or fn) at each vertex."""
        bm.normal_update()
        lg = _layers(bm)[0]
        for v in bm.verts:
            v[lg] = (fn or coat_g)(v.co, v.normal)
        return bm

    # ---- trunk and neck: two skins ---------------------------------------------------------------------
    skin = Skin(BODY)
    add("skin", gpaint(skin.mesh(segs=20)), coat)
    neck = Skin(NECK + [(*hs(NECK_TOP[0]), *NECK_TOP[1]), (*hs(NECK_TOP[2]), *NECK_TOP[3])])
    add("skin", gpaint(neck.mesh(segs=16)), coat)

    def on_skin(idx, th, L, W, back=1.0, down=0.0, out=0.0, g=None, on=None, fork=False, **kw):
        """A lock growing from the skin (or the neck, `on`) at section index idx and angle th, flowing
        back (towards the rump), down and out by the given amounts."""
        skin_ = on or skin
        s = skin_.s_of(idx)
        p, N = skin_.bare(s, th), skin_.normal(s, th)
        T = skin_.at(s)[1]
        side = Vector((math.copysign(1.0, p.x) if abs(p.x) > 1e-3 else 0.0, 0, 0))
        D = -T * back + Vector((0, 0, -down)) + side * out
        if g is None:
            g0 = coat_g(p, N)
            g = (g0, g0 + 0.03)
        elif not isinstance(g, tuple):
            g = (g, g + 0.03)
        return (forked if fork else lock)(p, D, N, L, W * (1.25 if fork else 1.0), g=g, **kw)

    # ---- muscle under the fur: shoulder blades and haunches ------------------------------------------------
    for sx in (-1, 1):
        add("muscle", gpaint(_ball_at((0.46, 0.9, 1.3), (0.64 * sx, -1.4, 3.86), (-26, 0, 0))), coat)
        add("muscle", gpaint(_ball_at((0.56, 1.28, 1.36), (0.64 * sx, 1.42, 3.5), (-16, 0, 0))), coat)

    # ---- legs: elbow, wrist, hock, big padded paws ---------------------------------------------------------
    def leg_g(sx, fore=False):
        def fn(p, n):
            inner = smooth(-n.x * sx, 0.1, 0.7)
            if fore:
                inner = max(inner, smooth(-n.y, 0.3, 0.8) * smooth(p.z, 2.6, 2.0))
            g = lerp(0.5, 0.8, inner)
            g = lerp(coat_g(p, n), g, smooth(p.z, 2.9, 2.3))
            return lerp(g, 0.16, smooth(p.z, 0.8, 0.32))     # dark charcoal-indigo socks
        return fn

    def paw(at, sx, size):
        F = M(at, scale=size)
        add("paws", paint(_ball_at((0.46, 0.52, 0.3), (0, 0.03, 0.15)), 0.18), pawm, F)
        for ox, oy in ((-0.2, -0.16), (-0.075, -0.22), (0.075, -0.22), (0.2, -0.16)):
            add("paws", paint(_ball_at((0.155, 0.2, 0.17), (ox, oy, 0.085), cuts=1), 0.12), pawm, F)
            c = [(ox, oy - 0.08, 0.1), (ox, oy - 0.15, 0.08), (ox, oy - 0.19, 0.0)]
            add("claws", loft(c, 3, fixed([0.035, 0.024, 0.004], P_CLAW), up=(0, -0.3, 1), g=(0.2, 1.0), tip=True), claw, F,
                crease=50)

    for sx in (-1, 1):
        # foreleg: shoulder, the elbow back at the brisket, a straight forearm, the wrist, a sloped pastern
        step = STEP if sx < 0 else 0.0
        fore = [(0.64 * sx, -1.38, 3.55), (0.72 * sx, -1.18 - 0.16 * step, 2.62), (0.76 * sx, -1.28 - 0.3 * step, 2.2),
                (0.79 * sx, -1.38 - 0.5 * step, 1.6), (0.83 * sx, -1.46 - 0.78 * step, 0.8), (0.85 * sx, -1.55 - 0.9 * step, 0.5),
                (0.87 * sx, -1.68 - step, 0.24)]
        add("legs", gpaint(limb(fore, [(0.52, 0.68), (0.42, 0.55), (0.38, 0.47), (0.31, 0.36), (0.28, 0.31), (0.25, 0.27), (0.27, 0.29)],
                                P_LEG, 20, up=(0, -1, 0)), leg_g(sx, True)), coat)
        add("legs", gpaint(_ball_at((0.24, 0.28, 0.34), (0.72 * sx, -0.94 - 0.16 * step, 2.62), cuts=1), leg_g(sx)), coat)  # elbow
        add("legs", gpaint(_ball_at((0.2, 0.18, 0.22), (0.83 * sx, -1.26 - 0.78 * step, 0.84), cuts=1), leg_g(sx)), coat)  # wrist pad
        paw(Vector((0.87 * sx, -1.78 - step, 0.0)), sx, 1.26)
        # hind leg: haunch, the stifle forward, the hock high and back, a near-upright rear pastern
        hind = [(0.6 * sx, 1.55, 3.75), (0.76 * sx, 1.25, 3.05), (0.83 * sx, 0.98, 2.4), (0.86 * sx, 1.35, 1.85),
                (0.89 * sx, 1.84, 1.25), (0.9 * sx, 1.76, 0.55), (0.9 * sx, 1.68, 0.24)]
        add("legs", gpaint(limb(hind, [(0.6, 0.98), (0.56, 0.88), (0.4, 0.52), (0.35, 0.47), (0.25, 0.33), (0.23, 0.25), (0.26, 0.28)],
                                P_LEG, 22, up=(0, -1, 0)), leg_g(sx)), coat)
        add("legs", gpaint(_ball_at((0.22, 0.26, 0.32), (0.89 * sx, 2.08, 1.33), cuts=1), leg_g(sx)), coat)        # point of the hock
        FC, HC = Curve(fore), Curve(hind)
        for t, L, W, ang in ((0.3, 0.55, 0.22, 0), (0.38, 0.5, 0.2, 35), (0.5, 0.42, 0.17, -30)):
            c = FC.at(t)
            rad = Vector((math.sin(math.radians(ang)) * sx, 1.0, 0.0)).normalized()
            add("leg fur", lock(c + rad * 0.25, Vector((0, 0.5, -1.0)), rad, L, W, rise=0.12, flick=0.1, g=(0.5, 0.54), n=4,
                                parted=False), coat)
        for t, L, W, ang in ((0.1, 0.75, 0.28, 60), (0.17, 0.7, 0.26, 10), (0.28, 0.6, 0.24, 40), (0.36, 0.5, 0.2, -10)):
            c = HC.at(t)
            rad = Vector((math.cos(math.radians(ang)) * sx, math.sin(math.radians(ang)), 0.0)).normalized()
            add("leg fur", lock(c + rad * 0.36, Vector((0, 0.6, -1.0)), rad, L, W, rise=0.1, flick=0.04,
                                g=(0.5 + 0.2 * smooth(ang, 30, -10), 0.56), n=4), coat)
        paw(Vector((0.9 * sx, 1.6, 0.0)), sx, 1.18)

    # ---- tail: a big full brush, held low and out, curving at the end ------------------------------------
    tail = [(0, 2.36, 3.98), (0, 2.8, 3.98), (0, 3.32, 3.72), (0, 3.78, 3.16), (0, 4.08, 2.48), (0, 4.22, 1.88)]
    TC = Curve(tail)
    add("tail", gpaint(loft(tail, 16, fixed([0.34, 0.54, 0.62, 0.56, 0.4, 0.12], round_shape(10)), up=(0, 0, 1)),
                       lambda p, n: lerp(lerp(0.3, 0.78, smooth(n.z, 0.1, -0.6)), 0.14, smooth(p.y, 3.9, 4.35))), coat)

    def tail_lock(t, ang, L, W, out=0.35, g=None, fl=0.0, fork=False):
        c, T = TC.at(t), TC.tangent(t)
        X = Vector((1, 0, 0))
        Y = T.cross(X).normalized()
        rad = X * math.cos(ang) + Y * math.sin(ang)
        r = _table([(0, 0.34), (0.2, 0.54), (0.45, 0.62), (0.7, 0.54), (1, 0.16)], t)
        up = rad.z
        gg = lerp(0.3, 0.78, smooth(up, 0.2, -0.6))
        gg = lerp(gg, 0.14, smooth(t, 0.7, 0.98)) if g is None else g
        return (forked if fork else lock)(c + rad * r * 0.85, T + rad * out, rad, L, W, rise=0.0, flick=fl,
                                          curl=0.25 * math.sin(2 * ang + 1.0), g=(gg, gg + 0.04), n=5)

    count = 17
    for i in range(count):
        t = lerp(0.05, 0.72, (i + 0.5) / count)
        ang = math.radians(137.508 * i + 20.0)
        L = (1.2 + 0.25 * math.sin(math.pi * min(t / 0.7, 1.0))) * (1 + 0.14 * math.sin(i * 2.3))
        add("tail", tail_lock(t, ang, L, 0.5 + 0.12 * (0.5 + 0.5 * math.sin(i * 1.7)), out=0.04, fl=-0.03, fork=True), coat)
    for j in range(5):                                                     # the tip: a closing brush of dark locks
        ang = 2 * math.pi * j / 5
        add("tail", tail_lock(0.84, ang, 0.7, 0.26, out=0.0, g=0.12 + 0.03 * (j % 2)), coat)

    # ---- the mane: four rings of big locks round the neck, silver-white in front, slate behind ---------------
    count = 34
    for i in range(count):
        f = (i + 0.5) / count                                   # 0 behind the head, 1 at the shoulders
        idx = lerp(2.8, 1.1, f)
        th = 90.0 + 137.508 * i
        side = abs(math.cos(math.radians(th)))
        front = smooth(math.sin(math.radians(th)), 0.35, -0.6)
        gm = lerp(0.36, 0.84, front) + 0.04 * (i % 2)
        L = lerp(0.8, 1.35, f) * (1 + 0.16 * math.sin(i * 1.9)) * lerp(1.0, 0.8, front) * (1 + 0.3 * side * f)
        W = L * (0.26 + 0.08 * (0.5 + 0.5 * math.sin(i * 2.9)))
        add("mane", on_skin(idx, th, L, W, back=1.0, down=0.5 * side, out=(0.4 + 0.8 * f) * side, g=gm, on=neck,
                            rise=0.03 + 0.28 * side * f, flick=0.02 + 0.14 * side, curl=0.3 * math.sin(i * 2.7), n=5,
                            fork=L > 1.05), coat)
    # the chest: a silver-white bib of locks flowing down
    for k, idx in enumerate((7.7, 7.15, 6.6)):
        for j in range(3):
            th = -90.0 + (j - 1.0 + 0.5 * (k % 2)) * 30.0
            add("bib", on_skin(idx, th, 0.95 - 0.1 * k, 0.32, back=0.7, down=1.0, g=0.82 + 0.03 * (j % 2), rise=0.04,
                               flick=0.05, curl=0.25 * math.sin(j * 1.7 + k), n=5), coat)
    # shoulders, back line, haunches and belly: locks flowing back, varied in size
    for sx in (-1, 1):
        for idx, th, L, W in ((6.4, 40, 0.8, 0.28), (6.0, 18, 0.75, 0.26), (5.7, 45, 0.7, 0.25), (5.5, 0, 0.65, 0.24)):
            thh = th if sx > 0 else 180 - th
            add("shoulders", on_skin(idx, thh, L, W, back=1.0, down=0.6, rise=0.03, flick=-0.03, curl=0.14 * sx), coat)
        for idx, L in ((6.0, 0.7), (5.25, 0.68), (4.5, 0.64), (3.75, 0.6), (3.0, 0.62), (2.3, 0.66)):
            th = 90 - 24 * sx
            add("back", on_skin(idx, th, L, 0.28, back=1.0, down=0.5, rise=0.0, flick=-0.1, sink=0.05, curl=0.12 * sx), coat)
        for idx, th, L, W in ((2.0, 30, 0.75, 0.27), (1.55, 10, 0.8, 0.28), (1.2, 40, 0.65, 0.24)):
            thh = th if sx > 0 else 180 - th
            add("haunches", on_skin(idx, thh, L, W, back=1.0, down=0.6, rise=0.05, flick=-0.02), coat)
        for idx, L in ((5.8, 0.7), (5.1, 0.62), (4.4, 0.55)):
            th = -90 + 34 * sx
            add("belly", on_skin(idx, th, L, 0.22, back=1.0, down=0.7, rise=0.1, g=0.84, parted=False, n=4), coat)

    # ---- crystals: a line of dark crystals with violet glowing points along the spine and shoulders --------
    def grow(p, axis, h, r, hint):
        F = frame(p, axis, hint)
        add("crystals", paint(sheath(h, r), lambda v, h=h: 0.2 + 0.8 * max(v.co.z, 0.0) / h), crystm, F, crease=25)
        add("glow", crystal(h, r * 0.74, rot=30.0, base=h * 0.28, shoulder=0.66, lean=0.15), glow, F)

    for k, (idx, h, r) in enumerate(((6.15, 1.45, 0.21), (5.45, 1.18, 0.18), (4.75, 0.92, 0.155), (4.05, 0.7, 0.13), (3.35, 0.5, 0.1))):
        s = skin.s_of(idx)
        p, n, t = skin.bare(s, 90.0), skin.normal(s, 90.0), skin.at(s)[1]
        grow(p - n * 0.02, (n * 0.9 - t * 0.45).normalized(), h, r, -t)
        sx = 1 if k % 2 == 0 else -1
        th = 90 - 20 * sx
        p2, n2 = skin.bare(s - 0.12, th), skin.normal(s - 0.12, th)
        grow(p2 - n2 * 0.02, (n2 * 0.9 - t * 0.4).normalized(), h * 0.55, r * 0.75, -t)
    for sx in (-1, 1):
        s = skin.s_of(6.05)
        th = 90 - 52 * sx
        p, n, t = skin.bare(s, th), skin.normal(s, th), skin.at(s)[1]
        grow(p - n * 0.02, (n - t * 0.4).normalized(), 0.8, 0.14, -t)
        p, n = skin.bare(s - 0.3, th - 10 * sx), skin.normal(s - 0.3, th - 10 * sx)
        grow(p - n * 0.02, (n - t * 0.5).normalized(), 0.5, 0.1, -t)

    # ---- head: placed in its own space, then turned as one -------------------------------------------
    head = head_shell()
    surf = Surface(head)
    eyes = []
    for sx in (-1, 1):
        # each eye sits in a small flat socket facing forward and out, so it lies flush and looks ahead
        p, _ = surf.hit((0.95 * sx, -0.7, 0.2), Vector((0.28 * sx, -0.28, 0.125)) - Vector((0.95 * sx, -0.7, 0.2)))
        out = Vector((0.64 * sx, -0.74, 0.14)).normalized()
        eyes.append((sx, p, out))
        for v in head.verts:
            d = (v.co - p).length
            if d < 0.27:
                w = smooth(d, 0.27, 0.12)
                v.co -= out * ((v.co - p).dot(out) + 0.012) * w * 0.9
    head.normal_update()
    surf = Surface(head)
    add("head", head, facem, H, crease=50)

    # the nose pad: broad, angular, overhanging the end of the muzzle
    nose = rounded_box((0.22, 0.2, 0.13), n=3.4, cuts=3)
    for v in nose.verts:
        x, y, z = v.co
        v.co.x *= 1.0 - 0.32 * smooth(z, 0.03, -0.065)                # narrower underneath
        v.co.y -= 0.035 * smooth(z, -0.05, 0.05)                       # the top juts forward, the underside tucks back
        v.co.z -= 0.03 * smooth(y, -0.04, 0.1)                         # the back sinks into the bridge
    add("nose", paint(nose, 0.55), nosem, H @ M((0, -1.2, 0.085), rot=(-8, 0, 0)), crease=40)
    for sx in (-1, 1):
        nostril = [(-0.5, 0.0), (-0.2, 0.35), (0.3, 0.3), (0.5, -0.1), (0.0, -0.3)]
        add("nose", paint(lens(nostril, 0.03), 0.0), nosem,
            H @ facing(Vector((0.058 * sx, -1.302, 0.07)), Vector((0.55 * sx, -1.0, 0.0)), Vector((sx, 0.3, 0.5))) @ M(scale=(0.06, 1, 0.05)))

    for sx in (-1, 1):
        # the eye: a glowing violet almond, slanted up towards the ear, under the brow
        # It is turned by hand, facing forward and out, so that from the front the outer corner is the
        # higher one (on the sloping surface it would droop and look sad).
        _, p, out = eyes[(sx + 1) // 2]
        flat = Vector((0.74 * sx, 0.64, 0.0))
        along = flat * math.cos(math.radians(EYE_SLANT)) + Vector((0, 0, 1)) * math.sin(math.radians(EYE_SLANT))
        eye = [(-0.54, -0.03), (-0.36, 0.07), (-0.12, 0.16), (0.14, 0.2), (0.38, 0.16), (0.6, 0.05), (0.38, -0.04), (0.12, -0.09),
               (-0.14, -0.1), (-0.38, -0.07)]
        add("eyes", lens([(a * 0.3, b * 0.56) for a, b in eye], 0.022, rows=((0.7, 0.9), (1.0, 0.0)), centre=(0.0, 0.03)),
            glow, H @ facing(p, out, along))
        # a dark rim round the eye, a little longer at the corners
        rim = [(-0.66, -0.05), (-0.42, 0.11), (-0.14, 0.22), (0.14, 0.27), (0.42, 0.22), (0.74, 0.07), (0.42, -0.08), (0.12, -0.14),
               (-0.16, -0.16), (-0.42, -0.12)]
        add("eyes", paint(lens([(a * 0.3, b * 0.56) for a, b in rim], 0.03), 0.1), nosem, H @ facing(p - out * 0.016, out, along))
        # ears: tall, pointed, cupped forward and a little out, pale fur inside
        def ear_prof(t):
            w = 0.22 * (1 - t) ** 0.8 + 0.005
            d = 0.13 * (1 - 0.7 * t) + 0.012
            return [(0, -d * 0.55), (0.6 * w, -d * 0.4), (w, d * 0.1), (0.55 * w, d * 0.28), (0, d * 0.02),
                    (-0.55 * w, d * 0.28), (-w, d * 0.1), (-0.6 * w, -d * 0.4)]
        a = math.radians(22)
        ear = loft([(0.23 * sx, 0.14, 0.36), (0.29 * sx, 0.2, 0.68), (0.37 * sx, 0.27, 1.0)], 8, ear_prof,
                   side=(math.cos(a), math.sin(a) * sx, 0), g=(0.36, 0.2), tip=True)
        ear.normal_update()
        lg = _layers(ear)[0]
        fwd = Vector((math.sin(a) * sx, -math.cos(a), 0))
        for v in ear.verts:
            if v.normal.dot(fwd) > 0.35 and v.co.z < 0.92:
                v[lg] = lerp(0.84, v[lg], smooth(v.co.z, 0.66, 0.92))
        add("ears", ear, facem, H, crease=45)
        for ox, L in ((-0.05, 0.26), (0.03, 0.22)):
            base = Vector(((0.25 + ox) * sx, 0.1, 0.42))
            add("ears", lock(base, Vector((0.14 * sx, 0.1, 1.0)), fwd, L, 0.08, rise=0.05, sink=0.02, flick=0.02, parted=False, n=4,
                             g=(0.86, 0.9)), facem, H)
        # cheek ruff: two layers of locks sweeping back, out and down from behind the eye, framing the face
        for layer, (y0, L, W, cnt) in enumerate(((-0.08, 0.5, 0.2, 4), (0.12, 0.72, 0.24, 5))):
            for j in range(cnt):
                f = j / (cnt - 1)
                z = lerp(0.1, -0.4, f)
                q, qn = surf.hit((0.9 * sx, y0 + 0.12 * f, z), (-sx, 0, 0))
                D = Vector((1.0 * sx, 0.75, -0.25 - 0.6 * f))
                gg = lerp(0.5, 0.84, smooth(f, 0.0, 0.55))
                add("ruff", lock(q, D, qn, L * (1 + 0.15 * math.sin(j * 2.1 + layer)), W, rise=0.12, sink=0.05, flick=0.14,
                                 curl=0.15 * sx * (1 if j % 2 else -1), g=(gg, gg + 0.04), n=5), facem, H)
    # a few locks over the crown and the nape, flowing back into the mane
    for x, y, L in ((0.0, 0.08, 0.5), (-0.13, 0.22, 0.45), (0.13, 0.22, 0.45)):
        q, qn = surf.hit((x, y, 1.5), (0, 0, -1))
        add("crown", lock(q, Vector((0.3 * x, 1.0, -0.3)), qn, L, 0.15, rise=0.15, sink=0.04, g=(0.4, 0.44), n=4), facem, H)

    wolf.build()
    for ob in wolf.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    wolf.withers = skin.bare(skin.s_of(6.0), 90.0).z
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
    ap.add_argument("--views", default="front 3/4,face,side,game distance",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Wolf review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "wolf_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    wolf = build()
    print("triangles by part:", dict(sorted(wolf.tally.items(), key=lambda kv: -kv[1])))
    head = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.4, 0.1))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(wolf, samples=samples, focus=(head.x, head.y + 1.4, head.z - 1.6))
        turn = Matrix.Rotation(math.radians(HEAD_ROT[2]), 3, 'Z')
        for name, d, dist in (("face", (-0.62, -1.0, 0.12), 6.0), ("face front", (-0.06, -1.0, 0.06), 5.6), ("face side", (-1.0, -0.12, 0.05), 6.0)):
            rig.cams[name] = review._camera("C_" + name.replace(" ", ""), head + (turn @ Vector(d)).normalized() * dist,
                                            head + turn @ Vector((0, 0.3, 0.02)), 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(a.samples)
        lo, hi = wolf.bounds()
        print("size in studs: %.2f wide, %.2f long, %.2f tall" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, cols=a.cols, title="peek")
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
        rig, review = rig_for(a.samples)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            rig.sheet(os.path.abspath(a.review), shots("full") if a.quick else review.STANDARD, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
