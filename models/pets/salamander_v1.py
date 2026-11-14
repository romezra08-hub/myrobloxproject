"""Lava Salamander pet: an epic salamander that lives in the mine's lava veins. Made by script.

    python models/pets/salamander.py --review out/salamander.png      # render the review sheet
    python models/pets/salamander.py --export models/export/salamander.fbx

Style: "molten creature", new to the collection: a rocky crust of cooled lava over glowing heat.
Tough and cool, never cute-blobby, never a lizard horror, never slimy or plastic. Must-haves:
  1. A broad flat head with a calm, clever face: glowing amber eyes without pupils under a slight
     brow, the mouth closed.
  2. A long, sleek, powerful body on splayed legs with spread toes, walking, the head raised and
     turned a little towards the viewer; a long tapering tail curling to one side.
  3. Dark basalt-black skin; a crust of raised cooled-lava plates along the back with glowing
     orange-red cracks between them; small obsidian spines down the spine.
  4. A warm ember-orange belly and toe tips.
  5. Matte rock-like skin with baked crease shading; the lava glow is a separate part.

Round 1: first build. Lofted trunk, a broad wedge head with crown plates, splayed legs, two rows
of crust plates either side of a glowing seam, obsidian spines down the middle.
"""
import argparse
import bisect
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

# The spine, from inside the head down the neck, along the back and out to the tip of the tail,
# which curls round to the -X side (towards the cameras).
SPINE = [(-0.28, -2.18, 2.86), (-0.12, -1.78, 2.15), (0.0, -1.2, 1.45), (0.0, -0.25, 1.12), (0.02, 0.72, 0.95),
         (0.0, 1.45, 0.66), (-0.3, 2.1, 0.36), (-0.95, 2.52, 0.2), (-1.68, 2.56, 0.12), (-2.22, 2.18, 0.08)]
# Half width and half height of the trunk at fractions of the spine's length.
GIRTH = [(0.00, 0.58, 0.48), (0.07, 0.62, 0.52), (0.15, 0.70, 0.50), (0.27, 0.72, 0.50), (0.38, 0.66, 0.48),
         (0.47, 0.62, 0.46), (0.56, 0.44, 0.36), (0.66, 0.29, 0.25), (0.78, 0.17, 0.15), (0.90, 0.09, 0.08),
         (1.00, 0.015, 0.015)]
SQUARE = 2.5           # squareness of the trunk's cross-section
BELLY = 0.78           # the underside is flatter than the back

HEAD_AT = Vector((-0.44, -2.62, 2.92))
SCALE = 1.08                       # the whole pet is built a little small and scaled up at the end
HEAD_ROT = (-4, 0, -16)            # a touch nose-down, turned towards -X (the cameras)
HEAD_SIZE = 1.14

SKIN = [(0.0, "#1C1A1C"), (0.3, "#242022"), (0.5, "#33221E"), (0.68, "#7A2E14"), (0.84, "#C2501C"), (1.0, "#EE7A2C")]
CRUST = [(0.0, "#8E2C10"), (0.22, "#4A2018"), (0.45, "#2E2826"), (0.8, "#423B38"), (1.0, "#57504B")]
OBSIDIAN = [(0.0, "#3A1610"), (0.25, "#141014"), (0.75, "#1E1A26"), (1.0, "#3A3550")]

LAYERS = ("g",)


def _layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in LAYERS]


def smooth(x, a, b):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def _cr(vals, t):
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _table(points, x, col=1):
    """Smooth reading of a table of rows (x, ...) at x, column col."""
    if x <= points[0][0]:
        return points[0][col]
    for r0, r1 in zip(points, points[1:]):
        if x <= r1[0]:
            return lerp(r0[col], r1[col], smooth(x, r0[0], r1[0]))
    return points[-1][col]


def _se(a, n):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


class Curve:
    """A smooth curve through `points`, read by the fraction t of its length (0 to 1)."""

    def __init__(self, points, n=200):
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


class Trunk:
    """The neck, body and tail as one skin round the spine. A point on it is read by (t, th): t the
    fraction along the spine, th the angle round it (0 is +X side, pi/2 the top of the back)."""

    def __init__(self):
        self.C = Curve(SPINE)

    def frame(self, t):
        T = self.C.tangent(t)
        up = Vector((0, 0, 1))
        N = (up - T * up.dot(T)).normalized()
        return T, T.cross(N), N

    def radii(self, t):
        return _table(GIRTH, t, 1), _table(GIRTH, t, 2)

    def point(self, t, th):
        t = min(max(t, 0.0), 1.0)
        T, W, N = self.frame(t)
        rx, rz = self.radii(t)
        x, y = _se(th, SQUARE)
        if y < 0:
            y *= BELLY
        return self.C.at(t) + W * (x * rx) + N * (y * rz)

    def normal(self, t, th):
        dt, da = 0.003, 0.02
        a = self.point(min(t + dt, 0.999), th) - self.point(max(t - dt, 0.001), th)
        b = self.point(t, th + da) - self.point(t, th - da)
        return a.cross(b).normalized()

    def rates(self, t, th):
        """Studs per unit of t, and per radian of th, at a point."""
        dt, da = 0.003, 0.02
        return ((self.point(t + dt, th) - self.point(t - dt, th)).length / (2 * dt),
                (self.point(t, th + da) - self.point(t, th - da)).length / (2 * da))

    def on(self, t, th, h=0.0):
        return self.point(t, th) + self.normal(t, th) * h

    def mesh(self, rings=72, segs=20):
        bm = bmesh.new()
        loops = []
        for i in range(rings + 1):
            t = (i / rings) ** 1.15                       # rings a little closer together near the head
            if i == rings:
                loops.append([bm.verts.new(self.C.at(1.0))])
                continue
            loops.append([bm.verts.new(self.point(t, 2 * math.pi * j / segs)) for j in range(segs)])
        for a, b in zip(loops, loops[1:]):
            for j in range(segs):
                if len(b) == 1:
                    bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
                else:
                    bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
        bm.faces.new(loops[0])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm


def skin_g(p, n):
    """Colour position of the skin: basalt on top, a dark red-brown flank, ember underneath."""
    return 0.22 + 0.33 * smooth(n.z, 0.1, -0.35) + 0.45 * smooth(n.z, -0.35, -0.8)


def gpaint(bm, fn=skin_g):
    bm.normal_update()
    lg = _layers(bm)[0]
    for v in bm.verts:
        v[lg] = fn(v.co, v.normal)
    return bm


def slab(outline, h, bevel=0.72, sink=0.05):
    """A crust plate: an irregular polygon `outline` (u, v) with straight walls from -sink up to
    0.7 h, a bevel in to a smaller top at h and a slightly raised middle. Each vertex has g from 0
    (the hot base) to 1 (the cool top). Returns (bm, a function mapping its verts afterwards)."""
    bm = bmesh.new()
    lg = _layers(bm)[0]
    k = len(outline)
    rings = []
    for scale, z, g in ((1.0, -sink, 0.0), (1.0, h * 0.62, 0.42), (bevel, h, 0.85)):
        ring = []
        for u, v in outline:
            vt = bm.verts.new((u * scale, v * scale, z))
            vt[lg] = g
            ring.append(vt)
        rings.append(ring)
    top = bm.verts.new((sum(u for u, _ in outline) / k * bevel, sum(v for _, v in outline) / k * bevel, h * 1.08))
    top[lg] = 1.0
    for a, b in zip(rings, rings[1:]):
        for j in range(k):
            bm.faces.new((a[j], a[(j + 1) % k], b[(j + 1) % k], b[j]))
    for j in range(k):
        bm.faces.new((rings[-1][j], rings[-1][(j + 1) % k], top))
    bm.faces.new(rings[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def outline(a, b, rnd, k=7, jag=0.2):
    """An irregular k-sided outline, a long (u) by b wide (v)."""
    off = rnd.uniform(0, 2 * math.pi)
    pts = []
    for j in range(k):
        ang = off + 2 * math.pi * (j + rnd.uniform(-0.25, 0.25)) / k
        r = 1.0 + rnd.uniform(-jag, jag * 0.4)
        pts.append((math.cos(ang) * a / 2 * r, math.sin(ang) * b / 2 * r))
    return pts


def on_trunk(trunk, bm, t0, th0):
    """Wrap a shape made flat in (u along the spine, v round it, z out of the skin) onto the trunk
    at (t0, th0)."""
    rt, ra = trunk.rates(t0, th0)
    for v in bm.verts:
        u, w, z = v.co
        v.co = trunk.on(t0 + u / rt, th0 + w / ra, z)
    bm.normal_update()
    return bm


def blade(L, W, D, lean, sides=5):
    """An obsidian spine: a faceted blade standing on +Z, L tall, W long at its base (along X), D
    thin, leaning back (+X) by `lean`. g from 0 at the base to 1 at the tip."""
    bm = bmesh.new()
    lg = _layers(bm)[0]
    rings = []
    for z, k, g in ((-0.06, 1.0, 0.0), (L * 0.45, 0.62, 0.45)):
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            vt = bm.verts.new((math.cos(a) * W / 2 * k + lean * z / L, math.sin(a) * D / 2 * k, z))
            vt[lg] = g
            ring.append(vt)
        rings.append(ring)
    tip = bm.verts.new((lean, 0, L))
    tip[lg] = 1.0
    a, b = rings
    for j in range(sides):
        bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        bm.faces.new((b[j], b[(j + 1) % sides], tip))
    bm.faces.new(a[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ramp_material(name, stops, rough=0.9, scales=None, mottle=None):
    """A ramp read from the vertex colour position g, with kit's scale pattern or a rocky mottle."""
    m = kit.material(name, stops[0][1], rough=rough)
    if scales:
        kit.scaly(m, **scales, rough=rough)
    else:
        kit.furry(m, **(mottle or dict(strength=0.08, mottle=0.14, fine=9.0, length=1.0)))
    tree = m.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    at = new("ShaderNodeAttribute")
    at.attribute_type, at.attribute_name = 'GEOMETRY', "g"
    rp = new("ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
    for pos, hexcode in stops[1:-1]:
        e = els.new(pos)
        e.color = (*kit.srgb(hexcode), 1.0)
    link(at.outputs["Fac"], rp.inputs["Fac"])
    link(rp.outputs["Color"], hsv.inputs["Color"])
    return m


def _ball(size, loc, rot=(0, 0, 0), cuts=3):
    bm = kit.ball(size, cuts=cuts)
    bm.transform(M(loc, rot=rot))
    return bm


# The head, lofted along -Y in its own space: y, half width, top, bottom (below the centre line).
HEAD = [(0.70, 0.46, 0.30, 0.32), (0.45, 0.70, 0.35, 0.37), (0.15, 0.75, 0.34, 0.32), (-0.18, 0.67, 0.30, 0.25),
        (-0.50, 0.55, 0.23, 0.19), (-0.82, 0.42, 0.16, 0.14), (-1.08, 0.29, 0.105, 0.10), (-1.22, 0.13, 0.06, 0.06)]
MOUTH = [(0.45, -0.16, 0.0), (0.32, -0.14, 0.05), (0.0, -0.11, 0.06), (-0.6, -0.07, 0.045), (-1.0, -0.05, 0.0)]   # y, z, groove depth


def head_shell(rings=18, segs=24):
    """One shell: flat crown, rounded sides, a flat jaw, and the mouth as a groove along each side
    that slopes gently down towards its corner (calm, not a grin) and fades out before the snout."""
    bm = bmesh.new()
    k = len(HEAD) - 1
    loops = []
    for i in range(rings + 1):
        u = i / rings * k
        y = _cr([h[0] for h in HEAD], u)
        w, zt, zb = (max(_cr([h[c] for h in HEAD], u), 0.02) for c in (1, 2, 3))
        mz = _table(MOUTH[::-1], y, 1)
        md = _table(MOUTH[::-1], y, 2)
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            cx, cz = _se(a, 3.4 if math.sin(a) > 0 else 2.4)
            x, z = w * cx, (zt if cz > 0 else zb) * cz
            # the groove: pull the side in where it crosses the mouth line
            x *= 1.0 - md * math.exp(-((z - mz) / 0.035) ** 2) * abs(cx) / max(w, 0.1)
            ring.append(bm.verts.new((x, y, z)))
        loops.append(ring)
    for a_, b_ in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a_[j], a_[(j + 1) % segs], b_[(j + 1) % segs], b_[j]))
    bm.faces.new(loops[0])
    bm.faces.new(loops[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def head_parts(rnd):
    """The head in its own space (snout towards -Y): the shell, recessed almond eyes under a brow
    shelf, and a few cooled-lava plates on the crown with the lava showing between them."""
    from mathutils.bvhtree import BVHTree
    shell = head_shell()
    bvh = BVHTree.FromBMesh(shell)

    def top(x, y):
        hit = bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)))
        return hit[0], hit[1]

    out = [("skin", shell)]
    for sx in (-1, 1):
        # the eye is sunk into the side of the head so only an almond shows; a shelf of brow sits
        # over it, level with the crown (no domes above the outline, no frown)
        eye_at, eye_rot = (sx * 0.57, -0.24, 0.16), (6, sx * 28, sx * 12)
        out.append(("rim", _ball((0.36, 0.2, 0.19), eye_at, rot=eye_rot, cuts=2)))
        out.append(("eye", _ball((0.33, 0.17, 0.16), (eye_at[0] + sx * 0.015, eye_at[1] - 0.01, eye_at[2] - 0.005), rot=eye_rot, cuts=3)))
        out.append(("skin", _ball((0.46, 0.24, 0.1), (sx * 0.58, -0.25, 0.25), rot=(2, sx * 30, sx * 8), cuts=2)))
        out.append(("rim", _ball((0.06, 0.05, 0.04), (sx * 0.15, -1.1, 0.075), cuts=1)))              # nostril
    # crown plates
    plates = [(0.0, 0.34, 0.36, 0.34), (-0.27, 0.06, 0.3, 0.26), (0.27, 0.06, 0.3, 0.26), (0.0, -0.08, 0.26, 0.24),
              (-0.2, 0.5, 0.24, 0.22), (0.2, 0.5, 0.24, 0.22), (0.0, -0.36, 0.2, 0.18)]
    for x, y, a, b in plates:
        p, n = top(x, y)
        bm = slab(outline(a, b, rnd, jag=0.12), 0.07, sink=0.05)
        z = Vector(n)
        xa = (Vector((0, -1, 0)) - z * z.y * -1).normalized()
        ya = z.cross(xa)
        m = Matrix((xa, ya, z)).transposed().to_4x4()
        m.translation = p
        bm.transform(m)
        out.append(("crust", bm))
    # the lava under them: a thin patch lying on the crown
    patch = bmesh.new()
    rings = []
    for r in (0.0, 0.16, 0.3):
        ring = []
        for j in range(1 if r == 0 else 10):
            ang = 2 * math.pi * j / 10
            p, n = top(math.cos(ang) * r * 1.05, 0.12 + math.sin(ang) * r * 1.4)
            ring.append((p, n))
        rings.append(ring)
    tops = [[patch.verts.new(p + n * 0.025) for p, n in ring] for ring in rings]
    for j in range(10):
        patch.faces.new((tops[0][0], tops[1][j], tops[1][(j + 1) % 10]))
        patch.faces.new((tops[1][j], tops[2][j], tops[2][(j + 1) % 10], tops[1][(j + 1) % 10]))
    under = [patch.verts.new(p - n * 0.04) for p, n in rings[2]]
    for j in range(10):
        patch.faces.new((tops[2][j], under[j], under[(j + 1) % 10], tops[2][(j + 1) % 10]))
    patch.faces.new(under[::-1])
    bmesh.ops.recalc_face_normals(patch, faces=patch.faces[:])
    out.append(("eye", patch))
    return out


def build():
    rnd = random.Random(7)
    skinm = ramp_material("Skin", SKIN, rough=0.9, scales=dict(size=0.085, joins=0.4, vary=0.2))
    crustm = ramp_material("Crust", CRUST, rough=0.95, mottle=dict(strength=0.1, mottle=0.2, fine=8.0, length=1.0))
    obsid = ramp_material("Obsidian", OBSIDIAN, rough=0.4, mottle=dict(strength=0.05, mottle=0.06, fine=30.0, length=2.0))
    rim = kit.material("Rim", "#0C0A0B", rough=0.6)
    glow = kit.material("GLOW_Lava", "#FF6A12", rough=0.4, emit=3.0)

    sal = Prop("Salamander")
    sal.tally = {}

    def add(part, bm, mat, at=None):
        _layers(bm)
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        sal.tally[part] = sal.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        sal.add(bm, mat)

    trunk = Trunk()
    add("trunk", gpaint(trunk.mesh()), skinm)

    # ---- head ---------------------------------------------------------------------------------------
    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    for kind, bm in head_parts(rnd):
        bm.transform(H)
        if kind == "skin":
            add("head", gpaint(bm), skinm)
        elif kind == "crust":
            add("plates", bm, crustm)
        elif kind == "rim":
            add("head", bm, rim)
        else:
            add("eyes", bm, glow)

    # ---- crust plates along the back, the lava seam under them, obsidian spines down the middle --------
    T0, T1 = 0.03, 0.80
    seam = 0.035                                      # half width of the glowing seam down the middle
    t = T0
    row = 0
    while t < T1:
        rx, _ = trunk.radii(t)
        s = min(max(rx / 0.7, 0.28), 1.0)
        a, b = 0.5 * s, 0.46 * s
        rt, ra = trunk.rates(t, math.pi / 2)
        for side in (-1, 1):
            v1 = seam + b / 2
            bm = slab(outline(a, b, rnd, jag=0.12), 0.12 * s + 0.03, sink=0.06)
            bm.transform(M((0, side * v1, 0)))
            add("plates", on_trunk(trunk, bm, t + rnd.uniform(-0.1, 0.1) * a / rt, math.pi / 2), crustm)
            if s > 0.45:                                 # an outer row, staggered, on the broad part
                v2 = v1 + b * 0.86
                bm = slab(outline(a * 0.85, b * 0.8, rnd, jag=0.12), 0.1 * s + 0.02, sink=0.06)
                bm.transform(M((0, side * v2, 0)))
                add("plates", on_trunk(trunk, bm, t + 0.5 * (a + 0.06) / rt, math.pi / 2), crustm)
        # a spine standing in the seam between this pair and the next
        if row % 1 == 0 and t < 0.72:
            bm = blade(0.42 * s + 0.06, 0.22 * s + 0.03, 0.08 * s + 0.02, lean=0.16 * s)
            T, W, N = trunk.frame(t)
            p = trunk.on(t + 0.5 * a / rt, math.pi / 2, -0.02)
            n = trunk.normal(t + 0.5 * a / rt, math.pi / 2)
            x = (T - n * T.dot(n)).normalized()
            y = n.cross(x)
            mm = Matrix((x, y, n)).transposed().to_4x4()
            mm.translation = p
            add("spines", bm, obsid, mm)
        t += (a + 0.035) / rt
        row += 1

    # the lava seam: a thin curved band lying just above the skin under the plates
    band = bmesh.new()
    loops = []
    nb = 44
    for i in range(nb + 1):
        tt = lerp(T0 - 0.01, T1 + 0.01, i / nb)
        rx, _ = trunk.radii(tt)
        s = min(max(rx / 0.7, 0.28), 1.0)
        half = seam + 0.46 * s * 0.72
        rt, ra = trunk.rates(tt, math.pi / 2)
        ring = []
        for j in range(6):
            th = math.pi / 2 + lerp(-half, half, j / 5) / ra
            ring.append(band.verts.new(trunk.on(tt, th, 0.035)))
        for th in (math.pi / 2 + half / ra, math.pi / 2 - half / ra):
            ring.append(band.verts.new(trunk.on(tt, th, -0.05)))
        loops.append(ring)
    m8 = len(loops[0])
    for a_, b_ in zip(loops, loops[1:]):
        for j in range(m8):
            band.faces.new((a_[j], a_[(j + 1) % m8], b_[(j + 1) % m8], b_[j]))
    band.faces.new(loops[0])
    band.faces.new(loops[-1][::-1])
    bmesh.ops.recalc_face_normals(band, faces=band.faces[:])
    add("seam", band, glow)

    # ---- legs: splayed, walking (near fore and far hind forward) -------------------------------------
    def leg(sx, y, fore, step):
        z0 = trunk.C.at(0.2 if fore else 0.45).z
        out_x = 1.38 if fore else 1.45
        shoulder = Vector((sx * 0.3, y, z0 - 0.1))
        elbow = Vector((sx * (out_x - 0.08), y - step * 0.22 + (0.12 if fore else -0.12), z0 + 0.06))
        wrist = Vector((sx * (out_x + 0.06), y - step * 0.5, 0.34))
        ankle = Vector((sx * (out_x + 0.1), y - step * 0.58, 0.15))
        r = (0.34, 0.25, 0.18, 0.16) if fore else (0.38, 0.28, 0.19, 0.16)
        bm = kit.tube([shoulder, elbow, wrist, ankle], r, segs=10)
        add("legs", gpaint(bm, lambda p, n: 0.2 + 0.5 * smooth(n.z, 0.1, -0.7)), skinm)
        # the foot: a broad palm with spread toes, the near ones turned out
        foot = Vector((ankle.x + sx * 0.05, ankle.y - 0.05, 0.08))
        palm = _ball((0.46, 0.44, 0.2), foot, cuts=2)
        add("feet", gpaint(palm, lambda p, n: 0.3), skinm)
        toes = 4 if fore else 5
        turn = math.radians(sx * (-20 if fore else -35))    # feet point forward and a little outward
        for k in range(toes):
            ang = turn + math.radians(lerp(-62, 62, k / (toes - 1)))
            L = (0.42 if fore else 0.46) * (1.0 - 0.18 * abs(k - (toes - 1) / 2) / ((toes - 1) / 2))
            d = Vector((math.sin(ang), -math.cos(ang), 0))
            base = foot + d * 0.12
            tip = foot + d * (0.12 + L)
            mid = base.lerp(tip, 0.5) + Vector((0, 0, 0.05))
            bm = kit.tube([base + Vector((0, 0, 0.04)), mid, tip + Vector((0, 0, 0.045))], (0.08, 0.055, 0.062), segs=6, rings=5)
            tl = (tip - base).length

            def toe_g(p, n, base=base, tl=tl):
                return 0.3 + 0.7 * smooth((p - base).length / tl, 0.45, 0.95)
            add("feet", gpaint(bm, toe_g), skinm)

    leg(-1, -1.05, True, 1.0)        # near foreleg steps forward
    leg(1, -1.05, True, -0.6)
    leg(-1, 0.9, False, -0.6)
    leg(1, 0.9, False, 1.0)

    sal.build(SCALE)
    for ob in sal.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return sal


def bake(sal, texture):
    """Everything that does not glow becomes one textured mesh, Salamander_Body: the skin, crust and
    soft shading in the creases are baked into its colour image. The glowing parts are joined into
    one mesh, Salamander_GLOW, that keeps its emissive material. Roblox gets two MeshParts."""
    import bpy
    glow = [ob for ob in sal.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in sal.objects if ob not in glow], texture, name="Salamander_Body",
                            shade=0.55, soften=3, rough=0.9, uv_angle=85.0, uv_margin=0.004, pack_margin=0.003)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = "Salamander_GLOW"
    sal.objects = [body, g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,side,top",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="full")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Lava Salamander review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "salamander_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    sal = build()
    print("triangles by part:", dict(sorted(sal.tally.items(), key=lambda kv: -kv[1])))
    head = (M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.2, 0.1))) * SCALE

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(sal, samples=samples, focus=(head.x + 0.3, head.y + 1.6, head.z - 1.2))
        turn = Matrix.Rotation(math.radians(HEAD_ROT[2]), 3, 'Z')
        for name, d, dist in (("face", (-0.55, -1.0, 0.25), 5.0), ("face front", (-0.05, -1.0, 0.12), 4.8)):
            rig.cams[name] = review._camera("C_" + name.replace(" ", ""), head + (turn @ Vector(d)).normalized() * dist,
                                            head + Vector((0, 0.2, -0.05)), 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(a.samples)
        lo, hi = sal.bounds()
        print("size in studs: %.2f wide, %.2f long, %.2f tall" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, cols=a.cols, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(sal, os.path.abspath(a.texture))
    tris = sal.triangles()
    lo, hi = sal.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = sal.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(sal.objects, os.path.abspath(a.export))
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
