"""Penguin pet in a carved, hand-painted wooden toy style, built from scratch by script.

    python models/pets/penguin.py --review out/penguin.png      # render the review sheet
    python models/pets/penguin.py --export models/export/penguin.fbx

Style: a small wooden toy penguin as a craftsman would carve and paint it. Must-haves, checked every review:
  1. Reads as a penguin in outline: an egg-shaped body, a rounded head, two flippers held slightly
     out, two flat feet, a short beak, a little tail.
  2. Toy proportions, NOT a simulator pet: the head is narrower than the body, never a cube.
  3. The surface is painted wood: long grain streaks show under every colour, the finish is matte,
     and there are carved touches (the groove where head meets body, three notches on each foot).
  4. A simple friendly face: modest glossy bead eyes set apart with one highlight each, a short
     rounded beak with a gentle smile line, rosy cheeks, nothing crowding the face.
  5. One accessory for character: a painted wooden bobble hat, worn a little to one side.

Painted panels (belly, face, cheeks) are thin patches pressed onto the surface by ray-casting, so
they follow the carved shape underneath.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, centre, cut, lumpy, rounded_box, split, taper, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402


# ---- placing things ON surfaces ---------------------------------------------------------------------

def tree_of(bm):
    bm.normal_update()
    return BVHTree.FromBMesh(bm)


def front_of(tree, x, z, out=0.0):
    """The point on the front (-Y side) of a shape at (x, z), pushed `out` off the surface, and the
    direction the surface faces there."""
    loc, nrm, _, _ = tree.ray_cast(Vector((x, -6.0, z)), Vector((0, 1, 0)))
    if loc is None:
        raise ValueError("nothing in front at (%.2f, %.2f)" % (x, z))
    return loc + nrm * out, nrm


def top_of(tree, x, y, out=0.0):
    """The point on the top of a shape above (x, y), pushed `out` off the surface."""
    loc, nrm, _, _ = tree.ray_cast(Vector((x, y, 6.0)), Vector((0, 0, -1)))
    if loc is None:
        raise ValueError("nothing under (%.2f, %.2f)" % (x, y))
    return loc + nrm * out


def aim(a, b):
    """A transform that stands a shape built along +Z on the point a, pointing at b, its +Y kept upmost."""
    a, b = Vector(a), Vector(b)
    return Matrix.Translation(a) @ (b - a).to_track_quat('Z', 'Y').to_matrix().to_4x4()


def oval(rx, rz, egg=0.0, dip=0.0, dip_w=0.4):
    """An outline for patch(): an ellipse, optionally fuller at the top (egg) or with a dip in the
    middle of its top edge (a heart-shaped face)."""
    def r(a):
        base = 1.0 / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / rz) ** 2)
        d = math.atan2(math.sin(a - math.pi / 2), math.cos(a - math.pi / 2))
        return base * (1 + egg * math.sin(a)) * (1 - dip * math.exp(-(d / dip_w) ** 2))
    return r


def patch(trees, at, facing, outline, lift=0.014, rings=3, segs=24, up=(0, 0, 1)):
    """A painted panel: the blob outline(angle) -> radius, pressed onto the nearest of `trees` from
    the direction `facing`, round the point `at`. It sits `lift` proud and its rim is tucked under."""
    f = Vector(facing).normalized()
    u = Vector(up).cross(f).normalized()
    v = f.cross(u).normalized()
    c = Vector(at)

    def on(x, y, h):
        best = None
        for t in trees:
            loc, nrm, _, dist = t.ray_cast(c + u * x + v * y + f * 6.0, -f)
            if loc is not None and (best is None or dist < best[2]):
                best = (loc, nrm, dist)
        if best is None:
            raise ValueError("nothing under (%.2f, %.2f)" % (x, y))
        return best[0] + best[1] * h

    bm = bmesh.new()
    fracs = [(i / rings, lift) for i in range(1, rings)] + [(0.94, lift), (1.0, -lift)]
    loops = [[bm.verts.new(on(0, 0, lift))]]
    for frac, h in fracs:
        loops.append([bm.verts.new(on(math.cos(a) * outline(a) * frac, math.sin(a) * outline(a) * frac, h))
                      for a in (2 * math.pi * j / segs for j in range(segs))])
    for lo, hi in zip(loops, loops[1:]):
        for j in range(segs):
            j1 = (j + 1) % segs
            if len(lo) == 1:
                bm.faces.new((lo[0], hi[j], hi[j1]))
            else:
                bm.faces.new((lo[j], lo[j1], hi[j1], hi[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((fc.normal for fc in bm.faces), Vector()).dot(f) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


# ---- the penguin ------------------------------------------------------------------------------------

def build():
    grain = dict(mottle=0.1, fine=14.0, length=16.0, shade_down=0.06)        # long streaks: wood grain under the paint
    navy = kit.furry(kit.material("Navy", "#27375A", rough=0.85), strength=0.32, **grain)
    cream = kit.furry(kit.material("Cream", "#F3E4C6", rough=0.85), strength=0.2, **grain)
    orange = kit.furry(kit.material("Orange", "#F08B2D", rough=0.85), strength=0.22, **grain)
    pink = kit.furry(kit.material("Pink", "#F0A0A4", rough=0.85), strength=0.16, **grain)
    red = kit.furry(kit.material("Hat", "#CC4A3F", rough=0.85), strength=0.22, **grain)
    eyes = kit.material("Eyes", "#141012", rough=0.08)
    pen = Prop("Penguin")

    # ---- body: an egg, fuller at the bottom, with a flat base to stand on -------------------------
    body = ball((2.2, 2.0, 2.3), cuts=7)
    taper(body, axis=2, lo=1.0, hi=0.7)
    lumpy(body, 0.015, 1.3, seed=2)
    body.transform(M((0, 0, 1.07)))
    for v in body.verts:
        v.co.z = max(v.co.z, 0.0)
    body_tree = tree_of(body)
    pen.add(patch([body_tree], (0, 0, 0.93), (0, -1, 0), oval(0.64, 0.73), lift=0.016, rings=5, segs=32), cream)   # the pale belly panel

    # ---- feet: flat and orange, toes out, three carved notches each --------------------------------
    for sx in (-1, 1):
        foot = rounded_box((0.6, 0.95, 0.2), n=3.0, cuts=5)
        taper(foot, axis=1, lo=1.0, hi=0.6)
        ft = tree_of(foot)
        F = M((0.4 * sx, -0.62, 0.1), rot=(0, 0, 14 * sx))
        for x in (-0.15, 0.0, 0.15):
            pts = [top_of(ft, x * k, y, 0.002) for y, k in ((-0.42, 1.0), (-0.33, 0.95), (-0.2, 0.85))]
            pen.add(tube(pts, [0.026, 0.022, 0.012], segs=5, rings=4), navy, F)
        pen.add(foot, orange, F)

    # ---- flippers: attached at the shoulder, tips held a little out from the body ------------------
    for sx in (-1, 1):
        wing = rounded_box((0.22, 0.66, 1.2), n=2.5, cuts=3)
        taper(wing, axis=2, lo=0.55, hi=1.0)
        pen.add(wing, navy, M((0.93 * sx, 0.04, 1.25), rot=(0, -28 * sx, 0)))

    # ---- tail: a small wedge at the back ------------------------------------------------------------
    tail = ball((0.5, 0.62, 0.26), cuts=3)
    taper(tail, axis=1, lo=1.0, hi=0.35)
    pen.add(tail, navy, M((0, 0.74, 0.3), rot=(18, 0, 0)))
    pen.add(body, navy)

    # ---- head: everything is placed round the head's own centre, then tilted as one ----------------
    H = M((0, -0.02, 2.24), rot=(-2, 3, -4))
    head = ball((1.5, 1.42, 1.36), cuts=7)
    head_tree = tree_of(head)
    face = patch([head_tree], (0, 0, -0.02), (0, -1, 0), oval(0.54, 0.36, dip=0.28, dip_w=0.42), lift=0.014, rings=4, segs=32)
    face_tree = tree_of(face)

    for sx in (-1, 1):
        ep, en = front_of(head_tree, 0.29 * sx, 0.05)                                                 # bead eyes
        eye = ball((0.19, 0.21, 0.13), cuts=3)
        eye.transform(aim(ep - en * 0.012, ep + en))
        shine = front_of(tree_of(eye), ep.x - 0.03, ep.z + 0.045)[0]
        pen.add(eye, eyes, H)
        pen.add(ball((0.056, 0.03, 0.056), cuts=1), cream, H @ M(shine + Vector((0, 0.004, 0))))
        ck = front_of(head_tree, 0.43 * sx, -0.17)[0]                                                 # rosy cheeks
        pen.add(patch([head_tree, face_tree], ck, (0.62 * sx, -1, -0.2), oval(0.1, 0.08), lift=0.012, rings=1, segs=14), pink, H)

    bp, _ = front_of(head_tree, 0.0, -0.15)                                                           # a short rounded beak
    beak = ball((0.46, 0.44, 0.26), cuts=3)
    taper(beak, axis=1, lo=0.5, hi=1.0)
    beak.transform(M((0, bp.y + 0.04, -0.15), rot=(-4, 0, 0)))
    bt = tree_of(beak)
    smile = [front_of(bt, x, -0.15 + dz, 0.004)[0] for x, dz in ((-0.12, 0.012), (-0.065, -0.018), (0.0, -0.03), (0.065, -0.018), (0.12, 0.012))]
    pen.add(tube(smile, [0.008, 0.013, 0.014, 0.013, 0.008], segs=5, rings=8), navy, H)
    pen.add(beak, orange, H)
    pen.add(face, cream, H)

    # ---- bobble hat: a cap, a rolled brim and a pom-pom, worn back and a little to one side --------
    T = H @ M((0, 0, 0), rot=(-8, 0, 5))
    dome = ball((1.58, 1.50, 1.46), cuts=5)
    cut(dome, (0, 0, 0.42), (0, 0, 1))
    cap, rest = split(dome, lambda f: centre(f).z > 0.42)
    rest.free()
    pen.add(cap, red, T)
    n = 16
    ring = [Vector((0.652 * math.cos(a), 0.62 * math.sin(a), 0.41)) for a in (math.pi / 2 + 2 * math.pi * i / n for i in range(n + 2))]
    pen.add(tube(ring, [0.115] * (n + 2), segs=8, rings=(n + 1) * 2), cream, T)
    pom = ball((0.42, 0.42, 0.4), cuts=3)
    lumpy(pom, 0.03, 6.0, seed=4)
    pen.add(pom, cream, T @ M((0.04, 0.05, 0.87)))

    pen.add(head, navy, H)
    pen.build()
    return pen


def bake(pen, texture, samples=48):
    """All the painted wood becomes one textured mesh with soft shading baked in. The glossy eyes
    stay a mesh of their own. Roblox gets two MeshParts."""
    gloss = [ob for ob in pen.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in pen.objects if ob not in gloss], texture, name="Penguin_Body", shade=0.5, soften=3, rough=0.85, sheen=0.15, samples=samples)
    pen.objects = [body] + gloss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--look", help="render only the close-up view to this PNG (a quick check)")
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "penguin_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    pen = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(pen, os.path.abspath(a.texture), samples=12 if a.quick else 48)
    tris = pen.triangles()
    lo, hi = pen.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(pen.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.look:
        import review
        rig = review.Rig(pen, samples=14 if a.quick else 40, focus=(0.0, -0.6, 2.15))
        if a.look:
            rig.render(os.path.abspath(a.look), "close-up", "full", a.px)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            shots = [("front 3/4", "full"), ("close-up", "full"), ("back 3/4", "full"), ("side", "full")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, title="Penguin (carved wood) review")
            print("review sheet", a.review)


if __name__ == "__main__":
    main()
