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
"""
import argparse
import bisect
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, split, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

SCALE = 1.0
HEAD_AT = Vector((-0.16, -1.04, 5.95))
HEAD_ROT = (-6, 4, -16)            # nose a little up, a small tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.25

# The trunk and neck are one skin over these sections, from the rump to inside the head:
# centre x, y, z, then half width, height above the centre line (the back), depth below it (the
# breast), squareness.
BODY = [
    (0.00, 1.25, 2.02, 0.36, 0.26, 0.30, 2.0),    # 0  rump, where the train grows
    (0.00, 0.85, 2.25, 0.78, 0.50, 0.66, 2.1),    # 1  hips
    (0.00, 0.25, 2.80, 0.98, 0.68, 1.02, 2.15),   # 2  belly
    (0.00, -0.25, 3.55, 0.92, 0.64, 0.98, 2.15),  # 3  breast, pushed out
    (0.00, -0.55, 4.25, 0.64, 0.48, 0.60, 2.1),   # 4  base of the neck
    (-0.04, -0.72, 4.90, 0.44, 0.38, 0.40, 2.0),  # 5  neck
    (-0.09, -0.82, 5.40, 0.36, 0.32, 0.32, 2.0),  # 6  throat
    (-0.13, -0.92, 5.78, 0.28, 0.25, 0.25, 2.0),  # 7  inside the head
]

# The head, in its own space (nose towards -Y), the same kind of sections from the back of the
# skull to the root of the beak. Squarish sections and a sloping brow make it sleek and angular.
HEAD = [
    (0.0, 0.52, -0.02, 0.15, 0.14, 0.16, 2.2),
    (0.0, 0.40, 0.02, 0.26, 0.27, 0.27, 2.3),
    (0.0, 0.18, 0.05, 0.33, 0.36, 0.32, 2.5),
    (0.0, -0.06, 0.05, 0.345, 0.36, 0.31, 2.7),
    (0.0, -0.26, 0.02, 0.30, 0.30, 0.25, 2.9),
    (0.0, -0.42, -0.01, 0.22, 0.22, 0.18, 2.9),
    (0.0, -0.50, -0.02, 0.15, 0.15, 0.13, 2.6),
]

# A wing, drawn flat: (outwards, up) in studs from the shoulder.
WING_ROOT = (0.68, 0.18, 3.80)
SWEEP, LEAN, WING_SIZE = 18.0, 14.0, 1.0
ARM = [(0.0, 0.0), (1.0, 0.85), (2.1, 2.4), (2.6, 3.0)]                     # shoulder, elbow, wrist, hand
PRIMARIES = [(76, 2.1), (64, 2.6), (52, 2.9), (41, 3.1), (30, 3.1), (20, 3.0), (10, 2.8), (0, 2.6)]   # angle, length
SECONDARIES = [(-8, 2.45), (-18, 2.4), (-28, 2.35), (-38, 2.25), (-48, 2.15), (-58, 2.05), (-68, 1.95)]
TERTIALS = [(-78, 1.75), (-86, 1.55), (-92, 1.35)]

# Width of a feather along its length, as a fraction of its half width (0 root, 1 tip).
FLIGHT = [(0, 0.40), (0.12, 0.78), (0.3, 1.0), (0.62, 0.95), (0.82, 0.70), (0.94, 0.36), (1, 0.0)]
FLAME = [(0, 0.22), (0.25, 0.55), (0.55, 0.95), (0.7, 1.0), (0.84, 0.72), (0.95, 0.3), (1, 0.0)]
CONTOUR = [(0, 0.55), (0.3, 0.95), (0.55, 1.0), (0.8, 0.68), (1, 0.0)]
COVERT = [(0, 0.6), (0.25, 0.95), (0.6, 0.95), (0.85, 0.6), (1, 0.0)]


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


def paint(bm, g, feather=0.0):
    """Give every vertex of a shape the colour position g on its material's ramp."""
    layers = {k: bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in ("g", "xn", "d", "f")}
    for v in bm.verts:
        v[layers["g"]] = g(v) if callable(g) else g
        v[layers["f"]] = feather
    return bm


def curve(points, n):
    """n + 1 points along a smooth curve through `points`, evenly spaced, and its length."""
    pts = [Vector(p) for p in points]
    k = len(pts) - 1
    fine = [_cr(pts, i / (n * 8) * k) for i in range(n * 8 + 1)]
    run = [0.0]
    for a, b in zip(fine, fine[1:]):
        run.append(run[-1] + (b - a).length)
    out = []
    for i in range(n + 1):
        d = run[-1] * i / n
        j = min(max(bisect.bisect_right(run, d) - 1, 0), len(fine) - 2)
        f = (d - run[j]) / max(run[j + 1] - run[j], 1e-9)
        out.append(fine[j].lerp(fine[j + 1], f))
    return out, run[-1]


def loft(points, n, profile, up=None, side=None, ref=None, g=(0.0, 0.0), gpow=1.0, feather=True, sharp=(), tip=True):
    """A closed shape lofted along a smooth curve through `points`, in n steps. profile(t) gives the
    cross-section at t (0 at the root, 1 at the tip) as (across, through) pairs. The through
    direction follows `up`, or is square to the across direction `side`; `ref` picks which way it
    faces. With tip the shape closes to a point. Each vertex stores its colour position g (g[0] at
    the root to g[1] at the tip), how far across the blade it is (xn, -1 to 1), how far along it is
    in studs (d) and whether it is a feather (f): the plumage shader draws the vane from these.
    Each face stores its step along the curve (layer "ring"), so a tip can be split off."""
    P, length = curve(points, n)
    bm = bmesh.new()
    lg, lx, ld, lf = (bm.verts.layers.float.new(k) for k in ("g", "xn", "d", "f"))
    lr = bm.faces.layers.int.new("ring")
    rings, sign = [], None
    for i, p in enumerate(P):
        t = i / n
        T = (P[min(i + 1, n)] - P[max(i - 1, 0)]).normalized()
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
        if tip and i == n:
            v = bm.verts.new(p)
            v[lg], v[lx], v[ld], v[lf] = gv, 0.0, length, 1.0 if feather else 0.0
            rings.append([v])
            continue
        prof = profile(t)
        wmax = max(abs(x) for x, _ in prof) or 1.0
        ring = []
        for x, y in prof:
            v = bm.verts.new(p + W * x + N * y)
            v[lg], v[lx], v[ld], v[lf] = gv, x / wmax, length * t, 1.0 if feather else 0.0
            ring.append(v)
        rings.append(ring)
    m = len(rings[0])
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for j in range(m):
            f = bm.faces.new((a[j], a[(j + 1) % m], b[0])) if len(b) == 1 else bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
            f[lr] = i
    bm.faces.new(rings[0])[lr] = 0
    if not tip:
        bm.faces.new(rings[-1])[lr] = n - 1
    for j in sharp:
        for a, b in zip(rings, rings[1:]):
            if len(b) > 1:
                bm.edges.get((a[j], b[j])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def blade(widths, W, h, cup=0.22, thin=0.35):
    """The cross-section of a feather: two sharp edges, a raised shaft on top and a keel under it,
    `W` to each side at its widest and `h` through, arched by `cup`, thinning towards the tip."""
    def prof(t):
        w = W * _table(widths, t)
        hh = h * (1 - (1 - thin) * t)
        c = cup * w
        return [(-w, -c), (0.0, hh), (w, -c), (0.0, -c - hh * 0.5)]
    return prof


def tip_off(bm, frac):
    """Split a lofted feather into its body and its tip (the faces from `frac` of the way along)."""
    lr = bm.faces.layers.int["ring"]
    n = max(f[lr] for f in bm.faces) + 1
    cut = round(frac * n)
    return split(bm, lambda f: f[lr] < cut)


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
        rump (sgn -1) or the head (sgn 1)."""
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


def vane(mat, hsv, period=0.11, slant=0.16, shaft=0.07):
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
    barbs = op('MULTIPLY_ADD', wave, 0.07, 1.0)                           # 0.93 .. 1.07
    rmp = new("ShaderNodeMapRange")                                       # 1 on the shaft, 0 off it
    rmp.inputs["From Min"].default_value, rmp.inputs["From Max"].default_value = shaft, 0.0
    link(ax, rmp.inputs["Value"])
    lit = op('MULTIPLY_ADD', rmp.outputs["Result"], 0.35, barbs)          # the shaft is paler
    edge = new("ShaderNodeMapRange")                                      # darker towards the edges
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.65, 1.0
    edge.inputs["To Min"].default_value, edge.inputs["To Max"].default_value = 1.0, 0.82
    link(ax, edge.inputs["Value"])
    pattern = op('MULTIPLY', lit, edge.outputs["Result"])
    mixed = op('MULTIPLY_ADD', op('SUBTRACT', pattern, 1.0), f, 1.0)      # only where f is 1
    old = hsv.inputs["Value"].links[0].from_socket
    link(op('MULTIPLY', old, mixed), hsv.inputs["Value"])


# ---- the phoenix -------------------------------------------------------------------------------------

def build():
    # Five materials. The plumage runs from deep crimson at a feather's root through orange to gold
    # at its tip (a ramp read from each vertex), with short streaks and a drawn vane on top.
    plum, plum_hsv = ramp_material("Plumage", [(0.0, "#3A0610"), (0.18, "#7E0C1A"), (0.38, "#B8161C"), (0.58, "#E8501A"),
                                               (0.78, "#FF9420"), (1.0, "#FFD35A")], 0.8,
                                   dict(strength=0.14, mottle=0.10, fine=34.0, length=5.0))
    vane(plum, plum_hsv)
    beak_m, _ = ramp_material("Beak", [(0.0, "#FFD866"), (0.55, "#F2A626"), (0.82, "#9A4E16"), (1.0, "#2E1408")], 0.5,
                              dict(strength=0.08, mottle=0.06, fine=70.0, length=3.0))
    talon, _ = ramp_material("Talon", [(0.0, "#FFD060"), (0.45, "#E8A030"), (0.8, "#5A2A10"), (1.0, "#1C0C08")], 0.6,
                             dict(strength=0.12, mottle=0.08, fine=40.0, length=2.0))
    glow = kit.material("GLOW_Flame", "#FFB020", rough=0.5, emit=4.0)
    ph = Prop("Phoenix")
    ph.tally = {}

    def add(part, bm, mat, at=None):
        ph.tally[part] = ph.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        ph.add(bm, mat, at)

    def feather(part, bm, glow_from=None, at=None):
        if glow_from is None:
            add(part, bm, plum, at)
            return
        body, tip = tip_off(bm, glow_from)
        add(part, body, plum, at)
        add("glow", tip, glow, at)

    # ---- trunk and neck: one smooth skin, then rows of blade feathers over it ------------------------
    skin = Skin(BODY)
    add("skin", paint(skin.mesh(segs=20), 0.14), plum)

    def on_skin(s0, th, L, W, lift, g, n=4, widths=CONTOUR, h=0.035, drift=0.0, sink=0.04):
        s1 = skin.toward(s0, th, L)
        pts = [skin.point(s0 + (s1 - s0) * u, th + drift * u, -sink + (lift + sink) * u ** 1.2) for u in (0.0, 0.35, 0.7, 1.0)]
        up = lambda t: skin.normal(s0 + (s1 - s0) * t, th + drift * t)
        return loft(pts, n, blade(widths, W, h), up=up, g=g, sharp=(0, 2))

    ember_s = skin.s_of(2.75)
    ember_at = skin.point(ember_s, -90.0)
    # breast, flanks and back: staggered rings of short pointed feathers, each row over the next
    s = skin.s_of(3.75)
    row = 0
    while s > skin.s_of(1.0):
        c, t, u, side, w, a, b, nsq = skin.at(s)
        count = 12
        r = (w + (a + b) / 2) / 2
        for k in range(count):
            th = 90.0 + 360.0 * (k + 0.5 * (row % 2)) / count
            if (skin.point(s, th) - ember_at).length < 0.42:
                continue
            front = math.sin(math.radians(th)) < -0.3
            L = 0.66 if front else 0.6
            add_lift = 0.06 + 0.02 * (k % 2)
            feather("body feathers", on_skin(s, th, L, 2 * math.pi * r / count * 0.62, add_lift, (0.10, 0.40 if front else 0.32)))
        s -= 0.30
        row += 1
    # neck hackles: longer feathers that flare out like a mane of flame
    for i, idx in enumerate((6.5, 5.9, 5.2, 4.5, 3.9)):
        s = skin.s_of(idx)
        c, t, u, side, w, a, b, nsq = skin.at(s)
        count = 10
        r = (w + (a + b) / 2) / 2
        for k in range(count):
            th = 90.0 + 360.0 * (k + 0.5 * (i % 2)) / count
            L = 0.55 + 0.07 * i
            feather("hackles", on_skin(s, th, L, 2 * math.pi * r / count * 0.75, 0.10 + 0.025 * i, (0.22, 0.62), n=5, widths=FLAME, h=0.04))
    # the ember at the heart of the breast
    flame = [(0.0, 1.0), (0.16, 0.62), (0.26, 0.22), (0.2, -0.18), (0.0, -0.32), (-0.2, -0.18), (-0.26, 0.22), (-0.16, 0.62)]
    nrm = skin.normal(ember_s, -90.0)
    add("glow", lens([(a * 0.75, b * 0.62) for a, b in flame], 0.12, centre=(0.0, 0.1)), glow,
        seat(ember_at + nrm * 0.02, nrm, up=skin.at(ember_s)[1]))

    # ---- legs: feathered thighs, golden scaled shanks, big taloned feet ------------------------------
    for sx in (-1, 1):
        thigh = [Vector((0.46 * sx, 0.42, 2.25)), Vector((0.52 * sx, 0.30, 1.75)), Vector((0.55 * sx, 0.16, 1.32))]
        add("legs", paint(tube(thigh, [0.42, 0.36, 0.25], segs=12, rings=6), 0.16), plum)
        for rown, (u, L) in enumerate(((0.3, 0.55), (0.62, 0.55), (0.95, 0.5))):
            c = _cr(thigh, u * 2)
            rad = 0.42 + (0.25 - 0.42) * u
            for k in range(8):
                ang = 2 * math.pi * (k + 0.5 * (rown % 2)) / 8
                radial = Vector((math.cos(ang), math.sin(ang), 0.0))
                root = c + radial * rad * 0.85
                tipp = root + Vector((0, 0, -L)) + radial * 0.14
                pts = [root, root.lerp(tipp, 0.5) + radial * 0.06, tipp]
                feather("thigh feathers", loft(pts, 4, blade(CONTOUR, 0.17, 0.035), up=radial, g=(0.14, 0.42), sharp=(0, 2)))
        shank = [Vector((0.55 * sx, 0.16, 1.40)), Vector((0.56 * sx, 0.06, 0.80)), Vector((0.57 * sx, -0.02, 0.22))]
        add("legs", paint(tube(shank, [0.19, 0.16, 0.17], segs=10, rings=6), 0.25), talon)
        foot = Vector((0.57 * sx, -0.04, 0.0))
        add("feet", paint(grounded(ball((0.44, 0.44, 0.30), cuts=2), M(foot + Vector((0, 0, 0.14)))), 0.25), talon)
        for yaw, size in ((-30 + 8 * sx, 1.0), (8 * sx, 1.15), (30 + 8 * sx, 1.0), (180, 0.6)):
            F = M(foot, rot=(0, 0, yaw), scale=(1.0, size, 1.0))
            toe = [(0, 0, 0.13), (0, -0.28, 0.135), (0, -0.55, 0.11), (0, -0.72, 0.09)]
            add("feet", paint(grounded(tube(toe, [0.13, 0.12, 0.10, 0.085], segs=8, rings=6), F), 0.3), talon)
            claw = [(0, -0.68, 0.11), (0, -0.86, 0.13), (0, -0.98, 0.07), (0, -1.03, 0.0)]
            add("claws", paint(grounded(tube(claw, [0.075, 0.06, 0.035, 0.01], segs=6, rings=5), F), 1.0), talon)

    # ---- wings: raised high and spread wide ---------------------------------------------------------
    for sx in (-1, 1):
        A = Vector((sx * math.cos(math.radians(SWEEP)), math.sin(math.radians(SWEEP)), 0.0))
        B = Vector((0.0, math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))))
        B = (B - A * B.dot(A)).normalized()
        F = A.cross(B)
        F = F if F.y < 0 else -F                                          # the front face of the wing
        R = Vector((WING_ROOT[0] * sx, WING_ROOT[1], WING_ROOT[2]))

        def P(a, b, c=0.0):
            """A point of the wing: `a` out and `b` up in the flat drawing, `c` in front of it; the
            wing is cupped so that its outer half sweeps back."""
            return R + (A * a + B * b) * WING_SIZE + F * (c - 0.03 * a * a)

        def Nw(a, b):
            n = (P(a + 0.05, b) - P(a - 0.05, b)).cross(P(a, b + 0.05) - P(a, b - 0.05))
            return n if n.dot(F) > 0 else -n

        def wf(a0, b0, phi, L, W, c0, g, widths=FLIGHT, n=8, bend=-0.07, curl=0.10, h=0.05):
            d = Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi))))
            q = Vector((-d.y, d.x))
            flat = [Vector((a0, b0)) + d * L * s + q * bend * L * s * s for s in (0.0, 1 / 3, 2 / 3, 1.0)]
            pts = [P(f.x, f.y, c0 - curl * L * s ** 2.5) for f, s in zip(flat, (0.0, 1 / 3, 2 / 3, 1.0))]
            up = lambda t: Nw(*(Vector((a0, b0)) + d * L * t))
            return loft(pts, n, blade(widths, W, h), up=up, g=g, sharp=(0, 2))

        S, E, Wr, Hd = (Vector(p) for p in ARM)
        for i, (phi, L) in enumerate(PRIMARIES):
            r = Hd.lerp(Wr, i / (len(PRIMARIES) - 1))
            feather("primaries", wf(r.x, r.y, phi, L, 0.26, -0.025 * i, (0.30, 0.98), n=12), glow_from=0.8 if 1 <= i <= 6 else None)
            cv = r - Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi)))) * 0.05
            feather("coverts", wf(cv.x, cv.y, phi, L * 0.42, 0.22, 0.09, (0.20, 0.62), widths=COVERT, n=5, curl=0.0, h=0.04))
        for j, (phi, L) in enumerate(SECONDARIES):
            r = Wr.lerp(E, (j + 0.4) / len(SECONDARIES))
            feather("secondaries", wf(r.x, r.y, phi, L, 0.27, -0.19 + 0.02 * j, (0.24, 0.90), n=9))
            cv = r + Vector((-math.sin(math.radians(phi)), math.cos(math.radians(phi)))) * 0.05
            feather("coverts", wf(cv.x, cv.y, phi, L * 0.45, 0.23, 0.09, (0.18, 0.58), widths=COVERT, n=5, curl=0.0, h=0.04))
        for j, (phi, L) in enumerate(TERTIALS):
            r = E.lerp(S, 0.15 + 0.3 * j)
            feather("secondaries", wf(r.x, r.y, phi, L, 0.25, -0.05 + 0.02 * j, (0.20, 0.75), n=7))
        # median coverts along the forearm and small marginal coverts over the leading edge
        for k in range(8):
            u = (k + 0.5) / 8
            r = S.lerp(E, u * 2) if u < 0.5 else E.lerp(Wr, u * 2 - 1)
            phi = -80 + 70 * u
            feather("coverts", wf(r.x + 0.05, r.y + 0.12, phi, 0.78, 0.2, 0.15, (0.16, 0.48), widths=COVERT, n=4, curl=0.0, h=0.04))
        arm = [S, E, Wr, Hd]
        for k in range(10):
            u = (k + 0.3) / 10 * 3
            r = _cr(arm, u)
            phi = _table([(0, -70), (1, -45), (2, -10), (3, 5)], u)
            feather("coverts", wf(r.x, r.y + 0.06, phi, 0.5, 0.17, 0.21, (0.12, 0.38), widths=CONTOUR, n=4, curl=0.0, h=0.035))
        add("wing arms", paint(tube([P(p.x, p.y, 0.05) for p in arm], [0.28, 0.18, 0.13, 0.08], segs=8, rings=10), 0.16), plum)

    # ---- the train: long flame feathers that sweep to the ground and curl up at the ends ---------------
    root = Vector((0.0, 1.12, 2.12))
    base = [(0, 0, 0), (0, 1.0, -0.78), (0, 2.2, -1.80), (0, 3.4, -2.12), (0, 4.5, -2.12), (0, 5.25, -1.80),
            (0, 5.6, -1.15), (0, 5.35, -0.62)]
    for i in (-3, 3, -2, 2, -1, 1, 0):                                  # outer ones first, the middle on top
        a = abs(i)
        yaw = 11.0 * i
        shrink = 1.0 - 0.07 * a
        lift = 0.03 * (3 - a)
        pts = []
        for k, (x, y, z) in enumerate(base):
            p = Vector((x, y * shrink, z))
            if k >= 3:
                p.z += lift
                p.x += 0.12 * i * (k - 2)                                  # the ends curl outwards a little
            p = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ p
            pts.append(root + Vector((0.08 * i, 0, 0)) + p)
        sidev = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((1, 0, 0))
        bm = loft(pts, 20, blade(FLAME, 0.36 - 0.02 * a, 0.06, cup=0.12), side=sidev, ref=(0, 0, 1), g=(0.16, 0.98), gpow=0.8, sharp=(0, 2))
        feather("train", grounded(bm), glow_from=0.84)
    for i in (-2, 2, -1, 1):                                            # shorter feathers over the root of the train
        yaw = 15.0 * i
        pts = [root + Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector(p) for p in
               ((0, -0.1, 0.12), (0, 0.9, -0.42), (0, 1.9, -1.15), (0, 2.75, -1.7), (0, 3.3, -1.95))]
        sidev = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((1, 0, 0))
        feather("train", loft(pts, 12, blade(FLAME, 0.30, 0.05, cup=0.12), side=sidev, ref=(0, 0, 1), g=(0.14, 0.85), sharp=(0, 2)))
    for i in range(-3, 4):                                              # coverts over the root
        yaw = 16.0 * i
        pts = [root + Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector(p) for p in ((0, -0.45, 0.32), (0, 0.25, 0.12), (0, 0.95, -0.28))]
        sidev = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((1, 0, 0))
        feather("train", loft(pts, 5, blade(COVERT, 0.26, 0.045), side=sidev, ref=(0, 0, 1), g=(0.12, 0.45), sharp=(0, 2)))

    # ---- head: placed in its own space, then turned as one ---------------------------------------------
    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    hs = Skin(HEAD, samples=16)
    add("head", paint(hs.mesh(segs=24, k=0.3, lo=0.05, hi=0.1), 0.34), plum, H)

    def hs_at(y):
        """The s of the head skin at the depth y (the head runs straight along -Y)."""
        return min(max(HEAD[0][1] - y, 0.0), hs.L)

    # the beak: a hooked upper bill over a shorter lower one
    def bill(t):
        w = 0.165 * (1 - t) ** 0.55 + 0.014
        hh = 0.15 * (1 - 0.72 * t) + 0.01
        return [(0.0, hh * 0.62), (0.62 * w, hh * 0.44), (w, -hh * 0.04), (0.72 * w, -hh * 0.42), (0.0, -hh * 0.46),
                (-0.72 * w, -hh * 0.42), (-w, -hh * 0.04), (-0.62 * w, hh * 0.44)]

    upper = [(0, -0.38, 0.03), (0, -0.64, 0.015), (0, -0.88, -0.05), (0, -1.0, -0.17), (0, -0.98, -0.31)]
    add("beak", loft(upper, 12, bill, side=(1, 0, 0), ref=(0, 0, 1), g=(0.0, 1.0), gpow=2.4, feather=False, sharp=(0, 3, 5)), beak_m, H)

    def jaw(t):
        w = 0.12 * (1 - t) ** 0.6 + 0.012
        hh = 0.075 * (1 - 0.6 * t) + 0.008
        return [(0.0, hh * 0.3), (w, 0.0), (0.6 * w, -hh * 0.6), (-0.6 * w, -hh * 0.6), (-w, 0.0)]

    lower = [(0, -0.38, -0.075), (0, -0.62, -0.11), (0, -0.82, -0.135)]
    add("beak", loft(lower, 6, jaw, side=(1, 0, 0), ref=(0, 0, 1), g=(0.1, 0.62), feather=False, sharp=(1, 4)), beak_m, H)

    # brows: a hard ledge over each eye, running down towards the beak
    for sx in (-1, 1):
        th = lambda u: 90 - sx * (90 - _table([(0, 62), (0.45, 32), (1, 40)], u))
        pts = [hs.point(hs_at(y), th(u), _table([(0, 0.0), (0.45, 0.035), (1, 0.0)], u))
               for u, y in ((0.0, -0.40), (0.25, -0.30), (0.45, -0.18), (0.7, -0.04), (1.0, 0.10))]

        def brow_prof(t, sx=sx):
            w = 0.075 * _table([(0, 0.6), (0.4, 1.0), (1, 0.5)], t)
            h = 0.05 * _table([(0, 0.6), (0.4, 1.0), (1, 0.4)], t)
            return [(-sx * w, -0.02), (-sx * 0.2 * w, h), (sx * w, h * 0.35), (sx * 0.4 * w, -0.03)]

        up = lambda t, th=th: hs.normal(hs_at(-0.40 + 0.5 * t), th(t))
        add("brows", loft(pts, 6, brow_prof, up=up, g=(0.30, 0.22), feather=False, sharp=(2,)), plum, H)

        # the eye: a glowing almond under the brow, the back corner higher than the front
        s_eye, th_eye = hs_at(-0.17), 90 - sx * (90 - 16)
        p, nrm = hs.point(s_eye, th_eye), hs.normal(s_eye, th_eye)
        look = (nrm + Vector((0, -0.45, 0))).normalized()
        outline = []
        for k in range(16):
            ang = 2 * math.pi * k / 16
            a = math.cos(ang)
            top = math.sin(ang) > 0
            b = math.sin(ang) * (0.42 if top else 0.55) * (1 - a * a) ** 0.15
            outline.append((a * 0.135, b * 0.13 + sx * 0.035 * a))
        add("glow", lens(outline, 0.06), glow, H @ seat(p - nrm * 0.012, look))

    # the crest: five flame plumes swept back from the crown, their tips glowing
    for k in (-2, 2, -1, 1, 0):
        a = abs(k)
        L = 1.0 - 0.17 * a
        r0 = Vector((0.05 * k, -0.08 + 0.07 * a, 0.36))
        pts = [r0 + Vector(d) * L for d in ((0, 0, 0), (0.12 * k, 0.45, 0.20), (0.25 * k, 0.95, 0.55), (0.33 * k, 1.22, 1.05),
                                            (0.30 * k, 1.12, 1.40))]
        tilt = math.radians(32 * a)
        upv = Vector((math.copysign(math.cos(tilt), k or 1), 0.0, math.sin(tilt)))
        bm = loft(pts, 12, blade(FLAME, 0.16 - 0.015 * a, 0.045, cup=0.1), up=upv, g=(0.36, 0.95), sharp=(0, 2))
        feather("crest", bm, glow_from=0.66, at=H)

    ph.build(SCALE)
    return ph


def bake(phoenix, texture):
    """Everything that does not glow becomes one textured mesh, its feather pattern and soft
    shading in the creases baked into one colour image. The glowing parts stay one mesh with their
    own bright material. Roblox gets two MeshParts."""
    glow = [ob for ob in phoenix.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in phoenix.objects if ob not in glow], texture, name="Phoenix_Body",
                            shade=0.55, soften=2, rough=0.85, sheen=0.15, uv_angle=85.0, uv_margin=0.004)
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
        rig.cams["face"] = review._camera("C_face", look + Vector((-0.5, -1.0, 0.12)).normalized() * 7.0, look, 30)
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
        rig, review = rig_for(40)
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
