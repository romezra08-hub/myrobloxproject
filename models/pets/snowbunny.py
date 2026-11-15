"""SnowBunny pet: a fluffy white bunny, remade from the game's white blocky rabbit with long ears. Built from
scratch by script.

    python models/pets/snowbunny.py --review out/snowbunny.png      # render the review sheet
    python models/pets/snowbunny.py --export models/export/snowbunny.fbx

Must-haves, checked in every review:
  1. The same creature: a white rabbit on all fours with long upright ears with pink insides.
  2. Soft natural fur: a fluffy outline (cheek, chest and haunch tufts) and fine painted fur, snowy
     white with cool shadows.
  3. Long ears with pink insides.
  4. A sweet face with dark glossy eyes, a small pink nose and a little mouth.
  5. A round fluffy tail.
  6. Clearly different from the crochet Bunny pet: a natural crouched rabbit with real fur, no yarn,
     no scarf, not sitting up like a toy.
  7. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 3: more triangles on the head so its outline is round; a rounder pompom tail; haunch tufts higher.

Round 2: smaller eyes set deeper (they bulged); thicker, shorter front legs under a fuller chest.

Round 1: first build.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402



# ---- helpers ------------------------------------------------------------------------------------

def smooth(x, a, b):
    """0 at a, 1 at b, smooth in between (a may be larger than b)."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def hexc(h):
    return kit.srgb(h)


def _object(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    old = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(me)
    return bm


def fuse(bm, voxel=0.025, factor=0.5, iterations=2):
    """Remesh a closed shape into an even skin of small faces (a voxel remesh), so it can be sculpted."""
    ob = _object(bm, "fuse")
    bm.free()
    r = ob.modifiers.new("r", 'REMESH')
    r.mode, r.voxel_size, r.adaptivity = 'VOXEL', voxel, 0.0
    if iterations:
        s = ob.modifiers.new("s", 'SMOOTH')
        s.factor, s.iterations = factor, iterations
    return _evaluated(ob)


def decimate(bm, target, keep=None, factor=2.0):
    """Bring a dense skin down to about `target` triangles. keep(co) -> 0..1 marks where to keep
    more of the detail (the face), so its small forms do not turn into polygons."""
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    ob = _object(bm, "dec")
    bm.free()
    if tris > target:
        d = ob.modifiers.new("d", 'DECIMATE')
        d.ratio = target / tris
        d.use_collapse_triangulate = True
        if keep:
            vg = ob.vertex_groups.new(name="keep")
            for v in ob.data.vertices:
                w = keep(v.co)
                if w > 0:
                    vg.add([v.index], w, 'REPLACE')
            d.vertex_group, d.invert_vertex_group, d.vertex_group_factor = "keep", True, factor
    out = _evaluated(ob)
    bmesh.ops.triangulate(out, faces=out.faces[:])
    return out


def sculpt(bm, fn):
    """Move every vertex by fn(co, normal) -> Vector."""
    bm.normal_update()
    moves = [fn(v.co.copy(), v.normal.copy()) for v in bm.verts]
    for v, d in zip(bm.verts, moves):
        if d is not None:
            v.co += d
    bm.normal_update()
    return bm


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length


def poly_dist(p, pts):
    return min(seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


def paint(bm, fn):
    """Give every vertex the colour fn(co, normal, g) -> linear rgb, in the attribute 'col'.
    g is the vertex float layer 'g' when the shape has one (0 root to 1 tip), else 0."""
    bm.normal_update()
    lay = bm.verts.layers.float_color.get("col") or bm.verts.layers.float_color.new("col")
    lg = bm.verts.layers.float.get("g")
    for v in bm.verts:
        v[lay] = (*fn(v.co, v.normal, v[lg] if lg else 0.0), 1.0)
    return bm


def flat_paint(bm, rgb):
    return paint(bm, lambda co, n, g: rgb)


def ell(c, r, rot=(0, 0, 0), cuts=4):
    """An ellipsoid with radii r."""
    bm = kit.ball(tuple(2 * x for x in r), cuts=cuts)
    bm.transform(M(c, rot=rot))
    return bm


def facing(bm, at, normal, up=(0, 0, 1)):
    """Turn a shape built round the origin so its local +Z points along `normal`, then move it to `at`."""
    n = Vector(normal).normalized()
    q = n.to_track_quat('Z', 'Y')
    bm.transform(M(at) @ q.to_matrix().to_4x4())
    return bm


def resample(profile, n):
    """Catmull-Rom through (r, z) points, n points out."""
    pts = [Vector(p) for p in profile]
    return [tuple(kit._spline(pts, i / (n - 1) * (len(pts) - 1))) for i in range(n)]


def lathe(profile, segs=48, closed=False):
    """A surface of revolution round the z axis through (r, z) points; r=0 at an end makes a pole.
    Each vertex keeps 'g', how far along the profile it is (0 to 1)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    rings = []
    n = len(profile)
    for i, (r, z) in enumerate(profile):
        if r <= 1e-6:
            v = bm.verts.new((0, 0, z))
            v[lg] = i / (n - 1)
            rings.append([v])
            continue
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), z))
            v[lg] = i / (n - 1)
            ring.append(v)
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for j in range(segs):
                bm.faces.new((a[0], b[(j + 1) % segs], b[j]))
        elif len(b) == 1:
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
        else:
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def loft(points, rfun, segs=12, rings=24, flat=1.0):
    """Circles along a smooth path through `points`; rfun(t) gives the radius at t (0 to 1).
    Each vertex keeps 'g' = t, for painting."""
    pts = [Vector(p) for p in points]
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    tangent = (path[1] - path[0]).normalized()
    normal = tangent.orthogonal().normalized()
    loops = []
    for i, p in enumerate(path):
        new = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        axis = tangent.cross(new)
        if axis.length > 1e-6:
            normal = Matrix.Rotation(tangent.angle(new), 3, axis.normalized()) @ normal
        tangent = new
        side = tangent.cross(normal).normalized()
        t = i / rings
        r = max(rfun(t), 1e-4)
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            v = bm.verts.new(p + (normal * math.cos(a) + side * math.sin(a) * flat) * r)
            v[lg] = t
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, t in ((loops[0], 0.0), (loops[-1], 1.0)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        c[lg] = t
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _ops(tree):
    new, link = tree.nodes.new, tree.links.new

    def attr(name, out="Color"):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs[out]
    return new, link, attr


def painted(name, streak, rough=0.9):
    """The vertex paint 'col' under kit.furry's fine streaks and mottling."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, **streak)
    new, link, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col"), hsv.inputs["Color"])
    return m


def join(bms):
    out = bmesh.new()
    for b in bms:
        tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(tmp)
        b.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return out




# ---- the snow bunny --------------------------------------------------------------------------------

NAME = "SnowBunny"
COL = {"fur": hexc("#F6F6F2"), "shade": hexc("#D6DCE6"), "deep": hexc("#B9C2D0"), "ear_in": hexc("#F2A9B8"),
       "ear_dk": hexc("#DA8C9E"), "nose": hexc("#E88A9C"), "mouth": hexc("#9A6470"), "white": hexc("#FFFFFF")}
SCALE = 1.15
BAKE = {"shade": 0.42, "rough": 0.92}
HEAD = Vector((0, -0.62, 1.52))
HEAD_M = M(HEAD, rot=(-6, 5, 0))
FACE = Vector((0, -1.0, 1.5)) * SCALE
FOCUS = FACE
FACE_DIST = 4.4


def build():
    fur_m = painted("Fur", dict(strength=0.3, mottle=0.1, fine=50.0, length=4.5), rough=0.95)
    eye_m = kit.material("Eyes", "#1A1212", rough=0.06)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def tuft(at, d, length=0.14, r=0.06):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.02))], lambda t: r * (1 - t) ** 0.9 + 0.006, segs=8, rings=5)

    def hd(p):
        return HEAD_M @ Vector(p)

    # ---- one fused skin: crouched body, haunches, feet, head, tufts and tail -------------------------
    clay = [ell((0, 0.18, 0.72), (0.6, 0.85, 0.6)),
            ell((0, -0.38, 0.8), (0.5, 0.46, 0.6)),                         # chest
            ell(hd((0, 0, 0)), (0.44, 0.42, 0.41)),
            ell(hd((0, -0.28, -0.12)), (0.25, 0.22, 0.2)),                  # muzzle
            ell(hd((0, 0.15, -0.3)), (0.32, 0.3, 0.3))]                     # neck
    for s in (-1, 1):
        clay += [ell(hd((0.1 * s, -0.36, -0.12)), (0.13, 0.12, 0.11)),      # muzzle puffs
                 ell(hd((0.25 * s, -0.12, -0.1)), (0.18, 0.17, 0.17)),      # cheeks
                 ell((0.4 * s, 0.42, 0.55), (0.3, 0.46, 0.42)),             # haunches
                 ell((0.42 * s, 0.3, 0.09), (0.17, 0.42, 0.1)),             # long hind feet
                 loft([(0.24 * s, -0.52, 0.6), (0.24 * s, -0.62, 0.3), (0.23 * s, -0.68, 0.1)], lambda t: lerp(0.16, 0.13, t), segs=10, rings=5),
                 ell((0.23 * s, -0.75, 0.08), (0.14, 0.18, 0.09))]          # front paws
        for k in range(3):                                                   # cheek fluff
            clay.append(tuft(hd((0.34 * s, -0.08 + 0.07 * k, -0.14 - 0.05 * k)), R @ Vector((s, 0.3, -0.5 - 0.2 * k)), length=0.13, r=0.06))
        for k in range(3):                                                   # fluffy haunches
            clay.append(tuft((0.6 * s, 0.3 + 0.15 * k, 0.75 - 0.05 * k), (s, 0.35, -0.5), length=0.11, r=0.055))
    for k in range(9):                                                       # chest ruff
        x = -0.36 + 0.09 * k
        clay.append(tuft((x, -0.72 + 0.25 * abs(x), 1.05 - 0.1 * abs(x) + 0.03 * math.sin(k * 2.1)), (0.5 * x, -0.6, -0.8), length=0.14, r=0.065))
    tail_c = Vector((0, 1.0, 0.68))
    clay.append(ell(tail_c + Vector((0, 0.04, 0.02)), (0.24, 0.22, 0.24)))
    for k in range(10):                                                      # a pompom of fluff
        a, b = k * 2.4, math.acos(1 - 2 * (k + 0.5) / 10)
        d = Vector((math.sin(b) * math.cos(a), math.sin(b) * math.sin(a) * 0.8 + 0.3, math.cos(b)))
        clay.append(tuft(tail_c + Vector((0, 0.04, 0.02)) + d * 0.16, d, length=0.09, r=0.07))
    skin = fuse(join(clay), voxel=0.021, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.22 * s, -1.5, 0.08)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.05)), fwd)
    mouth = [[hit(hd((0, -1.5, -0.08)), fwd)[0], hit(hd((0, -1.5, -0.16)), fwd)[0]]]
    for s in (-1, 1):
        mouth.append([hit(hd((0, -1.5, -0.16)), fwd)[0], hit(hd((0.06 * s, -1.5, -0.2)), fwd)[0], hit(hd((0.11 * s, -1.5, -0.18)), fwd)[0]])

    def carve(co, n):
        d = n * 0.015 * noise.noise(Vector((co.x * 10, co.y * 10, co.z * 2.5)))
        for e, en in eyes:
            d -= en * 0.035 * (1 - smooth((co - e).length, 0.07, 0.13))
        if (co - nose_at).length < 0.35:
            d -= n * 0.014 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.006, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6500, keep=lambda co: max(0.75 * (1 - smooth((Vector(co) - hd((0, -0.3, -0.05))).length, 0.25, 0.5)),
                                                    0.45 * (1 - smooth((Vector(co) - HEAD).length, 0.4, 0.6))), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(COL["shade"], COL["fur"], smooth(n.z, -0.4, 0.5))
        col = mix(col, COL["deep"], 0.35 * smooth(co.z, 0.25, 0.05))
        col = mix(col, COL["shade"], 0.25 * smooth(noise.noise(Vector((co.x * 8, co.y * 8, co.z * 2))), 0.2, 0.6))
        if (co - nose_at).length < 0.35:
            col = mix(col, COL["mouth"], 1 - smooth(min(poly_dist(co, m) for m in mouth), 0.006, 0.016))
        return col
    add("skin", skin, fur_m, fur_colour)

    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.085, 0.097, 0.05), cuts=3), e - en * 0.025, en), eye_m)
        add("glints", ell(e + en * 0.02 + R @ Vector((-0.026, 0, 0.034)), (0.024, 0.017, 0.024), cuts=1), fur_m, COL["white"])
        add("glints", ell(e + en * 0.024 + R @ Vector((0.024, 0, -0.03)), (0.01, 0.008, 0.01), cuts=1), fur_m, COL["white"])
    nose = ell((0, 0, 0), (0.07, 0.04, 0.05), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.55 + 0.45 * smooth(v.co.z, -0.05, 0.05)                  # a soft upside-down triangle
    nose.transform(M(nose_at) @ R.to_4x4())
    add("nose", nose, fur_m, COL["nose"])

    # long ears with pink insides
    for s, lean in ((-1, 0.0), (1, 0.08)):
        root = hd((0.15 * s, 0.02, 0.3))
        pts = [root, root + Vector((0.05 * s, 0.03, 0.32)), root + Vector((0.11 * s, 0.07 + lean, 0.68)), root + Vector((0.16 * s, 0.12 + lean * 2, 0.98))]
        ear = loft(pts, lambda t: 0.15 * math.sin(math.pi * min(0.25 + t * 0.85, 1.0)) ** 0.6 + 0.02, segs=12, rings=14, flat=0.42)
        # cup the front: pull the front-facing side in a little
        for v in ear.verts:
            g = v[ear.verts.layers.float["g"]]
            off = v.co - kit._spline(pts, g * 3)
            if off.y < 0:
                v.co.y -= off.y * 0.5 * smooth(g, 0.05, 0.25) * smooth(g, 1.0, 0.85)

        def ear_col(co, n, g, s=s):
            col = mix(COL["shade"], COL["fur"], smooth(n.z, -0.4, 0.5))
            inner = smooth(-n.y, 0.3, 0.75) * smooth(g, 0.06, 0.2) * smooth(g, 0.97, 0.85)
            pink = mix(COL["ear_in"], COL["ear_dk"], 0.4 * smooth(abs(n.x), 0.0, 0.5))
            return mix(col, pink, 0.9 * inner)
        add("ears", ear, fur_m, ear_col)

    lowest = min(v.co.z for bm, _ in c.parts.values() for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    parts = [ob for ob in c.objects if ob not in glow and ob not in eyes]
    if "before_bake" in globals():
        before_bake(parts)
    body = kit.bake_texture(parts, texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
    if "after_bake" in globals():
        after_bake(body)
    out = [body]
    for group, label in ((glow, "GLOW"), (eyes, "Eyes")):
        if not group:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for ob in group:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = pre + label
        out.append(g)
    c.objects = out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,front,side,back 3/4")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default=NAME + " review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", NAME.lower() + "_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    c = build()
    print("triangles by part:", dict(sorted(c.tally.items(), key=lambda kv: -kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(c, os.path.abspath(a.texture))
    tris = c.triangles()
    lo, hi = c.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(c.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(c, samples=a.samples, focus=FOCUS)
        head = Vector(FACE)
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * FACE_DIST, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * FACE_DIST * 0.94, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
