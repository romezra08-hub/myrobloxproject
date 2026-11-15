"""The Hatchery: the egg hatching station for "Mine an Egg". Built from scratch by script.

    python models/props/hatchery.py                       # Roblox files in models/export, sheet in models/preview/hatchery.png
    python models/props/hatchery.py --sheet out.png       # the review sheet somewhere else
    python models/props/hatchery.py --peek out.png        # a quick unbaked look while building

A sturdy mining-camp machine with a magical heart. Players bring the eggs they mine here; the egg sits
on a cushioned cradle under a big glass dome while four crystal pylons feed it light.

  Base       a round two-tier plinth of hewn stone blocks, 9.5 studs across and 1 stud high, with a
             stair at the front (-Y)
  Frame      a riveted iron drum with glowing rune windows, a brass collar, four iron straps over a
             glass bell dome 4.5 studs wide, a brass crown and vent on top
  Glow       four iron pylons on the diagonals with teal crystals lit from inside, conduits glowing
             down into the drum, rune glyphs inlaid in the stone
  Machinery  a control desk on the left (-X) with gauges and a big lever, an egg hopper with a chute
             at the back
  Mining     worn mining-yellow paint on the desk and the hopper, hazard stripes on the stair nosing
             and the hopper rim only

It arrives in Roblox as three MeshParts:
  Hatchery_Body   everything that does not glow or let light through, colours and crease shading baked
                  into hatchery_colour.png, roughness in hatchery_rough.png
  Hatchery_GLOW   crystal cores, runes and conduits, one emissive material GLOW_Hatchery (make it Neon)
  Hatchery_Glass  the dome, one plain material Hatchery_Glass (make it Glass, Transparency about 0.6)
and an empty, Hatchery_EggSpot, where the bottom of an egg should sit. The dome is left empty.
Bottom at z = 0, front (the stair and the lever) facing -Y.
"""
import argparse
import math
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, ".."))
TAU = 2 * math.pi
UP = Vector((0.0, 0.0, 1.0))
LIGHT = (-0.45, -0.55, 0.7)

# ---- layout (studs) ---------------------------------------------------------------------------------
R_LOW, R_UP, R_DRUM = 4.75, 4.15, 2.6          # lower tier, upper tier, iron drum
Z_TIER, Z_TOP, Z_DRUM, Z_COLLAR = 0.5, 1.0, 1.5, 1.85
R_GLASS, GLASS_T = 2.25, 0.06                  # outer radius and thickness of the dome
Z_WALL = 4.7                                   # top of the straight glass wall, centre of the dome cap
EGG_SPOT = Vector((0.0, 0.0, 2.18))            # where an egg's bottom rests on the cradle
PYLON_R, PYLON_TH = 3.6, (45, 135, 225, 315)   # pylons on the diagonals
CONSOLE_TH, HOPPER_TH = 270.0, 90.0
SOOT = [Vector((0, 0, 7.6))]


def polar(th, r, z=0.0):
    """th degrees round from the front (-Y) towards +X."""
    a = math.radians(th)
    return Vector((math.sin(a) * r, -math.cos(a) * r, z))


def outward(th):
    a = math.radians(th)
    return Vector((math.sin(a), -math.cos(a), 0.0))


# ---- small helpers (from the driller and the ore rocks) -----------------------------------------------

def layer(bm, name):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def sharpen(bm, degrees):
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def aim(origin, direction, roll=0.0):
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


def basis(origin, x, z):
    """A right-handed transform at `origin` whose Z is `z` and whose X is as near `x` as it can be."""
    z = Vector(z).normalized()
    x = Vector(x)
    x = (x - z * x.dot(z)).normalized()
    m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def slice_off(bm, co, no):
    no = Vector(no).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return bm


def chamfer(bm, width, degrees=30.0):
    if width <= 0:
        return bm
    bm.normal_update()
    lim = math.radians(degrees)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type='OFFSET', segments=1, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    return bm


def block(size, bevel=0.04, top=(1.0, 1.0), shift=(0.0, 0.0), cuts=()):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    sx, sy, sz = (s / 2.0 for s in size)
    for v in bm.verts:
        t = top if v.co.z > 0 else (1.0, 1.0)
        d = shift if v.co.z > 0 else (0.0, 0.0)
        v.co = Vector((v.co.x * sx * t[0] + d[0], v.co.y * sy * t[1] + d[1], v.co.z * sz))
    for co, n in cuts:
        slice_off(bm, co, n)
    return chamfer(bm, bevel)


def lathe(profile, segs=24, a0=0.0, a1=None, close=True):
    """Revolve a list of (r, z) round +Z. A point with r == 0 becomes a pole; a full turn is closed."""
    full = a1 is None
    a1 = TAU if full else a1
    n = segs if full else segs + 1
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(a0 + (a1 - a0) * j / segs), r * math.sin(a0 + (a1 - a0) * j / segs), z))
                          for j in range(n)])
    for a, b in zip(rings, rings[1:]):
        m = segs if full else segs
        for j in range(m):
            k = (j + 1) % n
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[j], b[k]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[k], b[0]))
            else:
                bm.faces.new((a[j], a[k], b[k], b[j]))
    if close and full:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2:
                bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def orient(bm, sign):
    """Turn every face of a dome shell to face away from (sign 1) or towards (-1) its axis."""
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        d = c - Vector((0, 0, min(c.z, Z_WALL)))
        if f.normal.dot(d) * sign < 0:
            f.normal_flip()
    return bm


def cylinder(r, length, segs=12, bevel=0.03, r2=None):
    r2 = r if r2 is None else r2
    h = length / 2
    if bevel <= 0:
        return lathe([(0, -h), (r, -h), (r2, h), (0, h)], segs)
    return lathe([(0, -h), (r - bevel, -h), (r, -h + bevel), (r2, h - bevel), (r2 - bevel, h), (0, h)], segs)


def wedge(r0, r1, a0, a1, z0, z1, segs=4, bevel=0.06, jag=None):
    """An annular sector block (a stone of a round plinth): angles in degrees from the front."""
    bm = bmesh.new()
    rings = []
    for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1)):
        rings.append([bm.verts.new(polar(a0 + (a1 - a0) * j / segs, r, z)) for j in range(segs + 1)])
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for j in range(segs):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bm.faces.new([r[0] for r in rings])
    bm.faces.new([r[-1] for r in rings][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if jag:
        rnd = random.Random(jag)
        for v in bm.verts:
            if v.co.z > z0 + 1e-4:
                v.co.z += rnd.uniform(-0.025, 0.02)
            d = Vector((v.co.x, v.co.y, 0)).normalized()
            if math.hypot(v.co.x, v.co.y) > r1 - 1e-3:
                v.co += d * rnd.uniform(-0.04, 0.03)
    return chamfer(bm, bevel, 25.0)


def rivet(r=0.05, h=0.04, segs=5):
    bm = bmesh.new()
    lo = [bm.verts.new((r * math.cos(TAU * j / segs), r * math.sin(TAU * j / segs), -0.02)) for j in range(segs)]
    mid = [bm.verts.new((r * 0.92 * math.cos(TAU * j / segs), r * 0.92 * math.sin(TAU * j / segs), h * 0.55)) for j in range(segs)]
    top = bm.verts.new((0, 0, h))
    for j in range(segs):
        k = (j + 1) % segs
        bm.faces.new((lo[j], lo[k], mid[k], mid[j]))
        bm.faces.new((mid[j], mid[k], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def sweep(points, normals, w, t):
    """A flat strap `w` wide and `t` thick laid along `points`, its back on the surface whose outward
    normals are `normals`."""
    bm = bmesh.new()
    rings = []
    n = len(points)
    for i, (p, nr) in enumerate(zip(points, normals)):
        tang = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
        side = tang.cross(nr).normalized()
        rings.append([bm.verts.new(p + side * sx * w / 2 + nr * nz) for sx, nz in ((-1, 0), (1, 0), (1, t), (-1, t))])
    for a, b in zip(rings, rings[1:]):
        for j in range(4):
            k = (j + 1) % 4
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def torus(R, r, nu=20, nv=10, pinch=0.0, lobes=8):
    """A ring cushion: `pinch` pulls it in at `lobes` seams, so it reads as a ring of stuffed pillows."""
    bm = bmesh.new()
    rings = []
    for i in range(nu):
        u = TAU * i / nu
        k = 1.0 - pinch * (0.5 + 0.5 * math.cos(lobes * u)) ** 6
        rings.append([bm.verts.new(((R + r * k * math.cos(TAU * j / nv)) * math.cos(u),
                                    (R + r * k * math.cos(TAU * j / nv)) * math.sin(u),
                                    r * k * 0.9 * math.sin(TAU * j / nv))) for j in range(nv)])
    for i in range(nu):
        a, b = rings[i], rings[(i + 1) % nu]
        for j in range(nv):
            bm.faces.new((a[j], b[j], b[(j + 1) % nv], a[(j + 1) % nv]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, taper=(0.78, 0.92), sides=6):
    """A crystal along +Z (from the ore rocks); "g" runs 0 at the foot to 1 at the tip."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    g = layer(bm, "g")
    turn = rnd.uniform(0, TAU / sides)
    tip_h = min(radius * rnd.uniform(*tip), length * 0.45)
    shoulder = length - tip_h
    tp = rnd.uniform(*taper)
    radii = [radius * rnd.uniform(0.88, 1.1) for _ in range(sides)]
    rings = []
    for z, s, gv in ((-sink * radius - 0.05, 1.0, 0.0), (shoulder, tp, 0.8)):
        ring = []
        for j in range(sides):
            a = turn + j * TAU / sides
            v = bm.verts.new((math.cos(a) * radii[j] * s, math.sin(a) * radii[j] * s, z))
            v[g] = gv
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.12, 0.12) * radius, rnd.uniform(-0.12, 0.12) * radius, length))
    apex[g] = 1.0
    lo, hi = rings
    for j in range(sides):
        k = (j + 1) % sides
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lit_crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, slit=0.016, sides=6):
    """A crystal lit from inside (from the ore rocks): facets a hair apart round a glowing core."""
    whole = crystal(length, radius, seed, tip, sink, sides=sides)
    src = whole.verts.layers.float.get("g")
    facets = bmesh.new()
    g = layer(facets, "g")
    for f in whole.faces:
        c = f.calc_center_median()
        vs = []
        for v in f.verts:
            d = v.co - c
            nv = facets.verts.new(c + d * max(0.0, 1 - slit / max(d.length, 1e-6)))
            nv[g] = v[src]
            vs.append(nv)
        facets.faces.new(vs)
    whole.free()
    return facets, crystal(length * 0.95, radius * 0.78, seed, tip, sink, sides=sides)


def _hemisphere():
    out = [Vector((0, 0, 1))]
    for tilt, n in ((25, 6), (50, 9), (72, 12), (86, 14)):
        t = math.radians(tilt)
        for j in range(n):
            a = TAU * (j + 0.5 * (tilt // 25 % 2)) / n
            out.append(Vector((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))))
    return out


def cull_hidden(parts, keep=("GLOW", "Glass"), see_through=("Glass",)):
    """Delete the faces no camera can see (from the driller); the glass does not hide anything."""
    verts, polys = [], []
    for key, (bm, _) in parts.items():
        if any(k in key for k in see_through):
            continue
        base = len(verts)
        bm.verts.index_update()
        verts += [v.co.copy() for v in bm.verts]
        polys += [[base + v.index for v in f.verts] for f in bm.faces]
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = _hemisphere()
    removed = 0
    for key, (bm, _) in parts.items():
        if any(k in key for k in keep):
            continue
        bm.normal_update()
        dead = []
        for f in bm.faces:
            n = f.normal
            if n.length < 0.5:
                continue
            c = f.calc_center_median()
            if c.z < 0.02 and n.z < -0.9:
                dead.append(f)
                continue
            rot = n.to_track_quat('Z', 'Y').to_matrix()
            world = [rot @ d for d in dirs]
            seen = False
            for p in [c] + [c.lerp(v.co, 0.8) for v in f.verts[:8]]:
                o = p + n * 0.004
                for d in world:
                    if bvh.ray_cast(o, d, 60.0)[0] is None:
                        seen = True
                        break
                if seen:
                    break
            if not seen:
                dead.append(f)
        removed += sum(len(f.verts) - 2 for f in dead)
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return removed


# ---- materials: worked out in 3D and baked into the colour image ---------------------------------------

class Nodes:
    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new
        self._co = None
        self.bsdf = kit.principled(mat)

    @property
    def co(self):
        if self._co is None:
            self._co = self.new("ShaderNodeTexCoord").outputs["Object"]
        return self._co

    def attr(self, name):
        a = self.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs["Fac"]

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        n.inputs["Roughness"].default_value = rough
        self.link(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def voronoi(self, vec, scale, feature='F1'):
        v = self.new("ShaderNodeTexVoronoi")
        v.feature = feature
        v.inputs["Scale"].default_value = scale
        self.link(vec, v.inputs["Vector"])
        return v

    def stretched(self, scale, rot=(0, 0, 0)):
        mp = self.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Rotation"].default_value = [math.radians(a) for a in rot]
        self.link(self.co, mp.inputs["Vector"])
        return mp.outputs["Vector"]

    def warp(self, co, scale, amount):
        n = self.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, 3.0
        self.link(co, n.inputs["Vector"])
        wv = self.new("ShaderNodeVectorMath")
        wv.operation = 'MULTIPLY_ADD'
        self.link(n.outputs["Color"], wv.inputs[0])
        wv.inputs[1].default_value = (amount, amount, amount)
        self.link(co, wv.inputs[2])
        return wv.outputs[0]

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

    def facing(self, direction, true=True):
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(geo.outputs["True Normal" if true else "Normal"], dot.inputs[0])
        dot.inputs[1].default_value = Vector(direction).normalized()
        return dot.outputs["Value"]

    def up(self, lo, hi):
        geo = self.new("ShaderNodeNewGeometry")
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(geo.outputs["Normal"], sep.inputs[0])
        return self.ramp(sep.outputs[2], lo, hi)

    def edge(self, radius=0.03, lo=0.997, hi=0.93):
        bev = self.new("ShaderNodeBevel")
        bev.samples = 6
        bev.inputs["Radius"].default_value = radius
        geo = self.new("ShaderNodeNewGeometry")
        dot = self.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        self.link(bev.outputs["Normal"], dot.inputs[0])
        self.link(geo.outputs["Normal"], dot.inputs[1])
        return self.ramp(dot.outputs["Value"], lo, hi)

    def cavity(self, distance=0.25, lo=0.95, hi=0.45):
        ao = self.new("ShaderNodeAmbientOcclusion")
        ao.only_local = True
        ao.samples = 8
        ao.inputs["Distance"].default_value = distance
        return self.ramp(ao.outputs["AO"], lo, hi)

    def height(self, lo, hi, a=1.0, b=0.0):
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(self.co, sep.inputs[0])
        return self.ramp(sep.outputs[2], lo, hi, a, b)

    def near(self, points, r0, r1):
        out = None
        for p in points:
            d = self.new("ShaderNodeVectorMath")
            d.operation = 'DISTANCE'
            self.link(self.co, d.inputs[0])
            d.inputs[1].default_value = tuple(p)
            f = self.ramp(d.outputs["Value"], r0, r1, 1.0, 0.0)
            out = f if out is None else self.math('MAXIMUM', out, f)
        return out

    def island(self):
        return self.new("ShaderNodeNewGeometry").outputs["Random Per Island"]

    def scratches(self, density=0.5):
        out = None
        for rot in ((0, 0, 28), (35, 0, -52)):
            v = self.stretched((2.2, 2.2, 2.2), rot)
            mp = self.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (60.0, 2.0, 2.0)
            self.link(v, mp.inputs["Vector"])
            line = self.ramp(self.noise(mp.outputs["Vector"], 1.0, 2.0, 0.5), 0.735, 0.748, smooth=False)
            out = line if out is None else self.math('MAXIMUM', out, line)
        patch = self.ramp(self.noise(self.co, 2.4, 2.0), 0.48, 0.6)
        return self.math('MULTIPLY', self.math('MULTIPLY', out, patch), density)

    def out(self, col, rough):
        self.link(col, self.bsdf.inputs["Base Color"])
        self.bsdf.inputs["Roughness"].default_value = rough


def stone(name, base="#8E877C", warm="#9C8A70", edge="#D2CBBE", crack="#3A3631", moss="#4A5A33", rough=0.9):
    """Hewn sandstone blocks: every block its own shade, warm and cool patches, mineral grain, hairline
    cracks, pale chipped edges, dirt in the joints and towards the ground, a little moss on top."""
    m = kit.material(name, base, rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    co = N.co
    warped = N.warp(co, 1.2, 0.3)
    big = N.noise(co, 0.5, 3.0)
    warmth = N.math('ADD', N.ramp(big, 0.42, 0.64), N.math('MULTIPLY_ADD', N.island(), 0.8, -0.35))
    col = N.mix(N.math('MULTIPLY', N.math('MINIMUM', N.math('MAXIMUM', warmth, 0.0), 1.0), 0.75), base, warm)
    cells = N.voronoi(warped, 3.0)
    bw = N.new("ShaderNodeRGBToBW")
    N.link(cells.outputs["Color"], bw.inputs[0])
    g1 = N.math('MULTIPLY_ADD', bw.outputs[0], 0.2, 0.88)
    g2 = N.math('MULTIPLY_ADD', N.noise(co, 14.0, 6.0, 0.62), 0.36, 0.82)
    tone = N.math('MULTIPLY_ADD', N.island(), 0.3, 0.84)
    col = N.value(col, N.mul(g1, g2, tone))
    cr = N.voronoi(warped, 1.0, 'DISTANCE_TO_EDGE')
    line = N.ramp(cr.outputs["Distance"], 0.0, 0.03, 1.0, 0.0)
    where = N.ramp(N.noise(co, 1.3, 3.0), 0.56, 0.63)
    col = N.mix(N.mul(line, where, 0.5), col, crack)
    col = N.mix(N.math('MULTIPLY', N.cavity(0.3, 0.97, 0.5), 0.75), col, "#2C2620")
    worn = N.ramp(N.noise(co, 5.0, 4.0, 0.65), 0.32, 0.6, 0.3, 1.0)
    col = N.mix(N.mul(N.edge(0.05, 0.998, 0.9), worn, 0.8), col, edge)
    col = N.mix(N.mul(N.height(0.0, 0.45), N.ramp(N.noise(co, 2.0, 3.0), 0.35, 0.62, 0.35, 1.0), 0.6), col, "#5A4E40")
    patch = N.ramp(N.noise(co, 1.4, 4.0, 0.6), 0.55, 0.62)
    col = N.mix(N.mul(N.up(0.5, 0.85), patch, 0.65), col, N.value(moss, N.math('MULTIPLY_ADD', N.noise(co, 20.0, 3.0), 0.6, 0.7)))
    N.out(col, rough)
    return m


def metal(name, base, edge="#A9AFB5", grime="#121314", vary=0.3, streak=0.28, mottle=0.16, wear=1.0, edge_r=0.05,
          scratch=0.5, dust=0.35, rough=0.6, warm="#4E3E30", warm_amount=0.3, rain=0.3, chips=0.0, bare="#8C939A"):
    """Weathered riveted iron (from the driller)."""
    m = kit.material(name, base, rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    grain = N.noise(N.stretched((30.0, 30.0, 1.4)), 1.0, 3.0, 0.55)
    tone = N.math('MULTIPLY_ADD', N.island(), vary, 1.0 - vary / 2)
    blotch = N.noise(N.co, 1.6, 4.0, 0.6)
    v = N.mul(N.math('MULTIPLY_ADD', grain, 2 * streak, 1.0 - streak), N.math('MULTIPLY_ADD', blotch, 2 * mottle, 1.0 - mottle))
    if rain:
        v = N.math('MULTIPLY', v, N.ramp(N.noise(N.stretched((16.0, 16.0, 0.8)), 1.0, 3.0, 0.6), 0.5, 0.72, 1.0, 1.0 - rain))
    col = N.value(N.mix(N.math('MULTIPLY', N.ramp(N.noise(N.co, 0.9, 3.0), 0.48, 0.68), warm_amount), base, warm),
                  N.math('MULTIPLY', v, tone))
    if chips:
        flake = N.noise(N.co, 4.5, 6.0, 0.7)
        lost = N.ramp(N.math('ADD', flake, N.math('MULTIPLY', N.edge(0.12, 0.999, 0.85), 0.3)), 0.7, 0.73)
        col = N.mix(N.math('MULTIPLY', lost, chips), col, N.value(bare, N.math('MULTIPLY_ADD', grain, 0.4, 0.8)))
    col = N.mix(N.math('MULTIPLY', N.cavity(0.3, 0.97, 0.5), 0.9), col, grime)
    if dust:
        col = N.mix(N.math('MULTIPLY', N.height(0.0, 1.4), dust), col, "#5E5649")
    worn = N.ramp(N.noise(N.co, 5.0, 4.0, 0.65), 0.3, 0.55, 0.45, 1.0)
    col = N.mix(N.mul(N.edge(edge_r, 0.998, 0.9), worn, wear), col, edge)
    if scratch:
        col = N.mix(N.scratches(scratch), col, edge)
    N.out(col, rough)
    return m


def brass(name, base="#9C7531", hi="#EBD08A", tarnish="#4E3A1C", patina="#4C8B78", patina_amount=0.45, rough=0.45):
    """Old brass (from the driller): brushed, tarnished, teal patina in the joints, bright handled edges."""
    m = kit.material(name, base, rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    grain = N.noise(N.stretched((30.0, 30.0, 1.6)), 1.0, 3.0, 0.55)
    col = N.value(base, N.mul(N.math('MULTIPLY_ADD', grain, 0.36, 0.82), N.math('MULTIPLY_ADD', N.island(), 0.2, 0.9)))
    col = N.mix(N.ramp(N.noise(N.co, 2.2, 4.0, 0.6), 0.42, 0.68, 0.0, 0.7), col, tarnish)
    f = N.facing(LIGHT, true=False)
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.55, 0.95), 0.45), col, "#E9C977")
    pat = N.math('MULTIPLY', N.math('MAXIMUM', N.cavity(0.2, 0.97, 0.6), N.ramp(N.noise(N.co, 4.0, 4.0), 0.62, 0.72)), patina_amount)
    col = N.mix(pat, col, patina)
    col = N.mix(N.math('MULTIPLY', N.edge(0.03, 0.998, 0.92), 0.9), col, hi)
    N.out(col, rough)
    return m


def paint(name, base, bare="#9AA1A8", grime="#140F0B", vary=0.2, chips=1.0, chip_scale=5.0, edge_chip=0.32,
          fade=0.3, rain=0.3, dust=0.4, top_dust=0.3, scratch=0.4, rough=0.6):
    """Worn industrial enamel over steel (from the driller): faded patches, streaks, chips back to bare
    steel along the edges with dark rims, grime in the joints, dust on top."""
    m = kit.material(name, base, rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    grain = N.noise(N.stretched((30.0, 1.4, 30.0)), 1.0, 3.0, 0.55)
    tone = N.math('MULTIPLY_ADD', N.island(), vary, 1.0 - vary / 2)
    col = N.value(base, N.mul(N.math('MULTIPLY_ADD', N.noise(N.co, 1.4, 4.0, 0.6), 0.28, 0.86), tone))
    if fade:
        col = N.mix(N.ramp(N.noise(N.co, 1.9, 3.0, 0.55), 0.5, 0.68, 0.0, fade), col, N.mix(0.4, N.value(col, 1.2), "#B5AC94"))
    if rain:
        col = N.mix(N.ramp(N.noise(N.stretched((5.0, 5.0, 0.6)), 1.0, 2.0, 0.5), 0.54, 0.7, 0.0, rain), col, "#3B2E20")
    if chips:
        flake = N.noise(N.co, chip_scale, 3.0, 0.55)
        zone = N.math('MULTIPLY_ADD', N.noise(N.co, 1.1, 2.0, 0.5), 0.3, -0.15)
        s = N.math('ADD', N.math('ADD', flake, zone), N.math('MULTIPLY', N.edge(0.07, 0.999, 0.86), edge_chip))
        col = N.mix(N.math('MULTIPLY', N.ramp(s, 0.664, 0.669, smooth=False), chips), col, "#2A2017")
        col = N.mix(N.math('MULTIPLY', N.ramp(s, 0.674, 0.679, smooth=False), chips), col,
                    N.value(bare, N.math('MULTIPLY_ADD', grain, 0.45, 0.75)))
    col = N.mix(N.math('MULTIPLY', N.cavity(0.3, 0.97, 0.5), 0.9), col, grime)
    if dust:
        col = N.mix(N.math('MULTIPLY', N.height(0.0, 1.4), dust), col, "#6A5E4C")
    if top_dust:
        settle = N.math('MULTIPLY', N.up(0.35, 0.85), N.ramp(N.noise(N.co, 3.2, 4.0, 0.6), 0.4, 0.62, 0.2, 1.0))
        col = N.mix(N.math('MULTIPLY', settle, top_dust), col, "#8A8270")
    worn = N.math('MULTIPLY', N.edge(0.03, 0.998, 0.93), N.ramp(N.noise(N.co, 5.0, 4.0, 0.65), 0.4, 0.6, 0.0, 1.0))
    col = N.mix(N.ramp(worn, 0.4, 0.46, smooth=False), col, "#C6CBCF")
    if scratch:
        col = N.mix(N.scratches(scratch), col, "#B9BEC2")
    N.out(col, rough)
    return m


def hazard(name, width=0.16, axis=(0.62, 0.48, 0.62)):
    """Hazard stripes (from the driller), chipped and worn back to steel at the edges."""
    m = kit.material(name, "#E0AA1C", rough=0.62)
    m["rgh"] = 0.62
    N = Nodes(m)
    d = N.new("ShaderNodeVectorMath")
    d.operation = 'DOT_PRODUCT'
    N.link(N.co, d.inputs[0])
    d.inputs[1].default_value = axis
    stripe = N.math('GREATER_THAN', N.math('FRACT', N.math('MULTIPLY', d.outputs["Value"], 1.0 / (2 * width))), 0.5)
    yellow = N.value("#D9A51E", N.math('MULTIPLY_ADD', N.noise(N.co, 3.0, 4.0), 0.3, 0.85))
    col = N.mix(stripe, yellow, "#1C1B1A")
    chips = N.ramp(N.noise(N.co, 9.0, 5.0, 0.6), 0.64, 0.67)
    worn = N.ramp(N.noise(N.co, 6.0, 4.0, 0.65), 0.3, 0.55, 0.4, 1.0)
    col = N.mix(N.math('MAXIMUM', chips, N.math('MULTIPLY', N.edge(0.05, 0.998, 0.9), worn)), col, "#8E949A")
    col = N.mix(N.scratches(0.6), col, "#9EA4AA")
    col = N.mix(N.math('MULTIPLY', N.cavity(), 0.8), col, "#17171A")
    N.out(col, 0.62)
    return m


def velvet(name, base="#6E2233", rough=0.95):
    """Plum velvet: a soft nap, paler where it turns from the eye and on the plump tops, deep in the seams."""
    m = kit.material(name, base, rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    nap = N.noise(N.co, 40.0, 3.0, 0.6)
    col = N.value(base, N.mul(N.math('MULTIPLY_ADD', nap, 0.25, 0.88), N.math('MULTIPLY_ADD', N.noise(N.co, 3.0, 3.0), 0.3, 0.85)))
    col = N.mix(N.math('MULTIPLY', N.up(0.3, 0.9), 0.3), col, "#A2475A")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.15, 0.97, 0.6), 0.85), col, "#2A0B12")
    N.out(col, rough)
    return m


def dial(name):
    """A gauge face: aged cream enamel, black ticks round the rim, a red zone at the top end, using the
    face's own coordinates "lx", "ly" (-1 to 1)."""
    m = kit.material(name, "#E8DDC0", rough=0.5)
    m["rgh"] = 0.4
    N = Nodes(m)
    x, y = N.attr("lx"), N.attr("ly")
    rad = N.math('SQRT', N.math('ADD', N.math('MULTIPLY', x, x), N.math('MULTIPLY', y, y)))
    ang = N.new("ShaderNodeMath")
    ang.operation = 'ARCTAN2'
    N.link(y, ang.inputs[0])
    N.link(x, ang.inputs[1])
    a = ang.outputs[0]                                         # -pi..pi, 0 to the right, pi/2 up
    sweep_ok = N.ramp(N.math('ABSOLUTE', N.math('SUBTRACT', a, -1.5708)), 0.75, 0.7, 0.0, 1.0, smooth=False)  # no ticks at the bottom
    ticks = N.ramp(N.math('ABSOLUTE', N.math('SUBTRACT', N.math('FRACT', N.math('MULTIPLY', a, 20.0 / TAU)), 0.5)), 0.42, 0.45, 0.0, 1.0, smooth=False)
    ring = N.mul(N.ramp(rad, 0.66, 0.68, 0.0, 1.0, smooth=False), N.ramp(rad, 0.86, 0.84, 0.0, 1.0, smooth=False))
    col = N.value("#E9DEC2", N.math('MULTIPLY_ADD', N.noise(N.co, 18.0, 3.0), 0.16, 0.9))
    col = N.mix(N.math('MULTIPLY', N.ramp(rad, 0.5, 1.0), 0.35), col, "#B49C6E")
    red = N.mul(N.ramp(a, 0.2, 0.25, 0.0, 1.0, smooth=False), N.ramp(a, 1.2, 1.15, 0.0, 1.0, smooth=False),
                N.ramp(rad, 0.7, 0.72, 0.0, 1.0, smooth=False), N.ramp(rad, 0.84, 0.82, 0.0, 1.0, smooth=False))
    col = N.mix(N.mul(red, sweep_ok), col, "#B3261E")
    col = N.mix(N.mul(ring, ticks, sweep_ok), col, "#1E1A16")
    col = N.mix(N.mul(N.ramp(rad, 0.74, 0.76, 0.0, 1.0, smooth=False), N.ramp(rad, 0.78, 0.76, 0.0, 1.0, smooth=False), sweep_ok), col, "#1E1A16")
    col = N.mix(N.ramp(rad, 0.16, 0.13, 0.0, 1.0, smooth=False), col, "#2A2420")
    N.out(col, 0.4)
    return m


def gem(name, stops, edge, inner, rough=0.3):
    """A crystal (from the ore rocks): dark foot, clear body, pale tip, each facet shaded by its facing."""
    m = kit.material(name, stops[2][1], rough=rough)
    m["rgh"] = rough
    N = Nodes(m)
    col = N.colours(N.attr("g"), stops)
    f = N.facing(LIGHT)
    col = N.value(col, N.math('MULTIPLY_ADD', f, 0.38, 1.0))
    col = N.mix(N.math('MULTIPLY', N.ramp(f, 0.55, 0.95), 0.5), col, inner)
    col = N.mix(N.math('MULTIPLY', N.edge(0.02, 0.995, 0.9), 0.55), col, edge)
    N.out(col, rough)
    return m


def glass_material(name):
    """Plain glass for the game (Principled, pale, a little see-through); for the renders a clear
    shell that lets light and shadow through, with a fresnel sheen and a faint tint."""
    m = kit.material(name, "#CFE8EC", rough=0.08)
    b = kit.principled(m)
    b.inputs["Alpha"].default_value = 0.35
    t = m.node_tree
    out = next(n for n in t.nodes if n.type == 'OUTPUT_MATERIAL')
    clear = t.nodes.new("ShaderNodeBsdfTransparent")
    clear.inputs[0].default_value = (*kit.srgb("#EEF7F6"), 1.0)
    gloss = t.nodes.new("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.04
    lw = t.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.22
    mixer = t.nodes.new("ShaderNodeMixShader")
    rng = t.nodes.new("ShaderNodeMapRange")
    rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.06, 0.75
    t.links.new(lw.outputs["Fresnel"], rng.inputs["Value"])
    t.links.new(rng.outputs["Result"], mixer.inputs[0])
    t.links.new(clear.outputs[0], mixer.inputs[1])
    t.links.new(gloss.outputs[0], mixer.inputs[2])
    m["render_out"] = mixer.name
    t.links.new(mixer.outputs[0], out.inputs[0])
    return m


def glass_for(m, render=True):
    t = m.node_tree
    out = next(n for n in t.nodes if n.type == 'OUTPUT_MATERIAL')
    src = t.nodes[m["render_out"]] if render else kit.principled(m)
    t.links.new(src.outputs[0], out.inputs[0])


# ---- the hatchery ---------------------------------------------------------------------------------------

def build():
    rock = stone("Stone")
    floor = stone("Flagstone", base="#7E786F", warm="#8A7A66")
    iron = metal("Iron", "#3A3835", edge="#9A958E", warm="#5A3A22", warm_amount=0.45)
    dark = metal("DarkIron", "#24272B", edge="#868C93", vary=0.25, rain=0.2)
    brs = brass("Brass")
    yellow = paint("Paint", "#DE9C22")
    haz = hazard("Hazard")
    haz_rim = hazard("HazardRim", width=0.13, axis=(0.7, 0.0, 0.7))
    cushion = velvet("Velvet")
    face = dial("Dial")
    knob = paint("KnobRed", "#A3241C", chips=0.6, fade=0.1, rain=0.0, dust=0.0, top_dust=0.0)
    teal = gem("Crystal", [(0.0, "#052A2A"), (0.35, "#0D6461"), (0.75, "#22B3A4"), (1.0, "#B6FFF2")], "#D8FFF8", "#5FF2DC")
    glow = kit.material("GLOW_Hatchery", "#3FF0D6", rough=0.4, emit=6.0)
    glass = glass_material("Hatchery_Glass")

    h = Prop("Hatchery")
    h.tally = {}

    def add(part, bm, mat, at=None, crease=40.0):
        layer(bm, "g")
        lx, ly, rg = layer(bm, "lx"), layer(bm, "ly"), layer(bm, "rgh")
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
            v[rg] = mat.get("rgh", 0.6)
        if crease:
            sharpen(bm, crease)
        h.tally[part] = h.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        h.add(bm, mat)

    def rivets(points, mat=dark, r=0.05):
        for p, n in points:
            add("rivets", rivet(r, r * 0.8), mat, aim(p, n, 15), crease=0)

    # ---- base: two tiers of hewn stone, a stair at the front -------------------------------------------------
    add("base", lathe([(0, 0), (R_LOW - 0.6, 0), (R_LOW - 0.6, Z_TIER - 0.02), (0, Z_TIER - 0.02)], 16), floor, crease=0)
    n_low = 18
    for k in range(n_low):
        a0, a1 = 360.0 * k / n_low + 0.35, 360.0 * (k + 1) / n_low - 0.35
        add("base", wedge(R_LOW - 0.85, R_LOW, a0, a1, 0.0, Z_TIER, segs=2, bevel=0.06, jag=k + 1), rock)
    n_up = 14
    for k in range(n_up):
        a0, a1 = 360.0 * k / n_up + 7 + 0.45, 360.0 * (k + 1) / n_up + 7 - 0.45
        add("base", wedge(R_DRUM - 0.1, R_UP, a0, a1, Z_TIER - 0.02, Z_TOP, segs=3, bevel=0.06, jag=50 + k), rock)
    # the stair: three steps up to the top of the plinth, hazard nosing on the top one
    for j, (y0, z1) in enumerate(((-5.45, 0.34), (-5.05, 0.67), (-4.6, Z_TOP))):
        w = 2.9 - 0.2 * j
        add("stair", block((w, 1.3, z1), bevel=0.05), rock, M((0, y0 + 0.65, z1 / 2)))
    add("stair", block((2.5, 0.16, 0.06), bevel=0.015), haz, M((0, -4.52, Z_TOP + 0.02)))
    add("stair", block((2.5, 0.05, 0.22), bevel=0.012), haz, M((0, -4.62, Z_TOP - 0.09)))

    # ---- the iron drum, brass collar and the floor of the dome --------------------------------------------------
    add("drum", lathe([(0, Z_TOP - 0.1), (R_DRUM, Z_TOP - 0.1), (R_DRUM, Z_DRUM - 0.06), (R_DRUM - 0.06, Z_DRUM), (0, Z_DRUM)], 28), iron)
    add("drum", lathe([(R_DRUM + 0.04, Z_TOP - 0.02), (R_DRUM + 0.1, Z_TOP + 0.04), (R_DRUM + 0.1, Z_TOP + 0.12), (R_DRUM + 0.04, Z_TOP + 0.16),
                       (R_DRUM - 0.1, Z_TOP + 0.16), (R_DRUM - 0.1, Z_TOP - 0.02)], 28), dark)
    add("collar", lathe([(R_GLASS - 0.1, Z_DRUM - 0.02), (R_DRUM - 0.05, Z_DRUM - 0.02), (R_DRUM + 0.02, Z_DRUM + 0.05),
                         (R_DRUM + 0.02, Z_DRUM + 0.16), (R_GLASS + 0.2, Z_COLLAR - 0.06), (R_GLASS + 0.14, Z_COLLAR),
                         (R_GLASS - 0.12, Z_COLLAR), (R_GLASS - 0.12, Z_DRUM - 0.02)], 28), brs)
    add("collar", lathe([(0, Z_COLLAR - 0.12), (R_GLASS - 0.05, Z_COLLAR - 0.12), (R_GLASS - 0.05, Z_COLLAR - 0.04), (0, Z_COLLAR - 0.04)], 24), dark)
    rivets([(polar(th, R_DRUM + 0.012, Z_TOP + 0.33), outward(th)) for th in range(0, 360, 24)], dark, 0.05)
    rivets([(polar(th, R_GLASS + 0.17, Z_COLLAR - 0.03), (outward(th) * 0.5 + UP).normalized()) for th in range(8, 360, 30)], brs, 0.045)
    # rune windows round the drum, the light inside showing through
    for k in range(8):
        th = 22.5 + 45 * k
        if abs(((th - HOPPER_TH + 180) % 360) - 180) < 10:
            continue
        o = outward(th)
        Mw = basis(polar(th, R_DRUM, Z_TOP + 0.3), Vector((0, 0, 1)).cross(o), o)
        add("drum", block((0.5, 0.36, 0.08), bevel=0.02), brs, Mw @ M((0, 0, 0.0)))
        add("runes", block((0.36, 0.22, 0.04), bevel=0.0), glow, Mw @ M((0, 0, 0.035)), crease=0)
        for sx in (-1, 1):
            add("drum", block((0.03, 0.22, 0.03), bevel=0.0), dark, Mw @ M((sx * 0.06, 0, 0.055)))

    # ---- the cradle: a brass bowl, a quilted ring cushion and a pad in the middle ------------------------------
    add("cradle", lathe([(0.0, Z_COLLAR - 0.05), (1.5, Z_COLLAR - 0.05), (1.62, Z_COLLAR + 0.08), (1.66, 2.2), (1.58, 2.28),
                         (1.48, 2.24), (1.4, 2.0), (0.0, 2.0)], 28), brs)
    add("cradle", lathe([(1.52, 2.0), (1.68, 2.18), (1.7, 2.25), (1.6, 2.32), (1.48, 2.28)], 28, close=False), dark, M((0, 0, 0.0)))
    add("cushion", torus(1.02, 0.4, nu=24, nv=10, pinch=0.16, lobes=8), cushion, M((0, 0, 2.1)), crease=0)
    add("cushion", lathe([(0, EGG_SPOT.z), (0.45, EGG_SPOT.z - 0.02), (0.7, EGG_SPOT.z - 0.1), (0.75, 1.95), (0, 1.95)], 16), cushion, crease=0)
    for k in range(8):
        th = 22.5 + 45 * k
        add("cushion", kit.ball((0.09, 0.09, 0.06), cuts=1), brs, M(polar(th, 1.02, 2.1 + 0.36)), crease=0)

    # ---- the glass bell dome ----------------------------------------------------------------------------------
    prof_out, prof_in = [], []
    for z in (Z_COLLAR - 0.08, Z_WALL):
        prof_out.append((R_GLASS, z))
    for k in range(1, 9):
        a = (math.pi / 2) * k / 9
        prof_out.append((R_GLASS * math.cos(a), Z_WALL + R_GLASS * math.sin(a)))
    prof_out.append((0.0, Z_WALL + R_GLASS))
    ri = R_GLASS - GLASS_T
    prof_in = [(0.0, Z_WALL + ri)] + [(ri * math.cos((math.pi / 2) * k / 9), Z_WALL + ri * math.sin((math.pi / 2) * k / 9)) for k in range(8, 0, -1)]
    prof_in += [(ri, z) for z in (Z_WALL, Z_COLLAR - 0.08)]
    add("glass", orient(lathe(prof_out, 28, close=False), 1), glass, crease=0)
    add("glass", orient(lathe(prof_in, 28, close=False), -1), glass, crease=0)

    # four riveted iron straps over the dome, on the diagonals, meeting under a brass crown
    for th in PYLON_TH:
        o = outward(th)
        pts, nrs = [], []
        for z in (Z_COLLAR - 0.02, 2.6, 3.4, 4.1, Z_WALL):
            pts.append(o * (R_GLASS + 0.005) + UP * z)
            nrs.append(o.copy())
        for k in range(1, 10):
            a = math.radians(74.0) * k / 9
            n = o * math.cos(a) + UP * math.sin(a)
            pts.append(UP * Z_WALL + n * (R_GLASS + 0.005))
            nrs.append(n)
        add("frame", sweep(pts, nrs, 0.2, 0.07), iron, crease=35)
        rp = [(UP * z + o * (R_GLASS + 0.075), o) for z in (2.4, 3.5)]
        for a in (24, 55):
            n = o * math.cos(math.radians(a)) + UP * math.sin(math.radians(a))
            rp.append((UP * Z_WALL + n * (R_GLASS + 0.075), n))
        rivets(rp, dark, 0.04)
    add("frame", lathe([(R_GLASS - 0.01, Z_WALL - 0.1), (R_GLASS + 0.09, Z_WALL - 0.1), (R_GLASS + 0.12, Z_WALL - 0.06), (R_GLASS + 0.12, Z_WALL + 0.06),
                        (R_GLASS + 0.09, Z_WALL + 0.1), (R_GLASS - 0.01, Z_WALL + 0.1)], 32, close=False), brs, crease=35)
    rivets([(polar(th, R_GLASS + 0.12, Z_WALL), outward(th)) for th in range(0, 360, 30) if th % 90], brs, 0.04)
    ztop = Z_WALL + R_GLASS
    add("crown", lathe([(0, ztop - 0.25), (0.62, ztop - 0.25), (0.78, ztop - 0.12), (0.72, ztop + 0.02), (0.5, ztop + 0.12),
                        (0.3, ztop + 0.14), (0, ztop + 0.14)], 20), brs)
    add("crown", cylinder(0.24, 0.36, segs=12, bevel=0.03), dark, M((0, 0, ztop + 0.3)))
    add("crown", cylinder(0.32, 0.08, segs=12, bevel=0.02), brs, M((0, 0, ztop + 0.5)))
    add("crown", lathe([(0, ztop + 0.54), (0.2, ztop + 0.54), (0.2, ztop + 0.6), (0.06, ztop + 0.72), (0, ztop + 0.72)], 10), dark)
    rivets([(polar(th, 0.58, ztop - 0.02), (outward(th) + UP).normalized()) for th in range(0, 360, 45)], dark, 0.04)
    add("runes", cylinder(0.245, 0.06, segs=12, bevel=0.0), glow, M((0, 0, ztop + 0.38)), crease=0)

    # ---- four crystal pylons on the diagonals -----------------------------------------------------------------
    rnd = random.Random(5)
    for i, th in enumerate(PYLON_TH):
        c = polar(th, PYLON_R)
        o = outward(th)
        R = basis(c, Vector((0, 0, 1)).cross(o), UP)
        add("pylons", block((0.95, 0.95, 0.42), bevel=0.06, top=(0.88, 0.88)), dark, R @ M((0, 0, Z_TOP + 0.21)))
        add("pylons", block((0.8, 0.8, 0.12), bevel=0.03), yellow, R @ M((0, 0, Z_TOP + 0.47)))
        col_h = 4.35 - (Z_TOP + 0.53)
        add("pylons", block((0.62, 0.62, col_h), bevel=0.05, top=(0.78, 0.78)), iron, R @ M((0, 0, Z_TOP + 0.53 + col_h / 2)))
        add("pylons", block((0.66, 0.66, 0.34), bevel=0.04, top=(0.97, 0.97)), yellow, R @ M((0, 0, 2.55)))
        for z, w in ((1.75, 0.7), (3.35, 0.62), (4.3, 0.6)):
            add("pylons", block((w, w, 0.14), bevel=0.03), brs, R @ M((0, 0, z)))
        rivets([(R @ Vector((sx * 0.33, sy * 0.33, 2.55)), (R.to_3x3() @ Vector((sx, sy, 0))).normalized())
                for sx, sy in ((-1, 0), (1, 0), (0, -1), (0, 1))], brs, 0.045)
        # the claw cup holding the crystal
        add("pylons", lathe([(0.0, 4.36), (0.34, 4.36), (0.48, 4.6), (0.44, 4.7), (0.28, 4.64), (0.0, 4.64)], 10), brs, R)
        for k in range(4):
            a = TAU * k / 4 + 0.785
            d = Vector((math.cos(a), math.sin(a), 0))
            pts = [d * 0.4 + UP * 4.6, d * 0.52 + UP * 5.0, d * 0.4 + UP * 5.42]
            add("pylons", kit.tube(pts, [0.07, 0.06, 0.03], segs=5, rings=4), brs, R, crease=0)
        tip = R @ Vector((0, 0, 4.58))
        for k, (ln, rad, lean, turn) in enumerate(((2.0, 0.36, 0.0, 0), (1.1, 0.22, 24.0, 40 + 90 * i), (0.9, 0.18, 28.0, 200 + 90 * i))):
            ax = Vector((0, 0, 1))
            if lean:
                ax = (Matrix.Rotation(math.radians(turn), 3, 'Z') @ Matrix.Rotation(math.radians(lean), 3, 'X') @ ax).normalized()
            off = Vector((0, 0, 0)) if k == 0 else (Matrix.Rotation(math.radians(turn), 3, 'Z') @ Vector((0, -0.16, 0)))
            at = aim(tip + off, ax, rnd.uniform(0, 60))
            facets, core = lit_crystal(ln, rad, seed=30 + 7 * i + k)
            add("crystals", facets, teal, at, crease=0)
            add("crystal cores", core, glow, at, crease=0)
        # a conduit from the pylon down into the drum, glowing between brass sleeves
        a0 = c - o * 0.28 + UP * 3.15
        a1 = c - o * 0.72 + UP * 2.35
        a2 = polar(th, R_DRUM + 0.3, Z_TOP + 0.38)
        a3 = polar(th, R_DRUM - 0.05, Z_TOP + 0.3)
        path = [a0, a1, a2, a3]
        pipe = kit.tube(path, [0.11] * 4, segs=6, rings=10)
        tl = pipe.faces.layers.float["t"]
        lit, metal_part = kit.split(pipe, lambda f: any(lo < f[tl] < hi for lo, hi in ((0.18, 0.38), (0.5, 0.72))))
        add("conduits", lit, glow, crease=0)
        add("conduits", metal_part, brs, crease=0)
        for t_ in (0.18, 0.38, 0.5, 0.72):
            k_ = t_ * 3
            p = kit._spline(path, k_)
            d = (kit._spline(path, min(k_ + 0.05, 3)) - kit._spline(path, max(k_ - 0.05, 0))).normalized()
            add("conduits", cylinder(0.15, 0.08, segs=6, bevel=0.0), dark, aim(p, d))
        add("conduits", cylinder(0.17, 0.2, segs=6, bevel=0.03), brs, aim(a3 + o * 0.12, o))

    # ---- rune glyphs inlaid in the top of the plinth --------------------------------------------------------
    grnd = random.Random(9)
    for th in range(24, 360, 13):
        bad = [(-26, 26), (CONSOLE_TH - 24, CONSOLE_TH + 24), (HOPPER_TH - 22, HOPPER_TH + 22)]
        tt = ((th + 180) % 360) - 180
        if any(lo <= (tt if lo < 0 else th) <= hi for lo, hi in bad):
            continue
        if min(abs(((th - p + 180) % 360) - 180) for p in PYLON_TH) < 11:
            continue
        o = outward(th)
        G = basis(polar(th, 3.45, Z_TOP + 0.005), o, UP)
        strokes = [((0, 0), 0.44, 0)]
        for _ in range(grnd.randint(1, 2)):
            strokes.append(((grnd.choice((-0.1, 0.1)), grnd.uniform(-0.12, 0.12)), grnd.uniform(0.18, 0.28), grnd.choice((40, -40, 90))))
        for (x, y), ln, rot in strokes:
            add("runes", block((ln, 0.07, 0.03), bevel=0.0), glow, G @ M((x, y, 0.0), rot=(0, 0, 90 + rot)), crease=0)

    # ---- the control desk on the left: gauges and a big lever --------------------------------------------------
    cth = CONSOLE_TH + 20
    o = outward(cth)
    side = Vector((0, 0, 1)).cross(o)               # along the desk, towards the front
    C = basis(polar(cth, 3.5, Z_TOP), side, UP)     # x along the desk, y in towards the dome... (y = UP x side)
    # in C: +x runs along the desk, -y faces out (o), z up
    def at_c(x, y, z, rot=(0, 0, 0)):
        return C @ M((x, y, z), rot=rot)
    add("desk", block((2.1, 1.0, 1.45), bevel=0.06), yellow, at_c(0, 0.05, 0.725))
    add("desk", block((2.2, 1.1, 0.14), bevel=0.03), dark, at_c(0, 0.05, 0.07))
    for x in (-0.55, 0.55):
        add("desk", block((0.05, 0.05, 0.9), bevel=0.0), dark, at_c(x, -0.46, 0.75))
    # a slanted iron panel on top, facing out and up
    P = at_c(0, -0.1, 1.5, rot=(-40, 0, 0))
    add("desk", block((2.15, 1.15, 0.14), bevel=0.04), dark, P)
    for k, (x, r) in enumerate(((-0.52, 0.36), (0.36, 0.36), (0.88, 0.18))):
        G = P @ M((x, 0.04 if k < 2 else -0.2, 0.07))
        add("gauges", lathe([(0, 0), (r + 0.05, 0), (r + 0.06, 0.06), (r + 0.02, 0.1), (r - 0.02, 0.06), (r - 0.02, 0.03), (0, 0.03)], 14), brs, G)
        f = lathe([(0, 0.035), (r - 0.02, 0.035)], 14, close=False)
        lx, ly = layer(f, "lx"), layer(f, "ly")
        for v in f.verts:
            v[lx], v[ly] = v.co.x / (r - 0.02), v.co.y / (r - 0.02)
        f.faces.ensure_lookup_table()
        add("gauges", f, face, G, crease=0)
        ang = (-40, 25, 70)[k]
        add("gauges", block((0.022, r * 0.75, 0.015), bevel=0.0), dark, G @ M((0, 0, 0.05), rot=(0, 0, ang)) @ M((0, r * 0.3, 0)))
        add("gauges", cylinder(0.035, 0.03, segs=6, bevel=0.0), brs, G @ M((0, 0, 0.055)))
    rivets([(P @ Vector((sx * 1.0, sy * 0.5, 0.07)), (P.to_3x3() @ Vector((0, 0, 1))).normalized()) for sx in (-1, 1) for sy in (-1, 1)], brs, 0.04)
    # a pipe from the desk into the drum
    p0 = C @ Vector((-0.5, 0.5, 0.4))
    p1 = polar(CONSOLE_TH + 4, R_DRUM - 0.05, Z_TOP + 0.3)
    add("desk", kit.tube([p0, p0.lerp(p1, 0.5) + UP * 0.05, p1], [0.07] * 3, segs=8, rings=6), brs, crease=0)
    # the lever, on the front end of the desk: a quadrant plate, a slotted guide and a long handle
    L = at_c(1.05, 0.05, 0.85)                        # the front face of the desk (+x end)
    LF = L @ M(rot=(0, 90, 0))                       # z points out of the front end
    add("lever", cylinder(0.4, 0.08, segs=12, bevel=0.02), dark, LF @ M((0, 0, 0.04)))
    add("lever", cylinder(0.15, 0.16, segs=10, bevel=0.025), brs, LF @ M((0, 0, 0.14)))
    knob_dir = (C.to_3x3() @ Vector((0.45, -0.2, 1.0))).normalized()
    pivot = L @ Vector((0.22, 0, 0))
    add("lever", kit.tube([pivot, pivot + knob_dir * 1.35], [0.065, 0.05], segs=6, rings=2), iron, crease=0)
    add("lever", kit.ball((0.34, 0.34, 0.34), cuts=2), knob, M(pivot + knob_dir * 1.48), crease=0)

    # ---- the egg hopper at the back, with a chute into the drum --------------------------------------------
    hc = polar(HOPPER_TH, 3.6)
    o = outward(HOPPER_TH)
    Hm = basis(hc, Vector((0, 0, 1)).cross(o), UP)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("hopper", block((0.16, 0.16, 2.5), bevel=0.03), dark, Hm @ M((sx * 0.62, sy * 0.45, Z_TOP + 1.25)))
    for z in (Z_TOP + 0.9,):
        add("hopper", block((1.4, 0.07, 0.1), bevel=0.02), dark, Hm @ M((0, -0.45, z)))
        add("hopper", block((1.4, 0.07, 0.1), bevel=0.02), dark, Hm @ M((0, 0.45, z)))
    zb, zt = 3.3, 4.65
    fun = bmesh.new()
    outer_lo, outer_hi, inner_hi, inner_lo = [], [], [], []
    for (x, y) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        outer_lo.append(fun.verts.new((x * 0.42, y * 0.36, zb)))
        outer_hi.append(fun.verts.new((x * 1.0, y * 0.85, zt)))
        inner_hi.append(fun.verts.new((x * 0.9, y * 0.75, zt)))
        inner_lo.append(fun.verts.new((x * 0.3, y * 0.24, zb + 0.15)))
    for ring_a, ring_b in ((outer_lo, outer_hi), (outer_hi, inner_hi), (inner_hi, inner_lo)):
        for j in range(4):
            k = (j + 1) % 4
            fun.faces.new((ring_a[j], ring_a[k], ring_b[k], ring_b[j]))
    fun.faces.new(outer_lo[::-1])
    fun.faces.new(inner_lo)
    bmesh.ops.recalc_face_normals(fun, faces=fun.faces[:])
    chamfer(fun, 0.03, 30.0)
    add("hopper", fun, yellow, Hm)
    rim = bmesh.new()
    lo_r, hi_r, hi_i, lo_i = [], [], [], []
    for (x, y) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lo_r.append(rim.verts.new((x * 0.97, y * 0.82, zt - 0.28)))
        hi_r.append(rim.verts.new((x * 1.04, y * 0.89, zt + 0.02)))
        hi_i.append(rim.verts.new((x * 0.92, y * 0.77, zt + 0.02)))
        lo_i.append(rim.verts.new((x * 0.87, y * 0.72, zt - 0.28)))
    for ring_a, ring_b in ((lo_r, hi_r), (hi_r, hi_i), (hi_i, lo_i), (lo_i, lo_r)):
        for j in range(4):
            k = (j + 1) % 4
            rim.faces.new((ring_a[j], ring_a[k], ring_b[k], ring_b[j]))
    bmesh.ops.recalc_face_normals(rim, faces=rim.faces[:])
    add("hopper", rim, haz_rim, Hm)
    rivets([(Hm @ Vector((x * 0.7, -0.62, (zb + zt) / 2 + 0.1)), (Hm.to_3x3() @ Vector((0, -0.9, 0.45))).normalized()) for x in (-1, 0, 1)], dark, 0.045)
    # the chute: a square iron trough from the hopper's mouth down into the drum under the dome
    c0 = Hm @ Vector((0, 0, zb - 0.1))
    c1 = polar(HOPPER_TH, R_DRUM + 0.05, Z_DRUM - 0.12)
    d = (c1 - c0)
    add("hopper", block((0.62, 0.62, d.length + 0.2), bevel=0.04), iron, basis((c0 + c1) / 2, Vector((1, 0, 0)), d))
    add("hopper", block((0.74, 0.74, 0.12), bevel=0.03), brs, basis(c0 + d.normalized() * 0.15, Vector((1, 0, 0)), d))
    add("hopper", block((0.74, 0.74, 0.12), bevel=0.03), brs, basis(c1 - d.normalized() * 0.3, Vector((1, 0, 0)), d))

    cut = cull_hidden(h.parts)
    print("  hidden faces removed: %d triangles" % cut, flush=True)
    h.build()
    egg = bpy.data.objects.new("Hatchery_EggSpot", None)
    egg.empty_display_type, egg.empty_display_size = 'SINGLE_ARROW', 0.6
    egg.location = EGG_SPOT
    bpy.context.scene.collection.objects.link(egg)
    h.egg_spot = egg
    return h


# ---- baking, export, numbers ----------------------------------------------------------------------------

def bake_rough(ob, texture, size):
    """A roughness image from the "rgh" value each part carries, with a faint mottle (from the ore rocks)."""
    stem = os.path.splitext(texture)[0]
    stem = stem[:-len("_colour")] if stem.endswith("_colour") else stem
    path = stem + "_rough.png"
    baked = ob.data.materials[0]
    tmp = bpy.data.materials.new("RoughBake")
    N = Nodes(tmp)
    em = N.new("ShaderNodeEmission")
    v = N.math('MULTIPLY_ADD', N.noise(N.co, 6.0, 3.0), 0.12, -0.06)
    N.link(N.math('ADD', N.attr("rgh"), v), em.inputs["Color"])
    out = next(n for n in tmp.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
    N.link(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new(os.path.basename(stem) + "_rough", size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    tex = N.new("ShaderNodeTexImage")
    tex.image = img
    tmp.node_tree.nodes.active = tex
    ob.data.materials[0] = tmp
    bpy.context.scene.cycles.samples = 4
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
    img.name = os.path.basename(stem) + "_rough"
    bpy.data.materials.remove(tmp)


def bake(h, texture, size=1024, samples=32):
    glow = [ob for ob in h.objects if ob.data.materials[0].name.startswith("GLOW_")]
    glass = [ob for ob in h.objects if "Glass" in ob.data.materials[0].name]
    for ob in glass:
        ob.hide_render = True
    body = kit.bake_texture([ob for ob in h.objects if ob not in glow and ob not in glass], texture, size=size, samples=samples,
                            name="Hatchery_Body", shade=0.6, soften=2, rough=0.6, uv_angle=70.0, uv_margin=0.004, pack_margin=0.003)
    bake_rough(body, texture, size)
    for ob in glass:
        ob.hide_render = False
    objs = [body]
    for group, name in ((glow, "Hatchery_GLOW"), (glass, "Hatchery_Glass")):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in group:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = name
        objs.append(g)
    h.objects = objs


def numbers(h, size):
    tris = h.triangles()
    lo, hi = h.bounds()
    me = h.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    return dict(tris=tris, total=sum(tris.values()), size=(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z), low=lo.z,
                used=a2, px_per_stud=(a2 * size * size / a3) ** 0.5)


def export(h, path):
    glass = [ob for ob in h.objects if "Glass" in ob.name]
    for ob in glass:
        glass_for(ob.data.materials[0], render=False)
    kit.export_fbx(h.objects + [h.egg_spot], path)
    for ob in glass:
        glass_for(ob.data.materials[0], render=True)


def review_sheet(h, out, samples=32, px=512, title="Hatchery"):
    """The standard eight views (review.py) into a sheet; the single renders go in a folder beside it,
    which is removed again unless the sheet is in the scratch area."""
    import review
    rig = review.Rig(h, samples=samples, focus=(0.0, 0.0, 3.2))
    rig.cams["close-up"] = review._camera("C_close2", Vector((-2.4, -14.0, 6.6)), Vector((0.0, 0.0, 3.1)), 30)
    c = rig.c
    d = rig.size * 2.7
    rig.cams["side"] = review._camera("C_side_r", c + Vector((1.0, -0.06, 0.1)).normalized() * d, c, 34)   # the hopper side
    shots = review.STANDARD
    rig.sheet(out, shots, px=px, title=title)
    return rig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(MODELS, "preview", "hatchery.png"))
    ap.add_argument("--export", default=os.path.join(MODELS, "export", "hatchery.fbx"))
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--peek", help="quick unbaked look: write the sheet here and stop")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--bake-samples", type=int, default=32)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--title", default="Hatchery")
    a = ap.parse_args()
    kit.fresh()
    h = build()
    print("triangles by part:", dict(sorted(h.tally.items(), key=lambda kv: -kv[1])), flush=True)
    if a.peek:
        lo, hi = h.bounds()
        print("unbaked: %d triangles; %.2f x %.2f x %.2f" % (sum(h.triangles().values()), hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
        review_sheet(h, os.path.abspath(a.peek), samples=12, px=a.px, title=a.title + " (peek, unbaked)")
        return
    texture = os.path.join(os.path.dirname(os.path.abspath(a.export)), "hatchery_colour.png")
    os.makedirs(os.path.dirname(texture), exist_ok=True)
    bake(h, texture, a.size, a.bake_samples)
    st = numbers(h, a.size)
    print("triangles %s total %d; %.2f wide, %.2f deep, %.2f tall studs, lowest z %.3f; texture %.0f%% used, %.0f px per stud"
          % (st["tris"], st["total"], st["size"][0], st["size"][1], st["size"][2], st["low"], st["used"] * 100, st["px_per_stud"]), flush=True)
    print("egg spot: (%.3f, %.3f, %.3f)" % tuple(h.egg_spot.location), flush=True)
    if not a.no_export:
        export(h, os.path.abspath(a.export))
        print("exported", a.export, flush=True)
    if a.sheet:
        out = os.path.abspath(a.sheet)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        review_sheet(h, out, samples=a.samples, px=a.px, title=a.title)
        views = os.path.splitext(out)[0] + "_views"
        if out.startswith(MODELS):
            shutil.rmtree(views, ignore_errors=True)
        print("sheet", out, flush=True)


if __name__ == "__main__":
    main()
