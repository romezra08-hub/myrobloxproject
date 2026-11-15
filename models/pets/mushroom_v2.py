"""Mushroom pet: a cute forest mushroom, remade from the game's red-and-white spotted mushroom cap creature
with tiny legs. Built from scratch by script.

    python models/pets/mushroom.py --review out/mushroom.png      # render the review sheet
    python models/pets/mushroom.py --export models/export/mushroom.fbx

Must-haves, checked in every review:
  1. The same creature: a big red cap with white spots on a pale stem body with tiny legs.
  2. A glossy red cap with raised white spots and a gently curled rim.
  3. Gills under the cap.
  4. A chunky cream stem body with a friendly face (glossy eyes, blush, smile) and stubby feet.
  5. A little moss and a tiny sprout.
  6. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.
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




# ---- the forest mushroom ---------------------------------------------------------------------------

NAME = "Mushroom"
COL = {"cap": hexc("#D12C26"), "cap_dk": hexc("#8E1A18"), "cap_lt": hexc("#EE5A44"), "cap_hi": hexc("#FFB8A0"),
       "spot": hexc("#FBF6EC"), "spot_dk": hexc("#E2D6C2"), "gill": hexc("#EBDCC0"), "gill_dk": hexc("#C4AD8A"),
       "stem": hexc("#F3EAD6"), "stem_dk": hexc("#D8C8A8"), "blush": hexc("#F2A0A0"), "mouth": hexc("#5A2A22"),
       "white": hexc("#FFFFFF"), "moss": hexc("#5E9A3A"), "moss_lt": hexc("#9CCB5A"), "moss_dk": hexc("#3C6E2A"),
       "leaf": hexc("#7CC24A"), "leaf_dk": hexc("#4E8E30")}
SCALE = 1.0
BAKE = {"shade": 0.45, "rough": 0.75}
CAP_Z = 1.55                                   # underside of the cap where it meets the stem
TILT = M(rot=(-4, 7, 0))                       # the cap sits at a jaunty angle
FACE = Vector((0, -0.7, 0.95))
FOCUS = Vector((0, -0.6, 1.4))
FACE_DIST = 4.2


def build():
    stem_m = painted("Stem", dict(strength=0.1, mottle=0.08, fine=40.0, length=9.0), rough=0.85)
    cap_m = painted("Cap", dict(strength=0.04, mottle=0.1, fine=20.0, length=1.5), rough=0.6)
    moss_m = kit.material("Moss", "#808080", rough=0.95)
    kit.scaly(moss_m, size=0.03, joins=0.3, vary=0.25, rough=0.95)
    _, link, attr = _ops(moss_m.node_tree)
    link(attr("col"), next(n for n in moss_m.node_tree.nodes if n.type == 'HUE_SAT').inputs["Color"])
    eye_m = kit.material("Eyes", "#1E1410", rough=0.06)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- stem body with feet: one fused skin -----------------------------------------------------------
    stem_prof = [(0.0, 0.18), (0.6, 0.2), (0.7, 0.45), (0.68, 0.8), (0.6, 1.2), (0.5, 1.6), (0.0, 1.7)]
    clay = [lathe(resample(stem_prof, 14), segs=32)]
    for s in (-1, 1):
        clay.append(ell((0.32 * s, -0.22, 0.13), (0.24, 0.3, 0.14)))       # stubby feet
        clay.append(ell((0.3 * s, -0.52, 0.85), (0.18, 0.12, 0.14)))        # cheeks
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit((0.24 * s, -3, 1.08)) for s in (-1, 1)]
    smile = [hit((x, -3, 0.82 + 3.0 * x * x))[0] for x in (-0.11, -0.055, 0.0, 0.055, 0.11)]

    def carve(co, n):
        d = Vector()
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.09, 0.15))
        if co.y < -0.4:
            d -= n * 0.02 * (1 - smooth(poly_dist(co, smile), 0.008, 0.026))
        if co.z < 0.3 and n.z < 0.5 and co.y < -0.2:                        # toe creases on the feet
            for s in (-1, 1):
                for dx in (-0.07, 0.07):
                    d -= n * 0.02 * (1 - smooth(abs(co.x - (0.32 * s + dx)), 0.005, 0.02)) * smooth(co.z, 0.24, 0.12)
        return d + n * 0.006 * noise.noise(Vector((co.x * 20, co.y * 20, co.z * 3)))
    sculpt(skin, carve)
    skin = decimate(skin, 2800, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - FACE).length, 0.25, 0.5)), factor=1.0)

    def stem_colour(co, n, g=0.0):
        col = mix(COL["stem_dk"], COL["stem"], smooth(co.z, 0.1, 0.6))
        col = mix(col, COL["stem_dk"], 0.4 * smooth(co.z, 1.3, 1.55))           # shadowed under the cap
        col = mix(col, COL["stem_dk"], 0.3 * smooth(noise.noise(Vector((co.x * 9, co.y * 9, co.z * 1.5))), 0.2, 0.6))
        if co.y < -0.3:
            for s in (-1, 1):
                b = (co - Vector((0.36 * s, -0.6, 0.86))) * Vector((1.0, 1.0, 1.3))
                col = mix(col, COL["blush"], 0.6 * (1 - smooth(b.length, 0.04, 0.12)))
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.01, 0.024))
        return col
    add("stem", skin, stem_m, stem_colour)

    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.1, 0.12, 0.06), cuts=3), e - en * 0.01, en), eye_m)
        add("glints", ell(e + en * 0.05 + Vector((-0.03, 0, 0.045)), (0.03, 0.02, 0.03), cuts=1), stem_m, COL["white"])
        add("glints", ell(e + en * 0.055 + Vector((0.03, 0, -0.035)), (0.013, 0.01, 0.013), cuts=1), stem_m, COL["white"])

    # ---- the cap: a lathed dome with a curled rim and gills underneath ---------------------------------------
    NG = 28                                                   # gills
    prof = [(0.0, 0.08), (0.42, 0.06), (0.75, 0.02), (1.08, -0.06), (1.3, -0.1), (1.42, -0.04), (1.46, 0.08),
            (1.42, 0.3), (1.28, 0.62), (1.0, 0.95), (0.6, 1.18), (0.0, 1.26)]
    pts = resample(prof, 22)
    cap = lathe(pts, segs=NG * 2)
    lg = cap.verts.layers.float["g"]
    for v in cap.verts:
        r = math.hypot(v.co.x, v.co.y)
        a = math.atan2(v.co.y, v.co.x)
        under = v[lg] < 0.32
        if under and 0.45 < r < 1.24:                         # radial gill ridges
            k = smooth(r, 0.45, 0.6) * smooth(r, 1.24, 1.08)
            v.co.z -= 0.05 * k * (0.5 + 0.5 * math.cos(a * NG))
        v.co.z += 0.03 * noise.noise(Vector((v.co.x * 1.6, v.co.y * 1.6, 3.0)))
        v.co.x *= 1 + 0.03 * noise.noise(Vector((a * 2, 1.0, 0.0)))
    cap.transform(M((0, 0, CAP_Z)) @ TILT)
    capc = Vector((0, 0, CAP_Z))

    def cap_colour(co, n, g):
        if g < 0.32:
            col = mix(COL["gill"], COL["gill_dk"], 0.5 * smooth(abs(math.cos(math.atan2(co.y, co.x) * NG)), 0.6, 1.0))
            return mix(col, COL["gill_dk"], 0.4 * smooth(g, 0.25, 0.05))
        col = mix(COL["cap_dk"], COL["cap"], smooth(g, 0.34, 0.5))
        col = mix(col, COL["cap_dk"], 0.25 * smooth(noise.noise(co * 3.0), 0.2, 0.6))
        col = mix(col, COL["cap_lt"], 0.35 * smooth(n.z, 0.6, 1.0))
        hi = smooth(n.z, 0.55, 0.85) * smooth(-n.y, -0.2, 0.4) * smooth(n.x, 0.3, -0.3)
        return mix(col, COL["cap_hi"], 0.55 * hi)                     # a soft painted gloss
    ct = BVHTree.FromBMesh(cap)                                  # for laying spots and moss on the dome
    add("cap", cap.copy(), cap_m, cap_colour)

    # raised white spots, laid on the dome
    rng = [(0.25, -0.2, 0.3), (0.72, 0.32, 0.24), (-0.6, -0.15, 0.26), (0.1, -0.85, 0.22), (-0.5, -0.75, 0.17), (0.82, -0.5, 0.2),
           (-1.08, 0.3, 0.16), (0.42, 0.88, 0.2), (-0.3, 0.95, 0.15), (1.12, 0.05, 0.14), (-0.95, -0.62, 0.13), (0.55, -1.08, 0.12),
           (-0.15, 0.4, 0.14), (1.0, 0.72, 0.12)]
    for x, y, r in rng:
        o = TILT @ Vector((x, y, 3.0)) + capc
        loc, nrm, _, _ = ct.ray_cast(o, (TILT.to_3x3() @ Vector((0, 0, -1))))
        if loc is None:
            continue
        sp = ell((0, 0, 0), (r, r * 0.85, 0.04), cuts=1)
        bmesh.ops.subdivide_edges(sp, edges=sp.edges[:], cuts=1, use_grid_fill=True)
        for v in sp.verts:
            q = Vector((v.co.x / r, v.co.y / (r * 0.85), 0))
            if q.length > 1e-3:
                v.co.x, v.co.y = q.normalized().x * r * min(q.length, 1.0) * (1 + 0.12 * math.sin(math.atan2(q.y, q.x) * 3 + x * 7)), \
                    q.normalized().y * r * 0.85 * min(q.length, 1.0) * (1 + 0.12 * math.sin(math.atan2(q.y, q.x) * 3 + x * 7))
        sp = kit.lumpy(sp, 0.01, 9.0, x + y)
        sp.transform(M(rot=(0, 0, x * 90)))
        facing(sp, loc + nrm * 0.005, nrm)
        add("spots", sp, cap_m, lambda co, n, g: mix(COL["spot_dk"], COL["spot"], smooth(n.z, -0.2, 0.7)))

    # ---- moss and a tiny sprout ---------------------------------------------------------------------------
    def moss_colour(co, n, g):
        k = noise.noise(co * 12.0)
        return mix(mix(COL["moss_dk"], COL["moss"], smooth(n.z, -0.3, 0.6)), COL["moss_lt"], 0.5 * smooth(k, 0.1, 0.5))
    sprout_at = None
    for k in range(10):                                               # a mossy patch on the crown of the cap
        a = k * 2.4
        rr = 0.05 + 0.3 * math.sqrt(k / 10)
        x, y = -0.3 + rr * math.cos(a), 0.2 + rr * math.sin(a) * 0.8
        o = TILT @ Vector((x, y, 3.0)) + capc
        loc, nrm, _, _ = ct.ray_cast(o, (TILT.to_3x3() @ Vector((0, 0, -1))))
        if loc is None:
            continue
        if sprout_at is None:
            sprout_at = (loc, nrm)
        sz = 0.11 + 0.03 * math.sin(k * 1.9)
        add("moss", facing(kit.lumpy(ell((0, 0, 0), (sz, sz * 0.9, sz * 0.45), cuts=1), 0.015, 12.0, k), loc, nrm), moss_m, moss_colour)
    for k, (x, y, sz) in enumerate(((0.62, 0.25, 0.17), (0.72, 0.0, 0.13), (0.5, 0.48, 0.14), (0.78, 0.38, 0.1),     # a cushion of moss
                                    (-0.66, 0.3, 0.14), (-0.55, 0.52, 0.11), (-0.72, 0.1, 0.09))):        # against the stem
        add("moss", kit.lumpy(ell((x, y, 0.05), (sz, sz * 0.9, sz * 0.55), cuts=1), 0.015, 12.0, k + 40), moss_m, moss_colour)
    loc, nrm = sprout_at
    top = loc + nrm * 0.32 + Vector((0.03, 0.02, 0))
    add("sprout", loft([loc - nrm * 0.02, loc + nrm * 0.16 + Vector((0.02, 0, 0)), top], lambda t: lerp(0.028, 0.018, t), segs=6, rings=6),
        moss_m, lambda co, n, g: mix(COL["leaf_dk"], COL["leaf"], g))
    for s in (-1, 1):
        leaf = ell((0, 0, 0), (0.13, 0.06, 0.014), cuts=2)
        for v in leaf.verts:
            v.co.z += 0.12 * (v.co.x / 0.13) ** 2 * 0.4 - 0.02 * (v.co.y / 0.06) ** 2
        leaf.transform(M(top + Vector((0.12 * s, 0, 0.02)), rot=(0, -20 * s, 15 * s)))
        add("sprout", leaf, moss_m, lambda co, n, g: mix(COL["leaf_dk"], COL["leaf"], smooth(n.z, 0.0, 0.9)))
    cap.free()
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
