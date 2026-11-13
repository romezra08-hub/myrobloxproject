"""Fox pet, built from scratch by script.

    python models/pets/fox.py --review out/fox.png      # render the review sheet
    python models/pets/fox.py --export models/export/fox.fbx

Style: chunky Roblox pet. Head more than half the height, pillow-shaped body, stubby legs,
big glossy eyes. Must-haves, checked in every review:
  1. Reads as a fox in outline: tall pointed ears with dark tips, big brush tail with a pale tip.
  2. Pale muzzle, cheeks and chest against orange fur; small dark nose.
  3. Big glossy eyes with a highlight; friendly.
  4. Dark socks; stands firmly on the ground.
  5. Not symmetrical: head tilted, one ear off, tail swung to one side.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402
from kit import M, Prop, ball, centre, cut, rounded_box, shear, split, taper, tube  # noqa: E402

SCALE = 0.8          # the whole pet, after building at a comfortable working size


def build():
    orange = kit.material("Orange", "#F0791A", rough=0.62)
    cream = kit.material("Cream", "#FFF1DC", rough=0.68)
    dark = kit.material("Dark", "#3B2217", rough=0.6)
    eye = kit.material("Eye", "#0A0A10", rough=0.06, coat=1.0)
    fox = Prop("Fox")

    # ---- body: low and wide, so the feet read as feet and not as pegs ---------------------------------
    body = taper(rounded_box((1.7, 1.95, 1.3), n=3.0, cuts=7), axis=1, lo=1.05, hi=0.9)
    fox.add(body, orange, M((0, 0.35, 0.86)))
    bib = taper(rounded_box((1.05, 0.55, 0.95), n=2.6, cuts=5), axis=2, lo=0.72, hi=1.0)
    fox.add(bib, cream, M((0, -0.55, 0.84), rot=(-8, 0, 0)))

    for sx in (-1, 1):
        for y, splay in ((-0.3, 9), (1.0, 5)):
            x = 0.52 * sx
            fox.add(tube([(0, 0, 0.3), (0, 0, 0.0), (0, 0, -0.25)], [0.33, 0.33, 0.32], segs=10, rings=2), orange, M((x, y, 0.42)))
            paw = taper(rounded_box((0.72, 0.9, 0.46), n=2.6, cuts=3), axis=2, lo=1.0, hi=0.82)
            fox.add(paw, dark, M((x, y - 0.13, 0.23), rot=(0, 0, -splay * sx)))

    # ---- tail: a big brush that curls up beside the body, so it shows from the front ----------------
    rings = 24
    tail = tube([(0, 1.15, 0.9), (0.4, 1.65, 0.92), (1.05, 1.85, 1.35), (1.6, 1.6, 2.1), (1.68, 1.15, 2.8), (1.5, 0.85, 3.15)],
                [0.24, 0.46, 0.66, 0.7, 0.42, 0.04], segs=14, rings=rings, zigzag=(0.6, 0.13))
    t = tail.faces.layers.float["t"]
    edge = kit.tube_ring(0.6, rings)
    tip, rest = split(tail, lambda f: f[t] > edge)
    fox.add(tip, cream)
    fox.add(rest, orange)

    # ---- head: everything here is placed around the head's own centre, then tilted as one ------------
    H = M((0, -0.52, 2.22), rot=(4, 5, -7))
    head = taper(rounded_box((2.5, 2.1, 2.0), n=3.4, cuts=10), axis=2, lo=0.9, hi=1.0)
    # pale mask: below two lines that run down and out from between the eyes, front of the head only
    z0, k = 0.2, 0.8
    cut(head, (0, 0, z0), (k, 0, 1))
    cut(head, (0, 0, z0), (-k, 0, 1))
    cut(head, (0, 0.35, 0), (0, 1, 0))
    mask, fur = split(head, lambda f: centre(f).z < z0 - k * abs(centre(f).x) and centre(f).y < 0.35)
    fox.add(mask, cream, H)
    fox.add(fur, orange, H)

    mz = (1.0, 0.82, 0.6)                                                                             # muzzle, sitting at MZ on the head
    MZ = (0, -1.05, -0.44)
    fox.add(rounded_box(mz, n=2.8, cuts=5), cream, H @ M(MZ))
    fox.add(ball((0.34, 0.24, 0.23), cuts=3), dark, H @ M((0, -1.45, -0.2)))                          # nose

    def on_muzzle(x, z, out=0.012):
        """The point on the muzzle's front surface at (x, z), a hair in front of it."""
        fx, fz = abs(x) / (mz[0] / 2), abs(z) / (mz[2] / 2)
        y = (mz[1] / 2) * max(0.0, 1 - fx ** 2.8 - fz ** 2.8) ** (1 / 2.8)
        return (MZ[0] + x, MZ[1] - y - out, MZ[2] + z)

    for sx in (-1, 1):                                                                               # a small smile, one curl each side
        smile = tube([on_muzzle(0.0, 0.0), on_muzzle(0.1 * sx, -0.1), on_muzzle(0.24 * sx, -0.12), on_muzzle(0.36 * sx, -0.03)],
                     [0.032, 0.036, 0.034, 0.012], segs=6, rings=9)
        fox.add(smile, dark, H)
    fox.add(tube([on_muzzle(0, 0.16), on_muzzle(0, 0.0)], [0.03, 0.032], segs=6, rings=2), dark, H)   # line from nose to mouth

    for sx in (-1, 1):
        fox.add(ball((0.52, 0.26, 0.68), cuts=4), eye, H @ M((0.6 * sx, -0.99, 0.12), rot=(0, -6 * sx, 0)))
        fox.add(ball((0.2, 0.1, 0.2), cuts=2), cream, H @ M((0.6 * sx - 0.09, -1.115, 0.3)))         # highlights, same side on both eyes
        fox.add(ball((0.09, 0.06, 0.09), cuts=2), cream, H @ M((0.6 * sx + 0.11, -1.1, -0.04)))

        # cheek fluff: three fat tufts a side, fanned downwards, flattened front to back
        for j, (z, length, tilt, fat) in enumerate(((-0.2, 0.74, 4, 0.34), (-0.48, 0.86, 28, 0.36), (-0.74, 0.62, 52, 0.3))):
            tuft = tube([(0, 0, 0), (length * 0.5, 0, 0.02), (length, 0, -0.06)], [fat, fat * 0.72, 0.02], segs=8, rings=5)
            fox.add(tuft, cream, H @ M((0.82 * sx, -0.4 + 0.07 * j, z), rot=(0, tilt if sx > 0 else 180 - tilt, 0), scale=(1, 0.6, 1)))

    # ears: the left one leans out further than the right
    for sx, lean, turn in ((1, 11, -8), (-1, -21, 12)):
        E = H @ M((0.8 * sx, 0.12, 1.32), rot=(-6, lean, turn))
        ear = shear(taper(rounded_box((1.02, 0.46, 1.36), n=3.0, cuts=5), axis=2, lo=1.0, hi=0.1), axis=2, along=0, amount=0.1 * sx)
        cut(ear, (0, 0, 0.24), (0, 0.0, 1))
        tipd, low = split(ear, lambda f: centre(f).z > 0.24)
        fox.add(tipd, dark, E)
        fox.add(low, orange, E)
        inner = shear(taper(rounded_box((0.62, 0.2, 0.86), n=3.0, cuts=3), axis=2, lo=1.0, hi=0.12), axis=2, along=0, amount=0.07 * sx)
        fox.add(inner, cream, E @ M((0, -0.17, -0.14)))

    fox.build(SCALE)
    return fox


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
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
        rig = review.Rig(fox, focus=(0, -0.9 * SCALE, 2.15 * SCALE))
        rig.sheet(os.path.abspath(a.review), review.STANDARD, px=a.px, title="Fox pet review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
