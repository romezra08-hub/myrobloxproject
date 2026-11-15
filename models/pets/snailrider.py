"""SnailRider pet: a charming snail cyclist, remade from the game's green snail with an orange shell on a
red bicycle. Built from scratch by script.

    python models/pets/snailrider.py --review out/snailrider.png      # render the review sheet
    python models/pets/snailrider.py --export models/export/snailrider.fbx

Must-haves, checked in every review:
  1. The same creature: a green snail with an orange shell riding a red bicycle.
  2. A glossy orange spiral shell with growth lines.
  3. A properly built little red bicycle: tyres, rims, spokes, frame tubes, fork, handlebars, saddle,
     cranks and pedals.
  4. A happy face with eyes on stalks.
  5. Matte painted textures with crease shading; under 5 studs long; Body under 9k triangles.
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




# ---- the snail cyclist -----------------------------------------------------------------------------

NAME = "SnailRider"
COL = {"skin": hexc("#6FC46C"), "skin_lt": hexc("#B4E08E"), "skin_dk": hexc("#3F8E4E"), "blush": hexc("#F08C86"),
       "mouth": hexc("#5A1E22"), "pupil": hexc("#141012"), "white": hexc("#FFFFFF"),
       "shell": hexc("#EE8424"), "shell_lt": hexc("#F8B648"), "shell_dk": hexc("#B4521A"), "shell_hi": hexc("#FFE0A0"),
       "frame": hexc("#D3302B"), "frame_dk": hexc("#981E1C"), "tyre": hexc("#26262A"), "steel": hexc("#C8CCD2"),
       "steel_dk": hexc("#7E838C"), "saddle": hexc("#3A2A24")}
SCALE = 1.0
BAKE = {"shade": 0.42, "rough": 0.72}
WR = 0.66                                    # wheel radius to the outside of the tyre
FH, RH = Vector((0, -1.25, WR)), Vector((0, 1.25, WR))
BB = Vector((0, 0.1, 0.5))
ST, HT, HB = Vector((0, 0.42, 1.38)), Vector((0, -0.82, 1.38)), Vector((0, -0.9, 1.1))
HEAD = Vector((0, -0.58, 2.42))
K = 0.82                                     # the bicycle is built at full size, then scaled down by K
SN = 1.2                                     # the snail is scaled up by SN about A0, which lands on A1
A0, A1 = Vector((0, 0.35, 1.42)), Vector((0, 0.4, 1.42 * K))
SNAIL_XF = M(A1) @ M(scale=SN) @ M(-A0)
FACE = SNAIL_XF @ (HEAD + Vector((0, -0.1, 0.15)))
FOCUS = FACE
FACE_DIST = 3.6


def skin_mat(name, rough=0.85):
    """Vertex paint under a fine pebbled skin (kit.scaly with soft joins)."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=0.035, joins=0.07, vary=0.07, rough=rough)
    new, link, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col"), hsv.inputs["Color"])
    return m


def rod(a, b, r, segs=8):
    return loft([Vector(a), (Vector(a) + Vector(b)) / 2, Vector(b)], lambda t: r, segs=segs, rings=2)


def torus(centre, axis, R, r, segs=32, sides=8):
    ring = lathe([(R + r * math.cos(t), r * math.sin(t)) for t in (2 * math.pi * j / sides for j in range(sides))], segs=segs, closed=True)
    return facing(ring, Vector(centre), Vector(axis))


def build():
    skin_m = skin_mat("Skin")
    shell_m = painted("Shell", dict(strength=0.05, mottle=0.06, fine=30.0, length=2.0), rough=0.6)
    bike_m = painted("Bike", dict(strength=0.02, mottle=0.04, fine=20.0, length=2.0), rough=0.6)
    eye_m = kit.material("Eyes", "#F4F3EC", rough=0.08)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None, xf=None):
        if col is not None:
            if callable(col):
                paint(bm, col)
            else:
                flat_paint(bm, col)
        bm.transform(xf if xf is not None else (SNAIL_XF if mat in (skin_m, shell_m, eye_m) else M(scale=K)))
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def metal(base, dark):
        return lambda co, n, g: mix(base, dark, 0.45 * smooth(-n.z, -0.2, 0.9))

    # ---- the bicycle -------------------------------------------------------------------------------------
    for hub in (FH, RH):
        add("tyres", torus(hub, (1, 0, 0), WR - 0.065, 0.065, segs=28, sides=6), bike_m, metal(COL["tyre"], hexc("#141416")))
        add("rims", torus(hub, (1, 0, 0), WR - 0.135, 0.022, segs=28, sides=4), bike_m, metal(COL["frame"], COL["frame_dk"]))
        add("hubs", facing(lathe([(0.0, -0.07), (0.04, -0.07), (0.05, -0.05), (0.035, 0.0), (0.05, 0.05), (0.04, 0.07), (0.0, 0.07)], segs=10), hub, (1, 0, 0)),
            bike_m, metal(COL["steel"], COL["steel_dk"]))
        for k in range(14):
            a = 2 * math.pi * k / 14
            side = 0.045 if k % 2 else -0.045
            rim = hub + Vector((0, math.cos(a), math.sin(a))) * (WR - 0.15)
            add("spokes", loft([hub + Vector((side, 0, 0)) + Vector((0, math.cos(a + 0.35), math.sin(a + 0.35))) * 0.035, rim],
                               lambda t: 0.011, segs=4, rings=1), bike_m, COL["steel"])
    red = metal(COL["frame"], COL["frame_dk"])
    add("frame", rod(ST + Vector((0, 0.02, 0.05)), HT + Vector((0, 0, -0.02)), 0.048), bike_m, red)       # top tube
    add("frame", rod(BB, HB, 0.055), bike_m, red)                                                         # down tube
    add("frame", rod(BB, ST + Vector((0, 0.02, 0.06)), 0.05), bike_m, red)                                # seat tube
    add("frame", rod(HB + Vector((0, 0.02, -0.04)), HT + Vector((0, -0.01, 0.1)), 0.06), bike_m, red)     # head tube
    for s in (-1, 1):
        add("frame", rod(BB + Vector((0.04 * s, 0, 0)), RH + Vector((0.055 * s, 0, 0)), 0.032), bike_m, red)       # chain stays
        add("frame", rod(ST + Vector((0.03 * s, 0, -0.04)), RH + Vector((0.055 * s, 0, 0)), 0.03), bike_m, red)    # seat stays
        add("frame", loft([HB + Vector((0.06 * s, 0, 0)), HB.lerp(FH, 0.55) + Vector((0.07 * s, -0.04, 0)), FH + Vector((0.06 * s, 0, 0))],
                          lambda t: lerp(0.04, 0.028, t), segs=8, rings=6), bike_m, red)                             # fork blades
    add("frame", facing(ell((0, 0, 0), (0.1, 0.07, 0.05), cuts=2), HB + Vector((0, 0, -0.03)), (0, 0, 1)), bike_m, red)   # fork crown
    # stem and handlebars
    stem_top = HT + Vector((0, 0.04, 0.26))
    add("bars", rod(HT + Vector((0, 0, 0.05)), stem_top, 0.032), bike_m, metal(COL["steel"], COL["steel_dk"]))
    bar = [Vector((-0.4, -0.6, 1.72)), Vector((-0.24, -0.76, 1.66)), Vector((0, -0.8, stem_top.z)), Vector((0.24, -0.76, 1.66)), Vector((0.4, -0.6, 1.72))]
    add("bars", loft(bar, lambda t: 0.026, segs=8, rings=16), bike_m, metal(COL["steel"], COL["steel_dk"]))
    for s in (-1, 1):
        g0 = bar[0 if s < 0 else -1]
        add("grips", loft([g0 + Vector((-0.02 * s, -0.04, 0)), g0 + Vector((0.07 * s, 0.1, 0.02))], lambda t: 0.042 - 0.006 * abs(t - 0.5), segs=8, rings=3),
            bike_m, COL["saddle"])
    # bell
    add("bars", facing(lathe([(0.0, 0.0), (0.06, 0.0), (0.055, 0.03), (0.035, 0.06), (0.0, 0.065)], segs=10), Vector((0.2, -0.79, 1.69)), (0, 0, 1)),
        bike_m, metal(hexc("#E8C35A"), hexc("#A07A2A")))
    # saddle and seat post
    add("frame", rod(ST, ST + Vector((0, 0.03, 0.14)), 0.03), bike_m, metal(COL["steel"], COL["steel_dk"]))
    add("saddle", ell(ST + Vector((0, 0.06, 0.18)), (0.12, 0.22, 0.05), cuts=2), bike_m, COL["saddle"])
    # cranks, chainring, pedals, chain
    add("drive", facing(lathe([(0.0, -0.012), (0.17, -0.012), (0.17, 0.012), (0.0, 0.012)], segs=20), BB + Vector((0.09, 0, 0)), (1, 0, 0)),
        bike_m, metal(COL["steel"], COL["steel_dk"]))
    add("drive", facing(lathe([(0.0, -0.01), (0.05, -0.01), (0.05, 0.01), (0.0, 0.01)], segs=10), RH + Vector((0.09, 0, 0)), (1, 0, 0)),
        bike_m, metal(COL["steel"], COL["steel_dk"]))
    add("drive", rod(BB + Vector((0.1, 0, 0.17)), RH + Vector((0.1, 0, 0.05)), 0.012, segs=4), bike_m, COL["steel_dk"])
    add("drive", rod(BB + Vector((0.1, 0, -0.17)), RH + Vector((0.1, 0, -0.05)), 0.012, segs=4), bike_m, COL["steel_dk"])
    for s, ang in ((1, -35), (-1, 145)):
        tip = BB + Vector((0.13 * s, 0.22 * math.cos(math.radians(ang)), 0.22 * math.sin(math.radians(ang))))
        add("drive", rod(BB + Vector((0.11 * s, 0, 0)), tip, 0.025, segs=6), bike_m, metal(COL["steel"], COL["steel_dk"]))
        ped = kit.rounded_box((0.13, 0.09, 0.035), n=4, cuts=1)
        ped.transform(M(tip + Vector((0.07 * s, 0, 0))))
        add("drive", ped, bike_m, COL["saddle"])

    # ---- the snail: one fused soft body -------------------------------------------------------------------
    path = [Vector((0, 1.24, 1.74)), Vector((0, 1.08, 1.6)), Vector((0, 0.75, 1.63)), Vector((0, 0.3, 1.64)), Vector((0, -0.12, 1.72)),
            Vector((0, -0.42, 1.98)), HEAD + Vector((0, 0.02, -0.12))]
    clay = [loft(path, lambda t: 0.07 + 0.2 * smooth(t, 0.0, 0.35) - 0.02 * smooth(t, 0.6, 1.0), segs=14, rings=20),
            ell(HEAD, (0.3, 0.29, 0.3)),
            ell(HEAD + Vector((0, -0.08, -0.1)), (0.25, 0.22, 0.2)),                  # full lower face
            ell((0, 0.35, 1.5), (0.3, 0.75, 0.1))]                                     # the foot skirt along the frame
    for s in (-1, 1):
        clay.append(ell(HEAD + Vector((0.16 * s, -0.1, -0.08)), (0.14, 0.14, 0.13)))  # cheeks
        stalk = [HEAD + Vector((0.11 * s, -0.04, 0.24)), HEAD + Vector((0.16 * s, -0.08, 0.45)), HEAD + Vector((0.22 * s, -0.14, 0.63))]
        clay.append(loft(stalk, lambda t: lerp(0.07, 0.045, t), segs=10, rings=6))
    skin = fuse(join(clay), voxel=0.02, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    smile = [HEAD + Vector((-0.17, -0.27, -0.03)), HEAD + Vector((-0.1, -0.33, -0.12)), HEAD + Vector((0, -0.34, -0.15)),
             HEAD + Vector((0.1, -0.33, -0.12)), HEAD + Vector((0.17, -0.27, -0.03))]
    smile = [hit(p + Vector((0, -0.6, 0)), (0, 1, 0))[0] or p for p in smile]

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 14)
        if co.y < HEAD.y - 0.1 and abs(co.z - HEAD.z + 0.1) < 0.15:
            d -= n * 0.03 * (1 - smooth(poly_dist(co, smile), 0.01, 0.032))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 3100, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - HEAD).length, 0.3, 0.55)), factor=1.0)

    def skin_colour(co, n, g=0.0):
        col = mix(COL["skin"], COL["skin_lt"], smooth(-n.z, 0.1, 0.7) * 0.8)
        col = mix(col, COL["skin_dk"], 0.35 * smooth(n.z, 0.4, 1.0) * smooth(co.z, 1.9, 1.7))
        col = mix(col, COL["skin_lt"], 0.7 * smooth(co.z, 1.55, 1.45))                         # pale foot rim
        col = mix(col, COL["skin_dk"], 0.25 * smooth(noise.noise(co * 6.0), 0.15, 0.5))
        for s in (-1, 1):
            b = (co - (HEAD + Vector((0.19 * s, -0.24, -0.08)))) * Vector((1.0, 1.4, 1.3))
            col = mix(col, COL["blush"], 0.55 * (1 - smooth(b.length, 0.03, 0.08)))
        col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.011, 0.026))
        return col
    add("skin", skin, skin_m, skin_colour)

    # eyes on the stalk tips
    for s in (-1, 1):
        tip = HEAD + Vector((0.22 * s, -0.16, 0.7))
        add("eyes", ell(tip, (0.11, 0.1, 0.11), cuts=3), eye_m)
        fwd = Vector((0.12 * s, -1, 0.05)).normalized()
        pp = tip + fwd * 0.085
        add("pupils", facing(ell((0, 0, 0), (0.062, 0.07, 0.03), cuts=2), pp, fwd), skin_m, COL["pupil"])
        add("pupils", ell(pp + fwd * 0.024 + Vector((-0.02, 0, 0.028)), (0.02, 0.02, 0.016), cuts=1), skin_m, COL["white"])

    # ---- the spiral shell ---------------------------------------------------------------------------------
    C = Vector((0, 0.6, 2.3))
    SPIN = 255
    turns = 3.1 * math.pi
    n = 56
    pts, rads = [], []
    for i in range(n + 1):
        th = turns * i / n
        R = 0.5 * math.exp(-0.2 * th)
        a = th + math.radians(SPIN)
        pts.append(C + Vector((0, R * math.cos(a), R * math.sin(a))))
        rads.append(0.4 * R + 0.012)
    shell = loft(pts, lambda t: kit._spline(rads, t * n), segs=12, rings=int(n * 1.4))
    for v in shell.verts:
        v.co.x = C.x + (v.co.x - C.x) * 1.75 + 0.08 * v[shell.verts.layers.float["g"]] ** 0.8      # a right-handed spire

    def shell_colour(co, n_, g):
        col = mix(COL["shell"], COL["shell_lt"], smooth(g, 0.3, 1.0))
        band = abs(math.sin(g * 70.0))
        col = mix(col, COL["shell_dk"], 0.35 * (1 - smooth(band, 0.0, 0.25)) * (1 - 0.5 * g))
        dd = co - C
        rr = max(math.hypot(dd.y, dd.z), 1e-4)
        phi = math.atan2(dd.z, dd.y) - math.radians(SPIN)
        w = (math.log(rr / 0.5) / -0.2 - phi) / (2 * math.pi)
        f = w - math.floor(w)                                          # 0 on a whorl's middle line, 0.5 at the seam
        flat = smooth(abs(n_.x), 0.4, 0.8)
        col = mix(col, COL["shell_lt"], 0.55 * flat * (1 - smooth(abs(f - 0.2), 0.03, 0.07)))
        col = mix(col, COL["shell_dk"], 0.7 * flat * (1 - smooth(abs(f - 0.5), 0.02, 0.06)) * smooth(g, 0.98, 0.9))
        side = abs(n_.x)
        col = mix(col, COL["shell_dk"], 0.25 * smooth(side, 0.7, 1.0) * smooth(g, 0.2, 0.0))
        hi = smooth(n_.z, 0.5, 0.8) * smooth(-n_.y, -0.6, 0.1) * smooth(abs(n_.x), 0.85, 0.45)
        col = mix(col, COL["shell_dk"], 0.3 * smooth(-n_.z, 0.2, 0.9))
        return mix(col, COL["shell_hi"], 0.85 * hi)
    add("shell", shell, shell_m, shell_colour)
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow and ob not in eyes], texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
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
