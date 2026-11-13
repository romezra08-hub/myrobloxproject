"""Fox pet, version 4: a sitting storybook fox. Built from scratch by script.

    python models/pets/fox_v4.py --review out/fox.png
    python models/pets/fox_v4.py --export models/export/fox.fbx

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
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402
from kit import M, Prop, ball, centre, cut, rounded_box, shear, split, taper, tube, tube_ring  # noqa: E402

SCALE = 0.85


def build():
    orange = kit.material("Orange", "#E9741C", rough=0.62)
    cream = kit.material("Cream", "#FFF0DA", rough=0.68)
    dark = kit.material("Dark", "#3A2218", rough=0.6)
    eye = kit.material("Eye", "#0B0B11", rough=0.08, coat=1.0)
    fox = Prop("Fox")

    # ---- sitting body: haunches on the ground, torso rising forward to the chest ---------------------
    fox.add(rounded_box((1.5, 1.5, 1.15), n=2.4, cuts=6), orange, M((0, 0.55, 0.6)))                      # hips
    fox.add(tube([(0, 0.55, 0.55), (0, 0.2, 1.05), (0, -0.2, 1.6), (0, -0.32, 2.0)], [0.6, 0.72, 0.6, 0.42], segs=14, rings=10), orange)
    bib = taper(ball((0.86, 0.42, 1.15), cuts=4), axis=2, lo=0.55, hi=1.0)
    fox.add(bib, cream, M((0, -0.5, 1.38), rot=(-17, 0, 0)))
    fox.add(tube([(0, -0.3, 1.85), (0, -0.4, 2.25)], [0.45, 0.4], segs=12, rings=2), orange)             # neck

    for sx in (-1, 1):
        # front legs: straight, with dark socks that end in a jagged fur line
        rings = 10
        leg = tube([(0.34 * sx, -0.42, 1.45), (0.36 * sx, -0.58, 0.8), (0.37 * sx, -0.64, 0.1)], [0.25, 0.2, 0.19], segs=10, rings=rings, zigzag=(0.5, 0.05))
        t = leg.faces.layers.float["t"]
        edge = tube_ring(0.5, rings)
        sock, upper = split(leg, lambda f: f[t] > edge)
        fox.add(sock, dark)
        fox.add(upper, orange)
        fox.add(rounded_box((0.44, 0.6, 0.26), n=2.5, cuts=3), dark, M((0.37 * sx, -0.75, 0.13), rot=(0, 0, -6 * sx)))
        # hind legs: a folded thigh and a long foot pointing forward
        fox.add(ball((0.66, 1.05, 0.95), cuts=4), orange, M((0.66 * sx, 0.42, 0.55), rot=(0, 0, 8 * sx)))
        fox.add(rounded_box((0.42, 0.78, 0.26), n=2.5, cuts=3), dark, M((0.76 * sx, -0.22, 0.13), rot=(0, 0, -10 * sx)))

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
    H = M((0, -0.5, 2.68), rot=(3, 6, 12))
    skull = taper(rounded_box((1.5, 1.4, 1.3), n=2.5, cuts=8), axis=2, lo=1.08, hi=0.92)
    z0, k = -0.02, 0.55                                    # pale cheeks: below two lines running down and out from between the eyes
    cut(skull, (0, 0, z0), (k, 0, 1))
    cut(skull, (0, 0, z0), (-k, 0, 1))
    cut(skull, (0, 0.2, 0), (0, 1, 0))
    mask, fur = split(skull, lambda f: centre(f).z < z0 - k * abs(centre(f).x) and centre(f).y < 0.2)
    fox.add(mask, cream, H)
    fox.add(fur, orange, H)

    snout = tube([(0, -0.45, -0.1), (0, -0.95, -0.2), (0, -1.32, -0.27)], [0.44, 0.3, 0.16], segs=16, rings=8)
    snout.normal_update()
    top, under = split(snout, lambda f: f.normal.z > 0.35)   # orange along the top, pale below
    fox.add(top, orange, H)
    fox.add(under, cream, H)
    fox.add(ball((0.24, 0.2, 0.18), cuts=3), dark, H @ M((0, -1.36, -0.22)))                               # nose

    for sx in (-1, 1):
        fox.add(ball((0.2, 0.12, 0.29), cuts=3), eye, H @ M((0.37 * sx, -0.62, 0.13), rot=(0, 10 * sx, 0)))
        fox.add(ball((0.075, 0.05, 0.075), cuts=2), cream, H @ M((0.37 * sx - 0.035, -0.685, 0.2)))
        # cheek ruff: a soft pad with two pointed tufts sweeping out, back and down
        fox.add(ball((0.5, 0.52, 0.56), cuts=4), cream, H @ M((0.47 * sx, -0.3, -0.3)))
        for z, length, tilt, fat in ((-0.2, 0.52, 10, 0.2), (-0.42, 0.44, 36, 0.17)):
            tuft = tube([(0, 0, 0), (length * 0.45 * sx, 0.03, 0), (length * 0.8 * sx, 0.1, -0.03), (length * sx, 0.17, -0.08)],
                        [fat, fat * 0.8, fat * 0.42, 0.012], segs=10, rings=9)
            fox.add(tuft, cream, H @ M((0.58 * sx, -0.26, z), rot=(0, tilt * sx, 0), scale=(1, 0.75, 1)))

    for sx, lean, turn in ((1, 10, -8), (-1, -17, 10)):       # ears: the left one leans out further
        E = H @ M((0.45 * sx, 0.08, 0.92), rot=(-5, lean, turn))
        ear = shear(taper(rounded_box((0.66, 0.3, 1.05), n=2.8, cuts=4), axis=2, lo=1.0, hi=0.1), axis=2, along=0, amount=0.06 * sx)
        cut(ear, (0, 0, 0.2), (0, 0, 1))
        tipd, low = split(ear, lambda f: centre(f).z > 0.2)
        fox.add(tipd, dark, E)
        fox.add(low, orange, E)
        inner = shear(taper(rounded_box((0.4, 0.14, 0.68), n=2.8, cuts=3), axis=2, lo=1.0, hi=0.12), axis=2, along=0, amount=0.04 * sx)
        fox.add(inner, cream, E @ M((0, -0.11, -0.12)))

    fox.build(SCALE)
    return fox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    a = ap.parse_args()
    kit.fresh()
    fox = build()
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
        rig = review.Rig(fox, focus=(0, -0.7 * SCALE, 2.6 * SCALE))
        quick = [("front 3/4", "full"), ("close-up", "full"), ("side", "full"), ("game distance", "full")]
        rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title="Fox pet review, v4")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
