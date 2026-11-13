"""Turtle pet: a friendly little turtle with a patterned shell, in a hand-painted storybook style.
Built from scratch by script.

    python models/pets/turtle.py --review out/turtle.png      # render the review sheet
    python models/pets/turtle.py --export models/export/turtle.fbx

Must-haves, checked in every review:
  1. Reads as a turtle in outline: a domed shell with a raised rim, four stubby legs, a round head
     on a short neck stretched forward and slightly up, a tiny pointed tail.
  2. A clear pattern of plates: raised ochre plates on a darker brown shell, a pale under-shell.
  3. A simple, clearly friendly face: modest bead eyes set apart with one highlight each, two small
     nostrils, a gentle smile. Nothing crowding the face.
  4. Not plastic: scale patterns and several tones baked into the texture, a matte finish.
  5. One touch of character: a little seedling growing on the shell. Head turned a little.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, ball, rounded_box, tube  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SCALE = 1.0
SHELL_AT = Vector((0.0, 0.40, 1.05))      # the centre of the shell's rim
SHELL = (1.14, 1.18, 1.10)                # half width, half length, height of the dome
HEAD_AT = (-0.07, -1.70, 1.50)
HEAD_ROT = (-7, 4, -15)                   # nose a little up, a small tilt, turned towards -X (where the cameras are)


# ---- helpers ---------------------------------------------------------------------------------------

def grounded(bm, at=None):
    """Move a shape into place and flatten whatever would go below the floor."""
    if at is not None:
        bm.transform(at)
    for v in bm.verts:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return bm


def tones(mat, up=None, down=None, up_mix=0.5, down_mix=0.4):
    """More than one tone for a patterned material: where the surface faces up it turns towards the
    colour `up`, where it faces down towards `down`. Baked into the colour texture."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    base = tuple(hsv.inputs["Color"].default_value)
    geo = new("ShaderNodeNewGeometry")
    sep = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])
    colour = None
    for hexcode, amount, lo, hi in ((up, up_mix, 0.15, 0.95), (down, down_mix, -0.10, -0.90)):
        if not hexcode:
            continue
        rng = new("ShaderNodeMapRange")
        rng.interpolation_type = 'SMOOTHSTEP'
        rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = lo, hi
        rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.0, amount
        link(sep.outputs[2], rng.inputs["Value"])
        mix = new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        link(rng.outputs["Result"], mix.inputs[0])
        if colour is None:
            mix.inputs[6].default_value = base
        else:
            link(colour, mix.inputs[6])
        mix.inputs[7].default_value = (*kit.srgb(hexcode), 1.0)
        colour = mix.outputs[2]
    if colour is not None:
        link(colour, hsv.inputs["Color"])
    return mat


def seat(p, normal, up=(0, 0, 1)):
    """A transform that seats a shape at p on a surface: its front (-Y) looks out along `normal`
    and its top is as near `up` as it can be."""
    y = -Vector(normal).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(p)
    return m


class Surface:
    """Finds points exactly on a mesh, so that details sit on it and neither float nor sink."""

    def __init__(self, bm):
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, direction, out=0.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


def dome(d, lift=0.0):
    """The point of the shell's dome in the direction d from its centre, `lift` proud of it, and
    the dome's normal there."""
    d = Vector(d).normalized()
    a, b, c = SHELL
    r = 1.0 / math.sqrt((d.x / a) ** 2 + (d.y / b) ** 2 + (d.z / c) ** 2)
    p = d * r
    n = Vector((p.x / a ** 2, p.y / b ** 2, p.z / c ** 2)).normalized()
    return SHELL_AT + p + n * lift, n


def plate_dir(alpha, beta):
    """A direction on the dome: `beta` degrees over to the side (+X), then `alpha` degrees round
    towards the back (negative: towards the front)."""
    a, b = math.radians(alpha), math.radians(beta)
    return Vector((math.sin(b), math.sin(a) * math.cos(b), math.cos(a) * math.cos(b)))


def scute(alpha, beta, hu, hv, height=0.075, pinch=0.22, grid=(-1, -0.84, -0.42, 0, 0.42, 0.84, 1)):
    """One raised plate of the shell, lying on the dome at plate_dir(alpha, beta): `hu` to each side
    across the shell and `hv` along it. Its rim is tucked just under the dome."""
    d0 = plate_dir(alpha, beta)
    a = math.radians(alpha)
    ty = Vector((0, math.cos(a), -math.sin(a)))
    tx = ty.cross(d0)
    bm = bmesh.new()
    rows = []
    for v in grid:
        row = []
        for q in grid:
            edge = max(abs(q), abs(v))
            u_ = hu * q * (1 - pinch * abs(v) ** 3)
            v_ = hv * v * (1 - pinch * abs(q) ** 3)
            lift = -0.03 if edge >= 1 else height * (1 - edge ** 6)
            row.append(bm.verts.new(dome(d0 + tx * u_ + ty * v_, lift)[0]))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(len(grid) - 1):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(d0) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def rim_height(phi_deg):
    """How far above the shell's widest line the rim runs: it arches up over the neck."""
    return 0.03 + 0.38 * math.exp(-(phi_deg / 30.0) ** 2)


def rim(n=48, m=8, wide=0.16, tall=0.12):
    """The raised rim of the shell: a closed ring round the dome's edge."""
    a, b, c = SHELL
    pts = []
    for i in range(n):
        deg = 360.0 * i / n
        deg = deg - 360.0 if deg > 180.0 else deg
        h = rim_height(deg)
        s = math.sqrt(1 - (h / c) ** 2)
        phi = math.radians(deg)
        pts.append(SHELL_AT + Vector(((a * s + 0.03) * math.sin(phi), -(b * s + 0.03) * math.cos(phi), h)))
    bm = bmesh.new()
    loops = []
    for i in range(n):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        out = Vector((pts[i].x - SHELL_AT.x, pts[i].y - SHELL_AT.y, 0.0)).normalized()
        out = (out - t * out.dot(t)).normalized()
        up = t.cross(out)
        loops.append([bm.verts.new(pts[i] + out * (math.cos(q) * wide) + up * (math.sin(q) * tall))
                      for q in (2 * math.pi * j / m for j in range(m))])
    for i in range(n):
        r0, r1 = loops[i], loops[(i + 1) % n]
        for j in range(m):
            bm.faces.new((r0[j], r0[(j + 1) % m], r1[(j + 1) % m], r1[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def leaf(length, width, thick=0.06):
    """A leaf with its stalk end at the origin and its tip at +Y."""
    bm = ball((width, length, thick), cuts=2)
    for v in bm.verts:
        k = abs(v.co.y) / (length / 2)
        v.co.x *= 1 - 0.55 * k * k
        v.co.z += 0.05 * (1 - k * k) - 0.10 * abs(v.co.x) / width      # a little fold along the middle
        v.co.y += length / 2
    return bm


# ---- the turtle ------------------------------------------------------------------------------------

def build():
    # Six flat colours. The owner found smooth flat colour "like plastic", so every colour gets a
    # pattern that is baked into the texture, and the skin and shell have more than one tone.
    skin = kit.scaly(kit.material("Skin", "#86A94B"), size=0.14, joins=0.18, vary=0.12, shade_down=0.10, rough=0.85)
    tones(skin, up="#5E8F42", down="#CBDD8C", up_mix=0.4, down_mix=0.5)
    shell = kit.scaly(kit.material("Shell", "#7A4827"), size=0.55, joins=0.4, vary=0.14, rough=0.8)
    plate = kit.scaly(kit.material("Plate", "#D29843"), size=0.5, joins=0.14, vary=0.12, rough=0.8)
    tones(plate, up="#E9BE66", down="#B2702C", up_mix=0.45, down_mix=0.5)
    cream = kit.scaly(kit.material("Cream", "#F4E4B4"), size=0.42, joins=0.2, vary=0.07, shade_down=0.08, rough=0.85)
    leafm = kit.scaly(kit.material("Leaf", "#6FBF4A"), size=0.2, joins=0.1, vary=0.08, rough=0.8)
    eye = kit.material("Eye", "#15111B", rough=0.18)
    t = Prop("Turtle")
    t.tally = {}

    def add(part, bm, mat, at=None):
        t.tally[part] = t.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        t.add(bm, mat, at)

    a, b, c = SHELL

    # ---- shell: a dome, a raised rim, raised plates, a pale under-shell -------------------------------
    top = ball((2 * a, 2 * b, 2 * c), cuts=8)
    for v in top.verts:
        if v.co.z < 0.0:
            v.co.z *= 0.12                                               # the dome's flat underside, inside the under-shell
    add("shell", top, shell, M(SHELL_AT))
    add("rim", rim(), plate)
    add("under-shell", rounded_box((2 * a - 0.10, 2 * b - 0.06, 0.80), n=2.6, cuts=5), cream, M((SHELL_AT.x, SHELL_AT.y, 0.85)))
    for alpha in (-51, -17, 17, 51):                                     # the row of plates down the middle
        add("plates", scute(alpha, 0.0, 0.30, 0.27), plate)
    for sx in (-1, 1):                                                   # and three bigger ones down each side
        for alpha in (-42, 0, 42):
            add("plates", scute(alpha, 42.7 * sx, 0.40, 0.235), plate)

    # ---- legs: four stubby ones, feet flat on the ground ---------------------------------------------
    def leg(x, y, x0, y0, yaw):
        add("legs", grounded(tube([(x0, y0, 0.88), ((x0 + x) / 2 + 0.06 * (1 if x > 0 else -1), (y0 + y) / 2, 0.52), (x, y, 0.20)],
                                  [0.40, 0.38, 0.40], segs=10, rings=5)), skin)
        add("feet", grounded(rounded_box((0.84, 0.96, 0.50), n=2.5, cuts=3), M((x, y, 0), rot=(0, 0, yaw)) @ M((0, -0.10, 0.22))), skin)

    for sx in (-1, 1):
        step = -0.16 if sx < 0 else 0.0                                  # the near front foot is a step ahead
        leg(1.10 * sx, -0.30 + step, 0.66 * sx, -0.10, 16 * sx)
        leg(1.08 * sx, 1.24, 0.66 * sx, 0.98, 30 * sx)

    # ---- tail: tiny and pointed, swung a little to one side ---------------------------------------------
    add("tail", tube([(0, 1.30, 0.80), (0.05, 1.68, 0.66), (0.15, 1.92, 0.55)], [0.20, 0.13, 0.025], segs=8, rings=5), skin)

    # ---- neck and head -----------------------------------------------------------------------------------
    add("neck", tube([(0, -0.25, 0.92), (0, -0.78, 0.97), (-0.03, -1.22, 1.22), HEAD_AT], [0.40, 0.385, 0.34, 0.32], segs=12, rings=8), skin)
    H = M(HEAD_AT, rot=HEAD_ROT)
    head = rounded_box((1.0, 1.08, 0.92), n=2.35, cuts=5)
    face = Surface(head)

    def muzzle(phi, elev, out=0.0):
        """The point of the face phi degrees round from straight ahead and elev degrees up, as seen
        from the middle of the head, `out` proud of the surface; and the surface's normal there."""
        p, e = math.radians(phi), math.radians(elev)
        return face.hit((0, 0, 0), (math.sin(p) * math.cos(e), -math.cos(p) * math.cos(e), math.sin(e)), out)

    def smile(phi):
        x = abs(phi) / 38.0
        return -25.0 + 9.0 * x * x

    line = [muzzle(-38 + 76 * k / 12, smile(-38 + 76 * k / 12), 0.006)[0] for k in range(13)]
    n = len(line)
    add("face", tube(line, [0.011 + 0.013 * max(0.0, math.sin(math.pi * i / (n - 1))) ** 0.5 for i in range(n)], segs=5, rings=12), shell, H)
    for sx in (-1, 1):                                                   # nostrils
        p, nrm = muzzle(8 * sx, -6.0)
        add("face", ball((0.05, 0.03, 0.06), cuts=1), shell, H @ seat(p, nrm))
    for sx in (-1, 1):
        p, nrm = face.hit((0.31 * sx, -9.0, 0.10), (0, 1, 0))
        E = seat(p - nrm * 0.02, nrm)
        add("eyes", ball((0.19, 0.12, 0.21), cuts=3), eye, H @ E)
        g = Vector((-0.30, -0.90, 0.30)).normalized()                    # one highlight, on the same side of both eyes
        add("face", ball((0.05, 0.028, 0.05), cuts=2), cream, H @ E @ M((0.095 * g.x, 0.06 * g.y, 0.105 * g.z)))
    add("head", head, skin, H)

    # ---- a seedling growing on the shell ---------------------------------------------------------------
    root, _ = dome(plate_dir(8, 10), -0.04)
    tip = root + Vector((-0.04, 0.02, 0.36))
    add("seedling", tube([root, root + Vector((0.02, 0.0, 0.18)), tip], [0.045, 0.035, 0.03], segs=6, rings=4), leafm)
    add("seedling", leaf(0.46, 0.26), leafm, M(tip - Vector((0, 0, 0.03)), rot=(24, 0, 105)))
    add("seedling", leaf(0.36, 0.21), leafm, M(tip - Vector((0, 0, 0.03)), rot=(38, 0, -70)))

    t.build(SCALE)
    return t


def bake(turtle, texture):
    """Everything but the glossy eyes becomes one textured mesh: the patterns, the tones and soft
    shading in the creases are baked into its colour image. Roblox gets two MeshParts."""
    eyes = [ob for ob in turtle.objects if ob.name.endswith("_Eye")]
    body = kit.bake_texture([ob for ob in turtle.objects if ob not in eyes], texture, name="Turtle_Body",
                            shade=0.5, soften=3, rough=0.85, sheen=0.15)
    for ob in eyes:
        ob.name = ob.data.name = "Turtle_Eyes"
    turtle.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Turtle review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "turtle_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    turtle = build()
    print("triangles by part:", dict(sorted(turtle.tally.items(), key=lambda kv: -kv[1])))
    focus = (HEAD_AT[0] * SCALE, (HEAD_AT[1] - 0.3) * SCALE, (HEAD_AT[2] - 0.1) * SCALE)
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(turtle, os.path.abspath(a.texture))
    tris = turtle.triangles()
    lo, hi = turtle.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(turtle.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(turtle, samples=40, focus=focus)
        look = Vector(focus) + Vector((0.0, 0.3, 0.05))                   # one more camera, tight on the face
        rig.cams["face"] = review._camera("C_face", look + Vector((-0.42, -1.0, 0.12)).normalized() * 4.2, look, 30)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            quick = [("front 3/4", "full"), ("side", "full"), ("face", "full"), ("back 3/4", "full")]
            rig.sheet(os.path.abspath(a.review), quick if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
