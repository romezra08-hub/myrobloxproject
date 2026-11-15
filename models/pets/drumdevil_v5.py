"""DrumDevil pet: a cheeky little imp living in a lantern drum, remade from the game's red drum demon.
Built from scratch by script.

    python models/pets/drumdevil.py --review out/drumdevil.png      # render the review sheet
    python models/pets/drumdevil.py --export models/export/drumdevil.fbx

The original is a red-and-pink drum-shaped body with small devil horns, a yellow flame on top, a face
on the side and a black trident. The remake keeps all of that. Must-haves, checked in every review:
  1. A red lacquered drum body, a little barrel-shaped, with pink hide drumheads, brass rims and a
     row of brass studs under each rim; lacquer with a soft sheen and wood grain, never plastic.
  2. Small dark horns, a little devil tail with a spade tip, stubby arms and feet.
  3. A cheerful face on the side: big eyes glancing sideways, one brow up, a lopsided grin with one
     small fang: mischievous but cute, never menacing.
  4. A small flickering yellow flame on top in a brass lantern cup (glow).
  5. A little black trident held at its side; 3-4.5 studs tall; Body under 9k triangles.

Round 5: round studs again (hexagons up close), a clearer sideways glance.

Round 4: the trident moves to its right hand, the near side in the three-quarter view, and the eyes
glance towards it; the hide bands are a single skin turned in at the edge; triangles under 9k.

Round 3: a squatter drum, wider than before like the original; the pink hide now wraps down over
both edges with a scalloped edge held by the brass tacks (the original's pink rims); the trident
arm comes forward so the trident shows from the front.

Round 2: the pupils sit on the curve of the eye (the eye white cut a notch in them); the trident
runs through the fist, thicker; heavier brass rims and bigger studs; a long wood grain under the
lacquer; the flame flickers front to back as well; triangles back under 9k.

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

NAME = "DrumDevil"


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


# ---- the drum devil -----------------------------------------------------------------------------

DRUM = [(0.0, 0.26), (0.98, 0.26), (1.05, 0.31), (1.1, 0.48), (1.15, 0.8), (1.17, 1.23), (1.15, 1.66),
        (1.1, 1.98), (1.05, 2.15), (0.98, 2.2), (0.0, 2.2)]
TOP = 2.2
OUTER = DRUM[1:10]
COL = {"red": hexc("#B8151F"), "deep": hexc("#6E0A12"), "hi": hexc("#D9363A"), "wood": hexc("#4A1A12"),
       "skin": hexc("#5C0E1A"), "skin_hi": hexc("#8A1E2A"), "hide": hexc("#E9AFA4"), "hide_dk": hexc("#B87A72"),
       "brass": hexc("#C08A2C"), "brass_hi": hexc("#F2CF74"), "brass_dk": hexc("#5E3E12"),
       "mouth": hexc("#36060D"), "tongue": hexc("#D9566A"), "ivory": hexc("#F4EBD6"), "iron": hexc("#1B1517")}
EYE_Z, EYE_AZ, MOUTH_Z = 1.42, 20.0, 0.98


def drum_r(z):
    """Outer radius of the drum at height z."""
    for (r0, z0), (r1, z1) in zip(OUTER, OUTER[1:]):
        if z0 <= z <= z1:
            return lerp(r0, r1, (z - z0) / (z1 - z0))
    return OUTER[-1][0] if z > OUTER[-1][1] else OUTER[0][0]


def on_drum(az, z, out=0.0):
    """A point and outward normal on the drum; az in degrees from the front (-Y) towards +X."""
    a = math.radians(az)
    d = Vector((math.sin(a), -math.cos(a), 0))
    r = drum_r(z)
    slope = (drum_r(z + 0.02) - drum_r(z - 0.02)) / 0.04
    n = (d - Vector((0, 0, slope))).normalized()
    return Vector((d.x * r, d.y * r, z)) + n * out, n


def stud(r=0.045, h=0.035, segs=8):
    """A low brass dome, its base on z=0."""
    return lathe([(0.0, h), (r * 0.72, h * 0.8), (r, 0.0), (0.0, -0.01)], segs=segs)



def poly_t(p, pts):
    """Distance to a polyline and how far along it (0 to 1) the nearest point is."""
    best, bt = 1e9, 0.0
    n = len(pts) - 1
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
        d = (p - (a + ab * t)).length
        if d < best:
            best, bt = d, (i + t) / n
    return best, bt


def hide_band(z_lip, z_edge, scallops=14, phase=0.0, depth=0.07, segs=56, rows=3):
    """The drumhead's hide pulled down over the edge of the drum: a band from the lip (z_lip) to a
    scalloped edge (about z_edge), dipping to a point at each of the `scallops` tacks."""
    bm = bmesh.new()
    up = z_lip > z_edge
    outer = []
    for i in range(rows + 2):
        ro = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            az = math.degrees(a)
            k = abs(math.cos((az - phase) * math.radians(1) * scallops / 2))   # 1 at a tack, 0 between
            edge = z_edge + (-1 if up else 1) * depth * (k ** 3 - 0.3)
            z = lerp(z_lip, edge, min(i, rows) / rows)
            r = drum_r(z) + (0.018 if i <= rows else -0.03)     # the last row turns in under the edge
            d = Vector((math.sin(a), -math.cos(a), 0))
            ro.append(bm.verts.new(d * r + Vector((0, 0, z))))
        outer.append(ro)
    for i in range(rows + 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((outer[i][j], outer[i][j2], outer[i + 1][j2], outer[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build():
    lac_m = painted("Lacquer", dict(strength=0.1, mottle=0.08, fine=30.0, length=9.0), rough=0.5)
    skin_m = painted("ImpSkin", dict(strength=0.08, mottle=0.1, fine=40.0, length=3.0), rough=0.8)
    brass_m = painted("Brass", dict(strength=0.06, mottle=0.14, fine=50.0, length=2.0), rough=0.45)
    hide_m = painted("Hide", dict(strength=0.06, mottle=0.18, fine=24.0, length=1.0), rough=0.85)
    eye_m = kit.material("Eyes", "#F5F0E4", rough=0.15)
    glow = kit.material("GLOW_Flame", "#FFC02E", rough=0.4, emit=3.0)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def brass_colour(co, n, g=0.0):
        col = mix(COL["brass"], COL["brass_hi"], 0.6 * smooth(n.z, 0.2, 0.9))
        col = mix(col, COL["brass_dk"], 0.45 * smooth(noise.noise(co * 4.0), 0.25, 0.7))
        return col

    def skin_colour(co, n, g=0.0):
        col = mix(COL["skin"], COL["skin_hi"], 0.5 * smooth(n.z, -0.2, 0.8))
        return mix(col, COL["deep"], 0.3 * smooth(noise.noise(co * 3.0), 0.2, 0.7))

    eyes = [on_drum(EYE_AZ * s, EYE_Z) for s in (-1, 1)]
    mouth = []
    for k in range(11):
        u = k / 10
        x = lerp(-0.27, 0.31, u)
        az = math.degrees(math.asin(x / drum_r(MOUTH_Z)))
        z = MOUTH_Z + 0.07 * ((x - 0.02) / 0.29) ** 2 + 0.06 * smooth(x, 0.1, 0.31)
        mouth.append(on_drum(az, z)[0])

    def half_width(t):
        return 0.028 + 0.05 * math.sin(math.pi * min(max(t, 0), 1)) ** 0.8

    # ---- the drum: remeshed so the face can be sculpted into it -------------------------------------
    drum = fuse(lathe(resample(DRUM, 50), segs=72), voxel=0.024, iterations=1)

    def carve(co, n):
        d = Vector()
        for p, en in eyes:                                       # shallow sockets
            r = (co - p).length
            d -= en * 0.05 * (1 - smooth(r, 0.17, 0.25))
        if co.y < -0.5:
            r, t = poly_t(co, mouth)                             # the open grin
            w = half_width(t)
            d -= n * 0.09 * (1 - smooth(r, w * 0.7, w * 1.15))
            d += n * 0.012 * (1 - smooth(abs(r - w * 1.35), 0.0, 0.03))
            for s in (-1, 1):                                    # round cheeks
                q, _ = on_drum(37 * s, 1.24)
                d += n * 0.035 * (1 - smooth((co - q).length, 0.05, 0.22))
        d += n * 0.005 * noise.noise(co * Vector((3, 3, 0.6)) * 3.0)   # a little hand-carved wobble
        return d
    sculpt(drum, carve)
    face_c = Vector((0, -1.15, 1.25))
    drum = decimate(drum, 2700, keep=lambda co: 0.6 * (1 - smooth((Vector(co) - face_c).length, 0.4, 0.9)), factor=1.0)

    def drum_colour(co, n, g=0.0):
        col = COL["red"]
        col = mix(col, COL["deep"], smooth(co.z, 1.0, 0.3) * 0.65 + 0.35 * smooth(co.z, 1.9, 2.4))
        col = mix(col, COL["hi"], 0.35 * smooth(noise.noise(co * Vector((2.5, 2.5, 0.4)) * 2.0), 0.1, 0.6))
        col = mix(col, COL["wood"], 0.5 * smooth(noise.noise(co * 9.0 + Vector((1, 2, 3))), 0.5, 0.8))
        grain = noise.noise(Vector((co.x * 5.0, co.y * 5.0, co.z * 0.7)) + Vector((0.5, 3.1, 0)))      # long vertical wood grain under the lacquer
        col = mix(col, COL["deep"], 0.35 * smooth(grain, 0.05, 0.4))
        col = mix(col, COL["hi"], 0.25 * smooth(-grain, 0.15, 0.45))
        if co.y < -0.5:
            r, t = poly_t(co, mouth)
            w = half_width(t)
            inside = 1 - smooth(r, w * 0.75, w * 1.0)
            col = mix(col, COL["mouth"], inside)
            q = mouth[5] + Vector((0, 0, -0.03))
            col = mix(col, COL["tongue"], inside * (1 - smooth((co - q).length, 0.02, 0.07)) * (co.z < q.z + 0.02))
            for s in (-1, 1):
                q, _ = on_drum(37 * s, 1.24)
                col = mix(col, hexc("#E25A5E"), 0.55 * (1 - smooth((co - q).length, 0.03, 0.16)))
        return col
    add("drum", paint(drum, drum_colour), lac_m)

    # ---- drumheads, brass rims and studs -----------------------------------------------------------
    for z, top in ((TOP, True), (0.26, False)):
        sgn = 1 if top else -1
        head = lathe([(0.0, z + 0.05 * sgn), (0.5, z + 0.045 * sgn), (0.92, z + 0.025 * sgn), (1.0, z + 0.005 * sgn),
                      (1.0, z - 0.03 * sgn), (0.0, z - 0.03 * sgn)], segs=32 if top else 16)

        def hide_colour(co, n, g=0.0):
            rr = math.hypot(co.x, co.y)
            col = mix(COL["hide"], COL["hide_dk"], 0.5 * smooth(noise.noise(co * 3.0), 0.0, 0.7))
            return mix(col, COL["hide_dk"], 0.6 * smooth(rr, 0.6, 0.9))
        add("heads", paint(head, hide_colour), hide_m)
        zr = z - 0.03 * sgn
        rim = lathe([(1.03 + 0.08 * math.cos(a), zr + 0.07 * math.sin(a)) for a in
                     (2 * math.pi * k / 6 for k in range(6))], segs=32, closed=True)
        add("rims", paint(rim, brass_colour), brass_m)
        zs = z - 0.27 * sgn
        phase = 360 * 0.5 / 14 + (12.86 if top else 0)
        band = hide_band(z - 0.02 * sgn, z - 0.21 * sgn, 14, phase, 0.06)
        add("hide bands", paint(band, hide_colour), hide_m)
        for k in range(14):
            p, n = on_drum(360 * (k + 0.5) / 14 + (12.86 if top else 0), zs, 0.012)
            add("studs", paint(facing(stud(0.058, 0.045, segs=8), p, n), brass_colour), brass_m)

    # ---- the face -----------------------------------------------------------------------------------
    for (p, n), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.17, 0.195, 0.085), cuts=3), p - n * 0.03, n), eye_m)
        look = (n + Vector((-0.36, 0, -0.03))).normalized()       # both glancing towards the trident
        pp = p - n * 0.03 + look * 0.078
        add("pupils", flat_paint(facing(ell((0, 0, 0), (0.105, 0.125, 0.03), cuts=2), pp, look), hexc("#1C0A0B")), skin_m)
        add("eyes", ell(pp + n * 0.03 + Vector((-0.032, 0, 0.045)), (0.032, 0.032, 0.03), cuts=1), eye_m)
        add("eyes", ell(pp + n * 0.03 + Vector((0.03, 0, -0.04)), (0.015, 0.015, 0.014), cuts=1), eye_m)
        # brows: ours left raised in an arch, ours right lower and flatter
        pts = []
        for k in range(5):
            u = k / 4 - 0.5
            lift = (0.3 + 0.07 * (1 - (2 * u) ** 2)) if s < 0 else (0.25 + 0.03 * (1 - (2 * u) ** 2) - 0.03 * u)
            pts.append(on_drum(EYE_AZ * s + u * 16, EYE_Z + lift, 0.0)[0])
        add("brows", paint(loft(pts, lambda t: 0.018 + 0.026 * math.sin(math.pi * t) ** 0.6, segs=6, rings=12), skin_colour), skin_m)
    # one small fang at the top of the grin
    fp = mouth[3]
    _, fn = on_drum(math.degrees(math.atan2(fp.x, -fp.y)), fp.z)
    top = fp + Vector((0, 0, 0.035)) - fn * 0.03
    fang = loft([top, top + Vector((0, 0, -0.06)) + fn * 0.015, top + Vector((0, 0, -0.1)) + fn * 0.01],
                lambda t: lerp(0.032, 0.006, t), segs=8, rings=5)
    add("fang", flat_paint(fang, COL["ivory"]), hide_m)

    # ---- horns, arms, feet, tail -----------------------------------------------------------------------
    for s in (-1, 1):
        root, n = on_drum(48 * s, 1.85, -0.06)
        d = Vector((n.x, n.y, 0)).normalized()
        pts = [root, root + d * 0.18 + Vector((0, 0, 0.16)), root + d * 0.24 + Vector((0, 0, 0.4)),
               root + d * 0.14 + Vector((0, 0.04, 0.58))]
        horn = loft(pts, lambda t: lerp(0.15, 0.008, t ** 1.2), segs=10, rings=10)
        add("horns", paint(horn, lambda co, nn, g: mix(COL["skin"], COL["iron"], smooth(g, 0.3, 0.95))), skin_m)
    for s in (-1, 1):
        sh, n = on_drum(84 * s, 1.0, -0.05)
        d = Vector((n.x, n.y, 0)).normalized()
        if s < 0:                                                # this arm holds the trident out at its side
            elbow, hand = sh + d * 0.22 + Vector((0, -0.04, -0.14)), sh + d * 0.33 + Vector((0, -0.1, 0.02))
        else:                                                    # the other rests on its hip
            elbow, hand = sh + d * 0.3 + Vector((0, 0.04, -0.12)), sh + d * 0.2 + Vector((0, -0.12, -0.3))
        arm = loft([sh, elbow, hand], lambda t: lerp(0.105, 0.08, t), segs=8, rings=6)
        add("arms", paint(arm, skin_colour), skin_m)
        add("arms", paint(ell(hand, (0.11, 0.11, 0.1), cuts=2), skin_colour), skin_m)
        if s < 0:
            c.hand = hand
    for s in (-1, 1):
        foot = Vector((0.45 * s, -0.72, 0.11))
        add("feet", paint(ell(foot, (0.2, 0.27, 0.13), rot=(0, 0, -12 * s), cuts=2), skin_colour), skin_m)
        add("feet", paint(loft([foot + Vector((0, 0.3, 0.05)), foot + Vector((0, 0.05, 0.08))],
                               lambda t: 0.12, segs=8, rings=2), skin_colour), skin_m)
    tail = [Vector((0.1, 1.05, 0.62)), Vector((0.25, 1.4, 0.5)), Vector((0.45, 1.6, 0.78)), Vector((0.42, 1.65, 1.15)),
            Vector((0.3, 1.55, 1.35))]
    add("tail", paint(loft(tail, lambda t: lerp(0.075, 0.04, t), segs=8, rings=12), skin_colour), skin_m)
    tip, dirv = tail[-1], (tail[-1] - tail[-2]).normalized()
    spade = ell((0, 0, 0), (0.15, 0.03, 0.17), cuts=2)
    for v in spade.verts:                                        # a heart-shaped spade: pointed tip, notched base
        z = v.co.z
        v.co.x *= (1 - 0.85 * smooth(z, 0.0, 0.17)) * (1 + 0.25 * smooth(z, 0.05, -0.12))
        if z < -0.1:
            v.co.z += 0.05 * (1 - abs(v.co.x) / 0.18)
    spade.transform(M(tip + dirv * 0.14) @ dirv.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    add("tail", paint(spade, skin_colour), skin_m)

    # ---- the trident ----------------------------------------------------------------------------------------
    h = c.hand
    lean = Vector((-0.05, -0.012, 1.0)).normalized()             # the shaft runs through the fist, leaning out a little
    base = h - lean * ((h.z - 0.06) / lean.z)
    top = h + lean * ((2.5 - h.z) / lean.z)
    ax = (top - base).normalized()

    def at(t):
        return base.lerp(top, t)
    add("trident", paint(loft([base, top], lambda t: 0.058, segs=8, rings=2),
                         lambda co, n, g: COL["iron"]), skin_m)
    side = Vector((1, 0, 0))
    cross = at(1.0)
    prongs = [[cross + side * 0.0, cross + ax * 0.2, cross + ax * 0.42],
              [cross - side * 0.03, cross - side * 0.17 + ax * 0.05, cross - side * 0.2 + ax * 0.32],
              [cross + side * 0.03, cross + side * 0.17 + ax * 0.05, cross + side * 0.2 + ax * 0.32]]
    for k, pts in enumerate(prongs):
        add("trident", paint(loft(pts, lambda t: lerp(0.055, 0.008, t ** 1.4), segs=8, rings=6),
                             lambda co, n, g: COL["iron"]), skin_m)
        tipp = pts[-1]
        bdir = (pts[-1] - pts[-2]).normalized()
        out = Vector((0, 0, 0)) if k == 0 else side * (1 if k == 2 else -1)
        for sx in ((-1, 1) if k == 0 else (-1,)):
            bs = tipp - bdir * 0.1 + (side * sx * 0.02 if k == 0 else -out * 0.02)
            barb_dir = (side * sx if k == 0 else -out) * 0.7 - bdir
            add("trident", paint(loft([bs, bs + barb_dir.normalized() * 0.08], lambda t: lerp(0.022, 0.004, t), segs=6, rings=2),
                                 lambda co, n, g: COL["iron"]), skin_m)
    add("trident", paint(loft([cross - side * 0.21, cross + side * 0.21], lambda t: 0.05, segs=8, rings=2),
                         lambda co, n, g: COL["iron"]), skin_m)

    # ---- the brass lantern cup and the flame ---------------------------------------------------------------
    cup = lathe([(0.0, 2.23), (0.2, 2.23), (0.26, 2.28), (0.24, 2.38), (0.2, 2.4), (0.17, 2.36), (0.0, 2.34)], segs=24)
    add("cup", paint(cup, brass_colour), brass_m)
    for t in (0.02, 0.83):
        ring = lathe([(0.062 + 0.02 * math.cos(a), 0.03 * math.sin(a)) for a in
                      (2 * math.pi * k / 6 for k in range(6))], segs=12, closed=True)
        ring.transform(M(at(t)) @ ax.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        add("trident", paint(ring, brass_colour), brass_m)
    flame = loft([(0, 0, 2.32), (0.03, -0.03, 2.58), (-0.06, 0.04, 2.88), (0.05, -0.04, 3.16), (-0.03, 0.05, 3.42)],
                 lambda t: 0.26 * (t / 0.2) ** 0.6 if t < 0.2 else 0.26 * (1 - (t - 0.2) / 0.8) ** 1.25 + 0.004,
                 segs=12, rings=20)
    add("flame", flame, glow)
    for s in (-1, 1):
        tongue = loft([(0.1 * s, 0.0, 2.38), (0.2 * s, -0.02, 2.6), (0.17 * s, 0.0, 2.8)],
                      lambda t: 0.1 * (1 - t) ** 1.1 + 0.004, segs=8, rings=8)
        add("flame", tongue, glow)
    c.build()
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, DrumDevil_Body; the flame
    is DrumDevil_GLOW, and the glossy eyes stay DrumDevil_Eyes."""
    glow = [ob for ob in c.objects if "GLOW" in ob.name]
    eyes = [ob for ob in c.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow and ob not in eyes], texture, name=NAME + "_Body",
                            shade=0.5, soften=3, rough=0.62, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = NAME + "_GLOW"
    for ob in eyes:
        ob.name = ob.data.name = NAME + "_Eyes"
    c.objects = [body, g] + eyes


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
    ap.add_argument("--title", default="DrumDevil review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "drumdevil_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=(0, -1.1, 1.35))
        head = Vector((0, -1.15, 1.3))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * 3.6, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * 3.4, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
