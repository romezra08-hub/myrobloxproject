"""SkeletonDog pet: a friendly "bone pup", remade from the game's skeleton dog. Built from scratch by
script.

    python models/pets/skeletondog.py --review out/skeletondog.png      # render the review sheet
    python models/pets/skeletondog.py --export models/export/skeletondog.fbx

The original is a white-and-black dog that is a skeleton, ribs and bones showing. The remake keeps
the black and white and the bones, but as a costume print on a happy black pup. Must-haves, checked
in every review:
  1. A black pup standing happy with its tail up: big head, floppy ears, sturdy legs, round paws.
  2. A stylised white bone print laid on the fur like a costume: ribs, spine, hip bones, leg bones and
     tail bones, each with a faint green glow round it. No real exposed bones, no skull face.
  3. A happy face: bright amber eyes with highlights, a white muzzle and blaze, black nose, an open
     smile with the tongue out.
  4. A collar with a little bone-shaped tag.
  5. Matte painted fur with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 4: a breastbone and collarbones printed on the chest, so the bone print reads from straight in
front too.

Round 3: the collar square to the neck (its front was buried in the jaw, so it only showed at the
sides), the tag hanging from its front; a fainter, tighter green glow (the legs read green).

Round 2: scaled up to 3.4 studs; the printed bones flatter (they read as piping), whiter in the
middle with the mint only at the edge, and a stronger green glow round them on the fur; ribs that
arc like a ribcage, wider leg bones with rounder knobs; broader, droopier ears; the collar higher so
it shows in front.

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
from mathutils import Vector, noise  # noqa: E402
from kit import M, Prop  # noqa: E402

NAME = "SkeletonDog"


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
            from mathutils import Matrix
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


def ribbon(tree, guide, wfun, n=8, cols=3, lift=0.008, sink=0.02):
    """A thin printed strip lying on a surface: the points `guide` (near the surface) are pulled onto
    it, and a slab wfun(t) wide is laid along them, `lift` proud of the surface. Each vertex keeps
    'g' = t along and 'h' (0 down the middle, 1 at the edges)."""
    pts = [Vector(p) for p in guide]
    path = [kit._spline(pts, i / n * (len(pts) - 1)) for i in range(n + 1)]
    on = []
    for q in path:
        loc, nrm, _, _ = tree.find_nearest(q)
        on.append((loc, nrm))
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    lh = bm.verts.layers.float.new("h")
    top, bot = [], []
    for i, (p, nrm) in enumerate(on):
        a, b = on[max(i - 1, 0)][0], on[min(i + 1, n)][0]
        tan = (b - a).normalized()
        side = nrm.cross(tan).normalized()
        t = i / n
        w = max(wfun(t), 0.004)
        tr, br = [], []
        for j in range(cols + 1):
            v = j / cols * 2 - 1
            u = bm.verts.new(p + side * v * w / 2 + nrm * lift * (1 - 0.3 * v * v))
            d = bm.verts.new(p + side * v * w / 2 - nrm * sink)
            u[lg] = d[lg] = t
            u[lh] = d[lh] = abs(v)
            tr.append(u)
            br.append(d)
        top.append(tr)
        bot.append(br)
    for i in range(n):
        for j in range(cols):
            bm.faces.new((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]))
            bm.faces.new((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]))
    ring = [(0, j) for j in range(cols + 1)] + [(i, cols) for i in range(1, n + 1)] + \
           [(n, j) for j in range(cols - 1, -1, -1)] + [(i, 0) for i in range(n - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((top[i0][j0], bot[i0][j0], bot[i1][j1], top[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, [p for p, _ in on]


def bone_w(width, knob=1.8, end=0.16):
    """Width along a printed bone: a slim shaft swelling to rounded knobs at both ends."""
    def w(t):
        k = max(1 - t / end, 1 - (1 - t) / end, 0.0)
        return width * (1 + (knob - 1) * math.sin(k * math.pi / 2) ** 0.7) * (0.35 + 0.65 * math.sin(min(t, 1 - t, 0.06) / 0.06 * math.pi / 2))
    return w


# ---- the pup ------------------------------------------------------------------------------------

FUR = {"black": hexc("#17161B"), "sheen": hexc("#33323E"), "white": hexc("#EEEEE8"), "mint": hexc("#B4F2C2"),
       "halo": hexc("#2A6A44"), "mouth": hexc("#4A1418"), "tongue": hexc("#E2647A"), "nose": hexc("#0B0A0C"),
       "collar": hexc("#B3262E"), "pupil": hexc("#0E0806")}
HEAD = Vector((0, -0.85, 2.15))
SCALE = 1.15                               # built at pup size, then scaled up to sit among the other pets


def build():
    from mathutils.bvhtree import BVHTree
    fur_m = painted("Fur", dict(strength=0.2, mottle=0.1, fine=34.0, length=5.0), rough=0.9)
    print_m = painted("BonePrint", dict(strength=0.06, mottle=0.08, fine=40.0, length=3.0), rough=0.9)
    eye_m = kit.material("Eyes", "#E9A23A", rough=0.12)
    glow = kit.material("GLOW_Bone", "#9DFFB4", rough=0.4, emit=1.6)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    tail_pts = [Vector((0, 1.08, 1.38)), Vector((0.02, 1.38, 1.62)), Vector((0.08, 1.5, 1.98)), Vector((0.16, 1.44, 2.25))]
    clay = [ell((0, 0.15, 1.15), (0.5, 0.85, 0.47)), ell((0, -0.42, 1.25), (0.48, 0.42, 0.5)),
            ell((0, 0.72, 1.15), (0.46, 0.45, 0.46)),
            loft([(0, -0.42, 1.4), (0, -0.62, 1.75), (0, -0.75, 1.95)], lambda t: lerp(0.36, 0.33, t), segs=12, rings=6),
            ell(HEAD, (0.5, 0.45, 0.46)),                                       # cranium
            ell((0, -1.3, 2.0), (0.25, 0.32, 0.2)),                             # snout
            ell((0, -1.22, 1.86), (0.21, 0.26, 0.12)),                          # lower jaw
            loft(tail_pts, lambda t: lerp(0.1, 0.055, t), segs=10, rings=10)]
    for s in (-1, 1):
        clay += [ell((0.25 * s, -1.08, 2.0), (0.2, 0.2, 0.18)),                 # cheeks
                 ell((0.3 * s, -0.42, 1.02), (0.22, 0.26, 0.36)),               # shoulders
                 loft([(0.3 * s, -0.48, 0.9), (0.3 * s, -0.52, 0.45), (0.3 * s, -0.55, 0.15)],
                      lambda t: lerp(0.16, 0.13, t), segs=12, rings=6),
                 ell((0.3 * s, -0.66, 0.1), (0.17, 0.22, 0.11)),                # fore paws
                 ell((0.31 * s, 0.72, 0.95), (0.22, 0.34, 0.38)),               # thighs
                 loft([(0.32 * s, 0.85, 0.72), (0.33 * s, 0.95, 0.4), (0.32 * s, 0.86, 0.14)],
                      lambda t: lerp(0.15, 0.12, t), segs=12, rings=6),
                 ell((0.32 * s, 0.78, 0.1), (0.16, 0.21, 0.1))]                 # hind paws
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit((0.22 * s, -2.5, 2.22)) for s in (-1, 1)]
    nose_at, _ = hit((0, -2.5, 2.07))
    mouth_c = Vector((0, nose_at.y + 0.1, 1.86))
    lip = [Vector((-0.2, -1.36, 1.92)), Vector((-0.1, nose_at.y + 0.1, 1.9)), Vector((0, nose_at.y + 0.06, 1.95)),
           Vector((0.1, nose_at.y + 0.1, 1.9)), Vector((0.2, -1.36, 1.92))]

    def carve(co, n):
        d = Vector()
        for p, en in eyes:
            d -= en * 0.04 * (1 - smooth((co - p).length, 0.08, 0.15))
        if co.y < -1.15:
            q = (co - mouth_c) * Vector((1 / 0.15, 1 / 0.14, 1 / 0.055))
            d += Vector((0, 0.12, 0.0)) * (1 - smooth(q.length, 0.6, 1.0))             # the open mouth
            d -= n * 0.02 * (1 - smooth(poly_dist(co, lip), 0.01, 0.03))                # the smile line
        return d
    sculpt(skin, carve)
    tree = BVHTree.FromBMesh(skin)

    # ---- the bone print: guides near the surface, pulled onto it -------------------------------------
    prints = []                                                   # (ribbon, path) for the glow halo
    for s in (-1, 1):
        for k in range(4):
            y0 = -0.5 + 0.21 * k
            guide = []
            for i in range(6):
                phi = math.radians(lerp(14, 104, i / 5))
                guide.append((s * math.sin(phi) * 0.7, y0 + 0.13 * math.sin(math.pi * i / 5) + 0.04 * i / 5, 1.22 + math.cos(phi) * 0.7))
            prints.append(ribbon(tree, guide, bone_w(0.088 - 0.008 * abs(k - 1.5), knob=1.35, end=0.14), n=7))
        prints.append(ribbon(tree, [(s * 0.6, 0.52, 1.42), (s * 0.62, 0.72, 1.38), (s * 0.6, 0.95, 1.22)],
                             lambda t: 0.06 + 0.12 * math.sin(math.pi * min(max(t, 0.0), 1.0)) ** 0.7, n=6))     # hip bones
        for a, b in (((0.52, -0.42, 1.12), (0.45, -0.5, 0.62)), ((0.44, -0.52, 0.55), (0.42, -0.57, 0.2)),
                     ((0.55, 0.7, 1.12), (0.52, 0.86, 0.72)), ((0.47, 0.92, 0.62), (0.45, 0.9, 0.22))):
            ga, gb = Vector((a[0] * s, a[1], a[2])), Vector((b[0] * s, b[1], b[2]))
            prints.append(ribbon(tree, [ga, ga.lerp(gb, 0.5), gb], bone_w(0.08, knob=2.0, end=0.2), n=8))
    prints.append(ribbon(tree, [(0, -0.95, 1.4), (0, -0.92, 1.18), (0, -0.82, 0.95)], bone_w(0.085, knob=1.6, end=0.18), n=6))   # breastbone
    for s in (-1, 1):                                             # collarbones from it out to the shoulders
        prints.append(ribbon(tree, [(0.06 * s, -0.95, 1.42), (0.2 * s, -0.88, 1.43), (0.36 * s, -0.75, 1.36)],
                             bone_w(0.06, knob=1.7, end=0.2), n=5))
    spine = [(0, -0.55, 1.85), (0, -0.2, 1.75), (0, 0.3, 1.72), (0, 0.8, 1.72), (0, 1.05, 1.55)]
    prints.append(ribbon(tree, spine, lambda t: 0.06 + 0.04 * abs(math.sin(t * math.pi * 9)), n=26))
    tail_guide = [p + Vector((0, -0.05, 0.12)) for p in tail_pts]
    prints.append(ribbon(tree, tail_guide, lambda t: (0.05 + 0.03 * abs(math.sin(t * math.pi * 5))) * (1 - 0.4 * t), n=14))
    halo = [p for _, path in prints for p in path]

    def print_colour(co, n, g):
        return FUR["white"]
    for bm, _ in prints:
        lh = bm.verts.layers.float.get("h")
        lay = bm.verts.layers.float_color.new("col")
        for v in bm.verts:
            v[lay] = (*mix(FUR["white"], FUR["mint"], smooth(v[lh], 0.6, 1.0)), 1.0)
        add("bone print", bm, print_m)

    skin = decimate(skin, 4250, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - Vector((0, -1.2, 2.05))).length, 0.35, 0.7)), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(FUR["black"], FUR["sheen"], 0.6 * smooth(n.z, 0.3, 1.0))
        hd = min((co - p).length for p in halo)
        col = mix(col, FUR["halo"], 0.6 * (1 - smooth(hd, 0.04, 0.14)))
        if co.y < -1.0 and co.z > 1.7:                            # white muzzle and blaze
            m = (co - Vector((0, -1.42, 1.96))) * Vector((1.0, 0.9, 1.3))
            blaze = (1 - smooth(abs(co.x), 0.045, 0.075)) * smooth(co.z, 2.05, 2.15) * smooth(co.z, 2.55, 2.4)
            col = mix(col, FUR["white"], max(1 - smooth(m.length, 0.22, 0.28), blaze))
            q = (co - mouth_c) * Vector((1 / 0.15, 1 / 0.14, 1 / 0.055))
            col = mix(col, FUR["mouth"], 1 - smooth(q.length, 0.75, 0.95))
            col = mix(col, FUR["black"], 0.85 * (1 - smooth(poly_dist(co, lip), 0.008, 0.022)))
        return col
    add("skin", paint(skin, fur_colour), fur_m)

    # ---- face: eyes, nose, tongue, ears --------------------------------------------------------------------
    for (p, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.105, 0.115, 0.06), cuts=3), p - en * 0.01, en), eye_m)
        pp = p + en * 0.04
        add("pupils", flat_paint(facing(ell((0, 0, 0), (0.068, 0.075, 0.025), cuts=2), pp, en), FUR["pupil"]), fur_m)
        add("pupils", flat_paint(ell(pp + en * 0.02 + Vector((-0.03, 0, 0.035)), (0.024, 0.024, 0.022), cuts=1), FUR["white"]), fur_m)
    nose = ell((0, 0, 0), (0.1, 0.075, 0.07), cuts=2)
    for v in nose.verts:
        v.co.x *= 1 + 0.3 * smooth(v.co.z, -0.07, 0.07) - 0.3
    nose.transform(M(nose_at + Vector((0, 0.0, 0.01))))
    add("nose", flat_paint(nose, FUR["nose"]), fur_m)
    tongue = loft([mouth_c + Vector((0.0, -0.02, 0.0)), mouth_c + Vector((0.03, -0.11, -0.04)), mouth_c + Vector((0.05, -0.14, -0.15))],
                  lambda t: 0.075 * (0.8 + 0.2 * math.sin(math.pi * t)) * (1 - 0.3 * t ** 3), segs=10, rings=8, flat=0.4)
    add("tongue", paint(tongue, lambda co, n, g: mix(FUR["tongue"], hexc("#B8445A"), 0.4 * (1 - smooth(abs(co.x - 0.03 * g), 0.0, 0.02)))), fur_m)
    for s in (-1, 1):
        root = HEAD + Vector((0.3 * s, 0.05, 0.32))
        ear = loft([root, root + Vector((0.12 * s, -0.04, 0.26)), root + Vector((0.28 * s, -0.16, 0.32)), root + Vector((0.38 * s, -0.3, 0.18))],
                   lambda t: lerp(0.2, 0.07, t ** 1.2), segs=10, rings=10, flat=0.32)
        add("ears", paint(ear, lambda co, n, g: mix(FUR["black"], FUR["sheen"], 0.5 * smooth(n.z, 0.2, 1.0))), fur_m)

    # ---- collar and bone tag ----------------------------------------------------------------------------
    ring = lathe([(0.37 + 0.05 * math.cos(a), 0.04 * math.sin(a)) for a in (2 * math.pi * k / 6 for k in range(6))], segs=28, closed=True)
    ring.transform(M((0, -0.63, 1.74), rot=(31, 0, 0), scale=(1.02, 1.0, 1.0)))          # square to the neck
    add("collar", paint(ring, lambda co, n, g: mix(FUR["collar"], hexc("#7A141A"), 0.4 * smooth(-n.z, 0.0, 0.8))), fur_m)
    tag_at, _ = hit((0, -2.5, 1.5))
    tag_at = Vector((0, -1.04, 1.47))
    tag = [loft([tag_at + Vector((-0.09, 0, 0)), tag_at + Vector((0.09, 0, 0))], lambda t: 0.035, segs=8, rings=2)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            tag.append(ell(tag_at + Vector((0.1 * sx, 0, 0.032 * sz)), (0.042, 0.03, 0.042), cuts=1))
    for b in tag:
        add("tag", b, glow)
    add("collar", paint(loft([tag_at + Vector((0, 0.02, 0.03)), tag_at + Vector((0, 0.05, 0.12))], lambda t: 0.02, segs=6, rings=2),
                        lambda co, n, g: hexc("#C9CDD6")), fur_m)
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything but the eyes and the glowing tag becomes one textured mesh, SkeletonDog_Body; the tag
    is SkeletonDog_GLOW and the glossy amber eyes stay SkeletonDog_Eyes."""
    glow = [ob for ob in c.objects if "GLOW" in ob.name]
    eyes = [ob for ob in c.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow and ob not in eyes], texture, name=NAME + "_Body",
                            shade=0.45, soften=3, rough=0.88, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    for ob in glow:
        ob.name = ob.data.name = NAME + "_GLOW"
    for ob in eyes:
        ob.name = ob.data.name = NAME + "_Eyes"
    c.objects = [body] + glow + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,side,back 3/4,game distance")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default="SkeletonDog review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "skeletondog_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=(0, -0.7, 2.05))
        head = Vector((0, -1.25, 2.05)) * SCALE
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * 3.4, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * 3.2, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
