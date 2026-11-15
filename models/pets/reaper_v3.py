"""Reaper pet: a cute-cool little spirit reaper, remade from the game's hooded reaper. Built from
scratch by script.

    python models/pets/reaper.py --review out/reaper.png      # render the review sheet
    python models/pets/reaper.py --export models/export/reaper.fbx

The original is a small hooded figure in dark purple-black robes holding a scythe, with a purple
aura and no face, only a dark hood. The remake keeps that. Must-haves, checked in every review:
  1. A chibi hooded cloak in deep violet-black: a big hood with a drooping point and a thick brim,
     cloth folds, a tattered hem fading to violet, floating above the ground.
  2. Inside the hood only darkness and two soft glowing violet eyes: no skull, no teeth.
  3. Small mitten hands from bell sleeves holding a scythe: a wooden staff and a silver
     crescent-moon blade, a violet gem in the collar.
  4. A few floating violet wisps for the aura.
  5. Matte painted cloth with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 3: a short shoulder cape with its own tatters over the robe, long creases down the robe;
a more violet black; bluer violet glow; a duller silver collar.

Round 2: no crescent clasp at the neck (from the front it read as two fangs under the hood); deeper
violet-black cloth; a smaller hood opening with a thinner brim; violet eyes and wisps, not pink-white;
the scythe stands in front so the far arm comes across the robe and both sleeves show; bigger, paler
mittens; a darker staff.

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

NAME = "Reaper"


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


def crescent(centre, R, a0, a1, wfun, spine=0.045, edge=0.006, n=22, cols=3):
    """A crescent-moon blade in the XZ plane: its back follows a circle of radius R round `centre`
    from angle a0 to a1 (degrees), its width wfun(t) reaching in towards the centre, thick at the
    back (`spine`) and thin at the inner, cutting edge. Each vertex keeps 'g' = t and 'h' (0 at the
    back, 1 at the edge)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    lh = bm.verts.layers.float.new("h")
    C = Vector(centre)
    front, back = [], []
    for i in range(n + 1):
        t = i / n
        a = math.radians(lerp(a0, a1, t))
        d = Vector((math.cos(a), 0, math.sin(a)))
        w = max(wfun(t), 0.004)
        fr, br = [], []
        for j in range(cols + 1):
            h = j / cols
            p = C + d * (R - w * h)
            th = lerp(spine, edge, h) * (0.35 + 0.65 * math.sin(math.pi * min(max(t, 0.04), 0.96)) ** 0.5)
            f, b = bm.verts.new(p + Vector((0, -th / 2, 0))), bm.verts.new(p + Vector((0, th / 2, 0)))
            f[lg] = b[lg] = t
            f[lh] = b[lh] = h
            fr.append(f)
            br.append(b)
        front.append(fr)
        back.append(br)
    for i in range(n):
        for j in range(cols):
            bm.faces.new((front[i][j], front[i][j + 1], front[i + 1][j + 1], front[i + 1][j]))
            bm.faces.new((back[i][j], back[i + 1][j], back[i + 1][j + 1], back[i][j + 1]))
    ring = [(0, j) for j in range(cols + 1)] + [(i, cols) for i in range(1, n + 1)] + \
           [(n, j) for j in range(cols - 1, -1, -1)] + [(i, 0) for i in range(n - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((front[i0][j0], back[i0][j0], back[i1][j1], front[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- the reaper ---------------------------------------------------------------------------------

CLOTH = {"base": hexc("#150B24"), "fold": hexc("#2C1846"), "deep": hexc("#07040C"), "hem": hexc("#4E2A86"),
         "void": hexc("#050307"), "spill": hexc("#2C1846"), "mitten": hexc("#9C8DBA"), "wood": hexc("#5A3A22"),
         "wood_dk": hexc("#3C2414"), "silver": hexc("#B4B9C6"), "silver_dk": hexc("#5A6070"), "edge": hexc("#F0F2F8")}
HOOD = Vector((0, 0.05, 2.45))
FACE = Vector((0, -0.58, 2.36))            # middle of the hood's opening
FACE_R = (0.31, 0.27)
HEM = 0.62                                 # where the hem's tatters start; their points hang lower
TATTERS = [0.22, 0.3, 0.18, 0.27, 0.2, 0.32, 0.16, 0.26, 0.24, 0.3, 0.19]


def cloak_r(z):
    """Radius of the robe at height z: a bell from narrow shoulders to a wide hem."""
    t = smooth(z, 1.95, 0.35)
    return lerp(0.44, 0.92, t ** 0.85)


def hem_z(theta):
    """Height of the hem at angle theta (radians): a ring of uneven pointed tatters."""
    n = len(TATTERS)
    f = (theta / (2 * math.pi) * n + 0.37) % n
    i = int(f)
    u = f - i
    tri = 1 - abs(2 * u - 1)
    return HEM - TATTERS[i] * tri ** 1.6


def fold(theta, z):
    """Cloth folds: a soft ripple round the robe that grows towards the hem."""
    return (0.055 * math.sin(theta * 7 + 0.6) + 0.03 * math.sin(theta * 12 + 2.0)) * smooth(z, 1.8, 0.55)


def robe():
    """The robe as one closed shape: outside from the shoulders down to the tattered hem, a thick
    turned edge, and the inside back up to a dome, so it can be remeshed with the rest."""
    bm = bmesh.new()
    segs, rows = 88, 16
    grid = []
    for i in range(rows + 1):
        ring = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            zb = hem_z(th)
            z = lerp(1.98, zb, i / rows)
            r = cloak_r(z) * (1 + fold(th, z))
            ring.append(bm.verts.new((math.sin(th) * r, -math.cos(th) * r, z)))
        grid.append(ring)
    for k, (dz, dr) in enumerate(((0.0, -0.09), (0.25, -0.12))):     # the turned edge and the inside
        ring = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            z = hem_z(th) + dz + (0.02 if k == 0 else 0.0)
            r = cloak_r(z) * (1 + fold(th, z)) + dr
            ring.append(bm.verts.new((math.sin(th) * r, -math.cos(th) * r, z)))
        grid.append(ring)
    for a, b in zip(grid, grid[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    top = bm.verts.new((0, 0, 2.02))
    for j in range(segs):
        bm.faces.new((grid[0][(j + 1) % segs], grid[0][j], top))
    dome = bm.verts.new((0, 0, 1.25))
    for j in range(segs):
        bm.faces.new((grid[-1][j], grid[-1][(j + 1) % segs], dome))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def capelet():
    """A short shoulder cape over the top of the robe, with its own ring of small tatters."""
    bm = bmesh.new()
    segs, rows = 72, 6
    n = 9

    def edge(th):
        f = (th / (2 * math.pi) * n + 0.1) % n
        u = f - int(f)
        return 1.5 - (0.08 + 0.05 * math.sin(int(f) * 2.3)) * (1 - abs(2 * u - 1)) ** 1.5

    def rad(z):
        return lerp(0.47, 0.66, smooth(z, 2.0, 1.45))
    grid = []
    for i in range(rows + 3):
        ring = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            if i <= rows:
                z = lerp(2.02, edge(th), i / rows)
                r = rad(z) * (1 + 0.04 * math.sin(th * 6 + 1.0) * smooth(z, 1.95, 1.5))
            elif i == rows + 1:
                z, r = edge(th) + 0.02, rad(edge(th)) - 0.07
            else:
                z, r = edge(th) + 0.2, 0.42
            ring.append(bm.verts.new((math.sin(th) * r, -math.cos(th) * r, z)))
        grid.append(ring)
    for a, b in zip(grid, grid[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, z, rev in ((grid[0], 2.05, True), (grid[-1], 1.9, False)):
        cv = bm.verts.new((0, 0, z))
        for j in range(segs):
            bm.faces.new((ring[(j + 1) % segs], ring[j], cv) if rev else (ring[j], ring[(j + 1) % segs], cv))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build():
    from mathutils.bvhtree import BVHTree
    cloth_m = painted("Cloth", dict(strength=0.12, mottle=0.12, fine=44.0, length=6.0), rough=0.92)
    wood_m = painted("Wood", dict(strength=0.25, mottle=0.1, fine=40.0, length=10.0), rough=0.8)
    metal_m = painted("Silver", dict(strength=0.04, mottle=0.08, fine=60.0, length=2.0), rough=0.4)
    glow = kit.material("GLOW_Spirit", "#7A4BFF", rough=0.4, emit=2.0)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    staff_lo, staff_hi = Vector((-0.92, -0.58, 0.0)), Vector((-0.74, -0.5, 3.15))
    sdir = (staff_hi - staff_lo).normalized()

    def on_staff(z):
        return staff_lo + sdir * ((z - staff_lo.z) / sdir.z)
    grips = [on_staff(1.42), on_staff(1.06)]

    # ---- the clay: robe, hood, hood point, brim, sleeves ------------------------------------------
    clay = [robe(), capelet(), ell(HOOD, (0.7, 0.68, 0.68)), ell((0, 0.02, 1.95), (0.5, 0.45, 0.3)),
            loft([HOOD + Vector((0, 0.15, 0.45)), HOOD + Vector((0, 0.55, 0.62)), HOOD + Vector((0.04, 0.88, 0.42)),
                  HOOD + Vector((0.08, 1.0, 0.18))], lambda t: lerp(0.34, 0.035, t ** 0.9), segs=12, rings=10)]
    brim = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        brim.append(FACE + Vector((math.cos(a) * (FACE_R[0] + 0.07), 0.02 - 0.06 * math.sin(a), math.sin(a) * (FACE_R[1] + 0.07))))
    clay.append(loft(brim, lambda t: 0.07, segs=8, rings=48))
    shoulders = [Vector((-0.42, -0.04, 1.86)), Vector((0.4, -0.1, 1.85))]
    elbows = [Vector((-0.68, -0.2, 1.5)), Vector((0.12, -0.78, 1.32))]     # the far arm comes across the front
    cuffs = []
    for sh, el, g in zip(shoulders, elbows, grips):
        cuff = g + (el - g).normalized() * 0.15
        clay.append(loft([sh, el, cuff], lambda t: lerp(0.14, 0.19, t ** 2), segs=12, rings=10))
        cuffs.append((cuff, (g - el).normalized()))
    skin = fuse(join(clay), voxel=0.024, iterations=2)

    def carve(co, n):                                           # the dark opening of the hood
        e = math.hypot((co.x - FACE.x) / FACE_R[0], (co.z - FACE.z) / FACE_R[1])
        if co.y < 0.0 and e < 1.05:
            return Vector((0, 0.42 * (1 - smooth(e, 0.75, 1.02)), 0))
        if co.z < 1.5:                                           # long creases running down the robe
            th = math.atan2(co.x, -co.y)
            return n * 0.025 * math.sin(th * 5 + 1.3) * smooth(co.z, 1.5, 1.1)
        return None
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: 0.6 * (1 - smooth((Vector(co) - FACE).length, 0.45, 0.8)), factor=1.0)
    tree = BVHTree.FromBMesh(skin)
    eyes = []
    for s in (-1, 1):
        loc, nrm, _, _ = tree.ray_cast(Vector((0.14 * s, -2.0, 2.36)), Vector((0, 1, 0)))
        eyes.append(loc)

    def cloth_colour(co, n, g=0.0):
        th = math.atan2(co.x, -co.y)
        col = CLOTH["base"]
        col = mix(col, CLOTH["fold"], 0.6 * smooth(n.z, 0.2, 0.9))
        f = math.sin(th * 7 + 0.6)
        col = mix(col, CLOTH["fold"], 0.35 * smooth(f, 0.2, 0.9) * smooth(co.z, 1.8, 0.8))
        col = mix(col, CLOTH["deep"], 0.4 * smooth(-f, 0.4, 1.0) * smooth(co.z, 1.8, 0.8))
        col = mix(col, CLOTH["hem"], smooth(co.z, HEM + 0.2, HEM - 0.25) * 0.85)
        e = math.hypot((co.x - FACE.x) / FACE_R[0], (co.z - FACE.z) / FACE_R[1])
        if co.y > -0.62 and e < 1.0 and co.y < 0.0:              # the darkness inside the hood
            col = mix(col, CLOTH["void"], 1 - smooth(e, 0.85, 1.0))
            for p in eyes:
                col = mix(col, CLOTH["spill"], 0.8 * (1 - smooth((co - p).length, 0.06, 0.2)))
        if co.z < 1.3 and math.hypot(co.x, co.y) < cloak_r(co.z) - 0.05:      # inside the robe
            col = CLOTH["deep"]
        return col
    add("cloak", paint(skin, cloth_colour), cloth_m)

    # ---- eyes, wisps (glow) -------------------------------------------------------------------------
    for p, s in zip(eyes, (-1, 1)):
        add("eyes", ell(p + Vector((0, -0.02, 0)), (0.06, 0.035, 0.085), rot=(0, 10 * s, 0), cuts=2), glow)
    for at, size, turn in (((0.82, -0.2, 1.1), 0.12, 0.0), ((0.6, 0.45, 2.6), 0.1, 1.0), ((-0.55, 0.3, 0.3), 0.1, 2.0),
                           ((0.35, -0.75, 0.42), 0.08, 3.0)):
        P = Vector(at)
        pts = [P, P + Vector((0.05 * math.cos(turn), 0.05 * math.sin(turn), size * 1.6)),
               P + Vector((-0.06 * math.cos(turn), -0.06 * math.sin(turn), size * 3.0)),
               P + Vector((0.02, 0.0, size * 3.8))]
        add("wisps", loft(pts, lambda t: size * (1 - t) ** 1.2 * (0.6 + 0.4 * smooth(t, 0.0, 0.2)) + 0.004, segs=8, rings=10), glow)

    # ---- mittens, scythe -------------------------------------------------------------------------------
    for (cuff, d), g in zip(cuffs, grips):
        add("mittens", paint(ell(g - d * 0.03, (0.135, 0.13, 0.12), cuts=2), lambda co, n, gg: CLOTH["mitten"]), cloth_m)
        thumb = g - d * 0.02 + Vector((0, -0.1, 0.07))
        add("mittens", paint(ell(thumb, (0.055, 0.055, 0.065), cuts=1), lambda co, n, gg: CLOTH["mitten"]), cloth_m)

    def wood_colour(co, n, g=0.0):
        k = noise.noise(Vector((co.x * 30, co.y * 30, co.z * 2.0)))
        return mix(CLOTH["wood"], CLOTH["wood_dk"], smooth(k, -0.1, 0.5) * 0.7)
    staff = loft([staff_lo, staff_lo.lerp(staff_hi, 0.5) + Vector((0.02, 0, 0)), staff_hi],
                 lambda t: 0.052 + 0.01 * math.sin(t * 19), segs=8, rings=16)
    add("staff", paint(staff, wood_colour), wood_m)

    def silver(co, n, g=0.0):
        return mix(CLOTH["silver"], CLOTH["silver_dk"], 0.4 * smooth(noise.noise(co * 6.0), 0.0, 0.7))
    top = staff_hi
    collar = loft([top - sdir * 0.16, top + sdir * 0.05], lambda t: 0.075 + 0.02 * math.sin(math.pi * t), segs=10, rings=4)
    add("collar", paint(collar, silver), metal_m)
    add("gem", ell(top - sdir * 0.05 + Vector((0, -0.075, 0)), (0.045, 0.03, 0.06), cuts=1), glow)
    centre = top + Vector((-0.42, 0, -0.08))
    blade = crescent(centre, 0.46, 12, 222, lambda t: 0.24 * math.sin(math.pi * min(t * 1.25, 1.0)) ** 0.8 * (1 - 0.6 * t) + 0.012,
                     n=22, cols=3)

    def blade_colour(co, n, g=0.0):
        rr = (co - centre).length
        h = smooth(rr, 0.46, 0.25)
        col = mix(CLOTH["silver_dk"], CLOTH["silver"], smooth(h, 0.0, 0.4))
        col = mix(col, CLOTH["edge"], smooth(h, 0.5, 0.9))
        return mix(col, CLOTH["silver_dk"], 0.25 * smooth(noise.noise(co * 5.0), 0.2, 0.7))
    add("blade", paint(blade, blade_colour), metal_m)

    c.build()
    return c


def bake(c, texture):
    """Everything that does not glow becomes one textured mesh, Reaper_Body; the eyes, wisps and the
    gem are joined into Reaper_GLOW, which keeps its emissive violet material."""
    glow = [ob for ob in c.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow], texture, name=NAME + "_Body",
                            shade=0.5, soften=3, rough=0.88, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = NAME + "_GLOW"
    c.objects = [body, g]


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
    ap.add_argument("--title", default="Reaper review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "reaper_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=(0, -0.4, 2.0))
        head = Vector((0, -0.55, 2.3))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * 3.2, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * 3.2, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
