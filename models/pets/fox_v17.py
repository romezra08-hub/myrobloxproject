"""Fox pet, version 17: a sitting storybook fox. Built from scratch by script.

    python models/pets/fox_v17.py --review out/fox.png
    python models/pets/fox_v17.py --export models/export/fox.fbx

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
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 0.85


def hit(bvh, x, z, out=0.0):
    """Where a ray from far in front meets a mesh at (x, z): the point, moved `out` off the surface,
    and the surface's normal there. Used to put face details exactly on the surface they sit on."""
    loc, normal, _, _ = bvh.ray_cast(Vector((x, -9.0, z)), Vector((0, 1, 0)))
    return loc + normal * out, normal


def build():
    orange = kit.material("Orange", "#E9741C", rough=0.62)
    cream = kit.material("Cream", "#FFF0DA", rough=0.68)
    dark = kit.material("Dark", "#3A2218", rough=0.6)
    eye = kit.material("Eye", "#0B0B11", rough=0.08, coat=1.0)
    deep = kit.material("OrangeDeep", "#D5661A", rough=0.66)     # baked into the same texture, so it costs no extra part
    # Round 17: the owner said the smooth flat colours look like cheap plastic, so the coat is now
    # short fur: fine streaks and mottling baked into the texture, a matte finish and a soft rim.
    for mat, strength, mottle, down in ((orange, 0.34, 0.14, 0.12), (deep, 0.34, 0.14, 0.12), (cream, 0.2, 0.08, 0.05), (dark, 0.3, 0.12, 0.0)):
        kit.furry(mat, strength=strength, mottle=mottle, shade_down=down)
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
    # Round 14. The owner found the fox's face creepy twice: first small black eyes on a long sharp
    # snout with a thin sideways smile and spiky fur, then very large sparkly eyes with brows, blush
    # and lumpy cheek fur. He accepted the plush puppy, so this face follows the puppy's recipe:
    # a round head, modest bead eyes set apart with one highlight each, a short clean muzzle, a
    # small glossy nose and a clear smile. One soft point of fur is left on each cheek.
    H = M((0, -0.5, 2.7), rot=(3, 6, 10))
    skull = taper(rounded_box((1.62, 1.44, 1.32), n=2.3, cuts=9), axis=2, lo=1.07, hi=0.93)
    # pale cheeks: below two lines that start under the muzzle and rise outwards, so that the white sweeps
    # from beside the muzzle up to the cheek points and they read as part of the cheek, not as stuck-on flaps
    z0, k = -0.44, 0.44
    cut(skull, (0, 0, z0), (k, 0, 1))
    cut(skull, (0, 0, z0), (-k, 0, 1))
    back = Vector((0, 1, 0.79))                            # the white ends along a line slanting back and down, not a straight drop
    cut(skull, (0, -0.22, 0), back)
    on_skull = BVHTree.FromBMesh(skull)
    mask, fur = split(skull, lambda f: centre(f).z < z0 + k * abs(centre(f).x) and centre(f).dot(back) < -0.22)
    fox.add(mask, cream, H)
    fox.add(fur, orange, H)

    mc = -0.25                                             # muzzle: short, a little narrower at the front, all pale
    muzzle = taper(rounded_box((0.72, 0.8, 0.5), n=2.5, cuts=5), axis=1, lo=0.74, hi=1.0)
    muzzle.transform(M((0, -0.74, mc)))
    on_muzzle = BVHTree.FromBMesh(muzzle)
    for sx in (-1, 1):                                     # the smile: each side dips and curls up, like the puppy's
        pts = [hit(on_muzzle, x * sx, mc + z, 0.012)[0] for x, z in ((0.0, -0.05), (0.07, -0.12), (0.15, -0.13), (0.22, -0.07))]
        fox.add(tube(pts, [0.02, 0.023, 0.023, 0.01], segs=6, rings=9), dark, H)
    fox.add(tube([hit(on_muzzle, 0, mc + 0.06, 0.012)[0], hit(on_muzzle, 0, mc - 0.05, 0.012)[0]], [0.018, 0.02], segs=6, rings=2), dark, H)
    fox.add(muzzle, cream, H)
    tip, _ = hit(on_muzzle, 0, mc + 0.13)
    fox.add(ball((0.25, 0.18, 0.18), cuts=3), eye, H @ M((tip.x, tip.y + 0.02, tip.z)))                    # glossy nose

    ex, ey, ez = 0.2, 0.15, 0.24                           # eyes: modest glossy beads, set apart

    def on_eye(u, w, lift=0.006):
        """A point on the front of an eye, in the eye's own frame (u across, w up)."""
        return (u, -(ey / 2) * math.sqrt(max(0.0, 1 - (2 * u / ex) ** 2 - (2 * w / ez) ** 2)) - lift, w)

    for sx in (-1, 1):
        p, n = hit(on_skull, 0.37 * sx, 0.12)
        yaw, pitch = math.degrees(math.atan2(n.x, -n.y)), math.degrees(math.atan2(n.z, math.hypot(n.x, n.y)))
        E = H @ M(p - n * 0.02, rot=(-pitch, 0, yaw))
        fox.add(ball((ex, ey, ez), cuts=3), eye, E)
        fox.add(ball((0.07, 0.05, 0.07), cuts=2), cream, E @ M(on_eye(-0.035, 0.05)))                      # one highlight, the same side on both

        tuft = tube([(0, 0, 0), (0.17 * sx, 0.02, -0.02), (0.32 * sx, 0.05, -0.08)], [0.26, 0.18, 0.03], segs=10, rings=8)   # one soft cheek point
        fox.add(tuft, cream, H @ M((0.6 * sx, -0.2, -0.36), rot=(0, 14 * sx, 0), scale=(1, 0.6, 1)))

    for sx, lean, turn in ((1, 10, -8), (-1, -17, 10)):       # ears: rounded tips; the left one leans out further
        E = H @ M((0.46 * sx, 0.06, 0.92), rot=(-5, lean, turn))
        ear = shear(taper(rounded_box((0.7, 0.32, 0.98), n=2.6, cuts=4), axis=2, lo=1.0, hi=0.24), axis=2, along=0, amount=0.06 * sx)
        cut(ear, (0, 0, 0.2), (0, 0, 1))
        tipd, low = split(ear, lambda f: centre(f).z > 0.2)
        fox.add(tipd, dark, E)
        fox.add(low, orange, E)
        inner = shear(taper(rounded_box((0.43, 0.14, 0.64), n=2.6, cuts=3), axis=2, lo=1.0, hi=0.26), axis=2, along=0, amount=0.04 * sx)
        fox.add(inner, cream, E @ M((0, -0.12, -0.12)))

    fox.build(SCALE)
    return fox


def bake(fox, texture):
    """Fur, cream and dark parts become one textured mesh with soft shading baked in; the glossy
    eyes stay a mesh of their own. Roblox gets two MeshParts."""
    eyes = [ob for ob in fox.objects if ob.name.endswith("_Eye")]
    body = kit.bake_texture([ob for ob in fox.objects if ob not in eyes], texture, name="Fox_Body", shade=0.5, soften=3, rough=0.95, sheen=0.5)
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
        rig = review.Rig(fox, focus=(0, -0.7 * SCALE, 2.62 * SCALE))
        quick = [("front 3/4", "full"), ("close-up", "full"), ("side", "full"), ("game distance", "full")]
        rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title="Fox pet review, v17")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
