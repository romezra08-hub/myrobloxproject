"""Puppy pet in a soft plush-toy style, built from scratch by script.

    python models/pets/puppy.py --review out/puppy.png      # render the review sheet
    python models/pets/puppy.py --export models/export/puppy.fbx

Style: a well-made stuffed toy dog, sitting. NOT a simulator pet: the head is about a third of
the height, there is a neck with a collar, a chest over haunches. Must-haves, checked every review:
  1. Reads as a dog in outline: long floppy ears that hang, a snout that sticks out in the side
     view, a short tail swung out to one side.
  2. Toy proportions: head about a third of the height, a visible neck, chest and haunches.
  3. Small friendly bead eyes with a highlight, a darker patch over one eye.
  4. A collar with a tag, in one accent colour.
  5. Not symmetrical: head tilted, one ear flopped differently, tail to one side.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, rounded_box, shear, split, taper, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0


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


def ribbon(points, widths, thicks, wdir, segs=12, rings=12, tip=0.22, tip_rings=4, n=2.4):
    """A flat strap lofted along a smooth path, for a floppy ear. widths and thicks are half sizes
    at each point; wdir is roughly the direction the width runs in. The far end is rounded off
    over the last `tip` of the length."""
    pts = [Vector(p) for p in points]
    k = len(pts) - 1
    us, fs = [i / rings * (1 - tip) for i in range(rings + 1)], [1.0] * (rings + 1)
    for j in range(1, tip_rings + 1):
        phi = (math.pi / 2) * j / (tip_rings + 0.4)
        us.append(1 - tip + tip * math.sin(phi))
        fs.append(math.cos(phi))
    path = [_cr(pts, u * k) for u in us]
    wd = Vector(wdir).normalized()
    bm = bmesh.new()
    loops = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        w = (wd - t * wd.dot(t)).normalized()
        nrm = t.cross(w).normalized()
        hw = max(1e-3, _cr(list(widths), us[i] * k)) * fs[i]
        ht = max(1e-3, _cr(list(thicks), us[i] * k)) * fs[i] ** 0.5
        ring = []
        for j in range(segs):
            x, y = _super(2 * math.pi * j / segs, n)
            ring.append(bm.verts.new(p + w * x * hw + nrm * y * ht))
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, c in ((loops[0], path[0]), (loops[-1], _cr(pts, float(k)))):
        cv = bm.verts.new(c)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], cv))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def band(radius, half_thick, half_height, segs=28, ring=8, n=3.0):
    """A ring with a rounded-rectangle section, lying flat round the Z axis: a collar."""
    bm = bmesh.new()
    loops = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        out = Vector((math.cos(a), math.sin(a), 0))
        loop = []
        for j in range(ring):
            x, y = _super(2 * math.pi * j / ring, n)
            loop.append(bm.verts.new(out * (radius + x * half_thick) + Vector((0, 0, y * half_height))))
        loops.append(loop)
    for i in range(segs):
        a, b = loops[i], loops[(i + 1) % segs]
        for j in range(ring):
            bm.faces.new((a[j], a[(j + 1) % ring], b[(j + 1) % ring], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


class Press:
    """Presses flat things onto the mesh `target` from the direction `facing`: at(x, y) is the point
    of the surface under (x, y) of a flat sheet held in front of it at `centre`."""

    def __init__(self, target, centre, facing, up=(0, 0, 1)):
        self.bvh = BVHTree.FromBMesh(target)
        self.f = Vector(facing).normalized()
        self.u = Vector(up).cross(self.f).normalized()
        self.v = self.f.cross(self.u).normalized()
        self.c = Vector(centre)

    def at(self, x, y, lift=0.0):
        loc, nrm, _, _ = self.bvh.ray_cast(self.c + self.u * x + self.v * y + self.f * 6.0, -self.f)
        if loc is None:
            raise ValueError("nothing under (%.2f, %.2f)" % (x, y))
        return loc + nrm * lift


def applique(press, outline, lift=0.022, rings=4, segs=20):
    """A sewn-on patch: the blob outline(angle) -> radius, pressed on. It sits `lift` proud of the
    surface and its rim is tucked just under it."""
    bm = bmesh.new()
    mid = bm.verts.new(press.at(0, 0, lift))
    steps = [(i / rings, lift) for i in range(1, rings)] + [(0.93, lift), (1.0, -lift)]
    loops = []
    for frac, h in steps:
        angles = [2 * math.pi * j / segs for j in range(segs)]
        loops.append([bm.verts.new(press.at(math.cos(a) * outline(a) * frac, math.sin(a) * outline(a) * frac, h)) for a in angles])
    for j in range(segs):
        bm.faces.new((mid, loops[0][j], loops[0][(j + 1) % segs]))
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], b[j], b[(j + 1) % segs], a[(j + 1) % segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((fc.normal for fc in bm.faces), Vector()).dot(press.f) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def stitches(press, outline, count, reach=0.038, phase=0.0, r=0.011):
    """Short threads across the edge of a patch, as if it were sewn on by hand."""
    out = []
    for k in range(count):
        a = phase + 2 * math.pi * k / count
        r0, r1 = outline(a) - reach, outline(a) + reach
        p0 = press.at(math.cos(a) * r0, math.sin(a) * r0, 0.029)
        p1 = press.at(math.cos(a) * r1, math.sin(a) * r1, 0.007)
        out.append(tube([p0, p1], [r, r], segs=4, rings=1))
    return out


def square_stitches(press, half, turn, reach=0.04, r=0.011):
    """Two threads straight across each side of a square patch (squarish(half, turn=turn))."""
    out = []
    for side in range(4):
        a = turn + side * math.pi / 2
        nx, ny = math.cos(a), math.sin(a)
        for off in (-0.45 * half, 0.45 * half):
            ends = [press.at(nx * d - ny * off, ny * d + nx * off, h) for d, h in ((half - reach, 0.029), (half + reach, 0.007))]
            out.append(tube(ends, [r, r], segs=4, rings=1))
    return out


def dashes(points, r=0.012):
    """A running stitch: a short thread for each (start, end) pair of points."""
    return [tube([a, b], [r, r], segs=4, rings=1) for a, b in points]


def squarish(half, n=5.0, turn=0.0):
    """An outline for applique(): a square with soft corners, turned by `turn` radians."""
    def r(a):
        c, sn = abs(math.cos(a - turn)), abs(math.sin(a - turn))
        return half / (c ** n + sn ** n) ** (1.0 / n)
    return r


def oval(rx, rz, wobble=0.0, phase=0.0):
    """An outline for applique(): an ellipse, optionally a bit uneven."""
    def r(a):
        base = 1.0 / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / rz) ** 2)
        return base * (1 + wobble * math.sin(2 * a + phase) + 0.6 * wobble * math.sin(3 * a + 2 * phase))
    return r


def grounded(bm, at):
    """Move a shape into place and flatten whatever would go below the floor, like a beanbag."""
    bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def front_of(bm, x, z, out=0.0):
    """The point on the front (-Y side) of a mesh at (x, z), pushed `out` towards the viewer."""
    loc, _, _, _ = BVHTree.FromBMesh(bm).ray_cast(Vector((x, -6.0, z)), Vector((0, 1, 0)))
    return Vector((loc.x, loc.y - out, loc.z))


def toe_lines(paw, centre, yaw, offsets=(-0.085, 0.085)):
    """Two stitched toe lines over the front of a paw (a mesh already in place, turned `yaw` degrees)."""
    bvh = BVHTree.FromBMesh(paw)
    a = math.radians(yaw)
    fwd, side, upv = Vector((math.sin(a), -math.cos(a), 0)), Vector((math.cos(a), math.sin(a), 0)), Vector((0, 0, 1))
    lines = []
    for off in offsets:
        pts = []
        for phi in (72, 42, 14, -10):
            d = fwd * math.cos(math.radians(phi)) + upv * math.sin(math.radians(phi))
            o = Vector(centre) + fwd * 0.1 + side * off
            loc = bvh.ray_cast(o + d * 3.0, -d)[0]
            pts.append(loc + d * 0.008)
        lines.append(tube(pts, [0.008, 0.017, 0.017, 0.008], segs=4, rings=3))
    return lines


# ---- the puppy -----------------------------------------------------------------------------------

def build():
    tan = kit.material("Tan", "#D9A569", rough=0.9)
    cream = kit.material("Cream", "#FAEBD2", rough=0.9)
    brown = kit.material("Brown", "#70452A", rough=0.9)
    gloss = kit.material("Gloss", "#141012", rough=0.1)
    red = kit.material("Collar", "#D5402E", rough=0.5)
    # Round 7: the owner said smooth flat colours look like cheap plastic. The cloth parts get a short
    # fleecy nap baked into the texture, a matte finish and a soft rim, like real plush.
    for mat in (tan, cream, brown):
        kit.furry(mat, strength=0.24, mottle=0.1, fine=34.0, length=2.2, shade_down=0.06)
    pup = Prop("Puppy")

    # ---- body: a pear that leans forward, chest over the front legs, weight on the haunches ------------
    body = rounded_box((1.36, 1.3, 1.74), n=2.3, cuts=7)
    taper(body, axis=2, lo=1.14, hi=0.86)
    shear(body, axis=2, along=1, amount=-0.5, power=1.3)
    grounded(body, M((0, 0.32, 0.8)))
    pup.add(applique(Press(body, (0, 0, 1.0), (0, -1, 0.22)), oval(0.4, 0.62), rings=4, segs=20), cream)   # belly
    pup.add(applique(Press(body, (0.1, 0.1, 1.1), (0.8, 1, 0.35)), oval(0.32, 0.42, 0.12, 2.0), rings=3, segs=18), brown)   # saddle spot
    back = Press(body, (0, 0.3, 1.05), (0, 1, 0.3))                                                   # a running stitch down the back seam
    for d in dashes([(back.at(0, 0.42 - 0.17 * i, 0.01), back.at(0, 0.32 - 0.17 * i, 0.01)) for i in range(5)]):
        pup.add(d, brown)
    lab = back.at(0.0, -0.055)                                                                        # the toy's label, sewn into that seam
    pup.add(rounded_box((0.035, 0.24, 0.15), n=5.0, cuts=2), red, M((lab.x + 0.04, lab.y + 0.07, lab.z), rot=(0, 0, -30)))
    pup.add(body, tan)

    for sx in (-1, 1):
        leg = tube([(0.24 * sx, -0.1, 1.52), (0.36 * sx, -0.3, 1.2), (0.41 * sx, -0.56, 0.68), (0.41 * sx, -0.66, 0.12)],
                   [0.1, 0.26, 0.21, 0.19], segs=10, rings=8)
        pup.add(leg, tan)
        paw = grounded(rounded_box((0.52, 0.64, 0.36), n=2.4, cuts=4), M((0.41 * sx, -0.8, 0.17), rot=(0, 0, 6 * sx)))
        for line in toe_lines(paw, (0.41 * sx, -0.8, 0.14), 6 * sx):
            pup.add(line, brown)
        pup.add(paw, cream)
        hip = grounded(ball((0.8, 1.02, 0.86), cuts=5), M((0.6 * sx, 0.34, 0.42), rot=(0, 0, 10 * sx)))
        if sx < 0:                                                                                    # mended once: a square patch, hand stitched
            mend = Press(hip, (-0.6, 0.38, 0.5), (-1, 0.05, 0.6), up=(0, 1, 0))
            pup.add(applique(mend, squarish(0.19, n=7.0, turn=0.25), rings=2, segs=16), cream)
            for st in square_stitches(mend, 0.19, 0.25):
                pup.add(st, brown)
        pup.add(hip, tan)
        foot = grounded(rounded_box((0.44, 0.76, 0.34), n=2.4, cuts=3), M((0.76 * sx, -0.3, 0.16), rot=(0, 0, 14 * sx)))
        for line in toe_lines(foot, (0.76 * sx + 0.04 * sx, -0.46, 0.13), 14 * sx, offsets=(-0.075, 0.075)):
            pup.add(line, brown)
        pup.add(foot, cream)

    # ---- tail: short, swung out to the side the cameras see ----------------------------------------
    tail = tube([(-0.08, 0.82, 0.4), (-0.32, 1.2, 0.5), (-0.6, 1.42, 0.78), (-0.78, 1.42, 1.1), (-0.83, 1.3, 1.36), (-0.82, 1.22, 1.45)],
                [0.22, 0.23, 0.21, 0.18, 0.13, 0.03], segs=10, rings=15)
    t = tail.faces.layers.float["t"]
    tip, rest = split(tail, lambda f: f[t] > 0.66)
    pup.add(tip, cream)
    pup.add(rest, tan)

    # ---- neck and collar -------------------------------------------------------------------------
    pup.add(tube([(0, -0.1, 1.2), (0, -0.2, 1.72), (0, -0.33, 2.3)], [0.3, 0.4, 0.39], segs=12, rings=4), tan)
    C = M((0, -0.22, 1.82), rot=(18, 0, 0))
    pup.add(band(0.405, 0.04, 0.085, segs=24, ring=6, n=4.0), red, C)
    pup.add(ball((0.25, 0.07, 0.25), cuts=2), cream, C @ M((0, -0.455, -0.18), rot=(-18, 0, 0)))         # the tag

    # ---- head: everything is placed round the head's own centre, then tilted as one ---------------
    H = M((0, -0.36, 2.62), rot=(-2, 7, -8))
    head = taper(rounded_box((1.46, 1.32, 1.2), n=2.3, cuts=10), axis=2, lo=1.06, hi=0.93)
    ex, ez = 0.33, 0.12
    eye_at = {sx: front_of(head, ex * sx, ez) for sx in (-1, 1)}
    spot, blob = Press(head, eye_at[-1] + Vector((-0.07, 0, 0.05)), (-0.42, -1, 0.12)), oval(0.3, 0.36, 0.1, 0.8)
    pup.add(applique(spot, blob, rings=3, segs=20), brown, H)
    for st in stitches(spot, blob, 10, phase=0.2):
        pup.add(st, cream, H)
    hb = BVHTree.FromBMesh(head)                                                                      # seam: over the top, down the back

    def on_head(phi):                                                                                 # phi: degrees back from straight up
        d = Vector((0, math.sin(math.radians(phi)), math.cos(math.radians(phi))))
        loc, nrm, _, _ = hb.ray_cast(d * 6.0, -d)
        return loc + nrm * 0.01
    for d in dashes([(on_head(-22 + 17 * i), on_head(-12 + 17 * i)) for i in range(8)]):
        pup.add(d, brown, H)
    pup.add(head, tan, H)

    muzzle = rounded_box((0.76, 0.66, 0.54), n=2.5, cuts=5)
    muzzle.transform(M((0, -0.68, -0.22)))
    for sx in (-1, 1):                                                                                # a small stitched smile
        pts = [front_of(muzzle, x * sx, z, 0.012) for x, z in ((0.0, -0.29), (0.07, -0.35), (0.16, -0.36), (0.23, -0.31))]
        pup.add(tube(pts, [0.022, 0.024, 0.022, 0.01], segs=6, rings=6), brown, H)
    pup.add(tube([front_of(muzzle, 0, -0.14, 0.012), front_of(muzzle, 0, -0.29, 0.012)], [0.02, 0.022], segs=6, rings=2), brown, H)
    for sx in (-1, 1):                                                                                # whisker dots
        for x, z in ((0.2, -0.15), (0.28, -0.2), (0.21, -0.245)):
            d = front_of(muzzle, x * sx, z)
            pup.add(ball((0.042, 0.03, 0.042), cuts=0), brown, H @ M((d.x, d.y, d.z)))
    pup.add(muzzle, cream, H)
    pup.add(ball((0.26, 0.18, 0.19), cuts=3), gloss, H @ M((0, -1.0, -0.06)))                           # nose

    for sx in (-1, 1):
        e = eye_at[sx]
        pup.add(ball((0.18, 0.14, 0.2), cuts=3), gloss, H @ M((e.x, e.y + 0.01, e.z), rot=(0, 0, -14 * sx)))
        pup.add(ball((0.06, 0.04, 0.06), cuts=1), cream, H @ M((e.x - 0.035, e.y - 0.055, e.z + 0.045)))  # highlight, same side on both

    # ears: flat straps that come out of the top of the head and hang; the left one is kinked outwards
    ear_r = ribbon([(0.36, 0.06, 0.5), (0.6, 0.06, 0.5), (0.8, 0.04, 0.2), (0.87, 0.0, -0.22), (0.85, -0.05, -0.62)],
                   [0.16, 0.24, 0.31, 0.36, 0.34], [0.08, 0.08, 0.075, 0.07, 0.07], (0.3, 1, 0), segs=10)
    pup.add(ear_r, brown, H)
    ear_l = ribbon([(-0.36, 0.06, 0.5), (-0.62, 0.06, 0.54), (-0.9, 0.03, 0.34), (-1.02, -0.02, -0.02), (-0.98, -0.08, -0.4)],
                   [0.16, 0.24, 0.31, 0.36, 0.34], [0.08, 0.08, 0.075, 0.07, 0.07], (-0.3, 1, 0), segs=10)
    pup.add(ear_l, brown, H)

    pup.build(SCALE)
    return pup


def bake(pup, texture):
    """Fur, cream, brown and collar become one textured mesh with soft shading baked in,
    so the toy stops looking like flat-coloured clay. The glossy eyes and nose stay a mesh of
    their own. Roblox gets two MeshParts instead of five."""
    gloss = [ob for ob in pup.objects if ob.name.endswith("_Gloss")]
    body = kit.bake_texture([ob for ob in pup.objects if ob not in gloss], texture, name="Puppy_Body", shade=0.5, soften=3, rough=0.95, sheen=0.4)
    pup.objects = [body] + gloss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "puppy_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    pup = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(pup, os.path.abspath(a.texture))
    tris = pup.triangles()
    lo, hi = pup.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(pup.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        import review
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig = review.Rig(pup, focus=(0, -0.95 * SCALE, 2.5 * SCALE))
        rig.sheet(os.path.abspath(a.review), review.STANDARD, px=a.px, title="Puppy (plush) review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
