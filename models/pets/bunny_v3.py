"""Bunny pet in a crochet (amigurumi) style, built from scratch by script.

    python models/pets/bunny.py --review out/bunny.png      # render the review sheet
    python models/pets/bunny.py --export models/export/bunny.fbx

Style: a hand-crocheted toy rabbit, sitting with its feet out in front. Must-haves, checked every review:
  1. Reads as a rabbit in outline: two long ears, one upright and one bent over, a round head,
     a pear-shaped body, a pom-pom tail.
  2. Toy proportions, NOT a simulator pet: a round head about as wide as the body, never a cube.
  3. The surface is yarn: rows of little V stitches worked in rounds, matte, never smooth plastic.
  4. A simple friendly face: small glossy bead eyes set apart with one highlight each, a pale muzzle,
     an embroidered pink nose and a small stitched smile.
  5. Made by hand, with care: a knitted scarf in one accent colour, paw pads, a sewn-on heart, and
     nothing perfectly symmetrical (head tilted, one ear bent, scarf tied to one side).

How the stitches work: every shape is made the way the real toy is, in rounds. Each corner of each
face remembers where it is in the work (how far round the round, which round, how many stitches that
round has) and the yarn material draws one V per stitch from that. So the rows follow every shape,
and bending or squashing a shape afterwards carries its stitches along.
"""
import argparse
import bisect
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, lumpy, rounded_box, shear, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

ROW = 0.085       # the height of one round of stitches, in studs
STITCH = 0.09    # the width of one stitch
FLAT = 100.0      # the stitch count given to flat pieces, whose rows run straight across


# ---- yarn: a material that draws crochet stitches ---------------------------------------------------

class Graph:
    """Shorthand for wiring shader nodes."""

    def __init__(self, mat):
        self.tree = mat.node_tree

    def node(self, kind, **props):
        n = self.tree.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def put(self, value, socket):
        if isinstance(value, (int, float)):
            socket.default_value = value
        else:
            self.tree.links.new(value, socket)

    def math(self, op, a, b=None, c=None):
        n = self.node("ShaderNodeMath", operation=op)
        for i, x in enumerate((a, b, c)):
            if x is not None:
                self.put(x, n.inputs[i])
        return n.outputs[0]

    def smooth(self, x, lo, hi):
        """0 below lo, 1 above hi, a soft step between."""
        n = self.node("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP')
        self.put(x, n.inputs["Value"])
        n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = lo, hi
        return n.outputs["Result"]

    def attribute(self, name):
        n = self.node("ShaderNodeAttribute", attribute_name=name)
        sep = self.node("ShaderNodeSeparateXYZ")
        self.tree.links.new(n.outputs["Vector"], sep.inputs[0])
        return sep.outputs[0], sep.outputs[1], sep.outputs[2]


def yarn(name, hexcode, alt=None, shadow="#BE9F86", depth=1.0, vary=0.10, fibre=0.10, rough=0.95):
    """A matte yarn colour that draws one V per crochet stitch.

    It reads two things the stitched shapes below store on every face corner:
      st  = (how far round the round, 0 to 1;  which round;  how many stitches the round has)
      st2 = (0 for this colour or 1 for the second colour `alt`;  a number that shifts the pattern;
             how far to quieten the stitches, 0 to 1, for a calm area such as the muzzle)
    Each stitch is two strands of yarn in a V. Between the strands and between the rounds the colour
    is multiplied by `shadow`, as if looking into the gaps; every stitch is a slightly different
    brightness (`vary`) and fine fibres run through all of it (`fibre`). Shapes with no stitch count
    (thread, felt) get the plain colour with the fibres only. bake_texture bakes it into the image.
    """
    mat = kit.material(name, hexcode, rough=rough)
    g, b = Graph(mat), kit.principled(mat)
    link = mat.node_tree.links.new
    u, v, n = g.attribute("st")
    tone, seed, calm = g.attribute("st2")
    row = g.math('FLOOR', v)
    up = g.math('SUBTRACT', v, row)                                             # 0 at the bottom of a round, 1 at its top
    along = g.math('ADD', g.math('MULTIPLY', u, n), g.math('MULTIPLY_ADD', row, 0.5, seed))   # each round is half a stitch out of step
    stitch = g.math('FLOOR', along)
    side = g.math('ABSOLUTE', g.math('SUBTRACT', g.math('SUBTRACT', along, stitch), 0.5))     # 0 in the middle of a stitch, 0.5 at its edge
    off = g.math('ABSOLUTE', g.math('SUBTRACT', side, g.math('MULTIPLY_ADD', up, 0.23, 0.12)))  # distance from the V's strand
    strand = g.math('SUBTRACT', 1.0, g.smooth(off, 0.14, 0.235))
    rows = g.math('MULTIPLY', g.smooth(up, 0.0, 0.14), g.math('SUBTRACT', 1.0, g.smooth(up, 0.89, 1.0)))
    worked = g.math('GREATER_THAN', n, 0.5)
    gap = g.math('MULTIPLY', worked, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', strand, rows)))   # 1 deep between strands, 0 on one
    gap = g.math('MULTIPLY', g.math('MULTIPLY', gap, depth), g.math('SUBTRACT', 1.0, calm))

    cell = g.node("ShaderNodeTexWhiteNoise", noise_dimensions='3D')
    where = g.node("ShaderNodeCombineXYZ")
    g.put(stitch, where.inputs[0])
    g.put(row, where.inputs[1])
    g.put(seed, where.inputs[2])
    link(where.outputs[0], cell.inputs["Vector"])
    coord = g.node("ShaderNodeTexCoord")
    fuzz = g.node("ShaderNodeTexNoise")
    fuzz.inputs["Scale"].default_value, fuzz.inputs["Detail"].default_value = 42.0, 3.0
    link(coord.outputs["Object"], fuzz.inputs["Vector"])
    value = g.math('MULTIPLY', g.math('MULTIPLY_ADD', cell.outputs["Value"], vary, 1 - vary / 2),
                   g.math('MULTIPLY_ADD', fuzz.outputs[0], fibre, 1 - fibre / 2))

    base = g.node("ShaderNodeMix", data_type='RGBA')
    g.put(tone, base.inputs[0])
    base.inputs[6].default_value = (*kit.srgb(hexcode), 1.0)
    base.inputs[7].default_value = (*kit.srgb(alt or hexcode), 1.0)
    deep = g.node("ShaderNodeMix", data_type='RGBA', blend_type='MULTIPLY')
    g.put(gap, deep.inputs[0])
    link(base.outputs[2], deep.inputs[6])
    deep.inputs[7].default_value = (*kit.srgb(shadow), 1.0)
    hsv = g.node("ShaderNodeHueSaturation")
    link(deep.outputs[2], hsv.inputs["Color"])
    g.put(value, hsv.inputs["Value"])
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    return mat


# ---- shapes that carry their stitches ---------------------------------------------------------------

def _layers(bm):
    lay = bm.loops.layers.float_vector
    return lay.get("st") or lay.new("st"), lay.get("st2") or lay.new("st2")


def _face(bm, lay, corners, n, tone, seed):
    """A face from (vertex, u, v) corners: u is how far round the round, v which round it is."""
    f = bm.faces.new([c[0] for c in corners])
    where = {c[0]: c for c in corners}
    for loop in f.loops:
        _, u, v = where[loop.vert]
        loop[lay[0]] = (u, v, n)
        loop[lay[1]] = (tone, seed, 0.0)
    return f


def calmed(bm, amount):
    """Quieten the stitches drawn on a shape (0 leaves them, 1 hides them)."""
    lay = _layers(bm)
    for f in bm.faces:
        for loop in f.loops:
            loop[lay[1]] = (loop[lay[1]][0], loop[lay[1]][1], amount)
    return bm


def tinted(bm, tone=0.0, seed=0.0):
    """Give a plain kit shape (no stitches) the first or second colour of its yarn."""
    lay = _layers(bm)
    for f in bm.faces:
        for loop in f.loops:
            loop[lay[0]] = (0.0, 0.0, 0.0)
            loop[lay[1]] = (tone, seed, 0.0)
    return bm


def _catmull(p0, p1, p2, p3, u):
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _outline(points, per=24):
    """A smooth, closely stepped outline through (radius, height) points. Where it starts or ends on
    the axis it meets it squarely, so the end is rounded and not a cone."""
    pts = [Vector((r, z)) for r, z in points]
    first = Vector((-pts[1].x, pts[1].y)) if pts[0].x < 1e-6 else 2 * pts[0] - pts[1]
    last = Vector((-pts[-2].x, pts[-2].y)) if pts[-1].x < 1e-6 else 2 * pts[-1] - pts[-2]
    ext = [first] + pts + [last]
    out = []
    for k in range(len(pts) - 1):
        out += [_catmull(ext[k], ext[k + 1], ext[k + 2], ext[k + 3], i / per) for i in range(per)]
    out.append(pts[-1].copy())
    for p in out:
        p.x = max(p.x, 0.0)
    return out


class _Measured:
    """A stepped line that can be asked for the point a given distance along it."""

    def __init__(self, line):
        self.line, self.s = line, [0.0]
        for a, b in zip(line, line[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.total = self.s[-1]

    def at(self, d):
        i = min(max(bisect.bisect_right(self.s, d) - 1, 0), len(self.line) - 2)
        t = (d - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-9)
        return self.line[i].lerp(self.line[i + 1], t)


def spun(points, segs=24, scale=(1.0, 1.0), band=1, row=ROW, stitch=STITCH, tone=0.0, seed=0.0):
    """A shape worked in rounds, as amigurumi is: the outline `points`, (radius, height) from the first
    round to the last, spun round the Z axis and stretched by `scale` in X and Y. There is a ring of
    vertices every `band` rounds, and each round has as many stitches as fit round it, so stitches
    stay the same size from the widest round to the last few at the end. An end that is not on the
    axis is closed with a flat lid (it is meant to be hidden inside another shape)."""
    m = _Measured(_outline(points))
    rows = max(2, round(m.total / row))
    marks = list(range(0, rows, band)) + [rows]
    sx, sy = scale
    spread = math.sqrt((sx * sx + sy * sy) / 2.0)
    bm = bmesh.new()
    lay = _layers(bm)
    rings = []
    for k in marks:
        p = m.at(m.total * k / rows)
        if p.x < 1e-4:
            rings.append([bm.verts.new((0.0, 0.0, p.y))])
        else:
            rings.append([bm.verts.new((p.x * sx * math.cos(a), p.x * sy * math.sin(a), p.y))
                          for a in (2 * math.pi * j / segs + math.pi / 2 for j in range(segs))])
    for k in range(len(marks) - 1):
        lo, hi, v0, v1 = rings[k], rings[k + 1], marks[k], marks[k + 1]
        n = max(4, round(2 * math.pi * m.at(m.total * (v0 + v1) / 2.0 / rows).x * spread / stitch))
        for j in range(segs):
            u0, u1, j1 = j / segs, (j + 1) / segs, (j + 1) % segs
            if len(lo) == 1:
                _face(bm, lay, [(lo[0], (u0 + u1) / 2, v0), (hi[j], u0, v1), (hi[j1], u1, v1)], n, tone, seed)
            elif len(hi) == 1:
                _face(bm, lay, [(lo[j], u0, v0), (lo[j1], u1, v0), (hi[0], (u0 + u1) / 2, v1)], n, tone, seed)
            else:
                _face(bm, lay, [(lo[j], u0, v0), (lo[j1], u1, v0), (hi[j1], u1, v1), (hi[j], u0, v1)], n, tone, seed)
    for ring in (rings[0], rings[-1]):
        if len(ring) > 1:
            c = bm.verts.new((0.0, 0.0, ring[0].co.z))
            for j in range(segs):
                _face(bm, lay, [(c, 0, 0), (ring[j], 0, 0), (ring[(j + 1) % segs], 0, 0)], 0.0, tone, seed)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _super(a, n):
    """A point on a unit superellipse (n=2 is a circle, larger is squarer)."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def strap(points, half_w, half_t, across, segs=8, shape=2.6, closed=False, row=ROW, stitch=STITCH, tone=0.0, seed=0.0):
    """A flat knitted band along a smooth path through `points`: a scarf. Its rows run across the
    width, one ring of vertices per row. `across` says which way the width runs: one rough
    direction, or a list of surface normals, one per point, for a band lying on a surface.
    `tone` may be a function of (row, rows), for stripes."""
    pts = [Vector(p) for p in points]
    k = len(pts) if closed else len(pts) - 1

    def P(t):
        i = int(math.floor(t))
        if closed:
            ids = [(i - 1) % k, i % k, (i + 1) % k, (i + 2) % k]
        else:
            i = min(max(i, 0), k - 1)
            ids = [max(i - 1, 0), i, i + 1, min(i + 2, k)]
        return _catmull(*(pts[j] for j in ids), t - i)

    steps = k * 16
    ts = [k * i / steps for i in range(steps + 1)]
    m = _Measured([P(t) for t in ts])
    rows = max(2, round(m.total / row))
    count = rows if closed else rows + 1
    bm = bmesh.new()
    lay = _layers(bm)
    n = max(4, round(3.6 * (half_w + half_t) / stitch))
    rings, mids = [], []
    for r in range(count):
        d = m.total * r / rows
        i = min(max(bisect.bisect_right(m.s, d) - 1, 0), steps - 1)
        t = ts[i] + (ts[i + 1] - ts[i]) * (d - m.s[i]) / max(m.s[i + 1] - m.s[i], 1e-9)
        p = P(t)
        tan = (P(t + 0.02) - P(t - 0.02)).normalized() if closed else (P(min(t + 0.02, k)) - P(max(t - 0.02, 0.0))).normalized()
        if isinstance(across, (list, tuple)) and isinstance(across[0], Vector):
            i0 = min(int(t), k - 1)
            nrm = across[i0].lerp(across[min(i0 + 1, len(across) - 1)], t - i0)
            nrm = (nrm - tan * nrm.dot(tan)).normalized()
            w = tan.cross(nrm).normalized()
        else:
            w = Vector(across)
            w = (w - tan * w.dot(tan)).normalized()
            nrm = w.cross(tan).normalized()
        rings.append([bm.verts.new(p + w * x * half_w + nrm * y * half_t)
                      for x, y in (_super(2 * math.pi * (j + 0.5) / segs, shape) for j in range(segs))])
        mids.append(p)
    for r in range(rows):
        lo, hi = rings[r], rings[(r + 1) % count]
        tn = tone(r, rows) if callable(tone) else tone
        for j in range(segs):
            u0, u1, j1 = j / segs, (j + 1) / segs, (j + 1) % segs
            _face(bm, lay, [(lo[j], u0, r), (lo[j1], u1, r), (hi[j1], u1, r + 1), (hi[j], u0, r + 1)], n, tn, seed)
    if not closed:
        for ring, p, r in ((rings[0], mids[0], 0), (rings[-1], mids[-1], rows - 1)):
            c = bm.verts.new(p)
            tn = tone(r, rows) if callable(tone) else tone
            for j in range(segs):
                _face(bm, lay, [(c, 0, 0), (ring[j], 0, 0), (ring[(j + 1) % segs], 0, 0)], 0.0, tn, seed)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


class Press:
    """Presses flat things onto one or more meshes from the direction `facing`: at(x, y) is the
    point of the surface under (x, y) of a flat sheet held in front of it at `centre`."""

    def __init__(self, targets, centre, facing, up=(0, 0, 1)):
        targets = targets if isinstance(targets, (list, tuple)) else [targets]
        self.trees = [t if isinstance(t, BVHTree) else BVHTree.FromBMesh(t) for t in targets]
        self.f = Vector(facing).normalized()
        self.u = Vector(up).cross(self.f).normalized()
        self.v = self.f.cross(self.u).normalized()
        self.c = Vector(centre)

    def moved(self, x, y):
        return Press(self.trees, self.c + self.u * x + self.v * y, self.f, self.v)

    def hit(self, x, y):
        best = None
        for tree in self.trees:
            loc, nrm, _, dist = tree.ray_cast(self.c + self.u * x + self.v * y + self.f * 6.0, -self.f)
            if loc is not None and (best is None or dist < best[2]):
                best = (loc, nrm, dist)
        if best is None:
            raise ValueError("nothing under (%.2f, %.2f)" % (x, y))
        return best[0], best[1]

    def at(self, x, y, lift=0.0):
        loc, nrm = self.hit(x, y)
        return loc + nrm * lift


def applique(press, outline, lift=0.016, rings=3, segs=20, rows=None, tone=0.0, seed=0.0):
    """A sewn-on patch: the blob outline(angle) -> radius, pressed on. It sits `lift` proud of the
    surface and its rim is tucked just under it. rows="round" gives it crochet rounds from its
    middle, rows="straight" rows straight across; None leaves it plain, like felt."""
    bm = bmesh.new()
    lay = _layers(bm)
    mean = sum(outline(2 * math.pi * j / segs) for j in range(segs)) / segs
    fracs = [(0.0, lift)] + [(i / rings, lift) for i in range(1, rings)] + [(0.93, lift), (1.0, -lift)]
    loops = [[bm.verts.new(press.at(0, 0, lift))]]
    for frac, h in fracs[1:]:
        loops.append([bm.verts.new(press.at(math.cos(a) * outline(a) * frac, math.sin(a) * outline(a) * frac, h))
                      for a in (2 * math.pi * j / segs for j in range(segs))])

    def corner(vert, ring, j):
        frac = fracs[ring][0]
        a = 2 * math.pi * j / segs
        if rows == "straight":
            return (vert, math.cos(a) * outline(a) * frac / (STITCH * FLAT), math.sin(a) * outline(a) * frac / ROW)
        return (vert, j / segs, frac * mean / ROW)

    for ring in range(len(loops) - 1):
        lo, hi = loops[ring], loops[ring + 1]
        mid = (fracs[ring][0] + fracs[ring + 1][0]) / 2 * mean
        n = FLAT if rows == "straight" else (max(5, round(2 * math.pi * mid / STITCH)) if rows == "round" else 0.0)
        for j in range(segs):
            j1 = (j + 1) % segs
            wrap = segs if j1 == 0 and rows != "straight" else j1                      # the last face of a round ends at u = 1, not 0
            if len(lo) == 1:
                _face(bm, lay, [(lo[0], (j + 0.5) / segs if rows != "straight" else 0.0, 0.0), corner(hi[j], ring + 1, j), (hi[j1],) + corner(None, ring + 1, wrap)[1:]], n, tone, seed)
            else:
                _face(bm, lay, [corner(lo[j], ring, j), (lo[j1],) + corner(None, ring, wrap)[1:],
                                (hi[j1],) + corner(None, ring + 1, wrap)[1:], corner(hi[j], ring + 1, j)], n, tone, seed)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((fc.normal for fc in bm.faces), Vector()).dot(press.f) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def stitches(press, outline, count, reach=0.036, phase=0.0, r=0.011):
    """Short threads across the edge of a patch, as if it were sewn on by hand."""
    out = []
    for k in range(count):
        a = phase + 2 * math.pi * k / count
        r0, r1 = outline(a) - reach, outline(a) + reach
        p0 = press.at(math.cos(a) * r0, math.sin(a) * r0, 0.024)
        p1 = press.at(math.cos(a) * r1, math.sin(a) * r1, 0.006)
        out.append(tube([p0, p1], [r, r], segs=4, rings=1))
    return out


def oval(rx, rz, wobble=0.0, phase=0.0, egg=0.0):
    """An outline for applique(): an ellipse, optionally a bit uneven, or fuller at the top (egg)."""
    def r(a):
        base = 1.0 / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / rz) ** 2)
        return base * (1 + wobble * math.sin(2 * a + phase) + 0.6 * wobble * math.sin(3 * a + 2 * phase)) * (1 + egg * math.sin(a))
    return r


def heart(size):
    """An outline for applique(): a heart about `size` studs across."""
    table = []
    for i in range(360):
        t = 2 * math.pi * i / 360
        x, y = 16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t) + 2.5
        table.append((math.atan2(y, x) % (2 * math.pi), math.hypot(x, y) * size / 32.0))
    table.sort()

    def r(a):
        a %= 2 * math.pi
        i = bisect.bisect_left(table, (a, 0.0)) % len(table)
        return table[i][1]
    return r


def aim(a, b):
    """A transform that stands a shape built along +Z on the point a, pointing at b, its +Y kept upmost."""
    a, b = Vector(a), Vector(b)
    return Matrix.Translation(a) @ (b - a).to_track_quat('Z', 'Y').to_matrix().to_4x4()


def bend(bm, z0, z1, angle, toward=(1.0, 0.0)):
    """Fold the part of a shape above the height z0 over towards the direction `toward` (in X, Y):
    between z0 and z1 its axis follows an arc of `angle` degrees, above z1 it carries on straight."""
    a, span = math.radians(angle), z1 - z0
    r = span / a
    d = Vector((toward[0], toward[1], 0.0)).normalized()
    for v in bm.verts:
        h = v.co.z - z0
        if h <= 0:
            continue
        p = v.co.x * d.x + v.co.y * d.y                         # how far towards the fold this point is from the axis
        rest = Vector((v.co.x, v.co.y, 0.0)) - d * p
        th, over = min(h, span) / r, max(h - span, 0.0)
        out = r - (r - p) * math.cos(th) + over * math.sin(th)
        up = (r - p) * math.sin(th) + over * math.cos(th)
        v.co = rest + d * out + Vector((0.0, 0.0, z0 + up))
    return bm


def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor, like a beanbag."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def front_of(bm, x, z, out=0.0):
    """The point on the front (-Y side) of a mesh at (x, z), pushed `out` off the surface, and the
    direction the surface faces there."""
    loc, nrm, _, _ = BVHTree.FromBMesh(bm).ray_cast(Vector((x, -6.0, z)), Vector((0, 1, 0)))
    return loc + nrm * out, nrm


# ---- the bunny --------------------------------------------------------------------------------------

def build():
    cream = yarn("Cream", "#F3E2C8", alt="#FDF8EE", shadow="#CDB49E")
    pink = yarn("Pink", "#F6B6C4", alt="#E8839D", shadow="#DCA2AE")
    teal = yarn("Scarf", "#4DB3A6", alt="#FBF2E0", shadow="#A3B8C6")
    thread = yarn("Thread", "#7A5646", vary=0.0)
    fluff = kit.furry(kit.material("Fluff", "#FFFDF8", rough=0.95), strength=0.2, mottle=0.08, fine=42.0, length=1.3)
    eyes = kit.material("Eyes", "#141012", rough=0.08)
    bun = Prop("Bunny")

    # ---- body: a pear worked from the base up, sitting back a little -----------------------------
    body = spun([(0.42, 0.0), (0.58, 0.03), (0.675, 0.17), (0.70, 0.38), (0.68, 0.60), (0.61, 0.85), (0.50, 1.08),
                 (0.41, 1.27), (0.36, 1.46)], segs=30, scale=(1.0, 0.95), seed=0.13)
    lumpy(body, 0.02, 1.3, seed=2)
    shear(body, axis=2, along=1, amount=0.07, power=1.2)
    grounded(body)
    body_tree = BVHTree.FromBMesh(body)

    def on_body(turn, z, trees=None):
        """The point of the body (or of `trees`) seen from `turn` degrees left of straight ahead, at height z."""
        a = math.radians(turn)
        d = Vector((-math.sin(a), -math.cos(a), 0.0))
        best = None
        for tree in trees or [body_tree]:
            loc, nrm, _, dist = tree.ray_cast(Vector((0, 0.05, z)) + d * 4.0, -d)
            if loc is not None and (best is None or dist < best[2]):
                best = (loc, nrm, dist)
        return best[0], best[1]

    # a felt heart sewn on the tummy, to the right of the scarf ends
    spot, face = on_body(-24, 0.63)
    sewn = Press(body_tree, spot, face)
    bun.add(applique(sewn, heart(0.3), rings=2, segs=24, tone=1.0), pink)

    # ---- legs straight out in front, big oval feet with pads -------------------------------------
    limbs = []
    for sx, splay in ((-1, 15), (1, 11)):
        a = math.radians(splay)
        fwd = Vector((math.sin(a) * sx, -math.cos(a), 0.0))
        hip = Vector((0.31 * sx, -0.28, 0.20))
        leg = spun([(0.185, 0.0), (0.2, 0.3), (0.185, 0.66)], segs=12, seed=0.3 + 0.2 * sx)
        leg.transform(aim(hip, hip + fwd))
        limbs.append(grounded(leg))
        foot = spun([(0.0, 0.13), (0.13, 0.125), (0.21, 0.08), (0.235, -0.01), (0.2, -0.11), (0.11, -0.17), (0.0, -0.185)],
                    segs=16, scale=(0.92, 1.2), seed=0.6 + 0.1 * sx)
        sole = Press(foot, (0, 0, 0), (0, 0, 1), up=(0, 1, 0))
        pads = [applique(sole.moved(0.0, -0.075), oval(0.115, 0.095, 0.05, 1.0 + sx), rings=2, segs=16)]
        pads += [applique(sole.moved(x * sx, y), oval(0.043, 0.047), rings=1, segs=10, lift=0.014)
                 for x, y in ((-0.105, 0.085), (0.0, 0.14), (0.105, 0.085))]
        place = aim(hip + fwd * 0.7 + Vector((0, 0, 0.085)), hip + fwd * 1.7 + Vector((0, 0, 0.3)))
        for pad in pads:
            bun.add(grounded(pad, place), pink)
        limbs.append(grounded(foot, place))

    # ---- arms: stubby, sewn on under the scarf, the left one resting on the tummy ----------------
    for sx, hand in ((-1, (-0.64, -0.37, 0.68)), (1, (0.71, -0.25, 0.66))):
        arm = spun([(0.0, 0.0), (0.11, 0.025), (0.165, 0.11), (0.17, 0.26), (0.15, 0.52), (0.13, 0.74)], segs=12, seed=0.45 + 0.07 * sx)
        arm.transform(aim(hand, (0.38 * sx, 0.0, 1.22)))
        limbs.append(arm)

    # ---- tail: a pom-pom, a little off centre -----------------------------------------------------
    pom = ball((0.52, 0.52, 0.5), cuts=5)
    for v in pom.verts:
        v.co *= 1.0 + 0.11 * noise.noise(v.co * 9.0)
    bun.add(pom, fluff, M((-0.08, 0.78, 0.36)))

    # ---- scarf: once round the neck, tied to the left, two ends hanging down the front ------------
    S = M((0, 0.06, 1.37), rot=(7, 0, 3))
    loop = [S @ Vector((math.cos(a) * 0.455 * (1 + 0.03 * math.sin(3 * a + 1)), math.sin(a) * 0.44, 0.012 * math.sin(2 * a + 0.5)))
            for a in (2 * math.pi * i / 16 for i in range(16))]
    bun.add(strap(loop, 0.13, 0.085, (0, 0, 1), closed=True, seed=0.2), teal)
    knot_turn = 25.0
    ka = math.radians(knot_turn)
    out = Vector((-math.sin(ka), -math.cos(ka), 0.0))
    K = S @ Vector((out.x * 0.455, out.y * 0.44, 0.0))
    upz, along = Vector((0, 0, 1)), Vector((0, 0, 1)).cross(out)
    bun.add(strap([K + out * 0.02 + upz * 0.17, K + out * 0.13 + upz * 0.10, K + out * 0.155 - upz * 0.01,
                   K + out * 0.12 - upz * 0.11, K + out * 0.02 - upz * 0.17], 0.115, 0.05, along, seed=0.5), teal)
    drape = [body_tree] + [BVHTree.FromBMesh(l) for l in limbs]

    def stripes(r, rows):
        return 1.0 if rows - r in (2, 4) else 0.0

    for turns, lift, half_w, sd in (([(1.19, 3), (1.04, 5), (0.88, 6), (0.72, 5)], (0.0, 0.0, 0.0, 0.03), 0.125, 0.3),
                                    ([(1.18, -10), (1.05, -21), (0.93, -30)], (0.03, 0.02, 0.05), 0.115, 0.7)):
        pts, nrms = [K + out * 0.06 - upz * 0.06], [out]
        for (z, dt), extra in zip(turns, lift):
            loc, nrm = on_body(knot_turn - dt, z, drape)
            pts.append(loc + nrm * (0.05 + extra))
            nrms.append(nrm)
        end = strap(pts, half_w, 0.045, nrms, tone=stripes, seed=sd)
        bun.add(end, teal)
        tip, before = pts[-1], pts[-2]
        run = (tip - before).normalized()
        wide = run.cross(nrms[-1]).normalized()
        for i in range(5):                                                                            # the fringe
            f = (i - 2) / 2.0
            root = tip + wide * f * (half_w - 0.02) - run * 0.02
            bun.add(tinted(tube([root, root + run * 0.07 + wide * f * 0.012, root + run * (0.13 + 0.015 * math.cos(i * 2.1)) + wide * f * 0.03 + nrms[-1] * 0.01],
                                [0.021, 0.021, 0.017], segs=5, rings=2)), teal)

    for l in limbs:
        bun.add(l, cream)
    bun.add(body, cream)

    # ---- head: everything is placed round the head's own centre, then tilted as one ---------------
    H = M((0, 0.03, 1.95), rot=(-3, 5, -5))
    head = spun([(0.0, -0.6), (0.3, -0.56), (0.57, -0.4), (0.715, -0.12), (0.71, 0.14), (0.58, 0.4), (0.32, 0.56), (0.0, 0.6)],
                segs=32, scale=(1.0, 0.9), seed=0.0)
    lumpy(head, 0.012, 1.6, seed=5)

    # muzzle: a small white dome worked from its middle, sewn on low between the eyes
    mp, mn = front_of(head, 0.0, -0.17)
    muzzle = spun([(0.0, 0.17), (0.12, 0.155), (0.2, 0.1), (0.235, 0.02), (0.24, -0.08)], segs=18, scale=(1.0, 0.76), tone=1.0, seed=0.4)
    muzzle.transform(aim(mp - mn * 0.035, mp + mn))
    calmed(muzzle, 0.45)                                                                              # a clean pale muzzle
    np_, nn = front_of(muzzle, 0.0, -0.105)                                                           # the nose: a small soft triangle of pink
    nose = ball((0.16, 0.105, 0.075), cuts=2)
    for v in nose.verts:
        v.co.x *= 1.0 + 0.4 * v.co.y / 0.0525
    nose.transform(aim(np_ - nn * 0.012, np_ + nn))
    bun.add(tinted(nose, tone=1.0), pink, H)
    for sx in (-1, 1):                                                                                # a small stitched smile
        pts = [front_of(muzzle, x * sx, z, 0.01)[0] for x, z in ((0.0, -0.235), (0.055, -0.28), (0.12, -0.285), (0.175, -0.245))]
        bun.add(tube(pts, [0.019, 0.021, 0.02, 0.01], segs=5, rings=6), thread, H)
    bun.add(tube([front_of(muzzle, 0, -0.15, 0.01)[0], front_of(muzzle, 0, -0.235, 0.01)[0]], [0.018, 0.02], segs=5, rings=2), thread, H)
    bun.add(muzzle, cream, H)

    for sx in (-1, 1):
        ep, en = front_of(head, 0.3 * sx, 0.035)                                                      # bead eyes, like safety eyes
        eye = ball((0.17, 0.185, 0.115), cuts=3)
        eye.transform(aim(ep - en * 0.012, ep + en))
        shine = front_of(eye, ep.x - 0.03, ep.z + 0.04)[0]
        bun.add(eye, eyes, H)
        bun.add(tinted(ball((0.052, 0.03, 0.052), cuts=1), tone=1.0), cream, H @ M(shine + Vector((0, 0.004, 0))))
        cheek = Press(head, front_of(head, 0.47 * sx, -0.2)[0], (0.62 * sx, -1, -0.2))                # a blush of pink felt
        bun.add(applique(cheek, oval(0.095, 0.08), rings=1, segs=14, lift=0.012), pink, H)

    # ears: long flat tubes worked from the tip down; the right one stands, the left one is bent over
    for sx in (-1, 1):
        ear = spun([(0.0, 1.12), (0.1, 1.08), (0.155, 0.92), (0.175, 0.68), (0.165, 0.4), (0.13, 0.15), (0.1, 0.0)],
                   segs=12, scale=(1.0, 0.36), seed=0.8 + 0.1 * sx)
        inner = applique(Press(ear, (0, 0, 0.6), (0, -1, 0)), oval(0.1, 0.38, egg=0.1), rings=2, segs=18, lift=0.012, rows="straight", seed=0.2)
        for part in (ear, inner):
            for v in part.verts:
                v.co.y -= 0.9 * v.co.x ** 2                                                           # cupped a little, like a real ear
            if sx < 0:
                bend(part, 0.34, 0.84, 105, toward=(-0.9, -0.42))
        E = H @ M((0.29 * sx, 0.03, 0.47), rot=(-6, 9 * sx, 12 * sx) if sx > 0 else (-4, -7, -16))
        bun.add(inner, pink, E)
        bun.add(ear, cream, E)

    bun.add(head, cream, H)
    bun.build()
    return bun


def bake(bun, texture, samples=48):
    """All the yarn, felt and thread become one textured mesh with soft shading baked in. The glossy
    eyes stay a mesh of their own. Roblox gets two MeshParts."""
    gloss = [ob for ob in bun.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in bun.objects if ob not in gloss], texture, name="Bunny_Body", shade=0.5, soften=3, rough=0.95, sheen=0.4, samples=samples)
    bun.objects = [body] + gloss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--look", help="render only the close-up view to this PNG (a quick check)")
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "bunny_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    bun = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(bun, os.path.abspath(a.texture), samples=12 if a.quick else 48)
    tris = bun.triangles()
    lo, hi = bun.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(bun.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.look:
        import review
        rig = review.Rig(bun, samples=14 if a.quick else 40, focus=(0.0, -0.6, 1.9))
        if a.look:
            rig.render(os.path.abspath(a.look), "close-up", "full", a.px)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            shots = [("front 3/4", "full"), ("close-up", "full")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, title="Bunny (crochet) review")
            print("review sheet", a.review)


if __name__ == "__main__":
    main()
