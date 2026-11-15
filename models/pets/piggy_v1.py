"""Piggy pet: a cute round piglet, remade from the game's pink blocky pig. Built from scratch by script.

    python models/pets/piggy.py --review out/piggy.png      # render the review sheet
    python models/pets/piggy.py --export models/export/piggy.fbx

Must-haves, checked in every review:
  1. The same creature: a pink pig, now round and soft instead of blocky.
  2. Soft pink skin with a slight fuzz.
  3. A proper snout with nostrils.
  4. Floppy ears folding forward.
  5. A curly tail.
  6. A happy face: glossy eyes with highlights, blushing cheeks, a smile.
  7. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.
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




# ---- the piglet ------------------------------------------------------------------------------------

NAME = "Piggy"
COL = {"skin": hexc("#F2A3B2"), "skin_lt": hexc("#FAC9D1"), "skin_dk": hexc("#D97E92"), "snout": hexc("#EC8C9E"),
       "nostril": hexc("#8E3A50"), "hoof": hexc("#8A5A5C"), "hoof_lt": hexc("#B07C7C"), "blush": hexc("#EE6F88"),
       "mouth": hexc("#6A2232"), "tongue": hexc("#E2566E"), "white": hexc("#FFFFFF"), "ear_in": hexc("#E68597")}
SCALE = 1.2
BAKE = {"shade": 0.42, "rough": 0.85}
HEAD = Vector((0, -0.72, 1.62))
SNOUT = Vector((0, -1.32, 1.5))
FACE = Vector((0, -1.25, 1.68)) * SCALE
FOCUS = FACE
FACE_DIST = 4.4


def build():
    skin_m = painted("Skin", dict(strength=0.12, mottle=0.1, fine=60.0, length=3.0), rough=0.9)
    eye_m = kit.material("Eyes", "#160E0E", rough=0.06)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    snout = lathe([(0.0, -0.13), (0.2, -0.13), (0.25, -0.1), (0.26, 0.0), (0.24, 0.1), (0.2, 0.13), (0.0, 0.135)], segs=28)
    snout.transform(M(SNOUT, rot=(90, 0, 0), scale=(1.0, 0.82, 1.0)))
    clay = [ell((0, 0.15, 1.08), (0.78, 0.92, 0.72)),                    # round body
            ell((0, -0.35, 1.2), (0.7, 0.5, 0.66)),                       # chest
            ell(HEAD, (0.6, 0.55, 0.56)),
            ell(HEAD + Vector((0, -0.3, -0.18)), (0.4, 0.35, 0.3)),        # muzzle
            snout]
    for s in (-1, 1):
        clay.append(ell(HEAD + Vector((0.32 * s, -0.28, -0.12)), (0.24, 0.22, 0.2)))           # cheeks
        for y, rr in ((-0.42, 0.2), (0.68, 0.21)):
            clay.append(loft([(0.4 * s, y, 0.7), (0.41 * s, y - 0.02, 0.35), (0.41 * s, y - 0.03, 0.12)],
                             lambda t: lerp(rr, rr * 0.82, t), segs=12, rings=5))                # stubby legs
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit(HEAD + Vector((0.26 * s, -3, 0.17))) for s in (-1, 1)]
    nos = [hit(SNOUT + Vector((0.09 * s, -2, 0.0)))[0] for s in (-1, 1)]
    mc = HEAD + Vector((0, -0.55, -0.36))
    smile = [hit(Vector((x, -3, mc.z + 2.2 * x * x)))[0] for x in (-0.17, -0.09, 0.0, 0.09, 0.17)]
    mouth_c = hit(Vector((0, -3, mc.z - 0.01)))[0]

    def mouth_in(co):
        if co.y > mouth_c.y + 0.12:
            return 0.0
        u = co.x / 0.12
        if abs(u) > 1.05:
            return 0.0
        top, bot = mc.z + 0.0 + 0.03 * u * u, mc.z - 0.085 + 0.08 * u * u
        return smooth(co.z, bot - 0.004, bot + 0.012) * smooth(co.z, top + 0.004, top - 0.012) * smooth(abs(u), 1.02, 0.8)

    def carve(co, n):
        d = Vector()
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.08, 0.14))
        for p in nos:
            q = (co - p) * Vector((1 / 0.045, 1.0 / 0.06, 1 / 0.07))
            d += Vector((0, 0.07, 0)) * (1 - smooth(q.length, 0.6, 1.0))
        if co.y < HEAD.y - 0.3:
            d += Vector((0, 0.07, 0)) * mouth_in(co)
            d -= n * 0.016 * (1 - smooth(poly_dist(co, smile), 0.008, 0.024))
        if co.z < 0.16 and n.z < 0.7:                                       # cloven hooves
            for s in (-1, 1):
                if abs(co.x - 0.41 * s) < 0.05 and n.y < 0:
                    d -= n * 0.03 * (1 - smooth(abs(co.x - 0.41 * s), 0.004, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 4400, keep=lambda co: 0.75 * (1 - smooth((Vector(co) - Vector((0, -1.2, 1.55))).length, 0.25, 0.55)), factor=1.0)

    def skin_colour(co, n, g=0.0):
        col = mix(COL["skin"], COL["skin_lt"], 0.45 * smooth(n.z, 0.2, 1.0))
        col = mix(col, COL["skin_dk"], 0.35 * smooth(-n.z, 0.2, 0.9))
        col = mix(col, COL["skin_dk"], 0.15 * smooth(noise.noise(co * 4.0), 0.2, 0.6))
        col = mix(col, COL["hoof"], smooth(co.z, 0.2, 0.14))
        col = mix(col, COL["hoof_lt"], 0.3 * smooth(co.z, 0.18, 0.15) * smooth(co.z, 0.1, 0.14))
        sd = ((co - SNOUT) * Vector((1, 1.0, 1 / 0.82)))
        if co.y < SNOUT.y + 0.12:
            col = mix(col, COL["snout"], smooth(math.hypot(sd.x, sd.z), 0.27, 0.2))
        for p in nos:
            q = (co - p) * Vector((1 / 0.045, 1.0, 1 / 0.07))
            col = mix(col, COL["nostril"], 1 - smooth(Vector((q.x, 0, q.z)).length, 0.7, 1.05))
        if co.y < HEAD.y - 0.25:
            for s in (-1, 1):
                b = (co - (HEAD + Vector((0.4 * s, -0.42, -0.08)))) * Vector((1.0, 1.0, 1.3))
                col = mix(col, COL["blush"], 0.55 * (1 - smooth(b.length, 0.04, 0.13)))
            col = mix(col, COL["mouth"], max(smooth(mouth_in(co), 0.1, 0.5), 1 - smooth(poly_dist(co, smile), 0.008, 0.02)))
        return col
    add("skin", skin, skin_m, skin_colour)

    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.095, 0.11, 0.055), cuts=3), e - en * 0.01, en), eye_m)
        add("glints", ell(e + en * 0.045 + Vector((-0.03, 0, 0.04)), (0.028, 0.02, 0.028), cuts=1), skin_m, COL["white"])
        add("glints", ell(e + en * 0.05 + Vector((0.028, 0, -0.035)), (0.012, 0.01, 0.012), cuts=1), skin_m, COL["white"])
    tg = ell(mouth_c + Vector((0, 0.03, -0.035)), (0.07, 0.06, 0.03), cuts=2)
    add("tongue", tg, skin_m, COL["tongue"])

    # floppy ears folding forward
    for s in (-1, 1):
        root = HEAD + Vector((0.3 * s, 0.05, 0.42))
        pts = [root, root + Vector((0.14 * s, -0.04, 0.16)), root + Vector((0.26 * s, -0.2, 0.18)), root + Vector((0.33 * s, -0.36, 0.06))]
        ear = loft(pts, lambda t: 0.2 * (1 - t) ** 0.7 + 0.03, segs=10, rings=10, flat=0.3)

        def ear_col(co, n, g):
            col = mix(COL["skin"], COL["skin_lt"], 0.4 * smooth(n.z, 0.2, 1.0))
            return mix(col, COL["ear_in"], 0.6 * smooth(-n.z, 0.1, 0.7) * smooth(g, 0.05, 0.3))
        add("ears", ear, skin_m, ear_col)

    # curly tail
    tail = []
    base = Vector((0, 1.02, 1.25))
    for i in range(16):
        t = i / 15
        a = t * 2.4 * math.pi
        r = 0.12 * (1 - 0.45 * t)
        tail.append(base + Vector((r * math.sin(a), 0.08 + 0.18 * t, r * (math.cos(a) - 1) + 0.12 * t)))
    add("tail", loft(tail, lambda t: lerp(0.05, 0.03, t), segs=8, rings=24), skin_m,
        lambda co, n, g: mix(COL["skin"], COL["skin_lt"], 0.4 * smooth(n.z, 0.2, 1.0)))

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
