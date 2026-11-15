"""SpiritBlob pet: a round violet smoke-wisp spirit, an original design that replaces the game's purple
spiky ghost blob. Built from scratch by script.

    python models/pets/spiritblob.py --review out/spiritblob.png      # render the review sheet
    python models/pets/spiritblob.py --export models/export/spiritblob.fbx

Must-haves, checked in every review:
  1. The same idea as before: a round purple ghost spirit, but an original design that looks like no
     famous character.
  2. A round violet body that trails off into a curling smoke tail, with flowing flame-like wisps on
     top and at the sides instead of spikes; soft smoke swirls painted and pressed into it.
  3. Two calm glowing eyes (pale aqua, gently lidded) and a tiny smile. No wide grin, no red eyes,
     no floating hands.
  4. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 3: flickering licks off the big flame; soft spiral ripples pressed into the body and painted.

Round 2: one big swept-back flame with two curls and trailing side smoke (the first crown of points read as ears or spikes); smooth spiral bands instead of crack-like grooves; smaller aqua eyes with less glow.

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




# ---- the smoke-wisp spirit -------------------------------------------------------------------------

NAME = "SpiritBlob"
COL = {"violet": hexc("#7146B8"), "lilac": hexc("#B394EC"), "pale": hexc("#E3D2FF"), "deep": hexc("#3E2578"),
       "indigo": hexc("#2C1A5C"), "blush": hexc("#D88CD8"), "mouth": hexc("#2A1446")}
SCALE = 1.0
BAKE = {"shade": 0.4, "rough": 0.9}
C0 = Vector((0, 0, 1.75))                    # body centre
R0 = 0.88
FACE = C0 + Vector((0, -0.75, 0.0))
FOCUS = FACE
FACE_DIST = 4.0


def build():
    smoke_m = painted("Smoke", dict(strength=0.07, mottle=0.12, fine=18.0, length=3.0), rough=0.9)
    glow = kit.material("GLOW_Spirit", "#8FE6F6", rough=0.4, emit=1.6)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def flame(pts, r0, power=1.0):
        return loft([Vector(p) for p in pts], lambda t: r0 * (1 - t) ** power + 0.006, segs=12, rings=16)

    # ---- one fused body: the round spirit, its crown of wisps, side wisps and smoke tail ------------------
    clay = [ell(C0, (R0, R0 * 0.95, R0 * 0.98)),
            ell(C0 + Vector((0, 0.05, -0.45)), (0.7, 0.66, 0.5)),
            flame([C0 + Vector((0, 0.15, -0.7)), Vector((0.12, 0.4, 0.7)), Vector((0.32, 0.62, 0.32)), Vector((0.18, 0.86, 0.1)), Vector((-0.12, 0.9, 0.02))], 0.5, 0.9)]
    # one big flame sweeping up and back off the crown, with two smaller curls behind it
    clay.append(flame([C0 + Vector((0, -0.05, 0.62)), C0 + Vector((0.0, 0.12, 1.08)), C0 + Vector((0.06, 0.42, 1.38)),
                       C0 + Vector((0.0, 0.72, 1.48)), C0 + Vector((-0.06, 0.92, 1.36))], 0.5, 1.15))
    for s_ in (-1, 1):                                                      # licks flickering off the big flame
        clay.append(flame([C0 + Vector((0.16 * s_, 0.0, 0.85)), C0 + Vector((0.3 * s_, 0.1, 1.1)), C0 + Vector((0.34 * s_, 0.3, 1.3)),
                           C0 + Vector((0.26 * s_, 0.42, 1.36))], 0.17, 1.1))
        clay.append(flame([C0 + Vector((0.1 * s_, 0.42, 1.1)), C0 + Vector((0.22 * s_, 0.7, 1.25)), C0 + Vector((0.2 * s_, 0.95, 1.2))], 0.15, 1.1))
    for s_ in (-1, 1):
        clay.append(flame([C0 + Vector((0.3 * s_, 0.25, 0.6)), C0 + Vector((0.48 * s_, 0.55, 0.88)),
                           C0 + Vector((0.58 * s_, 0.88, 0.92)), C0 + Vector((0.5 * s_, 1.08, 0.78))], 0.3, 1.1))
        clay.append(flame([C0 + Vector((0.7 * s_, 0.15, -0.22)), C0 + Vector((1.0 * s_, 0.5, -0.38)),       # smoke trailing back
                           C0 + Vector((1.04 * s_, 0.86, -0.25)), C0 + Vector((0.9 * s_, 1.06, -0.04))], 0.24, 1.0))
    skin = fuse(join(clay), voxel=0.022, iterations=4)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit(C0 + Vector((0.27 * s, -3, 0.08))) for s in (-1, 1)]
    smile = [hit(C0 + Vector((x, -3, -0.2 + 1.6 * x * x)))[0] for x in (-0.08, -0.04, 0.0, 0.04, 0.08)]

    def wisp(co):
        """-1..1: soft smoke bands spiralling up round the body, wobbled by noise."""
        a = math.atan2(co.y - C0.y, co.x - C0.x)
        return math.sin(a * 2 + co.z * 4.5 + 1.2 * noise.noise(co * 1.6))

    def carve(co, n):
        d = n * 0.028 * wisp(co) * smooth((co - FACE).length, 0.35, 0.6)
        for e, en in eyes:
            d -= en * 0.035 * (1 - smooth((co - e).length, 0.12, 0.2))
        if co.y < -0.5:
            d -= n * 0.016 * (1 - smooth(poly_dist(co, smile), 0.006, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5200, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - FACE).length, 0.25, 0.55)), factor=1.0)

    def smoke_colour(co, n, g=0.0):
        h = co.z
        col = mix(COL["deep"], COL["violet"], smooth(h, 0.4, 1.5))
        col = mix(col, COL["lilac"], 0.55 * smooth(h, 1.9, 2.9) + 0.25 * smooth(-n.y, 0.3, 1.0) * smooth(h, 1.2, 1.9))
        col = mix(col, COL["pale"], 0.85 * smooth(h, 2.85, 3.3))                # pale flame tips
        col = mix(col, COL["indigo"], 0.5 * smooth(h, 0.7, 0.1))
        w = wisp(co)
        away = smooth((co - FACE).length, 0.35, 0.6)
        col = mix(col, COL["lilac"], 0.45 * smooth(w, 0.4, 0.95) * away)
        col = mix(col, COL["pale"], 0.3 * smooth(w, 0.85, 1.0) * away)
        col = mix(col, COL["deep"], 0.35 * smooth(w, -0.3, -0.95) * away)
        if co.y < -0.5:
            for s in (-1, 1):
                b = (co - (C0 + Vector((0.42 * s, -0.7, -0.14)))) * Vector((1.0, 1.0, 1.4))
                col = mix(col, COL["blush"], 0.5 * (1 - smooth(b.length, 0.04, 0.12)))
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.007, 0.018))
        return col
    add("skin", skin, smoke_m, smoke_colour)

    # ---- calm glowing eyes: soft ovals with a gently lidded top ------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        eye = ell((0, 0, 0), (0.085, 0.12, 0.045), cuts=3)
        for v in eye.verts:
            if v.co.y > 0.04:                                    # flatten the top into a calm, lidded line
                v.co.y = 0.04 + (v.co.y - 0.04) * 0.25
        eye.transform(M(rot=(0, 0, -8 * s)))
        facing(eye, e - en * 0.005, en)
        add("eyes", eye, glow)
    for at, r in ((Vector((0.55, 1.0, 0.75)), 0.06), (Vector((-0.42, 1.05, 0.45)), 0.045), (Vector((1.3, 0.75, 1.75)), 0.04)):
        add("motes", ell(at, (r, r, r), cuts=2), glow)

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
