"""Mineable ore rocks for "Mine an Egg": one for each pickaxe tier and a special egg geode. Built from scratch by script.

    python models/props/ores.py                      # all seven: Roblox files in models/export, sheet in models/preview/ores.png
    python models/props/ores.py --only gold          # just one or a few (stone, coal, iron, gold, emerald, ember, geode)
    python models/props/ores.py --peek out.png       # a quick unbaked look while building

Every rock is about 4-5 studs wide and 3-4.5 tall, sits on a flat bottom at z = 0 and faces -Y. It arrives
in Roblox as at most two MeshParts: <Name>_Body, with its colours and crease shading baked into one image
(<tier>_ore_colour.png) and a roughness map beside it (<tier>_ore_rough.png: rock matte, coal, metal and
crystal a little shinier), and on the three top tiers <Name>_GLOW with one emissive GLOW_<Name> material.
Each is under 3,000 triangles.

The rocks are cut, not modelled: points sampled from an uneven dome are wrapped in a convex hull, nearly
flat neighbours are merged into big planes and every edge is cut by a chamfer. Strata are stacked slabs,
cracks are real splits with a gap, and ore and crystals are raised shapes laid on the rock by ray casts.

  Stone    weathered grey boulder, lichen spots, a few quartz flecks (starter)
  Coal     dark rock with black glossy coal seams and chunks breaking out of them
  Iron     brown-grey rock, rusty orange-brown lumps and dull metallic nuggets
  Gold     warm sandstone with thick gold veins and chunky nuggets
  Emerald  dark slate split open by emerald crystals lit from inside
  Ember    black obsidian with molten cracks and glowing ember crystals (the rarest ore)
  Geode    a geode broken open: agate rim, violet crystal hollow, a speckled egg nestled inside, ringed by
           small pale crystals with a soft glow
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import Prop  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, ".."))
LAYERS = ("g", "rgh", "band")
TAU = 2 * math.pi
UP = Vector((0.0, 0.0, 1.0))
LIGHT = (-0.45, -0.55, 0.7)          # where the painted highlights on gloss and metal come from


# ---- small helpers ----------------------------------------------------------------------------------

def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def layer(bm, name):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def layers(bm):
    return {k: layer(bm, k) for k in LAYERS}


def aim(origin, direction, roll=0.0):
    """A transform standing a shape built along +Z on `origin`, pointing along `direction`."""
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


def frame(n):
    """Two unit vectors square to n and to each other."""
    n = Vector(n).normalized()
    a = n.cross(UP)
    if a.length < 1e-4:
        a = n.cross(Vector((1, 0, 0)))
    a.normalize()
    return a, n.cross(a)


def jitter(rnd, v, amount):
    return (Vector(v) + Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))) * amount).normalized()


# ---- cutting rock -----------------------------------------------------------------------------------

def hull(points):
    """The convex hull of some points: a closed shape of flat facets."""
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs)
    junk = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
    junk = [v for v in junk if v.is_valid]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context='VERTS')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def slice_off(bm, co, no, fill=True):
    """Cut away everything on the side of the plane through `co` that `no` points to, and close the cut
    with a flat face."""
    no = Vector(no).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges and fill:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return bm


def chisel(bm, chamfer, flat=9.0, angle=14.0, segments=1):
    """Merge nearly flat neighbouring facets into big planes, then cut every edge that turns by more
    than `angle` degrees with a chamfer `chamfer` studs wide."""
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(flat), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:])
    bm.normal_update()
    if chamfer > 0:
        lim = math.radians(angle)
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim]
        if edges:
            bmesh.ops.bevel(bm, geom=edges, offset=chamfer, offset_type='OFFSET', segments=segments,
                            profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def split(bm, co, no, gap=0.1, turn=0.0):
    """Two pieces of a shape either side of the plane through `co` facing `no`, pushed `gap` apart and
    each tipped `turn` degrees away from the other about the foot of the cut. Uses up bm; returns
    (the piece behind the plane, the piece in front)."""
    no, co = Vector(no).normalized(), Vector(co)
    back = bm.copy()
    slice_off(back, co, no)
    slice_off(bm, co, -no)
    axis = no.cross(UP).normalized()
    pivot = Vector((co.x, co.y, 0.0))
    for piece, sgn in ((bm, 1), (back, -1)):
        m = Matrix.Translation(no * sgn * gap / 2)
        if turn:
            m = m @ Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-sgn * turn), 4, axis) @ Matrix.Translation(-pivot)
        piece.transform(m)
    return back, bm


def section(bm, co, no):
    """The outline where the plane through co facing no cuts a closed shape, as a loop of points."""
    c = bm.copy()
    no, co = Vector(no).normalized(), Vector(co)
    res = bmesh.ops.bisect_plane(c, geom=c.verts[:] + c.edges[:] + c.faces[:], dist=1e-5, plane_co=co, plane_no=no)
    pts = [v.co.copy() for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]
    c.free()
    mid = sum(pts, Vector()) / max(len(pts), 1)
    e1, e2 = frame(no)
    pts.sort(key=lambda p: math.atan2((p - mid).dot(e2), (p - mid).dot(e1)))
    return pts


def plate(loop, no, thick=0.05, shrink=0.1):
    """A thin slab filling a loop of points on a plane, `shrink` studs inside it: the glow seen down a crack."""
    no = Vector(no).normalized()
    mid = sum(loop, Vector()) / len(loop)
    bm = bmesh.new()
    layers(bm)
    top, bot = [], []
    for p in loop:
        d = p - mid
        q = mid + d * max(0.0, (d.length - shrink) / max(d.length, 1e-6))
        top.append(bm.verts.new(q + no * thick / 2))
        bot.append(bm.verts.new(q - no * thick / 2))
    n = len(loop)
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top[i], bot[i], bot[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


class Shape:
    """The uneven dome a rock is cut from. th is degrees round from the front (-Y) towards +X, t the
    height from 0 (ground) to 1 (top). `n` sets how square the dome's shoulders are, `cap` how wide its
    flat top is, `lean` how far the top leans per stud of height, `peak` where the top sits off centre and
    `flare` how much wider the foot is, so it settles onto the ground."""

    def __init__(self, rx, ry, h, seed, wob=0.09, n=2.2, cap=0.45, lean=(0.0, 0.0), at=(0.0, 0.0), flare=0.06,
                 peak=(0.0, 0.0)):
        rnd = random.Random(seed)
        self.rx, self.ry, self.h, self.n, self.cap = rx, ry, h, n, cap
        self.lean, self.at = Vector((lean[0], lean[1], 0.0)), Vector((at[0], at[1], 0.0))
        self.flare, self.peak = flare, Vector((peak[0], peak[1], 0.0))
        self.harm = [(k, wob * rnd.uniform(0.4, 1.0) / k ** 0.7, rnd.uniform(0, TAU)) for k in (1, 2, 3, 5)]

    def wobble(self, th):
        a = math.radians(th)
        return 1.0 + sum(amp * math.cos(k * a + ph) for k, amp, ph in self.harm)

    def profile(self, t):
        if t <= 0:
            return 1.0 + self.flare
        return max((1.0 - min(t, 1.0) ** self.n) ** (1.0 / self.n), self.cap)

    def point(self, th, t, jit=0.0, scale=1.0):
        a = math.radians(th)
        r = self.wobble(th) * self.profile(t) * (1 + jit) * scale
        return (Vector((math.sin(a) * self.rx * r, -math.cos(a) * self.ry * r, t * self.h)) + self.at
                + self.lean * max(t, 0.0) * self.h + self.peak * max(t, 0.0) ** 1.6)


def strata(shape, cuts, rnd, n=7, scales=None, shifts=None, tilt=(0.0, 0.0), rings=(0.18, 0.5, 0.8), cap_n=5,
           below=-0.2, jit=0.08, extra=(), spikes=None):
    """Point clouds for a rock as a stack of slabs split at the heights `cuts` (0 to 1). Each slab can be
    scaled and shifted a little, so the strata step in and out; the joins are tilted by `tilt`
    (studs of height per stud across in x and y). `extra` points are added to the top slab."""
    bounds = [below] + list(cuts) + [1.0]
    slabs = []
    top_k = len(bounds) - 2
    for k in range(top_k + 1):
        t0, t1 = bounds[k], bounds[k + 1]
        ts = [t0] + [t for t in rings if t0 + 0.06 < t < t1 - 0.04] + ([t1] if k < top_k else [])
        s = scales[k] if scales else 1.0
        dx, dy = shifts[k] if shifts else (0.0, 0.0)
        pts = []
        for t in ts:
            off = rnd.uniform(0, 360.0 / n)
            for j in range(n):
                th = off + 360.0 * j / n + rnd.uniform(-0.22, 0.22) * 360.0 / n
                p = shape.point(th, t, rnd.uniform(-jit, jit), s) + Vector((dx, dy, 0.0))
                joint = (t == t0 and k > 0) or (t == t1 and k < top_k)
                if joint:
                    p.z += tilt[0] * p.x + tilt[1] * p.y
                if t == t0 and k > 0:
                    p.z -= 0.012 * shape.h                         # a little overlap, so no daylight between slabs
                pts.append(p)
        if spikes and k in spikes:                                  # a jagged edge: a few points pushed out
            for j in range(spikes[k]):
                t = t0 + (t1 - t0) * rnd.uniform(0.3, 0.7)
                pts.append(shape.point(rnd.uniform(0, 360), t, rnd.uniform(0.06, 0.14), s) + Vector((dx, dy, 0.0)))
        if k == top_k:
            off = rnd.uniform(0, 360.0)
            for j in range(cap_n):
                th = off + 360.0 * j / cap_n + rnd.uniform(-18, 18)
                p = shape.point(th, 1.0, rnd.uniform(-0.25, 0.15), s) + Vector((dx, dy, 0.0))
                p.z += shape.h * rnd.uniform(-0.06, 0.02)
                pts.append(p)
            pts += [Vector(e) for e in extra]
        slabs.append(pts)
    return slabs


def nugget(rnd, size, n=10, squash=(1.0, 0.9, 0.75), chamfer=0.2, flat=8.0, angle=10.0):
    """A chunky lump of `size` studs: a hull of n points spread round a squashed ball, chamfered."""
    ga = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        d = jitter(rnd, (r * math.cos(i * ga), r * math.sin(i * ga), z), 0.35)
        k = size * rnd.uniform(0.82, 1.05)
        pts.append(Vector((d.x * squash[0] * k, d.y * squash[1] * k, d.z * squash[2] * k)))
    return chisel(hull(pts), chamfer * size, flat, angle)


def lump(rnd, size, squash=(1.0, 0.92, 0.72), seed=0.0):
    """A rounded, knobbly lump (rust): a low ball pushed in and out by noise."""
    bm = kit.ball((2 * size * squash[0], 2 * size * squash[1], 2 * size * squash[2]), cuts=1)
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in bm.verts:
        v.co *= 1.0 + 0.22 * noise.noise(v.co * (2.2 / size) + off)
    return bm


def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, taper=(0.78, 0.92), sides=6):
    """A crystal along +Z: a slightly tapering, slightly irregular prism from `sink` below its foot to a
    pointed tip. "g" runs 0 at the foot to 1 at the tip."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = layers(bm)
    turn = rnd.uniform(0, TAU / sides)
    tip_h = min(radius * rnd.uniform(*tip), length * 0.45)
    shoulder = length - tip_h
    tp = rnd.uniform(*taper)
    radii = [radius * rnd.uniform(0.88, 1.1) for _ in range(sides)]
    rings = []
    for z, s, g in ((-sink * radius - 0.05, 1.0, 0.0), (shoulder, tp, 0.8)):
        ring = []
        for j in range(sides):
            a = turn + j * TAU / sides
            v = bm.verts.new((math.cos(a) * radii[j] * s, math.sin(a) * radii[j] * s, z))
            v[lay["g"]] = g
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.12, 0.12) * radius, rnd.uniform(-0.12, 0.12) * radius, length))
    apex[lay["g"]] = 1.0
    lo, hi = rings
    for j in range(sides):
        k = (j + 1) % sides
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lit_crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, slit=0.016, sides=6):
    """A crystal lit from inside: its facets stand a hair apart and a glowing core fills it, so the light
    shows along every edge. Returns (facets, core)."""
    whole = crystal(length, radius, seed, tip, sink, sides=sides)
    src = whole.verts.layers.float.get("g")
    facets = bmesh.new()
    lay = layers(facets)
    for f in whole.faces:
        c = f.calc_center_median()
        vs = []
        for v in f.verts:
            d = v.co - c
            nv = facets.verts.new(c + d * max(0.0, 1 - slit / max(d.length, 1e-6)))
            nv[lay["g"]] = v[src]
            vs.append(nv)
        facets.faces.new(vs)
    whole.free()
    return facets, crystal(length * 0.95, radius * 0.78, seed, tip, sink, sides=sides)


def egg_shape(height, radius, segs=16, rings=12):
    """An egg standing on its round end along +Z: fuller below, longer above."""
    bm = bmesh.new()
    layers(bm)
    zc = 0.42 * height
    loops = []
    for i in range(1, rings):
        phi = -math.pi / 2 + math.pi * i / rings
        z = zc + math.sin(phi) * (zc if phi < 0 else height - zc)
        r = radius * math.cos(phi) ** (0.9 if phi < 0 else 1.05)
        loops.append([bm.verts.new((r * math.cos(TAU * j / segs), r * math.sin(TAU * j / segs), z)) for j in range(segs)])
    bot, top = bm.verts.new((0, 0, 0)), bm.verts.new((0, 0, height))
    for j in range(segs):
        k = (j + 1) % segs
        bm.faces.new((bot, loops[0][k], loops[0][j]))
        for a, b in zip(loops, loops[1:]):
            bm.faces.new((a[j], a[k], b[k], b[j]))
        bm.faces.new((loops[-1][j], loops[-1][k], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


class Surface:
    """Finds points on the rock, so that ore and crystals sit on it and neither float nor sink."""

    def __init__(self, bms, axis=(0.0, 0.0)):
        joined = bmesh.new()
        tmp = bpy.data.meshes.new("tmp_surface")
        for bm in bms:
            bm.to_mesh(tmp)
            joined.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        joined.normal_update()
        self.bvh = BVHTree.FromBMesh(joined)
        joined.free()
        self.axis = axis

    def at(self, th, z, down=0.0):
        """The point and outward normal where a ray aimed at the rock's axis at height z from direction
        th (degrees from the front towards +X, `down` tilting it to come from above) meets the rock."""
        a = math.radians(th)
        o = Vector((math.sin(a), -math.cos(a), down)).normalized()
        target = Vector((self.axis[0], self.axis[1], z))
        loc, nrm, _, _ = self.bvh.ray_cast(target + o * 30.0, -o)
        if loc is None:
            raise ValueError("no rock at th=%s z=%s" % (th, z))
        if nrm.dot(o) < 0:
            nrm = -nrm
        return loc, nrm.normalized()

    def path(self, ctrl, step=0.2, smooth=True):
        """Points on the rock along control points (th, z[, down]), splined (or joined by straight runs),
        about `step` studs apart, with their normals smoothed."""
        ctrl = [(c[0], c[1], c[2] if len(c) > 2 else 0.0) for c in ctrl]
        hits = [self.at(*c) for c in ctrl]
        length = sum((b[0] - a[0]).length for a, b in zip(hits, hits[1:]))
        n = max(int(length / step), 2 * len(ctrl))
        out = []
        for i in range(n + 1):
            t = i / n * (len(ctrl) - 1)
            if smooth:
                out.append(self.at(*(_cr([c[k] for c in ctrl], t) for k in range(3))))
            else:
                j = min(int(t), len(ctrl) - 2)
                u = t - j
                out.append(self.at(*(ctrl[j][k] + (ctrl[j + 1][k] - ctrl[j][k]) * u for k in range(3))))
        ns = [h[1] for h in out]
        sm = [(ns[max(i - 1, 0)] + ns[i] * 2 + ns[min(i + 1, len(ns) - 1)]).normalized() for i in range(len(ns))]
        return [(h[0], nn) for h, nn in zip(out, sm)]


VEIN = [(-1.0, None), (-0.82, 0.7), (-0.55, 1.0), (0.5, 0.94), (0.8, 0.66), (1.0, None)]     # flat top, chamfered sides
LIPS = [(-1.0, None), (-0.78, 0.8), (-0.45, 1.0), (-0.22, 0.15), (0.22, 0.15), (0.45, 1.0), (0.78, 0.8), (1.0, None)]
CORE = [(-1.0, None), (-0.5, 0.35), (0.5, 0.35), (1.0, None)]


def ridge(samples, width, height, section=VEIN, sink=0.08, ends=0.15, seed=0, wobble=0.0, sharp=()):
    """A raised band laid along points on the rock (a vein of ore, the lip of a crack): `section` is its
    cross-section, (u, h) going across with u from -1 to 1 (times the half `width`) and h the height (times
    `height`), None for a point sunk `sink` into the rock. It dives into the rock at both ends."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = layers(bm)
    m = len(samples)
    rings = []
    for i, (p, n) in enumerate(samples):
        t = i / (m - 1)
        a, b = samples[max(i - 1, 0)][0], samples[min(i + 1, m - 1)][0]
        tang = b - a
        tang = (tang - n * tang.dot(n)).normalized()
        side = tang.cross(n).normalized()
        f = max(0.0, min(1.0, t / ends, (1 - t) / ends)) if ends else 1.0
        w = (width(t) if callable(width) else width) * (0.35 + 0.65 * f) * (1 + wobble * rnd.uniform(-1, 1))
        h = (height(t) if callable(height) else height) * f - sink * (1 - f) * 0.6
        ring = []
        for u, hh in section:
            off = -sink if hh is None else hh * h
            v = bm.verts.new(p + side * u * w + n * off)
            v[lay["g"]] = 0.0 if hh is None else hh
            ring.append(v)
        rings.append(ring)
    k = len(section)
    for A, B in zip(rings, rings[1:]):
        for j in range(k):
            bm.faces.new((A[j], A[(j + 1) % k], B[(j + 1) % k], B[j]))
    for ring in (rings[0], rings[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / k)
        for j in range(k):
            bm.faces.new((ring[j], ring[(j + 1) % k], c))
    for j in sharp:
        for A, B in zip(rings, rings[1:]):
            e = bm.edges.get((A[j], B[j]))
            if e:
                e.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def open_up(bm, co, no, rnd, rim=0.26, depth=1.2, jag=0.08):
    """Break a rock open: cut away the cap on the side of the plane through `co` that `no` points to, and
    turn the hole into a hollow lined with crust: a rim band `rim` studs wide, then walls going `depth`
    down into the rock to a floor. "band" runs 0 at the broken edge, 0.35 at the rim's inner edge, 0.7 on
    the walls and 1 on the floor. Returns the hollow's centre on the plane and the rim's inner points."""
    no, co = Vector(no).normalized(), Vector(co)
    lay = layers(bm)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    loop = list({v for e in edges for v in e.verts})
    c = sum((v.co for v in loop), Vector()) / len(loop)
    c -= no * (c - co).dot(no)
    for v in bm.verts:
        v[lay["band"]] = 0.0
    for v in loop:
        v.co += no * rnd.uniform(-jag, jag * 0.4)

    def inplane(p):
        d = p - c
        return d - no * d.dot(no)

    cur, rim_pts = edges, []
    for k, band in enumerate((0.35, 0.7, 1.0)):
        res = bmesh.ops.extrude_edge_only(bm, edges=cur)
        nv = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in nv:
            d = inplane(v.co)
            if k == 0:
                v.co = v.co - d.normalized() * rim - no * 0.05
                rim_pts.append(v.co.copy())
            elif k == 1:
                v.co = c + d * 0.86 - no * depth * 0.55
            else:
                v.co = c + d * 0.42 - no * depth
            v[lay["band"]] = band
        cur = [g for g in res["geom"] if isinstance(g, bmesh.types.BMEdge) and len(g.link_faces) == 1]
    bmesh.ops.holes_fill(bm, edges=cur, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return c, rim_pts


# ---- materials -----------------------------------------------------------------------------------------

class Nodes:
    """A few shortcuts for building shader node trees (as in the eggs and pickaxes)."""

    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new
        self.bsdf = kit.principled(mat)

    def coord(self):
        return self.new("ShaderNodeTexCoord").outputs["Object"]

    def attr(self, name):
        a = self.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs["Fac"]

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        n.inputs["Roughness"].default_value = rough
        self.link(vec, n.inputs["Vector"])
        return n

    def voronoi(self, vec, scale, feature='F1'):
        v = self.new("ShaderNodeTexVoronoi")
        v.feature = feature
        v.inputs["Scale"].default_value = scale
        self.link(vec, v.inputs["Vector"])
        return v

    def mapping(self, vec, scale=(1, 1, 1)):
        mp = self.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        self.link(vec, mp.inputs["Vector"])
        return mp.outputs["Vector"]

    def bw(self, colour):
        b = self.new("ShaderNodeRGBToBW")
        self.link(colour, b.inputs[0])
        return b.outputs[0]

    def rgb(self, colour):
        s = self.new("ShaderNodeSeparateColor")
        self.link(colour, s.inputs[0])
        return s.outputs

    def ramp(self, src, a, b, c=0.0, d=1.0, smooth=True):
        r = self.new("ShaderNodeMapRange")
        if smooth:
            r.interpolation_type = 'SMOOTHSTEP'
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b
        r.inputs["To Min"].default_value, r.inputs["To Max"].default_value = c, d
        self.link(src, r.inputs["Value"])
        return r.outputs["Result"]

    def math(self, op, a, b=None, c=None):
        m = self.new("ShaderNodeMath")
        m.operation = op
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                m.inputs[i].default_value = x
            else:
                self.link(x, m.inputs[i])
        return m.outputs[0]

    def mul(self, *xs):
        out = xs[0]
        for x in xs[1:]:
            out = self.math('MULTIPLY', out, x)
        return out

    def mix(self, fac, a, b):
        m = self.new("ShaderNodeMix")
        m.data_type = 'RGBA'
        m.clamp_factor = True
        for sock, x in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, str):
                sock.default_value = (*kit.srgb(x), 1.0)
            else:
                self.link(x, sock)
        return m.outputs[2]

    def value(self, colour, v):
        h = self.new("ShaderNodeHueSaturation")
        if isinstance(colour, str):
            h.inputs["Color"].default_value = (*kit.srgb(colour), 1.0)
        else:
            self.link(colour, h.inputs["Color"])
        if isinstance(v, (int, float)):
            h.inputs["Value"].default_value = v
        else:
            self.link(v, h.inputs["Value"])
        return h.outputs["Color"]

    def colours(self, src, stops, constant=False):
        ramp = self.new("ShaderNodeValToRGB")
        if constant:
            ramp.color_ramp.interpolation = 'CONSTANT'
        els = ramp.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
        els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
        for pos, hexcode in stops[1:-1]:
            e = els.new(pos)
            e.color = (*kit.srgb(hexcode), 1.0)
        self.link(src, ramp.inputs["Fac"])
        return ramp.outputs["Color"]

    def edge(self, radius=0.03, lo=0.997, hi=0.95):
        """1 on the sharp edges of the shape, 0 on its flat planes."""
        bev = self.new("ShaderNodeBevel")
        bev.samples = 4
        bev.inputs["Radius"].default_value = radius
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(bev.outputs["Normal"], dot.inputs[0])
        self.link(geo.outputs["True Normal"], dot.inputs[1])
        return self.ramp(dot.outputs["Value"], lo, hi)

    def facing(self, direction, true=True):
        """How much the surface faces `direction` (-1 to 1)."""
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(geo.outputs["True Normal" if true else "Normal"], dot.inputs[0])
        dot.inputs[1].default_value = Vector(direction).normalized()
        return dot.outputs["Value"]

    def up(self, lo, hi):
        return self.ramp(self.facing((0, 0, 1)), lo, hi)

    def height(self, co):
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(co, sep.inputs[0])
        return sep.outputs[2]

    def warp(self, co, scale, amount):
        n = self.noise(co, scale, 3.0)
        wv = self.new("ShaderNodeVectorMath")
        wv.operation = 'MULTIPLY_ADD'
        self.link(n.outputs["Color"], wv.inputs[0])
        wv.inputs[1].default_value = (amount, amount, amount)
        self.link(co, wv.inputs[2])
        return wv.outputs[0]

    def near(self, co, points, reach):
        """1 at the nearest of `points`, fading to 0 at `reach` studs."""
        best = None
        for p in points:
            d = self.new("ShaderNodeVectorMath")
            d.operation = 'DISTANCE'
            self.link(co, d.inputs[0])
            d.inputs[1].default_value = tuple(p)
            best = d.outputs["Value"] if best is None else self.math('MINIMUM', best, d.outputs["Value"])
        return self.ramp(best, reach, reach * 0.2)

    def plane(self, co, at, no, reach):
        """1 on the plane through `at` facing `no`, fading to 0 at `reach` studs either side."""
        sub = self.new("ShaderNodeVectorMath")
        sub.operation = 'SUBTRACT'
        self.link(co, sub.inputs[0])
        sub.inputs[1].default_value = tuple(at)
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(sub.outputs[0], dot.inputs[0])
        dot.inputs[1].default_value = Vector(no).normalized()
        return self.ramp(self.math('ABSOLUTE', dot.outputs["Value"]), reach, 0.0)

    def out(self, colour, rough):
        self.link(colour, self.bsdf.inputs["Base Color"])
        self.bsdf.inputs["Roughness"].default_value = rough


def tinted(N, co, col, tints):
    """Apply colour washes: ("pts", points, reach, colour, amount) or ("plane", at, normal, reach, colour, amount)."""
    for t in tints:
        if t[0] == "pts":
            _, pts, reach, hexcode, amount = t
            f = N.near(co, pts, reach)
        else:
            _, at, no, reach, hexcode, amount = t
            f = N.plane(co, at, no, reach)
        col = N.mix(N.math('MULTIPLY', f, amount), col, hexcode)
    return col


def rock_colour(N, base, warm, edge, crack, dirt, top=None, vary=0.3, wear=0.75, cracks=0.4, strata=0.1,
                lichen=0.0, flecks=0.0, fleck_colour="#EEEAE0", moss=0.0, tints=(), grain=1.0):
    """Painted rock: each chunk its own shade, warm and cool patches, faint strata, mineral grain, hairline
    cracks, sun on the tops, pale chipped edges, earth near the ground; optionally lichen, flecks and moss."""
    co = N.coord()
    warped = N.warp(co, 1.1, 0.3)
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]
    big = N.noise(co, 0.6, 3.0)
    warmth = N.math('ADD', N.ramp(big.outputs["Fac"], 0.42, 0.64), N.math('MULTIPLY_ADD', island, 0.8, -0.35))
    col = N.mix(N.math('MULTIPLY', N.math('MINIMUM', N.math('MAXIMUM', warmth, 0.0), 1.0), 0.8), base, warm)
    lay = 1.0
    if strata:
        bands = N.noise(N.mapping(warped, (0.35, 0.35, 3.4)), 1.0, 2.0)          # broad horizontal layers
        lay = N.math('MULTIPLY_ADD', N.ramp(bands.outputs["Fac"], 0.32, 0.68), strata * 2, 1 - strata)
    cells = N.voronoi(warped, 3.2)
    g1 = N.math('MULTIPLY_ADD', N.bw(cells.outputs["Color"]), 0.22 * grain, 1 - 0.13 * grain)
    speck = N.noise(co, 14.0, 6.0, 0.62)
    g2 = N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.4 * grain, 1 - 0.2 * grain)
    tone = N.math('MULTIPLY_ADD', island, vary, 1 - vary * 0.55)
    col = N.value(col, N.mul(g1, g2, tone, lay))
    cr = N.voronoi(warped, 1.1, 'DISTANCE_TO_EDGE')
    line = N.ramp(cr.outputs["Distance"], 0.0, 0.035, 1.0, 0.0)
    where = N.ramp(N.noise(co, 1.3, 3.0).outputs["Fac"], 0.56, 0.63)
    col = N.mix(N.mul(line, where, cracks), col, crack)
    if top:
        col = N.mix(N.math('MULTIPLY', N.up(0.5, 0.95), top[1]), col, top[0])
    worn = N.ramp(N.noise(co, 5.0, 4.0, 0.65).outputs["Fac"], 0.32, 0.6, 0.3, 1.0)
    col = N.mix(N.mul(N.edge(0.045), worn, wear), col, edge)
    patchy = N.ramp(N.noise(co, 2.0, 3.0).outputs["Fac"], 0.35, 0.62, 0.35, 1.0)
    col = N.mix(N.mul(N.ramp(N.height(co), 0.32, 0.0), patchy, 0.45), col, dirt)
    if moss:
        patch = N.ramp(N.noise(co, 1.2, 4.0, 0.6).outputs["Fac"], 0.47, 0.56)
        mossy = N.value("#3B4B2B", N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.7, 0.65))
        col = N.mix(N.mul(N.up(0.45, 0.8), patch, moss), col, mossy)
    if lichen:
        vor = N.voronoi(N.warp(co, 3.0, 0.07), 2.4)
        r, g, b = N.rgb(vor.outputs["Color"])[:3]
        size = N.math('MULTIPLY_ADD', b, 0.16, 0.13)
        spot = N.ramp(N.math('SUBTRACT', vor.outputs["Distance"], size), 0.0, -0.03)
        keep = N.math('GREATER_THAN', r, 0.36)
        paint = N.colours(g, [(0.0, "#9DB07A"), (0.6, "#9DB07A"), (0.62, "#D09A3C"), (0.8, "#D09A3C"), (0.82, "#D2D0C0"), (1.0, "#D2D0C0")], constant=True)
        paint = N.value(paint, N.math('MULTIPLY_ADD', N.noise(co, 30.0, 2.0).outputs["Fac"], 0.3, 0.85))
        col = N.mix(N.mul(spot, keep, N.up(-0.1, 0.45), lichen), col, paint)
    if flecks:
        vor = N.voronoi(co, 7.0)
        r = N.rgb(vor.outputs["Color"])[0]
        spot = N.ramp(vor.outputs["Distance"], 0.16, 0.1)
        col = N.mix(N.mul(spot, N.math('GREATER_THAN', r, 0.72), flecks), col, fleck_colour)
    return tinted(N, co, col, tints)


def rock_material(name, rough=0.9, **kw):
    m = kit.material(name, kw.get("base", "#888888"), rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    N.out(rock_colour(N, **kw), rough)
    return m


def coal_material(name):
    """Coal: nearly black, with a cold glossy sheen painted on the facets that face the light and bright
    chipped edges, a hint of brown in the dull parts."""
    m = kit.material(name, "#131316", rough=0.5)
    m["rgh"] = 0.48
    N = Nodes(m)
    co = N.coord()
    f = N.facing(LIGHT)
    col = N.mix(N.ramp(f, -0.5, 0.8), "#050506", "#141418")
    col = N.mix(N.math('MULTIPLY', N.ramp(N.noise(co, 2.5, 3.0).outputs["Fac"], 0.45, 0.65), 0.35), col, "#16120E")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.72, 0.97), 0.6), col, "#454A57")
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 24.0, 3.0).outputs["Fac"], 0.3, 0.85))
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.45), col, "#666C7C")
    N.out(col, 0.48)
    return m


def rust_material(name):
    """Rusty iron ore: blotched orange-brown, darker pits, dusty paler tops and edges."""
    m = kit.material(name, "#8A4318", rough=0.82)
    m["rgh"] = 0.82
    N = Nodes(m)
    co = N.coord()
    col = N.colours(N.noise(co, 2.6, 4.0).outputs["Fac"], [(0.3, "#4E200C"), (0.46, "#843A16"), (0.6, "#A65424"), (0.76, "#C47A3C")])
    pits = N.voronoi(N.warp(co, 6.0, 0.05), 9.0)
    col = N.mix(N.math('MULTIPLY', N.ramp(pits.outputs["Distance"], 0.16, 0.05), 0.4), col, "#3A190B")
    col = N.mix(N.math('MULTIPLY', N.up(0.4, 0.9), 0.3), col, "#D49A62")
    col = N.mix(N.math('MULTIPLY', N.edge(0.03), 0.45), col, "#E2A666")
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 26.0, 3.0).outputs["Fac"], 0.3, 0.85))
    N.out(col, 0.82)
    return m


def iron_material(name):
    """Dull raw iron: dark grey turning lighter towards the light, hammered mottling, bright worn edges and a
    few rust spots."""
    m = kit.material(name, "#61676E", rough=0.52)
    m["rgh"] = 0.52
    N = Nodes(m)
    co = N.coord()
    f = N.facing(LIGHT)
    col = N.mix(N.ramp(f, -0.5, 0.8), "#2C3035", "#6E757D")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.6, 0.95), 0.6), col, "#AEB6BF")
    col = N.value(col, N.math('MULTIPLY_ADD', N.bw(N.voronoi(co, 9.0).outputs["Color"]), 0.25, 0.88))
    col = N.mix(N.math('MULTIPLY', N.ramp(N.noise(co, 4.0, 3.0).outputs["Fac"], 0.6, 0.7), 0.5), col, "#7A4420")
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.7), col, "#D2D8DE")
    N.out(col, 0.52)
    return m


def gold_material(name):
    """Raw gold: deep amber where it turns from the light, bright yellow towards it, a pale hot spot on
    the facets facing it, dimpled, with bright edges."""
    m = kit.material(name, "#D49A1E", rough=0.4)
    m["rgh"] = 0.4
    N = Nodes(m)
    co = N.coord()
    f = N.facing(LIGHT)
    col = N.mix(N.ramp(f, -0.6, 0.7), "#6A3E08", "#CF921C")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.45, 0.9), 0.85), col, "#F6C640")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.88, 0.99), 0.7), col, "#FFF2BE")
    col = N.value(col, N.math('MULTIPLY_ADD', N.bw(N.voronoi(co, 8.0).outputs["Color"]), 0.18, 0.92))
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.7), col, "#FFF0A8")
    N.out(col, 0.4)
    return m


def gem_material(name, stops, edge, inner, rough=0.32):
    """A crystal: dark at the foot, clear in the body, pale at the tip ("g" from 0 to 1), each facet lighter
    or darker by the way it faces, faint inclusions, bright edges."""
    m = kit.material(name, stops[2][1], rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    col = N.colours(N.attr("g"), stops)
    f = N.facing(LIGHT)
    col = N.value(col, N.math('MULTIPLY_ADD', f, 0.38, 1.0))
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.55, 0.95), 0.5), col, inner)
    cr = N.voronoi(N.coord(), 5.0, 'DISTANCE_TO_EDGE')
    col = N.mix(N.math('MULTIPLY', N.ramp(cr.outputs["Distance"], 0.0, 0.025, 1.0, 0.0), 0.15), col, edge)
    col = N.mix(N.math('MULTIPLY', N.edge(0.02, 0.995, 0.9), 0.55), col, edge)
    N.out(col, rough)
    return m


def obsidian_material(name, tints=()):
    """Volcanic glass: black, a cold sheen on the facets facing the light, faint conchoidal ripples, thin
    bright chipped edges; tints redden it near the molten cracks."""
    m = kit.material(name, "#08080A", rough=0.32)
    m["rgh"] = 0.32
    N = Nodes(m)
    co = N.coord()
    f = N.facing(LIGHT)
    col = N.mix(N.ramp(f, -0.3, 0.85), "#030304", "#0E0E13")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.85, 0.98), 0.6), col, "#4A4E5C")
    rip = N.new("ShaderNodeTexWave")
    rip.wave_type, rip.rings_direction = 'RINGS', 'SPHERICAL'
    rip.inputs["Scale"].default_value, rip.inputs["Distortion"].default_value = 3.0, 3.0
    N.link(N.warp(co, 0.8, 0.5), rip.inputs["Vector"])
    col = N.value(col, N.math('MULTIPLY_ADD', rip.outputs["Fac"], 0.35, 0.82))
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]
    col = N.value(col, N.math('MULTIPLY_ADD', island, 0.3, 0.85))
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.55), col, "#7E8294")
    N.out(tinted(N, co, col, tints), 0.32)
    return m


def egg_material(name):
    """A warm cream eggshell with soft caramel, cocoa and sea-green speckles, deeper low down."""
    m = kit.material(name, "#F4E8CF", rough=0.65)
    m["rgh"] = 0.65
    N = Nodes(m)
    co = N.coord()
    col = N.mix(N.ramp(N.attr("g"), 0.0, 1.0), "#E6CFA2", "#FBF3E2")
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 40.0, 2.0).outputs["Fac"], 0.1, 0.95))
    warped = N.warp(co, 4.0, 0.06)
    for scale, size, keep, amount in ((5.0, 0.26, 0.35, 0.9), (11.0, 0.22, 0.3, 0.85), (20.0, 0.2, 0.4, 0.7)):
        vor = N.voronoi(warped, scale)
        r, g, b = N.rgb(vor.outputs["Color"])[:3]
        rad = N.math('MULTIPLY_ADD', b, size * 0.6, size * 0.5)
        dot = N.math('MULTIPLY', N.ramp(N.math('SUBTRACT', vor.outputs["Distance"], rad), 0.02, -0.04),
                     N.math('GREATER_THAN', r, keep))
        paint = N.colours(g, [(0.0, "#B9814F"), (0.45, "#B9814F"), (0.47, "#7E5A40"), (0.72, "#7E5A40"), (0.74, "#79AFA0"), (1.0, "#79AFA0")], constant=True)
        col = N.mix(N.math('MULTIPLY', dot, amount), col, paint)
    col = N.mix(N.math('MULTIPLY', N.up(0.3, 0.95), 0.25), col, "#FFFBF0")
    N.out(col, 0.65)
    return m


def geode_material(name, **rock):
    """The geode: rock outside; inside, by "band", a dark rind, white and grey agate rings round the opening,
    then lilac and deep violet crystal lining with glints."""
    m = kit.material(name, "#4D4A5C", rough=0.88)
    m["rgh"] = 0.85
    N = Nodes(m)
    outside = rock_colour(N, **rock)
    band = N.attr("band")
    co = N.coord()
    inner = N.colours(band, [(0.0, "#26222E"), (0.05, "#26222E"), (0.09, "#E9E4EF"), (0.3, "#CCC2DE"),
                             (0.4, "#B497E0"), (0.6, "#7351B6"), (1.0, "#3C2670")])
    rings = N.math('SINE', N.math('MULTIPLY', band, TAU * 11.0))
    agate = N.mul(N.ramp(rings, 0.3, 0.9), N.ramp(band, 0.08, 0.1), N.ramp(band, 0.33, 0.3))
    inner = N.mix(N.math('MULTIPLY', agate, 0.45), inner, "#9A8FB2")
    druze = N.voronoi(co, 24.0)
    glint = N.mul(N.ramp(druze.outputs["Distance"], 0.16, 0.06), N.ramp(band, 0.38, 0.45))
    inner = N.mix(N.math('MULTIPLY', glint, 0.75), inner, "#F3EAFF")
    inner = N.value(inner, N.math('MULTIPLY_ADD', N.noise(co, 30.0, 2.0).outputs["Fac"], 0.2, 0.9))
    col = N.mix(N.ramp(band, 0.008, 0.02, 0.0, 1.0, smooth=False), outside, inner)
    N.out(col, 0.85)
    return m


def glow_material(name, hexcode, emit):
    m = kit.material("GLOW_" + name, hexcode, rough=0.4, emit=emit)
    m["rgh"] = 0.4
    return m


# ---- building a rock ------------------------------------------------------------------------------------

class Build:
    """A Prop and the bookkeeping each rock needs: the floor cut, the roughness of each part, a tally of
    triangles by part."""

    def __init__(self, name):
        self.prop = Prop(name)
        self.prop.tally = {}

    def add(self, part, bm, mat, at=None, flat=False):
        lay = layers(bm)
        if at is not None:
            bm.transform(at)
        if bm.verts and min(v.co.z for v in bm.verts) < -1e-4:
            slice_off(bm, (0, 0, 0), (0, 0, -1))
        if not bm.faces:
            bm.free()
            return
        r = mat.get("rgh", 0.85)
        for v in bm.verts:
            v[lay["rgh"]] = r
        if flat:
            for e in bm.edges:
                e.smooth = False
        self.prop.tally[part] = self.prop.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        self.prop.add(bm, mat)

    def done(self):
        self.prop.build()
        for ob in self.prop.objects:
            weighted(ob)
        return self.prop


def weighted(ob):
    """Big planes keep their own flat shading and the chamfers between them shade softly round."""
    for mod in list(ob.modifiers):
        if mod.type == 'WEIGHTED_NORMAL':
            ob.modifiers.remove(mod)
    mod = ob.modifiers.new("Weighted", 'WEIGHTED_NORMAL')
    mod.mode, mod.weight, mod.keep_sharp = 'FACE_AREA', 50, True


def pebbles(b, sh, rnd, mat, spots, part="pebbles", chamfer=0.17, n=9):
    """Broken-off stones at the foot of the rock: (th, gap, size) round the outline of shape `sh`."""
    for th, gap, size in spots:
        base = sh.point(th, 0.0)
        d = Vector((base.x - sh.at.x, base.y - sh.at.y, 0.0)).normalized()
        pos = base + d * (gap + size * 0.7)
        bm = nugget(rnd, size, n=n, squash=(1.0, 0.85, 0.6), chamfer=chamfer)
        b.add(part, bm, mat, at=Matrix.Translation((pos.x, pos.y, size * 0.2)) @ Matrix.Rotation(rnd.uniform(0, TAU), 4, 'Z')
              @ Matrix.Rotation(rnd.uniform(-0.35, 0.35), 4, 'X'))


def seam_hit(surf, sh, th, t, tilt):
    """The point on the rock at direction th on the tilted join of strata at height t."""
    z = t * sh.h
    p, _ = surf.at(th, z)
    return surf.at(th, z + tilt[0] * p.x + tilt[1] * p.y)


def stone_ore():
    rnd = random.Random(11)
    sh = Shape(1.85, 1.55, 2.8, seed=4, wob=0.1, n=2.0, cap=0.45, peak=(-0.3, 0.15), flare=0.07)
    lower_pts, upper_pts = strata(sh, [0.38], rnd, scales=[1.0, 0.95], shifts=[(0, 0), (0.05, 0.06)], tilt=(0.07, 0.02))
    lower = chisel(hull(lower_pts), 0.12)
    ua, ub = split(hull(upper_pts), (0.35, 0, 0), (0.93, -0.36, 0.08), gap=0.08, turn=4.0)
    sh2 = Shape(0.78, 0.7, 1.55, seed=8, wob=0.08, n=1.9, cap=0.45, at=(1.35, -0.35), peak=(0.1, 0.05))
    side = chisel(hull(strata(sh2, [], rnd, n=6, rings=(0.3, 0.65), cap_n=4)[0]), 0.1)
    pieces = [lower, chisel(ua, 0.12), chisel(ub, 0.12), side]
    surf = Surface(pieces)
    rock = rock_material("StoneRock", base="#8A8882", warm="#968B7A", edge="#D3CFC4", crack="#3A3936", dirt="#5A554C",
                         top=("#A8A69C", 0.3), lichen=1.0, flecks=0.5, vary=0.22)
    quartz = gem_material("StoneQuartz", [(0.0, "#A9A69E"), (0.4, "#DCD9D2"), (0.8, "#F2F0EA"), (1.0, "#FFFFFF")], "#FFFFFF", "#FFFFFF", rough=0.35)
    b = Build("StoneOre")
    for p in pieces:
        b.add("rock", p, rock)
    pebbles(b, sh, rnd, rock, [(-75, 0.05, 0.34), (-30, 0.25, 0.24), (110, 0.25, 0.28), (200, 0.15, 0.3)])
    for k, (th, z, cnt) in enumerate([(-42, 0.9, 3), (-10, 1.7, 2), (12, 0.7, 2), (-65, 1.7, 2), (150, 1.3, 2), (205, 0.8, 2)]):
        p, n = surf.at(th, z)
        ax = jitter(rnd, n + UP * 0.35, 0.2)
        e1, e2 = frame(n)
        for j in range(cnt):
            a2 = jitter(rnd, ax, 0.35) if j else ax
            off = (e1 * rnd.uniform(-1, 1) + e2 * rnd.uniform(-1, 1)) * 0.08 * (j > 0)
            b.add("quartz", crystal(rnd.uniform(0.3, 0.45) * (1 - 0.25 * j), rnd.uniform(0.07, 0.1), seed=100 + k * 3 + j, sides=5),
                  quartz, aim(p - n * 0.03 + off, a2, rnd.uniform(0, 60)), flat=True)
    return b.done()


def coal_ore():
    rnd = random.Random(22)
    sh = Shape(2.1, 1.75, 3.2, seed=13, wob=0.08, n=2.4, cap=0.5, peak=(0.2, 0.1), flare=0.05)
    tilt = (0.15, -0.06)
    slabs = strata(sh, [0.27, 0.42, 0.64, 0.73], rnd, scales=[1.0, 1.06, 0.97, 1.05, 0.92],
                   shifts=[(0, 0), (0, -0.03), (0.03, 0.02), (0, -0.02), (-0.06, 0.06)], tilt=tilt, spikes={1: 6, 3: 5})
    rock = rock_material("CoalRock", base="#4E4A45", warm="#5A524A", edge="#A39C90", crack="#1A1918", dirt="#2B2826",
                         top=("#66615B", 0.25), vary=0.28, strata=0.08)
    coal = coal_material("CoalSeam")
    pieces = []
    for k, pts in enumerate(slabs):
        seam = k in (1, 3)
        pieces.append((chisel(hull(pts), 0.04 if seam else 0.12, flat=6.0 if seam else 9.0, angle=8 if seam else 14), coal if seam else rock))
    surf = Surface([p for p, _ in pieces])
    b = Build("CoalOre")
    for p, m in pieces:
        b.add("coal seams" if m is coal else "rock", p, m)
    for th, t, size in [(-42, 0.345, 0.42), (-14, 0.35, 0.34), (12, 0.34, 0.44), (38, 0.35, 0.3), (-62, 0.685, 0.3),
                        (-20, 0.69, 0.34), (10, 0.685, 0.26), (150, 0.345, 0.34), (205, 0.69, 0.28)]:
        p, n = seam_hit(surf, sh, th, t, tilt)
        bm = nugget(rnd, size, n=8, squash=(1.3, 1.0, 0.85), chamfer=0.08, angle=8)
        b.add("coal chunks", bm, coal, aim(p + n * size * 0.25, jitter(rnd, n + UP * 0.1, 0.3), rnd.uniform(0, 360)))
    pebbles(b, sh, rnd, rock, [(-60, 0.1, 0.3), (140, 0.15, 0.26)])
    pebbles(b, sh, rnd, coal, [(-18, 0.2, 0.26), (-40, 0.45, 0.18), (22, 0.35, 0.2), (180, 0.2, 0.2)], part="coal pebbles", chamfer=0.07, n=8)
    return b.done()


def iron_ore():
    rnd = random.Random(33)
    sh = Shape(1.9, 1.65, 3.6, seed=23, wob=0.11, n=2.0, cap=0.4, peak=(0.35, 0.25), flare=0.06)
    lo_pts, hi_pts = strata(sh, [0.36], rnd, scales=[1.0, 0.96], shifts=[(0, 0), (0.04, 0.04)], tilt=(-0.08, 0.05))
    ua, ub = split(hull(hi_pts), (-0.4, -0.2, 0), (-0.82, -0.55, 0.1), gap=0.12, turn=6.0)
    pieces = [chisel(hull(lo_pts), 0.12), chisel(ua, 0.12), chisel(ub, 0.12)]
    surf = Surface(pieces)
    rust, iron = rust_material("IronRust"), iron_material("IronMetal")
    lumps, nuggets = [], []
    for th, z, count in [(-35, 1.2, 4), (-75, 0.7, 2), (0, 2.25, 3), (38, 1.0, 2), (-58, 2.4, 2), (165, 1.5, 3), (110, 2.3, 1)]:
        p, n = surf.at(th, z)
        lumps.append((p, n, rnd.uniform(0.5, 0.58)))
        for j in range(count - 1):
            a = TAU * j / max(count - 1, 1) + rnd.uniform(-0.4, 0.4)
            lumps.append(surf.at(th + 15 * math.cos(a), z + 0.42 * math.sin(a)) + (rnd.uniform(0.32, 0.42),))
        a = rnd.uniform(0, TAU)
        nuggets.append(surf.at(th + 18 * math.cos(a), z + 0.5 * math.sin(a)) + (rnd.uniform(0.3, 0.36),))
    rock = rock_material("IronRock", base="#6B635B", warm="#7C624C", edge="#B9AD9C", crack="#2A2420", dirt="#3E3530",
                         top=("#857C72", 0.25), vary=0.28, tints=[("pts", [p for p, _, _ in lumps], 0.7, "#7B4524", 0.6)])
    b = Build("IronOre")
    for p in pieces:
        b.add("rock", p, rock)
    for p, n, s in lumps:
        b.add("rust lumps", nugget(rnd, s, n=9, squash=(1.1, 1.0, 0.8), chamfer=0.3), rust,
              aim(p - n * s * 0.22, jitter(rnd, n, 0.2), rnd.uniform(0, 360)))
    for p, n, s in nuggets:
        b.add("iron nuggets", nugget(rnd, s, n=8, squash=(1.2, 1.0, 0.7), chamfer=0.14), iron,
              aim(p - n * s * 0.1, jitter(rnd, n, 0.2), rnd.uniform(0, 360)))
    pebbles(b, sh, rnd, rock, [(-50, 0.2, 0.32), (35, 0.3, 0.26), (190, 0.2, 0.3)])
    pebbles(b, sh, rnd, rust, [(-15, 0.3, 0.24)], part="rust lumps", chamfer=0.3, n=10)
    pebbles(b, sh, rnd, iron, [(15, 0.45, 0.18)], part="iron nuggets", chamfer=0.12, n=8)
    return b.done()


def gold_ore():
    rnd = random.Random(44)
    sh = Shape(2.2, 1.8, 3.4, seed=35, wob=0.09, n=2.2, cap=0.42, peak=(-0.35, 0.1), flare=0.06)
    slabs = strata(sh, [0.33, 0.64], rnd, scales=[1.0, 0.97, 0.93], shifts=[(0, 0), (0.03, 0.03), (-0.03, 0.07)], tilt=(0.06, 0.06))
    pieces = [chisel(hull(s), 0.12) for s in slabs]
    surf = Surface(pieces)
    gold = gold_material("GoldOre")
    veins = [
        [(-75, 0.25), (-62, 0.7), (-52, 0.85), (-44, 1.35), (-30, 1.55), (-24, 2.0), (-10, 2.3), (-4, 2.8), (8, 3.15, 0.6)],
        [(-30, 1.55), (-14, 1.3), (-2, 1.38), (14, 0.95), (26, 0.85), (40, 0.4), (48, 0.15)],
        [(-4, 2.8), (12, 2.55), (28, 2.62), (46, 2.35), (62, 2.4)],
        [(140, 0.35), (150, 0.9), (165, 1.15), (178, 1.7), (195, 1.9), (205, 2.5)],
    ]
    nug_at = [(-44, 1.35, 0, 0.56), (-4, 2.8, 0, 0.55), (10, 3.2, 1.0, 0.55), (26, 0.85, 0, 0.48), (-62, 0.7, 0, 0.42),
              (178, 1.7, 0, 0.46), (62, 2.4, 0, 0.4), (-22, 2.05, 0, 0.36)]
    hits = [surf.at(th, z, d) for th, z, d, _ in nug_at]
    rock = rock_material("GoldRock", base="#B49B74", warm="#AA8458", edge="#E6D7B5", crack="#4A3826", dirt="#6B5238",
                         top=("#CDB894", 0.3), vary=0.22, strata=0.12, flecks=0.6, fleck_colour="#F0C850",
                         tints=[("pts", [p for p, _ in hits], 0.8, "#C9A050", 0.3)])
    b = Build("GoldOre")
    for p in pieces:
        b.add("rock", p, rock)
    for k, ctrl in enumerate(veins):
        b.add("veins", ridge(surf.path(ctrl, 0.2, smooth=False), 0.19, 0.1, seed=k, wobble=0.3, sharp=(1, 4)), gold)
    for (p, n), (_, _, _, s) in zip(hits, nug_at):
        b.add("nuggets", nugget(rnd, s, n=12, squash=(1.1, 0.95, 0.8), chamfer=0.18), gold,
              aim(p - n * s * 0.2, jitter(rnd, n, 0.15), rnd.uniform(0, 360)))
    pebbles(b, sh, rnd, rock, [(-60, 0.2, 0.32), (35, 0.3, 0.27), (195, 0.2, 0.3)])
    pebbles(b, sh, rnd, gold, [(-20, 0.35, 0.22)], part="nuggets", chamfer=0.18, n=11)
    return b.done()


def emerald_ore():
    rnd = random.Random(55)
    sh = Shape(2.1, 1.75, 2.9, seed=47, wob=0.09, n=2.1, cap=0.45, flare=0.06, peak=(0.1, 0.15))
    slabs = strata(sh, [0.42], rnd, scales=[1.0, 0.96], shifts=[(0, 0), (0.02, 0.05)], tilt=(0.04, -0.05))
    co, no = Vector((0.15, 0.0, 0.0)), Vector((0.96, 0.25, 0.0)).normalized()
    pieces, glows = [], []
    for pts in slabs:
        h = hull(pts)
        glows.append(plate(section(h, co, no), no, thick=0.05, shrink=0.3))
        a, c = split(h, co, no, gap=0.16, turn=6.0)
        pieces += [chisel(a, 0.12), chisel(c, 0.12)]
    surf = Surface(pieces)
    F = Vector((0.12, -0.25, sh.h * 0.62))
    side = no.cross(UP).normalized()
    spec = [(2.3, 0, 0.0, 0.34), (1.6, 30, 0.34, 0.25), (1.4, 28, 0.32, 0.23), (1.15, 38, 0.33, 0.2), (0.95, 40, 0.3, 0.18),
            (1.05, 50, 0.3, 0.19), (0.7, 58, 0.36, 0.14), (0.85, 45, 0.36, 0.16), (0.6, 62, 0.3, 0.12)]
    d0 = Vector((0.04, -0.28, 1.0)).normalized()
    gem = gem_material("EmeraldGem", [(0.0, "#021A0F"), (0.4, "#06452A"), (0.8, "#109A5B"), (1.0, "#8CF0BC")], "#D2FFE8", "#4CF0A2")
    glow = glow_material("EmeraldOre", "#1FD47A", 3.2)
    feet = [F]
    b = Build("EmeraldOre")
    for k, (ln, ang, off, rad) in enumerate(spec):
        if k == 0:
            axis, foot = d0, F
        else:
            o = Matrix.Rotation(TAU * k / 8 + 0.5, 3, d0) @ side
            axis = (Matrix.Rotation(math.radians(ang), 3, d0.cross(o).normalized()) @ d0).normalized()
            foot = F + o * off - UP * 0.1
        at = aim(foot, axis, rnd.uniform(0, 60))
        if k < 3:
            facets, core = lit_crystal(ln, rad, seed=40 + k)
            b.add("crystals", facets, gem, at, flat=True)
            b.add("crystal cores", core, glow, at)
        else:
            b.add("crystals", crystal(ln, rad, seed=40 + k), gem, at, flat=True)
    for th, z, ln, cnt in [(-50, 1.1, 0.55, 2), (150, 1.1, 0.6, 3), (60, 0.5, 0.45, 2)]:
        p, n = surf.at(th, z)
        feet.append(p)
        s2 = n.cross(UP).normalized()
        for k in range(cnt):
            ax = jitter(rnd, n + UP * 0.6 + s2 * 0.35 * (k - (cnt - 1) / 2), 0.1)
            b.add("crystals", crystal(ln * (1 - 0.22 * k), 0.11 - 0.015 * k, seed=70 + k + int(th)), gem,
                  aim(p - n * 0.06 + s2 * 0.12 * (k - (cnt - 1) / 2), ax, rnd.uniform(0, 60)), flat=True)
    rock = rock_material("EmeraldRock", base="#3A3F44", warm="#4A463F", edge="#8F9590", crack="#121416", dirt="#23272A",
                         top=("#4F555A", 0.25), moss=0.5, vary=0.3,
                         tints=[("pts", feet, 1.1, "#1C6A44", 0.5), ("plane", co, no, 0.4, "#145A3A", 0.7)])
    for p in pieces:
        b.add("rock", p, rock)
    for g in glows:
        b.add("crack glow", g, glow)
    pebbles(b, sh, rnd, rock, [(-65, 0.2, 0.33), (25, 0.3, 0.27), (200, 0.2, 0.3)])
    return b.done()


def ember_ore():
    rnd = random.Random(66)
    sh = Shape(2.25, 1.85, 3.4, seed=59, wob=0.13, n=1.9, cap=0.3, lean=(0.05, 0.1), flare=0.05)
    peaks = [(-0.55, -0.15, 3.75), (0.65, 0.35, 3.5), (-1.35, 0.25, 2.85)]
    pts = strata(sh, [], rnd, n=8, rings=(0.2, 0.45, 0.7, 0.88), cap_n=4, extra=peaks)[0]
    whole = hull(pts)
    cuts = [(Vector((0.55, 0.0, 0.0)), Vector((0.88, -0.38, 0.28)).normalized()),
            (Vector((-0.6, 0.0, 0.0)), Vector((-0.85, -0.45, 0.25)).normalized())]
    glows = [plate(section(whole, co, no), no, thick=0.04, shrink=0.5) for co, no in cuts]
    left, right = split(whole, cuts[0][0], cuts[0][1], gap=0.1, turn=1.5)
    mid, far_left = split(left, cuts[1][0] - cuts[0][1] * 0.08, cuts[1][1], gap=0.1, turn=1.5)
    pieces = [chisel(p, 0.07, angle=12) for p in (right, mid, far_left)]
    surf = Surface(pieces)
    tints = [("plane", co, no, 0.45, "#5A1606", 0.8) for co, no in cuts]
    rock = obsidian_material("EmberRock", tints=tints)
    crust = obsidian_material("EmberCrust", tints=[("pts", [(0, 0, 0)], 0.01, "#000000", 0.0)])
    gem = gem_material("EmberGem", [(0.0, "#2A0402"), (0.4, "#8A1A06"), (0.8, "#E5481A"), (1.0, "#FFC46A")], "#FFD9A0", "#FF8A3A")
    glow = glow_material("EmberOre", "#FF5A14", 3.5)
    b = Build("EmberOre")
    for p in pieces:
        b.add("rock", p, rock)
    for g in glows:
        b.add("crack glow", g, glow)
    for k, ctrl in enumerate([[(-18, 0.3), (-3, 0.62), (-16, 0.95), (-1, 1.45), (-14, 1.8), (2, 2.45)],
                              [(-16, 0.95), (2, 1.1), (6, 1.5), (22, 1.62)],
                              [(-54, 0.45), (-40, 0.9), (-54, 1.35), (-42, 1.95)],
                              [(176, 0.45), (190, 0.95), (178, 1.5), (190, 2.1)]]):
        path = surf.path(ctrl, 0.22, smooth=False)
        b.add("crack lips", ridge(path, 0.11, 0.05, LIPS, seed=k, wobble=0.2), crust)
        b.add("molten cracks", ridge(path, 0.035, 0.05, CORE, seed=k), glow)
    for (th, z, d), spec in [((70, 2.7, 0.8), [(1.35, 0, 0.27), (1.05, 30, 0.2), (0.9, 35, 0.18), (0.75, 40, 0.16)]),
                             ((-75, 1.0, 0.0), [(1.0, 0, 0.2), (0.7, 35, 0.15), (0.55, 40, 0.13)]),
                             ((200, 2.3, 0.5), [(1.0, 0, 0.2), (0.65, 30, 0.15)])]:
        p, n = surf.at(th, z, d)
        d0 = (n + UP * 0.8).normalized()
        s2 = d0.cross(UP).normalized()
        for k, (ln, ang, rad) in enumerate(spec):
            o = Matrix.Rotation(TAU * k / len(spec), 3, d0) @ s2
            axis = d0 if k == 0 else (Matrix.Rotation(math.radians(ang), 3, d0.cross(o).normalized()) @ d0).normalized()
            at = aim(p - n * 0.12 + o * 0.14 * (k > 0), axis, rnd.uniform(0, 60))
            facets, core = lit_crystal(ln, rad, seed=200 + k + int(th))
            b.add("crystals", facets, gem, at, flat=True)
            b.add("crystal cores", core, glow, at)
    pebbles(b, sh, rnd, rock, [(-55, 0.2, 0.3), (40, 0.3, 0.26), (185, 0.2, 0.28), (-20, 0.45, 0.18)], chamfer=0.07, n=8)
    return b.done()


def geode_ore():
    rnd = random.Random(77)
    sh = Shape(2.2, 1.95, 3.55, seed=71, wob=0.08, n=1.9, cap=0.45, flare=0.06, peak=(0.15, 0.2))
    shell = chisel(hull(strata(sh, [], rnd, n=8, rings=(0.2, 0.45, 0.7, 0.88), cap_n=5)[0]), 0.13)
    no = Vector((0.06, -0.8, 0.6)).normalized()
    centre = Vector((0.0, 0.0, sh.h * 0.5))
    reach = BVHTree.FromBMesh(shell).ray_cast(centre, no)[3]
    c, rim_pts = open_up(shell, centre + no * (reach - 0.55), no, rnd, rim=0.24, depth=1.2)
    rock = geode_material("GeodeRock", base="#4E4B5E", warm="#5C5262", edge="#A39CB6", crack="#1E1C26", dirt="#2E2B33",
                          top=("#6E6A80", 0.25), vary=0.25, cracks=0.25)
    egg_m = egg_material("GeodeEgg")
    pale = gem_material("GeodeCrystal", [(0.0, "#7C6EA8"), (0.4, "#B9AEDD"), (0.8, "#E8E2FA"), (1.0, "#FFFFFF")], "#FFFFFF", "#F6F0FF", rough=0.3)
    glow = glow_material("GeodeOre", "#E2D4FF", 2.2)
    b = Build("GeodeOre")
    b.add("rock", shell, rock)
    axis = (no * 0.4 + UP * 0.9).normalized()
    egg = egg_shape(2.05, 0.74)
    lg = layer(egg, "g")
    for v in egg.verts:
        v[lg] = v.co.z / 2.05
    b.add("egg", egg, egg_m, aim(c - no * 0.85 - UP * 0.25, axis, 20))
    e1, e2 = frame(no)
    ring = sorted(rim_pts, key=lambda p: math.atan2((p - c).dot(e2), (p - c).dot(e1)))
    count = 20
    for k in range(count):
        p = ring[int(k * len(ring) / count)]
        out = (p - c - no * (p - c).dot(no)).normalized()
        ax = jitter(rnd, no * 0.85 + out * 0.6, 0.12)
        ln, rad = rnd.uniform(0.4, 0.7), rnd.uniform(0.08, 0.11)
        at = aim(p - ax * 0.04, ax, rnd.uniform(0, 60))
        if k % 3 == 0:
            facets, core = lit_crystal(ln, rad, seed=300 + k)
            b.add("crystals", facets, pale, at, flat=True)
            b.add("crystal cores", core, glow, at)
        else:
            b.add("crystals", crystal(ln, rad, seed=300 + k), pale, at, flat=True)
    foot = c - no * 0.85 - UP * 0.25
    for k in range(5):
        a = TAU * k / 5 + 0.3
        o = e1 * math.cos(a) + e2 * math.sin(a)
        ax = jitter(rnd, no + o * 0.7, 0.1)
        facets, core = lit_crystal(rnd.uniform(0.35, 0.5), 0.08, seed=350 + k)
        at = aim(foot + o * 0.74 + no * 0.15, ax, rnd.uniform(0, 60))
        b.add("crystals", facets, pale, at, flat=True)
        b.add("crystal cores", core, glow, at)
    pebbles(b, sh, rnd, rock, [(-60, 0.2, 0.3), (45, 0.3, 0.26), (190, 0.2, 0.3), (-15, 0.5, 0.2)])
    return b.done()


ORES = {  # key: (name, builder, bake settings)
    "stone": ("StoneOre", stone_ore, dict(shade=0.65, soften=2, uv_angle=66.0)),
    "coal": ("CoalOre", coal_ore, dict(shade=0.65, soften=2, uv_angle=66.0)),
    "iron": ("IronOre", iron_ore, dict(shade=0.65, soften=2, uv_angle=66.0)),
    "gold": ("GoldOre", gold_ore, dict(shade=0.6, soften=2, uv_angle=66.0)),
    "emerald": ("EmeraldOre", emerald_ore, dict(shade=0.65, soften=2, uv_angle=66.0)),
    "ember": ("EmberOre", ember_ore, dict(shade=0.6, soften=2, uv_angle=66.0)),
    "geode": ("GeodeOre", geode_ore, dict(shade=0.7, soften=2, uv_angle=66.0)),
}


def snake(name):
    return name.replace("Ore", "").lower() + "_ore"


# ---- baking, export and numbers ---------------------------------------------------------------------------

def bake(prop, name, texture, settings, size=1024, samples=32):
    """Everything that does not glow becomes one textured mesh, <Name>_Body, with a roughness map baked from
    each part's roughness; the glowing parts stay one mesh, <Name>_GLOW, with their single GLOW_ material."""
    glow = [ob for ob in prop.objects if ob.data.materials[0].name.startswith("GLOW_")]
    body = kit.bake_texture([ob for ob in prop.objects if ob not in glow], texture, size=size, samples=samples,
                            name=name + "_Body", uv_margin=0.004, pack_margin=0.003, **settings)
    bake_rough(body, texture, size)
    weighted(body)
    objs = [body]
    if glow:
        bpy.ops.object.select_all(action='DESELECT')
        for ob in glow:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = glow[0]
        if len(glow) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = name + "_GLOW"
        weighted(g)
        objs.append(g)
    prop.objects = objs


def bake_rough(ob, texture, size):
    """Replace kit's flat grey roughness image with one baked from the "rgh" value each part carries, with a
    faint mottle, and wire it into the body's material."""
    if os.environ.get("PETS_FAST"):
        size = min(size, 512)
    stem = os.path.splitext(texture)[0]
    stem = stem[:-len("_colour")] if stem.endswith("_colour") else stem
    path = stem + "_rough.png"
    baked = ob.data.materials[0]
    tmp = bpy.data.materials.new("RoughBake")
    N = Nodes(tmp)
    em = N.new("ShaderNodeEmission")
    v = N.math('MULTIPLY_ADD', N.noise(N.coord(), 6.0, 3.0).outputs["Fac"], 0.12, -0.06)
    N.link(N.math('ADD', N.attr("rgh"), v), em.inputs["Color"])
    out = next(n for n in tmp.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
    N.link(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new(os.path.basename(stem) + "_rough", size, size, alpha=False)
    img.generated_color = (0.85, 0.85, 0.85, 1.0)
    img.colorspace_settings.name = 'Non-Color'
    tex = N.new("ShaderNodeTexImage")
    tex.image = img
    tmp.node_tree.nodes.active = tex
    ob.data.materials[0] = tmp
    sc = bpy.context.scene
    sc.cycles.samples = 4
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='EMIT', margin=12)
    img.filepath_raw, img.file_format = path, 'PNG'
    img.save()
    ob.data.materials[0] = baked
    bsdf = kit.principled(baked)
    link = bsdf.inputs["Roughness"].links[0] if bsdf.inputs["Roughness"].links else None
    old = link.from_node.image if link else None
    node = link.from_node if link else baked.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    if not link:
        baked.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Roughness"])
    if old is not None and old != img:
        bpy.data.images.remove(old)
    bpy.data.materials.remove(tmp)


def numbers(prop, size):
    tris = prop.triangles()
    lo, hi = extent(prop)
    me = prop.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    return dict(tris=tris, total=sum(tris.values()), size=(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z), low=lo.z,
                used=a2, px_per_stud=(a2 * size * size / a3) ** 0.5)


# ---- the review sheet -----------------------------------------------------------------------------------------

def extent(prop):
    """The true bounds of a prop as it stands (its vertices, not its turned bounding boxes)."""
    pts = [ob.matrix_world @ v.co for ob in prop.objects for v in ob.data.vertices]
    return (Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts))),
            Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts))))


class Group:
    """Several props treated as one, for the review rig."""

    def __init__(self, props):
        self.props = props

    def bounds(self):
        los, his = zip(*(extent(p) for p in self.props))
        return (Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los))),
                Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his))))


def shoot(rig, cam, path, size, look="full", hide=()):
    sc, vl = bpy.context.scene, bpy.context.view_layer
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.filepath = path
    outline = look == "silhouette"
    vl.material_override = {"clay": rig.clay, "silhouette": rig.black}.get(look)
    rig.ground.hide_render = rig.dummy.hide_render = outline
    rig._world((1, 1, 1) if outline else (0.045, 0.05, 0.06), 1.0)
    for ob in sc.objects:
        if ob.type == 'LIGHT':
            ob.hide_render = outline
    for ob in hide:
        ob.hide_render = True
    bpy.ops.render.render(write_still=True)
    for ob in hide:
        ob.hide_render = False
    vl.material_override = None
    return path


def sheet(props, labels, out, samples=24, scale=1.0, title="", keep_views=False, clay=False):
    """All the rocks in a row in tier order, each turned to show its front three-quarters: the row from the
    front, a close-up of each (and of the geode's opening), the row from behind, the row at game distance
    next to the 5-stud block, and the row as silhouettes."""
    import review
    import shutil
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    turn, gap = math.radians(32.0), 1.2
    edge = 0.0
    for p in props:
        for ob in p.objects:
            ob.location, ob.rotation_euler = (0.0, 0.0, 0.0), (0.0, 0.0, turn)
        bpy.context.view_layer.update()
        lo, hi = extent(p)
        for ob in p.objects:
            ob.location.x = edge - lo.x
            ob.location.y = -(lo.y + hi.y) / 2
        edge += (hi.x - lo.x) + gap
    bpy.context.view_layer.update()
    group = Group(props)
    rig = review.Rig(group, samples=samples)
    rig.ground.scale = (6, 6, 1)
    rig.dummy.location.y = 0.0
    sc = bpy.context.scene
    sc.render.resolution_percentage = int(100 * scale)
    lo, hi = group.bounds()
    mid = Vector(((lo.x + hi.x) / 2 + 0.9, 0.0, 1.9))
    width = hi.x - lo.x + 4.0
    away = (width / 2) / math.tan(math.radians(10))
    right = rig.dummy.location.x + 1.0
    gx = (lo.x + right) / 2
    gd = max(20.0, ((right - lo.x) / 2 + 1.5) / math.tan(math.radians(35)))
    cams = {
        "front": review._camera("O_front", mid + Vector((0, -1.0, 0.22)).normalized() * away, mid, 20),
        "back": review._camera("O_back", mid + Vector((0, 1.0, 0.25)).normalized() * away, mid, 20),
        "game": review._camera("O_game", Vector((gx, -gd, 5.5)), Vector((gx, 0.0, 1.6)), 70),
    }
    for c in cams.values():
        c.data.clip_end = 2000.0
    folder = os.path.splitext(out)[0] + "_views" if keep_views else tempfile.mkdtemp(prefix="ores_views_")
    os.makedirs(folder, exist_ok=True)
    W, T = 2100, 525
    row_h = 520
    rows = [(shoot(rig, cams["front"], os.path.join(folder, "front.png"), (W, row_h)), "all seven in tier order, front three-quarters")]
    if clay:
        rows.append((shoot(rig, cams["front"], os.path.join(folder, "front_clay.png"), (W, row_h), "clay"), "clay"))
    allobs = [ob for p in props for ob in p.objects]
    close = []
    for p, label in zip(props, labels):
        lo_p, hi_p = extent(p)
        c = (lo_p + hi_p) / 2
        cam = review._camera("O_close_" + label, c + Vector((0, -1.0, 0.3)).normalized() * 11.0, c + Vector((0, 0, -0.1)), 30)
        close.append((shoot(rig, cam, os.path.join(folder, "close_%s.png" % label), (T, T),
                            hide=[ob for ob in allobs if ob not in p.objects]), label))
    if "geode" in labels:
        p = props[labels.index("geode")]
        lo_p, hi_p = extent(p)
        c = (lo_p + hi_p) / 2 + Vector((0, 0, 0.35))
        cam = review._camera("O_close_opening", c + Vector((0.25, -1.0, 0.75)).normalized() * 6.2, c, 30)
        close.append((shoot(rig, cam, os.path.join(folder, "close_opening.png"), (T, T),
                            hide=[ob for ob in allobs if ob not in p.objects]), "geode opening"))
    rows.append((close, None))
    rows.append((shoot(rig, cams["back"], os.path.join(folder, "back.png"), (W, row_h)), "all seven from behind"))
    rows.append((shoot(rig, cams["game"], os.path.join(folder, "game.png"), (W, 640)),
                 "game distance (%.0f studs, FOV 70, eye 5.5 studs up) next to the 5-stud block" % gd))
    rows.append((shoot(rig, cams["front"], os.path.join(folder, "front_sil.png"), (W, row_h), "silhouette"), "silhouettes"))
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = ImageFont.truetype(f, 16) if os.path.exists(f) else ImageFont.load_default()
    sz = lambda q: Image.open(q).size
    heights = [(T * ((len(t) + 3) // 4) if isinstance(t, list) else int(sz(t)[1] * W / sz(t)[0])) for t, _ in rows]
    img = Image.new("RGB", (W, sum(heights) + 34), (18, 20, 24))
    draw = ImageDraw.Draw(img)
    draw.text((10, 8), title, fill=(235, 235, 235), font=font)
    y = 34

    def label_at(x, yy, text):
        w = draw.textlength(text, font=font)
        draw.rectangle((x, yy, x + w + 12, yy + 22), fill=(0, 0, 0))
        draw.text((x + 6, yy + 2), text, fill=(255, 255, 255), font=font)

    for (t, label), h in zip(rows, heights):
        if isinstance(t, list):
            for i, (q, lab) in enumerate(t):
                x, yy = (i % 4) * T, y + (i // 4) * T
                img.paste(Image.open(q).convert("RGB").resize((T, T)), (x, yy))
                label_at(x, yy, "close-up: " + lab)
        else:
            img.paste(Image.open(t).convert("RGB").resize((W, h)), (0, y))
            label_at(0, y, label)
        y += h
    img.save(out)
    if not keep_views:
        shutil.rmtree(folder, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated rocks to build: " + ", ".join(ORES))
    ap.add_argument("--export-dir", default=os.path.join(MODELS, "export"))
    ap.add_argument("--sheet", default=os.path.join(MODELS, "preview", "ores.png"))
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--peek", help="quick unbaked look: write the sheet here and stop")
    ap.add_argument("--fast", action="store_true", help="512 textures, few samples, smaller renders")
    ap.add_argument("--clay", action="store_true", help="add the row in clay to the sheet")
    ap.add_argument("--keep-views", action="store_true", help="keep each view's render in a folder beside the sheet")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--title", default="Ore rocks")
    a = ap.parse_args()
    if a.fast:
        os.environ["PETS_FAST"] = "1"
    keys = list(ORES)
    if a.only:
        want = [w.strip().lower().replace("_ore", "").replace("ore", "") for w in a.only.split(",")]
        keys = [k for k in keys if k in want]
    kit.fresh()
    props, labels = [], []
    for i, key in enumerate(keys):
        name, builder, settings = ORES[key]
        prop = builder()
        print("%s: triangles by part %s" % (name, dict(sorted(prop.tally.items(), key=lambda kv: -kv[1]))), flush=True)
        if not a.peek:
            os.makedirs(a.export_dir, exist_ok=True)
            bake(prop, name, os.path.join(a.export_dir, snake(name) + "_colour.png"), settings, size=a.size,
                 samples=16 if a.fast else a.samples)
            size = 512 if a.fast else a.size
            st = numbers(prop, size)
            print("%s: triangles %s total %d; %.2f wide, %.2f deep, %.2f tall studs, lowest z %.3f; texture %d px, %.0f%% of it used, %.0f px per stud"
                  % (name, st["tris"], st["total"], st["size"][0], st["size"][1], st["size"][2], st["low"], size, st["used"] * 100, st["px_per_stud"]), flush=True)
            if not a.no_export:
                path = os.path.join(a.export_dir, snake(name) + ".fbx")
                kit.export_fbx(prop.objects, path)
                print("exported", path, flush=True)
        else:
            st = numbers_raw(prop)
            print("%s: %d triangles; %.2f wide, %.2f deep, %.2f tall" % (name, st[0], *st[1]), flush=True)
        for ob in prop.objects:
            ob.location.x = 400 + 80 * i               # out of the way while the next one is baked
        props.append(prop)
        labels.append(key)
    out = a.peek or (None if a.no_sheet else a.sheet)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        sheet(props, labels, os.path.abspath(out), samples=12 if (a.peek or a.fast) else a.samples,
              scale=0.5 if (a.peek or a.fast) else 1.0, title=a.title, keep_views=a.keep_views, clay=a.clay or bool(a.peek))
        print("sheet", out, flush=True)


def numbers_raw(prop):
    lo, hi = extent(prop)
    return sum(prop.triangles().values()), (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)


if __name__ == "__main__":
    main()
