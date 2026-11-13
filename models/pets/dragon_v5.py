"""Dragon pet: a big, friendly dragon in a chunky cartoon-fantasy style with plated scales.
Built from scratch by script.

    python models/pets/dragon.py --review out/dragon.png      # render the review sheet
    python models/pets/dragon.py --export models/export/dragon.fbx

Style: smooth rounded forms (not faceted, not plush, not fur) carrying plates: a gentle guardian
that a child would want as a pet. Must-haves, checked in every review:
  1. Reads as a dragon in outline: two horns, half-open wings, a row of rounded plates down the
     neck, back and tail, a long tail that ends in a spade.
  2. Big and sturdy: about 7 studs to the horn tips and 9 long, a barrel body on four short thick
     legs, a strong arched neck. The head is in proportion (NOT a simulator pet).
  3. A simple, clearly friendly face: modest bead eyes with one highlight each, a gentle closed
     smile. Nothing crowding the face (round 3: no brow ridges, they read as worried).
  4. Plated: big overlapping cream plates down the throat and belly, coral plates down the spine,
     darker shields along the back.
  5. Not plastic: a scale pattern and several tones baked into the texture, a matte finish.
  6. Not symmetrical: head turned and tilted, tail swung round to one side, wings held differently.
"""
import argparse
import bisect
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, cut, rounded_box, split, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0
HEAD_AT = (-0.50, -2.98, 5.22)
HEAD_ROT = (9, 5, -24)             # nose a little down, a small tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 0.9                    # round 2: the head was baby-sized against the body

# The neck, trunk and tail are one skin over these sections, from the head to the tail tip:
# centre x, y, z, then half width, height above the centre line, depth below it, squareness.
SPINE = [
    (-0.46, -2.62, 5.00, 0.60, 0.58, 0.60, 2.0),   # 0  inside the head
    (-0.38, -2.06, 4.60, 0.66, 0.60, 0.64, 2.0),   # 1  throat
    (-0.26, -1.76, 4.05, 0.80, 0.68, 0.78, 2.1),   # 2  neck
    (-0.12, -1.50, 3.50, 1.02, 0.84, 1.10, 2.2),   # 3  neck base
    (0.00, -1.02, 2.92, 1.34, 1.10, 1.40, 2.3),    # 4  chest
    (0.00, -0.30, 2.56, 1.56, 1.28, 1.40, 2.4),    # 5  shoulders
    (0.00, 0.62, 2.44, 1.62, 1.33, 1.43, 2.5),     # 6  belly
    (0.00, 1.58, 2.42, 1.50, 1.20, 1.25, 2.4),     # 7  hips
    (0.00, 2.42, 2.20, 1.14, 0.94, 0.90, 2.2),     # 8  rump
    (-0.08, 3.10, 1.78, 0.86, 0.76, 0.70, 2.1),    # 9  tail root
    (-0.42, 3.72, 1.28, 0.68, 0.62, 0.58, 2.0),    # 10
    (-1.02, 4.14, 0.86, 0.56, 0.52, 0.50, 2.0),    # 11
    (-1.76, 4.28, 0.56, 0.46, 0.44, 0.42, 2.0),    # 12
    (-2.46, 4.14, 0.40, 0.38, 0.37, 0.36, 2.0),    # 13 resting on the ground
    (-3.00, 3.82, 0.44, 0.31, 0.31, 0.30, 2.0),    # 14
    (-3.34, 3.44, 0.78, 0.26, 0.26, 0.25, 2.0),    # 15 the tip curls up
    (-3.48, 3.18, 1.32, 0.21, 0.21, 0.21, 2.0),    # 16
    (-3.50, 3.06, 1.90, 0.17, 0.17, 0.17, 2.0),    # 17 where the spade sits
]
SHOULDERS = 5

# The head is one shell over these sections, from the back of the skull to the nose:
# distance towards the nose, top, bottom, half width, squareness.
HEAD = [
    (-0.80, 0.58, -0.46, 0.76, 2.1),
    (-0.48, 0.90, -0.68, 1.03, 2.15),
    (-0.10, 1.06, -0.80, 1.14, 2.2),
    (0.24, 1.02, -0.86, 1.13, 2.2),
    (0.48, 0.84, -0.86, 1.05, 2.25),    # the brow
    (0.64, 0.50, -0.84, 0.90, 2.3),     # the step down to the snout, where the eyes sit
    (0.80, 0.30, -0.80, 0.76, 2.3),
    (1.05, 0.24, -0.75, 0.71, 2.3),
    (1.30, 0.22, -0.68, 0.66, 2.3),     # the blunt end of the snout
]
SNOUT_CAP = 0.32

# A wing, drawn flat: (along the span, up), in studs from the shoulder.
WING = {"S": (0.0, 0.0), "E": (0.35, 1.25), "W": (1.25, 2.35),
        "T1": (3.15, 2.30), "T2": (3.00, 0.95), "T3": (2.10, -0.10), "B": (0.85, -0.30)}


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


def grounded(bm, at):
    """Move a shape into place and flatten whatever would go below the floor."""
    bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def tones(mat, up=None, down=None, up_mix=0.5, down_mix=0.4):
    """More than one tone for a material that kit.scaly or kit.furry has patterned: where the surface
    faces up (the back, the top of the head) it turns towards the colour `up`, where it faces down
    towards `down`. Like the pattern, this is baked into the colour texture."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    base = tuple(hsv.inputs["Color"].default_value)
    geo = new("ShaderNodeNewGeometry")
    sep = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])
    colour = None
    for hexcode, amount, lo, hi in ((up, up_mix, 0.15, 0.95), (down, down_mix, -0.10, -0.90)):
        if not hexcode:
            continue
        rng = new("ShaderNodeMapRange")
        rng.interpolation_type = 'SMOOTHSTEP'
        rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = lo, hi
        rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.0, amount
        link(sep.outputs[2], rng.inputs["Value"])
        mix = new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        link(rng.outputs["Result"], mix.inputs[0])
        if colour is None:
            mix.inputs[6].default_value = base
        else:
            link(colour, mix.inputs[6])
        mix.inputs[7].default_value = (*kit.srgb(hexcode), 1.0)
        colour = mix.outputs[2]
    if colour is not None:
        link(colour, hsv.inputs["Color"])
    return mat


class Skin:
    """A smooth skin over sections along a path: the dragon's neck, trunk and tail in one piece.
    Positions on it are (s, angle): s is the distance along the path from the head end, the angle
    goes round the section in degrees, 90 at the spine and -90 at the belly."""

    def __init__(self, sections, shoulders, samples=40):
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
        # "Up" (the spine side). From the shoulders to the tail tip it is straight up, leaned over only
        # as far as the path makes it, so the back plates of a tail lying on the ground stand upright.
        # From the shoulders to the head it is carried along the path without twisting, so the spine
        # stays on the back of a neck that rises steeply and leans to one side.
        up = Vector((0, 0, 1))
        self.U = [(up - t * up.dot(t)).normalized() for t in self.T]
        for i in range(shoulders * samples - 1, -1, -1):
            u, axis = self.U[i + 1], self.T[i + 1].cross(self.T[i])
            if axis.length > 1e-9:
                u = Matrix.Rotation(self.T[i + 1].angle(self.T[i]), 3, axis.normalized()) @ u
            self.U[i] = (u - self.T[i] * u.dot(self.T[i])).normalized()

    def s_of(self, index):
        """Distance along the path of section number `index` (which may be a fraction)."""
        x = index * self.samples
        i = min(int(x), len(self.len) - 2)
        return self.len[i] + (self.len[i + 1] - self.len[i]) * (x - i)

    def index_of(self, s):
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.len) - 2)
        return (i + (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)) / self.samples

    def at(self, s):
        """Centre, tangent, up, side and the section's sizes at s."""
        s = min(max(s, 0.0), self.L)
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.pts) - 2)
        f = (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)
        c = self.pts[i].lerp(self.pts[i + 1], f)
        t = self.T[i].lerp(self.T[i + 1], f).normalized()
        u = self.U[i].lerp(self.U[i + 1], f)
        u = (u - t * u.dot(t)).normalized()
        w, a, b, n = (p + (q - p) * f for p, q in zip(self.par[i], self.par[i + 1]))
        return c, t, u, t.cross(u), w, a, b, n

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
        """The point of the skin at (s, th), `lift` proud of it."""
        p = self.bare(s, th)
        return p + self.normal(s, th) * lift if lift else p

    def line(self, th, step=0.02):
        """A table of how long the line along the skin at the angle th is, at each s."""
        n = int(self.L / step)
        ss = [self.L * i / n for i in range(n + 1)]
        pts = [self.bare(s, th) for s in ss]
        run = [0.0]
        for a, b in zip(pts, pts[1:]):
            run.append(run[-1] + (b - a).length)
        return ss, run

    @staticmethod
    def along(line, d):
        """The s at which the line (from line()) has run the distance d."""
        ss, run = line
        i = min(max(bisect.bisect_right(run, d) - 1, 0), len(ss) - 2)
        return ss[i] + (ss[i + 1] - ss[i]) * (d - run[i]) / max(run[i + 1] - run[i], 1e-9)

    @staticmethod
    def run_at(line, s):
        ss, run = line
        i = min(max(bisect.bisect_right(ss, s) - 1, 0), len(ss) - 2)
        return run[i] + (run[i + 1] - run[i]) * (s - ss[i]) / max(ss[i + 1] - ss[i], 1e-9)

    def rings(self, k=0.42, lo=0.13, hi=0.42):
        """Where to put the rings of the mesh: closer together where the skin is thin."""
        s, out = 0.0, [0.0]
        while True:
            _, _, _, _, w, a, b, _ = self.at(s)
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            out.append(s)
        return out + [self.L]

    def mesh(self, segs=20):
        bm = bmesh.new()
        ss = self.rings()
        loops = [[bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)] for s in ss]
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


def plate(skin, s0, s1, half, centre=-90.0, lift=(0.03, 0.11), bow=0.0, pinch=0.2, tuck=-0.02,
          vs=(0, 0.12, 0.45, 0.8, 0.94, 1), qs=(-1, -0.9, -0.55, -0.2, 0.2, 0.55, 0.9, 1)):
    """A plate lying on the skin from s0 to s1, `half` degrees to each side of the angle `centre`.
    It rises from `lift[0]` at the head end to `lift[1]` at the tail end, where the next plate tucks
    under it, like roof tiles; its rim is tucked just under the skin. `bow` lets the free edge sag
    in the middle, `pinch` rounds the corners."""
    bm = bmesh.new()
    grid = []
    for i, v in enumerate(vs):
        row = []
        for j, q in enumerate(qs):
            rim = i in (0, len(vs) - 1) or j in (0, len(qs) - 1)
            s = s0 + (s1 - s0) * v + bow * (1 - q * q) * v
            th = centre + half * (1 - pinch * abs(2 * v - 1) ** 3) * q
            row.append(bm.verts.new(skin.point(s, th, tuck if rim else lift[0] + (lift[1] - lift[0]) * v ** 1.3)))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(len(qs) - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bm.normal_update()
    out = skin.normal((s0 + s1) / 2, centre)
    if sum((f.normal for f in bm.faces), Vector()).dot(out) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
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


def arch(length, height, sweep=0.25, n=2.3, steps=7, sink=0.3):
    """The outline of a rounded back plate: an arch `length` along the spine and `height` tall that
    leans back by `sweep`, carried on below the skin by `sink` of its height so its foot is buried."""
    pts = []
    for i in range(steps + 1):
        x, y = _super(math.pi * i / steps, n)
        pts.append((-x * length / 2 + sweep * height * y, y * height))
    return pts + [(length * 0.4, -sink * height), (-length * 0.4, -sink * height)]


def smooth_outline(points, per=3):
    """A closed outline through `points`, with `per` points for each one given."""
    n = len(points)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = (Vector(points[(i + d) % n]) for d in (-1, 0, 1, 2))
        for k in range(per):
            u = k / per
            out.append(tuple(0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)))
    return out


def stand(origin, across, up):
    """A transform that stands a lens() at `origin`: its length runs `across`, its height `up`."""
    z = Vector(up).normalized()
    x = Vector(across)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def seat(p, normal, up=(0, 0, 1)):
    """A transform that seats a shape at p on a surface: its front (-Y) looks out along `normal`
    and its top is as near `up` as it can be."""
    y = -Vector(normal).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(p)
    return m


def membrane(wrist, rim, scallop, billow, back, thick=0.085, cols=5, ts=(0.3, 0.58, 0.82, 0.94, 1.0)):
    """A wing membrane: a fan of skin round the wrist out to the points of `rim`. Between rim[k] and
    rim[k+1] the edge dips in by scallop[k] (0 gives a straight edge) and the panel billows towards
    `back` by billow[k]. It is a closed shape `thick` through, thinning to nothing at its edges."""
    w = Vector(wrist)
    spokes = []                                              # (rim point, how far this spoke billows)
    for k, (a, c) in enumerate(zip(rim, rim[1:])):
        a, c = Vector(a) - w, Vector(c) - w
        steps = cols if scallop[k] else 2
        fs = [i / steps for i in range(steps)]
        if k == 0:
            fs.insert(1, 0.1)
        if k == len(rim) - 2:
            fs.append(0.9)
        for f in fs:
            if scallop[k]:
                reach = (a.length + (c.length - a.length) * f) * (1 - scallop[k] * math.sin(math.pi * f))
                p = a.normalized().lerp(c.normalized(), f).normalized() * reach
            else:
                p = a.lerp(c, f)
            spokes.append((p, billow[k] * math.sin(math.pi * f)))
    spokes.append((Vector(rim[-1]) - w, 0.0))
    bm = bmesh.new()
    mid = bm.verts.new(w)
    back = Vector(back).normalized()
    sheets = ([], [])
    last = len(spokes) - 1
    for i, (p, puff) in enumerate(spokes):
        cols_ = ([], [])
        for t in ts:
            c = w + p * t + back * (puff * t ** 1.3)
            if i in (0, last) or t == 1.0:
                v = bm.verts.new(c)
                cols_[0].append(v)
                cols_[1].append(v)
            else:
                cols_[0].append(bm.verts.new(c - back * thick / 2))
                cols_[1].append(bm.verts.new(c + back * thick / 2))
        sheets[0].append(cols_[0])
        sheets[1].append(cols_[1])
    for sheet in sheets:
        for a, b in zip(sheet, sheet[1:]):
            bm.faces.new((mid, a[0], b[0]))
            for j in range(len(ts) - 1):
                bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def head_shell(segs=24, per=2):
    """The head as one smooth shell from the sections in HEAD, nose towards -Y."""
    k = len(HEAD) - 1

    def section(t):
        s, top, bot, w, n = (_cr([h[i] for h in HEAD], t) for i in range(5))
        return s, (top + bot) / 2, (top - bot) / 2, w, n

    first, last = section(0.0), section(float(k))
    rings = []                                               # s, centre height, half height, half width, squareness
    for phi in (72, 48, 24):                                 # the back of the skull, rounded off
        c, sn = math.cos(math.radians(phi)) ** (2 / 2.3), math.sin(math.radians(phi)) ** (2 / 2.3)
        rings.append((first[0] - 0.32 * sn, first[1], first[2] * c, first[3] * c, first[4]))
    rings += [section(i / per) for i in range(k * per + 1)]
    for phi in (24, 48, 72):                                 # the blunt end of the snout
        c, sn = math.cos(math.radians(phi)) ** (2 / 2.3), math.sin(math.radians(phi)) ** (2 / 2.3)
        rings.append((last[0] + SNOUT_CAP * sn, last[1], last[2] * c, last[3] * c, last[4]))
    bm = bmesh.new()
    loops = []
    for s, zc, h, w, n in rings:
        loop = []
        for j in range(segs):
            x, z = _super(math.pi / 2 + 2 * math.pi * j / segs, n)
            loop.append(bm.verts.new((w * x, -s, zc + h * z)))
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, tip in ((loops[0], (0, -(first[0] - 0.32), first[1])), (loops[-1], (0, -(last[0] + SNOUT_CAP), last[1]))):
        c = bm.verts.new(tip)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


class Surface:
    """Finds points exactly on a mesh, so that details sit on it and neither float nor sink."""

    def __init__(self, bm):
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, direction, out=0.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


# ---- the dragon ------------------------------------------------------------------------------------

def build():
    # Seven flat colours. The owner found smooth flat colour "like plastic", so every skin colour gets
    # a pattern of scales that is baked into the texture, and the body has three tones: a deeper,
    # bluer back, the teal flanks and a paler underside.
    teal = kit.scaly(kit.material("Teal", "#2FA79A"), size=0.34, joins=0.34, vary=0.16, shade_down=0.12, rough=0.85)
    tones(teal, up="#1A6F86", down="#8FE0B0", up_mix=0.5, down_mix=0.45)
    deep = kit.scaly(kit.material("Deep", "#176577"), size=0.5, joins=0.12, vary=0.10, rough=0.85)
    cream = kit.scaly(kit.material("Cream", "#FBEBB6"), size=0.5, joins=0.2, vary=0.08, shade_down=0.06, rough=0.85)
    coral = kit.scaly(kit.material("Coral", "#EC6548"), size=0.4, joins=0.22, vary=0.12, rough=0.85)
    skinm = kit.scaly(kit.material("Membrane", "#F79A5E"), size=0.45, joins=0.2, vary=0.10, rough=0.85)
    ivory = kit.furry(kit.material("Ivory", "#EFE2C4"), strength=0.24, mottle=0.08, fine=5.0, length=6.0)
    eye = kit.material("Eye", "#15111B", rough=0.18)
    d = Prop("Dragon")
    d.tally = {}

    def add(part, bm, mat, at=None):
        d.tally[part] = d.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        d.add(bm, mat, at)

    # ---- neck, trunk and tail: one smooth skin ---------------------------------------------------------
    skin = Skin(SPINE, SHOULDERS)
    body = skin.mesh(segs=20)
    for v in body.verts:
        v.co.z = max(v.co.z, 0.0)
    add("skin", body, teal)

    # ---- throat and belly: big cream plates that overlap like roof tiles -------------------------------
    belly = skin.line(-90.0)
    dist, stop = Skin.run_at(belly, skin.s_of(0.55)), Skin.run_at(belly, skin.s_of(11.2))
    while dist < stop:
        s0 = Skin.along(belly, dist)
        i = skin.index_of(s0)
        size = _table([(0, 0.50), (2.5, 0.56), (3.5, 0.66), (5, 0.80), (8, 0.74), (9.5, 0.56), (11.5, 0.40)], i)
        half = _table([(0, 44), (3, 42), (5, 38), (8, 36), (9.5, 34), (11.5, 26)], i)
        rise = _table([(0, 0.12), (5, 0.12), (6, 0.09), (11.5, 0.06)], i)
        s1 = Skin.along(belly, dist + size * 1.2)
        front = i < 5.3                                                   # the plates a player sees get more shape
        p = plate(skin, s0, s1, half, lift=(0.03, rise), bow=0.10 * size, pinch=0.22,
                  vs=(0, 0.16, 0.5, 0.84, 1) if front else (0, 0.2, 0.6, 0.86, 1),
                  qs=(-1, -0.82, -0.45, 0, 0.45, 0.82, 1) if front else (-1, -0.8, -0.3, 0.3, 0.8, 1))
        add("belly plates", p, cream)
        dist += size

    # ---- back plates: a row of rounded coral plates from the head to the tail --------------------------
    spine = skin.line(90.0)
    dist, stop = Skin.run_at(spine, skin.s_of(0.75)), Skin.run_at(spine, skin.s_of(15.6))
    while dist < stop:
        s = Skin.along(spine, dist)
        i = skin.index_of(s)
        size = _table([(0.7, 0.42), (1.5, 0.56), (2.3, 0.62), (3.0, 0.50), (3.7, 0.46), (4.4, 0.62), (5.2, 0.90), (6.3, 1.0),
                       (7.5, 0.90), (8.5, 0.78), (9.5, 0.66), (11, 0.54), (13, 0.40), (15.6, 0.26)], i)
        c, t, u, side, _, a, _, _ = skin.at(s)
        fin = lens(arch(size * 1.06, size * 0.84), 0.06 + 0.2 * size, centre=(0.05 * size, 0.24 * size))
        add("back plates", fin, coral, stand(c + u * (a - 0.02), t, u))
        dist += size * 0.9

    # ---- shields: a row of darker plates down each side of the spine -----------------------------------
    for sgn in (-1, 1):
        ridge = skin.line(90.0 + 31.0 * sgn)
        dist, stop = Skin.run_at(ridge, skin.s_of(1.0)), Skin.run_at(ridge, skin.s_of(10.6))
        while dist < stop:
            s0 = Skin.along(ridge, dist)
            i = skin.index_of(s0)
            size = _table([(1, 0.46), (3, 0.52), (5, 0.74), (7.5, 0.74), (9, 0.56), (10.6, 0.42)], i)
            s1 = Skin.along(ridge, dist + size * 1.22)
            p = plate(skin, s0, s1, 15.0, centre=90.0 + 31.0 * sgn, lift=(0.02, 0.085), bow=0.22 * size, pinch=0.4,
                      vs=(0, 0.25, 0.72, 1), qs=(-1, -0.6, 0, 0.6, 1))
            add("shields", p, deep)
            dist += size

    # ---- legs: short and thick, with big clawed feet --------------------------------------------------
    def foot(x, y, yaw):
        f = M((x, y, 0), rot=(0, 0, yaw))
        add("feet", grounded(rounded_box((1.02, 1.12, 0.62), n=2.6, cuts=3), f @ M((0, -0.10, 0.30))), teal)
        for k in (-1, 0, 1):
            toe = f @ M((0.34 * k, -0.60 - (0.07 if k == 0 else 0.0), 0.20), rot=(0, 0, 14 * k))
            add("feet", grounded(ball((0.40, 0.56, 0.40), cuts=1), toe), teal)
            claw = tube([(0, -0.14, 0.05), (0, -0.36, -0.02), (0, -0.52, -0.13)], [0.14, 0.11, 0.03], segs=6, rings=3)
            add("claws", claw, ivory, toe)

    for sx in (-1, 1):
        step = -0.28 if sx < 0 else 0.0                                   # the near front foot is a step ahead
        add("legs", ball((1.0, 1.55, 1.65), cuts=3), teal, M((1.14 * sx, -0.82, 2.45), rot=(12, 0, 0)))
        add("legs", tube([(0.92 * sx, -0.86, 2.6), (1.06 * sx, -0.94 + step * 0.3, 1.75), (1.14 * sx, -1.02 + step * 0.8, 0.95),
                          (1.15 * sx, -1.10 + step, 0.30)], [0.60, 0.60, 0.50, 0.47], segs=12, rings=6), teal)
        foot(1.15 * sx, -1.10 + step, 8 * sx)
        add("legs", ball((1.2, 2.05, 2.15), cuts=4), teal, M((1.2 * sx, 1.42, 2.05), rot=(-10, 0, 0)))
        add("legs", tube([(1.28 * sx, 1.50, 1.65), (1.40 * sx, 1.74, 0.98), (1.40 * sx, 1.60, 0.30)],
                         [0.62, 0.50, 0.47], segs=12, rings=5), teal)
        foot(1.40 * sx, 1.50, 12 * sx)

    # ---- wings: half open, the far one spread a little wider ------------------------------------------
    for sx, sweep, size in ((-1, 40.0, 0.88), (1, 27.0, 0.86)):
        a = math.radians(sweep)
        along = Vector((sx * math.cos(a), math.sin(a), 0.0))
        up = Vector((sx * 0.2, -0.08, 0.98)).normalized()
        root = Vector((0.8 * sx, -0.5, 3.4))
        P = {k: root + (along * p + up * q) * size for k, (p, q) in WING.items()}
        back = along.cross(up)
        back = back if back.y > 0 else -back
        web = membrane(P["W"], [P[k] for k in ("T1", "T2", "T3", "B", "S", "E")], (0.2, 0.2, 0.16, 0, 0), (0.16, 0.16, 0.12, 0, 0), back)
        add("wings", web, skinm)
        add("wings", tube([P["S"], P["E"], P["W"]], [0.21, 0.17, 0.13], segs=8, rings=6), teal)
        add("wings", ball((0.34, 0.34, 0.34), cuts=1), teal, M(P["W"]))
        for k, r in (("T1", 0.105), ("T2", 0.09), ("T3", 0.085)):
            tip = P[k] + (P[k] - P["W"]).normalized() * 0.07
            add("wings", tube([P["W"], (P["W"] + P[k]) / 2, tip], [r, r * 0.75, 0.03], segs=6, rings=4), teal)
        add("claws", tube([P["W"], P["W"] + up * 0.24 - along * 0.05, P["W"] + up * 0.42 - along * 0.16], [0.11, 0.08, 0.025], segs=6, rings=3), ivory)

    # ---- the spade at the end of the tail, held up and facing the front -------------------------------
    c, t, u, side, _, _, _, _ = skin.at(skin.L)
    leaf = smooth_outline([(0, 1.0), (0.24, 0.70), (0.47, 0.38), (0.52, 0.08), (0.36, -0.16), (0.12, -0.14),
                           (-0.12, -0.14), (-0.36, -0.16), (-0.52, 0.08), (-0.47, 0.38), (-0.24, 0.70)], per=2)
    spade = lens([(a * 1.3, b * 1.35) for a, b in leaf], 0.3, rows=((0.6, 0.95), (0.88, 0.62), (1.0, 0.0)), centre=(0.0, 0.4))
    facing = Vector((-0.3, -1.0, 0.1))
    add("spade", spade, coral, stand(c - t * 0.1, t.cross(facing), t))

    # ---- head: everything is placed in the head's own space, then turned as one ------------------------
    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    head = head_shell()
    face = Surface(head)
    core = Vector((0, -0.95, -0.26))                                      # a point inside the snout

    def snout(phi, elev, out=0.0):
        """The point of the snout phi degrees round from straight ahead and elev degrees up, as seen
        from its core, `out` proud of the surface; and the surface's normal there."""
        p, e = math.radians(phi), math.radians(elev)
        return face.hit(core, (math.sin(p) * math.cos(e), -math.cos(p) * math.cos(e), math.sin(e)), out)

    def smile(phi):
        """How high the mouth line is at phi: lowest in the middle, turning up towards both ends."""
        x = abs(phi) / 64.0
        return -13.0 + 17.0 * x * x + 5.0 * x ** 6

    # the chin: a cream plate under the mouth line, the first of the throat plates
    bm, grid = bmesh.new(), []
    phis, vs = (-66, -58, -40, -20, 0, 20, 40, 58, 66), (0.0, 0.12, 0.4, 0.7, 1.0)
    for i, v in enumerate(vs):
        row = []
        for j, phi in enumerate(phis):
            top = smile(max(min(phi, 64), -64))
            rim = j in (0, len(phis) - 1) or i == len(vs) - 1
            row.append(bm.verts.new(snout(phi, top + (-78.0 - top) * v, -0.02 if rim else (0.0 if i == 0 else 0.035))[0]))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(len(phis) - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(Vector((0, -1, -0.6))) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    add("face", bm, cream, H)

    line = [snout(phi, smile(phi), 0.012)[0] for phi in range(-64, 65, 8)]
    n = len(line)
    add("face", tube(line, [0.014 + 0.018 * max(0.0, math.sin(math.pi * i / (n - 1))) ** 0.5 for i in range(n)], segs=5, rings=20), deep, H)
    add("face", tube([snout(-38, smile(38) + 1.5, 0.02)[0], snout(-38, smile(38) - 6.0, 0.04)[0], snout(-38, smile(38) - 13.0, 0.045)[0]],
                     [0.07, 0.06, 0.02], segs=6, rings=3), ivory, H)                                    # one small fang
    for sx in (-1, 1):                                                                                 # nostrils
        p, nrm = snout(21 * sx, 40.0)
        add("face", ball((0.12, 0.07, 0.17), cuts=1), deep, H @ seat(p, nrm, up=(0, -1, 0.6)))

    for sx in (-1, 1):
        p, nrm = face.hit((0.60 * sx, -9.0, 0.42), (0, 1, 0))
        E = seat(p - nrm * 0.02, nrm)
        add("eyes", ball((0.32, 0.20, 0.36), cuts=3), eye, H @ E)
        g = Vector((-0.30, -0.90, 0.30)).normalized()                     # one highlight, on the same side of both eyes
        add("face", ball((0.08, 0.04, 0.08), cuts=2), ivory, H @ E @ M((0.16 * g.x, 0.10 * g.y, 0.18 * g.z)))
        horn = [(0.50 * sx, 0.35, 0.62), (0.68 * sx, 0.62, 1.14), (0.86 * sx, 1.04, 1.56), (0.95 * sx, 1.50, 1.80), (0.96 * sx, 1.78, 1.88)]
        add("horns", tube(horn, [0.27, 0.24, 0.18, 0.11, 0.06], segs=10, rings=8), ivory, H)
        fin = smooth_outline([(0, 1.0), (0.24, 0.72), (0.36, 0.40), (0.26, 0.10), (0, -0.12), (-0.26, 0.10), (-0.36, 0.40), (-0.24, 0.72)], per=2)
        add("ears", lens([(a * 0.85, b * 0.9) for a, b in fin], 0.16, centre=(0.0, 0.36)), skinm,
            H @ M((0.98 * sx, 0.42, 0.10), rot=(0, 58 * sx, 28 * sx)))
    for back, size in ((0.02, 0.46), (0.52, 0.56)):                       # two plates on top of the head carry the row forward
        p, _ = face.hit((0, back, 5.0), (0, 0, -1))
        add("back plates", lens(arch(size, size * 0.86), 0.06 + 0.2 * size, centre=(0.05 * size, 0.24 * size)), coral,
            H @ stand(p - Vector((0, 0, 0.03)), (0, 1, 0), (0, 0, 1)))
    add("head", head, teal, H)

    d.build(SCALE)
    return d


def bake(dragon, texture):
    """Everything but the glossy eyes becomes one textured mesh: the scale pattern, the tones and soft
    shading in the creases are baked into its colour image. Roblox gets two MeshParts."""
    eyes = [ob for ob in dragon.objects if ob.name.endswith("_Eye")]
    body = kit.bake_texture([ob for ob in dragon.objects if ob not in eyes], texture, name="Dragon_Body",
                            shade=0.5, soften=2, rough=0.85, sheen=0.2, uv_angle=85.0, uv_margin=0.004)   # round 5: a sharper texture
    for ob in eyes:
        ob.name = ob.data.name = "Dragon_Eyes"
    dragon.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,side,front,back 3/4")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Dragon review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "dragon_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    dragon = build()
    print("triangles by part:", dict(sorted(dragon.tally.items(), key=lambda kv: -kv[1])))
    focus = (-1.0 * SCALE, -3.6 * SCALE, 5.15 * SCALE)

    def rig_for(samples):
        import review
        rig = review.Rig(dragon, samples=samples, focus=focus)
        look = Vector(focus) + Vector((0.25, 0.5, 0.0))                   # one more camera, tight on the face
        rig.cams["face"] = review._camera("C_face", look + Vector((-0.42, -1.0, 0.10)).normalized() * 7.2, look, 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), a.look) for v in a.views.split(",")], px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(dragon, os.path.abspath(a.texture))
    tris = dragon.triangles()
    lo, hi = dragon.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = dragon.objects[0].data                                            # how much texture each stud of surface gets
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(dragon.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        rig, review = rig_for(40)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            quick = [("front 3/4", "full"), ("close-up", "full"), ("face", "full"), ("game distance", "full")]
            rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
