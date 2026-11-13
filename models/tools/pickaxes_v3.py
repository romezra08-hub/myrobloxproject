"""Five pickaxes for Mine an Egg, from a lashed flint pick to a legendary ember obsidian one. Round 3.

    python models/tools/pickaxes.py                      # all five: Roblox files and the review sheet
    python models/tools/pickaxes.py --only ember         # just one (or several: --only wooden iron)

One Blender unit is one stud. Each pickaxe stands on the bottom of its shaft (z = 0) with the shaft
along +Z and the head on top; the main pick points to -Y (forward). The head reaches as far back as
it does forward, so the shaft sits in the middle of the bounding box, where the Studio script
(SetupTools.lua) looks for it, and the hand holds it 0.7 studs above the bottom.

Each exports as <Name>_Handle (everything, baked into one colour image) and, for the two top tiers,
<Name>_GLOW (one emissive material, GLOW_...).
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "pets"))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, ".."))
LAYERS = ("u", "v", "s", "ca", "sa", "eng")
TAU = 2 * math.pi


# ---- small helpers ----------------------------------------------------------------------------------

def layer(bm, name):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def sharpen(bm, degrees, where=None):
    """Mark the edges where the surface turns by more than `degrees` as sharp: crisp creases.
    `where(edge)`, if given, limits it to some edges."""
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim and (where is None or where(e)):
            e.smooth = False
    return bm


def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _super(a, n):
    """A point on a unit superellipse (n=2 is a circle, smaller is a diamond, larger is squarer)."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def aim(origin, direction, roll=0.0):
    """A transform standing a shape built along +Z on `origin`, pointing along `direction`."""
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


class Surface:
    """Finds points exactly on a shape, so that details sit on it and neither float nor sink."""

    def __init__(self, *bms):
        joined = bmesh.new()
        tmp = bpy.data.meshes.new("tmp_surface")
        for bm in bms:
            bm.to_mesh(tmp)
            joined.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        joined.normal_update()
        self.bvh = BVHTree.FromBMesh(joined)
        joined.free()

    def hit(self, origin, direction):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc, nrm

    def near(self, point):
        loc, nrm, _, _ = self.bvh.find_nearest(Vector(point))
        return loc, nrm


# ---- shapes ------------------------------------------------------------------------------------------

def lathe(rings, segs=12, phase=0.0, squash=(1.0, 1.0)):
    """A body of revolution round Z with `segs` sides: rings of (z, r), closed flat at both ends.
    Each vertex keeps the cosine and sine of its angle (ca, sa) and its height (s)."""
    bm = bmesh.new()
    lu, ls, lca, lsa = (layer(bm, n) for n in ("u", "s", "ca", "sa"))
    z0, z1 = rings[0][0], rings[-1][0]
    loops = []
    for z, r in rings:
        ring = []
        for j in range(segs):
            a = phase + TAU * j / segs
            v = bm.verts.new((r * math.cos(a) * squash[0], r * math.sin(a) * squash[1], z))
            v[lca], v[lsa], v[ls], v[lu] = math.cos(a), math.sin(a), z, (z - z0) / max(z1 - z0, 1e-6)
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring, z in ((loops[0], z0), (loops[-1], z1)):
        c = bm.verts.new((0, 0, z))
        c[ls], c[lu] = z, (z - z0) / max(z1 - z0, 1e-6)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ring(inner, outer, depth, segs=12, phase=0.0, bevel=0.012):
    """A flat ring round Z from z = 0 to `depth`, open in the middle (a bezel or a collar), with its
    outer edges bevelled."""
    bm = bmesh.new()
    prof = [(inner, 0.0), (outer - bevel, 0.0), (outer, bevel), (outer, depth - bevel), (outer - bevel, depth), (inner, depth)]
    loops = []
    for r, z in prof:
        loops.append([bm.verts.new((r * math.cos(phase + TAU * j / segs), r * math.sin(phase + TAU * j / segs), z)) for j in range(segs)])
    for a, b in zip(loops, loops[1:] + loops[:1]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def loft(points, radii, profile, up=(0, 0, 1), rings=None, jitter=0.0, seed=0, cap=True):
    """The 2D `profile` (a list of (side, up) points going round) carried along a smooth path
    through `points`, its up side turned as near `up` as it can be. Radii are numbers or
    (side, up) pairs. Every vertex stores how far along it is (u, 0 to 1), the distance along the
    path (s), its profile height (v) and the cosine and sine of its angle round the path (ca, sa)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = rings or (n - 1) * 4
    ups = [Vector(u) for u in up] if isinstance(up[0], (tuple, list, Vector)) else [Vector(up)] * n
    rad = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]
    rnd = random.Random(seed)
    bm = bmesh.new()
    lu, lv, ls, lca, lsa = (layer(bm, k) for k in ("u", "v", "s", "ca", "sa"))
    path = [_cr(pts, i / rings * (n - 1)) for i in range(rings + 1)]
    dist = [0.0]
    for a, b in zip(path, path[1:]):
        dist.append(dist[-1] + (b - a).length)
    loops, m = [], len(profile)
    for i, p in enumerate(path):
        u = i / rings * (n - 1)
        t = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        z = _cr(ups, u)
        z = z - t * z.dot(t)
        z = z.normalized() if z.length > 1e-6 else t.orthogonal().normalized()
        x = z.cross(t)
        rx = max(_cr([r[0] for r in rad], u), 1e-3)
        rz = max(_cr([r[1] for r in rad], u), 1e-3)
        ring = []
        for a, b in profile:
            j = 1.0 + jitter * rnd.uniform(-1, 1) if 0 < i < rings else 1.0
            v = bm.verts.new(p + x * (a * rx * j) + z * (b * rz * j))
            ang = math.atan2(b, a)
            v[lu], v[lv], v[ls], v[lca], v[lsa] = i / rings, b, dist[i], math.cos(ang), math.sin(ang)
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    if cap:
        for ring, tip, i in ((loops[0], path[0], 0), (loops[-1], path[-1], rings)):
            c = bm.verts.new(tip)
            c[lu], c[ls] = i / rings, dist[i]
            for j in range(m):
                bm.faces.new((ring[j], ring[(j + 1) % m], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def hull(points, attr=None):
    """The convex hull of a cloud of points: a faceted, chipped-looking solid. `attr(co)` may give
    each vertex a value in the layer u."""
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    loose = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if attr:
        lu = layer(bm, "u")
        for v in bm.verts:
            v[lu] = attr(v.co)
    return bm


def spindle(root, tip, half, n=40, seed=0, power=0.9, diamond=1.4, tip_half=(0.0, 0.0), jit=0.14, sag=0.0):
    """Points for hull(): a blade from `root` to `tip`, `half` = (side, up) half sizes at the root,
    thinning to `tip_half` at the tip, its cross-section a diamond (diamond < 2) or an oval."""
    rnd = random.Random(seed)
    root, tip = Vector(root), Vector(tip)
    d = tip - root
    L = d.length
    d.normalize()
    upv = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, -1, 0))
    z = (upv - d * upv.dot(d)).normalized()
    x = d.cross(z).normalized()
    pts = []

    def at(s, a, j):
        w = (1.0 - s) ** power
        hx = tip_half[0] + (half[0] - tip_half[0]) * w
        hz = tip_half[1] + (half[1] - tip_half[1]) * w
        ca, sa = _super(a, diamond)
        return root + d * (s * L) + x * (ca * hx * j) + z * (sa * hz * j) - z * (sag * s * s)

    for k in range(8):
        pts.append(at(0.0, TAU * k / 8 + rnd.uniform(-0.2, 0.2), 1.0))
    for _ in range(n):
        pts.append(at(rnd.uniform(0.02, 0.97) ** 0.85, rnd.uniform(0, TAU), rnd.uniform(1 - jit, 1.0)))
    pts.append(at(1.0, 0.0, 0.0))
    return pts


def ribbon(points, normals, width, lift, sink=0.012):
    """A thin ridge laid along a line of surface points: its crest `lift` above the surface, its two
    edges `sink` below it, `width` across and pinched at both ends."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    nrm = [Vector(n).normalized() for n in normals]
    n = len(pts)
    rows = []
    for i in range(n):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = nrm[i].cross(t).normalized()
        w = width * (0.15 if i in (0, n - 1) else 1.0) / 2
        rows.append((bm.verts.new(pts[i] + side * w - nrm[i] * sink), bm.verts.new(pts[i] + nrm[i] * lift),
                     bm.verts.new(pts[i] - side * w - nrm[i] * sink)))
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], b[0], b[1], a[1]))
        bm.faces.new((a[1], b[1], b[2], a[2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(sum(nrm, Vector())) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def slice_off(bm, co, no):
    """Cut away everything in front of the plane through `co` facing `no`, and close the cut with a
    flat face."""
    no = Vector(no).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return bm


def block(size, chamfer=0.05, top=(1.0, 1.0), corner=0.0, extra=()):
    """A box with every edge cut by a flat chamfer `chamfer` studs deep (a forged or carved block),
    its top scaled by `top`, its corners cut `corner` deep, and more cuts `extra` = (point, normal)."""
    sx, sy, sz = (s / 2.0 for s in size)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    for v in bm.verts:
        t = top if v.co.z > 0 else (1.0, 1.0)
        v.co = Vector((v.co.x * sx * t[0], v.co.y * sy * t[1], v.co.z * sz))
    bm.normal_update()
    planes = []
    for e in bm.edges:
        n = (e.link_faces[0].normal + e.link_faces[1].normal).normalized()
        mid = (e.verts[0].co + e.verts[1].co) / 2
        planes.append((mid - n * chamfer, n))
    if corner:
        for v in bm.verts:
            n = sum((f.normal for f in v.link_faces), Vector()).normalized()
            planes.append((v.co - n * corner, n))
    planes += [(Vector(c), Vector(n)) for c, n in extra]
    for c, n in planes:
        slice_off(bm, c, n)
    return bm


def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.3, taper=(0.8, 0.92), sides=6):
    """A crystal along +Z: a slightly tapering, slightly irregular prism from `sink` below its foot
    to a pointed tip. Every vertex stores how far up it is (0 to 1) in the layer u."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lu = layer(bm, "u")
    turn = rnd.uniform(0, TAU / sides)
    tip_h = min(radius * rnd.uniform(*tip), length * 0.45)
    shoulder = length - tip_h
    tp = rnd.uniform(*taper)
    radii = [radius * rnd.uniform(0.9, 1.1) for _ in range(sides)]
    rings = []
    for z, s, g in ((-sink * radius, 1.0, 0.0), (shoulder, tp, 0.8)):
        ring = []
        for j in range(sides):
            a = turn + j * TAU / sides
            v = bm.verts.new((math.cos(a) * radii[j] * s, math.sin(a) * radii[j] * s, z))
            v[lu] = g
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.1, 0.1) * radius, rnd.uniform(-0.1, 0.1) * radius, length))
    apex[lu] = 1.0
    lo, hi = rings
    for j in range(sides):
        k = (j + 1) % sides
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def bipyramid(radius, height, sides=6, seed=0):
    """A gem: two pyramids base to base along Z."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    ring = [bm.verts.new((radius * math.cos(TAU * j / sides) * rnd.uniform(0.92, 1.0),
                          radius * math.sin(TAU * j / sides) * rnd.uniform(0.92, 1.0), 0.0)) for j in range(sides)]
    top, bot = bm.verts.new((0, 0, height / 2)), bm.verts.new((0, 0, -height / 2))
    for j in range(sides):
        bm.faces.new((ring[j], ring[(j + 1) % sides], top))
        bm.faces.new((ring[(j + 1) % sides], ring[j], bot))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


P_ROUND6 = [(math.cos(TAU * j / 6), math.sin(TAU * j / 6)) for j in range(6)]
P_ROUND5 = [(math.cos(TAU * j / 5 + 0.3), math.sin(TAU * j / 5 + 0.3)) for j in range(5)]
P_OCT = [(math.cos(TAU * j / 8 + TAU / 16), math.sin(TAU * j / 8 + TAU / 16)) for j in range(8)]
P_STRAP = [(1.0, 0.35), (-1.0, 0.35), (-1.0, -0.35), (1.0, -0.35)]
P_HORN = [(0, 1.0), (0.55, 0.5), (0.8, -0.05), (0.6, -0.6), (0, -0.85), (-0.6, -0.6), (-0.8, -0.05), (-0.55, 0.5)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]
P_BLADE = [(0, 1.0), (0.72, 0.5), (0.78, -0.5), (0, -1.0), (-0.78, -0.5), (-0.72, 0.5)]


# ---- materials -------------------------------------------------------------------------------------------

class Nodes:
    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new
        self.bsdf = kit.principled(mat)

    def coord(self):
        return self.new("ShaderNodeTexCoord").outputs["Object"]

    def xyz(self, vec):
        s = self.new("ShaderNodeSeparateXYZ")
        self.link(vec, s.inputs[0])
        return s.outputs

    def attr(self, name):
        a = self.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs["Fac"]

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0)):
        mp = self.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Location"].default_value = loc
        self.link(vec, mp.inputs["Vector"])
        return mp.outputs["Vector"]

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

    def bw(self, colour):
        b = self.new("ShaderNodeRGBToBW")
        self.link(colour, b.inputs[0])
        return b.outputs[0]

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

    def facing(self, direction, true=False):
        """How much the surface faces `direction` (-1 to 1)."""
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(geo.outputs["True Normal" if true else "Normal"], dot.inputs[0])
        dot.inputs[1].default_value = Vector(direction).normalized()
        return dot.outputs["Value"]

    def line(self, x, width):
        """1 on the line where x = 0, fading to 0 at `width` either side."""
        return self.ramp(self.math('ABSOLUTE', x), width * 0.45, width, 1.0, 0.0)

    def out(self, colour, rough):
        self.link(colour, self.bsdf.inputs["Base Color"])
        self.bsdf.inputs["Roughness"].default_value = rough


def wood(name, base="#7B5332", dark="#4B2F19", light="#A27A4E", grime=0.0, grime_z=(0.3, 1.35), facets=0.08):
    """Wood with its grain along Z: growth rings whose centre is off the shaft, so they cross the
    surface as long arches, fine fibres, faint whittled facets, paler worn edges and, where hands go,
    darker grime."""
    m = kit.material(name, base, rough=0.85)
    N = Nodes(m)
    co = N.coord()
    wave = N.new("ShaderNodeTexWave")
    wave.wave_type, wave.rings_direction = 'RINGS', 'Z'
    wave.inputs["Scale"].default_value, wave.inputs["Distortion"].default_value = 5.0, 5.0
    wave.inputs["Detail"].default_value, wave.inputs["Detail Scale"].default_value = 3.0, 1.2
    N.link(N.mapping(co, (1, 1, 0.1), (0.41, 0.23, 0.0)), wave.inputs["Vector"])
    rings = N.ramp(wave.outputs["Fac"], 0.25, 0.8)
    col = N.mix(rings, dark, light)
    fibre = N.noise(N.mapping(co, (70, 70, 2.2)), 1.0, 3.0, 0.6)
    col = N.value(col, N.math('MULTIPLY_ADD', fibre.outputs["Fac"], 0.5, 0.75))
    cells = N.voronoi(N.mapping(co, (7, 7, 1.4)), 1.0)
    col = N.value(col, N.math('MULTIPLY_ADD', N.bw(cells.outputs["Color"]), facets * 2, 1.0 - facets))
    if grime:
        z = N.xyz(co)[2]
        band = N.math('MULTIPLY', N.ramp(z, grime_z[0] - 0.15, grime_z[0]), N.ramp(z, grime_z[1], grime_z[1] + 0.2, 1.0, 0.0))
        col = N.mix(N.math('MULTIPLY', band, grime), col, N.value(col, 0.55))
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.45), col, light)
    N.out(col, 0.85)
    return m


def flint(name, base="#3B3734", light="#6B635C", edge="#C4BBAE", cortex="#B3A68C"):
    """Knapped flint: every facet a different shade by the way it faces, faint banding, chalky
    patches of the outer rind, and pale chipped edges."""
    m = kit.material(name, base, rough=0.6)
    N = Nodes(m)
    co = N.coord()
    facet = N.math('MULTIPLY_ADD', N.facing((-0.45, -0.55, 0.7), true=True), 0.24, 1.0)
    band = N.new("ShaderNodeTexWave")
    band.inputs["Scale"].default_value, band.inputs["Distortion"].default_value = 3.0, 6.0
    N.link(N.mapping(co, (1.0, 0.5, 1.6)), band.inputs["Vector"])
    col = N.mix(N.math('MULTIPLY', N.ramp(band.outputs["Fac"], 0.4, 0.9), 0.5), base, light)
    speck = N.noise(co, 18.0, 4.0, 0.6)
    col = N.value(col, N.math('MULTIPLY', facet, N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.35, 0.82)))
    rind = N.ramp(N.noise(co, 5.0, 3.0).outputs["Fac"], 0.6, 0.64)
    col = N.mix(N.math('MULTIPLY', rind, 0.7), col, N.value(cortex, N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.4, 0.8)))
    col = N.mix(N.math('MULTIPLY', N.edge(0.018), 0.7), col, edge)
    N.out(col, 0.6)
    return m


def rope(name, base="#AD8A57", dark="#5A4226", strands=3, lay=0.22):
    """Twisted rope, painted: `strands` strands spiralling round the cord, each lighter in the
    middle and dark in the grooves between them, with fine fibres."""
    m = kit.material(name, base, rough=0.9)
    N = Nodes(m)
    ang = N.math('DIVIDE', N.math('ARCTAN2', N.attr("sa"), N.attr("ca")), TAU)
    f = N.math('FRACT', N.math('MULTIPLY', N.math('ADD', ang, N.math('DIVIDE', N.attr("s"), lay)), float(strands)))
    hump = N.math('SINE', N.math('MULTIPLY', f, math.pi))
    col = N.mix(N.ramp(hump, 0.05, 0.75), dark, base)
    fibre = N.noise(N.mapping(N.coord(), (40, 40, 40)), 1.0, 4.0, 0.7)
    col = N.value(col, N.math('MULTIPLY_ADD', fibre.outputs["Fac"], 0.5, 0.75))
    N.out(col, 0.9)
    return m


def wrap(name, base, dark, light, pitch=0.15, rough=0.75, stitch=None):
    """A strap wound round the shaft, painted on a plain round grip: each turn overlaps the one
    below it, so there is a dark line where it tucks under and it is paler where it bulges."""
    m = kit.material(name, base, rough=rough)
    N = Nodes(m)
    co = N.xyz(N.coord())
    ang = N.math('DIVIDE', N.math('ARCTAN2', co[1], co[0]), TAU)
    s = N.math('FRACT', N.math('ADD', N.math('DIVIDE', co[2], pitch), ang))
    bulge = N.math('SINE', N.math('MULTIPLY', N.math('POWER', s, 0.7), math.pi))
    col = N.mix(N.ramp(bulge, 0.0, 0.9), dark, base)
    col = N.mix(N.math('MULTIPLY', N.ramp(bulge, 0.75, 1.0), 0.5), col, light)
    grain = N.noise(N.coord(), 30.0, 4.0, 0.6)
    col = N.value(col, N.math('MULTIPLY_ADD', grain.outputs["Fac"], 0.3, 0.85))
    N.out(col, rough)
    return m


def metal(name, base, light, dark, edge, hammer=0.12, hammer_size=9.0, edge_amt=0.85, top=0.55, under=0.6,
          rough=0.55, horizon=None, wear=None, edge_radius=0.022):
    """Metal painted for a renderer that will not reflect anything: lighter where it faces up (as
    if it caught the sky), darker underneath, a dark band just below the horizon like polished
    metal has, hammer marks, and bright worn edges (unevenly). `wear`, a vertex layer name, also
    brightens where that layer is high (the worn tip of a pick)."""
    m = kit.material(name, base, rough=rough)
    N = Nodes(m)
    co = N.coord()
    nz = N.xyz(N.new("ShaderNodeNewGeometry").outputs["Normal"])[2]
    col = N.mix(N.ramp(nz, 0.05, 0.95, 0.0, top), base, light)
    col = N.mix(N.ramp(nz, -0.05, -0.9, 0.0, under), col, dark)
    if horizon:
        col = N.mix(N.math('MULTIPLY', N.line(N.math('ADD', nz, 0.18), 0.22), 0.6), col, horizon)
    if hammer:
        cells = N.voronoi(co, hammer_size)
        dent = N.math('MULTIPLY_ADD', N.bw(cells.outputs["Color"]), hammer * 2, 1.0 - hammer)
        rim = N.ramp(cells.outputs["Distance"], 0.25, 0.5, 1.0, 1.0 + hammer)
        col = N.value(col, N.math('MULTIPLY', dent, rim))
    fine = N.noise(co, 22.0, 4.0, 0.6)
    col = N.value(col, N.math('MULTIPLY_ADD', fine.outputs["Fac"], 0.16, 0.92))
    worn = N.ramp(N.noise(co, 6.0, 3.0, 0.6).outputs["Fac"], 0.3, 0.6, 0.35, 1.0)
    e = N.math('MULTIPLY', N.math('MULTIPLY', N.edge(edge_radius), worn), edge_amt)
    if wear:
        e = N.math('MAXIMUM', e, N.ramp(N.attr(wear), 0.8, 1.0, 0.0, 0.8))
    col = N.mix(e, col, edge)
    N.out(col, rough)
    return m


def gold(name):
    """Gold painted bright where it faces up, deep orange-brown underneath with a dark band below
    the horizon, pale worn edges, and engraved lines on the faces marked with the layer eng: a border
    along each edge of the blade and a wave down its middle."""
    m = kit.material(name, "#C9921F", rough=0.45)
    N = Nodes(m)
    co = N.coord()
    nz = N.xyz(N.new("ShaderNodeNewGeometry").outputs["Normal"])[2]
    col = N.mix(N.ramp(nz, 0.0, 0.9, 0.0, 0.7), "#B97A12", "#FFD45C")
    col = N.mix(N.ramp(nz, -0.05, -0.85, 0.0, 0.8), col, "#552A04")
    col = N.mix(N.math('MULTIPLY', N.line(N.math('ADD', nz, 0.2), 0.25), 0.6), col, "#3E2004")
    side = N.math('ABSOLUTE', N.facing((1, 0, 0)))
    col = N.mix(N.math('MULTIPLY', N.ramp(N.facing((-0.6, -0.8, 0.2)), 0.6, 0.95), 0.4), col, "#FFE89A")
    fine = N.noise(co, 25.0, 3.0, 0.5)
    col = N.value(col, N.math('MULTIPLY_ADD', fine.outputs["Fac"], 0.12, 0.94))
    v, u, eng = N.attr("v"), N.attr("u"), N.attr("eng")
    border = N.math('MAXIMUM', N.line(N.math('SUBTRACT', v, 0.36), 0.07), N.line(N.math('ADD', v, 0.36), 0.07))
    wave = N.line(N.math('SUBTRACT', v, N.math('MULTIPLY', N.math('SINE', N.math('MULTIPLY', u, 26.0)), 0.17)), 0.08)
    cut = N.math('MULTIPLY', N.math('MULTIPLY', N.math('MAXIMUM', border, wave), eng), N.ramp(side, 0.6, 0.9))
    col = N.mix(N.math('MULTIPLY', cut, 0.9), col, "#3E2306")
    col = N.mix(N.math('MULTIPLY', N.edge(0.02), 0.65), col, "#FFF0B0")
    N.out(col, 0.45)
    return m


def lacquer(name, base="#15100F", gleam="#6E6266"):
    """Black lacquer over wood: nearly black with a red-brown depth, faint grain showing through and
    a crisp painted gleam down the side that faces the light."""
    m = kit.material(name, base, rough=0.35)
    N = Nodes(m)
    co = N.coord()
    fibre = N.noise(N.mapping(co, (50, 50, 2.0)), 1.0, 3.0, 0.6)
    col = N.mix(N.math('MULTIPLY', fibre.outputs["Fac"], 0.5), base, "#2B1612")
    g = N.ramp(N.facing((-0.62, -0.78, 0.1)), 0.78, 0.97)
    col = N.mix(N.math('MULTIPLY', g, 0.85), col, gleam)
    col = N.mix(N.math('MULTIPLY', N.ramp(N.facing((0.7, 0.7, 0.2)), 0.7, 0.98), 0.4), col, "#3A2A2C")
    N.out(col, 0.35)
    return m


def ruby(name, base="#A3101E"):
    m = kit.material(name, base, rough=0.3)
    N = Nodes(m)
    facet = N.facing((-0.45, -0.55, 0.7), true=True)
    col = N.mix(N.ramp(facet, -0.6, 0.3), "#2E0306", base)
    col = N.mix(N.ramp(facet, 0.55, 0.95), col, "#FF7A82")
    col = N.mix(N.math('MULTIPLY', N.edge(0.01), 0.6), col, "#FFC2C6")
    N.out(col, 0.3)
    return m


def stone(name, base="#33363A", warm="#433D36", edge="#8A877F", crack="#121314", wear=0.6, cracks=0.6, rough=0.9, vary=0.25):
    """Weathered slate: every block its own shade, warm and cool patches, faint strata, mineral
    grains, fine speckle, hairline cracks and paler chipped edges."""
    m = kit.material(name, base, rough=rough)
    N = Nodes(m)
    co = N.coord()
    warp = N.noise(co, 1.4, 3.0)
    wv = N.new("ShaderNodeVectorMath")
    wv.operation = 'MULTIPLY_ADD'
    N.link(warp.outputs["Color"], wv.inputs[0])
    wv.inputs[1].default_value = (0.3, 0.3, 0.3)
    N.link(co, wv.inputs[2])
    warped = wv.outputs[0]
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]
    big = N.noise(co, 1.2, 3.0)
    warmth = N.math('ADD', N.ramp(big.outputs["Fac"], 0.42, 0.64), N.math('MULTIPLY_ADD', island, 0.8, -0.3))
    col = N.mix(N.math('MULTIPLY', N.math('MINIMUM', N.math('MAXIMUM', warmth, 0.0), 1.0), 0.85), base, warm)
    strata = N.new("ShaderNodeTexWave")
    strata.bands_direction = 'Z'
    strata.inputs["Scale"].default_value, strata.inputs["Distortion"].default_value = 6.0, 6.0
    N.link(warped, strata.inputs["Vector"])
    layers = N.math('MULTIPLY_ADD', strata.outputs["Fac"], 0.12, 0.94)
    cells = N.voronoi(warped, 7.0)
    grain = N.math('MULTIPLY_ADD', N.bw(cells.outputs["Color"]), 0.3, 0.85)
    speck = N.noise(co, 30.0, 6.0, 0.62)
    fine = N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.44, 0.78)
    tone = N.math('MULTIPLY_ADD', island, vary, 1.0 - vary * 0.55)
    col = N.value(col, N.math('MULTIPLY', N.math('MULTIPLY', grain, fine), N.math('MULTIPLY', tone, layers)))
    cr = N.voronoi(warped, 3.0, 'DISTANCE_TO_EDGE')
    line = N.ramp(cr.outputs["Distance"], 0.0, 0.04, 1.0, 0.0)
    where = N.ramp(N.noise(co, 3.0, 3.0).outputs["Fac"], 0.5, 0.6)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', line, where), cracks), col, crack)
    worn = N.ramp(N.noise(co, 8.0, 4.0, 0.65).outputs["Fac"], 0.32, 0.6, 0.25, 1.0)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', N.edge(0.02), worn), wear), col, edge)
    N.out(col, rough)
    return m


def emerald(name):
    """Emerald lit from inside: deep green on the facets turned from the light, clear green on those
    facing it, brighter towards the glowing core (u = 0) and paler at the tip, with faint pale
    inclusions and bright edges."""
    m = kit.material(name, "#10955A", rough=0.3)
    N = Nodes(m)
    u = N.attr("u")
    f = N.facing((-0.45, -0.55, 0.7), true=True)
    col = N.mix(N.ramp(f, -0.7, 0.6), "#053A22", "#11935A")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.45, 0.95), 0.75), col, "#47F0A0")
    col = N.mix(N.ramp(u, 0.4, 0.0, 0.0, 0.6), col, "#46F29C")
    cr = N.voronoi(N.mapping(N.coord(), (5, 5, 5)), 1.0, 'DISTANCE_TO_EDGE')
    col = N.mix(N.math('MULTIPLY', N.ramp(cr.outputs["Distance"], 0.0, 0.025, 1.0, 0.0), 0.16), col, "#C6FFE6")
    col = N.mix(N.ramp(u, 0.82, 1.0, 0.0, 0.55), col, "#C2FFE2")
    col = N.mix(N.math('MULTIPLY', N.edge(0.02, 0.995, 0.9), 0.55), col, "#D8FFEE")
    N.out(col, 0.3)
    return m


def obsidian(name, heat=None):
    """Volcanic glass: black, with a cold sheen on the few facets that face the light, as glass
    does, thin bright chipped edges and faint ripples of the conchoidal fracture. With `heat`, a dull
    red glow creeps out from the middle of the head (u = 0)."""
    m = kit.material(name, "#0A0A0D", rough=0.25)
    N = Nodes(m)
    co = N.coord()
    f = N.facing((-0.45, -0.55, 0.7), true=True)
    col = N.mix(N.ramp(f, -0.3, 0.85), "#040406", "#16161C")
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.8, 0.97), 0.85), col, "#6E7282")
    rip = N.new("ShaderNodeTexWave")
    rip.wave_type, rip.rings_direction = 'RINGS', 'SPHERICAL'
    rip.inputs["Scale"].default_value, rip.inputs["Distortion"].default_value = 9.0, 2.0
    N.link(co, rip.inputs["Vector"])
    col = N.value(col, N.math('MULTIPLY_ADD', rip.outputs["Fac"], 0.3, 0.85))
    col = N.mix(N.math('MULTIPLY', N.edge(0.012), 0.7), col, "#9A9DAE")
    if heat:
        col = N.mix(N.ramp(N.attr("u"), 0.0, 0.3, 0.35, 0.0), col, heat)
    N.out(col, 0.25)
    return m


def tones(mat, up=None, down=None, up_mix=0.5, down_mix=0.4):
    """Where the surface faces up the colour turns towards `up`, where it faces down towards `down`."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    base = tuple(hsv.inputs["Color"].default_value)
    geo = new("ShaderNodeNewGeometry")
    sep = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])
    colour = None
    for hexcode, amount, lo, hi in ((up, up_mix, 0.15, 0.95), (down, down_mix, -0.10, -0.90)):
        if not hexcode:
            continue
        rng = new("ShaderNodeMapRange")
        rng.interpolation_type = 'SMOOTHSTEP'
        rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = lo, hi
        rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.0, amount
        link(sep.outputs[2], rng.inputs["Value"])
        mix = new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        link(rng.outputs["Result"], mix.inputs[0])
        if colour is None:
            mix.inputs[6].default_value = base
        else:
            link(colour, mix.inputs[6])
        mix.inputs[7].default_value = (*kit.srgb(hexcode), 1.0)
        colour = mix.outputs[2]
    if colour is not None:
        link(colour, hsv.inputs["Color"])
    return mat


def ramp_by(mat, attr, stops):
    """Colour a patterned material along a ramp read from the vertex value `attr` (0 to 1)."""
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', attr
    ramp = new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
    for pos, hexcode in stops[1:-1]:
        e = els.new(pos)
        e.color = (*kit.srgb(hexcode), 1.0)
    link(a.outputs["Fac"], ramp.inputs["Fac"])
    link(ramp.outputs["Color"], hsv.inputs["Color"])
    return mat


# ---- putting a pickaxe together -------------------------------------------------------------------------

class Pick:
    """A Prop with a tally of triangles by part and every vertex layer present on every shape."""

    def __init__(self, name, head_z):
        self.name, self.head_z = name, head_z
        self.prop = Prop(name)
        self.tally = {}

    def add(self, part, bm, mat, at=None, crease=None):
        for nm in LAYERS:
            layer(bm, nm)
        if at is not None:
            bm.transform(at)
        if crease is not None:
            sharpen(bm, crease)
        self.tally[part] = self.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        self.prop.add(bm, mat)

    def build(self):
        self.prop.build()
        return self


def mark(bm, name, value):
    lay = layer(bm, name)
    for v in bm.verts:
        v[lay] = value
    return bm


def rope_path(surf, centre, axis, ref, turns, h0, h1, lift, per_turn=12, reach=1.0):
    """A helix round `axis` through `centre`, each point dropped onto the surface by a ray towards
    the axis and lifted `lift` off it."""
    axis, ref = Vector(axis).normalized(), Vector(ref).normalized()
    other = axis.cross(ref)
    n = max(int(per_turn * turns), 2)
    pts = []
    for i in range(n + 1):
        t = i / n
        a = TAU * turns * t
        c = Vector(centre) + axis * (h0 + (h1 - h0) * t)
        d = ref * math.cos(a) + other * math.sin(a)
        p, nrm = surf.hit(c + d * reach, -d)
        pts.append(p + d * lift)
    return pts


def wooden():
    """Tier 1: a carved branch with a knob at the end, a chunky knapped flint head lashed on with rope."""
    HZ = 3.95
    p = Pick("WoodenPickaxe", HZ)
    wd = wood("Wooden_Wood", base="#76573B", dark="#47311F", light="#9E7E58", grime=0.5)
    fl = flint("Wooden_Flint")
    rp = rope("Wooden_Rope")

    rnd = random.Random(4)
    rings = [(0.0, 0.2), (0.04, 0.228), (0.13, 0.238), (0.25, 0.212), (0.36, 0.182), (0.55, 0.176), (0.9, 0.178),
             (1.3, 0.181), (1.8, 0.186), (2.4, 0.192), (3.0, 0.198), (3.5, 0.203), (3.95, 0.205), (4.3, 0.2),
             (4.42, 0.175), (4.5, 0.11)]
    shaft = lathe([(z, r * (1 + (rnd.uniform(-0.035, 0.035) if 1.4 < z < 4.4 else 0))) for z, r in rings], segs=10, phase=0.2)
    sharpen(shaft, 30, where=lambda e: min(v.co.z for v in e.verts) > 1.35)      # whittled facets above the hand
    shaft_copy = shaft.copy()
    p.add("shaft", shaft, wd)

    # the flint head: two thick knapped blades meeting in the middle, the front one sharper, the back
    # one blunt, both reaching 1.25 studs from the shaft
    front = hull(spindle((0, 0.24, HZ + 0.03), (0, -1.25, HZ - 0.16), (0.27, 0.38), n=40, seed=3, power=0.72,
                         tip_half=(0.02, 0.03), sag=0.04, jit=0.12))
    back = hull(spindle((0, -0.24, HZ + 0.03), (0, 1.25, HZ - 0.1), (0.26, 0.36), n=36, seed=8, power=0.6,
                        tip_half=(0.08, 0.1), sag=0.03, jit=0.12))
    surf = Surface(front, back, shaft_copy)
    shaft_copy.free()
    p.add("head", front, fl, crease=1.0)
    p.add("head", back, fl, crease=1.0)

    # lashing: turns round the shaft under and over the head, a loop round each blade beside the
    # shaft, and a cross over the joint on both faces
    r = 0.045
    cords = []
    cords.append(rope_path(surf, (0, 0, HZ), (0, 0, 1), (1, 0, 0), 3.0, -0.66, -0.44, r * 0.75))
    cords.append(rope_path(surf, (0, 0, HZ), (0, 0, 1), (0, 1, 0), 1.1, 0.44, 0.5, r * 0.75))
    for sy in (-1, 1):
        cords.append(rope_path(surf, (0, sy * 0.33, HZ), (0, sy, 0), (1, 0, 0.3), 1.05, 0.0, 0.06, r * 0.75, per_turn=11))
    for sx in (-1, 1):
        for a, b in (((-0.3, 0.26), (0.3, -0.3)), ((0.3, 0.26), (-0.3, -0.3))):
            pts = []
            for i in range(7):
                t = i / 6
                y, z = a[0] + (b[0] - a[0]) * t, HZ + a[1] + (b[1] - a[1]) * t
                q, nrm = surf.near((sx * 0.5, y, z))
                pts.append(q + nrm * r * 0.75)
            cords.append(pts)
    for pts in cords:
        p.add("rope", loft(pts, [r] * len(pts), P_ROUND5, rings=len(pts) - 1, up=(0, 0, 1)), rp)
    return p.build()


def iron():
    """Tier 2: a forged dark-iron head with hammered facets, a leather grip, an iron collar and
    straps down a wooden shaft."""
    HZ = 4.28
    p = Pick("IronPickaxe", HZ)
    wd = wood("Iron_Wood", base="#6A4428", dark="#3E2614", light="#8C6440", grime=0.0)
    fe = metal("Iron_Iron", base="#25282D", light="#4D545E", dark="#101114", edge="#D9DEE4", hammer=0.2, hammer_size=7.0,
               edge_amt=1.0, edge_radius=0.035, wear="u", horizon="#0F1012")
    lt = wrap("Iron_Leather", base="#5A3A22", dark="#2A170C", light="#8A6040", pitch=0.14)

    p.add("shaft", lathe([(0.2, 0.18), (1.5, 0.183), (2.5, 0.19), (3.5, 0.198), (4.5, 0.2), (HZ + 0.4, 0.19)], segs=12), wd)
    p.add("wedge", block((0.045, 0.3, 0.08), chamfer=0.01), fe, M((0, 0, HZ + 0.39)), crease=30)
    p.add("pommel", lathe([(0.0, 0.15), (0.03, 0.2), (0.06, 0.214), (0.2, 0.214), (0.26, 0.19)], segs=8, phase=TAU / 16), fe, crease=30)
    p.add("grip", lathe([(0.24, 0.188), (0.27, 0.196), (1.42, 0.196), (1.46, 0.19)], segs=14), lt)
    p.add("collar", lathe([(3.46, 0.21), (3.49, 0.234), (3.64, 0.234), (3.67, 0.21)], segs=8, phase=TAU / 16), fe, crease=30)
    for sx in (-1, 1):
        p.add("straps", block((0.05, 0.13, 0.52), chamfer=0.012), fe, M((sx * 0.2, 0, 3.8)), crease=30)
        for z in (3.7, 3.92):
            p.add("rivets", lathe([(0.0, 0.035), (0.012, 0.032), (0.026, 0.012)], segs=6), fe, M((sx * 0.222, 0, z), rot=(0, 90 * sx, 0)), crease=40)

    # the eye: a forged block round the top of the shaft, with a cap where the shaft is wedged
    p.add("eye", block((0.48, 0.52, 0.7), chamfer=0.075, top=(0.92, 0.9), corner=0.05), fe, M((0, 0, HZ + 0.02)), crease=25)
    # the pick curves down to a point; the back is a flat chisel of the same reach
    pick = loft([(0, -0.12, HZ + 0.1), (0, -0.56, HZ + 0.08), (0, -1.0, HZ - 0.07), (0, -1.36, HZ - 0.36)],
                [(0.16, 0.23), (0.14, 0.18), (0.08, 0.105), (0.006, 0.008)], P_OCT, rings=10, jitter=0.11, seed=2)
    p.add("pick", pick, fe, crease=22)
    chisel = loft([(0, 0.12, HZ + 0.1), (0, 0.56, HZ + 0.08), (0, 1.0, HZ - 0.05), (0, 1.36, HZ - 0.27)],
                  [(0.16, 0.23), (0.14, 0.17), (0.11, 0.085), (0.09, 0.014)], P_OCT, rings=10, jitter=0.11, seed=5)
    p.add("chisel", chisel, fe, crease=22)
    return p.build()


def golden():
    """Tier 3: an ornate gold crescent head with engraved lines and a ruby, a black lacquer shaft,
    gold end caps and bands, and a red wrap."""
    HZ = 4.25
    p = Pick("GoldPickaxe", HZ)
    au = gold("Gold_Gold")
    lq = lacquer("Gold_Lacquer")
    rd = wrap("Gold_Wrap", base="#8E1418", dark="#3A0508", light="#C8434A", pitch=0.13, rough=0.7)
    gem = ruby("Gold_Ruby")

    p.add("shaft", lathe([(0.25, 0.18), (1.6, 0.183), (2.6, 0.19), (3.6, 0.196), (4.5, 0.2)], segs=12), lq)
    p.add("pommel", lathe([(0.0, 0.08), (0.02, 0.17), (0.06, 0.215), (0.12, 0.222), (0.16, 0.2), (0.19, 0.205),
                           (0.26, 0.2), (0.3, 0.188)], segs=12), au, crease=35)
    p.add("wrap", lathe([(0.28, 0.19), (0.3, 0.197), (1.5, 0.197), (1.52, 0.19)], segs=14), rd)
    for z0, z1, r in ((1.5, 1.6, 0.21), (2.55, 2.62, 0.205)):
        p.add("bands", lathe([(z0, r - 0.015), (z0 + 0.015, r), (z1 - 0.015, r), (z1, r - 0.015)], segs=12), au, crease=35)
    # a flared gold collar under the head, in three steps
    p.add("collar", lathe([(3.5, 0.2), (3.52, 0.215), (3.6, 0.215), (3.62, 0.205), (3.74, 0.215), (3.78, 0.245), (3.86, 0.25),
                           (3.9, 0.235)], segs=12), au, crease=35)

    # the boss: a stepped gold block with a raised medallion and a ruby on each face
    p.add("boss", block((0.46, 0.6, 0.72), chamfer=0.09, corner=0.06), au, M((0, 0, HZ)), crease=30)
    p.add("boss", block((0.36, 0.5, 0.86), chamfer=0.07, corner=0.05), au, M((0, 0, HZ)), crease=30)
    for sx in (-1, 1):
        disc = lathe([(0.0, 0.22), (0.035, 0.22), (0.055, 0.19), (0.06, 0.14)], segs=12)
        p.add("medallions", disc, au, M((sx * 0.21, 0, HZ), rot=(0, 90 * sx, 0)), crease=40)
        p.add("rubies", bipyramid(0.12, 0.13, sides=8, seed=sx), gem, M((sx * 0.275, 0, HZ), rot=(0, 90, 0)), crease=10)
    # the crescent: two engraved blades curving down to points of the same reach, a fin along the
    # top of each where it leaves the boss
    for sy in (-1, 1):
        arm = loft([(0, sy * 0.15, HZ + 0.1), (0, sy * 0.62, HZ + 0.11), (0, sy * 1.1, HZ - 0.06), (0, sy * 1.4, HZ - 0.45)],
                   [(0.13, 0.28), (0.115, 0.23), (0.07, 0.125), (0.004, 0.005)], P_BLADE, rings=12)
        mark(arm, "eng", 1.0)
        p.add("blades", arm, au, crease=30)
    # on top, a ruby held in a gold crown
    p.add("crown", lathe([(HZ + 0.38, 0.15), (HZ + 0.44, 0.17), (HZ + 0.5, 0.14), (HZ + 0.53, 0.11)], segs=8, phase=TAU / 16), au, crease=35)
    p.add("rubies", bipyramid(0.1, 0.34, sides=8, seed=5), gem, M((0, 0, HZ + 0.62)), crease=10)
    for k in range(4):
        a = TAU / 8 + k * TAU / 4
        c, sn = math.cos(a), math.sin(a)
        prong = loft([(0.12 * c, 0.12 * sn, HZ + 0.48), (0.11 * c, 0.11 * sn, HZ + 0.58), (0.075 * c, 0.075 * sn, HZ + 0.68)],
                     [(0.03, 0.02), (0.028, 0.02), (0.012, 0.01)], P_ROUND6, up=(c, sn, 0), rings=4)
        p.add("crown", prong, au, crease=40)
    return p.build()


def emerald_pick():
    """Tier 4: a dark slate shaft with silver fittings, a hexagonal slate socket holding a glowing
    emerald core, and big faceted emerald crystals for the pick and the back spike."""
    HZ = 4.38
    p = Pick("EmeraldPickaxe", HZ)
    sl = stone("Emerald_Slate", base="#30353A", warm="#3E3A34", edge="#959189", vary=0.35)
    ag = metal("Emerald_Silver", base="#8C949E", light="#F2F6FA", dark="#30353C", edge="#FFFFFF", hammer=0.0, rough=0.45,
               horizon="#262A30", top=0.7, under=0.7)
    gr = wrap("Emerald_Grip", base="#27302C", dark="#0C100E", light="#4A5A52", pitch=0.12)
    gem = emerald("Emerald_Crystal")
    glow = kit.material("GLOW_Emerald", "#17B850", rough=0.4, emit=4.0)

    p.add("pommel", lathe([(0.0, 0.14), (0.03, 0.2), (0.07, 0.22), (0.2, 0.207), (0.25, 0.19)], segs=8, phase=TAU / 16), ag, crease=30)
    p.add("grip", lathe([(0.22, 0.186), (0.25, 0.192), (1.5, 0.192), (1.53, 0.186)], segs=14), gr)
    for z0, z1 in ((0.22, 0.3), (1.48, 1.58), (2.55, 2.63), (3.55, 3.65)):
        p.add("bands", lathe([(z0, 0.198), (z0 + 0.015, 0.214), (z1 - 0.015, 0.214), (z1, 0.198)], segs=8, phase=TAU / 16), ag, crease=30)
    for z0, z1 in ((1.55, 2.58), (2.6, 3.6), (3.62, 4.1)):
        p.add("shaft", lathe([(z0, 0.19), (z0 + 0.03, 0.202), (z1 - 0.03, 0.202), (z1, 0.19)], segs=8, phase=TAU / 16), sl, crease=30)
    # the socket: a hexagonal slate drum bound in silver, the glowing core set in both faces
    drum = lathe([(HZ - 0.36, 0.26), (HZ - 0.31, 0.31), (HZ + 0.31, 0.31), (HZ + 0.36, 0.26)], segs=6, phase=0.0)
    p.add("socket", drum, sl, crease=25)
    for z in (HZ - 0.29, HZ + 0.29):
        p.add("socket bands", lathe([(z - 0.05, 0.315), (z - 0.035, 0.33), (z + 0.035, 0.33), (z + 0.05, 0.315)], segs=6), ag, crease=30)
    for sx in (-1, 1):
        p.add("bezels", ring(0.12, 0.2, 0.06, segs=8, phase=TAU / 16), ag, M((sx * 0.25, 0, HZ), rot=(0, 90 * sx, 0)), crease=30)
    p.add("core", bipyramid(0.155, 0.84, sides=6, seed=1), glow, M((0, 0, HZ), rot=(0, 90, 0)))
    # the crystals: one long blade-like one each way, angled a little down, with two small ones at
    # its foot, each held in a silver collar; a glowing vein runs from the core along each face
    for sy, seed in ((-1, 1), (1, 2)):
        d = Vector((0, sy, -0.24)).normalized()
        foot = Vector((0, sy * 0.24, HZ + 0.06))
        main = crystal(1.3, 0.25, seed=seed, tip=(2.0, 2.4), sink=0.5, taper=(0.82, 0.9))
        main.transform(aim(foot, d, 0) @ M(scale=(0.72, 1.22, 1.0)))
        surf = Surface(main)
        for sx in (-1, 1):
            pts, nrms = [], []
            for k in range(6):
                q = foot + d * (0.16 + 0.13 * k)
                h, n = surf.near(q + Vector((sx * 0.5, 0, 0.02 * math.sin(k * 1.7))))
                pts.append(h)
                nrms.append(n)
            p.add("veins", ribbon(pts, nrms, 0.07, 0.012, sink=0.006), glow)
        p.add("crystals", main, gem, crease=15)
        p.add("collars", lathe([(0.0, 0.25), (0.02, 0.285), (0.12, 0.285), (0.14, 0.26)], segs=6), ag, aim(foot + d * 0.04, d, 0), crease=30)
        for k, (tilt, ln, r, lift) in enumerate(((46, 0.56, 0.11, 0.24), (-44, 0.46, 0.1, -0.22))):
            dd = Matrix.Rotation(math.radians(-tilt * sy), 3, 'X') @ d
            p.add("crystals", crystal(ln, r, seed=seed * 10 + k), gem, aim(foot + d * 0.2 + Vector((0, 0, lift)), dd, 20), crease=15)
    p.add("finial", crystal(0.42, 0.1, seed=7, tip=(1.8, 2.2)), gem, M((0, 0, HZ + 0.3)), crease=15)
    return p.build()


def ember():
    """Tier 5 (legendary): a dragon-scaled shaft that ends in a claw gripping a jagged black obsidian
    pick with glowing ember cracks and a row of small blades along its back; behind, a ridged dragon
    horn of the same reach."""
    HZ = 4.72
    p = Pick("EmberPickaxe", HZ)
    scale = kit.scaly(kit.material("Ember_Scale", "#34292B"), size=0.1, joins=0.6, vary=0.25, rough=0.8)
    tones(scale, up="#4A3A3A", down="#120D0E", up_mix=0.45, down_mix=0.5)
    horn = kit.scaly(kit.material("Ember_Horn", "#1A1718"), size=0.5, joins=0.08, vary=0.08, rough=0.5)
    ramp_by(horn, "u", [(0.0, "#0E0C0D"), (0.45, "#221D1B"), (0.72, "#8F7E62"), (1.0, "#EDE2C4")])
    ob = obsidian("Ember_Obsidian", heat="#4A0E06")
    fe = metal("Ember_Iron", base="#2A2626", light="#4E4846", dark="#0E0C0C", edge="#9A8478", hammer=0.1, rough=0.55)
    bronze = metal("Ember_Bronze", base="#5A3A22", light="#9A6A3C", dark="#24160C", edge="#D2A070", hammer=0.08, rough=0.5)
    rim = kit.material("Ember_Heat", "#6A1E0A", rough=0.6)
    glow = kit.material("GLOW_Ember", "#FF6A14", rough=0.4, emit=6.0)

    p.add("pommel", lathe([(0.1, 0.13), (0.14, 0.2), (0.2, 0.218), (0.3, 0.205), (0.34, 0.19)], segs=8, phase=TAU / 16), bronze, crease=30)
    p.add("pommel", hull(spindle((0, 0, 0.16), (0, 0, 0.0), (0.14, 0.14), n=14, seed=4, power=0.9, diamond=2.0)), ob, crease=1.0)
    p.add("shaft", lathe([(0.32, 0.19), (1.6, 0.192), (2.6, 0.198), (3.6, 0.205), (4.2, 0.21)], segs=14), scale)
    for z0, z1 in ((1.6, 1.7), (3.05, 3.13)):
        p.add("bands", lathe([(z0, 0.2), (z0 + 0.02, 0.224), (z1 - 0.02, 0.224), (z1, 0.2)], segs=8, phase=TAU / 16), bronze, crease=30)
    # the claw's wrist under the head
    p.add("wrist", lathe([(4.0, 0.21), (4.12, 0.245), (4.26, 0.265), (4.42, 0.25), (4.5, 0.2)], segs=10), scale)
    # the obsidian head: knapped pieces following a curve down to the point in front and to a
    # heavier spike behind, meeting over the shaft
    pieces = [((0, 0.3, HZ + 0.05), (0, -0.8, HZ - 0.02), (0.23, 0.38), (0.13, 0.22), 1, 1.0),
              ((0, -0.62, HZ + 0.01), (0, -1.24, HZ - 0.23), (0.14, 0.24), (0.07, 0.1), 2, 1.0),
              ((0, -1.08, HZ - 0.12), (0, -1.52, HZ - 0.5), (0.085, 0.13), (0.0, 0.0), 3, 1.0),
              ((0, -0.3, HZ + 0.05), (0, 0.85, HZ - 0.06), (0.23, 0.36), (0.14, 0.2), 4, 1.0),
              ((0, 0.7, HZ - 0.02), (0, 1.52, HZ - 0.46), (0.14, 0.2), (0.03, 0.04), 5, 1.0)]
    obs = []
    for a, b, h, th, seed, pw in pieces:
        bm = hull(spindle(a, b, h, n=28, seed=seed * 7, power=pw, diamond=1.3, tip_half=th, jit=0.24),
                  attr=lambda co: min(1.0, abs(co.y) / 1.5))
        obs.append(bm.copy())
        p.add("obsidian", bm, ob, crease=1.0)
    # small raked blades along the top of the pick, like the dragon's back
    body = Surface(*obs)
    for k, (y, h) in enumerate(((-0.34, 0.19), (-0.6, 0.15), (-0.84, 0.11))):
        q, _ = body.hit(Vector((0, y, HZ + 1.0)), (0, 0, -1))
        shard = hull(spindle(q - Vector((0, 0, 0.05)), q + Vector((0, 0.1, h)), (0.06, 0.1), n=12, seed=40 + k, power=1.0, diamond=1.2, jit=0.2),
                     attr=lambda co: 0.6)
        obs.append(shard.copy())
        p.add("obsidian", shard, ob, crease=1.0)
    surf = Surface(*obs)
    for bm in obs:
        bm.free()
    # ember cracks on both faces, each with a dark red scorched rim
    cracks = [[(-0.2, 0.16), (-0.4, 0.04), (-0.58, 0.07), (-0.78, -0.04), (-0.98, -0.1), (-1.18, -0.24), (-1.32, -0.36)],
              [(-0.4, 0.04), (-0.48, -0.12), (-0.64, -0.2)],
              [(-0.78, -0.04), (-0.86, 0.1)],
              [(-0.98, -0.1), (-1.04, -0.22)],
              [(0.22, 0.14), (0.42, 0.02), (0.62, 0.04), (0.86, -0.08), (1.08, -0.18)],
              [(0.62, 0.04), (0.7, -0.14)]]
    for sx in (-1, 1):
        for path in cracks:
            pts, nrms = [], []
            for y, dz in path:
                q, n = surf.near((sx * 0.5, y, HZ + dz))
                pts.append(q)
                nrms.append(n)
            p.add("crack rims", ribbon(pts, nrms, 0.1, 0.006), rim)
            p.add("cracks", ribbon(pts, nrms, 0.034, 0.018), glow)
    # the claw: two talons each side, from the knuckles of the wrist up over the faces of the head,
    # lying against the obsidian as if gripping it
    for sx in (-1, 1):
        for sy in (-1, 1):
            base = Vector((sx * 0.19, sy * 0.13, HZ - 0.42))
            path = [base]
            for (yy, zz) in ((0.22, -0.2), (0.3, 0.0), (0.36, 0.17), (0.4, 0.27)):
                q, n = surf.near((sx * 0.6, sy * yy, HZ + zz))
                path.append(q + n * 0.05)
            p.add("talons", loft(path, [0.085, 0.08, 0.065, 0.04, 0.008], P_CLAW, up=(sx, 0, 0.1), rings=8), horn, crease=50)
            p.add("knuckles", kit.ball((0.15, 0.15, 0.15), cuts=1), scale, M((sx * 0.19, sy * 0.13, HZ - 0.42)))
    # two small dragon horns sweeping back from the top of the head
    for sx in (-1, 1):
        q, _ = surf.hit(Vector((sx * 0.08, 0.05, HZ + 1.0)), (0, 0, -1))
        hp = [q - Vector((0, 0, 0.06)), q + Vector((sx * 0.06, 0.22, 0.1)), q + Vector((sx * 0.1, 0.48, 0.13)), q + Vector((sx * 0.12, 0.66, 0.1))]
        p.add("horns", loft(hp, [0.075, 0.06, 0.035, 0.006], P_HORN, up=(sx * 0.4, 0, 1), rings=6), horn, crease=50)
    # the glowing heart of the head, showing on both faces where the talons meet
    p.add("core", bipyramid(0.12, 0.62, sides=6, seed=3), glow, M((0, 0, HZ - 0.02), rot=(0, 90, 0)))
    return p.build()


TIERS = [
    ("WoodenPickaxe", "wooden_pickaxe", wooden, dict(rough=0.85, shade=0.55)),
    ("IronPickaxe", "iron_pickaxe", iron, dict(rough=0.6, shade=0.6)),
    ("GoldPickaxe", "gold_pickaxe", golden, dict(rough=0.5, shade=0.55)),
    ("EmeraldPickaxe", "emerald_pickaxe", emerald_pick, dict(rough=0.6, shade=0.6)),
    ("EmberPickaxe", "ember_pickaxe", ember, dict(rough=0.6, shade=0.6)),
]


def bake(pick, colour_path, size, samples, rough, shade):
    """Everything that does not glow becomes <Name>_Handle with one baked colour image; the glowing
    parts, if any, become <Name>_GLOW with their one emissive material."""
    glow = [ob for ob in pick.prop.objects if "GLOW" in ob.name]
    handle = kit.bake_texture([ob for ob in pick.prop.objects if ob not in glow], colour_path, size=size, shade=shade,
                              samples=samples, rough=rough, soften=2, name=pick.name + "_Handle",
                              uv_angle=75.0, uv_margin=0.004, pack_margin=0.003)
    objs = [handle]
    if glow:
        bpy.ops.object.select_all(action='DESELECT')
        for ob in glow:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = glow[0]
        if len(glow) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = pick.name + "_GLOW"
        objs.append(g)
    pick.objects = objs
    return objs


def measure(pick, size):
    """The numbers for the report: triangles, size, where the shaft sits in the bounding box, how
    thick the grip is 0.7 studs up, and how much of the texture image is used."""
    h = pick.objects[0]
    pts = [h.matrix_world @ v.co for v in h.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    grip = []
    me = h.data
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        if (a.z - 0.7) * (b.z - 0.7) < 0:
            t = (0.7 - a.z) / (b.z - a.z)
            q = a.lerp(b, t)
            grip.append(math.hypot(q.x, q.y))
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        ps = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(ps[i].x * ps[(i + 1) % len(ps)].y - ps[(i + 1) % len(ps)].x * ps[i].y for i in range(len(ps)))) / 2
    return {
        "tris": {ob.name: sum(len(pl.vertices) - 2 for pl in ob.data.polygons) for ob in pick.objects},
        "length": hi.z - lo.z, "head": hi.y - lo.y, "thick": hi.x - lo.x, "bottom": lo.z,
        "centre": ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2),
        "grip": (2 * min(grip), 2 * max(grip)) if grip else (0, 0),
        "used": a2, "px_per_stud": (a2 * size * size / a3) ** 0.5,
    }


# ---- review sheet -----------------------------------------------------------------------------------------

class Stage:
    """review.py's lights, world, grey ground and 5-stud block, with cameras for a row of pickaxes."""

    def __init__(self, samples):
        import review
        self.review = review
        sc = bpy.context.scene
        self.samples = samples
        sc.render.engine = 'CYCLES'
        sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = 'CPU', samples, True
        sc.view_settings.view_transform = 'Standard'
        sc.render.resolution_percentage = 100
        self.world = bpy.data.worlds.new("ReviewWorld")
        sc.world = self.world
        try:
            self.world.use_nodes = True
        except Exception:
            pass
        self.bg = next(n for n in self.world.node_tree.nodes if n.type == 'BACKGROUND')
        self.ground = self._object("ReviewGround", kit.rounded_box((400, 400, 0.2), n=20, cuts=0),
                                   kit.material("ReviewGrey", "#8A8D91", rough=0.9), (0, 0, -0.1))
        self.dummy = self._object("ReviewDummy", kit.rounded_box((2, 1, 5), n=8, cuts=2),
                                  kit.material("ReviewDummy", "#5C7C99", rough=0.7), (0, 0, 2.5))
        self.lights = [review._light("Key", (0, -1, 1), (0, 0, 0), 1, 1), review._light("Fill", (1, -1, 0), (0, 0, 0), 1, 1, (0.85, 0.92, 1.0)),
                       review._light("Rim", (0, 1, 1), (0, 0, 0), 1, 1, (1.0, 0.95, 0.85))]
        self.black = bpy.data.materials.new("ReviewBlack")
        b = kit.principled(self.black)
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Roughness"].default_value = 1.0
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.0

    def _object(self, name, bm, mat, loc):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.location = loc
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def light(self, c, size):
        """The review rig's three lights, placed for something `size` studs across centred on `c`."""
        c = Vector(c)
        for ob, off, watts, sz in zip(self.lights, ((-0.9, -1.2, 1.5), (1.3, -0.8, 0.4), (0.5, 1.3, 1.1)), (165, 55, 150), (1.6, 2.2, 1.2)):
            ob.location = c + Vector(off) * size * 1.6
            ob.data.energy, ob.data.size = watts * size * size, size * sz
            self.review._aim(ob, c)

    def camera(self, name, loc, target, fov=30.0, ortho=None):
        cam = self.review._camera(name, loc, target, fov)
        cam.data.clip_end = 1000.0
        cam.data.sensor_fit = 'VERTICAL'
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
        else:
            cam.data.angle = math.radians(fov)
        return cam

    def render(self, path, cam, w, h, silhouette=False, dummy=False, samples=None):
        sc, lay = bpy.context.scene, bpy.context.view_layer
        sc.camera = cam
        sc.cycles.samples = samples or self.samples
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.filepath = path
        lay.material_override = self.black if silhouette else None
        self.ground.hide_render = silhouette
        self.dummy.hide_render = silhouette or not dummy
        self.bg.inputs[0].default_value = (1, 1, 1, 1) if silhouette else (0.045, 0.05, 0.06, 1)
        for ob in self.lights:
            ob.hide_render = silhouette
        bpy.ops.render.render(write_still=True)
        lay.material_override = None
        return path


def place(pick, x, turn, y=0.0):
    for ob in pick.objects:
        ob.location = (x, y, 0.0)
        ob.rotation_euler = (0.0, 0.0, math.radians(turn))
        ob.hide_render = False
    bpy.context.view_layer.update()


def sheet(picks, out, samples=24, tile=420, title=""):
    """All the pickaxes side by side in tier order: front 3/4 and side, each tile rendered with the
    same orthographic camera and lights so they are at the same scale and lit alike; a close-up of
    each head; silhouettes at a third of the size; and all of them together next to the 5-stud block."""
    from PIL import Image, ImageDraw, ImageFont
    folder = os.path.splitext(out)[0] + "_views"
    os.makedirs(folder, exist_ok=True)
    st = Stage(samples)
    n = len(picks)
    tall = 640
    span = 6.0                                   # studs shown from top to bottom of a tile

    def solo(pk):
        for other in picks:
            for ob in other.objects:
                ob.hide_render = other is not pk

    def tiles(name, turn, tilt, silhouette=False):
        paths = []
        target = Vector((0, 0, 2.6))
        cam = st.camera("C_" + name, target + Vector((0, -1, tilt)).normalized() * 60, target, ortho=span)
        st.light(Vector((0, 0, 2.6)), 5.5)
        for i, pk in enumerate(picks):
            solo(pk)
            place(pk, 0, turn)
            path = os.path.join(folder, "%s_%d.png" % (name, i))
            st.render(path, cam, tile, tall, silhouette=silhouette)
            paths.append(path)
        return paths

    front = tiles("front34", 35, 0.22)
    side = tiles("side", 90, 0.12)
    sil = tiles("silhouette", 35, 0.12, silhouette=True)
    close = []
    for i, pk in enumerate(picks):
        solo(pk)
        place(pk, 0, 35)
        target = Vector((0, -0.12, pk.head_z - 0.14))
        cam = st.camera("C_close%d" % i, target + Vector((0, -1, 0.3)).normalized() * 5.0, target, fov=30)
        st.light(target, 3.5)
        path = os.path.join(folder, "close_%d.png" % i)
        st.render(path, cam, tile, tile)
        close.append(path)
    # all of them together next to the 5-stud block
    for pk in picks:
        for ob in pk.objects:
            ob.hide_render = False
    gap = 3.0
    xs = [i * gap for i in range(n)]
    for pk, x in zip(picks, xs):
        place(pk, x, 35)
    st.dummy.location = (xs[-1] + 2.6, 0.6, 2.5)
    lo_x, hi_x = -1.6, xs[-1] + 3.8
    target = Vector(((lo_x + hi_x) / 2, 0, 2.2))
    wide = hi_x - lo_x
    away = (wide / 2 + 1.0) / math.tan(math.radians(15))
    cam = st.camera("C_scale", target + Vector((-0.28, -1.0, 0.3)).normalized() * away, target, fov=30)
    cam.data.sensor_fit = 'HORIZONTAL'
    st.light(target, max(wide, 6.0))
    scale_h = int(tall * 0.85)
    scale_path = os.path.join(folder, "scale.png")
    st.render(scale_path, cam, n * tile, scale_h, dummy=True)

    W = n * tile
    font = small = None
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.exists(f):
        font, small = ImageFont.truetype(f, 18), ImageFont.truetype(f, 15)
    else:
        font = small = ImageFont.load_default()
    labels = [pk.name.replace("Pickaxe", "") for pk in picks]
    sil_h = tall // 3
    heights = [36, tall, tall, tile, sil_h, scale_h]
    canvas = Image.new("RGB", (W, sum(heights)), (18, 20, 24))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title, fill=(235, 235, 235), font=font)

    def tag(x, y, text):
        w = d.textlength(text, font=small)
        d.rectangle((x, y, x + w + 12, y + 22), fill=(0, 0, 0))
        d.text((x + 6, y + 3), text, fill=(255, 255, 255), font=small)

    y = 36
    for label, paths in (("front 3/4", front), ("side", side)):
        for i, pth in enumerate(paths):
            canvas.paste(Image.open(pth).convert("RGB"), (i * tile, y))
            name = "%d %s" % (i + 1, labels[i])
            d.text((i * tile + tile // 2 - d.textlength(name, font=small) / 2, y + tall - 26), name, fill=(25, 25, 25), font=small)
        tag(0, y, label)
        y += tall
    for i, pth in enumerate(close):
        canvas.paste(Image.open(pth).convert("RGB"), (i * tile, y))
        tag(i * tile, y, labels[i] + " head")
    y += tile
    for i, pth in enumerate(sil):
        img = Image.open(pth).convert("RGB").resize((tile // 3, sil_h), Image.LANCZOS)
        canvas.paste(img, (i * (tile // 3), y))
    d.text((n * (tile // 3) + 12, y + 10), "silhouettes at a third of the size", fill=(200, 200, 200), font=small)
    y += sil_h
    canvas.paste(Image.open(scale_path).convert("RGB"), (0, y))
    tag(0, y, "all five next to the 5-stud block")
    canvas.save(out)
    return out


# ---- main -------------------------------------------------------------------------------------------------

def pick_names(only):
    if not only:
        return TIERS
    want = [o.lower().replace("_", "").replace("pickaxe", "") for o in only]
    return [t for t in TIERS if t[0].lower().replace("pickaxe", "") in want]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", help="build only these, e.g. --only ember or --only wooden iron")
    ap.add_argument("--export-dir", default=os.path.join(MODELS, "export"))
    ap.add_argument("--sheet", default=os.path.join(MODELS, "preview", "pickaxes.png"))
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--size", type=int, default=512, help="texture size in pixels")
    ap.add_argument("--bake-samples", type=int, default=32)
    ap.add_argument("--samples", type=int, default=24, help="render samples for the sheet")
    ap.add_argument("--title", default="Pickaxes, round 3")
    a = ap.parse_args()
    kit.fresh()
    os.makedirs(a.export_dir, exist_ok=True)
    picks = []
    for k, (name, stem, fn, opts) in enumerate(pick_names(a.only)):
        pk = fn()
        print("%s: triangles by part %s" % (name, dict(sorted(pk.tally.items(), key=lambda kv: -kv[1]))))
        bake(pk, os.path.join(a.export_dir, stem + "_colour.png"), a.size, a.bake_samples, opts["rough"], opts["shade"])
        info = measure(pk, a.size)
        print("%s: %s" % (name, ", ".join("%s %d" % kv for kv in info["tris"].items())))
        print("%s: %.2f long, head %.2f across (Y), %.2f thick (X); bottom z=%.3f; shaft off the box centre by (%.3f, %.3f); "
              "grip at 0.7 is %.3f to %.3f thick; texture %d px, %.0f%% used, %.0f px per stud"
              % (name, info["length"], info["head"], info["thick"], info["bottom"], info["centre"][0], info["centre"][1],
                 info["grip"][0], info["grip"][1], a.size, info["used"] * 100, info["px_per_stud"]))
        kit.export_fbx(pk.objects, os.path.join(a.export_dir, stem + ".fbx"))
        for ob in pk.objects:
            ob.location.x = 200 + 40 * k                 # out of the way while the next one is baked
        picks.append(pk)
    if not a.no_sheet:
        os.makedirs(os.path.dirname(os.path.abspath(a.sheet)), exist_ok=True)
        sheet(picks, os.path.abspath(a.sheet), samples=a.samples, title=a.title)
        print("sheet", a.sheet)


if __name__ == "__main__":
    main()
