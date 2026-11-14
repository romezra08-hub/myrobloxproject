"""Golem pet: an ancient crystal golem, a stone guardian. Built from scratch by script.

    python models/pets/golem.py --review out/golem.png      # render the review sheet
    python models/pets/golem.py --export models/export/golem.fbx

Style: a legendary creature next to the adult dragon, phoenix and griffin. Cool, ancient and
powerful; never cute, never a rounded cartoon rock man. Must-haves:
  1. Adult, imposing proportions: very broad shoulders, a deep chest leaning forward, a narrower
     waist, long heavy arms with huge fists hanging at knee height, short thick legs.
  2. Assembled from separate carved blocks with dark gaps between them (chest, shoulder boulders,
     upper arms, forearms, fists, pelvis, thighs, shins, feet), held by dark joint stones.
  3. A small low head sunk between the shoulders: a heavy carved brow over a glowing visor slit.
     No eyes, no mouth.
  4. Crisp chiselled planes: every block is a box cut by flat planes (chamfers, knocked-off
     corners, hewn facets), slightly irregular. No rounded pillows.
  5. Weathered dark slate with warm-brown variation, dark moss on some top surfaces, emerald
     crystal clusters on the shoulders, back and a forearm, and a modest emerald glow (visor,
     crystal cores, a few rune cracks on the chest and forearms).
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

LEAN = 15.0                       # the upper body leans forward this many degrees, round the waist
PIVOT = Vector((0.0, 0.1, 4.4))   # the point it leans round


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


def aim(origin, direction, roll=0.0):
    """A transform standing a shape built along +Z on `origin`, pointing along `direction`."""
    d = Vector(direction).normalized()
    m = d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Rotation(math.radians(roll), 4, 'Z')
    m.translation = Vector(origin)
    return m


class Surface:
    """Finds points exactly on a shape, so that details sit on it and neither float nor sink."""

    def __init__(self, bm):
        bm.normal_update()
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, direction):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized())
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc, nrm


# ---- carved stone -------------------------------------------------------------------------------------

def slice_off(bm, co, no):
    """Cut away everything in front of the plane through `co` facing `no`, and close the cut with a
    flat face: one stroke of the chisel."""
    no = Vector(no).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=Vector(co), plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return bm


def hewn(size, top=(1.0, 1.0), bottom=(1.0, 1.0), shift=(0.0, 0.0), seed=0, chamfer=(0.04, 0.1),
         corner=(0.02, 0.2), facets=3, tilt=(5.0, 12.0), rock=0, rock_depth=(0.84, 0.96), extra=(),
         chips=0, chip_depth=(0.16, 0.32)):
    """A carved stone block centred on the origin: a box `size` whose top is scaled by `top` and
    moved by `shift` and whose bottom is scaled by `bottom`, with every edge cut by a flat chamfer of
    a random width, every corner knocked off by a random plane (some barely, some deeply) and `facets` faces broken into two
    planes a few degrees apart. `rock` more random planes make a faceted boulder, and `extra` are
    more cuts, each (point, normal), in the block's own space. Chamfer depths are fractions of the
    smallest side, corner depths of the middle one."""
    rnd = random.Random(seed)
    sx, sy, sz = (s / 2.0 for s in size)
    small = min(size)
    middle = sorted(size)[1]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    for v in bm.verts:
        t = top if v.co.z > 0 else bottom
        d = shift if v.co.z > 0 else (0.0, 0.0)
        v.co = Vector((v.co.x * sx * t[0] + d[0], v.co.y * sy * t[1] + d[1], v.co.z * sz))
    bm.normal_update()
    planes = []
    for e in bm.edges:
        n = (e.link_faces[0].normal + e.link_faces[1].normal).normalized()
        mid = (e.verts[0].co + e.verts[1].co) / 2
        planes.append((mid - n * rnd.uniform(*chamfer) * small, n))
    for v in bm.verts:
        n = sum((f.normal for f in v.link_faces), Vector()).normalized()
        planes.append((v.co - n * rnd.uniform(*corner) * middle, n))
    faces = list(bm.faces)
    rnd.shuffle(faces)
    for f in faces[:facets]:
        n = f.normal.copy()
        c = f.calc_center_median()
        a = n.orthogonal().normalized()
        a = Matrix.Rotation(rnd.uniform(0, 2 * math.pi), 3, n) @ a
        reach = max((v.co - c).dot(a) for v in f.verts)
        hinge = c + a * rnd.uniform(-0.35, 0.2) * reach
        n2 = Matrix.Rotation(math.radians(rnd.uniform(*tilt)), 3, n.cross(a)) @ n
        if n2.dot(a) < 0:
            n2 = Matrix.Rotation(-2 * n.angle(n2), 3, n.cross(a)) @ n2
        planes.append((hinge, n2))
    for _ in range(rock):
        n = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        reach = math.sqrt((sx * n.x) ** 2 + (sy * n.y) ** 2 + (sz * n.z) ** 2)
        planes.append((n * reach * rnd.uniform(*rock_depth), n))
    corners = list(bm.verts)
    rnd.shuffle(corners)
    for v in corners[:chips]:                     # a few corners broken off deeply and skewed: old damage
        n = sum((f.normal for f in v.link_faces), Vector()).normalized()
        n = (n + Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))) * 0.35).normalized()
        planes.append((v.co - n * rnd.uniform(*chip_depth) * middle * 1.6, n))
    planes += [(Vector(co), Vector(n)) for co, n in extra]
    for co, n in planes:
        slice_off(bm, co, n)
    return bm


def ridge(face, half, axis, degrees, inset=0.01):
    """Two more cuts for hewn(): they break one face of a block into two planes meeting along a ridge
    through its middle, the way a mason dresses a stone. `face` is the face's outward direction in the
    block's own space, `half` how far out from the centre the face lies, `axis` the ridge's direction."""
    n = Vector(face).normalized()
    a = Vector(axis).normalized()
    co = n * (half - inset)
    return [(co, Matrix.Rotation(math.radians(degrees), 3, a) @ n), (co, Matrix.Rotation(math.radians(-degrees), 3, a) @ n)]


# ---- crystals ------------------------------------------------------------------------------------------

def crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35):
    """A hexagonal crystal along +Z: a slightly tapering, slightly irregular prism from `sink` below
    its foot to a pointed tip. Every vertex stores how far up it is (0 to 1) in the layer "grad"."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = layer(bm, "grad")
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
            v[lay] = g
            ring.append(v)
        rings.append(ring)
    apex = bm.verts.new((rnd.uniform(-0.15, 0.15) * radius, rnd.uniform(-0.15, 0.15) * radius, length))
    apex[lay] = 1.0
    lo, hi = rings
    for j in range(6):
        k = (j + 1) % 6
        bm.faces.new((lo[j], lo[k], hi[k], hi[j]))
        bm.faces.new((hi[j], hi[k], apex))
    bm.faces.new(lo[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lit_crystal(length, radius, seed=0, tip=(1.2, 2.0), sink=0.35, slit=0.03, core=0.74):
    """A crystal lit from inside: its facets stand a little apart, so the glowing core inside shows
    along every edge, and each long facet is split down its middle, where the layer "mid" is 1, so
    the colour can be paler there, as if the light behind showed through clearer stone.
    Returns (facets, core); the open bottom is sunk in the stone."""
    whole = crystal(length, radius, seed, tip, sink)
    src = whole.verts.layers.float.get("grad")
    bm = bmesh.new()
    lg, lm = layer(bm, "grad"), layer(bm, "mid")

    def vert(co, c, g, mid):
        d = co - c
        v = bm.verts.new(c + d * max(0.0, 1 - slit / max(d.length, 1e-6)))
        v[lg], v[lm] = g, mid
        return v

    for f in whole.faces:
        vs = list(f.verts)
        c = f.calc_center_median()
        if len(vs) == 4:                                   # a long facet: split down its middle
            a, b, cc, d = vs
            p = [vert(v.co, c, v[src], 0.0) for v in vs]
            m1 = vert((a.co + b.co) / 2, c, a[src], 1.0)
            m2 = vert((cc.co + d.co) / 2, c, cc[src], 1.0)
            bm.faces.new((p[0], m1, m2, p[3]))
            bm.faces.new((m1, p[1], p[2], m2))
        elif len(vs) == 3:
            bm.faces.new([vert(v.co, c, v[src], 0.6 if v[src] > 0.95 else 0.0) for v in vs])
    for e in bm.edges:
        e.smooth = False
    whole.free()
    return bm, crystal(length * 0.95, radius * core, seed, tip, sink)


def ribbon(points, normals, width, lift, sink=0.012, closed=False):
    """A thin ridge laid along a line of surface points: its crest `lift` above the surface, its two
    edges `sink` below it, `width` across and pinched to nothing at both ends (or, `closed`, a loop)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    nrm = [Vector(n).normalized() for n in normals]
    n = len(pts)
    rows = []
    for i in range(n):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = nrm[i].cross(t).normalized()
        w = width * (0.15 if i in (0, n - 1) and not closed else 1.0) / 2
        rows.append((bm.verts.new(pts[i] + side * w - nrm[i] * sink), bm.verts.new(pts[i] + nrm[i] * lift),
                     bm.verts.new(pts[i] - side * w - nrm[i] * sink)))
    for a, b in zip(rows, rows[1:] + (rows[:1] if closed else [])):
        bm.faces.new((a[0], b[0], b[1], a[1]))
        bm.faces.new((a[1], b[1], b[2], a[2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum((f.normal for f in bm.faces), Vector()).dot(sum(nrm, Vector())) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


# ---- materials -------------------------------------------------------------------------------------------

class Nodes:
    def __init__(self, mat):
        self.tree = mat.node_tree
        self.new, self.link = self.tree.nodes.new, self.tree.links.new

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
        self.link(colour, h.inputs["Color"])
        self.link(v, h.inputs["Value"])
        return h.outputs["Color"]

    def edge(self, radius=0.035, lo=0.997, hi=0.95):
        """1 on the sharp edges of the shape, 0 on its flat planes (the Bevel node rounds the normal
        near an edge; where that differs from the face's own normal there is an edge)."""
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


def stone(name, base="#3C3F43", warm="#54493E", edge="#9A958A", crack="#141516", moss="#34452A",
          moss_amount=0.0, wear=0.7, cracks=0.75, rough=0.92, vary=0.34, weather=0.0, pale="#8D8A7E",
          under=0.0, moss_light="#6F8F3A"):
    """Weathered slate: every block its own shade (`vary`), warm and cool patches, faint strata, a
    mottle of mineral grains, fine speckle, cracks, paler chipped edges and, on surfaces that face
    up, patches of dark moss. Worked out in 3D, so it has no seams; bake_texture bakes it into the
    colour image."""
    m = kit.material(name, base, rough=rough)
    b = kit.principled(m)
    N = Nodes(m)
    co = N.new("ShaderNodeTexCoord").outputs["Object"]
    warp = N.noise(co, 1.4, 3.0)
    wv = N.new("ShaderNodeVectorMath")
    wv.operation = 'MULTIPLY_ADD'
    N.link(warp.outputs["Color"], wv.inputs[0])
    wv.inputs[1].default_value = (0.3, 0.3, 0.3)
    N.link(co, wv.inputs[2])
    warped = wv.outputs[0]
    # warm and cool patches
    island = N.new("ShaderNodeNewGeometry").outputs["Random Per Island"]      # one random number per block
    big = N.noise(co, 0.55, 3.0)
    warmth = N.math('ADD', N.ramp(big.outputs["Fac"], 0.42, 0.64), N.math('MULTIPLY_ADD', island, 0.8, -0.3))
    col = N.mix(N.math('MULTIPLY', N.math('MINIMUM', N.math('MAXIMUM', warmth, 0.0), 1.0), 0.85), base, warm)
    strata = N.new("ShaderNodeTexWave")
    strata.bands_direction = 'Z'
    strata.inputs["Scale"].default_value, strata.inputs["Distortion"].default_value = 2.2, 6.0
    strata.inputs["Detail"].default_value = 2.0
    N.link(warped, strata.inputs["Vector"])
    layers = N.math('MULTIPLY_ADD', strata.outputs["Fac"], 0.1, 0.95)
    # mineral grains and speckle
    cells = N.new("ShaderNodeTexVoronoi")
    cells.inputs["Scale"].default_value = 2.6
    N.link(warped, cells.inputs["Vector"])
    bw = N.new("ShaderNodeRGBToBW")
    N.link(cells.outputs["Color"], bw.inputs[0])
    grain = N.math('MULTIPLY_ADD', bw.outputs[0], 0.3, 0.85)
    speck = N.noise(co, 13.0, 6.0, 0.62)
    fine = N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.44, 0.78)
    tone = N.math('MULTIPLY_ADD', island, vary, 1.0 - vary * 0.55)
    col = N.value(col, N.math('MULTIPLY', N.math('MULTIPLY', grain, fine), N.math('MULTIPLY', tone, layers)))
    # hairline cracks, only in some places
    cr = N.new("ShaderNodeTexVoronoi")
    cr.feature = 'DISTANCE_TO_EDGE'
    cr.inputs["Scale"].default_value = 1.15
    N.link(warped, cr.inputs["Vector"])
    line = N.ramp(cr.outputs["Distance"], 0.0, 0.045, 1.0, 0.0)
    where = N.ramp(N.noise(co, 1.3, 3.0).outputs["Fac"], 0.5, 0.6)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', line, where), cracks), col, crack)
    # worn, paler edges, unevenly
    worn = N.ramp(N.noise(co, 5.0, 4.0, 0.65).outputs["Fac"], 0.32, 0.6, 0.25, 1.0)
    col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', N.edge(), worn), wear), col, edge)
    # sun- and rain-bleached tops: paler stone on surfaces facing up, in broad uneven patches
    if weather:
        bleach = N.ramp(N.noise(co, 0.9, 3.0, 0.55).outputs["Fac"], 0.36, 0.6, 0.35, 1.0)
        col = N.mix(N.math('MULTIPLY', N.math('MULTIPLY', N.up(0.15, 0.85), bleach), weather), col, pale)
    # undersides in shadow and grime, darker
    if under:
        geo = N.new("ShaderNodeNewGeometry")
        sep = N.new("ShaderNodeSeparateXYZ")
        N.link(geo.outputs["Normal"], sep.inputs[0])
        col = N.mix(N.math('MULTIPLY', N.ramp(sep.outputs[2], -0.1, -0.85), under), col, "#16171A")
    # moss on top surfaces: broad patches, darker in the middle and fresher green at the edges
    if moss_amount:
        mn = N.noise(co, 1.2, 4.0, 0.6).outputs["Fac"]
        patch = N.ramp(mn, 0.45, 0.52)
        mo = N.math('MULTIPLY', N.math('MULTIPLY', N.up(0.3, 0.72), patch), moss_amount)
        tone_m = N.mix(N.ramp(mn, 0.52, 0.66), moss_light, moss)
        mossy = N.value(tone_m, N.math('MULTIPLY_ADD', speck.outputs["Fac"], 0.7, 0.65))
        col = N.mix(mo, col, mossy)
    N.link(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def crystal_material(name):
    """Emerald: dark at the foot, clear green in the body, pale at the tip; each facet a little
    lighter or darker by the way it faces, and its edges catching the light."""
    m = kit.material(name, "#12784C", rough=0.3)
    b = kit.principled(m)
    N = Nodes(m)
    a = N.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "grad"
    ramp = N.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    stops = [(0.0, "#021A0F"), (0.4, "#063F25"), (0.8, "#0F6E40"), (1.0, "#7FD6A8")]
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
    facet = N.math('MULTIPLY_ADD', dot.outputs["Value"], 0.4, 1.0)
    col = N.value(ramp.outputs["Color"], facet)
    # the core seen through the clearer middle of each facet: a bright streak, strongest low down
    md = N.new("ShaderNodeAttribute")
    md.attribute_type, md.attribute_name = 'GEOMETRY', "mid"
    glowpath = N.math('MULTIPLY', N.ramp(md.outputs["Fac"], 0.25, 1.0), N.ramp(a.outputs["Fac"], 0.0, 0.85, 1.0, 0.55))
    col = N.mix(N.math('MULTIPLY', glowpath, 0.85), col, "#38E08A")
    col = N.mix(N.math('MULTIPLY', N.edge(0.025, 0.995, 0.9), 0.32), col, "#A8EBC8")
    N.link(col, b.inputs["Base Color"])
    return m


# ---- the golem ------------------------------------------------------------------------------------------

def build():
    rock = stone("Stone", base="#4A4C4F", warm="#63554A", moss_amount=1.0, vary=0.46, weather=0.75, under=0.55)
    core = stone("CoreStone", base="#2C2D30", warm="#352F2A", edge="#55534E", wear=0.3, cracks=0.4, under=0.4)
    mossmat = stone("Moss", base="#3E5A24", warm="#56742C", edge="#86A44C", crack="#1F2A14", wear=0.6, cracks=0.0, vary=0.35)
    rootmat = stone("Root", base="#4A3B2B", warm="#5E4A34", edge="#8A7656", crack="#1E1710", wear=0.5, cracks=0.3, vary=0.25)
    scorch = stone("Scorch", base="#161716", warm="#1C1A17", edge="#2A2A28", wear=0.2, cracks=0.0)
    carved = stone("Carved", base="#1D1E20", warm="#221F1C", edge="#3A3936", wear=0.3, cracks=0.0, vary=0.1)
    gem = crystal_material("Crystal")
    glow = kit.material("GLOW_Emerald", "#17B850", rough=0.4, emit=3.0)

    g = Prop("Golem")
    g.tally = {}
    seeds = iter(range(1000))

    def add(part, bm, mat, at=None, crease=1.0, keep=False):
        layer(bm, "grad")
        layer(bm, "mid")
        if at is not None:
            bm.transform(at)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
        if crease is not None:
            sharpen(bm, crease)
        surf = Surface(bm) if keep else None
        g.tally[part] = g.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        g.add(bm, mat)
        return surf

    def block(part, size, at, mat=None, keep=False, **kw):
        kw.setdefault("seed", next(seeds) * 7 + 3)
        return add(part, hewn(size, **kw), mat or rock, at, keep=keep)

    L = Matrix.Translation(PIVOT) @ Matrix.Rotation(math.radians(LEAN), 4, 'X') @ Matrix.Translation(-PIVOT)

    def lean(p):
        return L @ Vector(p)

    def slab(part, size, at, mat=None, keep=False, **kw):
        """A hewn block with its own character: chamfer widths, corner knocks, broken facets and a
        few deep chips all drawn per block, so no two limb stones look alike."""
        seed = next(seeds) * 7 + 3
        r = random.Random(seed * 13 + 5)
        kw.setdefault("chamfer", (r.uniform(0.02, 0.05), r.uniform(0.07, 0.15)))
        kw.setdefault("corner", (0.02, r.uniform(0.14, 0.34)))
        kw.setdefault("facets", r.randint(1, 4))
        kw.setdefault("tilt", (4.0, r.uniform(9.0, 17.0)))
        kw.setdefault("chips", r.randint(1, 3))
        return add(part, hewn(size, seed=seed, **kw), mat or rock, at, keep=keep)

    def moss_tuft(centre, size, seed, up=(0, 0, 1)):
        """A cushion of moss: two or three squashed lumps."""
        r = random.Random(seed)
        U = Vector(up).normalized()
        for k in range(r.randint(2, 3)):
            w = size * r.uniform(0.55, 1.0)
            bm = kit.ball((w, w * r.uniform(0.6, 0.9), w * 0.42), cuts=1)
            kit.lumpy(bm, 0.03, 4.0, seed + k)
            off = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * size * 0.35
            add("moss", bm, mossmat, aim(Vector(centre) + off, U, r.uniform(0, 180)), crease=None)

    def root(points, r0=0.08, r1=0.025):
        n = len(points)
        radii = [r0 + (r1 - r0) * (i / (n - 1)) ** 0.8 for i in range(n)]
        add("roots", kit.tube(points, radii, segs=5, rings=(n - 1) * 3), rootmat, crease=None)

    # ---- legs: a heavy stone giant's: tapering thigh and shin masses dressed with fitted, broken slabs, a big
    # knee boulder, broad splayed feet whose toe stones grip the ground, moss and roots in the joints ----------
    legs = []
    for sx in (-1, 1):
        fy = -0.35 if sx < 0 else 0.1
        x = 1.2 * sx
        F = M((x, fy, 0.0), rot=(0, 0, 15 * sx))
        # the foot: a sole slab, an instep slab sloping down to the toes, a heel stone, four splayed toes
        slab("feet", (1.5, 1.35, 0.52), F @ M((0, 0.18, 0.26)), top=(0.86, 0.82), shift=(0, 0.06))
        slab("feet", (1.1, 0.95, 0.42), F @ M((0.04 * sx, -0.12, 0.66), rot=(14, 0, 3 * sx)), top=(0.8, 0.72), bottom=(1.0, 1.0))
        slab("feet", (0.8, 0.5, 0.42), F @ M((0.1 * sx, 0.86, 0.2), rot=(-10, 0, -8 * sx)), top=(0.8, 0.7))
        tr = random.Random(40 + sx)
        for k, ang in enumerate((-31, -10, 10, 31)):
            a = math.radians(ang + tr.uniform(-4, 4))
            w = (0.42, 0.48, 0.46, 0.38)[k] * tr.uniform(0.92, 1.08)
            ln = (0.6, 0.74, 0.7, 0.55)[k] * tr.uniform(0.92, 1.08)
            h = (0.4, 0.46, 0.44, 0.36)[k]
            base = Vector((0.18 * math.sin(a) * 2, -0.42, 0.0))
            tip_dir = Vector((math.sin(a), -math.cos(a), 0.0))
            c = base + tip_dir * ln * 0.55
            T = F @ Matrix.Translation((c.x, c.y, h * 0.42)) @ Matrix.Rotation(a, 4, 'Z') @ M(rot=(97, 0, 0))
            slab("toes", (w, h, ln), T, top=(0.72, 0.62), shift=(0, -0.06), chips=1)
        slab("joints", (0.92, 0.92, 0.6), M((x, fy + 0.1, 0.86)), core, rock=8, chips=0)
        # the shin: a calf mass wide under the knee, narrowing to the ankle, with two broken front plates and
        # an outer slab; a rune band glows in the gap between the plates
        S = M((x * 1.02, fy + 0.06, 1.42), rot=(4, 0, -3 * sx))
        shin = slab("shins", (1.04, 1.06, 1.3), S, top=(1.3, 1.26), rock=4, rock_depth=(0.9, 0.98), chips=0, keep=True)
        slab("shins", (0.96, 0.3, 0.62), S @ M((0.04 * sx, -0.66, 0.33), rot=(-9, 4 * sx, 5 * sx)), top=(1.0, 0.8), bottom=(0.84, 1.0))
        slab("shins", (0.74, 0.28, 0.42), S @ M((-0.03 * sx, -0.54, -0.44), rot=(7, -5 * sx, -6 * sx)), top=(0.86, 0.9))
        slab("shins", (0.3, 0.92, 0.7), S @ M((0.66 * sx, 0.05, 0.36), rot=(0, 9 * sx, 0)), top=(0.8, 0.85))
        slab("joints", (0.95, 0.95, 0.66), M((x * 1.02, fy, 2.14)), core, rock=8, chips=0)
        # the knee: a big faceted boulder
        slab("knees", (0.92, 0.66, 0.82), M((x * 1.03, fy - 0.56, 2.12), rot=(12, 0, -8 * sx)), rock=12,
             rock_depth=(0.8, 0.95), chips=1)
        # the thigh: a mass broad at the hip and tapering to the knee, an outer slab and a front slab
        Th = M((x * 0.96, fy * 0.5 + 0.08, 2.9), rot=(-9, 0, 4 * sx))
        thigh = slab("thighs", (1.0, 1.04, 1.25), Th, top=(1.38, 1.3), rock=4, rock_depth=(0.9, 0.98), chips=0, keep=True)
        slab("thighs", (0.34, 1.12, 0.9), Th @ M((0.72 * sx, 0.05, 0.2), rot=(0, -12 * sx, 4)), top=(0.75, 0.86), bottom=(1.0, 0.9))
        slab("thighs", (0.98, 0.32, 0.72), Th @ M((-0.06 * sx, -0.72, 0.18), rot=(-11, 0, -4 * sx)), top=(1.0, 0.85), bottom=(0.78, 1.0))
        legs.append((shin, S, -0.1, thigh, Th, -0.34, x, fy, sx))
        # roots: one winds round the ankle into the ground, one hangs over the outside of the knee
        a0 = math.radians(-60 if sx < 0 else 240)
        pts = []
        for i in range(7):
            t = i / 6
            ang = a0 + sx * t * 4.4
            rad = 0.47 + 0.18 * t
            pts.append(Vector((x + math.cos(ang) * rad, fy + 0.1 + math.sin(ang) * rad, 1.12 - 0.6 * t)))
        pts.append(pts[-1] + Vector((math.cos(ang), math.sin(ang), 0)) * 0.35 + Vector((0, 0, -0.45)))
        pts[-1].z = 0.02
        root(pts, 0.085, 0.03)
        root([Vector((x + 0.5 * sx, fy - 0.15, 2.62)), Vector((x + 0.68 * sx, fy - 0.3, 2.3)),
              Vector((x + 0.66 * sx, fy - 0.42, 2.0)), Vector((x + 0.58 * sx, fy - 0.38, 1.78))], 0.07, 0.02)
        # moss cushions in the joints
        moss_tuft((x + 0.05 * sx, fy - 0.3, 0.8), 0.42, 60 + sx, up=(0, -0.4, 1))
        moss_tuft((x - 0.3 * sx, fy - 0.25, 2.42), 0.36, 64 + sx, up=(0, -0.5, 1))
        moss_tuft((x + 0.55 * sx, fy + 0.05, 2.18), 0.3, 68 + sx, up=(sx, 0, 0.6))
        moss_tuft((x + 0.4 * sx, fy + 0.1, 3.45), 0.34, 72 + sx)

    # ---- hips and waist: a heavy pelvis, a narrow dark core with one belly stone in front ------------------
    pelvis = block("pelvis", (2.1, 1.5, 0.85), M((0, 0.12, 3.6)), bottom=(0.78, 0.86), keep=True)
    for sx in (-1, 1):
        block("pelvis", (0.7, 1.2, 0.85), M((1.22 * sx, 0.14, 3.42), rot=(0, -8 * sx, 0)), bottom=(0.78, 0.9))
    block("joints", (1.3, 1.05, 1.2), M((0, 0.15, 4.35)), core)
    block("belly", (1.3, 0.6, 0.78), L @ M((0, -0.5, 4.4), rot=(3, 0, 0)), top=(1.08, 0.92), bottom=(0.78, 1.0),
          extra=ridge((0, -1, 0), 0.29, (0, 0, 1), 12))

    # ---- chest: a slab broad at the top and narrow at the waist, two angular pectoral plates ----------------
    chest = block("chest", (3.8, 2.3, 2.65), L @ M((0, 0.1, 6.05)), top=(1.0, 1.0), bottom=(0.55, 0.76), keep=True)
    pecs = []
    for sx in (-1, 1):
        pecs.append(block("pecs", (1.62, 0.42, 1.26), L @ M((0.86 * sx, -1.13, 6.26), rot=(-4, 0, -12 * sx)),
                          top=(1.0, 0.86), bottom=(0.68, 1.0), shift=(0.08 * sx, 0.0), chamfer=(0.03, 0.08),
                          corner=(0.0, 0.3), facets=1, tilt=(9.0, 15.0), extra=ridge((0, -1, 0), 0.2, (1, 0, 0), 13), keep=True))
    block("chest", (1.7, 0.42, 0.6), L @ M((0, -1.02, 5.3), rot=(8, 0, 0)), top=(1.0, 0.9), bottom=(0.8, 1.0))
    hump = block("back", (3.1, 2.0, 1.95), L @ M((0, 1.0, 7.7), rot=(-14, 0, 0)), top=(0.62, 0.55), shift=(0, 0.1), rock=8, rock_depth=(0.86, 0.97), keep=True)

    # ---- shoulders: two big faceted boulders riding higher than the head ---------------------------------------
    boulders = []
    for sx in (-1, 1):
        boulders.append(block("shoulders", (2.3, 2.25, 2.05), L @ M((2.22 * sx, 0.15, 7.3)), rock=18,
                              chamfer=(0.02, 0.05), keep=True))

    # ---- head: a small low block sunk between the shoulders: a heavy brow whose top slopes back into the hump, a
    # dark gap below it with two narrow eye slots glowing in a frown, and a mask-like jaw plate; no mouth ---------
    H = L @ M((0, -1.32, 7.12), scale=0.9)
    block("head", (1.0, 0.8, 0.9), H @ M((0, 0.14, 0.0)), core)
    frown = [((0.12 * sx, 0.0, -0.31), (0.32 * sx, 0.0, -1.0)) for sx in (-1, 1)]
    frown += [((0.0, 0.0, 0.31), (0.38 * sx, 0.0, 1.0)) for sx in (-1, 1)]          # a ridge along the top
    block("brow", (1.3, 1.05, 0.62), H @ M((0, -0.05, 0.36)), top=(0.78, 0.5), shift=(0, 0.24), extra=frown,
          facets=0, corner=(0.02, 0.1), chamfer=(0.03, 0.07))
    for sx in (-1, 1):
        visor = hewn((0.36, 0.1, 0.075), seed=5 + sx, chamfer=(0.05, 0.1), corner=(0.1, 0.25), facets=0)
        add("visor", visor, glow, H @ M((0.26 * sx, -0.42, 0.06), rot=(0, -17.7 * sx, 8 * sx)))
    prow = [((0.0, -0.45, 0.0), (0.32 * sx, -1.0, 0.0)) for sx in (-1, 1)]
    block("head", (1.06, 0.9, 0.62), H @ M((0, -0.05, -0.33)), top=(1.0, 1.0), bottom=(0.66, 0.84), facets=1, extra=prow,
          corner=(0.02, 0.12), chamfer=(0.03, 0.07))

    # ---- arms: long and heavy, angled a little out from the body, huge fists at knee height --------------------
    forearms, uppers = [], []
    for sx in (-1, 1):
        S = lean((2.42 * sx, 0.0, 6.8))
        block("joints", (1.0, 1.0, 1.0), Matrix.Translation(S), core, rock=10)
        ay = -0.25 if sx < 0 else 0.12
        E = Vector((2.78 * sx, S.y - 0.05 + ay, 4.7))
        m, ln = frame(E + Vector((0, 0, 0.1)), S + Vector((0.05 * sx, 0, -0.15)), (sx, 0, 0))
        uppers.append((block("upper arms", (1.15, 1.2, ln), m, top=(1.1, 1.05), bottom=(0.86, 0.86), rock=5,
                             rock_depth=(0.88, 0.98), keep=True), m, ln, sx))
        block("joints", (0.85, 0.85, 0.75), Matrix.Translation(E), core, rock=8)
        W = Vector((2.92 * sx, E.y - 0.25, 2.72))
        m, ln = frame(W, E - Vector((0, 0, 0.12)), (sx, 0, 0))
        forearms.append((block("forearms", (1.42, 1.48, ln), m, top=(0.78, 0.8), bottom=(1.0, 1.0), rock=5, rock_depth=(0.88, 0.98),
                               extra=ridge((1, 0, 0), 0.63, (0, 0, 1), 12), keep=True), m, ln, sx))
        block("elbows", (0.6, 0.45, 0.66), Matrix.Translation(E + Vector((0.08 * sx, 0.48, 0.0))) @ M(rot=(-10, 0, 0)), top=(0.8, 0.7))
        block("joints", (0.8, 0.8, 0.6), Matrix.Translation(W + Vector((0, 0, -0.1))), core, rock=8)
        # the fist: the back of the hand, a row of knuckles underneath, the curled fingers on the palm side, a thumb
        Fz = M((2.96 * sx, W.y - 0.05, 1.97), rot=(0, 0, -6 * sx))
        block("fists", (1.2, 1.45, 1.0), Fz @ M((0.05 * sx, 0, 0.24)), top=(0.88, 0.84), bottom=(1.0, 1.0))
        for k, yk in enumerate((-0.52, -0.17, 0.18, 0.52)):
            drop = (0.0, 0.06, 0.04, -0.03)[k]
            block("fists", (0.95, 0.32, 0.55), Fz @ M((0.08 * sx, yk, -0.4 - drop), rot=(0, 6 * sx, 0)), top=(1.0, 1.0), bottom=(0.9, 0.8))
            block("fists", (0.5, 0.3, 0.45), Fz @ M((-0.5 * sx, yk, -0.2 - drop * 0.5), rot=(0, -10 * sx, 0)), top=(0.85, 1.0))
        block("fists", (0.45, 0.48, 0.8), Fz @ M((-0.26 * sx, -0.82, 0.0), rot=(18, 0, 14 * sx)), top=(0.8, 0.8))

    # ---- rune cracks: a glowing seam down the chest, a branching crack over one pectoral, one up each forearm --
    def crack(surf, pts2d, origin_of, direction, width=0.045):
        pts, nrms = [], []
        for u, v in pts2d:
            p, n = surf.hit(origin_of(u, v), direction)
            pts.append(p)
            nrms.append(n)
        add("rune rims", ribbon(pts, nrms, width * 2.8, 0.008), scorch, crease=None)
        add("runes", ribbon(pts, nrms, width, 0.022), glow, crease=None)

    fwd = L.to_3x3() @ Vector((0, 1, 0))
    left, right = pecs
    crack(left, [(-0.44, -0.26), (-0.42, -0.08), (-0.47, 0.12), (-0.62, 0.22), (-0.72, 0.45)], lambda u, v: lean((u, -3.0, 6.16 + v)), fwd)
    crack(left, [(-0.47, 0.12), (-0.57, -0.02), (-0.74, -0.1)], lambda u, v: lean((u, -3.0, 6.16 + v)), fwd, width=0.035)
    crack(right, [(0.55, 0.6), (0.5, 0.42), (0.62, 0.25)], lambda u, v: lean((u, -3.0, 6.16 + v)), fwd, width=0.035)
    crack(chest, [(0.0, 0.62), (0.02, 0.3), (-0.02, 0.0), (0.03, -0.32), (0.0, -0.55)], lambda u, v: lean((u, -3.0, 6.15 + v)), fwd, width=0.05)
    for surf, m, ln, sx in forearms:
        path = [(0.1, -0.2), (-0.05, -0.04), (0.06, 0.12), (-0.08, 0.26), (0.02, 0.4)]
        out = m.to_3x3() @ Vector((1, 0, 0))
        crack(surf, path, lambda u, v, m=m: m @ Vector((3.0, u, v * ln)), -out)

    # ---- carvings: worn grooves cut by whoever built it: bands round the wrists, chevrons on the upper arms and
    # shins, a zigzag along the belt ------------------------------------------------------------------------------
    def carve(surf, pts2d, origin_of, direction, width=0.05):
        pts, nrms = [], []
        for u, v in pts2d:
            q, n = surf.hit(origin_of(u, v), direction)
            pts.append(q)
            nrms.append(n)
        add("carvings", ribbon(pts, nrms, width, 0.01), carved, crease=None)

    def band(surf, m, h, width=0.055, n=36):
        pts, nrms = [], []
        axis = m @ Vector((0, 0, h))
        for k in range(n):
            a = 2 * math.pi * k / n
            o = m @ Vector((3.0 * math.cos(a), 3.0 * math.sin(a), h))
            q, nn = surf.hit(o, axis - o)
            pts.append(q)
            nrms.append(nn)
        add("carvings", ribbon(pts, nrms, width, 0.014, closed=True), carved, crease=None)

    def rune_band(surf, m, h, width=0.15, n=40, glyphs=9, seed=0):
        """A broad dark band carved round a limb with a row of runes in it glowing faintly emerald:
        slanted strokes and short upright ticks, so it reads as a lit ring from far away."""
        r = random.Random(seed)
        axis = m @ Vector((0, 0, h))

        def on(a, dh):
            for hh in (h + dh, h + dh * 0.5, h, h + 0.06, h - 0.06):
                o = m @ Vector((3.0 * math.cos(a), 3.0 * math.sin(a), hh))
                try:
                    return surf.hit(o, (m @ Vector((0, 0, hh))) - o)
                except ValueError:
                    continue
            raise ValueError("rune band off the stone")

        pts, nrms = zip(*(on(2 * math.pi * k / n, 0.0) for k in range(n)))
        add("carvings", ribbon(pts, nrms, width, 0.012, closed=True), carved, crease=None)
        step = 2 * math.pi / glyphs
        a_off = r.uniform(0, step)
        for g_ in range(glyphs):
            a0 = a_off + g_ * step
            sl = r.choice((-1, 1)) * width * 0.22
            stroke = [on(a0 + step * t, sl * (2 * t / 0.5 - 1)) for t in (0.0, 0.25, 0.5)]
            add("runes", ribbon([p for p, _ in stroke], [q for _, q in stroke], 0.045, 0.026, sink=0.004), glow, crease=None)
            tick = [on(a0 + step * 0.74, dh) for dh in (-width * 0.3, 0.0, width * 0.3)]
            add("runes", ribbon([p for p, _ in tick], [q for _, q in tick], 0.04, 0.026, sink=0.004), glow, crease=None)

    for surf, m, ln, sx in forearms:
        rune_band(surf, m, -ln / 2 + 0.24, seed=3 + sx)
    for surf, m, ln, sx in uppers:
        out = m.to_3x3() @ Vector((1, 0, 0))
        for dv in (0.12, -0.12):
            carve(surf, [(-0.32, dv + 0.18), (0.0, dv - 0.06), (0.32, dv + 0.18)], lambda u, v, m=m: m @ Vector((3.0, u, v)), -out)
    for shin, S, hs, thigh, Th, ht, x, fy, sx in legs:
        rune_band(shin, S, hs, width=0.14, seed=7 + sx)
        rune_band(thigh, Th, ht, width=0.14, seed=9 + sx)
    zig = [(-0.75 + 0.15 * k, 3.62 + (0.07 if k % 2 else -0.07)) for k in range(11)]
    carve(pelvis, zig, lambda u, v: Vector((u, -3.0, v)), (0, 1, 0), width=0.045)

    # ---- emerald crystals: clusters on the shoulders, the back and the left forearm --------------------------
    def cluster(surf, centre, direction, length, count, seed, spread=30.0, leaks=3):
        """Crystals growing out of the shape `surf` where a ray from inside it at `centre` along
        `direction` comes out: one long one and the rest shorter and splayed round it."""
        rnd = random.Random(seed)
        d = Vector(direction).normalized()
        p, nrm = surf.hit(Vector(centre) + d * 4.0, -d)
        side = d.orthogonal().normalized()
        for k in range(count):
            if k == 0:
                ln, off, tilt = length, Vector(), 0.0
            else:
                ln = length * rnd.uniform(0.38, 0.72)
                ang = 2 * math.pi * k / (count - 1) + rnd.uniform(-0.4, 0.4)
                off = Matrix.Rotation(ang, 3, d) @ side * length * rnd.uniform(0.12, 0.22)
                tilt = rnd.uniform(0.5, 1.0) * spread
            axis = Matrix.Rotation(math.radians(tilt), 3, d.cross(off).normalized()) @ d if off.length else d
            for f in (1.0, 0.6, 0.3, 0.0):
                try:
                    q, qn = surf.hit(p + off * f + d * 1.5, -d)
                    break
                except ValueError:
                    continue
            r = ln * rnd.uniform(0.15, 0.19)
            at = aim(q, axis, rnd.uniform(0, 60))
            if ln > 0.32:
                facets, heart = lit_crystal(ln, r, seed=seed * 31 + k, slit=max(0.02, r * 0.1))
                add("crystals", facets, gem, at, crease=None)
                add("crystal cores", heart, glow, at)
            else:
                add("crystals", crystal(ln, r, seed=seed * 31 + k), gem, at)
        # light leaking out of the stone round the foot of the cluster: a jagged glowing fissure, and a few
        # glowing cracks running out from it
        rim = []
        e1 = side
        e2 = d.cross(e1).normalized()
        reach = length * 0.42
        for k in range(14):
            a = 2 * math.pi * k / 14 + rnd.uniform(-0.12, 0.12)
            rr = reach * (1.0 if k % 2 == 0 else rnd.uniform(0.45, 0.65))
            rim.append(surf.hit(p + (e1 * math.cos(a) + e2 * math.sin(a)) * rr + d * 1.5, -d))
        pool = bmesh.new()
        mid = pool.verts.new(p + nrm * 0.03)
        ring = [pool.verts.new(q + qn * 0.018) for q, qn in rim]
        for k in range(len(ring)):
            pool.faces.new((mid, ring[k], ring[(k + 1) % len(ring)]))
        bmesh.ops.recalc_face_normals(pool, faces=pool.faces[:])
        pool.normal_update()
        if sum((f.normal for f in pool.faces), Vector()).dot(nrm) < 0:
            bmesh.ops.reverse_faces(pool, faces=pool.faces[:])
        add("crystal glow", pool, glow, crease=None)
        for k in range(leaks):
            a = 2 * math.pi * (k + rnd.uniform(-0.2, 0.2)) / leaks
            dirv = e1 * math.cos(a) + e2 * math.sin(a)
            perp = d.cross(dirv).normalized()
            path = [p + dirv * reach * t + perp * rnd.uniform(-0.08, 0.08) * t + d * 1.5 for t in (0.8, 1.3, 1.8, 2.3)]
            try:
                hits = [surf.hit(o, -d) for o in path]
            except ValueError:
                continue
            add("rune rims", ribbon([h_[0] for h_ in hits], [h_[1] for h_ in hits], 0.11, 0.008), scorch, crease=None)
            add("runes", ribbon([h_[0] for h_ in hits], [h_[1] for h_ in hits], 0.04, 0.022), glow, crease=None)

    for sx, surf, ln, n in ((-1, boulders[0], 2.15, 6), (1, boulders[1], 1.6, 5)):
        cluster(surf, lean((2.22 * sx, 0.15, 7.3)), (0.62 * sx, 0.22, 1.0), ln, n, 11 + sx)
    hc = lean((0, 1.0, 7.7))
    cluster(hump, hc + Vector((-0.35, 0.0, 0.0)), (-0.2, 1.05, 1.0), 1.85, 6, 21)
    cluster(hump, hc + Vector((0.75, 0.0, -0.2)), (0.7, 1.0, 0.45), 1.15, 4, 23)
    surf, m, ln, sx = forearms[0]
    cluster(surf, m @ Vector((0, 0, 0.1 * ln)), (-1.0, 0.75, 0.35), 0.72, 3, 31, spread=25, leaks=0)

    g.build()
    for ob in g.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return g


def bake(golem, texture):
    """Everything that does not glow becomes one textured mesh, Golem_Body: the stone and crystal
    colours and the shading in the gaps between the blocks are baked into its colour image. The
    glowing parts are joined into one mesh, Golem_GLOW, that keeps its emissive material."""
    glow = [ob for ob in golem.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in golem.objects if ob not in glow], texture, name="Golem_Body",
                            shade=0.72, soften=2, rough=0.9, samples=32, uv_angle=70.0, uv_margin=0.004, pack_margin=0.003)
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    gl = bpy.context.view_layer.objects.active
    gl.name = gl.data.name = "Golem_GLOW"
    golem.objects = [body, gl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the head and chest to this PNG")
    ap.add_argument("--peek", help="quick look while building: write these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,side,game distance:silhouette",
                    help="views for --quick and --peek, each 'view' or 'view:look'")
    ap.add_argument("--look", default="clay")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: four views instead of eight")
    ap.add_argument("--title", default="Golem review")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "golem_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    golem = build()
    print("triangles by part:", dict(sorted(golem.tally.items(), key=lambda kv: -kv[1])))
    L = Matrix.Translation(PIVOT) @ Matrix.Rotation(math.radians(LEAN), 4, 'X') @ Matrix.Translation(-PIVOT)
    head = L @ Vector((0, -1.32, 7.0))

    def shots(default_look):
        out = []
        for v in a.views.split(","):
            view, _, look = v.strip().partition(":")
            out.append((view.strip(), look.strip() or default_look))
        return out

    def rig_for(samples):
        import review
        rig = review.Rig(golem, samples=samples, focus=(head.x, head.y + 0.4, head.z - 1.0))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.55, -1.0, 0.18)).normalized() * 9.0,
                                          head + Vector((0, 0.3, -0.35)), 30)
        rig.cams["legs"] = review._camera("C_legs", Vector((0, 0, 1.7)) + Vector((-0.42, -1.0, 0.2)).normalized() * 12.5,
                                          Vector((0, 0, 1.7)), 34)
        cc = L @ Vector((0, 0.6, 7.9))
        rig.cams["crystals"] = review._camera("C_crys", cc + Vector((-0.5, -1.0, 0.55)).normalized() * 8.0, cc, 34)
        return rig, review

    if a.peek:
        rig, _ = rig_for(16)
        rig.sheet(os.path.abspath(a.peek), shots(a.look), px=a.px, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(golem, os.path.abspath(a.texture))
    tris = golem.triangles()
    lo, hi = golem.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = golem.objects[0].data
    uv = me.uv_layers.active.data
    a3 = sum(pl.area for pl in me.polygons)
    a2 = 0.0
    for pl in me.polygons:
        pts = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    print("texture: %.0f%% of the image used, about %.0f pixels to a stud" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(golem.objects, os.path.abspath(a.export))
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
