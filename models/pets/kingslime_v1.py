"""King Slime pet: a regal golden honey slime, remade from the game's original. Built from scratch by script.

    python models/pets/kingslime.py --review out/kingslime.png      # render the review sheet
    python models/pets/kingslime.py --export models/export/kingslime.fbx

The original is a yellow dome blob in a gold crown with staring cartoon eyes and a drooling base.
The remake keeps the yellow-gold dome, the gold crown and the drippy base, and gives it a calm,
pleased face. Must-haves:
  1. An amber-gold jelly dome that looks glossy (the shine is painted, the texture is matte), with a
     slightly drippy base: a few runs of honey sliding down to a puddled skirt.
  2. A few tiny bubbles and gems trapped inside.
  3. A proper little gold crown with gems, worn at a slight tilt.
  4. A cheerful, confident face: half-lidded content eyes and a small smile.
  5. Matte painted texture with baked crease shading; Body under 8k triangles.

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
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402

NAME = "KingSlime"
LAYERS = ()


def smooth(x, a, b):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _cr(vals, t):
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def layers(bm):
    return [bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k) for k in LAYERS]


# ---- a tiny node language: paint colours in the shader from the position, baked into the texture --

class Paint:
    """Builds a material's Base Color from expressions in position, normal and vertex layers."""

    def __init__(self, name, rough=0.9):
        self.mat = bpy.data.materials.new(name)
        self.b = kit.principled(self.mat)
        self.b.inputs["Roughness"].default_value = rough
        self.t = self.mat.node_tree
        co = self.node("ShaderNodeTexCoord")
        xyz = self.node("ShaderNodeSeparateXYZ")
        self.t.links.new(co.outputs["Object"], xyz.inputs[0])
        self.pos = co.outputs["Object"]
        self.x, self.y, self.z = (V(self, xyz.outputs[i]) for i in range(3))
        geo = self.node("ShaderNodeNewGeometry")
        nxyz = self.node("ShaderNodeSeparateXYZ")
        self.t.links.new(geo.outputs["Normal"], nxyz.inputs[0])
        self.nx, self.ny, self.nz = (V(self, nxyz.outputs[i]) for i in range(3))
        self.col = None

    def node(self, kind):
        return self.t.nodes.new(kind)

    def attr(self, name):
        a = self.node("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return V(self, a.outputs["Fac"])

    def noise(self, scale, detail=2.0, rough=0.5, offset=(0, 0, 0), stretch=(1, 1, 1)):
        m = self.node("ShaderNodeMapping")
        m.inputs["Location"].default_value = offset
        m.inputs["Scale"].default_value = tuple(scale * s for s in stretch)
        self.t.links.new(self.pos, m.inputs["Vector"])
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = 1.0, detail
        n.inputs["Roughness"].default_value = rough
        self.t.links.new(m.outputs["Vector"], n.inputs["Vector"])
        return V(self, n.outputs["Fac"])

    def base(self, hexcode):
        self.col = (*kit.srgb(hexcode), 1.0)
        return self

    def mix(self, hexcode, fac):
        m = self.node("ShaderNodeMix")
        m.data_type, m.clamp_factor = 'RGBA', True
        _feed(self, m.inputs[0], fac)
        _feed(self, m.inputs[6], self.col)
        _feed(self, m.inputs[7], (*kit.srgb(hexcode), 1.0) if isinstance(hexcode, str) else hexcode)
        self.col = m.outputs[2]
        return self

    def shade(self, fac):
        """Multiply the colour by a value (brightness)."""
        m = self.node("ShaderNodeMix")
        m.data_type, m.blend_type, m.clamp_factor = 'RGBA', 'MULTIPLY', True
        m.inputs[0].default_value = 1.0
        _feed(self, m.inputs[6], self.col)
        c = self.node("ShaderNodeCombineXYZ")
        for i in range(3):
            _feed(self, c.inputs[i], fac)
        self.t.links.new(c.outputs[0], m.inputs[7])
        self.col = m.outputs[2]
        return self

    def done(self):
        _feed(self, self.b.inputs["Base Color"], self.col)
        self.mat.diffuse_color = (0.8, 0.8, 0.8, 1)
        return self.mat


def _feed(p, sock, v):
    if isinstance(v, V):
        p.t.links.new(v.s, sock)
    elif isinstance(v, bpy.types.NodeSocket):
        p.t.links.new(v, sock)
    else:
        sock.default_value = v


class V:
    """A float socket that does arithmetic by adding Math nodes."""

    def __init__(self, p, s):
        self.p, self.s = p, s

    def op(self, kind, *args):
        n = self.p.node("ShaderNodeMath")
        n.operation = kind
        for i, a in enumerate((self,) + args):
            _feed(self.p, n.inputs[i], a)
        return V(self.p, n.outputs[0])

    def __add__(self, o): return self.op('ADD', o)
    def __radd__(self, o): return self.op('ADD', o)
    def __sub__(self, o): return self.op('SUBTRACT', o)
    def __rsub__(self, o): return V.const(self.p, o).op('SUBTRACT', self)
    def __mul__(self, o): return self.op('MULTIPLY', o)
    def __rmul__(self, o): return self.op('MULTIPLY', o)
    def __truediv__(self, o): return self.op('DIVIDE', o)
    def __neg__(self): return self.op('MULTIPLY', -1.0)
    def __abs__(self): return self.op('ABSOLUTE')
    def __pow__(self, o): return self.op('POWER', o)
    def sqrt(self): return self.op('SQRT')
    def min(self, o): return self.op('MINIMUM', o)
    def max(self, o): return self.op('MAXIMUM', o)
    def clamp(self): return self.op('MAXIMUM', 0.0).op('MINIMUM', 1.0)

    @staticmethod
    def const(p, v):
        n = p.node("ShaderNodeValue")
        n.outputs[0].default_value = v
        return V(p, n.outputs[0])

    def ss(self, a, b):
        """Smoothstep from a to b (either order), clamped 0..1."""
        m = self.p.node("ShaderNodeMapRange")
        m.interpolation_type = 'SMOOTHSTEP'
        m.clamp = True
        m.inputs["From Min"].default_value, m.inputs["From Max"].default_value = a, b
        self.p.t.links.new(self.s, m.inputs["Value"])
        return V(self.p, m.outputs["Result"])


def ellipse(p, cx, cz, rx, rz, soft=0.08, mirror=True):
    """1 inside an ellipse in the front (x, z) plane, 0 outside, with a soft edge (fraction of radius)."""
    x = abs(p.x) if mirror else p.x
    d = (((x - cx) / rx) ** 2 + ((p.z - cz) / rz) ** 2).sqrt()
    return d.ss(1.0 + soft, 1.0 - soft)


def place(bm, p, n, fwd=(1, 0, 0)):
    """Lay a shape made on +Z onto a surface at p with normal n, its +X towards fwd."""
    from mathutils import Matrix
    z = Vector(n).normalized()
    xa = Vector(fwd)
    xa = (xa - z * xa.dot(z)).normalized()
    m = Matrix((xa, z.cross(xa), z)).transposed().to_4x4()
    m.translation = Vector(p)
    bm.transform(m)
    return bm


def revolve(profile, rings, segs, fn, closed=False, caps=True):
    """Turn a (radius, height) profile round the Z axis. fn(th, r, z, u) gives each point (th = 0 at the
    front, -Y; u from 0 to 1 along the profile)."""
    bm = bmesh.new()
    k = len(profile) - 1
    loops = []
    n = rings if closed else rings + 1
    pts = profile + profile[:3] if closed else profile
    for i in range(n):
        u = i / rings * (k + 1 if closed else k)
        r = max(_cr([p[0] for p in pts], u), 0.001)
        z = _cr([p[1] for p in pts], u)
        loops.append([bm.verts.new(fn(2 * math.pi * j / segs, r, z, i / rings)) for j in range(segs)])
    pairs = list(zip(loops, loops[1:])) + ([(loops[-1], loops[0])] if closed else [])
    for a, b in pairs:
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    if caps and not closed:
        for ring in (loops[0], loops[-1]):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def polar(th, r, z):
    return Vector((math.sin(th) * r, -math.cos(th) * r, z))


def torus(R, r, segs=40, sides=8):
    return revolve([(R + r * math.cos(a), r * math.sin(a)) for a in (2 * math.pi * i / sides for i in range(sides))],
                   sides, segs, lambda th, rr, z, u: polar(th, rr, z), closed=True)


def hit(bvh, x, z):
    loc, nor, _, _ = bvh.ray_cast(Vector((x, -6, z)), Vector((0, 1, 0)))
    return loc, nor


# ---- the jelly ----------------------------------------------------------------------------------------

DOME = [(0.001, 2.42), (0.55, 2.38), (1.0, 2.22), (1.33, 1.94), (1.53, 1.56), (1.61, 1.16), (1.64, 0.8), (1.71, 0.47),
        (1.87, 0.22), (2.03, 0.08), (2.08, 0.03), (2.02, 0.0), (1.2, 0.0), (0.001, 0.0)]
# Runs of honey: angle from the front (degrees), top, height of the drop at the bottom, width.
DRIPS = [(38, 1.45, 0.52, 0.13), (96, 1.75, 0.6, 0.16), (148, 1.3, 0.48, 0.12), (205, 1.62, 0.55, 0.15),
         (262, 1.4, 0.5, 0.13), (318, 1.85, 0.62, 0.15)]


def jelly_point(th, r, z, u):
    skirt = smooth(z, 0.5, 0.04) * (1.0 if u < 0.85 else 0.0)
    r = r * (1 + 0.07 * skirt * (0.6 * math.sin(4 * th + 0.5) + 0.4 * math.sin(7 * th + 2.0)))
    if u < 0.8:
        for deg, top, drop, w in DRIPS:
            d = (th - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi
            fade = smooth(z, top, top - 0.25) * smooth(z, drop - 0.32, drop - 0.12)
            bulb = math.exp(-((z - drop) / 0.13) ** 2)
            width = w * (1 + 0.75 * bulb)
            r += (0.045 + 0.06 * bulb) * fade * math.exp(-((d * r) / width) ** 2)
    return polar(th, r, z)


EYE = (0.43, 1.36, 0.165, 0.19)          # x, z of the eye centres; half width and half height
LID = 0.12                                # the lid line, in eye heights above the centre
MOUTH = (1.08, 0.15, 0.05)               # z of the centre of the smile, half width, depth of its curve
CROWN_AT = ((0.05, 0.05, 2.22), (-7, 9, 0))


def jelly_paint(bvh):
    p = Paint("Jelly")
    front = (-p.ny).ss(0.2, 0.65)
    p.base("#E48B0E")
    p.mix("#F6A51C", p.nz.ss(-0.2, 0.5))                              # lighter as it faces up
    p.mix("#FFC845", p.nz.ss(0.45, 0.95))
    glow = p.z.ss(0.15, 0.65) * p.z.ss(1.7, 0.9)                      # light passing through the middle
    p.mix("#FFB62E", glow * 0.45)
    p.mix("#FFD064", p.z.ss(0.2, 0.02) * p.nz.ss(0.3, 0.8) * 0.8)     # the thin puddle is pale honey
    p.mix("#B9580A", (-p.nz).ss(0.2, 0.8))                            # the underside
    p.shade(0.95 + 0.1 * p.noise(2.2, detail=2.0))
    # bubbles and gems caught inside
    for x, z, r in ((-0.98, 0.82, 0.07), (-0.78, 0.6, 0.045), (1.05, 1.62, 0.055), (0.95, 0.5, 0.075),
                    (-0.35, 0.55, 0.05), (0.25, 1.85, 0.04), (-1.2, 1.25, 0.05), (1.3, 0.95, 0.045)):
        inside = ellipse(p, x, z, r, r, soft=0.2, mirror=False)
        rim = (ellipse(p, x, z, r, r, soft=0.1, mirror=False) - ellipse(p, x, z, r * 0.72, r * 0.72, soft=0.2, mirror=False)).clamp()
        shine = ellipse(p, x - r * 0.35, z + r * 0.35, r * 0.25, r * 0.25, soft=0.3, mirror=False)
        p.mix("#FFC75A", inside * front * 0.5).mix("#FFE7A6", rim * front * 0.8).mix("#FFFFFF", shine * front)
    for x, z, rx, rz, col in ((0.72, 0.72, 0.1, 0.13, "#B8233A"), (-0.62, 0.38, 0.08, 0.1, "#2F6FD0"), (1.25, 0.32, 0.07, 0.09, "#2FA866")):
        dia = (abs(p.x - x) / rx + abs(p.z - z) / rz).ss(1.15, 0.85)
        facet = (p.x - x).ss(-0.02, 0.02)
        p.mix(col, dia * front * 0.7).mix("#FFFFFF", dia * front * facet * 0.18)
    # glossy-looking: a soft window of light up on the dome, painted so the texture stays matte
    ld = Vector((-0.45, -0.55, 0.72)).normalized()
    facing = p.nx * ld.x + p.ny * ld.y + p.nz * ld.z
    p.mix("#FFF2C2", facing.ss(0.9, 0.975) * 0.85)
    p.mix("#FFFFFF", facing.ss(0.975, 0.99))
    ld2 = Vector((0.75, -0.55, 0.2)).normalized()
    p.mix("#FFE39A", (p.nx * ld2.x + p.ny * ld2.y + p.nz * ld2.z).ss(0.93, 0.985) * 0.6)
    # face: blush, half-lidded eyes, small smile
    ex, ez, ew, eh = EYE
    p.mix("#FF8F4A", ellipse(p, 0.78, 1.1, 0.17, 0.1, soft=0.6) * front * 0.65)
    u = (abs(p.x) - ex) / ew
    v = (p.z - ez) / eh
    eye = ((u * u + v * v).sqrt()).ss(1.06, 0.94) * front
    below = v.ss(LID + 0.04, LID - 0.04)
    p.mix("#FFF7E6", eye * below)                                     # the white of the eye
    iris = (((u + 0.08) ** 2 + (v + 0.28) ** 2).sqrt()).ss(0.66, 0.58)
    p.mix("#6B3A12", eye * below * iris)
    p.mix("#2A1406", eye * below * (((u + 0.08) ** 2 + (v + 0.3) ** 2).sqrt()).ss(0.4, 0.33))
    p.mix("#FFFFFF", eye * below * (((u + 0.32) ** 2 + (v + 0.05) ** 2).sqrt()).ss(0.16, 0.1))
    p.mix("#D67A10", eye * v.ss(LID - 0.02, LID + 0.06))              # the lid, a little deeper than the body
    lash = (abs(v - LID) - 0.07).ss(0.04, 0.0) * ((u * u + v * v).sqrt()).ss(1.18, 1.02) * front
    p.mix("#3A1A06", lash)
    mz, mw, md = MOUTH
    curve = mz - md * (1 - (p.x / mw) ** 2)
    smile = (abs(p.z - curve)).ss(0.024, 0.012) * abs(p.x).ss(mw + 0.02, mw - 0.01) * front
    p.mix("#3A1A06", smile)
    return p.done()


# ---- the crown ----------------------------------------------------------------------------------------

def gold_paint():
    p = Paint("Gold", rough=0.6)
    p.base("#E3A92E")
    p.mix("#A9680F", (-p.nz).ss(-0.1, 0.6))
    p.mix("#F7D063", p.nz.ss(0.2, 0.8))
    ld = Vector((-0.45, -0.55, 0.72)).normalized()
    p.mix("#FFF4B8", (p.nx * ld.x + p.ny * ld.y + p.nz * ld.z).ss(0.8, 0.97) * 0.8)
    p.shade(0.93 + 0.12 * p.noise(9.0, detail=1.0))
    return p.done()


def gem_paint(name, dark, light):
    p = Paint(name, rough=0.4)
    p.base(dark)
    ld = Vector((-0.45, -0.75, 0.5)).normalized()
    p.mix(light, (p.nx * ld.x + p.ny * ld.y + p.nz * ld.z).ss(0.2, 0.9))
    p.mix("#FFFFFF", (p.nx * ld.x + p.ny * ld.y + p.nz * ld.z).ss(0.9, 0.99) * 0.7)
    return p.done()


def gem(size, depth):
    bm = kit.rounded_box((size[0], size[1], depth), n=2.0, cuts=1)
    for v in bm.verts:
        if v.co.z > depth * 0.2:
            v.co.z = depth * 0.32                                      # a flat table on top
    return bm


def crown_parts():
    """(bmesh, material key) pairs in the crown's own space, its base on z=0, front -Y."""
    parts = []
    band = revolve([(0.53, 0.0), (0.61, 0.0), (0.635, 0.05), (0.66, 0.3), (0.645, 0.34), (0.585, 0.34), (0.555, 0.05)],
                   14, 44, lambda th, r, z, u: polar(th, r, z), closed=True)
    parts.append((band, "gold"))
    for R, z, r in ((0.63, 0.035, 0.045), (0.665, 0.32, 0.038)):
        ring = torus(R, r, segs=44, sides=8)
        ring.transform(M((0, 0, z)))
        parts.append((ring, "gold"))
    for i in range(5):
        th = 2 * math.pi * i / 5
        d = polar(th, 1.0, 0.0)
        spike = kit.tube([d * 0.63 + Vector((0, 0, 0.28)), d * 0.67 + Vector((0, 0, 0.55)), d * 0.7 + Vector((0, 0, 0.74))],
                         [0.14, 0.075, 0.018], segs=10, rings=8, flat=0.42)
        parts.append((spike, "gold"))
        tip = kit.ball((0.13, 0.13, 0.13), cuts=2)
        tip.transform(M(d * 0.705 + Vector((0, 0, 0.79))))
        parts.append((tip, "gold"))
        th2 = th + math.pi / 5                                          # a small point between each pair
        d2 = polar(th2, 1.0, 0.0)
        small = kit.tube([d2 * 0.64 + Vector((0, 0, 0.3)), d2 * 0.66 + Vector((0, 0, 0.46))], [0.08, 0.015], segs=8, rings=4, flat=0.45)
        parts.append((small, "gold"))
    cap = kit.ball((1.06, 1.06, 0.8), cuts=4)
    cap.transform(M((0, 0, 0.2)))
    parts.append((cap, "velvet"))
    orb = kit.ball((0.15, 0.15, 0.15), cuts=2)
    orb.transform(M((0, 0, 0.62)))
    parts.append((orb, "gold"))
    for th, kind, s in ((0.0, "ruby", (0.2, 0.16)), (2 * math.pi / 5, "sapphire", (0.12, 0.12)),
                        (-2 * math.pi / 5, "sapphire", (0.12, 0.12)), (4 * math.pi / 5, "emerald", (0.12, 0.12)),
                        (-4 * math.pi / 5, "emerald", (0.12, 0.12))):
        g = gem(s, 0.09)
        place(g, polar(th, 0.655, 0.17), polar(th, 1.0, 0.0), fwd=polar(th + math.pi / 2, 1.0, 0.0))
        parts.append((g, kind))
    return parts


def build():
    jelly = revolve(DOME, 44, 72, jelly_point)
    bvh = BVHTree.FromBMesh(jelly)
    g = Prop(NAME)
    g.add(jelly, jelly_paint(bvh))
    mats = {"gold": gold_paint(), "ruby": gem_paint("Ruby", "#7A0C22", "#E0304E"),
            "sapphire": gem_paint("Sapphire", "#10286E", "#3E7BE8"), "emerald": gem_paint("Emerald", "#0B4A2A", "#38B870")}
    vp = Paint("Velvet")
    vp.base("#8E1430").mix("#B8213E", vp.nz.ss(0.3, 0.9)).shade(0.9 + 0.2 * vp.noise(14.0, detail=2.0))
    mats["velvet"] = vp.done()
    at = M(*CROWN_AT)
    for bm, key in crown_parts():
        g.add(bm, mats[key], at)
    g.build()
    for ob in g.objects:
        if ob.name.endswith(("Ruby", "Sapphire", "Emerald")):
            ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
            ob.data.update()
        print("  %-22s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return g


def bake(g, texture, samples=48):
    """Everything becomes KingSlime_Body: colours, painted shine and crease shading baked into one image."""
    body = kit.bake_texture(list(g.objects), texture, name=NAME + "_Body", shade=0.5, soften=3, rough=0.8,
                            samples=samples, uv_angle=70.0, uv_margin=0.004, pack_margin=0.003)
    g.objects = [body]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--quick", action="store_true", help="with --review: the round views instead of all eight")
    ap.add_argument("--views", default="front 3/4,front,face,face front,side,back 3/4")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--bake-samples", type=int, default=48)
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "kingslime_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    g = build()
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(g, os.path.abspath(a.texture), a.bake_samples)
    tris = g.triangles()
    lo, hi = g.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(g.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        import review
        rig = review.Rig(g, samples=a.samples)
        face = Vector((0, -1.4, EYE[1] - 0.1))
        for name, d, dist in (("face", (-0.5, -1.0, 0.18), 3.8), ("face front", (0, -1.0, 0.08), 3.5)):
            rig.cams[name] = review._camera("C_" + name.replace(" ", ""), face + Vector(d).normalized() * dist, face, 30)
        shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols if a.quick else 4, title="King Slime review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
