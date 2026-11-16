"""SunDragon pet, hero-quality remake: a golden sun dragon on long legs, with a crest of red-orange blade
spines from the brow down the neck, swept-back pale-gold horns, half-raised warm wings and a flame at the
tail tip. Built from scratch by script, on the methods of the Dragon (models/pets/dragon.py), FrostWolf and
LavaWolf.

    python models/pets/sundragon.py --review out/sundragon.png
    python models/pets/sundragon.py --export models/export/sundragon.fbx

Round history: see the bottom of this docstring (filled in as the rounds go).
"""
import argparse
import bisect
import math
import os
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

NAME = "SunDragon"
SCALE = 0.46                       # built in the Dragon's units, then scaled to pet size
THREADS = 4
HEAD_AT = (-0.30, -4.55, 8.35)     # the back of the skull
HEAD_ROT = (5, 1, -6)             # nose a little down, a small tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.08
BROW_LIFT, BROW_WIDTH = 0.085, 0.075   # the brow shelf raised out of the skull over each eye
LEG_DROP = 0.8                     # the lower legs are shortened by this much after building

# The upper head (skull and snout) as sections from the back of the skull to the nose:
# y (nose towards -y), top z, half width of the top plane, cheek z, cheek half width, lip z, lip half width.
SKULL = [
    (0.30, 0.14, 0.09, 0.00, 0.18, -0.13, 0.13),
    (0.16, 0.36, 0.24, 0.07, 0.44, -0.19, 0.33),
    (-0.15, 0.45, 0.30, 0.05, 0.54, -0.20, 0.42),
    (-0.50, 0.44, 0.28, 0.02, 0.47, -0.195, 0.38),
    (-0.82, 0.35, 0.22, -0.02, 0.34, -0.185, 0.31),
    (-1.22, 0.27, 0.18, -0.05, 0.27, -0.175, 0.25),
    (-1.62, 0.21, 0.135, -0.07, 0.2, -0.165, 0.19),
    (-1.95, 0.16, 0.1, -0.07, 0.14, -0.15, 0.13),
    (-2.12, 0.08, 0.06, -0.08, 0.09, -0.13, 0.07),
]
# The lower jaw: y, top z, top half width, jaw-corner z, jaw-corner half width, chin-keel z.
JAW = [
    (0.10, -0.17, 0.3, -0.44, 0.3, -0.52),
    (-0.12, -0.165, 0.38, -0.50, 0.36, -0.62),
    (-0.50, -0.165, 0.34, -0.43, 0.29, -0.52),
    (-0.95, -0.16, 0.27, -0.35, 0.22, -0.41),
    (-1.45, -0.155, 0.2, -0.30, 0.155, -0.34),
    (-1.80, -0.15, 0.15, -0.26, 0.105, -0.29),
    (-1.95, -0.15, 0.07, -0.22, 0.05, -0.24),
]


def smooth(x, a, b):
    """0 at a, 1 at b, smooth in between (a may be larger than b)."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


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


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (a + ab * t - p).length


def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def layer(bm, name):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def set_grad(bm, fn):
    """Give every vertex a value in the layer "grad" (0 at the root of a horn, 1 at its tip)."""
    lay = layer(bm, "grad")
    for v in bm.verts:
        v[lay] = max(0.0, min(1.0, fn(v.co)))
    return bm


def sharpen(bm, degrees):
    """Mark the edges where the surface turns by more than `degrees` as sharp: crisp creases."""
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def tones(mat, up=None, down=None, up_mix=0.5, down_mix=0.4):
    """Where the surface faces up the colour turns towards `up`, where it faces down towards `down`."""
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


def ramp_by(mat, attr, stops):
    """Colour a patterned material along a ramp read from the vertex value `attr` (0 to 1)."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', attr
    ramp = new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
    for pos, hexcode in stops[1:-1]:
        e = els.new(pos)
        e.color = (*kit.srgb(hexcode), 1.0)
    link(a.outputs["Fac"], ramp.inputs["Fac"])
    link(ramp.outputs["Color"], hsv.inputs["Color"])
    return mat


# ---- shapes ------------------------------------------------------------------------------------------

def profile_round(k=10, n=2.0):
    return [_super(math.pi / 2 + 2 * math.pi * j / k, n) for j in range(k)]


# Cross-sections, (side, up), going round. Each has a sharp ridge at its top.
P_HORN = [(0, 1.0), (0.55, 0.5), (0.8, -0.05), (0.6, -0.6), (0, -0.85), (-0.6, -0.6), (-0.8, -0.05), (-0.55, 0.5)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]
P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]


def loft(points, radii, profile, up=(0, 0, 1), rings=None, grad=True):
    """The 2D `profile` carried along a smooth path through `points`, its up side turned as near
    `up` as it can be (one vector, or one per point). Radii are numbers or (side, up) pairs. Every
    vertex stores how far along it is (0 to 1) in the layer "grad"."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = rings or (n - 1) * 4
    ups = [Vector(u) for u in up] if isinstance(up[0], (tuple, list, Vector)) else [Vector(up)] * n
    rad = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]
    bm = bmesh.new()
    lay = layer(bm, "grad")
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
            v[lay] = i / rings if grad else 0.0
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


def lens(outline, thick, rows=((0.55, 0.8), (1.0, 0.0)), centre=(0.0, 0.0)):
    """A flat blade or pebble: `thick` through the middle and thinning to a sharp rim, with the
    outline given as (a, b) points going round `centre`. It lies in the XZ plane."""
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


def bezier(p0, c, p1, steps):
    p0, c, p1 = Vector(p0), Vector(c), Vector(p1)
    return [tuple((1 - u) ** 2 * p0 + 2 * (1 - u) * u * c + u * u * p1) for u in (i / steps for i in range(steps))]


def blade_outline(h, length, sweep=0.5, sink=0.4, steps=5):
    """The side view of a dorsal blade `h` tall: a convex front edge sweeping back to a sharp tip and
    a hollow back edge, carried on below the skin by `sink` of its height so its foot is buried."""
    tip = (sweep * h, h)
    front = bezier((-length / 2, 0.0), (-length * 0.38, h * 0.62), tip, steps)
    back = bezier(tip, (length * 0.12 + sweep * h * 0.45, h * 0.22), (length / 2, 0.0), steps)
    return front + back + [(length / 2, 0.0), (length * 0.4, -sink * h), (-length * 0.4, -sink * h)]


def stand(origin, across, up):
    """A transform that stands a lens() at `origin`: its length runs `across`, its height `up`."""
    z = Vector(up).normalized()
    x = Vector(across)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def facing(origin, out, along):
    """A transform for a shape lying on a surface: its X runs `along`, its Y looks out of the surface
    along `out` (a lens() lies flat on it), its Z completes the frame."""
    y = Vector(out).normalized()
    x = Vector(along)
    x = (x - y * x.dot(y)).normalized()
    z = x.cross(y)
    if z.z < 0:                                      # keep the shape's top up on both sides of the body
        y, z = -y, -z
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


class Skin:
    """A smooth skin over sections along a path: the neck, trunk and tail in one piece. Positions on
    it are (s, angle): s is the distance along the path from the head end, the angle goes round the
    section in degrees, 90 at the spine and -90 at the belly. Each section is x, y, z, half width,
    height above the centre line, depth below it, squareness, and a keel: a ridge along the spine."""

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

    def line(self, th, step=0.02):
        n = int(self.L / step)
        ss = [self.L * i / n for i in range(n + 1)]
        pts = [self.bare(s, th) for s in ss]
        run = [0.0]
        for a, b in zip(pts, pts[1:]):
            run.append(run[-1] + (b - a).length)
        return ss, run

    @staticmethod
    def along(line, d):
        ss, run = line
        i = min(max(bisect.bisect_right(run, d) - 1, 0), len(ss) - 2)
        return ss[i] + (ss[i + 1] - ss[i]) * (d - run[i]) / max(run[i + 1] - run[i], 1e-9)

    @staticmethod
    def run_at(line, s):
        ss, run = line
        i = min(max(bisect.bisect_right(ss, s) - 1, 0), len(ss) - 2)
        return run[i] + (run[i + 1] - run[i]) * (s - ss[i]) / max(ss[i + 1] - ss[i], 1e-9)

    def rings(self, k=0.4, lo=0.12, hi=0.4):
        s, out = 0.0, [0.0]
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            out.append(s)
        return out + [self.L]

    def mesh(self, segs=24, cuts=()):
        """The skin as one mesh. At each section number in `cuts` it is split into separate pieces
        (the same points, the edges unjoined), so the texture unwrap gets compact islands and not one
        long one curling round the tail."""
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


def plate(skin, s0, s1, half, centre=-90.0, lift=(0.03, 0.11), bow=0.0, pinch=0.2, tuck=-0.02,
          vs=(0, 0.12, 0.45, 0.8, 0.94, 1), qs=(-1, -0.9, -0.55, -0.2, 0.2, 0.55, 0.9, 1)):
    """A plate lying on the skin from s0 to s1, `half` degrees to each side of the angle `centre`,
    rising from lift[0] at its head end to lift[1] at its tail end like a roof tile."""
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


def shell(sections, corners, per=3, m=2, back_cap=0.0, nose_cap=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives the outline of one
    section as (x, z) corner points going round. Straight sides between corners make flat planes."""
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


def skull_at(y):
    """The SKULL section at y, read straight off the table."""
    rows = SKULL
    for a, b in zip(rows, rows[1:]):
        if b[0] <= y <= a[0]:
            f = (y - a[0]) / (b[0] - a[0])
            return tuple(p + (q - p) * f for p, q in zip(a, b))
    return rows[0] if y > rows[0][0] else rows[-1]


def skull_corners(sec):
    y, zt, wt, zc, wc, zb, wb = sec
    return [(0, zt + 0.05), (-wt, zt), (-wc, zc), (-wb, zb), (0, zb - 0.01), (wb, zb), (wc, zc), (wt, zt)]


def jaw_corners(sec):
    y, zt, wt, zj, wj, zk = sec
    return [(0, zt), (-wt, zt), (-wj, zj), (0, zk), (wj, zj), (wt, zt)]


def membrane(wrist, rim, scallop, billow, back, thick=0.07, cols=5, ts=(0.3, 0.58, 0.82, 0.94, 1.0)):
    """A wing membrane: a fan of skin round the wrist out to the points of `rim`. Between rim[k] and
    rim[k+1] the edge dips in by scallop[k] and the panel billows towards `back` by billow[k]. It is
    a closed shape `thick` through, thinning to nothing at its edges."""
    w = Vector(wrist)
    spokes = []
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


class Surface:
    """Finds points exactly on a mesh, so that details sit on it and neither float nor sink."""

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
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


def gloss(mat, strength=0.55, tint="#B8BCC8", light=(-0.45, -0.6, 0.66), lo=0.78, hi=0.98, sheen=0.0):
    """Paint a sharp highlight into the colour where the surface faces `light`: a glossy look that
    survives the bake into one matte texture (Roblox reads the colour, not the shine)."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    src = next((l.from_socket for l in tree.links if l.to_socket == hsv.inputs["Color"]), None)
    geo = new("ShaderNodeNewGeometry")
    dot = new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    link(geo.outputs["Normal"], dot.inputs[0])
    dot.inputs[1].default_value = Vector(light).normalized()
    rng = new("ShaderNodeMapRange")
    rng.interpolation_type = 'SMOOTHSTEP'
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = lo, hi
    rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = sheen, strength
    link(dot.outputs["Value"], rng.inputs["Value"])
    mix = new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    link(rng.outputs["Result"], mix.inputs[0])
    if src is not None:
        link(src, mix.inputs[6])
    else:
        mix.inputs[6].default_value = tuple(hsv.inputs["Color"].default_value)
    mix.inputs[7].default_value = (*kit.srgb(tint), 1.0)
    link(mix.outputs[2], hsv.inputs["Color"])
    return mat


def dome(mat, amount=0.35):
    """Shade each scale of a scaly() material like a low dome: lighter in the middle, darker at the
    rim, so the scales read as raised tiles and not as a drawn net."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    mapping = next(n for n in tree.nodes if n.type == 'MAPPING')
    src = next(l.from_socket for l in tree.links if l.to_socket == hsv.inputs["Value"])
    vor = new("ShaderNodeTexVoronoi")
    vor.feature = 'F1'
    vor.inputs["Scale"].default_value = 1.0
    link(mapping.outputs["Vector"], vor.inputs["Vector"])
    shade = new("ShaderNodeMath")
    shade.operation = 'MULTIPLY_ADD'                  # 1 + amount * (0.3 - distance) * 2
    shade.inputs[1].default_value, shade.inputs[2].default_value = -2 * amount, 1 + 0.6 * amount
    link(vor.outputs["Distance"], shade.inputs[0])
    both = new("ShaderNodeMath")
    both.operation = 'MULTIPLY'
    link(src, both.inputs[0])
    link(shade.outputs[0], both.inputs[1])
    link(both.outputs[0], hsv.inputs["Value"])
    return mat


def ridged(points, r0, r1, ridges=5, upto=0.36, depth=0.16, dense=28, power=1.0):
    """A horn path resampled densely with its radius falling from r0 to r1, ringed with `ridges`
    raised growth rings over the first `upto` of its length."""
    pts = [Vector(p) for p in points]
    n = len(pts) - 1
    path, radii = [], []
    for i in range(dense + 1):
        t = i / dense
        path.append(tuple(_cr(pts, t * n)))
        r = r1 + (r0 - r1) * (1 - t) ** power
        if t < upto:
            ring = max(0.0, math.cos(2 * math.pi * ridges * t / upto)) ** 3
            r *= 1 + depth * ring * (1 - t / upto * 0.5)
        radii.append(r)
    return path, radii


def mass(points, radii, up, rings=None):
    """A muscle: a smooth teardrop mass along `points` (round section, flattened by the radii)."""
    return loft(points, radii, profile_round(10, 2.2), up=up, rings=rings or (len(points) - 1) * 3, grad=False)


def _hemisphere():
    """Ray directions spread over the hemisphere round +Z, out to nearly grazing."""
    out = [Vector((0, 0, 1))]
    for tilt, n in ((25, 6), (50, 9), (72, 12), (86, 14)):
        t = math.radians(tilt)
        for j in range(n):
            a = 2 * math.pi * (j + 0.5 * (tilt // 25 % 2)) / n
            out.append(Vector((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))))
    return out


MEMBRANE_HID = 0.6         # the wing membranes get about 0.55 of the texture size the body gets
OPEN_FULL = 0.4            # a face that sees at least this much of the sky counts as fully seen


def cull_and_weigh(parts, keep=("GLOW", "Membrane")):
    """Delete the faces no camera can see (buried in another shape, tucked under a plate, flat on the
    floor) and mark the barely seen ones with the face value "hid" (0 seen to 1 hidden), so the unwrap
    can give them less of the texture. Returns the number of triangles removed."""
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
        if "Membrane" in key:                # big smooth panels: they keep their look at a lower texture density
            for f in bm.faces:
                f[lh] = MEMBRANE_HID
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
            o = c + n * 0.004
            free = sum(1 for d in world if bvh.ray_cast(o, d, 60.0)[0] is None)
            if free == 0:
                seen = False
                for p in [c.lerp(v.co, 0.8) for v in f.verts[:8]]:
                    o = p + n * 0.004
                    if any(bvh.ray_cast(o, d, 60.0)[0] is None for d in world):
                        seen = True
                        break
                if not seen:                     # a face turned the wrong way would look buried: try its back too
                    o = c - n * 0.004
                    if sum(1 for d in world if bvh.ray_cast(o, -d, 60.0)[0] is None) < len(dirs) // 3:
                        dead.append(f)
                        continue
            f[lh] = max(0.0, min(1.0, 1.0 - free / len(dirs) / OPEN_FULL)) - (f[lb] if lb else 0.0)
        removed += sum(len(f.verts) - 2 for f in dead)
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return removed



UV_ANGLE, UV_MARGIN, PACK_MARGIN = 85.0, 0.004, 0.003
HIDDEN_SHARE = 0.25           # a barely seen surface gets this much of the texture size a seen one gets (in each direction)
HEAD_BOOST = 0.45             # the head's surfaces get 1 + 0.75 * this of the texture size the body gets
EMBER = "#FF9638"             # the soft sunlight in the seams between the plates
EMBER_HOT = "#FFD47A"         # ... in the deepest part of a seam
EMBER_REACH = 0.16 * SCALE    # crevice shading from shapes this close
EMBER_FROM, EMBER_TO, EMBER_MAX = 0.15, 0.55, 0.7
BAKE_SHADE = 0.5              # how dark the deepest crease gets in the bake


def weigh_islands(ob, keep=HIDDEN_SHARE):
    """In edit mode, after the unwrap: shrink every texture island that is mostly hidden (the face
    value "hid") about its centre, so that the packing gives the seen surfaces more pixels."""
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
        k = 1.0 - (1.0 - keep) * w                 # below 1 for the hidden, above 1 for the boosted head
        loops = [l for f in faces for l in f.loops]
        c = sum((l[uvl].uv for l in loops), Vector((0.0, 0.0))) / len(loops)
        for l in loops:
            l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(me)


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




def gold_vary(mat, warm="#C8842A", pale="#F6D068", amount=0.4, broad=0.6):
    """Give each scale of a scaly() material its own shade of gold, from warm amber to pale gold, and drift
    the colour slowly over the body: the metallic gold feel comes from the colour varying, not from shine."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    mapping = next(n for n in tree.nodes if n.type == 'MAPPING')
    src = next((l.from_socket for l in tree.links if l.to_socket == hsv.inputs["Color"]), None)
    cell = new("ShaderNodeTexVoronoi")
    cell.feature = 'F1'
    cell.inputs["Scale"].default_value = 1.0
    link(mapping.outputs["Vector"], cell.inputs["Vector"])
    sep = new("ShaderNodeSeparateColor")
    link(cell.outputs["Color"], sep.inputs[0])
    coord = next(n for n in tree.nodes if n.type == 'TEX_COORD')
    drift = new("ShaderNodeTexNoise")
    drift.inputs["Scale"].default_value, drift.inputs["Detail"].default_value = 0.9 / SCALE, 1.0
    link(coord.outputs["Object"], drift.inputs["Vector"])
    t = _math(tree, 'ADD', _math(tree, 'MULTIPLY', sep.outputs[0], 1.0 - broad), _math(tree, 'MULTIPLY', drift.outputs["Fac"], broad))
    ramp = new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.25, (*kit.srgb(warm), 1.0)
    els[1].position, els[1].color = 0.75, (*kit.srgb(pale), 1.0)
    link(t, ramp.inputs["Fac"])
    mix = new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs[0].default_value = amount
    if src is not None:
        link(src, mix.inputs[6])
    else:
        mix.inputs[6].default_value = tuple(hsv.inputs["Color"].default_value)
    link(ramp.outputs["Color"], mix.inputs[7])
    link(mix.outputs[2], hsv.inputs["Color"])
    return mat


def drape(bm, surf, p, n, base):
    """Lay a flat shape built on the plane through p (normal n) onto the curve of `surf`: each vertex keeps
    its height above that plane, measured from the surface instead, plus `base`."""
    n = Vector(n).normalized()
    for v in bm.verts:
        h = (v.co - p).dot(n)
        flat = v.co - n * h
        loc, _ = surf.ray(flat + n * 0.3, -n, 0.6)
        if loc is not None:
            v.co = loc + n * (base + h)
    return bm


def smooth_outline(pts8, k=16):
    """A smooth closed outline of k points through the 8 given (fewer showed facets on the eyes)."""
    out = []
    n = len(pts8)
    for j in range(k):
        t_ = j * n / k
        i0 = int(t_)
        p4 = [Vector(pts8[(i0 + d) % n]) for d in (-1, 0, 1, 2)]
        q = _cr(p4, 1.0 + (t_ - i0))
        out.append((q.x, q.y))
    return out


def head_matrix():
    return M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)


# ---- the sun dragon ----------------------------------------------------------------------------------

def build():
    S = SCALE
    EYE_H.clear()
    scale = kit.scaly(kit.material("Scale", "#E0AA3E"), size=0.11 * S, joins=0.18, vary=0.1, rough=0.8)
    tones(scale, up="#B47A26", down="#F2CF7E", up_mix=0.38, down_mix=0.45)
    dome(scale, 0.12)
    gold_vary(scale)
    gloss(scale, strength=0.22, tint="#FFE9A8", light=(-0.45, -0.6, 0.66), lo=0.72, hi=0.99)
    hide = kit.scaly(kit.material("Hide", "#E2AC42"), size=0.16 * S, joins=0.22, vary=0.1, rough=0.8)
    tones(hide, up="#B47A26", down="#F2CF7E", up_mix=0.38, down_mix=0.45)
    dome(hide, 0.14)
    gold_vary(hide)
    gloss(hide, strength=0.22, tint="#FFE9A8", light=(-0.45, -0.6, 0.66), lo=0.72, hi=0.99)
    belly = kit.scaly(kit.material("Belly", "#F0DCA2"), size=0.4 * S, joins=0.22, vary=0.1, rough=0.7)
    tones(belly, up="#FBEDC4", down="#C99C56", up_mix=0.35, down_mix=0.45)
    horn = kit.scaly(kit.material("Horn", "#C8963E"), size=0.6 * S, joins=0.04, vary=0.05, rough=0.55)
    ramp_by(horn, "grad", [(0.0, "#4E2A10"), (0.45, "#7A4C1A"), (0.85, "#9C6E30"), (1.0, "#C49A58")])
    gloss(horn, strength=0.08, tint="#E8CC90", light=(-0.25, -0.35, 0.9), lo=0.95, hi=0.997)
    blade = kit.scaly(kit.material("Blade", "#C8361A"), size=0.6 * S, joins=0.04, vary=0.06, rough=0.6)
    ramp_by(blade, "grad", [(0.0, "#6E1E08"), (0.35, "#B4360E"), (0.7, "#E05A18"), (1.0, "#F68A30")])
    armour = kit.scaly(kit.material("Armour", "#D6A040"), size=0.55 * S, joins=0.1, vary=0.08, rough=0.6)
    tones(armour, up="#B47E2A", down="#EED08A", up_mix=0.4, down_mix=0.4)
    gloss(armour, strength=0.3, tint="#FFF0C8", light=(-0.25, -0.35, 0.9), lo=0.93, hi=0.997)
    web = kit.scaly(kit.material("Membrane", "#D2481C"), size=0.32 * S, joins=0.14, vary=0.08, rough=0.75)
    ramp_by(web, "web", [(0.0, "#8A2210"), (0.35, "#C2381A"), (0.75, "#E86622"), (1.0, "#F4983E")])
    facem = kit.scaly(kit.material("Face", "#E0AA3E"), size=0.08 * S, joins=0.18, vary=0.08, rough=0.8)
    tones(facem, up="#C08A2E", down="#F2D690", up_mix=0.3, down_mix=0.5)
    gold_vary(facem, amount=0.35)
    gloss(facem, strength=0.2, tint="#FFE9A8", light=(-0.45, -0.6, 0.66), lo=0.74, hi=0.99)
    dark = kit.material("Dark", "#2A1206", rough=0.7)
    glow = kit.material("GLOW_Sun", "#FFA634", rough=0.4, emit=1.5)

    d = Prop(NAME)
    d.tally = {}
    GLOSS = {"Armour": 0.4, "Horn": 0.25, "Blade": 0.0, "Belly": 0.15, "Scale": 0.22, "Hide": 0.22, "Face": 0.2}

    def add(part, bm, mat, at=None, crease=40.0, ember=0.0, boost=None):
        for name in ("grad", "web"):
            layer(bm, name)
        le, lg = layer(bm, "ember"), layer(bm, "gloss")    # the sunlit seams (sun_seams) and the shine (rough_map)
        gl = GLOSS.get(mat.name.split(".")[0], 0.0)
        for v in bm.verts:
            v[le] = ember
            v[lg] = gl
        lb = bm.faces.layers.float.get("boost") or bm.faces.layers.float.new("boost")
        if boost is None:
            boost = HEAD_BOOST if at is not None and at is H else 0.0
        for f in bm.faces:
            f[lb] = boost
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
        if crease:
            sharpen(bm, crease)
        d.tally[part] = d.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        d.add(bm, mat)

    H = head_matrix()

    # ---- neck, trunk and tail: one skin --------------------------------------------------------------
    def hs(p):
        return tuple(H @ Vector(p))

    spine = [
        (*hs((0, -0.20, -0.14)), 0.30, 0.28, 0.28, 2.2, 0.0),   # 0  inside the head
        (*hs((0, 0.28, -0.26)), 0.32, 0.32, 0.34, 2.2, 0.03),   # 1  behind the skull
        (-0.24, -4.12, 7.86, 0.42, 0.42, 0.46, 2.2, 0.04),      # 2  upper neck, rising under the head
        (-0.16, -3.98, 7.25, 0.5, 0.49, 0.58, 2.25, 0.05),      # 3
        (-0.08, -3.72, 6.62, 0.62, 0.58, 0.74, 2.3, 0.06),      # 4  the neck leans forward out of the chest
        (-0.03, -3.22, 6.06, 0.8, 0.7, 0.98, 2.35, 0.07),       # 5  neck base
        (0.00, -2.35, 5.70, 0.98, 0.82, 1.28, 2.4, 0.08),       # 6  deep chest
        (0.00, -1.55, 5.55, 1.02, 0.86, 1.18, 2.5, 0.09),       # 7  shoulders
        (0.00, -0.50, 5.58, 0.78, 0.68, 0.74, 2.45, 0.09),      # 8  narrow waist
        (0.00, 0.45, 5.62, 0.78, 0.68, 0.72, 2.45, 0.09),       # 9
        (0.00, 1.35, 5.62, 0.90, 0.78, 0.76, 2.5, 0.09),        # 10 hips
        (0.00, 2.25, 5.38, 0.68, 0.62, 0.58, 2.4, 0.08),        # 11 rump
        (-0.03, 3.10, 4.92, 0.50, 0.47, 0.45, 2.3, 0.07),       # 12 tail root
        (-0.10, 3.95, 4.25, 0.44, 0.41, 0.40, 2.25, 0.06),      # 13
        (-0.25, 4.75, 3.45, 0.37, 0.35, 0.34, 2.2, 0.05),       # 14
        (-0.50, 5.45, 2.75, 0.31, 0.29, 0.29, 2.2, 0.045),      # 15
        (-0.95, 6.0, 2.15, 0.26, 0.25, 0.25, 2.2, 0.04),        # 16
        (-1.60, 6.35, 1.78, 0.22, 0.21, 0.21, 2.2, 0.035),      # 17
        (-2.35, 6.42, 1.68, 0.18, 0.18, 0.18, 2.2, 0.03),       # 18
        (-3.0, 6.2, 2.15, 0.15, 0.15, 0.15, 2.2, 0.025),        # 19
        (-3.3, 5.8, 2.9, 0.12, 0.12, 0.12, 2.2, 0.02),          # 20 the tip, curling up, where the flame sits
    ]
    skin = Skin(spine, 7)
    body = skin.mesh(segs=20, cuts=(3.0, 5.6, 8.2, 10.9, 13.2, 15.4, 17.6))
    for v in body.verts:
        v.co.z = max(v.co.z, 0.0)
    kd = KDTree(len(skin.pts))
    for k, p in enumerate(skin.pts):
        kd.insert(p, k)
    kd.balance()
    trunk, rest = kit.split(body, lambda f: 5.6 <= kd.find(f.calc_center_median())[1] / skin.samples <= 13.2)
    add("skin", trunk, hide, crease=0)
    add("skin", rest, scale, crease=0)

    # ---- belly: cream plates from the throat to the tail ---------------------------------------------
    under = skin.line(-90.0)
    dist, stop = Skin.run_at(under, skin.s_of(1.15)), Skin.run_at(under, skin.s_of(17.5))
    while dist < stop:
        s0 = Skin.along(under, dist)
        i = skin.index_of(s0)
        size = _table([(1, 0.28), (3, 0.38), (5, 0.5), (7, 0.55), (10, 0.5), (12, 0.42), (15, 0.3), (17.5, 0.22)], i)
        half = _table([(1, 52), (4, 46), (6, 42), (8, 38), (11, 36), (14, 34), (17.5, 30)], i)
        s1 = Skin.along(under, dist + size * 1.22)
        p = plate(skin, s0, s1, half, lift=(0.02, 0.07), bow=0.0, pinch=0.06,
                  vs=(0, 0.1, 0.62, 0.95, 1), qs=(-1, -0.86, -0.3, 0.3, 0.86, 1))
        add("belly plates", p, belly, crease=50, ember=1.0)
        dist += size

    # ---- back plates: overlapping gold armour plates down the spine, under the crest ------------------
    ridge = skin.line(90.0)
    dist, stop = Skin.run_at(ridge, skin.s_of(2.2)), Skin.run_at(ridge, skin.s_of(16.5))
    while dist < stop:
        s0 = Skin.along(ridge, dist)
        i = skin.index_of(s0)
        size = _table([(2, 0.3), (4, 0.38), (6, 0.5), (7.5, 0.56), (9, 0.52), (10.5, 0.54), (12, 0.44), (14, 0.36), (16.5, 0.26)], i)
        half = _table([(2, 28), (5, 26), (7, 28), (8.5, 30), (10, 30), (12, 28), (16.5, 30)], i)
        s1 = Skin.along(ridge, dist + size * 1.25)
        add("back plates", plate(skin, s0, s1, half, centre=90.0, lift=(0.03, 0.1), pinch=0.25, bow=0.06,
                                 vs=(0, 0.15, 0.6, 0.92, 1), qs=(-1, -0.8, -0.3, 0.3, 0.8, 1)), armour, crease=40, ember=1.0)
        dist += size

    # ---- the crest: red-orange blade spines from behind the head down the neck and back, smaller on the tail
    dist, stop = Skin.run_at(ridge, skin.s_of(1.3)), Skin.run_at(ridge, skin.s_of(19.4))
    while dist < stop:
        s = Skin.along(ridge, dist)
        i = skin.index_of(s)
        size = _table([(1.3, 0.8), (2.2, 0.86), (3.2, 0.74), (4.2, 0.6), (5.5, 0.48), (7, 0.42), (8.5, 0.36), (10.5, 0.34),
                       (12, 0.3), (14, 0.25), (16, 0.2), (18, 0.16), (19.4, 0.13)], i)
        c, t, u = skin.at(s)[:3]
        top = skin.bare(s, 90.0)
        bm = lens(blade_outline(size, size * 0.8, sweep=0.62, steps=3), max(0.045, 0.11 * size), centre=(0.0, 0.25 * size))
        set_grad(bm, lambda co, h=size: 0.2 + 0.8 * max(co.z / h, 0.0))
        add("crest", bm, blade, stand(top + u * 0.04, t, u), crease=45)
        dist += size * (1.05 if i < 6 else 1.45)

    # ---- tail tip: a small sun flame cupped by three red blades ----------------------------------------
    c, t, u = skin.at(skin.L)[:3]
    side = t.cross(u).normalized()
    flame = [(0, 1.0), (0.1, 0.72), (0.22, 0.46), (0.28, 0.22), (0.2, 0.03), (0, -0.05), (-0.2, 0.03), (-0.28, 0.22),
             (-0.22, 0.44), (-0.09, 0.64)]
    for across in (side, u):
        bm = lens([(a * 0.74, b * 0.95) for a, b in flame], 0.16, rows=((0.55, 0.9), (1.0, 0.0)), centre=(0.0, 0.25))
        add("tail flame", bm, glow, stand(c - t * 0.1, across, t), crease=0)
    for ang in (-40, 40, 180):
        rot = Matrix.Rotation(math.radians(ang), 3, t)
        out = rot @ u
        bm = lens(blade_outline(0.42, 0.4, sweep=0.35, steps=3), 0.07, centre=(0.0, 0.1))
        set_grad(bm, lambda co: 0.25 + 0.75 * max(co.z / 0.42, 0.0))
        up_ = (out * 0.75 + t * 0.66).normalized()
        add("tail flame", bm, blade, stand(c - t * 0.22 + out * 0.04, t, up_), crease=45)

    # ---- legs: long and slender -----------------------------------------------------------------------
    def foot(x, y, yaw, size, hind):
        F = M((x, y, 0), rot=(0, 0, yaw), scale=size)
        add("feet", grounded(rounded_box((0.6, 0.78, 0.4), n=3.6, cuts=2), F @ M((0, 0.02, 0.18))), scale, crease=0)
        for k in (-1, 0, 1):
            ox = 0.2 * k
            reach = -0.06 if k else 0.0
            toe = [(ox * 0.8, -0.16, 0.22), (ox, -0.44 + reach, 0.18), (ox * 1.15, -0.62 + reach, 0.13)]
            add("feet", grounded(loft(toe, [0.13, 0.115, 0.09], P_CLAW, up=(0, 0, 1), rings=3), F), scale, crease=50)
            claw = [(ox * 1.15, -0.58 + reach, 0.15), (ox * 1.2, -0.76 + reach, 0.11), (ox * 1.22, -0.88 + reach, 0.0)]
            add("claws", grounded(loft(claw, [0.07, 0.045, 0.006], P_CLAW, up=(0, -0.3, 1), rings=5), F), horn, crease=50)
        if hind:
            claw = [(0, 0.28, 0.18), (0, 0.44, 0.1), (0, 0.52, 0.0)]
            add("claws", grounded(loft(claw, [0.065, 0.04, 0.006], P_CLAW, up=(0, 0.3, 1), rings=4), F), horn, crease=50)

    plates = []                               # (surface, ray origin, long axis, size, extra lift)
    for sx in (-1, 1):
        near = sx < 0
        step = 0.55 if near else 0.0
        elbow = Vector((1.0 * sx, -1.25 - 0.1 * near, 3.55))
        wrist = Vector((1.08 * sx, -1.85 - step, 1.0))
        arm = [(0.72 * sx, -1.75, 5.45), (0.98 * sx, -1.55, 4.55), tuple(elbow), tuple(elbow.lerp(wrist, 0.33) + Vector((0.02 * sx, 0.03, 0))),
               tuple(wrist), (1.1 * sx, -1.93 - step, 0.30)]
        bm = loft(arm, [(0.56, 0.7), (0.5, 0.6), (0.42, 0.46), (0.39, 0.43), (0.31, 0.33), (0.31, 0.33)], P_LEG, up=(0, -1, 0), rings=18)
        delt = mass([(0.78 * sx, -1.72, 5.55), (1.04 * sx, -1.72, 5.15), (1.12 * sx, -1.6, 4.6), (1.08 * sx, -1.45, 4.2)],
                    [(0.32, 0.38), (0.38, 0.46), (0.28, 0.34), (0.06, 0.08)], up=(0, -1, 0))
        tri = mass([(0.8 * sx, -1.25, 5.35), (1.0 * sx, -1.12, 4.75), (1.04 * sx, -1.15, 4.1)], [(0.28, 0.27), (0.28, 0.27), (0.08, 0.08)], up=(0, 1, 0))
        fore = mass([(1.07 * sx, -1.38 - 0.1 * step, 3.3), (1.1 * sx, -1.52 - 0.35 * step, 2.6), (1.1 * sx, -1.75 - 0.8 * step, 1.6)],
                    [(0.29, 0.27), (0.26, 0.26), (0.07, 0.07)], up=(0, -1, 0))
        limb = Surface(bm, delt, tri, fore)
        for z, ys, sz in ((5.42, (-1.9, -1.45), 0.52), (5.05, (-1.75, -1.3), 0.46)):
            for yy in ys:
                plates.append((limb, (3 * sx, yy, z), (0, 0.15, -1), (sz * 1.1, sz * 0.96), 0.04))
        plates.append((limb, (3 * sx, elbow.y - 0.28 - 0.25 * step, 2.75), wrist - elbow, (0.56, 0.32), 0.08))
        add("legs", bm, scale, crease=55)
        for m_ in (delt, tri, fore):
            add("muscle", m_, hide, crease=0)
        spur = [tuple(elbow + Vector((0, 0.08, 0.04))), tuple(elbow + Vector((0.02 * sx, 0.3, 0.1))), tuple(elbow + Vector((0.03 * sx, 0.46, 0.2)))]
        add("spurs", loft(spur, [0.09, 0.055, 0.008], P_CLAW, up=(0, 0, 1), rings=4), horn, crease=50)
        foot(1.1 * sx, -1.95 - step, 6 * sx, 1.15, False)

        thigh = [(0.62 * sx, 1.6, 5.6), (0.86 * sx, 1.15, 4.6), (0.98 * sx, 0.75, 3.5), (1.0 * sx, 0.8, 3.3)]
        bm = loft(thigh, [(0.66, 0.92), (0.58, 0.78), (0.36, 0.4), (0.3, 0.33)], P_LEG, up=(0, -1, 0.15), rings=12)
        glute = mass([(0.7 * sx, 2.1, 5.75), (1.02 * sx, 1.85, 5.25), (1.18 * sx, 1.5, 4.6), (1.12 * sx, 1.25, 4.0)],
                     [(0.3, 0.42), (0.4, 0.55), (0.32, 0.46), (0.08, 0.1)], up=(0, 1, 0.3))
        quad = mass([(0.85 * sx, 0.85, 5.2), (1.08 * sx, 0.7, 4.5), (1.12 * sx, 0.62, 3.8), (1.02 * sx, 0.68, 3.35)],
                    [(0.28, 0.32), (0.32, 0.38), (0.23, 0.26), (0.06, 0.06)], up=(0, -1, 0))
        haunch = Surface(bm, glute, quad)
        for z, ys, sz in ((5.3, (1.35, 1.9), 0.52), (4.9, (1.1, 1.65), 0.48), (4.5, (1.0,), 0.4)):
            for yy in ys:
                plates.append((haunch, (3 * sx, yy, z), (0, -0.25, -1), (sz * 1.1, sz * 0.96), 0.04))
        add("haunch", bm, hide, crease=55)
        for m_ in (glute, quad):
            add("muscle", m_, hide, crease=0)
        shin = [(0.98 * sx, 0.75, 3.4), (1.0 * sx, 1.3, 2.6), (1.0 * sx, 1.9, 1.75), (0.98 * sx, 1.72, 0.85), (0.97 * sx, 1.6, 0.28)]
        bm = loft(shin, [0.48, 0.42, 0.36, 0.34, 0.33], P_LEG, up=(0, -1, 0), rings=14)
        add("legs", bm, scale, crease=55)
        hock = [(1.0 * sx, 1.94, 1.78), (1.0 * sx, 2.2, 1.9), (1.01 * sx, 2.4, 2.06)]
        add("spurs", loft(hock, [0.1, 0.06, 0.008], P_CLAW, up=(0, 0, 1), rings=4), horn, crease=50)
        foot(0.97 * sx, 1.5, 4 * sx, 1.15, True)

    for sx in (-1, 1):
        add("muscle", mass([(0.24 * sx, -2.3, 5.8), (0.5 * sx, -2.7, 5.2), (0.66 * sx, -2.5, 4.65), (0.7 * sx, -2.25, 4.45)],
                           [(0.32, 0.34), (0.38, 0.42), (0.29, 0.3), (0.05, 0.05)], up=(0, -1, 0)), hide, crease=0)

    # ---- armour scales on the shoulders and thighs -----------------------------------------------------
    scute = [(-0.62, 0.0), (-0.3, 0.36), (0.12, 0.44), (0.5, 0.2), (0.62, -0.18), (0.42, -0.5), (0.0, -0.4), (-0.36, -0.24)]
    shield = [(0.5, 0.0), (0.28, 0.3), (-0.05, 0.46), (-0.4, 0.4), (-0.5, 0.0), (-0.4, -0.4), (-0.05, -0.46), (0.28, -0.3)]
    for limb, origin, along, size, tile in plates:
        origin = Vector(origin)
        try:
            p, nrm = limb.hit(origin, (-origin.x, 0, 0))
        except ValueError:
            continue
        down = abs(Vector(along).normalized().z) > 0.9
        outline = shield if down else scute
        thick = 0.09
        bm = lens([(a * size[0], b * size[1]) for a, b in outline], thick, rows=((0.35, 1.0), (1.0, 0.0)),
                  centre=(0.1 * size[0], -0.02 * size[1]) if not down else (0.12 * size[0], 0.0))
        T = facing(p, nrm, Vector(along))
        sign = 1.0 if T.col[1].xyz.dot(nrm) > 0 else -1.0
        for v in bm.verts:
            flat = T @ Vector((v.co.x, 0.0, v.co.z))
            try:
                q, _ = limb.hit(flat + nrm * 1.5, -nrm)
            except ValueError:
                q = flat
            rise = tile * max(0.0, 0.3 + v.co.x / size[0]) if down else tile * max(0.0, 0.45 - v.co.z / size[1])
            v.co = q + nrm * (v.co.y * sign + thick / 2 - 0.035 + rise)
        add("scutes", bm, armour, crease=30, ember=1.0)

    # ---- wings: smaller than the Dragon's, half raised and swept back ----------------------------------
    for sx, lift in ((-1, 0.0), (1, 0.2)):
        def P(x, y, z):
            return Vector((x * sx, y, z + lift * (z - 6.0) / 3.0))
        Sh, E, W = P(0.55, -0.85, 6.15), P(1.1, 0.05, 7.2), P(1.78, -0.32, 8.7)
        T = [P(2.6, 0.55, 9.3), P(3.15, 1.95, 8.35), P(2.9, 3.2, 7.2), P(2.05, 3.9, 6.4)]
        B = P(0.7, 2.0, 6.1)
        nrm = (T[1] - W).cross(B - W).normalized()
        back = nrm if nrm.y > 0 else -nrm
        bones = [(Sh, E), (E, W)] + [(W, tip) for tip in T]
        panels = (([T[0], T[1]], (0.14,), (0.1,)), ([T[1], T[2]], (0.18,), (0.12,)), ([T[2], T[3]], (0.18,), (0.12,)),
                  ([T[3], B, Sh, E], (0.22, 0.0, 0.0), (0.1, 0.0, 0.0)))
        for rim, scallop, billow in panels:
            web_bm = membrane(W, rim, scallop, billow, back, thick=0.06)
            lay = layer(web_bm, "web")
            for v in web_bm.verts:
                dd = min(_seg_dist(v.co, a, b) for a, b in bones)
                v[lay] = min(dd / 1.0, 1.0) ** 0.8
            add("membranes", web_bm, web, crease=0)
        outward = Vector((sx, 0, 0.3))
        add("wing arms", loft([Sh + Vector((-0.18 * sx, 0, -0.22)), Sh, (Sh + E) / 2 + Vector((0, 0, 0.1)), E, (E + W) / 2, W],
                              [0.3, 0.26, 0.2, 0.16, 0.13, 0.11], P_LEG, up=outward, rings=18), scale, crease=55)
        for k, tip in enumerate(T):
            bend = (tip - W).cross(back).normalized() * 0.06 * (1 if k < 2 else -1)
            pts = [W, W.lerp(tip, 0.5) + bend, tip + (tip - W).normalized() * 0.16]
            add("fingers", loft(pts, [0.09 - 0.008 * k, 0.055, 0.006], P_HORN, up=back, rings=6), scale, crease=55)
        hook = [W + Vector((0, 0, -0.04)), W + Vector((0.06 * sx, -0.14, 0.22)), W + Vector((0.04 * sx, -0.32, 0.32)), W + Vector((0, -0.46, 0.27))]
        add("wing claws", loft(hook, [0.09, 0.07, 0.04, 0.006], P_CLAW, up=(0, -0.3, 1), rings=6), horn, crease=50)

    # ---- head: everything placed in the head's own space, then turned as one ---------------------------
    skull = shell(SKULL, skull_corners, per=4, m=3, back_cap=0.06, nose_cap=0.02)
    face = Surface(skull)
    jaw = shell(JAW, jaw_corners, per=2, m=2, back_cap=0.05, nose_cap=0.02)
    add("head", jaw, facem, H, crease=38)

    EYE_RAY = ((0.75, -1.9, 0.26), (-0.35, 1.0, 0.0))
    eye8 = [(-0.5, -0.02), (-0.3, 0.15), (0.0, 0.205), (0.3, 0.17), (0.5, 0.04), (0.3, -0.11), (0.0, -0.15), (-0.3, -0.12)]
    eye = smooth_outline(eye8)
    for sx in (-1, 1):
        o = Vector((EYE_RAY[0][0] * sx, EYE_RAY[0][1], EYE_RAY[0][2]))
        dvec = Vector((EYE_RAY[1][0] * sx, EYE_RAY[1][1], EYE_RAY[1][2]))
        p, nrm = face.hit(o, dvec)
        EYE_H.append(p.copy())
        # the eye looks forward, about 30 degrees outward: its outline is laid onto the head along that
        # direction, so from the front it is a full almond, not a slit on the side of the skull
        look = Vector((0.5 * sx, -0.87, 0.1)).normalized()
        en = (nrm * 0.35 + look * 0.65).normalized()
        along = Vector((0.85 * sx, 0.45, 0.2))
        sock = lens([(a * 0.305, b * 0.345) for a, b in eye], 0.03, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        sock.transform(facing(p, en, along))
        add("sockets", drape(sock, face, p, en, 0.0), dark, H, crease=0)
        e = lens([(a * 0.26, b * 0.27) for a, b in eye], 0.03, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        e.transform(facing(p, en, along))
        add("eyes", drape(e, face, p, en, 0.012), glow, H, crease=0)
        # brow shelf: a level ridge above the eye with a clear gap, running back into the horn root
        brow = [p + Vector(q) for q in ((-0.07 * sx, -0.16, 0.13), (-0.02 * sx, 0.0, 0.16), (-0.02 * sx, 0.2, 0.17),
                                        (-0.05 * sx, 0.45, 0.18), (-0.09 * sx, 0.7, 0.18))]
        # a cheekbone low on the cheek and well behind the eye (higher it reads as a lower lid), and a raised
        # rim round each nostril
        cheek = [p + Vector(q) for q in ((0.05 * sx, 0.08, -0.22), (0.1 * sx, 0.36, -0.22), (0.08 * sx, 0.66, -0.18))]
        q, qn = face.hit((0.08 * sx, -2.4, 0.22), (0, 1, -0.5))
        # all three raised out of the skull itself (a separate brow shape left a dark gap that read as a drawn eyebrow)
        skull.normal_update()
        for line, height, width in ((brow, BROW_LIFT, BROW_WIDTH), (cheek, 0.06, 0.085), ([q, q + Vector((0, 0.05, 0))], 0.03, 0.05)):
            for v in skull.verts:
                dd = min(_seg_dist(v.co, a_, b_) for a_, b_ in zip(line, line[1:]))
                lift = height * math.exp(-(dd / width) ** 2)
                if lift > 1e-4:
                    v.co += v.normal * lift
        # nostrils: small dark slits on top of the snout tip
        add("nostrils", lens([(-0.5, 0), (0, 0.18), (0.5, 0.05), (0, -0.15)], 0.06, centre=(0, 0)), dark,
            H @ facing(q + qn * 0.004, qn, (sx * 0.4, 1, 0)) @ M(scale=(0.14, 1, 0.16)), crease=0, boost=HEAD_BOOST)
        # swept-back horns, pale gold, ridged at the root, the tips lifting a little
        hornpath = [(0.24 * sx, 0.0, 0.42), (0.46 * sx, 0.32, 0.68), (0.72 * sx, 0.72, 0.86), (0.98 * sx, 1.2, 0.94), (1.2 * sx, 1.7, 1.08)]
        path, radii = ridged(hornpath, 0.18, 0.012, ridges=5, upto=0.4, depth=0.12, dense=24, power=1.15)
        add("horns", loft(path, radii, P_HORN, up=(0.5 * sx, 0.3, 1), rings=24), horn, H, crease=50)
        # a frill of three red blades behind each cheek, swept back and out
        for y0, z0, h, out, dz in ((-0.08, 0.16, 0.5, 0.75, 0.55), (0.06, -0.02, 0.62, 0.95, 0.15), (0.18, -0.2, 0.56, 0.95, -0.2), (0.26, -0.38, 0.42, 0.8, -0.5)):
            base = Vector((0.36 * sx, y0, z0))
            up_ = Vector((out * sx, 0.55, dz)).normalized()
            bm = lens(blade_outline(h, h * 0.75, sweep=0.5, steps=3), 0.08, centre=(0.0, 0.25 * h))
            set_grad(bm, lambda co, h=h: 0.4 + 0.55 * max(co.z / h, 0.0))
            add("frill", bm, blade, H @ stand(base, (0, 1, 0), up_), crease=45, boost=HEAD_BOOST)
        # the closed mouth: a thin dark line along the lips, level, a touch higher at its back corner
        lip = [(skull_at(y)[6] * 0.97 * sx, y, skull_at(y)[5] - 0.005 + 0.03 * smooth(y, -0.3, 0.05)) for y in (0.05, -0.25, -0.55, -0.9, -1.25, -1.6, -1.85)]
        add("mouth", loft(lip, [0.006, 0.016, 0.018, 0.017, 0.015, 0.012, 0.004], profile_round(5), up=(0, 0, 1), rings=10, grad=False), dark, H, crease=0)

    # the crest begins on the head: blades rising along the top of the skull, tallest at the back
    # a centre row, and a shorter row each side leaning out, so from the front the crest is a spiky fan
    for x0, y0, h, lean in ((0, -0.9, 0.16, 0), (0, -0.6, 0.26, 0), (0, -0.3, 0.38, 0), (0, 0.02, 0.52, 0),
                            (0.17, -0.5, 0.18, 0.45), (0.19, -0.2, 0.26, 0.5), (0.18, 0.08, 0.32, 0.55),
                            (-0.17, -0.5, 0.18, -0.45), (-0.19, -0.2, 0.26, -0.5), (-0.18, 0.08, 0.32, -0.55)):
        p, _ = face.hit((x0, y0, 3.0), (0, 0, -1))
        bm = lens(blade_outline(h, h * 0.85, sweep=0.6, steps=3), 0.085 if x0 == 0 else 0.07, centre=(0, 0.25 * h))
        set_grad(bm, lambda co, h=h: 0.2 + 0.8 * max(co.z / h, 0.0))
        add("crest", bm, blade, H @ stand(p - Vector((0, 0, 0.03)), (0, 1, 0), (lean, 0.25, 1)), crease=45, boost=HEAD_BOOST)
    add("head", skull, facem, H, crease=38)

    # shorten the lower legs: everything above the ankles comes down by LEG_DROP, the feet stay put
    for bm, _ in d.parts.values():
        for v in bm.verts:
            v.co.z -= LEG_DROP * smooth(v.co.z, 0.5, 3.2)
    cut = cull_and_weigh(d.parts)
    print("  hidden faces removed: %d triangles" % cut)
    d.build(scale=SCALE)
    for ob in d.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return d


EYE_H = []


def _math(tree, op, a, b, c=None):
    n = tree.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b) if c is None else (a, b, c)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            tree.links.new(v, n.inputs[i])
    return n.outputs[0]


def sun_seams(ob, path, size):
    """After the bake (the Dragon's ember seams, softened): where the plates (vertex value "ember") sink into
    a tight crevice, warm the colour towards a soft sunlit gold, so the seams read as thin lines of light.
    Two quick bakes into the texture's own layout: the mask and a short reach crevice shading."""
    import numpy as np
    sc = bpy.context.scene
    keep_samples = sc.cycles.samples
    world = sc.world
    if world is None:
        world = sc.world = bpy.data.worlds.new("BakeWorld")
    keep_reach = world.light_settings.distance
    world.light_settings.distance = EMBER_REACH
    baked = ob.data.materials[0]
    m = bpy.data.materials.new("SunMask")
    kit.principled(m)
    tree = m.node_tree
    a = tree.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "ember"
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(a.outputs["Fac"], em.inputs["Color"])
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    tree.links.new(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new("sun_mask", size, size, alpha=False, float_buffer=True)
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

    def ss(x, a_, b_):
        t = np.clip((x - a_) / (b_ - a_), 0.0, 1.0)
        return t * t * (3 - 2 * t)
    occ = 1.0 - ao
    k = mask * EMBER_MAX * ss(occ, EMBER_FROM, EMBER_TO)
    hot = ss(occ, (EMBER_FROM + EMBER_TO) / 2, EMBER_TO + 0.15)
    glow = np.array(kit.srgb(EMBER), dtype=np.float32) * (1 - hot) + np.array(kit.srgb(EMBER_HOT), dtype=np.float32) * hot
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    px[..., :3] = px[..., :3] * (1 - k) + glow * k
    tex.pixels.foreach_set(px.ravel())
    tex.filepath_raw, tex.file_format = path, 'PNG'
    tex.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)


def rough_map(body, texture, base, vary=0.1):
    """A baked roughness image the size of the colour image: `base`, lower where a shape was marked
    glossy (vertex layer 'gloss': horns, claws, armour), broken up by fine and broad noise. Saved as
    <name>_rough.png and wired into the baked material."""
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


JUNK = ("hid", "boost", "ember", "grad", "web", "gloss")


def bake(dragon, texture):
    """Everything that does not glow becomes one textured mesh, SunDragon_Body: the scales, tones and soft
    crease shading baked into one colour image (1024, 512 under PETS_FAST), packed by real outlines with the
    barely seen surfaces given less of it; then the sunlit seams and a baked roughness image. The glowing
    parts (eyes and the tail flame) join into SunDragon_GLOW. Objects are matched by name prefix, since
    Blender renames shared materials ("GLOW_Sun.001") when several pets share a scene."""
    threads()
    pre = NAME + "_"
    glow = [ob for ob in dragon.objects if ob.name.startswith(pre + "GLOW")]
    real_pack = bpy.ops.uv.pack_islands

    def pack(**kw):
        weigh_islands(bpy.context.view_layer.objects.active)
        return real_pack(**kw)
    saved = bpy.ops
    bpy.ops = _OpsProxy(saved, pack)            # kit.bake_texture packs once, right after the unwrap
    try:
        body = kit.bake_texture([ob for ob in dragon.objects if ob not in glow], texture, name=pre + "Body",
                                shade=BAKE_SHADE, soften=2, rough=0.8, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved
    size = 512 if os.environ.get("PETS_FAST") else 1024
    sun_seams(body, texture, size)
    lo, hi = rough_map(body, texture, 0.8, 0.1)
    print("roughness from %.2f to %.2f" % (lo, hi))
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
    for name in JUNK:
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
    for name in JUNK:
        if name in g.data.attributes:
            g.data.attributes.remove(g.data.attributes[name])
    dragon.objects = [body, g]


def face_point():
    return (head_matrix() @ Vector((0, -0.85, 0.08)) - Vector((0, 0, LEG_DROP))) * SCALE


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
    dragon = build()
    print("triangles by part:", dict(sorted(dragon.tally.items(), key=lambda kv: -kv[1])))
    head = face_point()

    def rig_for(samples):
        import review
        rig = review.Rig(dragon, samples=samples, focus=(head.x * 0.6, head.y + 0.9, head.z - 0.9))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.72, -0.9, 0.16)).normalized() * 3.8, head + Vector((0, 0.2, -0.02)), 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0.0, -1.0, 0.07)).normalized() * 3.8, head + Vector((0, 0.2, -0.04)), 30)
        threads()
        return rig, review

    if a.peek:
        rig, _ = rig_for(a.samples)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), a.look) for v in a.views.split(",")], px=a.px, cols=a.cols, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(dragon, os.path.abspath(a.texture))
    tris = dragon.triangles()
    lo, hi = dragon.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(dragon.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        rig, review = rig_for(a.samples)
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        shots = review.STANDARD + [("face", "full"), ("face front", "full")]
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
