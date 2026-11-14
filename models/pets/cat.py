"""Cat pet, a needle-felted wool tabby wearing a little miner's cap (13 rounds of practice, 8 since
the remake in cat_v6.py). Built from scratch by script.

    python models/pets/cat.py --review out/cat.png
    python models/pets/cat.py --export models/export/cat.fbx

Style: a small hand-made needle-felted cat from a mine, sitting with its tail wrapped round its front
paws and its head tilted. Must-haves, checked in every review:
  1. Wool you can believe: tangled fibres, needle pocks, stray hairs and a soft fuzzy edge; lumpy,
     hand-felted forms; a matte surface. Never smooth plastic.
  2. Tabby laid on like wool roving: uneven, tapering stripes with fibrous edges, a classic "M" on the
     forehead, warm grey-brown on oatmeal, a cream chest, muzzle and paws. No hard bands.
  3. A small, sweet face: glossy bead eyes with an amber iris, a tiny pink felt nose, an embroidered
     thread mouth. No teeth, dots or big smile.
  4. An outline with character: pear-shaped sit, head tilted, tail curled round the paws, ears apart.
  5. A mining touch, small and tasteful: a mustard felt hard hat with a tiny brass lamp.

How the wool is made: every part is baked white by kit.bake_texture (which unwraps it and bakes the
soft shading of the creases). Then the position, normal and part of every texel are baked too, and the
wool is painted texel by texel from those: the colour regions and the tabby strokes, each with a
fibrous edge, and the fibres themselves, combed along the surface. It is worked out at twice the
texture size and averaged down, so fine fibres stay smooth.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, rounded_box, taper, tube  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0
TITLE = "Cat (needle-felted miner tabby) review"

# part ids, kept per vertex in the colour attribute "aux" (red = id / 64, green and blue = part data)
PID = dict(body=1, thigh=2, foot=3, leg=4, paw=5, tail=6, head=7, muzzle=8, ear=9, iris=10, nose=11,
           thread=12, cap=13, brass=14, chest=15)


# ---- shapes ------------------------------------------------------------------------------------------

def _super(a, n):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def loft(rings, segs=24, n=2.2):
    """A closed body lofted through horizontal rings (z, centre y, half width, half depth in front,
    half depth behind). The back can be rounder than the chest."""
    bm = bmesh.new()
    loops = []
    for z, cy, rx, ryf, ryb in rings:
        loop = []
        for j in range(segs):
            x, y = _super(2 * math.pi * j / segs, n)
            loop.append(bm.verts.new((x * rx, cy + y * (ryb if y > 0 else ryf), z)))
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for loop, (z, cy, *_), rev in ((loops[0], rings[0], True), (loops[-1], rings[-1], False)):
        c = bm.verts.new((0, cy, z))
        for j in range(segs):
            f = (loop[j], loop[(j + 1) % segs], c)
            bm.faces.new(f[::-1] if rev else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def bumpy(bm, amount=0.02, freq=1.5, seed=0.0):
    """Hand-felted unevenness along each point's own normal: a slow lump and a finer one."""
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    bm.normal_update()
    for v in bm.verts:
        k = noise.noise(v.co * freq + off) + 0.4 * noise.noise(v.co * freq * 2.7 + off * 1.7)
        v.co += v.normal * k * amount
    return bm


def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def fuzz(bm, count, rng, at=None, length=(0.04, 0.11), radius=0.0032, where=None):
    """Stray wool fibres: thin curved wisps rooted in the surface of `bm` (left unchanged), most of them
    lying close along it, a few standing out. Returns one bmesh of all of them, moved by `at`."""
    bm.normal_update()
    faces = [f for f in bm.faces if where is None or where(f.calc_center_median(), f.normal)]
    areas = np.array([f.calc_area() for f in faces])
    out = bmesh.new()
    if not faces:
        return out
    picks = rng.choice(len(faces), size=count, p=areas / areas.sum())
    for i in picks:
        f = faces[i]
        a, b = rng.random(2)
        if a + b > 1:
            a, b = 1 - a, 1 - b
        vs = [v.co for v in f.verts]
        base = vs[0] + (vs[1] - vs[0]) * a + (vs[-1] - vs[0]) * b
        nrm = f.normal.copy()
        side = nrm.orthogonal().normalized()
        side.rotate(Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, nrm))
        rise = rng.uniform(0.7, 1.8)
        L = rng.uniform(*length)
        d1 = (side + nrm * rise).normalized()
        curl = side.cross(nrm) * rng.uniform(-0.7, 0.7)
        pts = [base - nrm * 0.008, base + d1 * L * 0.55, base + (d1 + curl * 0.6 + side * 0.4).normalized() * L]
        e = (pts[1] - pts[0]).normalized()
        u = e.orthogonal().normalized()
        v = e.cross(u)
        ring = lambda c, r: [out.verts.new(c + (u * math.cos(k * 2.094) + v * math.sin(k * 2.094)) * r) for k in range(3)]
        r0, r1, tip = ring(pts[0], radius), ring(pts[1], radius * 0.75), out.verts.new(pts[2])
        for k in range(3):
            out.faces.new((r0[k], r0[(k + 1) % 3], r1[(k + 1) % 3], r1[k]))
            out.faces.new((r1[k], r1[(k + 1) % 3], tip))
    bmesh.ops.recalc_face_normals(out, faces=out.faces[:])
    if at is not None:
        out.transform(at)
    return out


def tree(bm, at=None):
    c = bm.copy()
    if at is not None:
        c.transform(at)
    t = BVHTree.FromBMesh(c)
    c.free()
    return t


def cast(bvh, origin, direction):
    """Where a ray from `origin` along `direction` first meets the mesh (point, normal)."""
    d = Vector(direction).normalized()
    loc, nrm, _, _ = bvh.ray_cast(Vector(origin), d)
    if loc is None:
        return None, None
    if nrm.dot(d) > 0:
        nrm = -nrm
    return loc, nrm


def from_front(bvh, x, z, y0=-5.0):
    return cast(bvh, (x, y0, z), (0, 1, 0))


def spline_pts(pts, n):
    pts = [Vector(p) for p in pts]
    return [kit._spline(pts, i / (n - 1) * (len(pts) - 1)) for i in range(n)]


def euler_facing(nrm):
    """Rotation (degrees, XYZ) that turns a shape's -Y side to face along `nrm`."""
    yaw = math.degrees(math.atan2(nrm.x, -nrm.y))
    pitch = math.degrees(math.atan2(nrm.z, math.hypot(nrm.x, nrm.y)))
    return (-pitch, 0, yaw)


# ---- the cat ---------------------------------------------------------------------------------------------

def build():
    """Returns the prop and what the paint pass needs: the frames and strokes of the markings."""
    mats = {k: kit.material("W_" + k, "#FFFFFF", rough=0.95) for k in PID}
    gloss = kit.material("Gloss", "#1A120D", rough=0.07, coat=1.0)
    glow = kit.material("GLOW_Lamp", "#FFD98A", rough=0.3, emit=4.0)
    cat = Prop("Cat")
    spec = {"strokes": [], "frames": {}}

    # ---- body: a pear-shaped sit, the back rounder than the chest ------------------------------------
    rings = [(0.00, 0.18, 0.72, 0.62, 0.74), (0.10, 0.18, 0.82, 0.72, 0.83), (0.32, 0.16, 0.87, 0.77, 0.86),
             (0.62, 0.11, 0.85, 0.75, 0.83), (0.92, 0.04, 0.79, 0.69, 0.76), (1.2, -0.04, 0.71, 0.63, 0.67),
             (1.46, -0.11, 0.62, 0.57, 0.58), (1.68, -0.16, 0.52, 0.5, 0.49), (1.86, -0.19, 0.41, 0.41, 0.38),
             (1.98, -0.2, 0.22, 0.22, 0.22)]
    spec["body_axis"] = [(z, cy) for z, cy, *_ in rings]
    body = grounded(bumpy(loft(rings, segs=26), 0.055, 1.35, seed=1.0))
    chest = grounded(bumpy(ball((0.72, 0.46, 0.92), cuts=4), 0.022, 2.0, seed=2.0), M((0, -0.42, 1.12), rot=(12, 0, 0)))
    on_body = tree(body)
    rng = np.random.default_rng(5)
    cat.add(fuzz(body, 26, rng, where=lambda c, nr: c.z > 0.7 and nr.y > 0.2), mats["body"])
    cat.add(body.copy(), mats["body"])
    cat.add(chest, mats["chest"])

    # ---- haunches and hind feet ----------------------------------------------------------------------------
    thighs = {}
    for sx in (-1, 1):
        T = M((0.64 * sx, 0.26, 0.42), rot=(0, 0, 10 * sx))
        th = grounded(bumpy(ball((0.6, 0.98, 0.86), cuts=4), 0.03, 1.8, seed=3 + sx), T)
        thighs[sx] = tree(th)
        cat.add(fuzz(th, 5, rng, where=lambda c, nr: nr.z > 0.3), mats["thigh"])
        cat.add(th, mats["thigh"])
        foot = grounded(bumpy(rounded_box((0.32, 0.6, 0.21), n=2.5, cuts=3), 0.012, 3.0, seed=4 + sx),
                        M((0.6 * sx, -0.44, 0.1), rot=(0, 0, 12 * sx)))
        cat.add(foot, mats["foot"])

    # ---- front legs and paws ---------------------------------------------------------------------------------
    legs = {}
    for sx in (-1, 1):
        top, bot = Vector((0.25 * sx, -0.4, 1.24)), Vector((0.27 * sx, -0.66, 0.14))
        mid = (top + bot) / 2 + Vector((0.02 * sx, -0.05, 0))
        leg = bumpy(tube([top, mid, bot], [0.2, 0.17, 0.152], segs=12, rings=10), 0.014, 3.0, seed=5 + sx)
        legs[sx] = (top, bot)
        cat.add(leg, mats["leg"])
        paw = grounded(bumpy(rounded_box((0.34, 0.42, 0.21), n=2.4, cuts=3), 0.012, 3.0, seed=6 + sx),
                       M((0.26 * sx, -0.75, 0.1), rot=(0, 0, 4 * sx)))
        cat.add(paw, mats["paw"])
    spec["legs"] = legs

    # ---- tail: from the back round the left side, its tip resting over the left paw -----------------------
    tail_pts = [(0.25, 0.86, 0.17), (-0.35, 0.86, 0.155), (-0.88, 0.5, 0.15), (-1.02, -0.1, 0.15),
                (-0.86, -0.62, 0.15), (-0.55, -0.93, 0.16), (-0.28, -0.98, 0.22), (-0.06, -0.92, 0.27)]
    tail_r = [0.16, 0.168, 0.165, 0.158, 0.15, 0.142, 0.13, 0.1]
    tail = bumpy(tube(tail_pts, tail_r, segs=12, rings=44), 0.012, 2.6, seed=7.0)
    for v in tail.verts:
        v.co.z = max(v.co.z, 0.0)
    cat.add(fuzz(tail, 16, rng, where=lambda c, nr: nr.z > 0.2), mats["tail"])
    cat.add(tail, mats["tail"])
    spec["tail"] = spline_pts(tail_pts, 120)

    # ---- head: built round its own centre, then tilted and turned as one ----------------------------------
    H = M((0.0, -0.3, 2.27), rot=(-4, 10, -9))
    spec["frames"]["head"] = H
    skull = kit.lumpy(taper(rounded_box((1.4, 1.16, 1.1), n=2.35, cuts=9), axis=2, lo=1.08, hi=0.88), 0.042, 1.25, seed=8.0)
    for v in skull.verts:
        if v.co.y < 0:
            v.co.y *= 0.88
        jowl = math.exp(-((v.co.z + 0.14) / 0.2) ** 2) * min(1.0, abs(v.co.x) / 0.5)
        v.co.x *= 1.0 + 0.075 * jowl                              # full felted cheeks, wider than the brow
    on_skull = tree(skull)
    cat.add(fuzz(skull, 70, rng, at=H, length=(0.05, 0.12), where=lambda c, nr: abs(nr.y) < 0.55 and (nr.z > 0.15 or abs(nr.x) > 0.65)), mats["head"])
    cat.add(skull.copy(), mats["head"], H)

    face = skull                                            # skull, whisker pads and chin, to lay the thread on
    pads = []
    for sx in (-1, 1):
        p, n = from_front(on_skull, 0.088 * sx, -0.2)
        pad = kit.lumpy(ball((0.185, 0.11, 0.14), cuts=3), 0.006, 3.0, seed=9 + sx)
        pad.transform(M(p - n * 0.056))
        pads.append(pad)
    p, n = from_front(on_skull, 0.0, -0.32)
    chin = ball((0.12, 0.08, 0.07), cuts=2)
    chin.transform(M(p - n * 0.045))
    for part in pads + [chin]:
        tmp = bpy.data.meshes.new("tmp")
        part.to_mesh(tmp)
        face.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    on_face = BVHTree.FromBMesh(face)
    face.free()
    for part in pads + [chin]:
        cat.add(part, mats["muzzle"], H)

    # tiny felt nose: a soft rounded triangle, point down
    p, n = from_front(on_face, 0.0, -0.13)
    nose = taper(ball((0.115, 0.07, 0.078), cuts=2), axis=2, lo=0.35, hi=1.0)
    cat.add(nose, mats["nose"], H @ M(p - n * 0.012, rot=euler_facing(n)))

    # embroidered mouth: a short drop from the nose, then a soft "w"
    def thread(pts2d, r=0.0062):
        pts = [from_front(on_face, x, z)[0] + Vector((0, -0.006, 0)) for x, z in pts2d]
        return tube(pts, [r] * len(pts), segs=4, rings=3 * (len(pts) - 1))
    cat.add(thread([(0.0, -0.16), (0.0, -0.198)]), mats["thread"], H)
    for sx in (-1, 1):
        cat.add(thread([(0.0, -0.196), (0.024 * sx, -0.216), (0.047 * sx, -0.213), (0.062 * sx, -0.2)]), mats["thread"], H)

    # eyes: an amber felt iris bead with a glossy dark pupil bead set into it
    eyes = {}
    for sx in (-1, 1):
        p, n = from_front(on_skull, 0.29 * sx, 0.0)
        E = H @ M(p - n * 0.03, rot=euler_facing(n))
        eyes[sx] = E
        cat.add(ball((0.155, 0.085, 0.165), cuts=3), mats["iris"], E)
        cat.add(ball((0.1, 0.065, 0.108), cuts=3), gloss, E @ M((0, -0.024, 0.004)))
    spec["frames"]["eyes"] = eyes

    # ears: felted triangles, cupped in front, the left one leaning out a little more
    ears = {}
    for sx, lean, turn in ((1, 14, 9), (-1, -20, -12)):
        E = H @ M((0.43 * sx, 0.07, 0.36), rot=(-8, lean, turn))
        ears[sx] = E
        ear = rounded_box((0.5, 0.17, 0.46), n=2.4, cuts=4)
        for v in ear.verts:
            v.co.z += 0.23
        taper(ear, axis=2, lo=1.0, hi=0.18)
        for v in ear.verts:
            u = v.co.z / 0.46
            if v.co.y < 0:
                v.co.y += 0.06 * (1 - u) * max(0.0, 1 - (v.co.x / (0.25 * (1 - 0.8 * u) + 1e-3)) ** 2)
        kit.lumpy(ear, 0.01, 4.0, seed=10 + sx)
        cat.add(fuzz(ear, 10, rng, at=E, length=(0.03, 0.07), where=lambda c, nr: abs(nr.y) < 0.45 and c.z > 0.1), mats["ear"])
        cat.add(ear, mats["ear"], E)
    spec["frames"]["ears"] = ears

    # the miner's cap: a mustard felt hard hat, a peak in front, a ridge over the top and a tiny lamp
    C = H @ M((0.02, -0.06, 0.5), rot=(-10, 0, 3))
    spec["frames"]["cap"] = C
    dome = kit.lumpy(rounded_box((0.46, 0.5, 0.4), n=2.2, cuts=5), 0.008, 3.0, seed=11.0)
    cat.add(dome, mats["cap"], C @ M((0, 0, 0.04)))
    brim = rounded_box((0.56, 0.7, 0.05), n=2.3, cuts=4)
    cat.add(brim, mats["cap"], C @ M((0, -0.07, 0.03)))
    ridge = tube([(0, -0.26, 0.12), (0, -0.1, 0.24), (0, 0.1, 0.24), (0, 0.24, 0.12)], [0.035, 0.04, 0.04, 0.035], segs=6, rings=8)
    cat.add(ridge, mats["cap"], C)
    on_dome = tree(rounded_box((0.46, 0.5, 0.4), n=2.2, cuts=5), M((0, 0, 0.04)))
    p, n = cast(on_dome, (0, -2, 0.13), (0, 1, 0))
    lamp = tube([p - n * 0.02, p + n * 0.06], [0.068, 0.074], segs=10, rings=2)
    cat.add(lamp, mats["brass"], C)
    rim = tube([p + n * 0.055, p + n * 0.082], [0.078, 0.072], segs=10, rings=1)
    cat.add(rim, mats["brass"], C)
    cat.add(ball((0.1, 0.032, 0.1), cuts=2), glow, C @ M(p + n * 0.08, rot=euler_facing(n)))

    # ---- the markings, as strokes of roving laid on the surface (world space) ----------------------------
    def on_head(x, z, y0=-3.0):
        """A point on the front of the skull, head-local, found from straight in front."""
        p, _ = from_front(on_skull, x, z, y0)
        return p

    def over_head(az, el):
        """A point on the skull seen from its centre: az round from the front, el up from level (degrees)."""
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        p, _ = cast(on_skull, d * 3.0, -d)
        return p

    head_strokes = []
    # the "M": up from above each eye to a peak, down into a dip, up to the middle
    m_pts = [(-0.25, 0.07), (-0.225, 0.2), (-0.17, 0.3), (-0.115, 0.26), (-0.06, 0.19), (-0.02, 0.23), (0.0, 0.28)]
    m_r = [0.01, 0.034, 0.042, 0.038, 0.034, 0.034, 0.04]
    for sx in (-1, 1):
        pts = spline_pts([(x * sx, z) for x, z in m_pts], 19)
        rr = [float(np.interp(i / 18 * 6, range(7), m_r)) for i in range(19)]
        head_strokes.append(([on_head(v.x, v.y) for v in pts], rr))
    for x0, r, e0 in ((0.0, 0.04, 27), (-0.17, 0.032, 29), (0.17, 0.032, 29)):     # stripes from the M's peaks up over the crown and down the back
        pts = [over_head(math.degrees(math.atan2(x0, 0.6)) * (1 - k * 0.12), e0 + k * 20) for k in range(8)]
        head_strokes.append((pts, [r * 0.4, r * 0.9, r, r * 1.1, r * 1.1, r, r * 0.8, r * 0.3]))
    for sx in (-1, 1):                                       # cheek lines sweeping back from the eye
        head_strokes.append(([over_head(sx * a, e) for a, e in ((36, 3), (47, 1), (58, -3), (69, -8), (78, -14))], [0.006, 0.022, 0.026, 0.02, 0.006]))
        head_strokes.append(([over_head(sx * a, e) for a, e in ((48, -14), (59, -17), (69, -21))], [0.006, 0.02, 0.005]))
    spec["head_strokes"] = head_strokes

    body_strokes = []                                        # world space
    pts = [cast(on_body, (0, 4, z), (0, -1, 0))[0] for z in (1.95, 1.75, 1.5, 1.2, 0.9, 0.6, 0.38)]
    body_strokes.append((pts, [0.03, 0.07, 0.08, 0.085, 0.08, 0.06, 0.02]))              # the dark line down the spine
    neck = []
    for k in range(9):                                       # a broken "necklace" across the upper chest
        a = math.radians(-60 + 120 * k / 8)
        d = Vector((math.sin(a), -math.cos(a), 0.1))
        neck.append(cast(on_body, Vector((0, -0.12, 1.62)) + d * 3, -d)[0])
    body_strokes.append((neck[:4], [0.008, 0.03, 0.034, 0.01]))
    body_strokes.append((neck[5:], [0.01, 0.032, 0.026, 0.006]))
    for sx in (-1, 1):                                       # two arcs round each haunch
        T = M((0.64 * sx, 0.26, 0.42), rot=(0, 0, 10 * sx))
        c = T @ Vector((0, 0.05, 0.08))
        out = (T.to_3x3() @ Vector((sx, 0, 0))).normalized()
        for rho, a0, a1, w in ((0.17, -50, 210, 0.06), (0.37, -15, 175, 0.065)):
            arc = []
            for k in range(10):
                a = math.radians(a0 + (a1 - a0) * k / 9)
                q = c + Vector((0, math.cos(a) * rho * 1.15, math.sin(a) * rho))
                hitp, _ = cast(thighs[sx], q + out * 2.0, -out)
                if hitp is not None:
                    arc.append(hitp)
            body_strokes.append((arc, [w * s for s in (0.25, 0.7, 1, 1, 1, 0.9, 0.9, 0.8, 0.6, 0.2)][:len(arc)]))
    spec["body_strokes"] = body_strokes

    cat.build(SCALE)
    tag(cat, spec)
    return cat, spec


def tag(cat, spec):
    """Give every vertex its part id and part data in the colour attribute "aux"."""
    tail = [Vector(p) for p in spec["tail"]]
    for ob in cat.objects:
        key = ob.name[len("Cat_W_"):] if ob.name.startswith("Cat_W_") else None
        if key not in PID:
            continue
        me = ob.data
        attr = me.color_attributes.new("aux", 'FLOAT_COLOR', 'POINT')
        for i, v in enumerate(me.vertices):
            u = w = 0.0
            p = v.co
            if key == "tail":
                k = min(range(len(tail)), key=lambda j: (tail[j] - p).length_squared)
                u = k / (len(tail) - 1)
            elif key == "leg":
                top, bot = spec["legs"][1 if p.x > 0 else -1]
                ax = bot - top
                u = max(0.0, min(1.0, (p - top).dot(ax) / ax.length_squared))
            if key in ("ear", "iris", "leg", "paw", "foot", "thigh"):
                w = 0.75 if p.x > 0 else 0.25
            attr.data[i].color = (PID[key] / 64.0, u, w, 1.0)


# ---- the paint pass -------------------------------------------------------------------------------------

class Perlin:
    """Improved Perlin noise in numpy, about -1 to 1, for millions of points at once."""

    def __init__(self, seed):
        p = np.random.default_rng(seed).permutation(256)
        self.perm = np.concatenate([p, p]).astype(np.int64)

    def __call__(self, P):
        P = np.asarray(P, np.float64)
        fl = np.floor(P)
        f = P - fl
        i = fl.astype(np.int64) & 255
        u = f * f * f * (f * (f * 6 - 15) + 10)
        perm = self.perm
        X, Y, Z = i[:, 0], i[:, 1], i[:, 2]
        A = perm[X] + Y
        B = perm[X + 1] + Y
        AA, AB, BA, BB = perm[A] + Z, perm[A + 1] + Z, perm[B] + Z, perm[B + 1] + Z
        x, y, z = f[:, 0], f[:, 1], f[:, 2]

        def g(h, x, y, z):
            h = h & 15
            a = np.where(h < 8, x, y)
            b = np.where(h < 4, y, np.where((h == 12) | (h == 14), x, z))
            return np.where(h & 1, -a, a) + np.where(h & 2, -b, b)

        def lerp(t, a, b):
            return a + t * (b - a)
        ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
        return lerp(uz,
                    lerp(uy, lerp(ux, g(perm[AA], x, y, z), g(perm[BA], x - 1, y, z)),
                         lerp(ux, g(perm[AB], x, y - 1, z), g(perm[BB], x - 1, y - 1, z))),
                    lerp(uy, lerp(ux, g(perm[AA + 1], x, y, z - 1), g(perm[BA + 1], x - 1, y, z - 1)),
                         lerp(ux, g(perm[AB + 1], x, y - 1, z - 1), g(perm[BB + 1], x - 1, y - 1, z - 1))))


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def band(d, w, soft=0.2):
    """1 inside a band of half-width w (soft-edged), 0 outside, and 0 wherever w has tapered to nothing."""
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(w > 1e-5, sstep(w, w * soft, d), 0.0)


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def tangent(F, N):
    """F made to lie along the surface."""
    return unit(F - N * (F * N).sum(1, keepdims=True))


def combed(P, F, stretch):
    """Points squeezed along the fibre direction F, so noise on them turns into long fibres."""
    along = (P * F).sum(1, keepdims=True)
    return P - F * along * (1.0 - 1.0 / stretch)


def stroke_field(P, strokes):
    """For lists of (points, radii): how far inside the nearest stroke each point is (in units of the
    stroke's radius there, 1 at the centre line, 0 at the edge, negative outside) and the direction of
    that stroke."""
    best = np.full(len(P), -9.0)
    dirs = np.zeros_like(P)
    for pts, radii in strokes:
        for (a, ra), (b, rb) in zip(zip(pts, radii), zip(pts[1:], radii[1:])):
            a, b = np.array(a), np.array(b)
            ab = b - a
            L2 = max(ab @ ab, 1e-9)
            t = np.clip(((P - a) @ ab) / L2, 0, 1)
            d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
            r = ra + (rb - ra) * t
            inside = 1.0 - d / np.maximum(r, 1e-4)
            better = inside > best
            best = np.where(better, inside, best)
            dirs[better] = ab / math.sqrt(L2)
    return best, dirs


def bake_data(ob, size, make):
    """Bake one emission pass of `ob` into a float image: what `make(tree)` returns as a colour."""
    sc = bpy.context.scene
    keep = ob.data.materials[0]
    mat = bpy.data.materials.new("DataBake")
    mat.use_nodes = True
    t = mat.node_tree
    for n in list(t.nodes):
        t.nodes.remove(n)
    out = t.nodes.new("ShaderNodeOutputMaterial")
    em = t.nodes.new("ShaderNodeEmission")
    t.links.new(make(t), em.inputs["Color"])
    t.links.new(em.outputs[0], out.inputs["Surface"])
    img = bpy.data.images.new("data", size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.zeros(size * size * 4, np.float32))
    node = t.nodes.new("ShaderNodeTexImage")
    node.image = img
    t.nodes.active = node
    ob.data.materials[0] = mat
    samples = sc.cycles.samples
    sc.cycles.samples = 1
    bpy.ops.object.bake(type='EMIT', margin=24)
    sc.cycles.samples = samples
    px = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    ob.data.materials[0] = keep
    bpy.data.images.remove(img)
    bpy.data.materials.remove(mat)
    return px.reshape(size * size, 4)


LO, SPAN = -3.0, 7.0


def paint(ob, spec, size):
    """Paint the wool into the baked texture of `ob` (which so far holds only its soft shading)."""
    big = size * 2

    def position(t):
        tc = t.nodes.new("ShaderNodeTexCoord")
        m = t.nodes.new("ShaderNodeVectorMath")
        m.operation = 'MULTIPLY_ADD'
        m.inputs[1].default_value = (1 / SPAN,) * 3
        m.inputs[2].default_value = (-LO / SPAN,) * 3
        t.links.new(tc.outputs["Object"], m.inputs[0])
        return m.outputs[0]

    def normal(t):
        g = t.nodes.new("ShaderNodeNewGeometry")
        m = t.nodes.new("ShaderNodeVectorMath")
        m.operation = 'MULTIPLY_ADD'
        m.inputs[1].default_value = (0.5, 0.5, 0.5)
        m.inputs[2].default_value = (0.5, 0.5, 0.5)
        t.links.new(g.outputs["Normal"], m.inputs[0])
        return m.outputs[0]

    def aux(t):
        a = t.nodes.new("ShaderNodeAttribute")
        a.attribute_name = "aux"
        return a.outputs["Color"]

    D = bake_data(ob, big, aux)
    valid = D[:, 0] > 0.004
    idx = np.nonzero(valid)[0]
    P = bake_data(ob, big, position)[idx, :3].astype(np.float64) * SPAN + LO
    N = unit(bake_data(ob, big, normal)[idx, :3].astype(np.float64) * 2 - 1)
    pid = np.rint(D[idx, 0] * 64).astype(int)
    U, W = D[idx, 1].astype(np.float64), D[idx, 2].astype(np.float64)
    n = len(idx)
    print("paint: %d texels at %d px (%.0f%% of the image)" % (n, big, 100.0 * n / big / big))

    def part(*names):
        return np.isin(pid, [PID[k] for k in names])

    noise_a, noise_b, noise_c, noise_d = Perlin(1), Perlin(2), Perlin(3), Perlin(4)
    H = spec["frames"]["head"]
    Hi = H.inverted()
    R, t0 = np.array(Hi.to_3x3()), np.array(Hi.translation)
    Q = P @ R.T + t0                                          # head-local positions
    QN = N @ R.T

    # ---- colour regions ----
    OAT, TAB, CREAM = hexc("#C6AD86"), hexc("#7B6654"), hexc("#F4ECDF")
    col = np.tile(OAT, (n, 1))
    cream = np.zeros(n)
    tabby = np.zeros(n)
    flow = np.tile(np.array([0.0, 0.25, -1.0]), (n, 1))      # fibres combed down and a little back
    wisp = noise_b(P * np.array([30.0, 30.0, 30.0]) + 3.1)  # breaks every soft edge into fibres
    wisp2 = noise_c(P * 9.0)

    # body and haunches: stripes running round the back and down the flanks, tapering out
    bodyish = part("body", "thigh", "chest")
    ax = spec["body_axis"]
    zs = np.array([a for a, _ in ax])
    cys = np.array([b for _, b in ax])
    cy = np.interp(P[:, 2], zs, cys)
    theta = np.arctan2(P[:, 0], P[:, 1] - cy)                # 0 straight behind, +-pi in front
    s = P[:, 2] + 0.22 * (np.abs(theta) / 1.4) ** 2 + 0.07 * noise_a(P * 2.2) + 0.025 * noise_d(P * 6.0)
    stripes = [(0.4, 0.085, 1.6), (0.7, 0.115, 2.05), (0.98, 0.08, 1.75), (1.25, 0.11, 1.95), (1.52, 0.075, 1.65), (1.77, 0.06, 1.25),
               (0.56, 0.035, 1.2), (1.12, 0.04, 1.35), (1.4, 0.03, 0.9)]
    droops = [0.0, 0.06, -0.04, 0.08, -0.02, 0.05, 0.1, -0.06, 0.04]
    for k, (s0, w0, reach) in enumerate(stripes):
        s0 = s0 - droops[k] * (np.abs(theta) / 1.4) ** 2 + 0.03 * np.sign(theta) * ((k * 7) % 3 - 1)
        side = np.abs(theta) + 0.25 * np.sign(theta) * (k % 2 - 0.5) * 0.6
        w = w0 * np.clip(1 - (np.abs(side) / reach) ** 1.6, 0, 1) * (0.8 + 0.35 * noise_c(P * 3.0 + k))
        d = np.abs(s - s0) - w * 0.45 * wisp
        m = band(d, w) * bodyish * (P[:, 2] > 0.18)
        tabby = np.maximum(tabby, m * (0.7 + 0.3 * noise_d(P * 4 + k)))
    around = unit(np.cross(np.tile([0.0, 0, 1], (n, 1)), np.stack([P[:, 0], P[:, 1] - cy, np.zeros(n)], 1)))
    flow = np.where((bodyish & (tabby > 0.05))[:, None], around, flow)

    # chest bib: cream, a drop shape down the front, its edge fibrous
    front = np.abs(theta)
    bib_w = np.interp(P[:, 2], [0.2, 0.6, 1.0, 1.4, 1.75, 2.1], [0.35, 0.55, 0.68, 0.72, 0.66, 0.5])
    bib = sstep(np.pi - bib_w, np.pi - bib_w + 0.4, front + 0.16 * wisp + 0.12 * wisp2) * bodyish
    cream = np.maximum(cream, bib)

    f_strokes, f_dir = stroke_field(P, spec["body_strokes"])
    m = sstep(0.0, 0.55, f_strokes + 0.3 * wisp) * bodyish
    tabby = np.maximum(tabby, m * (0.8 + 0.2 * noise_d(P * 4)))
    flow = np.where((bodyish & (m > 0.3))[:, None], f_dir, flow)

    # front legs: oatmeal at the top, two short bars on the front, cream socks; paws and hind feet cream
    leg = part("leg")
    facing = np.clip(N[:, 1] * -0.8 + np.abs(N[:, 0]) * 0.6 + 0.25, 0, 1)
    for right, t_bar, w, op in ((False, 0.19, 0.075, 0.9), (False, 0.38, 0.045, 0.7), (True, 0.25, 0.065, 0.85), (True, 0.42, 0.05, 0.6)):
        sel = leg & ((W > 0.5) == right)
        slant = 0.05 * N[:, 0] * (1 if right else -1)
        d = np.abs(U - t_bar + slant - 0.025 * noise_a(P * 5)) * 1.2 - 0.4 * w * wisp
        tabby = np.maximum(tabby, band(d, w * facing * (0.75 + 0.25 * noise_c(P * 4)), 0.25) * sel * op)
    cream = np.maximum(cream, sstep(0.5, 0.66, U + 0.06 * wisp + 0.03 * wisp2) * leg)
    cream = np.where(part("paw", "foot"), 1.0, cream)
    flow = np.where(leg[:, None], np.tile([0.0, -0.2, -1.0], (n, 1)), flow)
    flow = np.where(part("paw", "foot")[:, None], np.tile([0.0, -1.0, 0.0], (n, 1)), flow)

    # tail: uneven rings, strong on top and fading underneath, and a dark tip
    tl = part("tail")
    tail = np.array([tuple(v) for v in spec["tail"]])
    tdir = np.gradient(tail, axis=0)
    k = np.clip(np.rint(U * (len(tail) - 1)).astype(int), 0, len(tail) - 1)
    tflow = unit(tdir[k])
    length = np.sum(np.linalg.norm(np.diff(tail, axis=0), axis=1))
    top = np.clip(N[:, 2] + 0.45, 0, 1)
    for t_ring, w in ((0.12, 0.075), (0.28, 0.09), (0.43, 0.07), (0.57, 0.085), (0.72, 0.075)):
        slant = 0.012 * (N[:, 0] + N[:, 1])
        d = np.abs(U - t_ring + slant + 0.01 * noise_a(P * 4)) * length - 0.45 * w * wisp
        ww = w * (0.35 + 0.65 * top)
        tabby = np.maximum(tabby, band(d, ww) * tl * (0.65 + 0.3 * top))
    tabby = np.maximum(tabby, sstep(0.86, 0.93, U + 0.02 * wisp) * tl)
    flow = np.where(tl[:, None], tflow, flow)

    # head: cream muzzle, chin and lower cheeks, light round the eyes; the "M", crown and cheek lines
    hd = part("head", "muzzle")
    e = np.linalg.norm((Q - np.array([0.0, -0.55, -0.23])) / np.array([0.22, 0.3, 0.145]), axis=1)
    mz = sstep(1.05, 0.8, e + 0.12 * wisp)
    low = sstep(-0.3, -0.44, Q[:, 2] + 0.05 * wisp) * (Q[:, 1] < -0.1)
    cream = np.where(hd, np.maximum(np.maximum(mz, low), part("muzzle")), cream)
    for sx in (-1, 1):
        Ei = spec["frames"]["eyes"][sx]
        c = np.array((Hi @ Ei).translation)
        d = np.linalg.norm(Q - c, axis=1)
        cream = np.maximum(cream, sstep(0.15, 0.1, d + 0.025 * wisp) * hd * 0.4)
    hs = spec["head_strokes"]
    h_strokes, h_dir = stroke_field(Q, hs[:2] + hs[5:])                # the M and the cheek lines
    c_strokes, c_dir = stroke_field(Q, hs[2:5])                         # fainter lines up the forehead and over the crown
    m = sstep(-0.1, 0.65, h_strokes + 0.45 * wisp) * hd
    mc = sstep(-0.1, 0.7, c_strokes + 0.5 * wisp) * hd * 0.6
    h_dir = np.where((mc > m)[:, None], c_dir, h_dir)
    m = np.maximum(m, mc)
    tabby = np.maximum(tabby, m * (0.85 + 0.15 * noise_d(P * 6)))
    radial = Q - np.array([0.0, -0.75, -0.2])
    hflow = tangent(radial, QN)
    hflow = np.where((m > 0.3)[:, None], h_dir, hflow)
    flow = np.where(hd[:, None], hflow @ np.array(H.to_3x3()).T, flow)

    # ears: pale inner wool with a fibrous edge, a darker back and tip
    er = part("ear")
    EAR_IN, EAR_BACK = hexc("#EFD7CC"), hexc("#9E8A74")
    ear_in = np.zeros(n)
    ear_back = np.zeros(n)
    for sx in (-1, 1):
        Ei = spec["frames"]["ears"][sx].inverted()
        L = P @ np.array(Ei.to_3x3()).T + np.array(Ei.translation)
        sel = er & ((W > 0.5) == (sx > 0))
        u = np.clip(L[:, 2] / 0.46, 0, 1)
        halfw = 0.25 * (1 - 0.82 * u)
        inside = (halfw - np.abs(L[:, 0])) / 0.25
        ear_in = np.where(sel, sstep(0.08, 0.2, inside + 0.06 * wisp) * sstep(0.0, -0.03, L[:, 1]) * sstep(0.85, 0.7, u), ear_in)
        ear_back = np.where(sel, sstep(0.35, 0.95, u + 0.08 * wisp) * 0.7, ear_back)
        ef = np.array(spec["frames"]["ears"][sx].to_3x3()) @ np.array([0.0, 0, 1])
        flow = np.where(sel[:, None], np.tile(ef, (n, 1)), flow)

    # ---- mix the regions ----
    flow = tangent(flow, N)
    tabby *= (1 - cream * 0.9)
    tab_core = sstep(0.4, 1.0, tabby)
    tab_col = (hexc("#A08A70")[None] * (1 - tab_core[:, None]) + hexc("#6C5847")[None] * tab_core[:, None])
    col = col * (1 - cream[:, None]) + CREAM[None] * cream[:, None]
    col = col * (1 - tabby[:, None]) + tab_col * tabby[:, None]
    col = np.where(er[:, None], col * (1 - ear_back[:, None]) + EAR_BACK * ear_back[:, None], col)
    col = np.where(er[:, None], col * (1 - ear_in[:, None]) + EAR_IN * ear_in[:, None], col)

    # parts with colours of their own
    def solid(name, hexcode):
        nonlocal col
        col = np.where(part(name)[:, None], hexc(hexcode)[None], col)
    solid("nose", "#D88A8A")
    solid("thread", "#6A4A40")
    solid("brass", "#B8964F")
    cap = part("cap")
    col = np.where(cap[:, None], hexc("#D3A03C")[None] * (0.93 + 0.07 * noise_c(P * 7))[:, None], col)
    iris = part("iris")
    if iris.any():
        for sx in (-1, 1):
            Ei = spec["frames"]["eyes"][sx].inverted()
            L = P @ np.array(Ei.to_3x3()).T + np.array(Ei.translation)
            r = np.hypot(L[:, 0] / 0.0775, L[:, 2] / 0.0825)
            ring = sstep(0.62, 0.95, r)
            ic = hexc("#F2BC48")[None] * (1 - ring[:, None]) + hexc("#C27A22")[None] * ring[:, None]
            ic = ic * (1 - sstep(0.93, 1.02, r)[:, None] * 0.3)
            streak = 0.9 + 0.1 * noise_a(np.stack([np.arctan2(L[:, 2], L[:, 0]) * 6, r * 3, L[:, 1] * 0], 1))
            col = np.where((iris & ((W > 0.5) == (sx > 0)))[:, None], ic * streak[:, None], col)
        flow = np.where(iris[:, None], np.tile([0.0, 0, 1.0], (n, 1)), flow)

    # ---- the wool itself ----
    wool = ~part("thread", "iris", "nose")
    felt = np.ones(n)
    # heathered roving: several shades of fibre mixed, in slow drifts
    felt *= 1 + 0.05 * noise_c(P * 5.0) + 0.035 * noise_d(P * 13.0)
    # combed fibres: the zero lines of noise squeezed along the flow are long, thin, curly strands
    light = sstep(0.84, 0.97, 1 - np.abs(noise_a(combed(P, flow, 6.0) * 46.0)))
    dark = sstep(0.84, 0.98, 1 - np.abs(noise_b(combed(P, flow, 5.0) * 26.0 + 7.7)))
    fine = sstep(0.8, 0.96, 1 - np.abs(noise_c(combed(P, flow, 3.0) * 70.0 + 1.3)))
    # tangled, uncombed fibres in every direction
    tangle = sstep(0.86, 0.98, 1 - np.abs(noise_d(P * 48.0 + 5.5)))
    lift = 1 - col
    col = col + lift * (0.22 * light + 0.16 * fine)[:, None] * wool[:, None]
    col = col * (1 - (0.16 * dark + 0.1 * tangle)[:, None] * wool[:, None])
    # stray dark hairs wandering over the pale wool, and pale ones over the stripes
    stray = sstep(0.93, 0.99, 1 - np.abs(noise_a(combed(P, flow, 12.0) * 15.0 + 11.0))) * sstep(0.2, 0.6, noise_b(P * 3.0 + 2.0))
    col = col * (1 - stray[:, None] * 0.35 * wool[:, None])
    # needle pocks: small soft dimples
    pock = sstep(0.55, 0.8, noise_c(P * 120.0 + 9.0))
    col = col * (1 - (0.09 * pock * wool)[:, None])
    col = col * felt[:, None]

    # ---- write it back, averaged down to the texture size and shaded by the baked creases ----
    img = next(nd.image for nd in ob.data.materials[0].node_tree.nodes if nd.type == 'TEX_IMAGE' and nd.image and nd.image.size[0] == size)
    base = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(base)
    base = base.reshape(size, size, 4)
    full = np.zeros((big * big, 3))
    full[idx] = np.clip(col, 0, 1)
    wt = np.zeros(big * big)
    wt[idx] = 1.0
    full = full.reshape(size, 2, size, 2, 3).sum(axis=(1, 3))
    wt = wt.reshape(size, 2, size, 2).sum(axis=(1, 3))
    have = wt > 0
    shade = base[..., :3]                                     # the white parts, baked: just the crease shading
    out = base.copy()
    out[have, :3] = full[have] / wt[have, None] * shade[have]
    img.pixels.foreach_set(out.ravel())
    img.save()


def bake(cat, spec, texture, size=1024):
    """All the wool and the cap become one textured mesh; the glossy pupils and the lamp glass stay
    meshes of their own. Roblox gets three MeshParts."""
    keep = [ob for ob in cat.objects if ob.name.endswith("_Gloss") or "GLOW" in ob.name]
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("BakeWorld")
    sc.world.light_settings.distance = 0.3               # crease shading only where shapes nearly touch
    body = kit.bake_texture([ob for ob in cat.objects if ob not in keep], texture, size=size, name="Cat_Body",
                            shade=0.55, soften=3, rough=0.95, sheen=0.75, pack_margin=0.003)
    paint(body, spec, size)
    for ob in keep:
        ob.name = ob.data.name = "Cat_Gloss" if ob.name.endswith("_Gloss") else "Cat_GLOW"
    cat.objects = [body] + keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="fewer views")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "cat_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    cat, spec = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(cat, spec, os.path.abspath(a.texture))
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
        face = spec["frames"]["head"] @ Vector((0, -0.4, -0.02))
        rig = review.Rig(cat, samples=a.samples, focus=tuple(face))
        rig.cams["face"] = review._camera("C_face", face + Vector((-0.3, -1.0, 0.12)).normalized() * 1.9, face, 30)
        quick = [("front 3/4", "full"), ("face", "full"), ("side", "full"), ("back 3/4", "full"), ("game distance", "full"), ("front 3/4", "clay")]
        rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, cols=3 if a.quick else 4, title=TITLE)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
