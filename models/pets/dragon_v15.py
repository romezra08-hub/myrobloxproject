"""Dragon pet: a legendary obsidian fire dragon. Built from scratch by script.

    python models/pets/dragon.py --review out/dragon.png      # render the review sheet
    python models/pets/dragon.py --export models/export/dragon.fbx

Style: a sleek, powerful game dragon (stylised, not realistic). The owner called the round, chunky
cartoon dragon "childish"; this one is the big creature players brag about. Must-haves:
  1. Adult proportions: a small wedge head (about 1/7 of the length), a long S-curved neck, a deep
     chest, a narrow waist, powerful haunches and a long tail ending in a blade.
  2. Standing proud on four muscular legs, one front leg stepping forward, head raised and turned,
     big bat wings raised and half spread, with fingers, wrist claws and membrane between.
  3. An angular head: long snout, strong jaw line, heavy brows, swept-back horns, a frill of small
     horns behind the jaw, two fangs, and glowing almond eyes without pupils.
  4. Edges, not blobs: sharp tips, flat planes and creases. Dorsal blades from head to tail.
  5. Obsidian scales, a darker back, bronze belly plates, black-to-bone horns and claws, deep red
     membranes and ember-orange glow (eyes, chest seams, neck vents, the tail blade's core).
  6. Not plastic: small scales and several tones baked into the texture, a matte finish.
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

HEAD_AT = (-0.42, -3.80, 7.45)     # the back of the skull
HEAD_ROT = (8, 3, -16)             # nose a little down, a small tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.06

# The upper head (skull and snout) as sections from the back of the skull to the nose:
# y (nose towards -y), top z, half width of the top plane, cheek z, cheek half width, lip z, lip half width.
SKULL = [
    (0.32, 0.16, 0.10, 0.00, 0.20, -0.16, 0.14),
    (0.18, 0.38, 0.26, 0.08, 0.44, -0.30, 0.34),
    (-0.15, 0.48, 0.34, 0.06, 0.54, -0.36, 0.42),
    (-0.50, 0.46, 0.32, 0.02, 0.48, -0.28, 0.40),
    (-0.82, 0.36, 0.25, -0.02, 0.39, -0.22, 0.35),
    (-1.25, 0.28, 0.21, -0.05, 0.32, -0.19, 0.29),
    (-1.65, 0.22, 0.17, -0.07, 0.27, -0.17, 0.25),
    (-1.94, 0.17, 0.13, -0.06, 0.20, -0.155, 0.18),
    (-2.05, 0.09, 0.08, -0.07, 0.12, -0.13, 0.10),
]
# The lower jaw: y, top z, top half width, jaw-corner z, jaw-corner half width, chin-keel z.
JAW = [
    (0.10, -0.22, 0.28, -0.46, 0.28, -0.54),
    (-0.12, -0.20, 0.38, -0.54, 0.36, -0.68),
    (-0.50, -0.20, 0.36, -0.47, 0.31, -0.58),
    (-0.95, -0.18, 0.31, -0.38, 0.25, -0.45),
    (-1.45, -0.17, 0.26, -0.33, 0.20, -0.38),
    (-1.80, -0.16, 0.20, -0.29, 0.15, -0.33),
    (-1.94, -0.16, 0.09, -0.25, 0.06, -0.27),
]


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


# ---- the dragon --------------------------------------------------------------------------------------

def build():
    scale = kit.scaly(kit.material("Scale", "#3C3842"), size=0.22, joins=0.62, vary=0.26, shade_down=0.12, rough=0.8)
    tones(scale, up="#17151A", down="#544640", up_mix=0.62, down_mix=0.5)
    dome(scale, 0.25)
    hide = kit.scaly(kit.material("Hide", "#3E3943"), size=0.36, joins=0.72, vary=0.3, shade_down=0.1, rough=0.8)
    tones(hide, up="#18161B", down="#56473F", up_mix=0.6, down_mix=0.5)
    dome(hide, 0.4)
    belly = kit.scaly(kit.material("Belly", "#7C5A28"), size=0.42, joins=0.3, vary=0.14, rough=0.6)
    tones(belly, up="#A27C3A", down="#4C3519", up_mix=0.35, down_mix=0.5)
    horn = kit.scaly(kit.material("Horn", "#0C0B0E"), size=0.6, joins=0.05, vary=0.06, rough=0.5)
    ramp_by(horn, "grad", [(0.0, "#050406"), (0.66, "#0B0A0D"), (0.8, "#5E5444"), (0.9, "#CBBE9C"), (1.0, "#F2EAD2")])
    gloss(horn, strength=0.5, lo=0.9, hi=0.995, sheen=0.03)
    blade = kit.scaly(kit.material("Blade", "#0C0B0E"), size=0.6, joins=0.05, vary=0.06, rough=0.5)
    ramp_by(blade, "grad", [(0.0, "#060507"), (0.6, "#0E0C10"), (0.78, "#4A4236"), (0.9, "#BFB292"), (1.0, "#EDE4CB")])
    armour = kit.scaly(kit.material("Armour", "#24212A"), size=0.55, joins=0.12, vary=0.1, rough=0.6)
    tones(armour, up="#121015", down="#3A302E", up_mix=0.5, down_mix=0.4)
    gloss(armour, strength=0.22, lo=0.92, hi=0.995)
    web = kit.scaly(kit.material("Membrane", "#6A140F"), size=0.32, joins=0.18, vary=0.1, rough=0.75)
    ramp_by(web, "web", [(0.0, "#1C0909"), (0.35, "#4A0E0B"), (0.75, "#841A10"), (1.0, "#B0381A")])
    facem = kit.scaly(kit.material("Face", "#3C3842"), size=0.13, joins=0.55, vary=0.24, rough=0.8)
    tones(facem, up="#1C1A20", down="#4E423D", up_mix=0.55, down_mix=0.45)
    dark = kit.material("Dark", "#0B0A0C", rough=0.7)
    glow = kit.material("GLOW_Ember", "#FF6A14", rough=0.4, emit=6.0)

    d = Prop("Dragon")
    d.tally = {}

    def add(part, bm, mat, at=None, crease=40.0, ember=0.0, boost=None):
        for name in ("grad", "web"):
            layer(bm, name)
        le = layer(bm, "ember")             # where the crevices glow ember after the bake (see ember_seams)
        for v in bm.verts:
            v[le] = ember
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

    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    HR = H.to_3x3().normalized()

    # ---- neck, trunk and tail: one skin --------------------------------------------------------------
    def hs(p):
        return tuple(H @ Vector(p))

    spine = [
        (*hs((0, -0.20, -0.16)), 0.32, 0.30, 0.30, 2.2, 0.0),   # 0  inside the head
        (*hs((0, 0.26, -0.30)), 0.36, 0.36, 0.38, 2.2, 0.04),   # 1  behind the skull
        (-0.28, -3.22, 6.82, 0.40, 0.40, 0.46, 2.2, 0.05),      # 2  upper neck, curving back
        (-0.20, -3.18, 6.10, 0.50, 0.50, 0.58, 2.25, 0.06),     # 3
        (-0.10, -3.24, 5.35, 0.66, 0.58, 0.76, 2.3, 0.07),      # 4  the lower neck swings forward
        (-0.03, -2.82, 4.60, 0.90, 0.74, 1.0, 2.35, 0.08),      # 5  neck base
        (0.00, -2.02, 4.12, 1.22, 0.96, 1.52, 2.4, 0.09),       # 6  deep chest
        (0.00, -1.25, 4.06, 1.30, 1.04, 1.40, 2.5, 0.10),       # 7  shoulders
        (0.00, -0.15, 4.12, 0.96, 0.80, 0.90, 2.45, 0.10),      # 8  waist
        (0.00, 0.85, 4.18, 0.94, 0.80, 0.86, 2.45, 0.10),       # 9
        (0.00, 1.75, 4.20, 1.16, 0.94, 0.96, 2.5, 0.10),        # 10 hips
        (0.00, 2.65, 3.95, 0.82, 0.74, 0.72, 2.4, 0.09),        # 11 rump
        (-0.05, 3.55, 3.45, 0.60, 0.56, 0.54, 2.3, 0.08),       # 12 tail root
        (-0.15, 4.45, 2.70, 0.48, 0.45, 0.44, 2.25, 0.07),      # 13
        (-0.35, 5.25, 1.85, 0.38, 0.36, 0.35, 2.2, 0.06),       # 14
        (-0.75, 5.90, 1.05, 0.31, 0.29, 0.28, 2.2, 0.05),       # 15
        (-1.40, 6.30, 0.45, 0.25, 0.24, 0.24, 2.2, 0.045),      # 16
        (-2.25, 6.35, 0.22, 0.20, 0.19, 0.19, 2.2, 0.04),       # 17 lying on the ground
        (-3.05, 5.95, 0.20, 0.16, 0.16, 0.16, 2.2, 0.035),      # 18
        (-3.60, 5.35, 0.34, 0.13, 0.13, 0.13, 2.2, 0.03),       # 19
        (-3.92, 4.72, 0.58, 0.10, 0.10, 0.10, 2.2, 0.02),       # 20 the tip, where the blade sits
    ]
    skin = Skin(spine, 7)
    body = skin.mesh(segs=20, cuts=(3.0, 5.6, 8.2, 10.9, 13.2, 15.4, 17.6))
    for v in body.verts:
        v.co.z = max(v.co.z, 0.0)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(skin.pts))
    for k, p in enumerate(skin.pts):
        kd.insert(p, k)
    kd.balance()
    trunk, rest = kit.split(body, lambda f: 5.6 <= kd.find(f.calc_center_median())[1] / skin.samples <= 13.2)
    add("skin", trunk, hide, crease=0)              # the barrel gets big bold scales, the neck and tail finer ones
    add("skin", rest, scale, crease=0)

    # ---- belly: bronze plates; on the chest they part to show the ember glowing beneath ---------------
    under = skin.line(-90.0)
    dist, stop = Skin.run_at(under, skin.s_of(1.15)), Skin.run_at(under, skin.s_of(17.5))
    seam_from, seam_to = skin.s_of(4.9), skin.s_of(6.8)
    while dist < stop:
        s0 = Skin.along(under, dist)
        i = skin.index_of(s0)
        size = _table([(1, 0.34), (3, 0.46), (5, 0.58), (7, 0.64), (10, 0.62), (12, 0.52), (15, 0.38), (17.5, 0.26)], i)
        half = _table([(1, 52), (4, 46), (6, 42), (8, 38), (11, 36), (14, 34), (17.5, 30)], i)
        seam = seam_from <= s0 <= seam_to
        s1 = Skin.along(under, dist + size * (0.9 if seam else 1.22))
        p = plate(skin, s0, s1, half, lift=(0.02, 0.075), bow=0.0, pinch=0.06,
                  vs=(0, 0.1, 0.62, 0.95, 1), qs=(-1, -0.86, -0.3, 0.3, 0.86, 1))
        add("belly plates", p, belly, crease=50, ember=1.0)
        dist += size
    add("chest glow", plate(skin, seam_from - 0.1, seam_to + 0.25, 36, lift=(0.012, 0.012), pinch=0.0,
                            vs=(0, 0.1, 0.3, 0.5, 0.7, 0.9, 1), qs=(-1, -0.8, -0.4, 0, 0.4, 0.8, 1)), glow, crease=0)

    # ---- back plates: a ridge of broad overlapping armour plates down the spine, under the blades ----
    ridge = skin.line(90.0)
    dist, stop = Skin.run_at(ridge, skin.s_of(2.2)), Skin.run_at(ridge, skin.s_of(16.5))
    while dist < stop:
        s0 = Skin.along(ridge, dist)
        i = skin.index_of(s0)
        size = _table([(2, 0.36), (4, 0.46), (6, 0.62), (7.5, 0.7), (9, 0.64), (10.5, 0.66), (12, 0.54), (14, 0.44), (16.5, 0.32)], i)
        half = _table([(2, 30), (5, 28), (7, 30), (8.5, 34), (10, 32), (12, 30), (16.5, 32)], i)
        s1 = Skin.along(ridge, dist + size * 1.25)
        add("back plates", plate(skin, s0, s1, half, centre=90.0, lift=(0.03, 0.12), pinch=0.25, bow=0.06,
                                 vs=(0, 0.15, 0.6, 0.92, 1), qs=(-1, -0.8, -0.3, 0.3, 0.8, 1)), armour, crease=40, ember=1.0)
        dist += size

    # ---- the ribcage: curved armour bands down each flank between the shoulder and the hip ------------
    for sx in (-1, 1):
        for k in range(6):
            i0 = 7.25 + 0.36 * k
            s0, s1 = skin.s_of(i0), skin.s_of(i0 + 0.46)
            centre = -18.0 if sx > 0 else 198.0
            half = 40.0 - 2.0 * abs(k - 2.5)
            add("rib plates", plate(skin, s0, s1, half, centre=centre, lift=(0.02, 0.14), pinch=0.35, bow=0.16,
                                    vs=(0, 0.15, 0.6, 0.92, 1), qs=(-1, -0.85, -0.45, 0, 0.45, 0.85, 1)), armour, crease=40, ember=1.0)

    # ---- dorsal blades from behind the head to the tail tip, largest at the shoulders ------------------
    ridge = skin.line(90.0)
    dist, stop = Skin.run_at(ridge, skin.s_of(1.2)), Skin.run_at(ridge, skin.s_of(19.6))
    while dist < stop:
        s = Skin.along(ridge, dist)
        i = skin.index_of(s)
        size = _table([(1.2, 0.30), (3, 0.40), (5, 0.62), (6.5, 0.86), (7.5, 0.92), (8.5, 0.70), (9.5, 0.62), (10.5, 0.66),
                       (12, 0.56), (14, 0.46), (16, 0.36), (18, 0.26), (19.6, 0.18)], i)
        c, t, u = skin.at(s)[:3]
        top = skin.bare(s, 90.0)
        bm = lens(blade_outline(size, size * 0.85, sweep=0.55, steps=3), max(0.05, 0.13 * size), centre=(0.0, 0.25 * size))
        set_grad(bm, lambda co, h=size: 0.25 + 0.5 * co.z / h)
        add("dorsal blades", bm, blade, stand(top + u * 0.04, t, u), crease=45)
        dist += size * 1.32

    # ---- tail blade: a dark spearhead with bone edges and a glowing core -------------------------------
    c, t, u = skin.at(skin.L)[:3]
    spear = [(0, 1.0), (0.12, 0.72), (0.26, 0.42), (0.46, 0.06), (0.17, 0.2), (0.13, -0.14),
             (-0.13, -0.14), (-0.17, 0.2), (-0.46, 0.06), (-0.26, 0.42), (-0.12, 0.72)]
    bm = lens([(a * 1.1, b * 1.15) for a, b in spear], 0.2, rows=((0.55, 0.9), (0.85, 0.5), (1.0, 0.0)), centre=(0.0, 0.3))
    set_grad(bm, lambda co: 0.1 + 0.9 * math.hypot(co.x / 0.5, (co.z - 0.3) / 0.8) ** 2)
    at = stand(c - t * 0.12, Vector((0, 0, 1)), t)
    add("tail blade", bm, blade, at, crease=45)
    vein = lens([(0, 0.82), (0.05, 0.45), (0.06, 0.2), (0, -0.04), (-0.06, 0.2), (-0.05, 0.45)], 0.24, centre=(0.0, 0.3))
    add("tail blade", vein, glow, at, crease=0)

    # ---- legs ----------------------------------------------------------------------------------------
    def foot(x, y, yaw, size, hind):
        F = M((x, y, 0), rot=(0, 0, yaw), scale=size)
        add("feet", grounded(rounded_box((0.72, 0.9, 0.46), n=3.6, cuts=2), F @ M((0, 0.02, 0.2))), scale, crease=0)
        for k in (-1, 0, 1):
            ox = 0.24 * k
            reach = -0.06 if k else 0.0
            toe = [(ox * 0.8, -0.18, 0.24), (ox, -0.48 + reach, 0.2), (ox * 1.15, -0.66 + reach, 0.15)]
            add("feet", grounded(loft(toe, [0.16, 0.14, 0.11], P_CLAW, up=(0, 0, 1), rings=3), F), scale, crease=50)
            claw = [(ox * 1.15, -0.62 + reach, 0.17), (ox * 1.2, -0.80 + reach, 0.13), (ox * 1.22, -0.92 + reach, 0.0)]
            add("claws", grounded(loft(claw, [0.085, 0.055, 0.008], P_CLAW, up=(0, -0.3, 1), rings=5), F), horn, crease=50)
        if hind:
            claw = [(0, 0.3, 0.2), (0, 0.48, 0.12), (0, 0.56, 0.0)]
            add("claws", grounded(loft(claw, [0.08, 0.05, 0.008], P_CLAW, up=(0, 0.3, 1), rings=4), F), horn, crease=50)

    plates = []                               # (surface, ray origin, long axis, size, extra lift)
    for sx in (-1, 1):
        near = sx < 0
        # front legs: the near one steps forward
        step = 0.65 if near else 0.0
        elbow = Vector((1.3 * sx, -1.42 - 0.12 * near, 2.35))
        wrist = Vector((1.26 * sx, -1.98 - step, 0.62))
        arm = [(0.92 * sx, -1.8, 3.95), (1.2 * sx, -1.6, 3.1), tuple(elbow), tuple(elbow.lerp(wrist, 0.33) + Vector((0.03 * sx, 0.04, 0))),
               tuple(wrist), (1.26 * sx, -2.06 - step, 0.30)]
        bm = loft(arm, [(0.7, 0.9), (0.6, 0.74), (0.48, 0.54), (0.46, 0.52), (0.31, 0.34), (0.31, 0.33)], P_LEG, up=(0, -1, 0), rings=18)
        # shoulder muscle: a deltoid cap over the top of the arm narrowing to the elbow, the triceps behind
        delt = mass([(0.98 * sx, -1.78, 4.05), (1.3 * sx, -1.78, 3.62), (1.42 * sx, -1.66, 3.05), (1.38 * sx, -1.5, 2.62)],
                    [(0.42, 0.5), (0.5, 0.62), (0.36, 0.44), (0.08, 0.1)], up=(0, -1, 0))
        tri = mass([(1.0 * sx, -1.28, 3.8), (1.24 * sx, -1.18, 3.25), (1.3 * sx, -1.2, 2.7)], [(0.36, 0.34), (0.36, 0.34), (0.1, 0.1)], up=(0, 1, 0))
        fore = mass([(1.36 * sx, -1.5 - 0.1 * step, 2.25), (1.36 * sx, -1.62 - 0.35 * step, 1.75), (1.3 * sx, -1.85 - 0.8 * step, 1.05)],
                    [(0.32, 0.3), (0.3, 0.3), (0.08, 0.08)], up=(0, -1, 0))
        limb = Surface(bm, delt, tri, fore)
        for z, ys, sz in ((3.98, (-2.0, -1.46), 0.62), (3.64, (-2.18, -1.72, -1.24), 0.56), (3.3, (-1.96, -1.46), 0.52),
                          (2.98, (-1.72,), 0.46)):
            for yy in ys:
                plates.append((limb, (3 * sx, yy, z), (0, 0.15, -1), (sz * 1.05, sz * 0.92), 0.12))
        plates.append((limb, (3 * sx, elbow.y - 0.3 - 0.25 * step, 1.75), wrist - elbow, (0.78, 0.44), 0.1))
        plates.append((limb, (3 * sx, elbow.y - 0.36 - 0.45 * step, 1.25), wrist - elbow, (0.62, 0.36), 0.1))
        add("legs", bm, scale, crease=55)
        for m_ in (delt, tri, fore):
            add("muscle", m_, hide, crease=0)
        spur = [tuple(elbow + Vector((0, 0.1, 0.05))), tuple(elbow + Vector((0.02 * sx, 0.38, 0.12))), tuple(elbow + Vector((0.03 * sx, 0.6, 0.24)))]
        add("spurs", loft(spur, [0.12, 0.07, 0.01], P_CLAW, up=(0, 0, 1), rings=4), horn, crease=50)
        foot(1.26 * sx, -2.10 - step, 6 * sx, 1.25, False)

        # hind legs: a powerful haunch, the knee forward, the hock high and back
        thigh = [(0.80 * sx, 1.95, 4.15), (1.08 * sx, 1.45, 3.25), (1.22 * sx, 0.95, 2.25), (1.24 * sx, 1.0, 2.05)]
        bm = loft(thigh, [(0.86, 1.2), (0.76, 1.02), (0.46, 0.52), (0.38, 0.42)], P_LEG, up=(0, -1, 0.15), rings=12)
        # the big outer thigh muscle and the front (quad) muscle down to the knee, the glute over the hip
        glute = mass([(0.9 * sx, 2.45, 4.35), (1.3 * sx, 2.15, 3.85), (1.5 * sx, 1.8, 3.2), (1.42 * sx, 1.55, 2.6)],
                     [(0.4, 0.55), (0.52, 0.72), (0.42, 0.6), (0.1, 0.14)], up=(0, 1, 0.3))
        quad = mass([(1.05 * sx, 1.05, 3.85), (1.35 * sx, 0.9, 3.15), (1.42 * sx, 0.8, 2.45), (1.3 * sx, 0.86, 2.08)],
                    [(0.36, 0.42), (0.42, 0.5), (0.3, 0.34), (0.08, 0.08)], up=(0, -1, 0))
        haunch = Surface(bm, glute, quad)
        for z, ys, sz in ((4.0, (1.4, 1.95, 2.45), 0.62), (3.62, (1.15, 1.68, 2.2), 0.62), (3.24, (1.0, 1.48, 1.96), 0.56),
                          (2.86, (1.02, 1.5), 0.5), (2.5, (1.12,), 0.42)):
            for yy in ys:
                plates.append((haunch, (3 * sx, yy, z), (0, -0.25, -1), (sz * 1.05, sz * 0.92), 0.12))
        add("haunch", bm, hide, crease=55)
        for m_ in (glute, quad):
            add("muscle", m_, hide, crease=0)
        shin = [(1.22 * sx, 0.92, 2.15), (1.25 * sx, 1.5, 1.62), (1.24 * sx, 2.08, 1.15), (1.22 * sx, 1.86, 0.55), (1.2 * sx, 1.72, 0.28)]
        bm = loft(shin, [0.5, 0.41, 0.33, 0.28, 0.28], P_LEG, up=(0, -1, 0), rings=14)
        plates.append((Surface(bm), (3 * sx, 1.5, 1.66), Vector(shin[2]) - Vector(shin[0]), (0.66, 0.42), 0.06))
        add("legs", bm, scale, crease=55)
        hock = [(1.24 * sx, 2.12, 1.18), (1.25 * sx, 2.45, 1.3), (1.26 * sx, 2.72, 1.5)]
        add("spurs", loft(hock, [0.13, 0.08, 0.01], P_CLAW, up=(0, 0, 1), rings=4), horn, crease=50)
        foot(1.2 * sx, 1.62, 4 * sx, 1.28, True)

    # chest muscle: two pectoral masses either side of the belly plates, between the front legs
    for sx in (-1, 1):
        add("muscle", mass([(0.3 * sx, -2.0, 4.2), (0.62 * sx, -2.42, 3.6), (0.82 * sx, -2.2, 3.0), (0.86 * sx, -1.95, 2.75)],
                           [(0.4, 0.42), (0.48, 0.52), (0.36, 0.38), (0.06, 0.06)], up=(0, -1, 0)), hide, crease=0)

    # ---- armour scales: hard angular plates in overlapping rows on the shoulders, haunches and shins ----
    scute = [(-0.62, 0.0), (-0.3, 0.36), (0.12, 0.44), (0.5, 0.2), (0.62, -0.18), (0.42, -0.5), (0.0, -0.4), (-0.36, -0.24)]
    # an armour scale seen with its point down the limb: X runs down it, Z across
    shield = [(0.5, 0.0), (0.28, 0.3), (-0.05, 0.46), (-0.4, 0.4), (-0.5, 0.0), (-0.4, -0.4), (-0.05, -0.46), (0.28, -0.3)]
    for limb, origin, along, size, tile in plates:
        origin = Vector(origin)
        try:
            p, nrm = limb.hit(origin, (-origin.x, 0, 0))
        except ValueError:
            continue
        down = abs(Vector(along).normalized().z) > 0.9      # a scale pointing down the limb, not a crosswise plate
        outline = shield if down else scute
        thick = 0.14
        bm = lens([(a * size[0], b * size[1]) for a, b in outline], thick, rows=((0.35, 1.0), (1.0, 0.0)),
                  centre=(0.1 * size[0], -0.02 * size[1]) if not down else (0.12 * size[0], 0.0))
        T = facing(p, nrm, Vector(along))
        sign = 1.0 if T.col[1].xyz.dot(nrm) > 0 else -1.0
        for v in bm.verts:                                   # drape it over the curve of the limb
            flat = T @ Vector((v.co.x, 0.0, v.co.z))
            try:
                q, _ = limb.hit(flat + nrm * 1.5, -nrm)
            except ValueError:
                q = flat
            if down:                                          # roof tiles: the lower end stands proud
                rise = tile * max(0.0, 0.3 + v.co.x / size[0])
            else:
                rise = tile * max(0.0, 0.45 - v.co.z / size[1])
            v.co = q + nrm * (v.co.y * sign + thick / 2 - 0.035 + rise)
        add("scutes", bm, armour, crease=30, ember=1.0)

    # ---- wings: raised and half spread -------------------------------------------------------------------
    for sx, lift, reach in ((-1, 0.0, 1.0), (1, 0.35, 1.04)):
        def P(x, y, z):
            return Vector((x * sx * reach, y, z + lift * (z - 5.0) / 5.0))
        S, E, W = P(0.55, -1.15, 5.0), P(1.65, -0.35, 6.7), P(2.55, -1.25, 8.8)
        T = [P(4.05, -0.55, 9.75), P(5.45, 0.65, 8.4), P(5.65, 1.95, 6.3), P(4.45, 3.05, 4.65)]
        B = P(0.85, 2.05, 4.7)
        nrm = (T[1] - W).cross(B - W).normalized()
        back = nrm if nrm.y > 0 else -nrm
        bones = [(S, E), (E, W)] + [(W, tip) for tip in T]
        panels = (([T[0], T[1]], (0.16,), (0.12,)), ([T[1], T[2]], (0.2,), (0.14,)), ([T[2], T[3]], (0.2,), (0.14,)),
                  ([T[3], B, S, E], (0.24, 0.0, 0.0), (0.12, 0.0, 0.0)))
        for rim, scallop, billow in panels:
            web_bm = membrane(W, rim, scallop, billow, back)
            lay = layer(web_bm, "web")
            for v in web_bm.verts:
                dd = min(_seg_dist(v.co, a, b) for a, b in bones)
                v[lay] = min(dd / 1.3, 1.0) ** 0.8
            add("membranes", web_bm, web, crease=0)
        outward = Vector((sx, 0, 0.3))
        add("wing arms", loft([S + Vector((-0.2 * sx, 0, -0.25)), S, (S + E) / 2 + Vector((0, 0, 0.12)), E, (E + W) / 2, W],
                              [0.48, 0.42, 0.34, 0.27, 0.21, 0.17], P_LEG, up=outward, rings=18), scale, crease=55)
        for k, tip in enumerate(T):
            bend = (tip - W).cross(back).normalized() * 0.08 * (1 if k < 2 else -1)
            pts = [W, W.lerp(tip, 0.5) + bend, tip + (tip - W).normalized() * 0.2]
            add("fingers", loft(pts, [0.12 - 0.01 * k, 0.07, 0.008], P_HORN, up=back, rings=6), scale, crease=55)
        hook = [W + Vector((0, 0, -0.05)), W + Vector((0.08 * sx, -0.18, 0.28)), W + Vector((0.05 * sx, -0.42, 0.42)), W + Vector((0, -0.6, 0.36))]
        add("wing claws", loft(hook, [0.12, 0.09, 0.05, 0.008], P_CLAW, up=(0, -0.3, 1), rings=6), horn, crease=50)

    # ---- head: everything is placed in the head's own space, then turned as one -----------------------
    skull = shell(SKULL, skull_corners, per=3, m=2, back_cap=0.06, nose_cap=0.02)
    face = Surface(skull)
    jaw = shell(JAW, jaw_corners, per=2, m=2, back_cap=0.05, nose_cap=0.02)
    add("head", jaw, facem, H, crease=38)

    for sx in (-1, 1):
        # brow ridge: a heavy, level shelf over the eye (never slanting down to the nose: that reads as a
        # scowl) that runs back into the horn
        brow = [(0.2 * sx, -1.0, 0.34), (0.36 * sx, -0.82, 0.44), (0.47 * sx, -0.56, 0.48), (0.47 * sx, -0.26, 0.5), (0.36 * sx, 0.06, 0.52)]
        add("brows", loft(brow, [(0.04, 0.035), (0.12, 0.09), (0.16, 0.12), (0.155, 0.11), (0.13, 0.1)], P_BROW,
                          up=(0.75 * sx, 0, 1), rings=12, grad=False), facem, H, crease=38)
        # cheek ridge: a hard crease from under the eye back to the frill
        cheek = [(0.36 * sx, -1.0, -0.06), (0.49 * sx, -0.62, -0.04), (0.57 * sx, -0.22, -0.02), (0.52 * sx, 0.12, 0.02)]
        add("cheeks", loft(cheek, [(0.02, 0.02), (0.08, 0.06), (0.1, 0.08), (0.07, 0.05)], P_BROW,
                           up=(1.0 * sx, 0, 0.35), rings=8, grad=False), facem, H, crease=38)
        # cheek spikes: three swept back and out from the cheekbone, widening the face
        for y0, z0, ln, out, dz in ((-0.42, -0.04, 0.42, 0.75, 0.05), (-0.16, -0.06, 0.55, 0.85, -0.05), (0.1, -0.1, 0.5, 0.8, -0.2)):
            base = Vector((0.5 * sx, y0, z0))
            dirn = Vector((out * sx, 1.0, dz)).normalized()
            pts = [base, base + dirn * ln * 0.55 + Vector((0, 0, 0.02)), base + dirn * ln]
            add("cheek spikes", loft(pts, [0.075, 0.045, 0.006], P_HORN, up=(0.2 * sx, 0, 1), rings=4), horn, H, crease=50)
        # the eye: a glowing almond, slanted, tucked under the brow
        p, nrm = face.hit((0.9 * sx, -0.6, 0.25), (-sx, 0.0, -0.05))
        back = Vector((0, 1, 0.1))
        eye = [(-0.5, -0.06), (-0.3, 0.06), (0.0, 0.13), (0.3, 0.17), (0.5, 0.16), (0.32, 0.02), (0.05, -0.08), (-0.25, -0.1)]
        add("eyes", lens([(a * 0.48, b * 0.52) for a, b in eye], 0.08, rows=((0.6, 0.85), (1.0, 0.0)), centre=(0.0, 0.03)),
            glow, H @ facing(p - nrm * 0.015, nrm, back), crease=0)
        # nostrils: small dark slits on the snout
        q, qn = face.hit((0.11 * sx, -2.2, 0.1), (0, 1, -0.6))
        add("nostrils", lens([(-0.5, 0), (0, 0.18), (0.5, 0.05), (0, -0.15)], 0.06, centre=(0, 0)), dark,
            H @ facing(q - qn * 0.01, qn, (sx * 0.4, 1, 0)) @ M(scale=(0.16, 1, 0.18)), crease=0)
        # the big horns: ridged at the root, swept back and out so that from the front they frame the face
        hornpath = [(0.30 * sx, 0.0, 0.42), (0.47 * sx, 0.42, 0.78), (0.68 * sx, 0.96, 0.98), (0.88 * sx, 1.55, 0.98), (1.02 * sx, 2.15, 0.78)]
        path, radii = ridged(hornpath, 0.27, 0.012, ridges=5, upto=0.4, depth=0.14, dense=26, power=1.15)
        add("horns", loft(path, radii, P_HORN, up=(0.6 * sx, 0.3, 1), rings=26), horn, H, crease=50)
        lower = [(0.42 * sx, 0.02, 0.2), (0.64 * sx, 0.42, 0.3), (0.84 * sx, 0.88, 0.28), (0.96 * sx, 1.3, 0.14)]
        path, radii = ridged(lower, 0.14, 0.01, ridges=3, upto=0.35, depth=0.14, dense=14)
        add("horns", loft(path, radii, P_HORN, up=(0.8 * sx, 0.2, 1), rings=14), horn, H, crease=50)
        # the crown: a fan of smaller horns behind the jaw, splayed out so they frame the head
        for k, (y0, z0, ln, ang, out) in enumerate(((-0.05, -0.14, 0.7, -14, 0.7), (0.12, 0.06, 0.82, 2, 0.75), (0.26, 0.26, 0.7, 16, 0.65))):
            base = Vector((0.42 * sx, y0, z0))
            dirn = Vector((out * sx, 1.0, math.tan(math.radians(ang)))).normalized()
            pts = [base, base + dirn * ln * 0.5 + Vector((0, 0, 0.04)), base + dirn * ln]
            add("frill", loft(pts, [0.09, 0.055, 0.008], P_HORN, up=(0.3 * sx, 0, 1), rings=4), horn, H, crease=50)
        # two fangs from the upper jaw, over the lower lip
        fang = [(0.235 * sx, -1.56, -0.14), (0.245 * sx, -1.58, -0.27), (0.24 * sx, -1.60, -0.37)]
        add("fangs", loft(fang, [0.05, 0.035, 0.005], P_CLAW, up=(0, -1, 0), rings=4), horn, H, crease=50)
        # the closed mouth: an ember seam glowing along the lips at the back of the jaw, the fire showing
        # through. It stops well short of the nose, so from the front the two sides never join into a grin.
        lip = [(skull_at(y)[6] * 0.95 * sx, y, skull_at(y)[5] - 0.012) for y in (0.02, -0.25, -0.55, -0.85, -1.1, -1.3)]
        add("mouth", loft(lip, [0.008, 0.024, 0.028, 0.026, 0.018, 0.005], profile_round(5), up=(0, 0, 1), rings=8, grad=False), glow, H, crease=0)

    # a small crest on the top of the skull carries the row of blades onto the head, and a ridge of
    # small spikes runs up the snout
    for y0, h in ((-1.78, 0.2), (-1.45, 0.15), (-1.12, 0.11), (-0.25, 0.16), (0.12, 0.2)):
        p, _ = face.hit((0, y0, 3.0), (0, 0, -1))
        bm = lens(blade_outline(h, h * 0.9, sweep=0.5), 0.06, centre=(0, 0.25 * h))
        set_grad(bm, lambda co, h=h: 0.25 + 0.5 * co.z / h)
        add("crest", bm, blade, H @ stand(p - Vector((0, 0, 0.02)), (0, 1, 0), (0, 0, 1)), crease=45)
    add("head", skull, facem, H, crease=38)

    # ---- glowing vents along the sides of the neck -----------------------------------------------------
    for sx in (-1, 1):
        th = 0.0 if sx > 0 else 180.0
        for k in range(4):
            s = skin.s_of(2.55 + 0.42 * k)
            p, nrm = skin.point(s, th + 8.0 * sx), skin.normal(s, th + 8.0 * sx)
            t = skin.at(s)[1]
            along = Matrix.Rotation(math.radians(62 * sx), 3, nrm) @ (t - nrm * nrm.dot(t)).normalized()
            add("vents", lens([(-0.5, 0), (-0.3, 0.06), (0.3, 0.08), (0.5, 0), (0.3, -0.06), (-0.3, -0.05)], 0.05, centre=(0, 0)),
                glow, facing(p - nrm * 0.008, nrm, along) @ M(scale=(0.62 - 0.05 * k, 1, 0.42)), crease=0)

    cut = cull_and_weigh(d.parts)
    print("  hidden faces removed: %d triangles" % cut)
    d.build()
    for ob in d.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return d


UV_ANGLE, UV_MARGIN, PACK_MARGIN = 85.0, 0.004, 0.003
HIDDEN_SHARE = 0.25           # a barely seen surface gets this much of the texture size a seen one gets (in each direction)
HEAD_BOOST = 0.45             # the head's surfaces get 1 + 0.75 * this of the texture size the body gets
EMBER = "#FF5A12"             # the glow in the seams between the plates
EMBER_REACH = 0.16            # crevice shading from shapes this close
EMBER_FROM, EMBER_TO, EMBER_MAX = 0.18, 0.62, 0.8


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


def ember_seams(ob, path, size):
    """After the bake: where the plates (vertex value "ember") sink into a tight crevice, between two
    plates or where a plate meets the skin, turn the colour towards glowing ember, so that the seams
    read as crisp lines of fire. Two quick bakes into the texture's own layout: the mask and a short
    reach crevice shading."""
    import bpy
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
    a = tree.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "ember"
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(a.outputs["Fac"], em.inputs["Color"])
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
    crev = np.clip(((1.0 - ao) - EMBER_FROM) / (EMBER_TO - EMBER_FROM), 0.0, 1.0)
    k = mask * EMBER_MAX * crev * crev * (3 - 2 * crev)
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    px[..., :3] = px[..., :3] * (1 - k) + np.array(kit.srgb(EMBER), dtype=np.float32) * k
    tex.pixels.foreach_set(px.ravel())
    tex.filepath_raw, tex.file_format = path, 'PNG'
    tex.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)


def bake(dragon, texture):
    """Everything that does not glow becomes one textured mesh, Dragon_Body: the scales, tones and
    soft shading in the creases are baked into its colour image, the barely seen surfaces getting
    less of it, and the seams between the plates are then lit ember (ember_seams). The glowing parts
    are joined into one mesh, Dragon_GLOW, that keeps its emissive material. Roblox gets two MeshParts."""
    import bpy
    glow = [ob for ob in dragon.objects if "GLOW" in ob.name]
    real_pack = bpy.ops.uv.pack_islands

    def pack(**kw):
        weigh_islands(bpy.context.view_layer.objects.active)
        return real_pack(**kw)
    saved = bpy.ops
    bpy.ops = _OpsProxy(saved, pack)            # kit.bake_texture packs once, right after the unwrap
    try:
        body = kit.bake_texture([ob for ob in dragon.objects if ob not in glow], texture, name="Dragon_Body",
                                shade=0.55, soften=2, rough=0.8, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved
    ember_seams(body, texture, 512 if os.environ.get("PETS_FAST") else 1024)    # kit bakes 512 under PETS_FAST
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
    for name in ("hid", "boost", "ember", "grad", "web"):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = "Dragon_GLOW"
    for name in ("hid", "boost", "ember", "grad", "web"):
        if name in g.data.attributes:
            g.data.attributes.remove(g.data.attributes[name])
    dragon.objects = [body, g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,side,face,front")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Dragon review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "dragon_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    dragon = build()
    print("triangles by part:", dict(sorted(dragon.tally.items(), key=lambda kv: -kv[1])))
    head = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.9, 0.05))
    focus = tuple(head)

    def rig_for(samples):
        import review
        rig = review.Rig(dragon, samples=samples, focus=(head.x, head.y + 1.5, head.z - 1.6))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.85, -0.8, 0.22)).normalized() * 6.5, head + Vector((0, 0.4, 0)), 30)
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
    me = dragon.objects[0].data
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
            quick = [("front 3/4", "full"), ("side", "full"), ("face", "full"), ("game distance", "full")]
            rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
