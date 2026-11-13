"""Cat pet, a needle-felted tabby (5 rounds of practice). Built from scratch by script.

    python models/pets/cat.py --review out/cat.png
    python models/pets/cat.py --export models/export/cat.fbx

Style: a handmade needle-felted wool figure of a grey tabby, sitting upright with its tail raised in
a question mark. Soft, slightly uneven wool forms with a fuzzy matte surface. Must-haves, checked in
every review:
  1. Reads as a cat in outline, not a fox or a dog: short wide triangular ears on the corners of a
     round head, a face with almost no snout, a slim tail held up with a hooked tip.
  2. Head a bit over a third of the height, on a short neck with a collar; pear-shaped sitting body.
  3. Friendly, not creepy: modest round bead eyes set apart with one highlight each, a small pink
     nose on a clean pale muzzle, a gentle "w" mouth, whisker dots. No slit pupils, no brows.
  4. Tabby: the "M" on the forehead, stripes over the back and the thighs, bars on the legs, rings
     on the tail; pale chest and muzzle, white socks, pink inside the ears.
  5. Felted wool, not plastic: fuzzy matte surface, uneven handmade forms, a few soft tufts.
  6. Not symmetrical: head turned and tilted, tail to one side, one ear leaning further.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, centre, cut, rounded_box, shear, split, taper, tube, tube_ring  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 0.84


# ---- helpers that the kit does not have ------------------------------------------------------------

def spline(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def hit(bvh, x, z, out=0.0):
    """Where a ray from far in front meets a mesh at (x, z): the point, moved `out` off the surface,
    and the surface's normal there. Used to put face details exactly on the surface they sit on."""
    loc, normal, _, _ = bvh.ray_cast(Vector((x, -9.0, z)), Vector((0, 1, 0)))
    return loc + normal * out, normal


def press(bvh, p, d, out=0.0):
    """Where a ray coming in along -d towards the point p meets a mesh, and the normal there."""
    d = Vector(d).normalized()
    loc, normal, _, _ = bvh.ray_cast(Vector(p) + d * 6.0, -d)
    if normal.dot(d) < 0:
        normal = -normal
    return loc + normal * out, normal


def bumpy(bm, amount=0.02, freq=1.5, seed=0.0):
    """Like kit.lumpy, but along each point's own normal, for shapes that are not built round the origin."""
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * freq + off) * amount
    return bm


def grounded(bm, at):
    """Move a shape into place and flatten whatever would go below the floor, like a beanbag."""
    bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def by_t(bm, pred):
    """Split a kit.tube by how far along it each face is (0 to 1). Uses up `bm`."""
    t = bm.faces.layers.float["t"]
    return split(bm, lambda f: pred(f[t]))


def strip(bvh, samples, widths, lift=0.02, tuck=0.014, across=5):
    """A strip of darker felt laid on a surface: a little proud of it, its edges tucked just under.

    samples: (point, direction) pairs along the strip; the middle of the strip is where a ray coming
    in along -direction towards the point meets the surface. widths: half the width at each sample.
    Every point of the strip is then found by a ray of its own, so it follows the surface under it."""
    mids = []
    for (p, d), w in zip(samples, widths):
        d = Vector(d).normalized()
        loc, nrm, _, _ = bvh.ray_cast(Vector(p) + d * 6.0, -d)
        if loc is None:
            continue
        mids.append((loc, nrm if nrm.dot(d) > 0 else -nrm, w))
    bm = bmesh.new()
    rows, tans, n = [], [], len(mids)
    for i, (loc, nrm, w) in enumerate(mids):
        t = (mids[min(i + 1, n - 1)][0] - mids[max(i - 1, 0)][0]).normalized()
        side = t.cross(nrm).normalized()
        row = []
        for j in range(across):
            a = math.pi * j / (across - 1)
            q = loc + side * (w * math.cos(a))
            h = lift * math.sin(a) if 0 < j < across - 1 else -tuck
            at, hn, _, _ = bvh.ray_cast(q + nrm * 0.35, -nrm)
            if at is None:
                at, hn = q, nrm
            elif hn.dot(nrm) < 0:
                hn = -hn
            row.append(bm.verts.new(at + hn * h))
        rows.append(row)
        tans.append(t)
    for a, b in zip(rows, rows[1:]):
        for j in range(across - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    for k, sign in ((0, -1.0), (n - 1, 1.0)):                     # close each end with a small point
        loc, nrm, w = mids[k]
        end = bm.verts.new(loc + tans[k] * sign * max(w, 0.02) - nrm * tuck)
        for j in range(across - 1):
            bm.faces.new((end, rows[k][j], rows[k][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(sum((m[1] for m in mids), Vector())) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def tuft(base, to, length, width, bend=(0, 0, 0), segs=6):
    """A soft, blunt lock of wool: from `base` (it starts a little inside the surface) towards `to`."""
    d, base, bend = Vector(to).normalized(), Vector(base), Vector(bend)
    return tube([base - d * width * 0.7, base + d * length * 0.45 + bend * 0.4, base + d * length * 0.85 + bend * 0.9, base + d * length + bend],
                [width, width * 0.86, width * 0.5, width * 0.16], segs=segs, rings=6)


def point(base, to, length, width, segs=7):
    """A short lock of wool that ends in one soft point."""
    d, base = Vector(to).normalized(), Vector(base)
    return tube([base - d * width * 0.7, base + d * length * 0.5, base + d * length], [width, width * 0.66, 0.015], segs=segs, rings=5)


def _super(a, n):
    """A point on a unit superellipse (n=2 is a circle, larger is squarer)."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


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


def toe_lines(paw, mid, yaw, offsets=(-0.085, 0.085)):
    """Two pulled-in toe lines over the front of a paw (a mesh already in place, turned `yaw` degrees)."""
    bvh = BVHTree.FromBMesh(paw)
    a = math.radians(yaw)
    fwd, side, upv = Vector((math.sin(a), -math.cos(a), 0)), Vector((math.cos(a), math.sin(a), 0)), Vector((0, 0, 1))
    lines = []
    for off in offsets:
        pts = []
        for phi in (72, 42, 14, -10):
            d = fwd * math.cos(math.radians(phi)) + upv * math.sin(math.radians(phi))
            o = Vector(mid) + fwd * 0.1 + side * off
            loc = bvh.ray_cast(o + d * 3.0, -d)[0]
            pts.append(loc + d * 0.008)
        lines.append(tube(pts, [0.008, 0.017, 0.017, 0.008], segs=4, rings=3))
    return lines


def felted(mat, fibre=0.18, grain=0.1):
    """On top of kit.furry(): the tangled fibres of needle-felted wool. Thin pale and dark strands
    that wander in every direction, and a fine grain. Worked out in 3D space, baked into the texture."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    src = hsv.inputs["Value"].links[0].from_socket
    coord = next(n for n in tree.nodes if n.type == 'TEX_COORD')

    def strands(turn, distortion, detail_scale):
        mp = new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = turn
        link(coord.outputs["Object"], mp.inputs["Vector"])
        w = new("ShaderNodeTexWave")
        w.wave_type, w.bands_direction, w.wave_profile = 'BANDS', 'X', 'SIN'
        w.inputs["Scale"].default_value = 1.0
        w.inputs["Distortion"].default_value = distortion
        w.inputs["Detail"].default_value = 2.0
        w.inputs["Detail Scale"].default_value = detail_scale
        link(mp.outputs["Vector"], w.inputs["Vector"])
        thin = new("ShaderNodeMapRange")
        thin.interpolation_type = 'SMOOTHSTEP'
        thin.inputs["From Min"].default_value, thin.inputs["From Max"].default_value = 0.7, 1.0
        link(w.outputs[0], thin.inputs["Value"])
        return thin.outputs["Result"]

    def mul_add(a, k, c):
        m = new("ShaderNodeMath")
        m.operation = 'MULTIPLY_ADD'
        link(a, m.inputs[0])
        m.inputs[1].default_value = k
        if isinstance(c, (int, float)):
            m.inputs[2].default_value = c
        else:
            link(c, m.inputs[2])
        return m.outputs[0]

    v = mul_add(strands((0.3, 0.5, 0.2), 54.0, 2.6), fibre, 1.0 - grain)
    v = mul_add(strands((1.1, -0.4, 0.9), 46.0, 3.3), -0.6 * fibre, v)
    speck = new("ShaderNodeTexNoise")
    speck.inputs["Scale"].default_value, speck.inputs["Detail"].default_value = 95.0, 2.0
    link(coord.outputs["Object"], speck.inputs["Vector"])
    v = mul_add(speck.outputs[0], 2 * grain, v)
    out = new("ShaderNodeMath")
    out.operation = 'MULTIPLY'
    link(src, out.inputs[0])
    link(v, out.inputs[1])
    link(out.outputs[0], hsv.inputs["Value"])
    return mat


def copy_into(shell, bm):
    """Add a copy of the shape `bm` to the mesh `shell`, which stripes are later laid on."""
    tmp = bpy.data.meshes.new("tmp")
    bm.to_mesh(tmp)
    shell.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


# ---- the cat ---------------------------------------------------------------------------------------

def build():
    grey = kit.material("Grey", "#A69B8E", rough=0.9)
    dark = kit.material("Dark", "#4E443D", rough=0.9)
    cream = kit.material("Cream", "#F8EFE0", rough=0.9)
    pink = kit.material("Pink", "#EAA6A4", rough=0.9)
    teal = kit.material("Collar", "#2A9D8F", rough=0.85)
    gold = kit.material("Bell", "#F0BE4A", rough=0.45)
    gloss = kit.material("Gloss", "#0C0B10", rough=0.08, coat=1.0)
    # Felted wool: a short, matted fibre (low `length`), baked into the texture with a matte finish.
    for mat, strength, mottle in ((grey, 0.3, 0.14), (dark, 0.28, 0.12), (cream, 0.2, 0.08), (pink, 0.2, 0.08), (teal, 0.22, 0.1)):
        kit.furry(mat, strength=strength, mottle=mottle, fine=30.0, length=1.6, shade_down=0.08)
        felted(mat, fibre=0.2 if mat in (grey, dark) else 0.13, grain=0.13 if mat in (grey, dark) else 0.09)
    cat = Prop("Cat")
    rnd = random.Random(11)

    # ---- sitting body: haunches on the ground, torso rising forward to the chest ---------------------
    shell = bmesh.new()                                         # hips, torso, neck: what the back stripes lie on
    hips = grounded(kit.lumpy(rounded_box((1.56, 1.5, 1.2), n=2.4, cuts=6), 0.035, 1.3, seed=1.0), M((0, 0.5, 0.6)))
    torso = bumpy(tube([(0, 0.5, 0.55), (0, 0.22, 1.02), (0, -0.1, 1.5), (0, -0.24, 1.95)], [0.62, 0.74, 0.62, 0.44], segs=14, rings=10), 0.03, 1.4, seed=2.0)
    neck = tube([(0, -0.1, 1.5), (0, -0.25, 1.9), (0, -0.36, 2.3)], [0.42, 0.45, 0.42], segs=12, rings=4)
    for part in (hips, torso, neck):
        copy_into(shell, part)
        cat.add(part, grey)
    on_body = BVHTree.FromBMesh(shell)

    def axis_y(z):
        """How far back the torso's centre line is at height z."""
        pts = ((0.55, 0.5), (1.02, 0.22), (1.5, -0.1), (1.95, -0.24))
        for (z0, y0), (z1, y1) in zip(pts, pts[1:]):
            if z <= z1:
                return y0 + (y1 - y0) * max(0.0, (z - z0) / (z1 - z0))
        return pts[-1][1]

    # tabby stripes over the back: each runs from one flank over the spine to the other, drooping at its ends
    for z0, reach, droop, wide in ((1.7, 72, 0.24, 0.055), (1.42, 78, 0.27, 0.07), (1.13, 70, 0.2, 0.07), (0.84, 40, 0.07, 0.06)):
        n = 13 if reach > 50 else 7
        tilt = rnd.uniform(-0.05, 0.05)
        samples, ws = [], []
        for i in range(n):
            f = -1 + 2 * i / (n - 1)
            phi = math.radians(reach * f)
            z = z0 - droop * abs(f) ** 1.4 + tilt * f
            samples.append((Vector((0, axis_y(z), z)), Vector((math.sin(phi), math.cos(phi), 0.15))))
            ws.append(0.012 + wide * (1 - abs(f) ** 2))
        cat.add(strip(on_body, samples, ws), dark)

    # pale chest: a soft bib from under the collar down between the front legs, with a few wool tufts
    bib = kit.lumpy(taper(ball((0.98, 0.5, 1.08), cuts=5), axis=2, lo=0.6, hi=1.0), 0.025, 1.6, seed=6.0)
    bib.transform(M((0, -0.55, 1.27), rot=(10, 0, 0)))
    on_bib = BVHTree.FromBMesh(bib)
    for x, z, length in ((0.01, 0.95, 0.17),):       # one soft point ends the bib: three long ones read as tusks, three small ones as teeth
        p, _ = hit(on_bib, x, z)
        cat.add(point(p, (x * 0.4, -0.1, -1), length + 0.04, 0.125, segs=8), cream)
    cat.add(bib, cream)

    for sx in (-1, 1):
        # front legs: straight and close together, two dark bars, then a white sock
        rings = 12
        leg = tube([(0.24 * sx, -0.16, 1.7), (0.33 * sx, -0.42, 1.36), (0.35 * sx, -0.56, 0.78), (0.35 * sx, -0.62, 0.1)],
                   [0.12, 0.3, 0.24, 0.22], segs=12, rings=rings, zigzag=(10 / 12, 0.03))
        edge = tube_ring(10 / 12, rings)
        sock, upper = by_t(leg, lambda v: v > edge)
        bars, upper = by_t(upper, lambda v: 0.5 < v < 0.58 or 0.67 < v < 0.75)
        cat.add(sock, cream)
        cat.add(bars, dark)
        cat.add(upper, grey)
        paw = grounded(rounded_box((0.52, 0.66, 0.34), n=2.4, cuts=3), M((0.35 * sx, -0.74, 0.16), rot=(0, 0, 5 * sx)))
        for line in toe_lines(paw, (0.35 * sx, -0.74, 0.13), 5 * sx):
            cat.add(line, grey)
        cat.add(paw, cream)

        # hind legs: a folded thigh with stripes round it, and a long white foot pointing forward
        T = M((0.68 * sx, 0.42, 0.52), rot=(0, 0, 8 * sx))
        thigh = grounded(kit.lumpy(ball((0.7, 1.08, 0.98), cuts=4), 0.03, 1.5, seed=4.0 + sx), T)
        on_thigh = BVHTree.FromBMesh(thigh)
        for y0, a0, a1 in ((0.3, 22, 122), (0.03, 26, 126), (-0.25, 36, 122)):
            samples, ws = [], []
            for i in range(9):
                f = i / 8
                a = math.radians(a0 + (a1 - a0) * f)
                samples.append((T @ Vector((0, y0 - 0.1 * f, 0)), T.to_3x3() @ Vector((sx * math.sin(a), 0, math.cos(a)))))
                ws.append(0.01 + 0.032 * math.sin(math.pi * f))
            cat.add(strip(on_thigh, samples, ws), dark)
        cat.add(thigh, grey)
        foot = grounded(rounded_box((0.46, 0.8, 0.32), n=2.4, cuts=3), M((0.8 * sx, -0.24, 0.15), rot=(0, 0, 8 * sx)))
        for line in toe_lines(foot, (0.8 * sx, -0.4, 0.12), 8 * sx, offsets=(-0.075, 0.075)):
            cat.add(line, grey)
        cat.add(foot, cream)

    # ---- tail: held up beside the body, the tip hooked over like a question mark ----------------------
    rings = 32
    tail_pts = [(-0.12, 1.0, 0.42), (-0.6, 1.42, 0.42), (-1.12, 1.5, 0.9), (-1.3, 1.4, 1.6), (-1.3, 1.3, 2.25),
                (-1.42, 1.25, 2.72), (-1.72, 1.22, 2.92), (-2.0, 1.2, 2.72), (-1.98, 1.2, 2.42)]
    tail = bumpy(tube(tail_pts, [0.17, 0.175, 0.165, 0.155, 0.15, 0.145, 0.14, 0.15, 0.085], segs=12, rings=rings), 0.015, 2.0, seed=5.0)
    ringed, plain = by_t(tail, lambda v: (int(v * rings) - 3) % 5 < 2 or v > 0.9)
    cat.add(ringed, dark)
    cat.add(plain, grey)
    end, before = Vector(tail_pts[-1]), Vector(tail_pts[-2])
    cat.add(tuft(end, end - before, 0.13, 0.075), dark)

    # ---- collar with a little bell --------------------------------------------------------------------
    C = M((0, -0.27, 1.95), rot=(16, 0, 0))
    cat.add(band(0.47, 0.045, 0.09, segs=24, ring=6, n=4.0), teal, C)
    B = C @ Vector((0, -0.6, -0.12))
    cat.add(ball((0.22, 0.22, 0.22), cuts=2), gold, M(B))
    cat.add(rounded_box((0.15, 0.06, 0.035), n=3.0, cuts=0), dark, M(B + Vector((0, -0.075, -0.07)), rot=(45, 0, 0)))

    # ---- head: built round its own centre, then turned and tilted as one ---------------------------------
    # The face follows the recipe of the plush puppy, which the owner accepted: a round head, modest
    # bead eyes set apart with one highlight each, a clean pale muzzle, a small nose and a clear smile.
    H = M((0, -0.4, 2.62), rot=(-3, 6, -8))
    skull = kit.lumpy(taper(rounded_box((1.72, 1.46, 1.36), n=2.3, cuts=9), axis=2, lo=1.08, hi=0.92), 0.03, 1.5, seed=3.0)
    on_skull = BVHTree.FromBMesh(skull)
    cat.add(skull, grey, H)                                # round 1 forgot this line: the face hung in the air
    O = Vector((0, 0, 0))

    def head_strip(points, widths, across=4, per=3):
        """A felt stripe on the skull through rough points in head space, pressed on from straight outside."""
        pts, n = [Vector(p) for p in points], (len(points) - 1) * per + 1
        us = [i / (n - 1) * (len(pts) - 1) for i in range(n)]
        return strip(on_skull, [(O, spline(pts, u)) for u in us], [spline(list(widths), u) for u in us], lift=0.018, across=across)

    def face(x, z):
        return hit(on_skull, x, z)[0]

    for sx in (-1, 1):
        # the tabby "M": each half runs up from above the eye, over a peak and down to the middle
        half = [face(0.31 * sx, 0.34), face(0.3 * sx, 0.47), face(0.2 * sx, 0.58), face(0.09 * sx, 0.5), face(0.0, 0.41)]
        cat.add(head_strip(half, [0.02, 0.04, 0.044, 0.04, 0.028]), dark, H)
        # two short stripes on each cheek, sweeping back from beyond the eye
        cat.add(head_strip([(0.6 * sx, -0.5, 0.04), (0.76 * sx, -0.3, -0.03), (0.85 * sx, -0.05, -0.12)], [0.014, 0.04, 0.014]), dark, H)
        cat.add(head_strip([(0.58 * sx, -0.5, -0.15), (0.74 * sx, -0.3, -0.22), (0.8 * sx, -0.08, -0.32)], [0.014, 0.036, 0.014]), dark, H)
        # and a stripe down the back of the head behind each ear
        cat.add(head_strip([(0.3 * sx, 0.32, 0.56), (0.31 * sx, 0.52, 0.4), (0.28 * sx, 0.66, 0.12)], [0.02, 0.05, 0.02]), dark, H)
    cat.add(head_strip([(0, -0.2, 0.68), (0, 0.05, 0.69), (0, 0.3, 0.62), (0, 0.55, 0.42), (0, 0.68, 0.1)], [0.02, 0.045, 0.055, 0.05, 0.02]), dark, H)

    mc = -0.24                                             # muzzle: short and wide, a cat has almost no snout
    muzzle = kit.lumpy(taper(rounded_box((0.66, 0.5, 0.42), n=2.5, cuts=4), axis=1, lo=0.8, hi=1.0), 0.01, 2.0, seed=7.0)
    muzzle.transform(M((0, -0.65, mc)))
    on_muzzle = BVHTree.FromBMesh(muzzle)
    for sx in (-1, 1):                                     # the smile: each side dips and curls up, like the puppy's
        pts = [hit(on_muzzle, x * sx, mc + z, 0.012)[0] for x, z in ((0.0, -0.03), (0.06, -0.1), (0.13, -0.11), (0.19, -0.06))]
        cat.add(tube(pts, [0.018, 0.021, 0.021, 0.009], segs=5, rings=6), dark, H)
        for x, z in ((0.15, 0.06), (0.23, 0.03), (0.19, -0.015)):                                         # whisker dots
            d, _ = hit(on_muzzle, x * sx, mc + z)
            cat.add(ball((0.04, 0.03, 0.04), cuts=0), dark, H @ M(d))
    cat.add(tube([hit(on_muzzle, 0, mc + 0.07, 0.012)[0], hit(on_muzzle, 0, mc - 0.03, 0.012)[0]], [0.016, 0.018], segs=5, rings=2), dark, H)
    tip, _ = hit(on_muzzle, 0, mc + 0.12)
    cat.add(taper(ball((0.18, 0.12, 0.13), cuts=2), axis=2, lo=0.4, hi=1.0), pink, H @ M((tip.x, tip.y + 0.03, tip.z)))   # felt nose
    cat.add(muzzle, cream, H)

    ex, ey, ez = 0.21, 0.15, 0.23                          # eyes: modest glossy beads, set apart

    def on_eye(u, w, lift=0.006):
        """A point on the front of an eye, in the eye's own frame (u across, w up)."""
        return (u, -(ey / 2) * math.sqrt(max(0.0, 1 - (2 * u / ex) ** 2 - (2 * w / ez) ** 2)) - lift, w)

    for sx in (-1, 1):
        p, n = hit(on_skull, 0.38 * sx, 0.06)
        yaw, pitch = math.degrees(math.atan2(n.x, -n.y)), math.degrees(math.atan2(n.z, math.hypot(n.x, n.y)))
        E = H @ M(p - n * 0.02, rot=(-pitch, 0, yaw))
        cat.add(ball((ex, ey, ez), cuts=3), gloss, E)
        cat.add(ball((0.065, 0.045, 0.065), cuts=1), cream, E @ M(on_eye(-0.035, 0.05)))                   # one highlight, the same side on both

        # soft cheek wool: one small point low on each cheek, the same grey as the cheek itself
        base, _ = press(on_skull, O, (0.9 * sx, -0.2, -0.44))
        cat.add(point(base, (sx, 0.05, -0.55), 0.2, 0.13, segs=8), grey, H)

    for sx, lean, turn in ((1, 13, 12), (-1, -19, -14)):   # ears: short wide triangles; the left one leans out further
        E = H @ M((0.42 * sx, 0.06, 0.78), rot=(-5, lean, turn))
        zlo, tall = -0.42, 0.84
        ear = taper(rounded_box((0.7, 0.3, tall), n=2.6, cuts=4), axis=2, lo=1.0, hi=0.22)
        for v in ear.verts:                                # hollow the front, like a real ear
            s = 1.0 - 0.78 * (v.co.z - zlo) / tall
            if v.co.y < 0:
                v.co.y += 0.08 * s * max(0.0, 1 - (v.co.x / (0.35 * s)) ** 2)
        a = 0.05 * sx
        shear(ear, axis=2, along=0, amount=a)
        cut(ear, (0.25, 0, zlo), (1, 0, (0.273 - a) / tall))        # the pink inside is cut into the ear's own surface
        cut(ear, (-0.25, 0, zlo), (-1, 0, (0.273 + a) / tall))
        ear.normal_update()

        def inside(f):
            c = centre(f)
            u = (c.z - zlo) / tall
            return f.normal.y < -0.25 and abs(c.x - a * u) < 0.25 - 0.273 * u

        inner, outer = split(ear, inside)
        cat.add(inner, pink, E)
        cat.add(outer, grey, E)
        for base, to, length in (((-0.15 * sx, -0.08, -0.2), (0.35 * sx, -0.2, 1), 0.2), ((-0.2 * sx, -0.08, -0.22), (0.8 * sx, -0.25, 0.6), 0.15)):
            cat.add(tuft(base, to, length, 0.055, segs=5), cream, E)                                        # pale wool inside the ear

    cat.build(SCALE)
    return cat


def bake(cat, texture):
    """All the wool, the collar and the bell become one textured mesh with soft shading baked in; the
    glass eyes stay a mesh of their own. Roblox gets two MeshParts."""
    eyes = [ob for ob in cat.objects if ob.name.endswith("_Gloss")]
    body = kit.bake_texture([ob for ob in cat.objects if ob not in eyes], texture, name="Cat_Body", shade=0.5, soften=3, rough=0.95, sheen=0.4)
    cat.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "cat_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    cat = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(cat, os.path.abspath(a.texture))
    tris = cat.triangles()
    lo, hi = cat.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(cat.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        import review
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig = review.Rig(cat, focus=(-0.1 * SCALE, -1.1 * SCALE, 2.56 * SCALE))
        quick = [("front 3/4", "full"), ("close-up", "full"), ("side", "full"), ("game distance", "full")]
        rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title="Cat (needle-felted tabby) review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
