"""Hatching eggs for "Mine an Egg": one egg for each family of pets. Built from scratch by script.

    python models/eggs/eggs.py                       # all six: Roblox files in models/export, sheet in models/preview/eggs.png
    python models/eggs/eggs.py --only ember          # just one or a few (meadow, ember, phoenix, storm, crystal, shadow)
    python models/eggs/eggs.py --peek out.png        # a quick unbaked look while building

Every egg is about 4.5 studs tall and 3.3 wide, stands on a slightly flattened bottom at z = 0 and faces
-Y. It arrives in Roblox as at most two MeshParts: <Name>_Body, with its colours and soft shading baked
into one 1024 image (<name>_colour.png, with <name>_rough.png beside it), and <Name>_GLOW, with one
emissive GLOW_ material (the Meadow Egg has none). Each is under 4,000 triangles.

Styles, one per family:
  Meadow  (cute toy pets)   warm cream eggshell, soft pastel painted speckles, a few raised glaze dabs and
                            a hairline crack near the top, as if it is about to hatch
  Ember   (obsidian dragon) eight rows of overlapping black obsidian scales with keels and real walls, ember-red
                            edges, small glowing ember peeks where the scale points meet, three bone-tipped horn nubs
  Phoenix (phoenix)         six rows of crimson-to-gold blade feathers swirling up the shell, flames glowing on the
                            top rows
  Storm   (storm griffin)   white storm-veined porcelain held by twelve navy enamel wing blades with silver rims,
                            lightning cracks striking down the front and back, streaks on the tallest blades
  Crystal (crystal golem)   hewn slate slabs with dark cracks, broken open at the front and the back, emerald
                            crystals lit from inside pushing out of a green-lit hollow
  Shadow  (shadow wolf)     smoky indigo shell, three silver claw grooves, a seal of violet runes between pewter
                            rings, a crest of violet-lit shards up the back

Practice rounds (eggs_v1.py ... eggs_v6.py beside this file):
  1  all six built. The flat bottom was 2 studs wide (bullet shapes), Ember glowed in big triangles, Storm's
     wings were stray fins, Crystal's crater was capped by the old faces, Shadow had zebra stripes.
  2  a true egg outline (flat bottom about 0.9 studs across), crater fixed, Storm as a crown of navy blades,
     smoky Shadow, denser Meadow speckles.
  3  Ember's rows kept at eight scales so they stagger exactly, crystals lit through slits between their
     facets in a smooth hollow, bigger speckles, calmer smoke.
  4  Ember's scale roots run on up under the row above, twelve fanned Storm blades, crystals aimed up and out
     so they are seen side on, the Shadow rune seal. First full bake.
  5  a little ember light let back in (root overlap 0.22), darker obsidian, lightning streaks on Storm's
     tallest blades, a second break with crystals round Crystal's back, a shard crest up Shadow's back, a
     natural crack and softer contact shading on Meadow, an unwrap angle chosen per egg.
  6  Shadow's rings in thinner, darker pewter so the runes lead; the 5-stud block stands in line with the row.
"""
import argparse
import bisect
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "pets"))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import Prop  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, ".."))
LAYERS = ("g", "xn", "d", "f", "grad", "heat", "tag", "pal")


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


def sharpen(bm, degrees):
    """Mark the edges where the surface turns by more than `degrees` as sharp: crisp creases."""
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def flip_out(bm, out):
    """Turn a shape's faces so that, taken together, they face along out(point)."""
    bm.normal_update()
    tot = sum(f.normal.dot(out(f.calc_center_median())) * f.calc_area() for f in bm.faces)
    if tot < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


# ---- the egg itself ---------------------------------------------------------------------------------

class Egg:
    """The outline of an egg turned round the Z axis, and a way to find points on it.

    The side view is two superellipses meeting at the widest point (`widest` of the way up): fuller
    below (`bottom`), a little pointed above (`top`). The bottom is cut flat at `flat` of the height so
    the egg stands on its own. A point on the shell is (s, th): s runs along the outline from the
    middle of the flat bottom (0) to the top (1), th is degrees round, 0 facing -Y (the front) and 90
    facing +X."""

    def __init__(self, height=4.4, radius=1.6, widest=0.41, bottom=2.0, top=1.75, flat=0.018, n=900):
        raw = []
        for i in range(n + 1):
            phi = math.pi * i / n
            c, s = math.cos(phi), math.sin(phi)
            if i <= n // 2:
                raw.append((s ** (2.0 / bottom), widest * (1 - abs(c) ** (2.0 / bottom))))
            else:
                raw.append((s ** (2.0 / top), widest + (1 - widest) * abs(c) ** (2.0 / top)))
        rc = raw[1][0]
        for (r0, z0), (r1, z1) in zip(raw, raw[1:]):
            if z0 < flat <= z1:
                rc = r0 + (r1 - r0) * (flat - z0) / (z1 - z0)
                break
        prof = [(rc * j / 6, flat) for j in range(6)] + [(rc, flat)] + [p for p in raw if p[1] > flat]
        pts = [(r * radius, (z - flat) / (1 - flat) * height) for r, z in prof]
        run = [0.0]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
            run.append(run[-1] + math.hypot(r1 - r0, z1 - z0))
        self.L = run[-1]
        self.s = [x / self.L for x in run]
        self.r = [p[0] for p in pts]
        self.z = [p[1] for p in pts]
        self.nr, self.nz = [], []
        for k in range(len(pts)):
            a, b = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
            tr, tz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tr, tz) or 1.0
            self.nr.append(tz / ln)
            self.nz.append(-tr / ln)
        self.nr[-1], self.nz[-1] = 0.0, 1.0
        self.height, self.radius = height, radius
        self.s_disk = self.s[6]
        self.zc = height * (widest - flat) / (1 - flat)
        self.phi = [math.atan2(z - self.zc, max(r, 1e-9)) for r, z in pts]

    def _at(self, s):
        s = min(max(s, 0.0), 1.0)
        j = min(max(bisect.bisect_right(self.s, s) - 1, 0), len(self.s) - 2)
        f = (s - self.s[j]) / max(self.s[j + 1] - self.s[j], 1e-12)
        return tuple(a[j] + (a[j + 1] - a[j]) * f for a in (self.r, self.z, self.nr, self.nz))

    def point(self, s, th, lift=0.0):
        r, z, nr, nz = self._at(s)
        a = math.radians(th)
        rr = r + nr * lift
        return Vector((math.sin(a) * rr, -math.cos(a) * rr, z + nz * lift))

    def normal(self, s, th):
        r, z, nr, nz = self._at(s)
        a = math.radians(th)
        return Vector((math.sin(a) * nr, -math.cos(a) * nr, nz)).normalized()

    def radius_at(self, s):
        return self._at(s)[0]

    def z_at(self, s):
        return self._at(s)[1]

    def s_at_z(self, z):
        j = max(6, min(bisect.bisect_right(self.z, z, lo=6) - 1, len(self.z) - 2))
        f = (z - self.z[j]) / max(self.z[j + 1] - self.z[j], 1e-12)
        return self.s[j] + (self.s[j + 1] - self.s[j]) * min(max(f, 0.0), 1.0)

    def walk(self, s, th, along, across):
        """(s, th) moved `along` studs up the shell and `across` studs round it (towards larger th)."""
        s2 = s + along / self.L
        r = max(self.radius_at((s + s2) / 2), 0.08)
        return s2, th + math.degrees(across / r)

    def frame(self, s, th):
        """Unit vectors up the shell and round it at (s, th), for turning (along, across) into 3D."""
        e = 1e-3
        up = (self.point(s + e, th) - self.point(s - e, th)).normalized()
        a = math.radians(th)
        return up, Vector((math.cos(a), math.sin(a), 0.0))

    def project(self, p):
        """The (s, th) of the shell point straight out from the egg's centre through p."""
        p = Vector(p)
        th = math.degrees(math.atan2(p.x, -p.y))
        phi = math.atan2(p.z - self.zc, math.hypot(p.x, p.y))
        j = min(max(bisect.bisect_right(self.phi, phi) - 1, 0), len(self.phi) - 2)
        f = (phi - self.phi[j]) / max(self.phi[j + 1] - self.phi[j], 1e-12)
        return self.s[j] + (self.s[j + 1] - self.s[j]) * min(max(f, 0.0), 1.0), th

    def from_sphere(self, d):
        """A point on the egg for a direction on the unit sphere, spread so that equal areas of the
        sphere land on roughly equal areas of the egg."""
        d = Vector(d).normalized()
        zz = self.zc + d.z * (self.zc if d.z < 0 else self.height - self.zc)
        return self.project((d.x * self.radius, d.y * self.radius, zz))

    def mesh(self, segs=24, rings=16, lift=0.0):
        """The shell as quads, with triangle fans at the two poles and a flat ring at the bottom."""
        bm = bmesh.new()
        ss = [self.s_disk * 0.5, self.s_disk] + [self.s_disk + (1 - self.s_disk) * i / rings for i in range(1, rings)]
        bottom = bm.verts.new(self.point(0.0, 0.0, lift))
        loops = [[bm.verts.new(self.point(s, 360.0 * j / segs, lift)) for j in range(segs)] for s in ss]
        top = bm.verts.new(self.point(1.0, 0.0, lift))
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((bottom, loops[0][k], loops[0][j]))
            for a, b in zip(loops, loops[1:]):
                bm.faces.new((a[j], a[k], b[k], b[j]))
            bm.faces.new((loops[-1][j], loops[-1][k], top))
        return flip_out(bm, self.outward)

    def outward(self, p):
        return Vector((p.x, p.y, p.z - self.zc))


# ---- shapes laid on the egg -------------------------------------------------------------------------

def strip(egg, path, widths, section, steps=None, smooth=True, taper=None, sink=0.03, sharp_cols=()):
    """A band laid on the shell along `path`, a list of (s, th) points. `widths` is the half width in
    studs at each point. `section` is the band's cross-section, (u, h, tag) going across: u from -1 to 1
    (times the half width), h the height above the shell in studs and tag a value for the material.
    Two neighbouring entries with the same u split the band there, for a crisp change of colour.
    `taper(t)` (0 to 1 along the band) lowers the band to `sink` below the shell at its ends.
    Smooth paths are splined; otherwise the points are joined by straight runs with mitred corners.
    Each vertex stores u in "xn", the distance along in "d", t in "grad" and the tag in "tag"."""
    bm = bmesh.new()
    lay = layers(bm)
    n = len(path)
    if smooth:
        steps = steps or (n - 1) * 4
        cen = [(_cr([p[0] for p in path], i / steps * (n - 1)), _cr([p[1] for p in path], i / steps * (n - 1))) for i in range(steps + 1)]
        wid = [_cr(list(widths), i / steps * (n - 1)) for i in range(steps + 1)]
    else:
        cen, wid = list(path), list(widths)
    m = len(cen)
    # directions in studs (up the shell, round it) and the distance along
    metric = []
    for i in range(m):
        s, th = cen[i]
        metric.append((s * egg.L, math.radians(th) * max(egg.radius_at(s), 0.08)))
    run = [0.0]
    for a, b in zip(metric, metric[1:]):
        run.append(run[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    rows = []
    for i in range(m):
        s, th = cen[i]
        d0 = d1 = None
        if i > 0:
            d0 = Vector((metric[i][0] - metric[i - 1][0], metric[i][1] - metric[i - 1][1])).normalized()
        if i < m - 1:
            d1 = Vector((metric[i + 1][0] - metric[i][0], metric[i + 1][1] - metric[i][1])).normalized()
        d = (d0 + d1).normalized() if (d0 and d1) else (d0 or d1)
        k = 1.0
        if d0 and d1 and not smooth:
            k = 1.0 / max(math.cos(d0.angle(d1, 0.0) / 2), 0.5)
        side = Vector((-d.y, d.x))                     # square to the path: (up, round)
        t = i / (m - 1)
        f = taper(t) if taper else 1.0
        row = []
        for u, h, tag in section:
            ss, tt = egg.walk(s, th, side.x * u * wid[i] * k, side.y * u * wid[i] * k)
            hh = -sink + (h + sink) * f
            v = bm.verts.new(egg.point(ss, tt, hh))
            v[lay["xn"]], v[lay["d"]], v[lay["grad"]], v[lay["tag"]] = u, run[i], t, tag
            row.append(v)
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for j in range(len(section) - 1):
            if section[j][0] == section[j + 1][0]:
                continue
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    for j in sharp_cols:
        for a, b in zip(rows, rows[1:]):
            e = bm.edges.get((a[j], b[j]))
            if e:
                e.smooth = False
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    return flip_out(bm, egg.outward)


def tile(egg, s0, s1, thc, half, lift=(-0.035, 0.11), keel=0.045, sink=0.06,
         qs=(-1, -0.5, 0, 0.5, 1), vs=(0.0, 0.6, 1.0), widths=(1.0, 0.9, 0.46), curve=0.4):
    """One overlapping scale lying on the egg: its root at s0 (higher up, buried in the shell), its
    rounded point at s1 (lower, standing lift[1] proud), `half` degrees to each side of `thc`. Its top
    is two planes meeting in a keel down the middle; its sides and point drop in walls to `sink` below
    the shell, so it has real thickness and casts a shadow on the scale below. "heat" is 1 on the
    walls and the edges of the top, for the glow of the seams."""
    bm = bmesh.new()
    lay = layers(bm)
    grid, where = [], {}
    for v, w in zip(vs, widths):
        row = []
        for q in qs:
            s = s0 + (s1 - s0) * v * (1 - curve * q * q)
            th = thc + half * w * q
            h = lift[0] + (lift[1] - lift[0]) * v ** 1.2 + keel * (1 - abs(q)) * min(1.0, 2.5 * v + 0.25)
            vert = bm.verts.new(egg.point(s, th, h))
            vert[lay["heat"]] = max(abs(q), v) ** 2
            vert[lay["grad"]] = v
            where[vert] = (s, th)
            row.append(vert)
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(len(qs) - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    mid = len(qs) // 2
    for a, b in zip(grid, grid[1:]):
        bm.edges.get((a[mid], b[mid])).smooth = False
    rim = [grid[i][-1] for i in range(len(vs))] + grid[-1][-2::-1] + [grid[i][0] for i in range(len(vs) - 2, -1, -1)]
    low = []
    for v in rim:
        s, th = where[v]
        b = bm.verts.new(egg.point(s, th, -sink))
        b[lay["heat"]], b[lay["grad"]] = 1.0, v[lay["grad"]]
        low.append(b)
    for i in range(len(rim) - 1):
        bm.faces.new((rim[i], rim[i + 1], low[i + 1], low[i]))
    return flip_out(bm, egg.outward)


def row(place, count, closed=False, cols=2, rows=3, depth=0.6, lift=0.08, sink=0.04, ridge=0.03, thick=0.03,
        g=(0.1, 0.4), gpow=1.0, L=0.6, point=1.0):
    """A row of pointed feathers as one closed sheet (from the phoenix). place(u, v) gives the point and
    the outward normal of the surface the row lies on: u runs across the row (feather j spans j to
    j + 1), v from the roots (0) to the tips (1). Between two feathers the tips are cut back by `depth`
    (`point` shapes the cut), so each one ends in a point. Each has a raised shaft (`ridge`), stands
    `lift` proud of the surface at its tip and is buried `sink` at its root, so the next row covers its
    root."""
    bm = bmesh.new()
    lay = layers(bm)
    ncol = count * cols + (0 if closed else 1)
    top, bot = [], []
    for c in range(ncol):
        u = c / cols
        q = 2.0 * (c % cols) / cols - 1.0                                  # -1 between feathers, 0 on a shaft
        vt = 1.0 - depth * abs(q) ** point
        tc, bc = [], []
        for r in range(rows + 1):
            v = vt * r / rows
            p, nrm = place(u, v)
            up = -sink + (lift + sink) * v ** 1.2 + ridge * (1 - abs(q)) * min(1.0, 3 * v + 0.3)
            rim = r in (0, rows) or (not closed and c in (0, ncol - 1))
            for lst, off in ((tc, up), (bc, up - thick * (0.5 + 0.5 * v))):
                if rim and lst is bc:
                    bc.append(tc[-1])
                    continue
                vert = bm.verts.new(p + nrm * off)
                vert[lay["g"]], vert[lay["xn"]], vert[lay["d"]], vert[lay["f"]] = g[0] + (g[1] - g[0]) * v ** gpow, q, v * L, 1.0
                lst.append(vert)
        top.append(tc)
        bot.append(bc)
    pairs = [(c, (c + 1) % ncol) for c in range(ncol if closed else ncol - 1)]
    for c, d in pairs:
        for r in range(rows):
            bm.faces.new((top[c][r], top[d][r], top[d][r + 1], top[c][r + 1]))
            bm.faces.new((bot[c][r + 1], bot[d][r + 1], bot[d][r], bot[c][r]))
        bm.edges.get((top[c][rows], top[d][rows])).smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def dab(egg, s, th, radius, height, pal=0.0, k=10):
    """A soft raised drop of paint on the shell: domed, its rim sunk just under the surface."""
    bm = bmesh.new()
    lay = layers(bm)
    c = bm.verts.new(egg.point(s, th, height))
    rings = []
    for rho, hh in ((0.6, height * 0.78), (1.0, -0.012)):
        ring = []
        for j in range(k):
            a = 2 * math.pi * j / k
            ss, tt = egg.walk(s, th, math.cos(a) * radius * rho, math.sin(a) * radius * rho)
            ring.append(bm.verts.new(egg.point(ss, tt, hh)))
        rings.append(ring)
    for v in bm.verts:
        v[lay["pal"]] = pal
    a, b = rings
    for j in range(k):
        jj = (j + 1) % k
        bm.faces.new((c, a[j], a[jj]))
        bm.faces.new((a[j], b[j], b[jj], a[jj]))
    return flip_out(bm, egg.outward)


def loft(points, radii, profile, up=(0, 0, 1), rings=None):
    """A 2D `profile` carried along a smooth path through `points` (from the dragon). Every vertex stores
    how far along it is (0 to 1) in "grad"."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = rings or (n - 1) * 3
    bm = bmesh.new()
    lay = layers(bm)
    path = [_cr(pts, i / rings * (n - 1)) for i in range(rings + 1)]
    loops = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        z = Vector(up) - t * Vector(up).dot(t)
        z = z.normalized() if z.length > 1e-6 else t.orthogonal().normalized()
        x = z.cross(t)
        r = max(_cr(list(radii), i / rings * (n - 1)), 1e-3)
        ring = []
        for a, b in profile:
            v = bm.verts.new(p + x * (a * r) + z * (b * r))
            v[lay["grad"]] = i / rings
            ring.append(v)
        loops.append(ring)
    m = len(profile)
    for a, b in zip(loops, loops[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    for ring, tip in ((loops[0], path[0]), (loops[-1], path[-1])):
        c = bm.verts.new(tip)
        c[lay["grad"]] = ring[0][lay["grad"]]
        for j in range(m):
            bm.faces.new((ring[j], ring[(j + 1) % m], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


P_HORN = [(0, 1.0), (0.8, 0.3), (0.6, -0.7), (0, -0.9), (-0.6, -0.7), (-0.8, 0.3)]


def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35):
    """A hexagonal crystal along +Z (from the golem): a slightly tapering, slightly irregular prism
    from `sink` below its foot to a pointed tip. "grad" runs 0 at the foot to 1 at the tip."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = layers(bm)
    turn = rnd.uniform(0, math.pi / 3)
    tip_h = min(radius * rnd.uniform(*tip), length * 0.45)
    shoulder = length - tip_h
    taper = rnd.uniform(0.78, 0.92)
    radii = [radius * rnd.uniform(0.9, 1.1) for _ in range(6)]
    rings = []
    for z, s, g in ((-sink * radius - 0.05, 1.0, 0.0), (shoulder, taper, 0.8)):
        ring = []
        for j in range(6):
            a = turn + j * math.pi / 3
            v = bm.verts.new((math.cos(a) * radii[j] * s, math.sin(a) * radii[j] * s, z))
            v[lay["grad"]] = g
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.15, 0.15) * radius, rnd.uniform(-0.15, 0.15) * radius, length))
    apex[lay["grad"]] = 1.0
    lo, hi = rings
    for j in range(6):
        k = (j + 1) % 6
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lit_crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, slit=0.015):
    """A crystal lit from inside: its facets stand a hair apart and a glowing core fills it, so the
    light shows along every edge. Returns (facets, core)."""
    whole = crystal(length, radius, seed, tip, sink)
    src = whole.verts.layers.float.get("grad")
    facets = bmesh.new()
    lay = layers(facets)
    for f in whole.faces:
        c = f.calc_center_median()
        vs = []
        for v in f.verts:
            d = v.co - c
            nv = facets.verts.new(c + d * max(0.0, 1 - slit / max(d.length, 1e-6)))
            nv[lay["grad"]] = v[src]
            vs.append(nv)
        facets.faces.new(vs)
    for e in facets.edges:
        e.smooth = False
    whole.free()
    return facets, crystal(length * 0.95, radius * 0.78, seed, tip, sink)


def aim(origin, direction, roll=0.0):
    """A transform standing a shape built along +Z on `origin`, pointing along `direction`."""
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


def sphere_cells(n, seed, jitter=0.6):
    """Voronoi cells on the unit sphere round n roughly even seeds: [(seed, [corner, ...]), ...], the
    corners in order round the seed (the circumcentres of the seeds' Delaunay triangles)."""
    rnd = random.Random(seed)
    ga = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        p = Vector((r * math.cos(i * ga), r * math.sin(i * ga), z))
        p += Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))) * jitter / math.sqrt(n)
        pts.append(p.normalized())
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    centre = {}
    for f in bm.faces:
        a, b, c = (v.co for v in f.verts[:3])
        nrm = (b - a).cross(c - a).normalized()
        if nrm.dot(a + b + c) < 0:
            nrm = -nrm
        centre[f] = nrm
    cells = []
    for v in vs:
        p = v.co.copy()
        e1 = p.orthogonal().normalized()
        e2 = p.cross(e1)
        cs = sorted((centre[f] for f in v.link_faces), key=lambda c: math.atan2(c.dot(e2), c.dot(e1)))
        cells.append((p, cs))
    bm.free()
    return cells


def stone_plate(egg, centre, corners, rnd, gap=0.05, chamfer=0.07, h=0.13, sink=0.05, tilt=0.05, away=None, lean=0.0):
    """A hewn slab of stone lying on the egg over one cell: a flat top a little tilted (`tilt`), its
    edge cut by a chamfer down to `sink` below the shell, `gap` short of the cell's edge so a dark
    crack runs between it and its neighbours. With `away` (a point) the slab's edge nearest that point
    is lifted by `lean`, as if pushed open from inside."""
    cs, cth = egg.project(centre)
    C, Nc = egg.point(cs, cth), egg.normal(cs, cth)
    Np = (Nc + Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))) * tilt).normalized()
    if away is not None:
        u = Vector(away) - C
        u = (u - Nc * u.dot(Nc)).normalized()
        Np = (Np - u * lean).normalized()
    P0 = C + Nc * h * rnd.uniform(0.85, 1.15)
    bm = bmesh.new()
    layers(bm)
    outer, mid, top = [], [], []
    for P in corners:
        d = P - C
        ln = max(d.length, 1e-6)
        qs, qt = egg.project(C + d * max(0.05, (ln - gap) / ln))
        outer.append(bm.verts.new(egg.point(qs, qt, -sink)))
        rs, rt = egg.project(C + d * max(0.05, (ln - gap - chamfer) / ln))
        R = egg.point(rs, rt)
        t = max((P0 - R).dot(Np) / max(Nc.dot(Np), 0.3), 0.035)
        top.append(bm.verts.new(R + Nc * t))
        ms, mt = egg.project(C + d * max(0.05, (ln - gap - chamfer * rnd.uniform(0.2, 0.45)) / ln))
        mid.append(bm.verts.new(egg.point(ms, mt) + egg.normal(ms, mt) * t * rnd.uniform(0.45, 0.8)))
    k = len(corners)
    bm.faces.new(top)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((mid[i], mid[j], top[j], top[i]))
        bm.faces.new((outer[i], outer[j], mid[j], mid[i]))
    for e in bm.edges:
        e.smooth = False
    return flip_out(bm, egg.outward)


def bolt_path(egg, s, th, heading, length, seed, step=(0.18, 0.3), jag=(0.06, 0.13)):
    """A jagged path for a lightning crack: from (s, th), heading (up, round) in studs, for `length`."""
    rnd = random.Random(seed)
    h = Vector(heading).normalized()
    side = Vector((-h.y, h.x))
    pts, d, sgn = [(s, th)], 0.0, 1
    bs, bt = s, th
    while d < length:
        stp = rnd.uniform(*step)
        d += stp
        bs, bt = egg.walk(bs, bt, h.x * stp, h.y * stp)
        j = rnd.uniform(*jag) * sgn
        sgn = -sgn
        pts.append(egg.walk(bs, bt, side.x * j, side.y * j))
    return pts


def crack_path(egg, s, th, heading, length, seed, step=(0.09, 0.2), jag=0.07):
    """A natural crack: short runs of uneven length, each turned a random amount from the heading."""
    rnd = random.Random(seed)
    h = Vector(heading).normalized()
    pts, d = [(s, th)], 0.0
    while d < length:
        stp = rnd.uniform(*step)
        d += stp
        turn = rnd.uniform(-1.0, 1.0) * 0.9
        dirn = Matrix.Rotation(turn, 2) @ h
        s, th = egg.walk(s, th, dirn.x * stp, dirn.y * stp)
        side = Vector((-h.y, h.x)) * rnd.uniform(-jag, jag)
        pts.append(egg.walk(s, th, side.x, side.y))
    return pts


# ---- materials -----------------------------------------------------------------------------------------

class Nodes:
    """A few shortcuts for building shader node trees (from the golem)."""

    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new

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

    def mix(self, fac, a, b):
        m = self.new("ShaderNodeMix")
        m.data_type = 'RGBA'
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

    def up(self, lo, hi):
        geo = self.new("ShaderNodeNewGeometry")
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(geo.outputs["Normal"], sep.inputs[0])
        return self.ramp(sep.outputs[2], lo, hi)

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

    def finish(self, mat, col, rough):
        b = kit.principled(mat)
        self.link(col, b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = rough
        return mat


def ramp_mat(name, stops, attr="g", rough=0.7, streak=None):
    """A colour ramp read from a vertex value, with kit.furry's fine streaks over it."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, **(streak or dict(strength=0.08, mottle=0.06, fine=40.0, length=3.0)))
    N = Nodes(m)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    N.link(N.colours(N.attr(attr), stops), hsv.inputs["Color"])
    kit.principled(m).inputs["Roughness"].default_value = rough
    return m, hsv


def vane(mat, hsv, period=0.1, slant=0.16, shaft=0.07):
    """Draw a feather on every feather blade (from the phoenix): a pale shaft and fine barbs."""
    N = Nodes(mat)
    ax = N.math('ABSOLUTE', N.attr("xn"))
    phase = N.math('MULTIPLY_ADD', ax, -slant, N.attr("d"))
    wave = N.math('SINE', N.math('MULTIPLY', phase, 2 * math.pi / period))
    barbs = N.math('MULTIPLY_ADD', wave, 0.08, 1.0)
    lit = N.math('MULTIPLY_ADD', N.ramp(ax, shaft, 0.0, 0.0, 1.0, smooth=False), 0.35, barbs)
    edge = N.ramp(ax, 0.65, 1.0, 1.0, 0.75, smooth=False)
    pattern = N.math('MULTIPLY', lit, edge)
    mixed = N.math('MULTIPLY_ADD', N.math('SUBTRACT', pattern, 1.0), N.attr("f"), 1.0)
    old = hsv.inputs["Value"].links[0].from_socket
    N.link(N.math('MULTIPLY', old, mixed), hsv.inputs["Value"])


def glow_material(name, hexcode, emit):
    return kit.material("GLOW_" + name, hexcode, rough=0.4, emit=emit)


def meadow_shell(name):
    """Warm cream eggshell: deeper and warmer low down, a fine porous stipple, soft mottling, and
    painted speckles in pastel colours in three sizes, with soft, slightly ragged edges."""
    m = kit.material(name, "#F4E7CC", rough=0.72)
    N = Nodes(m)
    co = N.coord()
    z = N.height(co)
    col = N.mix(N.ramp(z, 0.2, 4.2), "#E8D0A2", "#FBF3E0")
    stipple = N.math('MULTIPLY_ADD', N.noise(co, 42.0, 2.0).outputs["Fac"], 0.12, 0.94)
    mottle = N.math('MULTIPLY_ADD', N.noise(co, 1.8, 3.0).outputs["Fac"], 0.1, 0.95)
    col = N.value(col, N.math('MULTIPLY', stipple, mottle))
    warped = N.warp(co, 4.0, 0.08)
    palette = [(0.0, "#F2A2B6"), (0.18, "#9FDCC0"), (0.36, "#C4AEE6"), (0.54, "#9FCAF0"), (0.72, "#F5D686"), (0.86, "#F7B996"), (1.0, "#F7B996")]
    for scale, size, keep_above, amount in ((1.8, 0.3, 0.55, 0.85), (3.6, 0.3, 0.35, 0.85), (7.5, 0.28, 0.3, 0.8), (15.0, 0.25, 0.35, 0.7)):
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        N.link(warped, vor.inputs["Vector"])
        sep = N.new("ShaderNodeSeparateColor")
        N.link(vor.outputs["Color"], sep.inputs[0])
        r_size = N.math('MULTIPLY_ADD', sep.outputs["Blue"], size * 0.6, size * 0.55)
        inside = N.math('LESS_THAN', vor.outputs["Distance"], r_size)
        soft = N.ramp(N.math('SUBTRACT', vor.outputs["Distance"], r_size), -0.06, 0.02, 1.0, 0.0)
        keep = N.math('GREATER_THAN', sep.outputs["Red"], keep_above)
        dot = N.math('MULTIPLY', N.math('MAXIMUM', soft, N.math('MULTIPLY', inside, 0.0)), keep)
        paint = N.colours(sep.outputs["Green"], palette, constant=True)
        col = N.mix(N.math('MULTIPLY', dot, amount), col, paint)
    col = N.mix(N.math('GREATER_THAN', N.attr("tag"), 0.5), col, "#5E4430")       # the inside of a crack
    return N.finish(m, col, 0.72)


def dab_material(name):
    m = kit.material(name, "#F2A2B6", rough=0.6)
    N = Nodes(m)
    co = N.coord()
    palette = [(0.0, "#EE93AA"), (0.18, "#8ED4B4"), (0.36, "#B79FE0"), (0.54, "#8DBDEB"), (0.72, "#F2CC6E"), (0.86, "#F4A983"), (1.0, "#F4A983")]
    col = N.colours(N.attr("pal"), palette, constant=True)
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 30.0, 2.0).outputs["Fac"], 0.12, 0.94))
    col = N.mix(N.math('MULTIPLY', N.up(0.2, 0.9), 0.18), col, "#FFFFFF")
    return N.finish(m, col, 0.6)


def obsidian(name, heat=True):
    """Black volcanic glass: every scale its own shade, faint glassy bands, paler glints where it faces
    up and on its sharp edges, and (with `heat`) a deep ember red on the walls and edges of each scale,
    where the light from the seams falls."""
    m = kit.material(name, "#1C1A21", rough=0.5)
    N = Nodes(m)
    co = N.coord()
    warped = N.warp(co, 1.2, 0.4)
    # conchoidal ripples, the way volcanic glass breaks: faint rings round random centres
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.5
    N.link(warped, vor.inputs["Vector"])
    rings = N.math('SINE', N.math('MULTIPLY', vor.outputs["Distance"], 38.0))
    bands = N.ramp(rings, 0.7, 1.0)
    sheen = N.ramp(N.noise(co, 0.9, 3.0).outputs["Fac"], 0.4, 0.7)
    col = N.mix(sheen, "#121015", "#191A25")
    col = N.mix(N.math('MULTIPLY', bands, 0.12), col, "#4C4760")
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]
    speck = N.math('MULTIPLY_ADD', N.noise(co, 24.0, 3.0).outputs["Fac"], 0.25, 0.88)
    col = N.value(col, N.math('MULTIPLY', N.math('MULTIPLY_ADD', island, 0.35, 0.82), speck))
    col = N.mix(N.math('MULTIPLY', N.up(0.25, 0.95), 0.28), col, "#353142")
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.5), col, "#6A6278")
    if heat:
        flicker = N.ramp(N.noise(co, 3.5, 3.0).outputs["Fac"], 0.35, 0.65, 0.55, 1.0)
        hot = N.math('MULTIPLY', N.ramp(N.attr("heat"), 0.72, 1.0), flicker)
        col = N.mix(N.math('MULTIPLY', hot, 0.8), col, "#A3300A")
    return N.finish(m, col, 0.55)


def porcelain(name):
    """White storm porcelain: pale cloud-grey veins and patches like a stormy sky, a faint blue in
    what faces down, a fine grain."""
    m = kit.material(name, "#EEF1F5", rough=0.55)
    N = Nodes(m)
    co = N.coord()
    warped = N.warp(co, 0.9, 0.5)
    vn = N.noise(warped, 1.4, 6.0, 0.55)
    ridge = N.math('ABSOLUTE', N.math('SUBTRACT', vn.outputs["Fac"], 0.5))
    vein = N.ramp(ridge, 0.05, 0.0, 0.0, 1.0)
    clouds = N.ramp(N.noise(co, 0.8, 4.0).outputs["Fac"], 0.45, 0.7)
    col = N.mix(N.math('MULTIPLY', clouds, 0.4), "#F3F5F8", "#C9D2DE")
    col = N.mix(N.math('MULTIPLY', vein, 0.55), col, "#9FAABB")
    col = N.mix(N.math('MULTIPLY', N.up(-0.2, -0.9), 0.35), col, "#B4C2D6")
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 36.0, 2.0).outputs["Fac"], 0.08, 0.96))
    col = N.mix(N.ramp(N.height(co), 0.42, 0.3), col, "#121B36")              # the navy foot the wing blades rise from
    return N.finish(m, col, 0.55)


def enamel(name):
    """Navy enamel wing blades: darker at the root, a drawn feather (pale shaft, fine slanting barbs)
    and brushed silver on the bevelled rims (tag 1)."""
    m = kit.material(name, "#1C2A4E", rough=0.5)
    N = Nodes(m)
    co = N.coord()
    col = N.colours(N.attr("grad"), [(0.0, "#0F1730"), (0.5, "#1C2C55"), (1.0, "#2C4579")])
    ax = N.math('ABSOLUTE', N.attr("xn"))
    phase = N.math('MULTIPLY_ADD', ax, -0.22, N.attr("d"))
    barbs = N.math('MULTIPLY_ADD', N.math('SINE', N.math('MULTIPLY', phase, 2 * math.pi / 0.12)), 0.07, 1.0)
    col = N.value(col, N.math('MULTIPLY', barbs, N.math('MULTIPLY_ADD', N.noise(co, 30.0, 2.0).outputs["Fac"], 0.12, 0.94)))
    col = N.mix(N.ramp(ax, 0.07, 0.0), col, "#7D93BD")
    brushed = N.math('MULTIPLY_ADD', N.noise(co, 60.0, 2.0).outputs["Fac"], 0.2, 0.9)
    silver = N.value(N.mix(N.up(-0.3, 0.8), "#8E99AA", "#E2E7EE"), brushed)
    col = N.mix(N.math('GREATER_THAN', N.attr("tag"), 0.5), col, silver)
    return N.finish(m, col, 0.45)


def stone(name, base="#3C3F43", warm="#54493E", edge="#9A958A", crack="#141516", moss="#34452A",
          moss_amount=0.0, wear=0.7, cracks=0.75, rough=0.92, vary=0.34, tint=None):
    """Weathered slate (from the golem): every slab its own shade, warm and cool patches, faint strata,
    mineral grains, cracks, paler chipped edges and dark moss on what faces up."""
    m = kit.material(name, base, rough=rough)
    N = Nodes(m)
    co = N.coord()
    warped = N.warp(co, 1.4, 0.3)
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]
    big = N.noise(co, 0.55, 3.0)
    warmth = N.math('ADD', N.ramp(big.outputs["Fac"], 0.42, 0.64), N.math('MULTIPLY_ADD', island, 0.8, -0.3))
    col = N.mix(N.math('MULTIPLY', N.math('MINIMUM', N.math('MAXIMUM', warmth, 0.0), 1.0), 0.85), base, warm)
    strata = N.new("ShaderNodeTexWave")
    strata.bands_direction = 'Z'
    strata.inputs["Scale"].default_value, strata.inputs["Distortion"].default_value = 2.2, 6.0
    strata.inputs["Detail"].default_value = 2.0
    N.link(warped, strata.inputs["Vector"])
    lay = N.math('MULTIPLY_ADD', strata.outputs["Fac"], 0.1, 0.95)
    cells = N.new("ShaderNodeTexVoronoi")
    cells.inputs["Scale"].default_value = 2.6
    N.link(warped, cells.inputs["Vector"])
    bw = N.new("ShaderNodeRGBToBW")
    N.link(cells.outputs["Color"], bw.inputs[0])
    grain = N.math('MULTIPLY_ADD', bw.outputs[0], 0.3, 0.85)
    speck = N.noise(co, 13.0, 6.0, 0.62)
    fine = N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.44, 0.78)
    tone = N.math('MULTIPLY_ADD', island, vary, 1.0 - vary * 0.55)
    col = N.value(col, N.math('MULTIPLY', N.math('MULTIPLY', grain, fine), N.math('MULTIPLY', tone, lay)))
    cr = N.new("ShaderNodeTexVoronoi")
    cr.feature = 'DISTANCE_TO_EDGE'
    cr.inputs["Scale"].default_value = 1.15
    N.link(warped, cr.inputs["Vector"])
    line = N.ramp(cr.outputs["Distance"], 0.0, 0.045, 1.0, 0.0)
    where = N.ramp(N.noise(co, 1.3, 3.0).outputs["Fac"], 0.5, 0.6)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', line, where), cracks), col, crack)
    worn = N.ramp(N.noise(co, 5.0, 4.0, 0.65).outputs["Fac"], 0.32, 0.6, 0.25, 1.0)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', N.edge(0.035), worn), wear), col, edge)
    if moss_amount:
        patch = N.ramp(N.noise(co, 1.2, 4.0, 0.6).outputs["Fac"], 0.47, 0.55)
        mo = N.math('MULTIPLY', N.math('MULTIPLY', N.up(0.42, 0.78), patch), moss_amount)
        mossy = N.value(N.mix(0.0, moss, moss), N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.7, 0.65))
        col = N.mix(mo, col, mossy)
    if tint:
        at, reach, hexcode, amount = tint
        dist = N.new("ShaderNodeVectorMath")
        dist.operation = 'DISTANCE'
        N.link(co, dist.inputs[0])
        dist.inputs[1].default_value = tuple(at)
        col = N.mix(N.math('MULTIPLY', N.ramp(dist.outputs["Value"], reach, reach * 0.3), amount), col, hexcode)
    return N.finish(m, col, rough)


def crystal_material(name):
    """Emerald (from the golem): dark at the foot, clear green in the body, pale at the tip, each facet
    lighter or darker by the way it faces, its edges catching the light."""
    m = kit.material(name, "#12784C", rough=0.3)
    N = Nodes(m)
    col = N.colours(N.attr("grad"), [(0.0, "#021A0F"), (0.4, "#063F25"), (0.8, "#0F6E40"), (1.0, "#7FD6A8")])
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    N.link(geo.outputs["True Normal"], dot.inputs[0])
    dot.inputs[1].default_value = (-0.45, -0.55, 0.7)
    col = N.value(col, N.math('MULTIPLY_ADD', dot.outputs["Value"], 0.4, 1.0))
    col = N.mix(N.math('MULTIPLY', N.edge(0.025, 0.995, 0.9), 0.32), col, "#A8EBC8")
    return N.finish(m, col, 0.3)


def crease_edge(N, radius=0.02, lo=0.995, hi=0.93):
    """1 along the crisp (sharp-marked) edges of a smooth-shaded shape, 0 elsewhere. Nodes.edge() measures
    against the flat face normal, so on coarse smooth-shaded faces it lights whole faces; this measures the
    rounded bevel normal against the shading normal instead."""
    bev = N.new("ShaderNodeBevel")
    bev.samples = 4
    bev.inputs["Radius"].default_value = radius
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    N.link(bev.outputs["Normal"], dot.inputs[0])
    N.link(geo.outputs["Normal"], dot.inputs[1])
    return N.ramp(dot.outputs["Value"], lo, hi)


def shadow_shell(name, glow_at=None):
    """Dark slate-indigo, matte, like a night sky: slow smoky wisps of paler slate drifting round it, a fine
    grain, faint silver stars scattered over the upper shell, a cold silver frost where it faces up, paler
    worn edges, and a violet bloom painted round `glow_at` (a list of (point, reach)), where the light from
    inside spills out of the cracks."""
    m = kit.material(name, "#1C1E36", rough=0.72)
    N = Nodes(m)
    co = N.coord()
    warped = N.warp(N.warp(co, 0.55, 1.1), 1.3, 0.35)
    fil = N.noise(warped, 0.9, 5.0, 0.6)
    ridge = N.math('ABSOLUTE', N.math('SUBTRACT', fil.outputs["Fac"], 0.5))
    smoke = N.ramp(ridge, 0.07, 0.0)
    haze = N.ramp(N.noise(warped, 0.7, 3.0).outputs["Fac"], 0.45, 0.7)
    col = N.mix(N.math('MULTIPLY', haze, 0.55), "#181A31", "#232744")
    col = N.mix(N.math('MULTIPLY', smoke, 0.2), col, "#363C64")
    col = N.value(col, N.math('MULTIPLY_ADD', N.noise(co, 30.0, 3.0).outputs["Fac"], 0.2, 0.9))
    col = N.mix(N.math('MULTIPLY', N.up(0.35, 0.95), 0.3), col, "#566089")
    sky = N.ramp(N.height(co), 2.2, 2.8)
    for scale, keep, size, amount in ((4.0, 0.86, 0.09, 0.55), (1.9, 0.93, 0.07, 0.8)):
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        N.link(co, vor.inputs["Vector"])
        sep = N.new("ShaderNodeSeparateColor")
        N.link(vor.outputs["Color"], sep.inputs[0])
        star = N.math('MULTIPLY', N.ramp(vor.outputs["Distance"], size, size * 0.35), N.math('GREATER_THAN', sep.outputs["Red"], keep))
        col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', star, sky), amount), col, "#D4D8F0")
    col = N.mix(N.math('MULTIPLY', crease_edge(N, 0.02), 0.5), col, "#7C84A8")
    for at, reach in (glow_at or ()):
        dist = N.new("ShaderNodeVectorMath")
        dist.operation = 'DISTANCE'
        N.link(co, dist.inputs[0])
        dist.inputs[1].default_value = tuple(at)
        col = N.mix(N.math('MULTIPLY', N.ramp(dist.outputs["Value"], reach, reach * 0.2), 0.55), col, "#43297F")
    return N.finish(m, col, 0.72)


def shadow_fur(name):
    """Fur locks like the wolf's ruff: near black slate-indigo at the root, slate blue-grey up the lock
    and a ragged silver-white tip; painted strands running along each lock, every lock its own shade,
    paler crisp edges, and deep shade at the foot of its walls (f 1)."""
    m = kit.material(name, "#3A4366", rough=0.75)
    N = Nodes(m)
    co = N.coord()
    g, xn = N.attr("grad"), N.attr("xn")
    strands = N.math('SINE', N.math('MULTIPLY', xn, 4.0 * math.pi))
    jag = N.math('MULTIPLY_ADD', N.noise(co, 9.0, 2.0).outputs["Fac"], 0.1, -0.05)
    tipline = N.math('ADD', N.math('MULTIPLY_ADD', strands, 0.035, g), jag)
    col = N.colours(tipline, [(0.0, "#0E1120"), (0.38, "#232A45"), (0.62, "#384364"), (0.78, "#56628A"),
                              (0.86, "#B0B9CF"), (0.94, "#E6EAF2"), (1.0, "#F6F8FB")])
    lines = N.ramp(N.math('ABSOLUTE', N.math('SINE', N.math('MULTIPLY', xn, 6.0 * math.pi))), 0.25, 0.0)
    shade = N.math('MULTIPLY_ADD', N.attr("pal"), 0.24, 0.86)
    grain = N.math('MULTIPLY_ADD', N.noise(co, 34.0, 2.0).outputs["Fac"], 0.14, 0.93)
    col = N.value(col, N.math('MULTIPLY', N.math('MULTIPLY', shade, grain), N.math('MULTIPLY_ADD', lines, -0.22, 1.0)))
    col = N.mix(N.math('MULTIPLY', N.ramp(N.math('ABSOLUTE', xn), 0.16, 0.0), 0.45), col, "#0A0B16")
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', crease_edge(N, 0.018), N.ramp(g, 0.3, 0.9)), 0.5), col, "#B7C0D8")
    col = N.mix(N.math('MULTIPLY', N.ramp(N.attr("f"), 0.2, 1.0), 0.8), col, "#07080F")
    return N.finish(m, col, 0.75)


def shadow_crystal(name):
    """Violet-black crystal: nearly black at the foot, deep violet in the body, pale lilac at the tip,
    each facet lighter or darker by the way it faces, its edges catching the light."""
    m = kit.material(name, "#1D1438", rough=0.3)
    N = Nodes(m)
    col = N.colours(N.attr("grad"), [(0.0, "#050409"), (0.45, "#140E2A"), (0.8, "#2C1F5A"), (1.0, "#9A84E0")])
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    N.link(geo.outputs["True Normal"], dot.inputs[0])
    dot.inputs[1].default_value = (-0.45, -0.55, 0.7)
    col = N.value(col, N.math('MULTIPLY_ADD', dot.outputs["Value"], 0.45, 1.0))
    col = N.mix(N.math('MULTIPLY', N.edge(0.025, 0.995, 0.9), 0.4), col, "#B9A6F2")
    return N.finish(m, col, 0.3)


def shadow_silver(name):
    """Brushed silver for the crescent seal: bright where it faces up, darker beneath, a fine brushed grain."""
    m = kit.material(name, "#C9CFDB", rough=0.4)
    N = Nodes(m)
    co = N.coord()
    brushed = N.math('MULTIPLY_ADD', N.noise(co, 60.0, 2.0).outputs["Fac"], 0.22, 0.89)
    col = N.value(N.mix(N.up(-0.2, 0.9), "#5E6578", "#C4CAD8"), brushed)
    col = N.mix(N.math('MULTIPLY', crease_edge(N, 0.015), 0.75), col, "#F4F6FA")
    return N.finish(m, col, 0.4)


def flat(name, hexcode, rough=0.7, grain=24.0):
    """A dark filler colour with a faint grain, for cracks and rims."""
    m = kit.material(name, hexcode, rough=rough)
    N = Nodes(m)
    co = N.coord()
    col = N.value(hexcode, N.math('MULTIPLY_ADD', N.noise(co, grain, 3.0).outputs["Fac"], 0.3, 0.85))
    return N.finish(m, col, rough)


# ---- building an egg ------------------------------------------------------------------------------------

class Build:
    """A Prop and the bookkeeping each egg needs."""

    def __init__(self, name, egg):
        self.prop = Prop(name)
        self.prop.tally = {}
        self.egg = egg

    def add(self, part, bm, mat, at=None, crease=None):
        layers(bm)
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        if crease:
            sharpen(bm, crease)
        self.prop.tally[part] = self.prop.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        self.prop.add(bm, mat)

    def done(self):
        self.prop.build()
        return self.prop


def meadow():
    egg = Egg(height=4.48, radius=1.64)
    shell = meadow_shell("MeadowShell")
    paint = dab_material("MeadowDab")
    b = Build("MeadowEgg", egg)
    b.add("shell", egg.mesh(segs=36, rings=30), shell)
    rnd = random.Random(7)
    placed = []
    tries = 0
    while len(placed) < 15 and tries < 4000:
        tries += 1
        s, th, rad = rnd.uniform(0.22, 0.84), rnd.uniform(-180, 180), rnd.uniform(0.12, 0.21)
        p = egg.point(s, th)
        if any((p - q).length < rad + rr + 0.45 for q, rr in placed):
            continue
        placed.append((p, rad))
        b.add("dabs", dab(egg, s, th, rad, 0.018, pal=rnd.random(), k=12), paint)
    # a hairline crack near the top, as if it is about to hatch: one side of it stands a little proud
    sec = [(-1, -0.012, 0), (-0.35, 0.014, 0), (-0.35, 0.0, 1), (0.35, 0.0, 1), (0.35, 0.004, 0), (1, -0.012, 0)]
    for (s, th, hd, ln, seed, w) in ((0.8, -30.0, (0.25, 1.0), 1.1, 4, 0.032), (0.82, -12.0, (0.9, 0.4), 0.38, 8, 0.022)):
        path = crack_path(egg, s, th, hd, ln, seed)
        n = len(path)
        b.add("crack", strip(egg, path, [w * 0.5] + [w] * (n - 2) + [0.004], sec, smooth=False), shell)
    return b.done()


EMBER_ROOT = 0.22     # how far each scale's root runs on up under the row above, in scale lengths


def ember():
    egg = Egg(height=4.28, radius=1.47)
    scale_m = obsidian("EmberScale")
    shell_m = obsidian("EmberShell", heat=False)
    horn_m, _ = ramp_mat("EmberHorn", [(0.0, "#0E0C0D"), (0.55, "#1D1918"), (0.82, "#8F7E62"), (1.0, "#E8DCBC")], attr="grad", rough=0.5)
    glow = glow_material("EmberEgg", "#FF5A12", 3.0)
    b = Build("EmberEgg", egg)
    z_lo, z_hi = 0.3, egg.z_at(0.925)
    core = egg.mesh(segs=16, rings=12, lift=-0.024)
    hot, cold = kit.split(core, lambda f: z_lo < f.calc_center_median().z < z_hi)
    b.add("core", hot, glow)
    b.add("shell", cold, shell_m)
    rnd = random.Random(11)
    s0, off, n = 0.93, 0.0, 8
    while s0 > 0.13:
        w = 2 * math.pi * egg.radius_at(s0 - 0.04) / n
        ln = min(max(0.95 * w, 0.5), 0.95)
        s1 = max(s0 - ln / egg.L, 0.05)
        root = min(s0 + EMBER_ROOT * ln / egg.L, 0.975)   # buried under the row above, so its seams stop there
        half = 180.0 / n * (1 - 0.11 / w)
        for j in range(n):
            thc = off + 360.0 * j / n + rnd.uniform(-2.0, 2.0)
            b.add("scales", tile(egg, root, s1, thc, half * rnd.uniform(0.97, 1.0), lift=(-0.008, 0.115),
                                 vs=(0.0, 0.62, 1.0), widths=(1.0, 0.98, 0.46), curve=0.3), scale_m, crease=35)
        off += 180.0 / n
        s0 -= 0.62 * ln / egg.L
    for th in (-38.0, 82.0, 202.0):
        s = 0.885
        p0 = egg.point(s, th, -0.04)
        nrm, up = egg.normal(s, th), Vector((0, 0, 1))
        d = (nrm * 0.75 + up).normalized()
        pts = [p0, p0 + d * 0.16, p0 + d * 0.3 + up * 0.05 - nrm * 0.03, p0 + d * 0.4 + up * 0.11 - nrm * 0.08]
        b.add("horns", loft(pts, [0.095, 0.08, 0.05, 0.008], P_HORN, up=nrm, rings=5), horn_m, crease=40)
    return b.done()


def phoenix():
    egg = Egg(height=4.34, radius=1.52)
    stops = [(0.0, "#2A040A"), (0.2, "#6E0A14"), (0.4, "#B01414"), (0.6, "#E5531A"), (0.8, "#FF9A22"), (1.0, "#FFD25A")]
    plum, hsv = ramp_mat("PhoenixPlumage", stops, attr="g", rough=0.75, streak=dict(strength=0.12, mottle=0.08, fine=34.0, length=5.0))
    vane(plum, hsv)
    glow = glow_material("PhoenixEgg", "#FFB020", 4.0)
    b = Build("PhoenixEgg", egg)
    core = egg.mesh(segs=16, rings=12)
    lg = layer(core, "g")
    for v in core.verts:
        v[lg] = 0.05 + 0.7 * v.co.z / egg.height
    b.add("shell", core, plum)
    spec = [  # root s, tip s, feathers, g at root, g at tip
        (0.03, 0.30, 11, 0.02, 0.62),
        (0.17, 0.44, 12, 0.08, 0.7),
        (0.31, 0.58, 11, 0.14, 0.78),
        (0.45, 0.71, 10, 0.2, 0.86),
        (0.59, 0.84, 8, 0.28, 0.93),
        (0.72, 0.975, 6, 0.36, 1.0),
    ]
    twist = 34.0
    for k, (s0, s1, n, g0, g1) in enumerate(spec):
        th0 = 17.0 * k

        def place(u, v, s0=s0, s1=s1, n=n, th0=th0):
            th = th0 + u * 360.0 / n + twist * v
            s = s0 + (s1 - s0) * v
            return egg.point(s, th), egg.normal(s, th)
        ln = (s1 - s0) * egg.L
        b.add("feathers", row(place, n, closed=True, cols=4, rows=3, depth=0.58, lift=0.045 if k == 0 else 0.065, sink=0.04,
                              ridge=0.03, thick=0.035, g=(g0, g1), gpow=1.6, L=ln, point=0.6), plum)
        if k >= 4:                                    # flames licking up from the tips of the top two rows
            for j in range(n):
                if k == 4 and j % 2:
                    continue
                b.add("flames", flame(egg, place, j, 0.55, 1.06, 0.42, lift=0.065, sink=0.04, ridge=0.03), glow)
    return b.done()


def flame(egg, place, j, v0, v1, width, lift, sink, ridge, steps=5):
    """A glowing flame lying along the shaft of feather j of a row: from a point at v0, swelling to
    `width` of the feather and out to a point at v1 (just past the feather's tip)."""
    bm = bmesh.new()
    layers(bm)
    tops, bots = [], []
    for i in range(steps + 1):
        v = v0 + (v1 - v0) * i / steps
        w = width * math.sin(math.pi * i / steps) ** 0.8
        vv = min(v, 1.0)
        tr, br = [], []
        for q in (-1.0, 0.0, 1.0):
            u = j + 0.5 + 0.5 * q * w
            p, nrm = place(u, vv)
            surf = -sink + (lift + sink) * vv ** 1.2 + ridge * (1 - abs(q * w)) * min(1.0, 3 * vv + 0.3)
            over = surf + (0.02 if q == 0 else 0.008) + max(v - 1.0, 0.0) * 0.5
            tr.append(bm.verts.new(p + nrm * over))
            br.append(tr[-1] if q != 0 else bm.verts.new(p + nrm * (surf - 0.02)))
        tops.append(tr)
        bots.append(br)
    for a, b in zip(tops, tops[1:]):
        for c in range(2):
            bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
    for a, b in zip(bots, bots[1:]):
        for c in range(2):
            bm.faces.new((b[c], b[c + 1], a[c + 1], a[c]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def storm():
    egg = Egg(height=4.42, radius=1.58)
    shell_m = porcelain("StormShell")
    wing_m = enamel("StormWing")
    crack_m = flat("StormCrack", "#0B1124", rough=0.6)
    glow = glow_material("StormEgg", "#3AA0FF", 3.2)
    b = Build("StormEgg", egg)
    b.add("shell", egg.mesh(segs=30, rings=22), shell_m)
    # a crown of navy enamel wing blades round the lower egg, silver-rimmed, rising highest at the sides
    # and swept back a little; white gaps stay open at the front and back for the lightning
    bev = [(-1.0, -0.03, 1), (-0.8, 0.045, 1), (-0.8, 0.045, 0), (-0.45, 0.062, 0), (0.0, 0.078, 0),
           (0.45, 0.062, 0), (0.8, 0.045, 0), (0.8, 0.045, 1), (1.0, -0.03, 1)]
    blades = ((22, 0.34, 2, 0.5), (48, 0.53, 8, 0.56), (74, 0.7, 14, 0.58), (100, 0.72, 18, 0.58), (126, 0.62, 16, 0.55), (152, 0.46, 10, 0.5))
    for k, (thc, tip, sweep, w) in enumerate(blades):
        sec = [(u, h + 0.012 * (len(blades) - 1 - k), t) for u, h, t in bev]
        for sx in (-1, 1):
            c, sw = sx * thc, sx * sweep
            path = [(0.085, c), (0.16, c + sw * 0.1), (0.1 + 0.55 * (tip - 0.1), c + sw * 0.55), (tip, c + sw)]
            widths = [w * 0.55, w, w * 0.8, 0.03]
            b.add("wings", strip(egg, path, widths, sec, steps=11, taper=lambda t: min(1.0, t / 0.07), sharp_cols=(1, 2, 4, 6, 7)),
                  wing_m, crease=30)
            if thc in (74, 100):
                n = len(path) - 1
                zig = ((0.5, 0.0), (0.58, 0.32), (0.66, -0.26), (0.74, 0.28), (0.82, -0.14), (0.88, 0.04))
                pts, wds = [], []
                for t, off in zig:
                    cs_ = _cr([p[0] for p in path], t * n)
                    ct_ = _cr([p[1] for p in path], t * n)
                    half_w = _cr(widths, t * n)
                    pts.append(egg.walk(cs_, ct_, 0.0, off * half_w * sx))
                    wds.append(0.02)
                wds[0], wds[-1] = 0.008, 0.006
                lift = 0.012 * (len(blades) - 1 - k)
                streak = [(-1, 0.06 + lift, 0), (0, 0.095 + lift, 0), (1, 0.06 + lift, 0)]
                b.add("lightning", strip(egg, pts, wds, streak, smooth=False), glow)
    # lightning striking down from the top into the gaps, cut into the porcelain
    rim = [(-1, -0.012, 0), (-0.45, 0.006, 0), (0.45, 0.006, 0), (1, -0.012, 0)]
    core = [(-1, -0.006, 0), (0, 0.022, 0), (1, -0.006, 0)]
    for (s, th, hd, ln, seed) in ((0.87, -4.0, (-1.0, 0.08), 2.75, 5), (0.68, -2.0, (-0.55, 1.0), 0.95, 9),
                                  (0.86, 178.0, (-1.0, -0.08), 2.4, 13), (0.64, 181.0, (-0.5, -1.0), 0.8, 17)):
        path = bolt_path(egg, s, th, hd, ln, seed)
        n = len(path)
        taper = [0.25] + [1.0] * (n - 3) + [0.7, 0.2]
        b.add("cracks", strip(egg, path, [0.08 * t for t in taper], rim, smooth=False), crack_m)
        b.add("lightning", strip(egg, path, [0.028 * t for t in taper], core, smooth=False), glow)
    return b.done()


def crystal_egg():
    egg = Egg(height=4.3, radius=1.5)
    rock = stone("CrystalStone", base="#383B3F", warm="#4C443B", moss_amount=0.5)
    gem = crystal_material("CrystalGem")
    glow = glow_material("CrystalEgg", "#17B850", 3.0)
    b = Build("CrystalEgg", egg)
    rnd = random.Random(5)
    O_s, O_th = 0.62, -30.0
    O = egg.point(O_s, O_th)
    centre = Vector((0, 0, egg.zc))
    inner = stone("CrystalInner", base="#1B1C1E", warm="#211E1B", edge="#3A3936", wear=0.2, cracks=0.0, vary=0.1,
                  tint=(O + (centre - O).normalized() * 0.3, 1.0, "#0F5A34", 0.85))
    # the dark core, sunk into a smooth hollow where the shell is broken open
    B_s, B_th = 0.48, 152.0
    Bk = egg.point(B_s, B_th)
    core = egg.mesh(segs=30, rings=22)
    for v in core.verts:
        for at, reach, depth in ((O, 0.9, 0.45), (Bk, 0.62, 0.3)):
            d = (v.co - at).length
            if d < reach:
                v.co += (centre - v.co).normalized() * depth * (1 - (d / reach) ** 2) ** 1.5
    b.add("core", core, inner)
    # hewn slabs over Voronoi cells, three of them missing round the opening, the next ones pushed open
    cells = []
    for d, corners in sphere_cells(52, 3):
        cs, cth = egg.from_sphere(d)
        C = egg.point(cs, cth)
        pts = [egg.point(*egg.from_sphere(c)) for c in corners]
        cells.append((C, pts))
    order = sorted(range(len(cells)), key=lambda i: (cells[i][0] - O).length)
    back = sorted(range(len(cells)), key=lambda i: (cells[i][0] - Bk).length)
    gone = set(order[:3]) | {back[0]}
    near = set(order[3:9])
    for i, (C, pts) in enumerate(cells):
        if i in gone:
            continue
        kw = dict(away=O, lean=0.28) if i in near else (dict(away=Bk, lean=0.2) if i in back[1:4] else {})
        b.add("slabs", stone_plate(egg, C, pts, rnd, **kw), rock)
    # emerald crystals pushing out of the opening; the three biggest are lit from inside
    nrm = egg.normal(O_s, O_th)
    up = Vector((0, 0, 1))
    d0 = (nrm * 0.75 + up).normalized()
    F = O + (centre - O).normalized() * 0.3
    side = d0.cross(up).normalized()
    spec = ((1.28, 0, 0.0, 0.22), (0.92, 30, 0.22, 0.17), (0.82, 28, 0.23, 0.16), (0.7, 36, 0.22, 0.15), (0.6, 34, 0.21, 0.14),
            (0.66, 44, 0.2, 0.14), (0.48, 50, 0.26, 0.12), (0.42, 58, 0.3, 0.11))
    for k, (ln, ang, off, rad) in enumerate(spec):
        if k == 0:
            axis, foot = d0, F
        else:
            o = Matrix.Rotation(2 * math.pi * k / 7 + 0.4, 3, d0) @ side
            axis = (Matrix.Rotation(math.radians(ang), 3, d0.cross(o).normalized()) @ d0).normalized()
            foot = F + o * off
        at = aim(foot, axis, rnd.uniform(0, 60))
        if k < 3:
            facets, lit = lit_crystal(ln, rad, seed=40 + k)
            b.add("crystals", facets, gem, at)
            b.add("crystal cores", lit, glow, at)
        else:
            b.add("crystals", crystal(ln, rad, seed=40 + k), gem, at, crease=25)
    # a smaller cluster out of the break round the back, its biggest crystal lit from inside
    nb = egg.normal(B_s, B_th)
    db = (nb * 0.8 + up).normalized()
    Fb = Bk + (centre - Bk).normalized() * 0.2
    sb = db.cross(up).normalized()
    for k, (ln, ang, off, rad) in enumerate(((0.9, 0, 0.0, 0.16), (0.62, 32, 0.15, 0.12), (0.55, 30, 0.15, 0.11), (0.44, 40, 0.16, 0.1))):
        if k == 0:
            axis, foot = db, Fb
        else:
            o = Matrix.Rotation(2 * math.pi * k / 3 + 0.8, 3, db) @ sb
            axis = (Matrix.Rotation(math.radians(ang), 3, db.cross(o).normalized()) @ db).normalized()
            foot = Fb + o * off
        at = aim(foot, axis, rnd.uniform(0, 60))
        if k == 0:
            facets, lit = lit_crystal(ln, rad, seed=90)
            b.add("crystals", facets, gem, at)
            b.add("crystal cores", lit, glow, at)
        else:
            b.add("crystals", crystal(ln, rad, seed=90 + k), gem, at, crease=25)
    # small crystals pushing through cracks, low on the left and beside the opening
    for (s, th, ln, n, seed) in ((0.24, -95.0, 0.42, 2, 71), (0.53, -46.0, 0.36, 2, 81)):
        P = egg.point(s, th, -0.12)
        nn = egg.normal(s, th)
        sd = nn.cross(up).normalized()
        for k in range(n):
            ax = (Matrix.Rotation(math.radians(22 * (k - (n - 1) / 2)), 3, nn.cross(sd)) @ (nn + up * 0.3)).normalized()
            b.add("crystals", crystal(ln * (1.0 - 0.25 * k), 0.09, seed=seed + k), gem, aim(P + sd * 0.1 * (k - (n - 1) / 2), ax, 20), crease=25)
    return b.done()


def fur_lock(egg, s0, th0, length, n, bend=0.0, lift=(-0.05, 0.07), flare=0.07, keel=0.05, sink=0.07, extra=0.0,
             fill=0.98, rows=4, tips=(0.5, 0.8, 0.62, 1.0, 0.56), ridge=(0.0, 1.0, 0.45, 1.0, 0.0), shade=0.5):
    """One upward-sweeping lock of fur lying on the egg, like the locks of the wolf's ruff: its root at
    (s0, th0), buried in the shell, runs `length` studs up the shell, curling `bend` studs round it on the
    way (towards larger th), more and more towards its tip. It is as wide as one of `n` locks side by
    side round the egg (times `fill`), a little fuller in the middle, and split into two strands: a
    groove runs up the middle between two ridges, and it ends in two points, the longer one on the side
    it curls to (`tips` is how far up each of its five columns runs, `ridge` their heights). Its top
    rises from the root to stand `extra` + lift[1] proud, its points flaring out by `flare`; its sides and
    points drop in walls to `sink` below the shell, so it has real thickness and shades the lock behind.
    "grad" runs 0 at the root to 1 at the longest point, "xn" is the place across (-1 to 1), "f" is 1 at
    the foot of the walls and "pal" is the lock's own shade."""
    bm = bmesh.new()
    lay = layers(bm)
    qs = (-1.0, -0.5, 0.0, 0.5, 1.0)
    if bend < 0:
        tips, ridge = tips[::-1], ridge[::-1]
    grid, where = [], {}
    for r in range(rows + 1):
        line = []
        for q, top, rg in zip(qs, tips, ridge):
            v = top * r / rows
            a, c = length * v, bend * v ** 2.2
            d = Vector((length, 2.2 * bend * v ** 1.2)).normalized()
            hw = fill * math.pi * egg.radius_at(s0 + a / egg.L) / n * (1.0 + 0.12 * math.sin(math.pi * v)) * (1 - 0.25 * v)
            w = q * hw
            s, th = egg.walk(s0, th0, a - d.y * w, c + d.x * w)
            h = lift[0] + (lift[1] + extra - lift[0]) * v ** 0.8 + flare * v ** 3 + keel * rg * min(1.0, 2.5 * v + 0.3)
            vert = bm.verts.new(egg.point(s, th, h))
            vert[lay["grad"]], vert[lay["xn"]], vert[lay["pal"]] = v, q, shade
            where[vert] = (s, th)
            line.append(vert)
        grid.append(line)
    m = len(qs)
    for a, b in zip(grid, grid[1:]):
        for j in range(m - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
        for j in (1, 2, 3):
            bm.edges.get((a[j], b[j])).smooth = False
    rim = [grid[r][-1] for r in range(rows + 1)] + grid[-1][-2::-1] + [grid[r][0] for r in range(rows - 1, -1, -1)]
    low = []
    for v in rim:
        s, th = where[v]
        lo = bm.verts.new(egg.point(s, th, -sink))
        lo[lay["grad"]], lo[lay["xn"]], lo[lay["pal"]], lo[lay["f"]] = v[lay["grad"]], v[lay["xn"]], shade, 1.0
        low.append(lo)
    for i in range(len(rim) - 1):
        bm.faces.new((rim[i], rim[i + 1], low[i + 1], low[i]))
    return flip_out(bm, egg.outward)


def disc_point(egg, s, th, rho, ang):
    """The point `rho` studs from (s, th) on the shell, `ang` radians round from straight across."""
    return egg.walk(s, th, rho * math.sin(ang), rho * math.cos(ang))


def crater(b, egg, s, th, r0, r1, n, mat, rnd, lean=0.3, h=0.08, gap=0.02, chamfer=0.025):
    """A ring of `n` broken shell pieces round (s, th), from r0 to r1 studs out, their inner edges pushed
    up and out as if something broke through from inside."""
    P = egg.point(s, th)
    cuts = [2 * math.pi * k / n + rnd.uniform(-0.18, 0.18) for k in range(n)]
    cuts.append(cuts[0] + 2 * math.pi)
    for k in range(n):
        a0, a1 = cuts[k], cuts[k + 1]
        am = (a0 + a1) / 2
        ring = [(r0 * rnd.uniform(0.9, 1.15), a0), (r1 * rnd.uniform(0.8, 0.95), a0 + 0.08),
                (r1 * rnd.uniform(1.0, 1.15), am + rnd.uniform(-0.15, 0.15)), (r1 * rnd.uniform(0.8, 0.95), a1 - 0.08),
                (r0 * rnd.uniform(0.9, 1.15), a1)]
        corners = [egg.point(*disc_point(egg, s, th, rho, a)) for rho, a in ring]
        C = egg.point(*disc_point(egg, s, th, (r0 + r1) / 2, am))
        b.add("shell shards", stone_plate(egg, C, corners, rnd, gap=gap, chamfer=chamfer, h=h, sink=0.05, tilt=0.05,
                                          away=P, lean=lean), mat)


def pool(egg, s, th, radius, h=0.03, k=12):
    """A flat pool of light lying on the shell under broken pieces: level at `h` out to `radius` (clear of
    the shell's flat facets), then dropping just under the shell."""
    bm = bmesh.new()
    layers(bm)
    c = bm.verts.new(egg.point(s, th, h))
    rings = []
    for rho, hh in ((0.5, h), (1.0, h), (1.12, -0.015)):
        rings.append([bm.verts.new(egg.point(*disc_point(egg, s, th, radius * rho, 2 * math.pi * j / k), hh)) for j in range(k)])
    for j in range(k):
        jj = (j + 1) % k
        bm.faces.new((c, rings[0][j], rings[0][jj]))
        for a, b in zip(rings, rings[1:]):
            bm.faces.new((a[j], b[j], b[jj], a[jj]))
    return flip_out(bm, egg.outward)


def burst(b, egg, s, th, spec, gem, glow, rnd, seed, out=0.8, lit=1, sunk=0.1, spin=0.4):
    """Crystals bursting out of the shell at (s, th), aimed up and out: spec is ((length, degrees off the
    main axis, foot offset, radius), ...), the first one along the main axis; the first `lit` of them are
    lit from inside."""
    nrm = egg.normal(s, th)
    up = Vector((0, 0, 1))
    d0 = (nrm * out + up).normalized()
    F = egg.point(s, th) - nrm * sunk
    side = d0.cross(up).normalized()
    others = max(len(spec) - 1, 1)
    for k, (ln, ang, off, rad) in enumerate(spec):
        if k == 0:
            axis, foot = d0, F
        else:
            o = Matrix.Rotation(2 * math.pi * (k - 1) / others + spin, 3, d0) @ side
            axis = (Matrix.Rotation(math.radians(ang), 3, d0.cross(o).normalized()) @ d0).normalized()
            foot = F + o * off
        at = aim(foot, axis, rnd.uniform(0, 60))
        if k < lit:
            facets, core = lit_crystal(ln, rad, seed=seed + k, slit=0.018)
            b.add("crystals", facets, gem, at)
            b.add("crystal cores", core, glow, at)
        else:
            b.add("crystals", crystal(ln, rad, seed=seed + k), gem, at, crease=25)


CRACK_RIM = [(-1, -0.012, 0), (-0.45, 0.008, 0), (0.45, 0.008, 0), (1, -0.012, 0)]
CRACK_CORE = [(-1, -0.004, 0), (0, 0.02, 0), (1, -0.004, 0)]


def glow_crack(b, egg, s, th, heading, length, seed, crack_m, glow, wide=0.06):
    """A thin crack in the shell, glowing faintly from inside."""
    path = crack_path(egg, s, th, heading, length, seed)
    n = len(path)
    taper = [0.5] + [1.0] * max(n - 3, 0) + [0.6, 0.15]
    taper = taper[:n]
    b.add("cracks", strip(egg, path, [wide * t for t in taper], CRACK_RIM, smooth=False), crack_m)
    b.add("crack glow", strip(egg, path, [wide * 0.36 * t for t in taper], CRACK_CORE, smooth=False), glow)


SHADOW_SHELL = dict(height=4.3, radius=1.48)
SHADOW_FRONT = (0.735, -12.0)       # where the crystals burst out of the front


def shadow():
    egg = Egg(**SHADOW_SHELL)
    up = Vector((0, 0, 1))
    F_s, F_th = SHADOW_FRONT
    backs = ((0.6, 182.0, 0.62), (0.7, 175.0, 0.72), (0.8, 183.0, 0.56))
    sides = ((0.6, 106.0), (0.63, -114.0))
    glow_at = [(egg.point(F_s, F_th), 0.8)] + [(egg.point(s, th), 0.42) for s, th, _ in backs] + [(egg.point(s, th), 0.42) for s, th in sides]
    shell_m = shadow_shell("ShadowShell", glow_at)
    fur_m = shadow_fur("ShadowFur")
    gem_m = shadow_crystal("ShadowCrystal")
    silver_m = shadow_silver("ShadowSilver")
    crack_m = flat("ShadowCrack", "#0B0918", rough=0.6)
    glow = glow_material("ShadowEgg", "#6A3CFF", 2.3)
    b = Build("ShadowEgg", egg)
    rnd = random.Random(23)
    b.add("shell", egg.mesh(segs=24, rings=16), shell_m)
    # the ruff: three staggered tiers of fur locks sweeping up the lower egg, the lowest tier standing proudest
    for k, (s0, ln, n, off, extra, fl, mane) in enumerate(((0.085, 1.5, 9, 0.0, 0.07, 0.15, 0.06), (0.17, 1.62, 9, 20.0, 0.04, 0.11, 0.14),
                                                           (0.275, 1.66, 9, 0.0, 0.01, 0.07, 0.3))):
        for j in range(n):
            thc = off + 360.0 * j / n + rnd.uniform(-3.0, 3.0)
            sn = math.sin(math.radians(thc))
            sweep = 0.95 * math.copysign(max(abs(sn), 0.3) ** 0.6, sn if abs(thc) > 2 else 1.0) + rnd.uniform(-0.06, 0.06)
            rise = 1.0 + mane * (1 - math.cos(math.radians(thc))) / 2            # longer towards the back
            b.add("fur", fur_lock(egg, s0, thc, ln * rise * rnd.uniform(0.94, 1.04), n, bend=sweep * rise, extra=extra, flare=fl,
                                  shade=rnd.random()), fur_m, crease=32)
    # the front: violet-black crystals bursting out through broken shell, cradled by a silver crescent
    b.add("crack glow", pool(egg, F_s, F_th, 0.55, 0.03, k=12), glow)
    crater(b, egg, F_s, F_th, 0.17, 0.64, 6, shell_m, rnd, lean=0.6, h=0.065)
    burst(b, egg, F_s, F_th, ((1.36, 0, 0.0, 0.21), (0.9, 30, 0.2, 0.15), (0.8, 30, 0.2, 0.14), (0.62, 40, 0.2, 0.12),
                              (0.52, 44, 0.19, 0.11), (0.44, 52, 0.22, 0.1)), gem_m, glow, rnd, 40, out=0.55, lit=3)
    for hd, ln, seed in (((0.85, -0.5), 0.7, 3), ((0.9, 0.6), 0.65, 5), ((0.05, 1.0), 0.55, 7)):
        hv = Vector(hd).normalized()
        s1, th1 = egg.walk(F_s, F_th, hv.x * 0.6, hv.y * 0.6)
        glow_crack(b, egg, s1, th1, hd, ln, seed, crack_m, glow)
    R, path, widths = 0.76, [], []
    for i in range(11):
        t = i / 10
        phi = math.radians(172 + 196 * t)
        path.append(egg.walk(F_s - 0.01, F_th, R * math.sin(phi), R * math.cos(phi)))
        widths.append(0.085 * math.sin(math.pi * t) ** 1.7 + 0.004)
    moon = [(-1, -0.02, 0), (-0.7, 0.045, 0), (-0.12, 0.06, 0), (0.0, 0.045, 0), (0.12, 0.06, 0), (0.7, 0.045, 0), (1, -0.02, 0)]
    b.add("crescent", strip(egg, path, widths, moon, steps=20, sharp_cols=(1, 2, 4, 5)), silver_m, crease=35)
    # a crest of lit crystals up the back, as on the wolf's spine, and a small burst on each side
    for k, (s, th, ln) in enumerate(backs):
        nn = egg.normal(s, th)
        at = aim(egg.point(s, th, -0.12), (nn + egg.frame(s, th)[0] * 1.5).normalized(), 15.0)
        facets, core = lit_crystal(ln, 0.15, seed=60 + k, slit=0.018)
        b.add("crystals", facets, gem_m, at)
        b.add("crystal cores", core, glow, at)
        b.add("crack glow", dab(egg, s, th, 0.2, 0.01, k=8), glow)
        sd = 1 if k % 2 == 0 else -1
        glow_crack(b, egg, *egg.walk(s, th, 0.0, 0.16 * sd), (0.3, sd), 0.5, 70 + k, crack_m, glow, wide=0.05)
    for k, (s, th) in enumerate(sides):
        b.add("crack glow", dab(egg, s, th, 0.22, 0.01, k=8), glow)
        burst(b, egg, s, th, ((0.74, 0, 0.0, 0.15), (0.5, 34, 0.13, 0.11), (0.4, 40, 0.13, 0.095)), gem_m, glow, rnd, 90 + 10 * k,
              out=1.1, lit=1)
        glow_crack(b, egg, *egg.walk(s, th, 0.18, 0.05), (1.0, 0.2 * (1 - 2 * k)), 0.55, 95 + k, crack_m, glow, wide=0.05)
    return b.done()


EGGS = {  # key: (name, builder, bake settings); the unwrap angle is whichever used most of the image in a test
    "meadow": ("MeadowEgg", meadow, dict(samples=32, shade=0.4, soften=1, rough=0.72, uv_angle=75.0)),
    "ember": ("EmberEgg", ember, dict(samples=32, shade=0.6, soften=2, rough=0.6, uv_angle=66.0)),
    "phoenix": ("PhoenixEgg", phoenix, dict(samples=32, shade=0.6, soften=2, rough=0.78, uv_angle=85.0)),
    "storm": ("StormEgg", storm, dict(samples=32, shade=0.5, soften=2, rough=0.55, uv_angle=75.0)),
    "crystal": ("CrystalEgg", crystal_egg, dict(samples=32, shade=0.7, soften=2, rough=0.88, uv_angle=70.0)),
    "shadow": ("ShadowEgg", shadow, dict(samples=32, shade=0.55, soften=2, rough=0.7, uv_angle=70.0)),
}


def snake(name):
    return name.replace("Egg", "_egg").lower()


# ---- baking, export and numbers ---------------------------------------------------------------------------

def bake(prop, name, texture, settings, size=1024):
    """Everything that does not glow becomes one textured mesh, <Name>_Body; the glowing parts stay one
    mesh, <Name>_GLOW, with their single emissive GLOW_ material."""
    glow = [ob for ob in prop.objects if ob.data.materials[0].name.startswith("GLOW_")]
    body = kit.bake_texture([ob for ob in prop.objects if ob not in glow], texture, size=size, name=name + "_Body",
                            uv_margin=0.004, pack_margin=0.003, **settings)
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
        objs.append(g)
    prop.objects = objs


def numbers(prop, size):
    tris = prop.triangles()
    lo, hi = prop.bounds()
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


def sheet(props, labels, out, samples=32, scale=1.0, extra=False, title="", keep_views=False):
    """All the eggs in a row, each turned to show its front three-quarters: the row from the front, a
    close-up of each, the row from behind and the row at game distance next to the 5-stud block.
    `extra` adds the row in clay and as silhouettes."""
    import review
    from PIL import Image, ImageDraw
    turn, gap = math.radians(29.0), 1.0
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
    bpy.context.scene.render.resolution_percentage = int(100 * scale)
    lo, hi = group.bounds()
    mid = Vector(((lo.x + hi.x) / 2 + 0.9, 0.0, 2.1))
    width = hi.x - lo.x + 4.0
    away = (width / 2) / math.tan(math.radians(11))
    # game distance: a player's eye 5.5 studs up, far enough back for the whole row and the block at FOV 70
    right = rig.dummy.location.x + 1.0
    gx = (lo.x + right) / 2
    gd = max(20.0, ((right - lo.x) / 2 + 1.5) / math.tan(math.radians(35)))
    cams = {
        "front": review._camera("E_front", mid + Vector((0, -1.0, 0.2)).normalized() * away, mid, 22),
        "back": review._camera("E_back", mid + Vector((0, 1.0, 0.2)).normalized() * away, mid, 22),
        "game": review._camera("E_game", Vector((gx, -gd, 5.5)), Vector((gx, 0.0, 1.8)), 70),
    }
    import tempfile
    folder = os.path.splitext(out)[0] + "_views" if keep_views else tempfile.mkdtemp(prefix="eggs_views_")
    os.makedirs(folder, exist_ok=True)
    W = 1800
    tiles = []
    tiles.append((shoot(rig, cams["front"], os.path.join(folder, "front.png"), (W, 520)), "all six, front three-quarters"))
    if extra:
        tiles.append((shoot(rig, cams["front"], os.path.join(folder, "front_clay.png"), (W, 520), "clay"), "clay"))
    allobs = [ob for p in props for ob in p.objects]
    close = []
    for p, label in zip(props, labels):
        lo_p, hi_p = extent(p)
        c = (lo_p + hi_p) / 2
        cam = review._camera("E_close_" + label, c + Vector((0, -1.0, 0.22)).normalized() * 9.6, c + Vector((0, 0, -0.05)), 30)
        close.append((shoot(rig, cam, os.path.join(folder, "close_%s.png" % label), (600, 600),
                            hide=[ob for ob in allobs if ob not in p.objects]), label))
    tiles.append((close, None))
    tiles.append((shoot(rig, cams["back"], os.path.join(folder, "back.png"), (W, 520)), "all six from behind"))
    tiles.append((shoot(rig, cams["game"], os.path.join(folder, "game.png"), (W, 640)),
                  "game distance (%.0f studs, FOV 70, eye 5.5 studs up) next to the 5-stud block" % gd))
    if extra:
        tiles.append((shoot(rig, cams["front"], os.path.join(folder, "front_sil.png"), (W, 520), "silhouette"), "silhouette"))
    sz = lambda p: Image.open(p).size
    heights = [(600 * 2 if isinstance(t, list) else int(sz(t)[1] * W / sz(t)[0])) for t, _ in tiles]
    img = Image.new("RGB", (W, sum(heights) + 30), (18, 20, 24))
    draw = ImageDraw.Draw(img)
    draw.text((8, 9), title, fill=(235, 235, 235))
    y = 30

    def label_at(x, yy, text):
        draw.rectangle((x, yy, x + 10 + 7 * len(text), yy + 18), fill=(0, 0, 0))
        draw.text((x + 4, yy + 3), text, fill=(255, 255, 255))

    for (t, label), h in zip(tiles, heights):
        if isinstance(t, list):
            for i, (p, lab) in enumerate(t):
                x, yy = (i % 3) * 600, y + (i // 3) * 600
                img.paste(Image.open(p).convert("RGB").resize((600, 600)), (x, yy))
                label_at(x, yy, "close-up: " + lab)
        else:
            img.paste(Image.open(t).convert("RGB").resize((W, h)), (0, y))
            label_at(0, y, label)
        y += h
    img.save(out)
    if not keep_views:
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated eggs to build: " + ", ".join(EGGS))
    ap.add_argument("--export-dir", default=os.path.join(MODELS, "export"))
    ap.add_argument("--sheet", default=os.path.join(MODELS, "preview", "eggs.png"))
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--peek", help="quick unbaked look: write the sheet here and stop")
    ap.add_argument("--fast", action="store_true", help="512 textures, few samples, smaller renders")
    ap.add_argument("--extra", action="store_true", help="add clay and silhouette rows to the sheet")
    ap.add_argument("--keep-views", action="store_true", help="keep each view's render in a folder beside the sheet")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--title", default="Hatching eggs")
    a = ap.parse_args()
    if a.fast:
        os.environ["PETS_FAST"] = "1"
    keys = list(EGGS)
    if a.only:
        want = [w.strip().lower().replace("_egg", "").replace("egg", "") for w in a.only.split(",")]
        keys = [k for k in keys if k in want]
    kit.fresh()
    props, labels = [], []
    for i, key in enumerate(keys):
        name, builder, settings = EGGS[key]
        prop = builder()
        print("%s: triangles by part %s" % (name, dict(sorted(prop.tally.items(), key=lambda kv: -kv[1]))), flush=True)
        if not a.peek:
            os.makedirs(a.export_dir, exist_ok=True)
            bake(prop, name, os.path.join(a.export_dir, snake(name) + "_colour.png"), settings, size=a.size)
            size = 512 if a.fast else a.size
            st = numbers(prop, size)
            print("%s: triangles %s total %d; %.2f wide, %.2f deep, %.2f tall studs, lowest z %.3f; texture %d px, %.0f%% of it used, %.0f px per stud"
                  % (name, st["tris"], st["total"], st["size"][0], st["size"][1], st["size"][2], st["low"], size, st["used"] * 100, st["px_per_stud"]), flush=True)
            if not a.no_export:
                path = os.path.join(a.export_dir, snake(name) + ".fbx")
                kit.export_fbx(prop.objects, path)
                print("exported", path, flush=True)
        for ob in prop.objects:
            ob.location.x = 400 + 80 * i               # out of the way while the next one is baked
        props.append(prop)
        labels.append(key)
    out = a.peek or (None if a.no_sheet else a.sheet)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        sheet(props, labels, os.path.abspath(out), samples=12 if (a.peek or a.fast) else a.samples,
              scale=0.6 if (a.peek or a.fast) else 1.0, extra=a.extra or bool(a.peek), title=a.title,
              keep_views=a.keep_views or bool(a.peek))
        print("sheet", out, flush=True)


if __name__ == "__main__":
    main()
