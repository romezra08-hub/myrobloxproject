"""Fox pet, a sitting storybook fox (round 13 of practice). Built from scratch by script.

    python models/pets/fox.py --review out/fox.png
    python models/pets/fox.py --export models/export/fox.fbx

Versions 1 and 2 were "pet simulator" style (cube head, tiny body); the owner asked for something
else. Style now: a storybook animal with real proportions, sitting upright with its tail curled
round its feet. Must-haves, checked in every review:
  1. Reads as a fox in outline: tall pointed ears, long tapered snout, brush tail with a pale tip.
  2. Head about a third of the height on a clear neck; pear-shaped sitting body.
  3. Friendly, not creepy: small dark eyes with a highlight, no bug eyes.
  4. Pale snout underside, cheeks, chest and tail tip; dark socks and ear tips.
  5. Not symmetrical: head turned and tilted, tail to one side.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402
from kit import M, Prop, ball, centre, cut, rounded_box, shear, split, taper, tube, tube_ring  # noqa: E402
from mathutils import Vector  # noqa: E402

SCALE = 0.85


def build():
    orange = kit.material("Orange", "#E9741C", rough=0.62)
    cream = kit.material("Cream", "#FFF0DA", rough=0.68)
    dark = kit.material("Dark", "#3A2218", rough=0.6)
    eye = kit.material("Eye", "#0B0B11", rough=0.08, coat=1.0)
    deep = kit.material("OrangeDeep", "#D5661A", rough=0.66)     # baked into the same texture, so it costs no extra part
    fox = Prop("Fox")

    # ---- sitting body: haunches on the ground, torso rising forward to the chest ---------------------
    def striped(bm, at=None):
        """Add a body part with a darker stripe down the middle of its back, cut cleanly into its own surface."""
        if at is not None:
            bm.transform(at)
        cut(bm, (0.3, 0, 0), (1, 0, 0))
        cut(bm, (-0.3, 0, 0), (1, 0, 0))
        bm.normal_update()
        stripe, rest = split(bm, lambda f: abs(centre(f).x) < 0.3 and f.normal.y > 0.25 and centre(f).z > 0.45)
        fox.add(stripe, deep)
        fox.add(rest, orange)

    striped(rounded_box((1.5, 1.5, 1.15), n=2.4, cuts=6), M((0, 0.55, 0.6)))                               # hips
    striped(tube([(0, 0.55, 0.55), (0, 0.2, 1.05), (0, -0.2, 1.6), (0, -0.32, 2.0)], [0.6, 0.72, 0.6, 0.42], segs=14, rings=10))
    # chest ruff: from under the chin down between the front legs, ending in fur points
    bib = taper(ball((1.02, 0.5, 1.4), cuts=5), axis=2, lo=0.5, hi=1.0)
    fox.add(bib, cream, M((0, -0.61, 1.5), rot=(10, 0, 0)))
    for x, z, length in ((-0.27, 1.04, 0.4), (0.02, 0.96, 0.52), (0.29, 1.06, 0.36)):
        fox.add(tube([(0, 0, 0), (0, -0.04, -length * 0.5), (0, -0.02, -length)], [0.19, 0.13, 0.012], segs=8, rings=7), cream,
                M((x, -0.62, z), rot=(0, x * 75, 0), scale=(1, 0.6, 1)))
    fox.add(tube([(0, -0.3, 1.85), (0, -0.4, 2.25)], [0.45, 0.4], segs=12, rings=2), orange)             # neck

    for sx in (-1, 1):
        # front legs: straight, with dark socks that end in a jagged fur line
        rings = 12
        leg = tube([(0.26 * sx, -0.18, 1.72), (0.36 * sx, -0.44, 1.38), (0.37 * sx, -0.58, 0.8), (0.37 * sx, -0.64, 0.1)],
                   [0.12, 0.33, 0.25, 0.22], segs=12, rings=rings, zigzag=(0.67, 0.05))
        t = leg.faces.layers.float["t"]
        edge = tube_ring(0.67, rings)
        sock, upper = split(leg, lambda f: f[t] > edge)
        fox.add(sock, dark)
        fox.add(upper, orange)
        fox.add(rounded_box((0.54, 0.68, 0.32), n=2.3, cuts=3), dark, M((0.37 * sx, -0.76, 0.16), rot=(0, 0, -6 * sx)))
        # hind legs: a folded thigh and a long foot pointing forward
        fox.add(ball((0.66, 1.05, 0.95), cuts=4), orange, M((0.66 * sx, 0.42, 0.55), rot=(0, 0, 8 * sx)))
        fox.add(rounded_box((0.48, 0.82, 0.32), n=2.3, cuts=3), dark, M((0.78 * sx, -0.2, 0.16), rot=(0, 0, -10 * sx)))

    # ---- tail: curled round the right side to rest in front of the feet ----------------------------------
    rings = 26
    tail = tube([(0, 1.2, 0.5), (0.75, 1.35, 0.5), (1.5, 0.75, 0.56), (1.62, -0.25, 0.58), (1.15, -0.95, 0.5), (0.55, -1.15, 0.42)],
                [0.3, 0.46, 0.58, 0.56, 0.36, 0.05], segs=14, rings=rings, zigzag=(0.68, 0.12))
    t = tail.faces.layers.float["t"]
    edge = tube_ring(0.68, rings)
    tip, rest = split(tail, lambda f: f[t] > edge)
    fox.add(tip, cream)
    fox.add(rest, orange)

    # ---- head: built round its own centre, then turned and tilted as one ---------------------------------
    # Round 12: the owner found the face creepy (small black eyes, long sharp snout, thin sideways
    # smile, spiky fur). The face now follows what reads as friendly: a bigger rounder head, big
    # round eyes set low with clear highlights, a short blunt snout, a centred smile, rosy cheeks.
    # Round 13: everything on the face is now placed on the surface it sits on, by calculation.
    H = M((0, -0.5, 2.74), rot=(3, 6, 12))
    hs, hn = (1.7, 1.5, 1.45), 2.3
    skull = taper(rounded_box(hs, n=hn, cuts=8), axis=2, lo=1.08, hi=0.92)
    z0, k = -0.08, 0.5                                     # pale cheeks: below two lines running down and out from between the eyes
    cut(skull, (0, 0, z0), (k, 0, 1))
    cut(skull, (0, 0, z0), (-k, 0, 1))
    cut(skull, (0, 0.2, 0), (0, 1, 0))
    mask, fur = split(skull, lambda f: centre(f).z < z0 - k * abs(centre(f).x) and centre(f).y < 0.2)
    fox.add(mask, cream, H)
    fox.add(fur, orange, H)

    def on_face(x, z, out=0.0):
        """The point on the front of the head at (x, z), moved `out` along the surface's normal,
        with the normal's direction as (yaw, pitch) in degrees for laying things flat on it."""
        s = 1.08 - 0.16 * (z + hs[2] / 2) / hs[2]
        A, B, C = hs[0] / 2 * s, hs[1] / 2 * s, hs[2] / 2
        fx, fz = abs(x) / A, abs(z) / C
        fy = max(0.0, 1 - fx ** hn - fz ** hn) ** (1 / hn)
        gx, gy, gz = math.copysign(fx ** (hn - 1) / A, x), fy ** (hn - 1) / B, math.copysign(fz ** (hn - 1) / C, z)
        g = math.sqrt(gx * gx + gy * gy + gz * gz)
        point = (x + out * gx / g, -B * fy - out * gy / g, z + out * gz / g)
        return point, math.degrees(math.atan2(gx, gy)), math.degrees(math.atan2(gz, math.hypot(gx, gy)))

    # snout: short, with a rounded tip; an orange strip along the top, cut cleanly along two planes through its axis
    sn, sn_r = [(0, -0.5, -0.17), (0, -0.92, -0.23), (0, -1.1, -0.255), (0, -1.17, -0.262)], [0.43, 0.32, 0.22, 0.11]
    snout = tube(sn, sn_r, segs=16, rings=9)
    axis = (Vector(sn[-1]) - Vector(sn[0])).normalized()
    up = Vector((0, 0, 1))
    up = (up - axis * up.dot(axis)).normalized()
    side, half = Vector((1, 0, 0)), math.radians(40)
    m1, m2 = up * math.sin(half) - side * math.cos(half), up * math.sin(half) + side * math.cos(half)
    P0 = Vector(sn[0])
    cut(snout, P0, m1)
    cut(snout, P0, m2)
    top, under = split(snout, lambda f: (centre(f) - P0).dot(m1) > 1e-4 and (centre(f) - P0).dot(m2) > 1e-4)
    fox.add(top, orange, H)
    fox.add(under, cream, H)
    fox.add(ball((0.26, 0.2, 0.19), cuts=3), dark, H @ M((0, -1.22, -0.2)))                                # nose

    def on_snout(t, phi, out=0.004):
        """A point on the snout: t along it (0 at the head, 1 at the tip), phi degrees round from straight down."""
        tt = t * (len(sn) - 1)
        c, rad = kit._spline([Vector(q) for q in sn], tt), kit._spline(sn_r, tt)
        a = math.radians(phi)
        return c + (side * math.sin(a) - up * math.cos(a)) * (rad + out)

    front = Vector(sn[-1]) + Vector((0, -0.018, -0.07))      # just under the nose
    for sx in (-1, 1):                                       # a small centred smile: each side dips, then curls up
        smile = tube([front, on_snout(0.93, 22 * sx), on_snout(0.8, 48 * sx), on_snout(0.62, 75 * sx)],
                     [0.02, 0.024, 0.024, 0.009], segs=6, rings=9)
        fox.add(smile, dark, H)

    blush = kit.material("Blush", "#F3A39B", rough=0.7)
    ex, ey, ez = 0.34, 0.17, 0.42                            # eyes: big, round, set low

    def on_eye(u, w, lift=0.006):
        """A point on the front of an eye, in the eye's own frame (u across, w up)."""
        return (u, -(ey / 2) * math.sqrt(max(0.0, 1 - (2 * u / ex) ** 2 - (2 * w / ez) ** 2)) - lift, w)

    for sx in (-1, 1):
        p, yaw, pitch = on_face(0.43 * sx, 0.03, out=-0.03)                                                # the centre sits a little inside the head
        E = H @ M(p, rot=(-pitch, -5 * sx, yaw))
        fox.add(ball((ex, ey, ez), cuts=4), eye, E)
        fox.add(ball((0.12, 0.07, 0.12), cuts=2), cream, E @ M(on_eye(-0.05, 0.085)))                      # highlights, on the eye's own surface,
        fox.add(ball((0.055, 0.04, 0.055), cuts=2), cream, E @ M(on_eye(0.06, -0.09)))                     # the same side on both eyes
        p, yaw, pitch = on_face(0.43 * sx, 0.37)                                                           # soft brows, raised in the middle
        fox.add(ball((0.2, 0.07, 0.06), cuts=2), deep, H @ M(p, rot=(-pitch, 10 * sx, yaw)))
        p, yaw, pitch = on_face(0.6 * sx, -0.22)                                                           # rosy cheeks
        fox.add(ball((0.26, 0.05, 0.15), cuts=2), blush, H @ M(p, rot=(-pitch, 0, yaw)))

        # cheek fluff: a soft pad and two short rounded tufts, no spikes
        fox.add(ball((0.56, 0.56, 0.6), cuts=4), cream, H @ M((0.55 * sx, -0.26, -0.36)))
        for z, length, tilt, fat in ((-0.26, 0.36, 8, 0.2), (-0.48, 0.3, 34, 0.17)):
            tuft = tube([(0, 0, 0), (length * 0.5 * sx, 0.03, 0), (length * 0.85 * sx, 0.08, -0.02), (length * sx, 0.11, -0.04)],
                        [fat, fat * 0.85, fat * 0.55, 0.035], segs=10, rings=9)
            fox.add(tuft, cream, H @ M((0.68 * sx, -0.24, z), rot=(0, tilt * sx, 0), scale=(1, 0.75, 1)))

    for x, y, length, lean in ((-0.07, -0.1, 0.34, -16), (0.1, 0.05, 0.27, 12)):   # two tufts on the crown, between the ears
        tuft = tube([(0, 0, 0), (0, -0.06, length * 0.55), (0, -0.16, length)], [0.15, 0.11, 0.03], segs=8, rings=7)
        fox.add(tuft, deep, H @ M((x, y, 0.66), rot=(0, lean, 0)))

    for sx, lean, turn in ((1, 10, -8), (-1, -17, 10)):       # ears: rounder tips; the left one leans out further
        E = H @ M((0.5 * sx, 0.08, 1.0), rot=(-5, lean, turn))
        ear = shear(taper(rounded_box((0.72, 0.32, 1.0), n=2.6, cuts=4), axis=2, lo=1.0, hi=0.24), axis=2, along=0, amount=0.06 * sx)
        cut(ear, (0, 0, 0.2), (0, 0, 1))
        tipd, low = split(ear, lambda f: centre(f).z > 0.2)
        fox.add(tipd, dark, E)
        fox.add(low, orange, E)
        inner = shear(taper(rounded_box((0.44, 0.14, 0.66), n=2.6, cuts=3), axis=2, lo=1.0, hi=0.26), axis=2, along=0, amount=0.04 * sx)
        fox.add(inner, cream, E @ M((0, -0.12, -0.12)))

    fox.build(SCALE)
    return fox


def bake(fox, texture):
    """Fur, cream and dark parts become one textured mesh with soft shading baked in; the glossy
    eyes stay a mesh of their own. Roblox gets two MeshParts."""
    eyes = [ob for ob in fox.objects if ob.name.endswith("_Eye")]
    body = kit.bake_texture([ob for ob in fox.objects if ob not in eyes], texture, name="Fox_Body", shade=0.5, soften=3)
    fox.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "fox_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    fox = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(fox, os.path.abspath(a.texture))
    tris = fox.triangles()
    lo, hi = fox.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(fox.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        import review
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig = review.Rig(fox, focus=(0, -0.7 * SCALE, 2.68 * SCALE))
        quick = [("front 3/4", "full"), ("close-up", "full"), ("side", "full"), ("game distance", "full")]
        rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title="Fox pet review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
