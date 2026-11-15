"""Cauldron pet: a charming witch's cauldron creature, remade from the game's horned black cauldron.
Built from scratch by script.

    python models/pets/cauldron.py --review out/cauldron.png      # render the review sheet
    python models/pets/cauldron.py --export models/export/cauldron.fbx

The original is a round black cauldron with big red-tipped horns, white angry eyes, a white swirl on
top, a green glowing mouth slot and little black legs. The remake keeps all of that and makes it
friendly. Must-haves, checked in every review:
  1. A sturdy cast-iron pot: a rolled rim, a riveted band, side lugs with rings, soot towards the
     bottom and worn edges, matte and speckled, never plastic.
  2. Two big curved horns from the shoulders, dark at the root with ember-red tips.
  3. Green potion bubbling at the top with glowing bubbles, a pale swirl of foam, a drip over the rim.
  4. A friendly face on the belly: round calm eyes and a small green-glowing grin, never angry.
  5. Stubby iron feet; about 3.5-4 studs tall; Body under 9k triangles.

Round 5: worn iron with a soft sheen (roughness 0.62) on broad hammered dents so it reads as
metal and not clay; rust runs down from the rivets.

Round 4: livelier iron: larger patches of blue-grey and black, pitting and worn flecks, a
casting seam down each side, a harder hammered surface; bigger pupils (less googly); thicker,
ringed horns; smaller, softer cheeks.

Round 3: the grin sunk into a deeper groove with dimples at the corners so it reads as a slot
and not a sticker; no brows (they were lost under the band); a rougher pitted iron with worn
highlights on the rim, band and rivets; triangles cut to the 9k budget.

Round 2: darker hammered iron; the face sculpted into the pot (eye sockets, a grin groove holding
the glow, arched brows, warm cheeks); bigger pupils so the eyes stop looking googly; bigger horns
leaving the band below the rim; fewer triangles in the feet and rivets.

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

NAME = "Cauldron"


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


def decimate(bm, target):
    """Bring a dense skin down to about `target` triangles."""
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    ob = _object(bm, "dec")
    bm.free()
    if tris > target:
        d = ob.modifiers.new("d", 'DECIMATE')
        d.ratio = target / tris
        d.use_collapse_triangulate = True
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


# ---- the cauldron -------------------------------------------------------------------------------

POT = [(0.0, 0.40), (0.5, 0.42), (0.92, 0.53), (1.2, 0.74), (1.36, 1.02), (1.41, 1.34), (1.38, 1.64),
       (1.28, 1.92), (1.16, 2.12), (1.1, 2.25), (1.12, 2.34), (1.22, 2.39), (1.29, 2.47), (1.28, 2.57),
       (1.19, 2.63), (1.07, 2.61), (1.01, 2.52), (0.99, 2.42), (0.6, 2.37), (0.0, 2.36)]
OUTER = [p for p in POT[1:10]]
IRON = {"iron": hexc("#222328"), "dark": hexc("#111113"), "worn": hexc("#666C78"), "rust": hexc("#4A2E20"),
        "soot": hexc("#0B0B0D"), "green": hexc("#2F5E2A"), "cheek": hexc("#5A2A26")}
EYE_Z, EYE_AZ, MOUTH_Z = 1.62, 19.0, 1.2


def pot_r(z):
    """Outer radius of the pot at height z (on the belly)."""
    for (r0, z0), (r1, z1) in zip(OUTER, OUTER[1:]):
        if z0 <= z <= z1:
            return lerp(r0, r1, (z - z0) / (z1 - z0))
    return OUTER[-1][0] if z > OUTER[-1][1] else OUTER[0][0]


def on_pot(az, z, out=0.0):
    """A point and outward normal on the belly; az in degrees from the front (-Y) towards +X."""
    a = math.radians(az)
    d = Vector((math.sin(a), -math.cos(a), 0))
    r = pot_r(z)
    slope = (pot_r(z + 0.02) - pot_r(z - 0.02)) / 0.04
    n = (d - Vector((0, 0, slope))).normalized()
    return Vector((d.x * r, d.y * r, z)) + n * out, n


def build():
    iron_m = painted("Iron", dict(strength=0.12, mottle=0.2, fine=70.0, length=1.0), rough=0.8)
    horn_m = painted("Horn", dict(strength=0.12, mottle=0.08, fine=34.0, length=5.0), rough=0.7)
    foam_m = painted("Foam", dict(strength=0.05, mottle=0.1, fine=30.0, length=1.0), rough=0.8)
    eye_m = kit.material("Eyes", "#F3F0E6", rough=0.15)
    glow = kit.material("GLOW_Potion", "#62F23A", rough=0.4, emit=2.6)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    eyes = [on_pot(EYE_AZ * s, EYE_Z) for s in (-1, 1)]
    mouth = []
    for k in range(9):
        x = (k / 8 - 0.5) * 0.4
        az = math.degrees(math.asin(x / pot_r(MOUTH_Z)))
        mouth.append(on_pot(az, MOUTH_Z + 0.085 * (x / 0.2) ** 2)[0])
    brows = []
    for s in (-1, 1):
        p, n = eyes[0 if s < 0 else 1]
        pts = []
        for k in range(5):
            u = k / 4 - 0.5
            az = EYE_AZ * s + u * 15
            pts.append(on_pot(az, EYE_Z + 0.3 - 0.06 * (2 * u) ** 2 + 0.02 * u * s)[0])
        brows.append(pts)

    def iron_colour(co, n, g=0.0):
        col = IRON["iron"]
        col = mix(col, IRON["rust"], 0.55 * smooth(noise.noise(co * 2.2 + Vector((3, 1, 0))), 0.2, 0.6))
        col = mix(col, IRON["soot"], smooth(co.z, 1.2, 0.45) * 0.85)
        col = mix(col, IRON["worn"], smooth(n.z, 0.55, 0.95) * smooth(co.z, 2.3, 2.55) * 0.9)
        col = mix(col, IRON["worn"], 0.35 * smooth(n.z, 0.6, 1.0) * smooth(co.z, 0.6, 1.0))
        col = mix(col, IRON["worn"], 0.3 * smooth(noise.noise(co * 6.0), 0.3, 0.7))
        col = mix(col, hexc("#3A3D45"), 0.45 * smooth(noise.noise(co * 1.3 + Vector((7, 2, 5))), 0.0, 0.5))
        col = mix(col, IRON["worn"], 0.5 * smooth(noise.noise(co * 14.0), 0.45, 0.75) * smooth(co.z, 0.9, 1.6))
        return col

    # ---- the pot: remeshed so the face can be sculpted into it -------------------------------------
    pot = fuse(lathe(resample(POT, 60), segs=72), voxel=0.024, iterations=1)

    def carve(co, n):
        d = Vector()
        for p, en in eyes:                                       # sockets with a soft raised rim
            r = (co - p).length
            d -= en * 0.06 * (1 - smooth(r, 0.17, 0.215))
            d += en * 0.02 * (1 - smooth(abs(r - 0.245), 0.0, 0.04))
        if co.y < -0.6:
            r = poly_dist(co, mouth)                             # the grin: a groove
            d -= n * 0.07 * (1 - smooth(r, 0.028, 0.06))
            d += n * 0.012 * (1 - smooth(abs(r - 0.085), 0.0, 0.03))
            for q in (mouth[0], mouth[-1]):                      # little dimples at the corners
                d -= n * 0.025 * (1 - smooth((co - q).length, 0.03, 0.07))
        d += n * 0.012 * noise.noise(co * 5.5)                   # hammered, a little uneven
        d += n * 0.014 * (abs(noise.noise(co * 3.2 + Vector((4, 4, 4)))) - 0.3)
        d += n * 0.004 * noise.noise(co * 16.0)
        ax = abs(co.x) - math.hypot(co.x, co.y) * 0.0
        if co.z < 2.0 and abs(co.y) < 0.06:                      # the casting seam down each side
            d += n * 0.018 * (1 - smooth(abs(co.y), 0.0, 0.05))
        return d
    sculpt(pot, carve)
    pot = decimate(pot, 3800)

    def pot_colour(co, n, g=0.0):
        rr = math.hypot(co.x, co.y)
        col = iron_colour(co, n)
        if co.z > 2.3 and rr < pot_r(min(co.z, 2.25)) - 0.08:     # inside the rim: dark with green light
            col = mix(IRON["dark"], IRON["green"], smooth(co.z, 2.6, 2.42))
        for p, en in eyes:
            col = mix(col, IRON["dark"], 0.7 * (1 - smooth((co - p).length, 0.2, 0.25)))
        if co.y < -0.6:
            col = mix(col, IRON["soot"], 1 - smooth(poly_dist(co, mouth), 0.04, 0.07))
            for s in (-1, 1):                                   # a warm ember blush on the cheeks
                q, _ = on_pot(34 * s, 1.34)
                col = mix(col, IRON["cheek"], 0.55 * (1 - smooth((co - q).length, 0.03, 0.15)))
        if 0.8 < co.z < 1.97:                                    # rust run down from each rivet
            az = math.degrees(math.atan2(co.x, -co.y))
            for k in range(12):
                da = (az - 360 * (k + 0.5) / 12 + 180) % 360 - 180
                w = abs(math.radians(da)) * pot_r(co.z)
                if w < 0.06:
                    run = smooth(co.z, 1.97 - 0.12 - 0.3 * (0.5 + 0.5 * math.sin(k * 2.3)), 1.95)
                    col = mix(col, IRON["rust"], 0.75 * run * (1 - smooth(w, 0.012, 0.05)))
        return col
    add("pot", paint(pot, pot_colour), iron_m)

    # riveted band under the neck
    z0, z1 = 1.97, 2.1
    band = lathe([(pot_r(z0) - 0.01, z0 - 0.01), (pot_r(z0) + 0.035, z0), (pot_r(z1) + 0.035, z1),
                  (pot_r(z1) - 0.01, z1 + 0.01)], segs=40, closed=True)
    add("band", paint(band, iron_colour), iron_m)
    for k in range(12):
        az = 360 * (k + 0.5) / 12
        p, n = on_pot(az, (z0 + z1) / 2, 0.035)
        add("rivets", paint(facing(ell((0, 0, 0), (0.045, 0.045, 0.035), cuts=1), p, n),
                            lambda co, nn, g: mix(iron_colour(co, nn), IRON["worn"], 0.4)), iron_m)

    # side lugs with hanging rings: the little "arms" of the original
    for s in (-1, 1):
        p, n = on_pot(90 * s, 1.5, 0.0)
        add("lugs", paint(ell(p + n * 0.05, (0.12, 0.13, 0.11), cuts=2), iron_colour), iron_m)
        ring = lathe([(0.17 + 0.04 * math.cos(a), 0.04 * math.sin(a)) for a in
                      (2 * math.pi * k / 6 for k in range(6))], segs=14, closed=True)
        ring.transform(M(p + n * 0.13 + Vector((0, 0, -0.16)), rot=(90, 0, 0)))
        add("lugs", paint(ring, iron_colour), iron_m)

    # stubby iron feet
    for az in (-45, 45, 135, -135):
        a = math.radians(az)
        d = Vector((math.sin(a), -math.cos(a), 0))
        root = d * 0.75 + Vector((0, 0, 0.62))
        knee = d * 1.0 + Vector((0, 0, 0.38))
        foot = d * 1.08 + Vector((0, 0, 0.13))
        leg = loft([root, knee, foot], lambda t: lerp(0.22, 0.15, t), segs=10, rings=6)
        add("feet", paint(leg, iron_colour), iron_m)
        rot = (0, 0, math.degrees(math.atan2(d.y, d.x)))
        add("feet", paint(ell(foot + d * 0.05 + Vector((0, 0, -0.02)), (0.25, 0.21, 0.14), rot=rot, cuts=2), iron_colour), iron_m)
        side = Vector((-d.y, d.x, 0))
        for t in (-1, 0, 1):
            toe = foot + d * 0.26 + side * (0.12 * t) + Vector((0, 0, -0.06))
            add("feet", paint(ell(toe - d * 0.03 * abs(t), (0.08, 0.08, 0.075), cuts=1), iron_colour), iron_m)

    # ---- horns from the shoulders ------------------------------------------------------------------
    for s in (-1, 1):
        az = 68 * s
        a = math.radians(az)
        d = Vector((math.sin(a), -math.cos(a), 0))
        up = Vector((0, 0, 1))
        root, _ = on_pot(az, 2.02, -0.14)
        pts = [root, root + d * 0.5 + up * 0.12, root + d * 0.82 + up * 0.5, root + d * 0.8 + up * 1.05,
               root + d * 0.55 + up * 1.45 + Vector((0, 0.06, 0)), root + d * 0.3 + up * 1.62 + Vector((0, 0.1, 0))]

        def hr(t):
            ridge = 1 - 0.09 * abs(math.sin(t * 22)) * (1 - t)
            return lerp(0.31, 0.014, t ** 1.05) * ridge
        horn = loft(pts, hr, segs=10, rings=28)

        def horn_colour(co, n, g):
            col = mix(hexc("#1A181B"), hexc("#3A1815"), smooth(g, 0.2, 0.5))
            col = mix(col, hexc("#0C0B0C"), 0.5 * (abs(math.sin(g * 22)) < 0.25) * (1 - g))
            col = mix(col, hexc("#C2301A"), smooth(g, 0.48, 0.76))
            col = mix(col, hexc("#FF7A2E"), smooth(g, 0.84, 1.0))
            return col
        add("horns", paint(horn, horn_colour), horn_m)
        p, n = on_pot(az, 2.02, 0.0)
        collar = lathe([(0.3 + 0.05 * math.cos(q), 0.05 * math.sin(q)) for q in
                        (2 * math.pi * k / 6 for k in range(6))], segs=16, closed=True)
        add("horns", paint(facing(collar, p + n * 0.04, (pts[1] - pts[0]).normalized()), iron_colour), iron_m)

    # ---- the face ------------------------------------------------------------------------------------
    for (p, n), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.165, 0.18, 0.085), cuts=3), p - n * 0.035, n), eye_m)
        pp = p + n * 0.03 + Vector((0, 0, -0.012)) + Vector((-s * 0.012, 0, 0))
        add("pupils", flat_paint(facing(ell((0, 0, 0), (0.128, 0.142, 0.035), cuts=2), pp, n), hexc("#16100D")), iron_m)
        add("eyes", ell(pp + n * 0.03 + Vector((-0.035, 0, 0.045)), (0.033, 0.033, 0.03), cuts=1), eye_m)
        add("eyes", ell(pp + n * 0.03 + Vector((0.03, 0, -0.04)), (0.016, 0.016, 0.015), cuts=1), eye_m)
    mp = [q + (q - Vector((0, 0, q.z))).normalized() * -0.05 for q in mouth]
    add("mouth", loft(mp, lambda t: 0.018 + 0.026 * math.sin(math.pi * t) ** 0.5, segs=10, rings=24), glow)

    # ---- potion, bubbles, foam swirl, drips ------------------------------------------------------------
    potion = lathe([(0.0, 2.5), (0.5, 2.49), (0.9, 2.47), (1.03, 2.46), (1.02, 2.4), (0.0, 2.4)], segs=48)
    add("potion", potion, glow)
    for x, y, r, z in ((0.38, -0.22, 0.17, 2.5), (-0.42, 0.2, 0.14, 2.5), (0.12, 0.5, 0.12, 2.5),
                       (-0.2, -0.52, 0.1, 2.5), (0.62, 0.3, 0.09, 2.49), (-0.68, -0.22, 0.11, 2.49),
                       (0.55, -0.5, 0.07, 2.49), (-0.5, 0.58, 0.07, 2.49),
                       (0.22, 0.05, 0.075, 2.88), (-0.08, -0.18, 0.05, 3.12)):
        add("bubbles", ell((x, y, z), (r, r, r * 0.92), cuts=2), glow)
    sw = []
    for k in range(22):
        t = k / 21
        a = t * 2.6 * math.pi
        rr = 0.12 + 0.6 * t
        sw.append((rr * math.cos(a), rr * math.sin(a), 2.505))
    swirl = loft(sw, lambda t: 0.05 * (1 - 0.6 * t) + 0.012, segs=6, rings=26, flat=0.6)
    add("foam", flat_paint(swirl, hexc("#E4F5D6")), foam_m)
    for az, L in ((-36, 0.3), (150, 0.42)):
        a = math.radians(az)
        d = Vector((math.sin(a), -math.cos(a), 0))
        drip = loft([d * 1.12 + Vector((0, 0, 2.63)), d * 1.27 + Vector((0, 0, 2.55)), d * 1.27 + Vector((0, 0, 2.6 - L)),
                     d * 1.2 + Vector((0, 0, 2.52 - L))], lambda t: 0.055 + 0.025 * smooth(t, 0.7, 1.0), segs=10, rings=14)
        add("potion", drip, glow)
    c.build()
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, Cauldron_Body; the potion,
    bubbles and grin are joined into Cauldron_GLOW, and the glossy eyes stay Cauldron_Eyes."""
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
    ap.add_argument("--title", default="Cauldron review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "cauldron_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=(0, -1.2, 1.5))
        head = Vector((0, -1.3, 1.5))
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
