"""Driller pet: a mechanical drill mole, an armoured digging machine. Built from scratch by script.

    python models/pets/driller.py --review out/driller.png      # render the review sheet
    python models/pets/driller.py --export models/export/driller.fbx

Style: the first machine in the set. Rugged industrial mining equipment shaped like a mole or a
badger tank: cool and tough, never a cute toy and never a creepy animal. Must-haves:
  1. A low, heavy armoured body on four short sturdy legs; a big spiral-fluted steel drill cone on
     the nose, forward and a little lowered; two oversized shovel claws of thick steel blades
     planted on the ground in front.
  2. A rounded back of overlapping riveted plates, like an armadillo's banded shell.
  3. A machine face: a painted brow hood over a wide visor light bar (a row of lamp cells, never
     two eyes), a heavy snout housing and a dark collar framing the bright drill.
  4. A furnace glowing through a belly grille and along the flanks, two short exhaust stacks,
     pipes along the flanks, a chain hanging between plates, a few amethyst and sapphire chunks
     stuck in the back plates.
  5. One paint scheme: mining-machine yellow on the armour, gunmetal underneath, brass and copper
     fittings, hazard stripes on the claw backs and the rear bumper only, a polished drill and an
     orange glow.
  6. Not plastic: paint chipped back to bare steel along the edges with a dark rim round each chip,
     grime in the joints, rain streaks, soot, patina and scratches are painted into the baked
     colour; crisp creases and real plate thickness.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

# ---- layout (studs; front is -Y) ---------------------------------------------------------------------
SPRING = 1.5                     # height of the shell's springline
SHELL_Y = (-1.35, 2.42)          # front and back of the banded shell (a dome cap closes the back)
BANDS, BAND_LEN = 6, 0.82
HEAD_AT = Vector((0.0, -1.85, 1.95))
HEAD_ROT = (10, 0, 0)            # nose a little down
DRILL_TILT = 20.0                # the drill points this many degrees below level
HUB = Vector((0.0, -0.45, -0.34))  # the drill's axis leaves the head here (head space)
ENGINE_Y = 1.1                  # the boiler housing on the back, the stacks rising from its rear corners
STACK_TOP = 4.7
SOOT = [Vector((-0.28, 1.4, 3.7)), Vector((0.28, 1.4, 3.7)), Vector((-0.33, 1.9, 4.62)), Vector((0.3, 1.8, 4.35))]


# ---- small helpers ----------------------------------------------------------------------------------

def layer(bm, name):
    return bm.verts.layers.float.get(name) or bm.verts.layers.float.new(name)


def sharpen(bm, degrees):
    """Mark the edges where the surface turns by more than `degrees` as sharp: crisp creases."""
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def sgnpow(x, p):
    return math.copysign(abs(x) ** p, x)


def frame(a, b, xref=(1, 0, 0)):
    """A transform whose Z runs from a to b (centred between them), its X as near `xref` as it can
    be, and the distance from a to b."""
    a, b = Vector(a), Vector(b)
    z = (b - a).normalized()
    x = Vector(xref)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (a + b) / 2
    return m, (b - a).length


def basis(origin, x, z):
    """A right-handed transform at `origin` whose Z is `z` and whose X is as near `x` as it can be."""
    z = Vector(z).normalized()
    x = Vector(x)
    x = (x - z * x.dot(z)).normalized()
    m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def aim(origin, direction, roll=0.0):
    """A transform standing a shape built along +Z on `origin`, pointing along `direction`."""
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


def slice_off(bm, co, no):
    """Cut away everything in front of the plane through `co` facing `no` and close the cut."""
    no = Vector(no).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return bm


def chamfer(bm, width, degrees=30.0, edges=None):
    """A flat 45-degree chamfer of `width` on every edge sharper than `degrees`: a highlight line."""
    if width <= 0:
        return bm
    bm.normal_update()
    lim = math.radians(degrees)
    if edges is None:
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type='OFFSET', segments=1, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    return bm


class Surface:
    """Finds points exactly on a set of shapes, so details sit on them and neither float nor sink."""

    def __init__(self):
        self.verts, self.polys = [], []

    def take(self, bm):
        base = len(self.verts)
        bm.verts.index_update()
        self.verts += [v.co.copy() for v in bm.verts]
        self.polys += [[base + v.index for v in f.verts] for f in bm.faces]

    def done(self):
        self.bvh = BVHTree.FromPolygons(self.verts, self.polys)
        return self

    def hit(self, origin, direction):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc, nrm


def _hemisphere():
    """Ray directions spread over the hemisphere round +Z, out to nearly grazing."""
    out = [Vector((0, 0, 1))]
    for tilt, n in ((25, 6), (50, 9), (72, 12), (86, 14)):
        t = math.radians(tilt)
        for j in range(n):
            a = 2 * math.pi * (j + 0.5 * (tilt // 25 % 2)) / n
            out.append(Vector((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))))
    return out


def cull_hidden(parts, keep=("GLOW",)):
    """Delete the faces no camera can see: tucked under other plates, buried inside another shape or
    flat on the ground. Each face is tried from its centre and near each corner with rays over its
    whole outward hemisphere; it goes only if every ray hits something. That frees triangles and,
    more usefully, texture space for the faces that show. Returns the number of triangles removed."""
    verts, polys = [], []
    for bm, _ in parts.values():
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


# ---- shapes ------------------------------------------------------------------------------------------

def block(size, cuts=(), bevel=0.04, top=(1.0, 1.0), shift=(0.0, 0.0), degrees=30.0):
    """A box `size` centred on the origin, its top scaled by `top` and moved by `shift`, cut by the
    planes `cuts` (point, normal) and chamfered on every sharp edge: a machined steel part."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    sx, sy, sz = (s / 2.0 for s in size)
    for v in bm.verts:
        t = top if v.co.z > 0 else (1.0, 1.0)
        d = shift if v.co.z > 0 else (0.0, 0.0)
        v.co = Vector((v.co.x * sx * t[0] + d[0], v.co.y * sy * t[1] + d[1], v.co.z * sz))
    for co, n in cuts:
        slice_off(bm, co, n)
    return chamfer(bm, bevel, degrees)


def cylinder(r, length, segs=12, bevel=0.03, r2=None):
    """A short cylinder along +Z centred on the origin, its ends chamfered."""
    r2 = r if r2 is None else r2
    h = length / 2
    if bevel <= 0:
        return kit.tube([(0, 0, -h), (0, 0, h)], [r, r2], segs=segs, rings=1)
    pts = [(0, 0, -h), (0, 0, -h + bevel), (0, 0, h - bevel), (0, 0, h)]
    return kit.tube(pts, [r - bevel, r, r2, r2 - bevel], segs=segs, rings=3)


def hollow(r_out, r_in, h, segs=12):
    """An open-topped ring (a pipe end, a stack's mouth) along +Z from 0 to h."""
    bm = bmesh.new()
    rings = []
    for r, z in ((r_out, 0.0), (r_out, h), (r_in, h), (r_in, 0.0)):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z))
                      for j in range(segs)])
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def arch_band(rx_of, rz_of, y0, y1, a0, a1, n=2.6, thick=0.12, cols=18, rows=2, bevel=0.025, ridge=0.0, ridge_w=0.5):
    """One band of the shell: a thick arched plate from y0 to y1 whose cross-section is a
    superellipse from angle a0 to a1 (0 is +X, pi/2 straight up) with half width rx_of(v) and
    height rz_of(v) above the springline, v running 0 to 1 from the front edge to the back edge.
    Returns the shape and a function giving (point, outward normal) at (u, v)."""

    def at(u, v, d=0.0):
        a = a0 + (a1 - a0) * u
        ec, es = sgnpow(math.cos(a), 2.0 / n), sgnpow(math.sin(a), 2.0 / n)
        rx, rz = rx_of(v), rz_of(v)
        nrm = Vector((sgnpow(ec, n - 1) / rx, 0.0, sgnpow(es, n - 1) / rz))
        nrm = nrm.normalized() if nrm.length > 1e-9 else Vector((0, 0, 1))
        crest = ridge * max(0.0, 1.0 - abs(a - math.pi / 2) / ridge_w)
        p = Vector((rx * ec, y0 + (y1 - y0) * v, SPRING + rz * es + crest))
        return p - nrm * d, nrm

    bm = bmesh.new()
    us = [i / cols for i in range(cols + 1)]
    vs = [i / rows for i in range(rows + 1)]
    outer = [[bm.verts.new(at(u, v)[0]) for u in us] for v in vs]
    inner = [[bm.verts.new(at(u, v, thick)[0]) for u in us] for v in vs]
    for i in range(rows):
        for j in range(cols):
            bm.faces.new((outer[i][j], outer[i][j + 1], outer[i + 1][j + 1], outer[i + 1][j]))
            bm.faces.new((inner[i][j], inner[i + 1][j], inner[i + 1][j + 1], inner[i][j + 1]))
    rim = []
    for j in range(cols):
        for i in (0, rows):
            bm.faces.new((outer[i][j], inner[i][j], inner[i][j + 1], outer[i][j + 1]))
            rim.append(bm.edges.get((outer[i][j], outer[i][j + 1])))
    for i in range(rows):
        for j in (0, cols):
            bm.faces.new((outer[i][j], outer[i + 1][j], inner[i + 1][j], inner[i][j]))
            rim.append(bm.edges.get((outer[i][j], outer[i + 1][j])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    chamfer(bm, bevel, edges=[e for e in rim if e])
    return bm, at


def cap_plate(w, l, bulge=(0.08, 0.05), thick=0.1, nu=6, nv=4, bevel=0.025, taper=1.0, corner=0.0):
    """A thick, gently domed rectangular armour plate, outer face up (+Z), `w` across X and `l`
    along Y; `taper` narrows its +Y end. Returns the shape and a function giving (point, normal)
    at (u, v), both -1 to 1."""

    def at(u, v, d=0.0):
        if corner and abs(u) + abs(v) > 2.0 - corner:          # knock the corners off: a shield outline
            f = (2.0 - corner) / (abs(u) + abs(v))
            u, v = u * (f + (1 - f) * (1 - abs(v))), v * (f + (1 - f) * (1 - abs(u)))
        k = 1.0 + (taper - 1.0) * (v + 1) / 2
        x, y = u * w / 2 * k, v * l / 2
        z = bulge[0] * (1 - u * u) + bulge[1] * (1 - v * v)
        nrm = Vector((2 * bulge[0] * u / (w / 2 * k), 2 * bulge[1] * v / (l / 2), 1.0)).normalized()
        return Vector((x, y, z)) - nrm * d, nrm

    bm = bmesh.new()
    us = [-1 + 2 * i / nu for i in range(nu + 1)]
    vs = [-1 + 2 * i / nv for i in range(nv + 1)]
    outer = [[bm.verts.new(at(u, v)[0]) for u in us] for v in vs]
    inner = [[bm.verts.new(at(u, v, thick)[0]) for u in us] for v in vs]
    rim = []
    for i in range(nv):
        for j in range(nu):
            bm.faces.new((outer[i][j], outer[i][j + 1], outer[i + 1][j + 1], outer[i + 1][j]))
            bm.faces.new((inner[i][j], inner[i + 1][j], inner[i + 1][j + 1], inner[i][j + 1]))
    for j in range(nu):
        for i in (0, nv):
            bm.faces.new((outer[i][j], inner[i][j], inner[i][j + 1], outer[i][j + 1]))
            rim.append(bm.edges.get((outer[i][j], outer[i][j + 1])))
    for i in range(nv):
        for j in (0, nu):
            bm.faces.new((outer[i][j], outer[i + 1][j], inner[i + 1][j], inner[i][j]))
            rim.append(bm.edges.get((outer[i][j], outer[i + 1][j])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    chamfer(bm, bevel, edges=[e for e in rim if e])
    return bm, at


def drill_cone(length, radius, flutes=3, per=12, rings=16, turns=1.1):
    """A spiral-fluted drill along +Z from its base (z=0) to its point: each flute a concave scoop
    ending in a sharp cutting ridge that winds round the cone. Vertex layer "grad" is 0 at the base
    and 1 at the tip."""
    bm = bmesh.new()
    lay = layer(bm, "grad")
    spin = layer(bm, "spin")
    segs = flutes * per
    prof = []                                             # a flat polished land, then the scoop of the flute
    for k in range(per):
        if k <= 1:
            prof.append(1.0)
        elif k == 2:
            prof.append(0.975)
        else:
            prof.append(0.94 - 0.3 * ((k - 2) / (per - 2)) ** 0.7)
    loops = []
    for i in range(rings):
        t = i / rings
        env = radius * (1.0 - t) ** 0.92
        twist = turns * 2 * math.pi * t
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs + twist
            r = env * prof[j % per]
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), t * length))
            v[lay] = t
            v[spin] = (j % per) / per
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((a[j], a[k], b[k], b[j]))
    tip = bm.verts.new((0, 0, length))
    tip[lay] = 1.0
    for j in range(segs):
        bm.faces.new((loops[-1][j], loops[-1][(j + 1) % segs], tip))
    bm.faces.new(loops[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def section_loft(points, profile_of, up, rings=None):
    """Sections lofted along a smooth path through `points`; profile_of(t) gives one section as
    (across, up) points going round, `up` fixes which way the section faces. Ends are capped."""
    pts = [Vector(p) for p in points]
    rings = rings or (len(pts) - 1) * 4
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    bm = bmesh.new()
    lay = layer(bm, "grad")
    loops = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        upv = Vector(up)
        side = t.cross(upv).normalized()
        upv = side.cross(t).normalized()
        loops.append([bm.verts.new(p + side * a + upv * b) for a, b in profile_of(i / rings)])
        for v in loops[-1]:
            v[lay] = i / rings
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bm.faces.new(loops[0])
    bm.faces.new(loops[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def blade_profile(w, th):
    """A thick blade section with bevelled cutting edges on both sides."""
    return [(w / 2, 0.0), (w * 0.28, th / 2), (-w * 0.28, th / 2), (-w / 2, 0.0), (-w * 0.28, -th / 2), (w * 0.28, -th / 2)]


def rivet(r=0.05, h=0.04, segs=5):
    """A domed rivet head along +Z, its foot sunk a little below z=0."""
    bm = bmesh.new()
    lo = [bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), -0.02)) for j in range(segs)]
    mid = [bm.verts.new((r * 0.92 * math.cos(2 * math.pi * j / segs), r * 0.92 * math.sin(2 * math.pi * j / segs), h * 0.55)) for j in range(segs)]
    top = bm.verts.new((0, 0, h))
    for j in range(segs):
        k = (j + 1) % segs
        bm.faces.new((lo[j], lo[k], mid[k], mid[j]))
        bm.faces.new((mid[j], mid[k], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def chain_link(length=0.2, width=0.12, wire=0.026, nu=8, nv=3):
    """One oval chain link lying in the XY plane, long along X."""
    bm = bmesh.new()
    rows = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        c = Vector(((length / 2 - width / 2) * math.copysign(1, math.cos(a)) + width / 2 * math.cos(a), width / 2 * math.sin(a), 0))
        out = Vector((math.cos(a), math.sin(a), 0))
        rows.append([bm.verts.new(c + (out * math.cos(b) + Vector((0, 0, 1)) * math.sin(b)) * wire)
                     for b in (2 * math.pi * j / nv for j in range(nv))])
    for i in range(nu):
        a, b = rows[i], rows[(i + 1) % nu]
        for j in range(nv):
            bm.faces.new((a[j], b[j], b[(j + 1) % nv], a[(j + 1) % nv]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.6):
    """A hexagonal crystal along +Z, sunk `sink` radii below its foot, with a pointed tip. Every
    vertex stores how far up it is (0 to 1) in the layer "grad"."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = layer(bm, "grad")
    turn = rnd.uniform(0, math.pi / 3)
    tip_h = min(radius * rnd.uniform(*tip), length * 0.45)
    shoulder = length - tip_h
    taper = rnd.uniform(0.8, 0.94)
    radii = [radius * rnd.uniform(0.85, 1.15) for _ in range(6)]
    rings = []
    for z, s, g in ((-sink * radius, 1.0, 0.0), (shoulder, taper, 0.75)):
        ring = []
        for j in range(6):
            a = turn + j * math.pi / 3
            v = bm.verts.new((math.cos(a) * radii[j] * s, math.sin(a) * radii[j] * s, z))
            v[lay] = g
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.2, 0.2) * radius, rnd.uniform(-0.2, 0.2) * radius, length))
    apex[lay] = 1.0
    lo, hi = rings
    for j in range(6):
        k = (j + 1) % 6
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- materials: painted metal, worked out in 3D and baked into the colour image -------------------------

class Nodes:
    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new
        self._co = None

    @property
    def co(self):
        if self._co is None:
            self._co = self.new("ShaderNodeTexCoord").outputs["Object"]
        return self._co

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        n.inputs["Roughness"].default_value = rough
        self.link(vec, n.inputs["Vector"])
        return n.outputs["Fac"]

    def stretched(self, scale, rot=(0, 0, 0)):
        mp = self.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Rotation"].default_value = [math.radians(a) for a in rot]
        self.link(self.co, mp.inputs["Vector"])
        return mp.outputs["Vector"]

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

    def up(self, lo, hi):
        """1 where the surface faces up, 0 where it faces sideways or down."""
        geo = self.new("ShaderNodeNewGeometry")
        sep = self.new("ShaderNodeSeparateXYZ")
        self.link(geo.outputs["Normal"], sep.inputs[0])
        return self.ramp(sep.outputs[2], lo, hi)

    def edge(self, radius=0.03, lo=0.997, hi=0.93):
        """1 on the sharp edges of the shape, 0 elsewhere. The Bevel node rounds the normal across a
        crease; compared with the shading normal (not the flat facet normal, which differs from it
        all over a smooth curved part) that difference is only found at the creases."""
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
        """1 deep in a joint or recess, 0 in the open."""
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
        """1 within r0 of any of `points`, fading to 0 at r1."""
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
        """Thin, sparse scratch lines in two directions, clustered in patches."""
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


def metal(name, base, edge="#A9AFB5", grime="#121314", vary=0.3, streak=0.28, mottle=0.16, wear=1.0, edge_r=0.06,
          scratch=0.6, soot=0.0, dust=0.4, rough=0.62, warm="#4E3E30", warm_amount=0.25, rain=0.3, brush=(30.0, 1.4, 30.0),
          chips=0.0, bare="#8C939A", fade=0.0, oil=0.0, top_dust=0.0):
    """Weathered steel plate: every plate its own shade (`vary`), streaky brushed grain, dirty rain
    streaks running down, weathering blotches with warm staining, grime in the joints and recesses,
    dust towards the feet, light worn bevel edges, paint chipped back to bare steel along the edges
    and in scattered flakes (`chips`), scratches and soot near the exhausts."""
    m = kit.material(name, base, rough=rough)
    b = kit.principled(m)
    N = Nodes(m)
    grain = N.noise(N.stretched(brush), 1.0, 3.0, 0.55)
    tone = N.math('MULTIPLY_ADD', N.island(), vary, 1.0 - vary / 2)
    blotch = N.noise(N.co, 1.6, 4.0, 0.6)
    v = N.math('MULTIPLY', N.math('MULTIPLY_ADD', grain, 2 * streak, 1.0 - streak),
               N.math('MULTIPLY_ADD', blotch, 2 * mottle, 1.0 - mottle))
    if rain:
        streaks = N.ramp(N.noise(N.stretched((16.0, 16.0, 0.8)), 1.0, 3.0, 0.6), 0.5, 0.72, 1.0, 1.0 - rain)
        v = N.math('MULTIPLY', v, streaks)
    col = N.value(N.mix(N.math('MULTIPLY', N.ramp(N.noise(N.co, 0.9, 3.0), 0.48, 0.68), warm_amount), base, warm),
                  N.math('MULTIPLY', v, tone))
    if fade:
        # sun-faded, thinner paint in broad patches
        col = N.mix(N.ramp(N.noise(N.co, 2.2, 3.0, 0.55), 0.48, 0.66, 0.0, fade), col, N.value(col, 1.45))
    if oil:
        # dark oily blotches, heavier low down
        blot = N.math('MULTIPLY', N.ramp(N.noise(N.co, 1.3, 4.0, 0.6), 0.55, 0.7), N.height(0.6, 2.6, 1.0, 0.45))
        col = N.mix(N.math('MULTIPLY', blot, oil), col, "#14110E")
    if chips:
        # flakes of paint gone: wide along the edges, a few scattered on the faces; bare steel underneath
        flake = N.noise(N.co, 4.5, 6.0, 0.7)
        wide = N.edge(0.16, 0.999, 0.85)
        lost = N.math('MAXIMUM', N.ramp(N.math('ADD', flake, N.math('MULTIPLY', wide, 0.36)), 0.7, 0.73),
                      N.ramp(flake, 0.71, 0.73))
        steel_under = N.value(bare, N.math('MULTIPLY_ADD', grain, 0.4, 0.8))
        col = N.mix(N.math('MULTIPLY', lost, chips), col, steel_under)
    col = N.mix(N.math('MULTIPLY', N.cavity(0.3, 0.97, 0.5), 0.92), col, grime)
    if dust:
        col = N.mix(N.math('MULTIPLY', N.height(0.0, 0.9), dust), col, "#5E5649")
    if top_dust:
        settle = N.math('MULTIPLY', N.up(0.35, 0.85), N.ramp(N.noise(N.co, 3.2, 4.0, 0.6), 0.38, 0.62, 0.25, 1.0))
        col = N.mix(N.math('MULTIPLY', settle, top_dust), col, "#7D776C")
    worn = N.ramp(N.noise(N.co, 5.0, 4.0, 0.65), 0.3, 0.55, 0.45, 1.0)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', N.edge(edge_r, 0.998, 0.9), worn), wear), col, edge)
    if scratch:
        col = N.mix(N.scratches(scratch), col, edge)
    if soot:
        sooty = N.math('MULTIPLY', N.near(SOOT, 0.15, 0.85), N.ramp(N.noise(N.co, 3.0, 4.0), 0.3, 0.6, 0.55, 1.0))
        col = N.mix(N.math('MULTIPLY', sooty, soot), col, "#0B0A09")
    N.link(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def brass(name, base="#9C7531", hi="#EBD08A", tarnish="#4E3A1C", patina="#4C8B78", patina_amount=0.55,
          soot=0.0, rough=0.5):
    """Old brass or copper: brushed streaks, darker tarnish blotches, a teal patina gathered in the
    recesses and joints, and bright polished edges where it is handled."""
    m = kit.material(name, base, rough=rough)
    b = kit.principled(m)
    N = Nodes(m)
    grain = N.noise(N.stretched((30.0, 30.0, 1.6)), 1.0, 3.0, 0.55)
    col = N.value(base, N.math('MULTIPLY', N.math('MULTIPLY_ADD', grain, 0.36, 0.82),
                               N.math('MULTIPLY_ADD', N.island(), 0.2, 0.9)))
    col = N.mix(N.ramp(N.noise(N.co, 2.2, 4.0, 0.6), 0.42, 0.68, 0.0, 0.7), col, tarnish)
    pat = N.math('MULTIPLY', N.math('MAXIMUM', N.cavity(0.2, 0.97, 0.6), N.ramp(N.noise(N.co, 4.0, 4.0), 0.6, 0.7)), patina_amount)
    col = N.mix(pat, col, patina)
    col = N.mix(N.math('MULTIPLY', N.edge(0.03, 0.998, 0.92), 0.9), col, hi)
    if soot:
        col = N.mix(N.math('MULTIPLY', N.near(SOOT, 0.12, 0.6), soot), col, "#120E0A")
    N.link(col, b.inputs["Base Color"])
    return m


def drill_steel(name):
    """Polished drill steel that reads from across the room: each flute's land polished nearly white,
    the scoop behind it darkening to scoured steel and packed earth at its foot, so the three
    spirals stand out bright against dark; a mirror line on every cutting ridge, a straw-and-blue
    temper colour at the base."""
    m = kit.material(name, "#A9B1B8", rough=0.3)
    b = kit.principled(m)
    N = Nodes(m)
    a = N.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "grad"
    g = a.outputs["Fac"]
    sp = N.new("ShaderNodeAttribute")
    sp.attribute_type, sp.attribute_name = 'GEOMETRY', "spin"
    across = sp.outputs["Fac"]                            # 0 on the land behind a cutting ridge, ~0.92 at the foot of the next
    xyz = N.new("ShaderNodeCombineXYZ")
    N.link(N.math('MULTIPLY', across, 34.0), xyz.inputs[0])
    N.link(N.math('MULTIPLY', g, 2.5), xyz.inputs[1])
    grain = N.noise(xyz.outputs[0], 1.0, 3.0, 0.6)
    col = N.mix(N.ramp(across, 0.1, 0.85), "#DCE2E7", "#2C3237")
    col = N.value(col, N.math('MULTIPLY_ADD', grain, 0.36, 0.82))
    col = N.mix(N.ramp(g, 0.0, 0.07, 0.65, 0.0), col, "#A88446")
    col = N.mix(N.math('MULTIPLY', N.ramp(g, 0.05, 0.08, 0.0, 1.0), N.ramp(g, 0.09, 0.14, 0.45, 0.0)), col, "#4F5F8E")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.16, 0.99, 0.6), 0.8), col, "#1D2024")
    dirt = N.math('MULTIPLY', N.math('MULTIPLY', N.ramp(across, 0.6, 0.9), N.ramp(g, 0.25, 0.7)),
                  N.ramp(N.noise(N.co, 6.0, 4.0), 0.42, 0.56, 0.3, 0.9))
    col = N.mix(dirt, col, "#46311F")
    col = N.mix(N.edge(0.014, 0.999, 0.965), col, "#FBFCFD")
    col = N.mix(N.scratches(0.4), col, "#E4E8EB")
    N.link(col, b.inputs["Base Color"])
    return m


def paint(name, base, bare="#9AA1A8", grime="#140F0B", vary=0.12, chips=1.0, chip_scale=4.2, edge_chip=0.27,
          fade=0.3, rain=0.35, oil=0.3, soot=0.9, dust=0.5, top_dust=0.35, scratch=0.55, rough=0.55):
    """Thick industrial enamel over steel: each plate a slightly different batch, sun-faded patches,
    grime washed down in streaks and oily blotches low down, paint chipped back to bare brushed steel
    (most of it along the edges) with a hard dark rim round every chip, a thin rubbed-bright line on
    the very edges, scratches, grime in the joints, dust settled on top and towards the feet, soot by
    the stacks. The chip thresholds are hard, so the wear stays crisp when the texture is magnified."""
    m = kit.material(name, base, rough=rough)
    b = kit.principled(m)
    N = Nodes(m)
    grain = N.noise(N.stretched((30.0, 1.4, 30.0)), 1.0, 3.0, 0.55)
    tone = N.math('MULTIPLY_ADD', N.island(), vary, 1.0 - vary / 2)
    blotch = N.noise(N.co, 1.4, 4.0, 0.6)
    col = N.value(base, N.math('MULTIPLY', N.math('MULTIPLY_ADD', blotch, 0.28, 0.86), tone))
    if fade:
        f = N.ramp(N.noise(N.co, 1.9, 3.0, 0.55), 0.5, 0.68, 0.0, fade)
        col = N.mix(f, col, N.mix(0.4, N.value(col, 1.2), "#B5AC94"))
    if rain:
        streak = N.ramp(N.noise(N.stretched((14.0, 14.0, 0.7)), 1.0, 3.0, 0.6), 0.52, 0.7, 0.0, rain)
        col = N.mix(streak, col, "#3B2E20")
    if oil:
        blot = N.math('MULTIPLY', N.ramp(N.noise(N.co, 1.3, 4.0, 0.6), 0.55, 0.7), N.height(0.6, 2.4, 1.0, 0.35))
        col = N.mix(N.math('MULTIPLY', blot, oil), col, "#1A140E")
    if chips:
        flake = N.noise(N.co, chip_scale, 6.0, 0.72)
        s = N.math('ADD', flake, N.math('MULTIPLY', N.edge(0.13, 0.999, 0.86), edge_chip))
        rim = N.ramp(s, 0.655, 0.662, smooth=False)
        lost = N.ramp(s, 0.672, 0.678, smooth=False)
        col = N.mix(N.math('MULTIPLY', rim, chips), col, "#2A2017")
        under = N.value(bare, N.math('MULTIPLY_ADD', grain, 0.45, 0.75))
        col = N.mix(N.math('MULTIPLY', lost, chips), col, under)
    col = N.mix(N.math('MULTIPLY', N.cavity(0.3, 0.97, 0.5), 0.9), col, grime)
    if dust:
        col = N.mix(N.math('MULTIPLY', N.height(0.0, 0.9), dust), col, "#6A5E4C")
    if top_dust:
        settle = N.math('MULTIPLY', N.up(0.35, 0.85), N.ramp(N.noise(N.co, 3.2, 4.0, 0.6), 0.4, 0.62, 0.2, 1.0))
        col = N.mix(N.math('MULTIPLY', settle, top_dust), col, "#8A8270")
    worn = N.ramp(N.noise(N.co, 5.0, 4.0, 0.65), 0.35, 0.55, 0.3, 1.0)
    col = N.mix(N.math('MULTIPLY', N.edge(0.035, 0.998, 0.93), worn), col, "#C6CBCF")
    if scratch:
        col = N.mix(N.scratches(scratch), col, "#B9BEC2")
    if soot:
        sooty = N.math('MULTIPLY', N.near(SOOT, 0.15, 0.85), N.ramp(N.noise(N.co, 3.0, 4.0), 0.3, 0.6, 0.55, 1.0))
        col = N.mix(N.math('MULTIPLY', sooty, soot), col, "#0B0A09")
    N.link(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def blade_steel(name):
    """Digging blades: dark forged steel at the root, scoured bright towards the tip and along the
    cutting edges, scratched all over, earth caked in the joints."""
    m = kit.material(name, "#4F565D", rough=0.5)
    b = kit.principled(m)
    N = Nodes(m)
    grain = N.noise(N.stretched((2.0, 26.0, 26.0)), 1.0, 3.0, 0.55)
    col = N.value("#4F565D", N.math('MULTIPLY', N.math('MULTIPLY_ADD', grain, 0.4, 0.8),
                                    N.math('MULTIPLY_ADD', N.island(), 0.25, 0.88)))
    a = N.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "grad"
    scour = N.math('MULTIPLY', N.ramp(a.outputs["Fac"], 0.45, 0.95), N.ramp(N.noise(N.co, 4.0, 4.0), 0.3, 0.6, 0.6, 1.0))
    col = N.mix(N.math('MULTIPLY', scour, 0.8), col, "#959CA3")
    col = N.mix(N.math('MULTIPLY', N.cavity(0.2, 0.97, 0.55), 0.9), col, "#2A2018")
    col = N.mix(N.math('MULTIPLY', N.height(0.0, 0.35), 0.45), col, "#5A4A3A")
    col = N.mix(N.math('MULTIPLY', N.edge(0.04, 0.998, 0.9), 0.85), col, "#D9DEE2")
    col = N.mix(N.scratches(0.7), col, "#B8BEC4")
    N.link(col, b.inputs["Base Color"])
    return m


def hazard(name, width=0.2):
    """Hazard stripes, yellow and black at 45 degrees, chipped and worn back to steel at the edges."""
    m = kit.material(name, "#E0AA1C", rough=0.6)
    b = kit.principled(m)
    N = Nodes(m)
    d = N.new("ShaderNodeVectorMath")
    d.operation = 'DOT_PRODUCT'
    N.link(N.co, d.inputs[0])
    d.inputs[1].default_value = (0.62, 0.48, 0.62)
    stripe = N.math('GREATER_THAN', N.math('FRACT', N.math('MULTIPLY', d.outputs["Value"], 1.0 / (2 * width))), 0.5)
    yellow = N.value("#D9A51E", N.math('MULTIPLY_ADD', N.noise(N.co, 3.0, 4.0), 0.3, 0.85))
    col = N.mix(stripe, yellow, "#1C1B1A")
    chips = N.ramp(N.noise(N.co, 9.0, 5.0, 0.6), 0.64, 0.67)
    worn = N.ramp(N.noise(N.co, 6.0, 4.0, 0.65), 0.3, 0.55, 0.4, 1.0)
    col = N.mix(N.math('MAXIMUM', chips, N.math('MULTIPLY', N.edge(0.06, 0.998, 0.9), worn)), col, "#8E949A")
    col = N.mix(N.scratches(0.6), col, "#9EA4AA")
    col = N.mix(N.math('MULTIPLY', N.cavity(), 0.8), col, "#17171A")
    col = N.mix(N.math('MULTIPLY', N.height(0.0, 0.8), 0.4), col, "#5E5649")
    N.link(col, b.inputs["Base Color"])
    return m


def gem(name, stops, edge):
    """A crystal: dark at the foot, clear in the body, pale at the tip; each facet lighter or darker
    by the way it faces, its edges catching the light."""
    m = kit.material(name, stops[2][1], rough=0.3)
    b = kit.principled(m)
    N = Nodes(m)
    a = N.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "grad"
    ramp = N.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*kit.srgb(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*kit.srgb(stops[-1][1]), 1.0)
    for pos, hexcode in stops[1:-1]:
        e = els.new(pos)
        e.color = (*kit.srgb(hexcode), 1.0)
    N.link(a.outputs["Fac"], ramp.inputs["Fac"])
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    N.link(geo.outputs["True Normal"], dot.inputs[0])
    dot.inputs[1].default_value = (-0.45, -0.55, 0.7)
    col = N.value(ramp.outputs["Color"], N.math('MULTIPLY_ADD', dot.outputs["Value"], 0.4, 1.0))
    col = N.mix(N.math('MULTIPLY', N.edge(0.02, 0.995, 0.9), 0.4), col, edge)
    N.link(col, b.inputs["Base Color"])
    return m


# ---- the driller ----------------------------------------------------------------------------------------

def env(y):
    """Half width and height of the shell above the springline at y: a long dome, highest over the
    shoulders."""
    s = max(-1.0, min(1.0, (y - 0.45) / 2.2))
    return 1.52 * math.sqrt(max(0.0, 1 - 0.25 * s * s)), 1.66 * math.sqrt(max(0.0, 1 - 0.55 * s * s))


def build():
    yellow = paint("Paint", "#DE9C22")
    plate = metal("Gunmetal", "#353D46", edge="#B4BAC0", soot=0.9, chips=0.7, bare="#959CA3", vary=0.3, fade=0.3, oil=0.5,
                  top_dust=0.4, grime="#0E0F10")
    dark = metal("DarkSteel", "#23272C", edge="#8A9198", soot=0.9, vary=0.25, oil=0.4, top_dust=0.3, grime="#0B0B0C")
    steel = metal("Steel", "#454B52", edge="#B8BDC2", dust=0.6, chips=0.8, bare="#989EA5", fade=0.35, oil=0.45, top_dust=0.35,
                  grime="#0E0F10")
    iron = metal("Iron", "#3A3633", edge="#8A8580", warm="#5A3A22", warm_amount=0.5, scratch=0.2, rain=0.0)
    blade = blade_steel("BladeSteel")
    drill = drill_steel("DrillSteel")
    brs = brass("Brass", soot=0.8)
    cop = brass("Copper", base="#9A522B", hi="#EBA77A", tarnish="#46261A", patina="#3E8C78", patina_amount=0.7)
    haz = hazard("Hazard")
    amethyst = gem("Amethyst", [(0.0, "#2A0F40"), (0.35, "#5B2A93"), (0.75, "#9E62E6"), (1.0, "#E7D2FF")], "#F0E4FF")
    sapphire = gem("Sapphire", [(0.0, "#071A3A"), (0.35, "#17499E"), (0.75, "#3A84EC"), (1.0, "#C4DEFF")], "#DDEBFF")
    glow = kit.material("GLOW_Furnace", "#FF6E1A", rough=0.4, emit=5.0)

    d = Prop("Driller")
    d.tally = {}

    def add(part, bm, mat, at=None, crease=40.0):
        layer(bm, "grad")
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
        if crease:
            sharpen(bm, crease)
        d.tally[part] = d.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        d.add(bm, mat)

    def rivets(points, mat=dark, r=0.05):
        for p, n in points:
            add("rivets", rivet(r, r * 0.8, segs=6), mat, aim(p, n, 15), crease=0)

    def on(Mx, at, uvs):
        return [(Mx @ p, (Mx.to_3x3() @ n).normalized()) for p, n in (at(u, v) for u, v in uvs)]

    # ---- hull: a dark steel core under the shell, a hazard-striped bumper at the back -------------------------
    add("hull", block((2.3, 3.9, 1.35), bevel=0.08, top=(0.9, 0.95)), dark, M((0, 0.42, 1.62)))
    add("hull", block((2.15, 0.34, 0.62), bevel=0.05), haz, M((0, 2.5, 1.2), rot=(-8, 0, 0)))
    # furnace light leaking from under the armour skirt along both flanks
    for sx in (-1, 1):
        add("furnace", block((0.05, 2.7, 0.07), bevel=0.0), glow, M((sx * 1.165, 0.25, 1.04)), crease=0)
        for y in (-0.7, 0.2, 1.1):
            add("furnace", block((0.09, 0.07, 0.16), bevel=0.015), dark, M((sx * 1.18, y, 1.04)))

    # ---- the banded shell: painted, faceted, crested bands, each tucked under the one in front ---------------
    shell = Surface()
    step = (SHELL_Y[1] - SHELL_Y[0] - BAND_LEN) / (BANDS - 1)
    for i in range(BANDS):
        y0 = SHELL_Y[0] + i * step
        y1 = y0 + BAND_LEN

        def k(v):
            return 0.9 + 0.1 * v + 0.04 * v ** 3

        def rx_of(v, y0=y0, y1=y1):
            return env(y0 + (y1 - y0) * v)[0] * k(v)

        def rz_of(v, y0=y0, y1=y1):
            return env(y0 + (y1 - y0) * v)[1] * k(v)

        bm, at = arch_band(rx_of, rz_of, y0, y1, -0.2, math.pi + 0.2, n=2.4, thick=0.14, cols=12, rows=2,
                           bevel=0.03, ridge=0.1, ridge_w=0.45)
        shell.take(bm)
        add("shell", bm, yellow, crease=11.0)
        rivets([at(u, 0.84, -0.005) for u in (0.15, 0.38, 0.62, 0.85)])
    # the rump: a faceted dome tucked under the last band, closing the back
    yc = SHELL_Y[1] - 0.14
    rxc, rzc = env(yc)

    def kc(v):
        return 0.93 * math.cos(v * math.pi / 2 * 0.96)

    bm, at = arch_band(lambda v: rxc * kc(v), lambda v: rzc * kc(v), yc, yc + 0.62, -0.2, math.pi + 0.2, n=2.4, thick=0.13,
                       cols=12, rows=4, bevel=0.03, ridge=0.05, ridge_w=0.45)
    shell.take(bm)
    add("shell", bm, yellow, crease=11.0)
    rivets([at(u, 0.3, -0.005) for u in (0.2, 0.5, 0.8)])
    shell.done()

    # ---- head: a dark face under a painted brow hood, a wide visor light bar, a heavy snout housing ----------
    H = M(HEAD_AT, rot=HEAD_ROT)
    head_cuts = [((0.6, -0.55, 0), (1, -0.55, 0)), ((-0.6, -0.55, 0), (-1, -0.55, 0)),          # cheeks
                 ((0, -0.55, -0.42), (0, -0.75, -1.0))]                                           # chin
    add("head", block((1.7, 1.1, 1.32), cuts=head_cuts, bevel=0.045, top=(0.86, 0.92)), dark, H @ M((0, 0, 0.04)))
    # the visor: a protruding dark housing, a glowing bar split into five lamp cells by four ribs
    VZ = 0.53
    add("visor", block((1.32, 0.2, 0.25), bevel=0.03, top=(1.0, 0.85)), dark, H @ M((0, -0.6, VZ)))
    add("visor", block((1.2, 0.04, 0.12), bevel=0.0), glow, H @ M((0, -0.7, VZ)), crease=0)
    for x in (-0.36, -0.12, 0.12, 0.36):
        add("visor", block((0.05, 0.07, 0.17), bevel=0.012), iron, H @ M((x, -0.715, VZ)))
    for x in (-0.66, 0.66):
        add("visor", block((0.08, 0.24, 0.29), bevel=0.02), brs, H @ M((x, -0.6, VZ)))
    # the brow hood: a heavy painted plate overhanging the visor
    brow, brow_at = cap_plate(1.9, 1.15, bulge=(0.1, 0.04), thick=0.13, taper=0.82, corner=0.55)
    BR = H @ M((0, -0.2, 0.8), rot=(4, 0, 0)) @ M(rot=(0, 0, 180))
    add("head", brow, yellow, BR)
    rivets(on(BR, brow_at, ((-0.65, 0.5), (0.65, 0.5), (-0.62, -0.62), (0.62, -0.62))))
    for sx in (-1, 1):
        cheek, cheek_at = cap_plate(0.9, 0.95, bulge=(0.05, 0.05), thick=0.1, corner=0.4)
        CK = H @ M((sx * 0.86, 0.12, -0.08), rot=(0, 90 * sx, 0))
        add("head", cheek, yellow, CK)
        rivets(on(CK, cheek_at, ((-0.6, 0.6), (0.6, 0.6), (-0.6, -0.6), (0.6, -0.6))))

    # the snout: an eight-sided painted housing, a dark collar with a brass rim, the fluted cone
    ddir = Matrix.Rotation(math.radians(DRILL_TILT), 3, 'X') @ Vector((0, -1, 0))
    hub = H @ HUB
    add("snout", cylinder(0.76, 0.5, segs=8, bevel=0.05, r2=0.7), yellow, aim(hub + ddir * 0.2, ddir, 22.5), crease=30)
    add("snout", cylinder(0.71, 0.07, segs=16, bevel=0.02), brs, aim(hub + ddir * 0.47, ddir))
    add("snout", cylinder(0.68, 0.16, segs=16, bevel=0.035, r2=0.64), dark, aim(hub + ddir * 0.56, ddir))
    for j in range(8):
        a = 2 * math.pi * (j + 0.5) / 8
        q = aim(hub + ddir * 0.64, ddir) @ Vector((0.655 * math.cos(a), 0.655 * math.sin(a), 0))
        add("rivets", rivet(0.035, 0.03, segs=6), brs, aim(q, ddir), crease=0)
    base = hub + ddir * 0.6
    add("drill", drill_cone(2.35, 0.6, flutes=3, per=12, rings=18, turns=1.25), drill, aim(base, ddir))

    # ---- belly furnace: a low housing under the chest, its glow showing through angled louvres ---------------
    add("furnace", block((1.75, 0.8, 0.75), bevel=0.05, top=(0.95, 0.9)), dark, M((0, -1.8, 0.78)))
    add("furnace", block((1.48, 0.04, 0.46), bevel=0.0), glow, M((0, -2.2, 0.76)), crease=0)
    for z in (0.5, 1.02):
        add("furnace", block((1.64, 0.1, 0.08), bevel=0.02), brs, M((0, -2.22, z)))
    for x in (-0.78, 0.78):
        add("furnace", block((0.08, 0.1, 0.6), bevel=0.02), brs, M((x, -2.22, 0.76)))
    for z in (0.64, 0.77, 0.9):
        add("furnace", block((1.46, 0.05, 0.07), bevel=0.012), iron, M((0, -2.25, z), rot=(35, 0, 0)))

    # ---- front legs: a great pauldron, thick arm with a piston, and a shovel claw of three heavy blades ---------
    for sx in (-1, 1):
        S = Vector((sx * 1.22, -0.95, 1.38))
        E = Vector((sx * 1.72, -1.55, 0.92))
        W = Vector((sx * 1.95, -2.15, 0.58))
        add("front legs", cylinder(0.42, 0.5, segs=12), dark, aim(S + Vector((sx * 0.1, 0, 0)), (sx, 0, 0)))
        m, ln = frame(S, E, (sx, 0, 0))
        add("front legs", block((0.56, 0.58, ln + 0.3), bevel=0.06), steel, m)
        add("front legs", cylinder(0.27, 0.62, segs=12), dark, aim(E, (sx, 0, 0)))
        m, ln = frame(E, W, (sx, 0, 0))
        add("front legs", block((0.5, 0.52, ln + 0.2), bevel=0.05, top=(1.12, 1.12)), steel, m)
        p0, p1 = S + Vector((sx * 0.02, -0.38, 0.12)), W + Vector((0, -0.12, 0.3))
        add("pistons", kit.tube([p0, p0.lerp(p1, 0.55)], [0.09, 0.09], segs=8, rings=1), brs)
        add("pistons", kit.tube([p0.lerp(p1, 0.5), p1], [0.055, 0.055], segs=8, rings=1), drill)
        pauldron, pat = cap_plate(1.25, 1.15, bulge=(0.16, 0.1), thick=0.14, nu=6, nv=4, taper=0.85, corner=0.5)
        P = basis(S + Vector((sx * 0.35, 0.05, 0.28)), (0, -1, 0), (sx * 0.8, -0.12, 0.6))
        add("pauldrons", pauldron, yellow, P)
        rivets(on(P, pat, ((-0.85, 0.5), (-0.85, -0.5))))
        over, oat = cap_plate(0.82, 0.98, bulge=(0.12, 0.08), thick=0.12, nu=5, nv=4, taper=0.85, corner=0.55)
        P2 = P @ M((0.24, 0.0, 0.11))
        add("pauldrons", over, plate, P2)
        rivets(on(P2, oat, ((-0.6, 0.6), (0.6, 0.6), (-0.6, -0.6), (0.6, -0.6))), brs)

        # the hand: a thick mitt turned out like a mole's, its back plated with hazard stripes, three blades
        f = Vector((sx * 0.15, -0.78, -0.6)).normalized()
        u = Vector((sx * 0.45, -0.55, 0.7)).normalized()
        u = (u - f * u.dot(f)).normalized()
        across = f.cross(u).normalized()
        Hm = basis(W + f * 0.25, across, u)
        add("claws", block((1.2, 0.85, 0.38), bevel=0.06, top=(0.9, 0.85)), steel, Hm)
        add("claws", block((1.0, 0.66, 0.07), bevel=0.025), haz, Hm @ M((0, -0.03, 0.21)))
        rivets(on(Hm, lambda uu, vv: (Vector((uu * 0.55, vv * 0.38, 0.215)), Vector((0, 0, 1))), ((-1, -1), (1, -1), (-1, 1), (1, 1))), brs)
        for kk in (-1, 0, 1):
            R = Hm @ Vector((kk * 0.38, 0.42, -0.04))
            T = Vector((R.x + (R - W).x * 0.35 * abs(kk) + sx * 0.08, -3.3 + 0.08 * abs(kk), -0.05))
            C = R.lerp(T, 0.5) + Vector((0, -0.18, 0.26))
            path = [R - f * 0.3, R, C, T]
            add("claws", section_loft(path, lambda t: blade_profile(0.44 - 0.3 * t ** 1.3, 0.2 - 0.14 * t), u, rings=8), blade, crease=35)

    # ---- hind legs: hip hub, haunch armour, a thick short leg and a heavy foot with three toe claws --------------
    for sx in (-1, 1):
        Hp = Vector((sx * 1.18, 1.78, 1.15))
        K = Vector((sx * 1.45, 2.12, 0.66))
        A = Vector((sx * 1.45, 1.86, 0.36))
        add("hind legs", cylinder(0.42, 0.45, segs=12), dark, aim(Hp + Vector((sx * 0.1, 0, 0)), (sx, 0, 0)))
        m, ln = frame(Hp, K, (sx, 0, 0))
        add("hind legs", block((0.64, 0.68, ln + 0.3), bevel=0.06), steel, m)
        add("hind legs", cylinder(0.27, 0.62, segs=12), dark, aim(K, (sx, 0, 0)))
        m, ln = frame(K, A, (sx, 0, 0))
        add("hind legs", block((0.54, 0.56, ln + 0.25), bevel=0.05), steel, m)
        add("feet", block((0.92, 1.15, 0.42), bevel=0.06, top=(0.86, 0.8), shift=(0, 0.06)), steel, M((sx * 1.47, 1.7, 0.2)))
        for kk in (-1, 0, 1):
            R = Vector((sx * 1.47 + kk * 0.28, 1.2, 0.2))
            path = [R + Vector((0, 0.22, 0.02)), R, R + Vector((0, -0.2, -0.02)), Vector((R.x + kk * 0.04, 0.82, -0.04))]
            add("feet", section_loft(path, lambda t: blade_profile(0.24 - 0.14 * t, 0.15 - 0.09 * t), (0, 0, 1), rings=6), blade, crease=35)
        haunch, hat = cap_plate(1.4, 1.2, bulge=(0.14, 0.1), thick=0.14, corner=0.5)
        Q = basis(Vector((sx * 1.6, 1.85, 1.3)), (0, 1, 0), (sx * 0.94, 0.0, 0.34))
        add("haunches", haunch, yellow, Q)
        rivets(on(Q, hat, ((-0.85, 0.5), (-0.85, -0.5))))
        over, oat = cap_plate(0.95, 0.98, bulge=(0.12, 0.08), thick=0.12, nu=5, nv=4, corner=0.55)
        Q2 = Q @ M((0.24, 0.0, 0.11))
        add("haunches", over, plate, Q2)
        rivets(on(Q2, oat, ((-0.6, 0.6), (0.6, 0.6), (-0.6, -0.6), (0.6, -0.6))), brs)

    # ---- pipes along the flanks, clamped to the skirt of the shell ---------------------------------------------
    for sx in (-1, 1):
        run = [(sx * 1.2, -1.4, 1.0), (sx * 1.5, -1.05, 1.2), (sx * 1.64, -0.5, 1.24), (sx * 1.64, 0.9, 1.24),
               (sx * 1.58, 1.35, 1.22), (sx * 1.3, 1.7, 1.15)]
        add("pipes", kit.tube(run, [0.08] * len(run), segs=8, rings=10), cop)
        run2 = [(sx * 1.5, -0.75, 1.42), (sx * 1.6, -0.4, 1.42), (sx * 1.6, 0.85, 1.42), (sx * 1.5, 1.2, 1.4)]
        add("pipes", kit.tube(run2, [0.05] * len(run2), segs=6, rings=6), brs)
        for y in (-0.2, 0.45):
            add("pipes", block((0.16, 0.14, 0.36), bevel=0.02), dark, M((sx * 1.62, y, 1.33)))

    # ---- a chain hanging along the near flank, from the pauldron to the haunch ---------------------------------
    a, bpt = Vector((-1.84, -0.52, 1.12)), Vector((-1.86, 1.2, 1.08))
    nlinks = 9
    pts = []
    for j in range(nlinks + 1):
        t = j / nlinks
        p = a.lerp(bpt, t)
        p.z -= 0.32 * 4 * t * (1 - t)
        pts.append(p)
    for j in range(nlinks):
        c = (pts[j] + pts[j + 1]) / 2
        dvec = pts[j + 1] - pts[j]
        hint = Vector((1, 0, 0)) if j % 2 else Vector((0, 0, 1))
        dn = dvec.normalized()
        add("chain", chain_link(dvec.length * 1.4, 0.13, 0.028), iron, basis(c, dvec, hint - dn * hint.dot(dn)), crease=0)

    # ---- a boiler housing on the back, two short stacks raked back from its rear corners -------------------
    top, nrm = shell.hit((0, ENGINE_Y, 6.0), (0, 0, -1))
    tilt = -math.degrees(math.atan2(-nrm.y, nrm.z))
    E = M(top + Vector((0, 0, 0.12)), rot=(tilt, 0, 0))
    add("engine", block((1.3, 1.15, 0.62), bevel=0.05, top=(0.84, 0.82)), dark, E)
    add("engine", block((1.38, 1.22, 0.1), bevel=0.025), brs, E @ M((0, 0, -0.1)))
    eng_top = lambda uu, vv: (E @ Vector((uu * 0.42, vv * 0.36, 0.31)), (E.to_3x3() @ Vector((0, 0, 1))).normalized())
    rivets([eng_top(uu, vv) for uu, vv in ((-1, -1), (1, -1), (-1, 1), (1, 1))], brs, 0.045)
    for j in range(4):
        add("engine", block((0.05, 0.5, 0.05), bevel=0.012), iron, E @ M((-0.18 + 0.12 * j, -0.12, 0.31)))
    for sx, high in ((-1, STACK_TOP), (1, STACK_TOP - 0.28)):
        sdir = Vector((sx * 0.05, math.sin(math.radians(24)), math.cos(math.radians(24)))).normalized()
        foot = E @ Vector((sx * 0.27, 0.3, 0.12))
        ln = (high - foot.z) / sdir.z
        add("stacks", cylinder(0.2, ln - 0.2, segs=12, bevel=0.0), dark, aim(foot + sdir * (ln - 0.2) / 2, sdir))
        add("stacks", cylinder(0.25, 0.12, segs=12, bevel=0.03), brs, aim(foot + sdir * 0.45, sdir))
        mouth = foot + sdir * (ln - 0.28)
        add("stacks", hollow(0.26, 0.2, 0.28, segs=12), dark, aim(mouth, sdir))
        add("stacks", cylinder(0.205, 0.04, segs=12, bevel=0.0), glow, aim(mouth + sdir * 0.18, sdir), crease=0)
        # a rain flap hinged at the back of the mouth, its front edge lifted: the glow shows from the front
        # and the sides, and from behind the flap covers it
        rim = mouth + sdir * 0.28
        back = (Vector((0, 1, 0)) - sdir * sdir.y).normalized()
        open_ = math.radians(34)
        hinge = rim + back * 0.25
        flap_n = (sdir * math.cos(open_) + back * math.sin(open_)).normalized()
        centre = hinge + (-back * math.cos(open_) + sdir * math.sin(open_)) * 0.26 + flap_n * 0.03
        add("stacks", cylinder(0.27, 0.055, segs=12, bevel=0.018), iron, aim(centre, flap_n))
        add("stacks", block((0.16, 0.08, 0.08), bevel=0.015), brs, aim(hinge + flap_n * 0.02, flap_n))

    # ---- gem chunks the machine dug up, wedged between the back plates --------------------------------------
    for (x, y), mat, seed, n in (((-0.6, 0.15), amethyst, 1, 3), ((0.8, 0.95), sapphire, 2, 3), ((0.2, -0.7), sapphire, 3, 2),
                                 ((-1.05, 1.35), amethyst, 4, 2)):
        p, nrm = shell.hit((x, y, 6.0), (0, 0, -1))
        rnd = random.Random(seed)
        out = (nrm + Vector((0, 0.4, 0))).normalized()
        for j in range(n):
            ln = rnd.uniform(0.42, 0.55) * (1.0 if j == 0 else 0.68)
            off = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0)) if j else Vector()
            ax = (out + Vector((rnd.uniform(-0.45, 0.45), rnd.uniform(-0.3, 0.3), 0))).normalized()
            add("gems", crystal(ln, ln * 0.26, seed=seed * 10 + j), mat, aim(p + off, ax, rnd.uniform(0, 60)), crease=30)

    cut = cull_hidden(d.parts)
    print("  hidden faces removed: %d triangles" % cut)
    d.build()
    for ob in d.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return d


def bake(driller, texture, samples=32):
    """Everything that does not glow becomes one textured mesh, Driller_Body: the painted metal, its
    wear and grime and the soft shading in the joints are baked into its colour image. The glowing
    parts are joined into one mesh, Driller_GLOW, that keeps its emissive material."""
    glow = [ob for ob in driller.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in driller.objects if ob not in glow], texture, name="Driller_Body",
                            shade=0.6, soften=2, rough=0.62, samples=samples, uv_angle=75.0, uv_margin=0.004, pack_margin=0.003)
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    gl = bpy.context.view_layer.objects.active
    gl.name = gl.data.name = "Driller_GLOW"
    driller.objects = [body, gl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the head and drill to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,side,game distance:silhouette",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--bake-samples", type=int, default=32)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Driller review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "driller_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    driller = build()
    print("triangles by part:", dict(sorted(driller.tally.items(), key=lambda kv: -kv[1])))
    head = M(HEAD_AT, rot=HEAD_ROT) @ Vector((0, -0.6, -0.1))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(driller, samples=samples, focus=(head.x, head.y - 0.3, head.z - 0.3))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.62, -1.0, 0.32)).normalized() * 8.0,
                                          head + Vector((0, -0.55, -0.35)), 30)
        rig.cams["head"] = review._camera("C_head", head + Vector((-0.42, -1.0, 0.2)).normalized() * 5.2,
                                          head + Vector((0, -0.25, -0.15)), 30)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(driller, os.path.abspath(a.texture), a.bake_samples)
    tris = driller.triangles()
    lo, hi = driller.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = driller.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(driller.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        rig, review = rig_for(a.samples)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            rig.sheet(os.path.abspath(a.review), shots("full") if a.quick else review.STANDARD, px=a.px, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)
            print("face", a.face)


if __name__ == "__main__":
    main()
