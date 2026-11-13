"""Unicorn pet, low-poly papercraft style, built from scratch by script.

    python models/pets/unicorn_v2.py --review out/unicorn.png      # render the review sheet
    python models/pets/unicorn_v2.py --export models/export/unicorn.fbx

Style: a designer low-poly figurine. Flat shading, few big planes that follow the anatomy.
Must-haves, checked in every review:
  1. Reads as a unicorn in outline: arched neck, long legs, long tapered head, horn, flowing tail.
  2. Faceted on purpose: planes that follow the horse's build, never a pile of boxes.
  3. Pale body, pastel pink and blue mane and tail in a few bold locks, gold hooves, glowing horn.
  4. Small dark almond eyes with a tiny highlight; friendly, not creepy.
  5. Alive: one front leg raised, head turned, tail swung to one side.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402
from kit import M, Prop  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

SCALE = 1.0
LEAN = -0.10                      # how far the top of the neck swings to the side the head turns to
POLL = (-0.98, 3.12)              # (y, z) where the head hangs from the neck
HEAD = 1.12                       # head size, a little larger than life so the face reads
PITCH, ROLL, YAW = 45, 4, -18     # head: nose down, a small tilt, turned towards -X


def V(x, y, z):
    return Vector((x, y, z))


# ---- faceted building blocks ------------------------------------------------------------------------

def loft(rings, caps=(True, True)):
    """A closed skin over a list of rings. A ring is a list of points (all rings the same count)
    or a single Vector, which makes a pointed end. Everything is triangulated: the facets are the look."""
    bm = bmesh.new()
    vr = [[bm.verts.new(r)] if isinstance(r, Vector) else [bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vr, vr[1:]):
        if len(a) == 1:
            for j in range(len(b)):
                bm.faces.new((a[0], b[j], b[(j + 1) % len(b)]))
        elif len(b) == 1:
            for j in range(len(a)):
                bm.faces.new((a[j], a[(j + 1) % len(a)], b[0]))
        else:
            n = len(a)
            for j in range(n):
                bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    if caps[0] and len(vr[0]) > 2:
        bm.faces.new(vr[0])
    if caps[1] and len(vr[-1]) > 2:
        bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    if any(len(e.link_faces) != 2 for e in bm.edges):
        print("warning: a lofted part is not closed")
    return bm


def frames(path):
    """For points (x, y, z, ...) of a path that bends in the YZ plane: centre, tangent, the normal
    lying in that plane, and how much to stretch the ring at a bend so the limb keeps its thickness."""
    pts = [V(0, p[1], p[2]) for p in path]
    out = []
    for i in range(len(pts)):
        tin = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        tout = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        tin = tout if tin is None else tin
        tout = tin if tout is None else tout
        t = (tin + tout).normalized()
        miter = min(1.0 / max(t.dot(tout), 0.6), 1.5)
        out.append((V(path[i][0], path[i][1], path[i][2]), t, V(0, t.z, -t.y), miter))
    return out


HEX = [(math.cos(math.radians(90 + 60 * j)), math.sin(math.radians(90 + 60 * j))) for j in range(6)]


def limb(path, profile=HEX, caps=(True, True)):
    """Rings of `profile` (u across X, v along the path's in-plane normal) along a path of
    (x, y, z, half width, half depth). With HEX there is a ridge down the front and the back."""
    rings = []
    for (c, t, n, miter), p in zip(frames(path), path):
        rings.append([c + V(1, 0, 0) * (u * p[3]) + n * (v * p[4] * miter) for u, v in profile])
    return loft(rings, caps)


DIAMOND = [(1, 0), (0, 1), (-1, 0), (0, -0.6)]


def shard(points, widths, thick, wide=None, flat=None, profile=DIAMOND):
    """A lock of hair: a flat faceted blade along `points` that ends in a point. Give either `wide`
    (roughly the direction of its broad axis) or `flat` (roughly the normal of its broad face)."""
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts[:-1]):
        t = (pts[i + 1] - pts[max(i - 1, 0)]).normalized()
        if wide is not None:
            side = Vector(wide) - t * t.dot(Vector(wide))
            side.normalize()
            nrm = t.cross(side).normalized()
        else:
            nrm = Vector(flat) - t * t.dot(Vector(flat))
            nrm.normalize()
            side = nrm.cross(t).normalized()
        rings.append([p + side * (u * widths[i]) + nrm * (v * thick[i]) for u, v in profile])
    rings.append(pts[-1])
    return loft(rings)


def barrel(y, zt, zb, w, ku=0.6, kl=0.62, mid=0.5, fu=0.13, fl=0.15):
    """One cross-section of the trunk at y: a ridge along the spine and the belly, widest at `mid`."""
    h = zt - zb
    half = [(0, zt), (w * ku, zt - fu * h), (w, zb + mid * h), (w * kl, zb + fl * h), (0, zb)]
    pts = half + [(-x, z) for x, z in reversed(half[1:-1])]
    return [V(x, y, z) for x, z in pts]


def head_ring(s, wt, wm, wb, zt, zm, zb):
    """A cross-section of the head, s along the nose (-Y): flat brow, cheek corner, flat jaw."""
    return [V(wt, -s, zt), V(wm, -s, zm), V(wb, -s, zb), V(-wb, -s, zb), V(-wm, -s, zm), V(-wt, -s, zt)]


def hoof(h=0.16, k=1.18):
    """Top at the origin, sole h below, toe forward."""
    top = [V(0.086 * k * u, 0.094 * k * v, 0.03) for u, v in HEX]
    sole = [V(0.118 * k * u, 0.13 * k * v - 0.045 * k, -h) for u, v in HEX]
    return loft([top, sole])


def almond(sx, length=0.16, height=0.085, bulge=0.03, back=0.04):
    """An eye that faces sx along X: a dark almond, the corner towards the nose a little lower."""
    outline = [(-0.5, -0.08), (-0.18, 0.5), (0.2, 0.45), (0.5, 0.12), (0.2, -0.42), (-0.2, -0.5)]
    r0 = [V(-sx * back, y * length, z * height) for y, z in outline]
    r1 = [V(sx * bulge * 0.45, y * length, z * height) for y, z in outline]
    return loft([r0, r1, V(sx * bulge, 0, 0)])


def gem(r):
    """A tiny eight-sided sparkle."""
    return loft([V(0, 0, -r), [V(r, 0, 0), V(0, r, 0), V(-r, 0, 0), V(0, -r, 0)], V(0, 0, r)])


def ear(sx):
    r0 = [V(0.055, 0, 0), V(0, 0.04, 0), V(-0.055, 0, 0), V(0, -0.04, 0)]
    r1 = [V(0.07, 0, 0.1), V(0, 0.045, 0.1), V(-0.07, 0, 0.1), V(0, -0.035, 0.1)]
    return loft([r0, r1, V(0.012 * sx, 0, 0.3)])


def lean_x(z):
    t = min(max((z - 1.95) / 1.2, 0.0), 1.2)
    return LEAN * t ** 1.4


def warp(bm):
    """Swing the neck, and whatever grows on it, towards the side the head turns to."""
    for v in bm.verts:
        v.co.x += lean_x(v.co.z)
    return bm


# ---- the unicorn ---------------------------------------------------------------------------------------

# The neck is drawn by its two outlines, seen from the side: the crest (top line, convex, so the
# neck arches) and the throat (under line). Each ring spans from one to the other.
CREST = [(-0.05, 1.98), (-0.14, 2.42), (-0.28, 2.82), (-0.52, 3.13), (-0.84, 3.30), (-1.02, 3.20)]
THROAT = [(-0.80, 1.58), (-0.88, 2.02), (-0.82, 2.44), (-0.86, 2.74), (-1.00, 2.94), (-1.10, 3.04)]
NECK_W = [0.33, 0.29, 0.23, 0.19, 0.16, 0.08]
NECK_PROFILE = [(0, 1), (0.7, 0.45), (1, -0.25), (0.5, -0.9), (-0.5, -0.9), (-1, -0.25), (-0.7, 0.45)]


def neck():
    rings = []
    for (cy, cz), (ty, tz), w in zip(CREST, THROAT, NECK_W):
        c, t = V(0, cy, cz), V(0, ty, tz)
        mid, half = (c + t) / 2, (c - t) / 2
        rings.append([mid + half * v + V(1, 0, 0) * (u * w) for u, v in NECK_PROFILE])
    return loft(rings)


def neck_at(u):
    """Crest point, outward normal and half width of the neck at u (0 at the withers, 1 at the poll)."""
    x = u * 4.0
    k = min(int(x), 3)
    f = x - k
    c0, c1 = V(0, *CREST[k]), V(0, *CREST[k + 1])
    n0, n1 = (c0 - V(0, *THROAT[k])).normalized(), (c1 - V(0, *THROAT[k + 1])).normalized()
    return c0.lerp(c1, f), n0.lerp(n1, f).normalized(), NECK_W[k] + (NECK_W[k + 1] - NECK_W[k]) * f


def build():
    body = kit.material("Body", "#DAD2F0", rough=0.7)
    pink = kit.material("ManePink", "#FF9CCB", rough=0.55)
    blue = kit.material("ManeBlue", "#8ECFFF", rough=0.55)
    gold = kit.material("Gold", "#EDB740", rough=0.38, metal=0.25)
    eye = kit.material("Eye", "#2A2244", rough=0.25)
    glow = kit.material("GLOW_Horn", "#FFD45E", rough=0.4, emit=0.6)
    uni = Prop("Unicorn")

    # ---- trunk: deep chest, a dip behind the withers, belly tucked up towards the flank -------------
    trunk = [barrel(-0.84, 1.92, 1.55, 0.17),
             barrel(-0.62, 2.10, 1.27, 0.38),
             barrel(-0.30, 2.18, 1.15, 0.45),
             barrel(0.18, 2.07, 1.20, 0.46),
             barrel(0.58, 2.10, 1.36, 0.41),
             barrel(0.90, 2.18, 1.42, 0.45),
             barrel(1.14, 2.06, 1.56, 0.31),
             barrel(1.24, 1.94, 1.72, 0.14)]
    uni.add(loft(trunk), body)

    # ---- legs: (x, y, z, half width, half depth) from the top down ------------------------------------
    def front_leg(sx):
        return [(0.22 * sx, -0.40, 2.05, 0.09, 0.18), (0.30 * sx, -0.40, 1.80, 0.17, 0.33),
                (0.295 * sx, -0.36, 1.38, 0.16, 0.24), (0.28 * sx, -0.40, 0.98, 0.10, 0.115),
                (0.28 * sx, -0.42, 0.84, 0.112, 0.13), (0.28 * sx, -0.40, 0.70, 0.084, 0.094),
                (0.27 * sx, -0.39, 0.37, 0.076, 0.086), (0.27 * sx, -0.41, 0.27, 0.095, 0.106),
                (0.27 * sx, -0.48, 0.16, 0.086, 0.097)]

    def hind_leg(sx, dy=0.0):
        return [(0.22 * sx, 0.80, 2.10, 0.09, 0.20), (0.30 * sx, 0.78, 1.82, 0.19, 0.40),
                (0.30 * sx, 0.69 + dy * 0.3, 1.42, 0.17, 0.28), (0.285 * sx, 0.86 + dy * 0.6, 1.08, 0.105, 0.145),
                (0.28 * sx, 1.04 + dy, 0.86, 0.092, 0.112), (0.28 * sx, 1.02 + dy, 0.70, 0.082, 0.094),
                (0.275 * sx, 0.96 + dy, 0.37, 0.076, 0.086), (0.275 * sx, 0.94 + dy, 0.27, 0.095, 0.106),
                (0.275 * sx, 0.86 + dy, 0.16, 0.086, 0.097)]

    raised = [(-0.22, -0.40, 2.05, 0.09, 0.18), (-0.30, -0.40, 1.80, 0.17, 0.33),
              (-0.295, -0.40, 1.40, 0.16, 0.24), (-0.285, -0.70, 1.12, 0.10, 0.115),
              (-0.285, -0.81, 1.01, 0.11, 0.125), (-0.285, -0.79, 0.86, 0.084, 0.094),
              (-0.28, -0.64, 0.58, 0.076, 0.086), (-0.28, -0.60, 0.48, 0.095, 0.104),
              (-0.28, -0.55, 0.37, 0.086, 0.095)]

    for path in (front_leg(1), hind_leg(1, -0.06), hind_leg(-1, 0.08)):
        uni.add(limb(path), body)
        x, y, z = path[-1][:3]
        uni.add(hoof(), gold, M((x, y, z)))
    uni.add(limb(raised), body)
    uni.add(hoof(), gold, M((raised[-1][0], raised[-1][1], raised[-1][2]), rot=(30, 0, 0)))

    # ---- neck: thick at the shoulder, arched, thin at the throat ---------------------------------------
    uni.add(warp(neck()), body)

    # ---- head, hung from the poll; everything on it is placed in the head's own space ------------------
    H = M((lean_x(POLL[1]), POLL[0], POLL[1]), rot=(PITCH, ROLL, YAW), scale=HEAD)
    skull = [head_ring(-0.12, 0.06, 0.10, 0.05, 0.05, -0.07, -0.18),
             head_ring(0.10, 0.10, 0.165, 0.085, 0.115, -0.04, -0.33),
             head_ring(0.30, 0.085, 0.15, 0.07, 0.095, -0.07, -0.31),
             head_ring(0.55, 0.06, 0.10, 0.05, 0.045, -0.07, -0.20),
             head_ring(0.78, 0.055, 0.095, 0.055, 0.0, -0.085, -0.185),
             head_ring(0.90, 0.035, 0.065, 0.04, -0.04, -0.095, -0.155)]
    uni.add(loft(skull), body, H)

    for sx in (-1, 1):
        E = H @ M((0.1205 * sx, -0.26, 0.0175), rot=(0, -21.7 * sx, -5 * sx))
        uni.add(almond(sx), eye, E)
        uni.add(gem(0.02), body, E @ M((0.024 * sx, -0.03, 0.014)))
        uni.add(ear(sx), body, H @ M((0.09 * sx, 0.03, 0.04), rot=(-30, 22 * sx, 0)))

    # horn: five stacked, twisted steps, so it reads as a spiral
    HN = H @ M((0, -0.2, 0.06), rot=(-25, 0, 0))
    length, r0, steps = 0.84, 0.092, 5
    for k in range(steps):
        z0, z1 = length * k / steps, length * (k + 1) / steps
        rb = r0 * (1 - k / (steps + 0.4))
        rt = r0 * (1 - (k + 1) / (steps + 0.4)) * 0.62

        def ring(r, z, turn):
            return [V(r * math.cos(math.radians(turn + 72 * j)), r * math.sin(math.radians(turn + 72 * j)), z) for j in range(5)]
        top = V(0, 0, z1) if k == steps - 1 else ring(rt, z1 + 0.01, 36 * k + 24)
        uni.add(loft([ring(rb, z0, 36 * k), top]), glow, HN)

    # forelock: one bold lock swept to the side the head turns to, a smaller one the other way
    uni.add(shard([(0.0, 0.07, 0.02), (-0.03, -0.04, 0.17), (-0.10, -0.13, 0.17), (-0.17, -0.16, 0.08)],
                  [0.06, 0.075, 0.06], [0.04, 0.045, 0.035], flat=(-0.4, 0, 1)), pink, H)
    uni.add(shard([(0.0, 0.07, 0.02), (0.03, -0.03, 0.15), (0.09, -0.09, 0.14), (0.14, -0.10, 0.07)],
                  [0.05, 0.06, 0.045], [0.035, 0.04, 0.03], flat=(0.4, 0, 1)), blue, H)

    # ---- mane: six bold locks along the crest, falling back and to the show side -----------------------
    X, back, down = V(-1, 0, 0), V(0, 1, 0), V(0, 0, -1)
    locks = ((0.95, 0.72, blue), (0.83, 0.92, pink), (0.70, 1.0, blue), (0.56, 1.0, pink), (0.42, 0.85, blue), (0.28, 0.62, pink))
    for u, L, mat in locks:
        C, n, w = neck_at(u)
        out = 0.05 + 0.10 * (1 - u)
        pts = [C - n * 0.10,
               C + n * 0.09 + X * 0.03,
               C + n * 0.17 + (back * 0.16 + down * 0.10) * L + X * (0.05 + out * 0.4),
               C + n * 0.15 + (back * 0.38 + down * 0.34) * L + X * (0.05 + out * 0.8),
               C + n * 0.14 + (back * 0.60 + down * 0.64) * L + X * (0.06 + out)]
        uni.add(warp(shard(pts, [0.09, 0.14, 0.16, 0.11], [0.06, 0.075, 0.07, 0.05], flat=(-1, 0, 0.35))), mat)

    # ---- tail: three big locks from the dock, up, over and down, swung to the show side ----------------
    TAIL = M((0, -0.06, 0))
    uni.add(shard([(0, 1.18, 1.90), (-0.02, 1.42, 2.04), (-0.08, 1.68, 1.86), (-0.15, 1.80, 1.40), (-0.20, 1.76, 0.92), (-0.30, 1.98, 0.42)],
                  [0.09, 0.15, 0.20, 0.21, 0.15], [0.08, 0.12, 0.15, 0.14, 0.10], wide=(1, 0, 0)), pink, TAIL)
    uni.add(shard([(0, 1.20, 1.94), (0.02, 1.50, 2.12), (0.0, 1.84, 2.02), (-0.04, 2.04, 1.62), (-0.02, 2.02, 1.20), (0.06, 2.24, 0.80)],
                  [0.08, 0.13, 0.17, 0.17, 0.12], [0.07, 0.10, 0.12, 0.11, 0.08], wide=(1, 0, 0)), blue, TAIL)
    uni.add(shard([(0, 1.20, 1.96), (0.04, 1.52, 2.18), (0.08, 1.88, 2.22), (0.10, 2.14, 2.04), (0.14, 2.30, 1.74)],
                  [0.07, 0.11, 0.12, 0.08], [0.06, 0.08, 0.08, 0.06], wide=(1, 0, 0)), pink, TAIL)

    uni.build(SCALE)
    for ob in uni.objects:                                     # outward normals, then flat facets
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
        ob.data.update()
    return uni


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    a = ap.parse_args()
    kit.fresh()
    uni = build()
    tris = uni.triangles()
    lo, hi = uni.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    for ob in uni.objects:
        zs = [v.co.z for v in ob.data.vertices]
        print("  %-22s z %.3f to %.3f" % (ob.name, min(zs), max(zs)))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(uni.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        import review
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig = review.Rig(uni, focus=(-0.1 * SCALE, -1.0 * SCALE, 2.95 * SCALE))
        rig.sheet(os.path.abspath(a.review), review.STANDARD, px=a.px, title="Unicorn pet review (low-poly)")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
