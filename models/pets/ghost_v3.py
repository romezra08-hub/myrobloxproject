"""Ghost pet: a sweet little sheet ghost, remade from the game's original. Built from scratch by script.

    python models/pets/ghost.py --review out/ghost.png      # render the review sheet
    python models/pets/ghost.py --export models/export/ghost.fbx

The original is a white sheet-ghost blob with huge bulging purple-ringed eyes and a small open
mouth; the bulging eyes made it creepy. The remake keeps the white sheet, the side arm nubs, the
purple around the eyes and the small open mouth, and makes it sweet. Must-haves:
  1. A soft white body, slightly translucent-looking (cool lavender in the shadows, lighter at the
     thin hem), with a gently flowing wavy hem, floating a little above the ground.
  2. Small rounded arm nubs.
  3. Small calm eyes, dark with a soft lavender glow low in them and a highlight.
  4. A tiny smile.
  5. A faint lavender glow inside the hem; matte painted texture with baked crease shading.

Round 3: bigger mitten-shaped arm nubs that stand clear of the body (they read as doorknobs from
the side), the left one waving; soft folds running down into the hem lobes so the sheet is cloth,
not a smooth plastic shell; the motes a softer lavender.

Round 2: a rounder head with a soft little peak swept back on top (it was a flat-topped box); a
livelier hem with uneven lobes that trails further back; smaller arm nubs further forward, the left one
raised in a wave; a stronger lavender cast down the body so the white is less flat.

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

NAME = "Ghost"
LAYERS = ("hem", "inner")


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


# ---- the body: one profile turned round the Z axis, outside down to the hem lip and back up inside --

# (radius, height) from the top of the head, down the outside, round the lip of the hem and up the inside.
PROFILE = [(0.001, 3.26), (0.36, 3.23), (0.7, 3.1), (0.98, 2.88), (1.15, 2.58), (1.23, 2.22), (1.22, 1.86),
           (1.19, 1.55), (1.23, 1.25), (1.33, 0.96), (1.47, 0.72), (1.6, 0.54), (1.62, 0.47), (1.57, 0.43), (1.48, 0.46),
           (1.37, 0.6), (1.22, 0.9), (1.03, 1.22), (0.68, 1.45), (0.001, 1.52)]
INNER_FROM = 14           # profile points from here on are the inside of the sheet
LOBES = 5
FLOAT = 0.34              # the lowest point of the hem is this far above the ground


def body_mesh(rings=46, segs=56):
    bm = bmesh.new()
    lh, li = layers(bm)
    k = len(PROFILE) - 1
    prof = []
    for i in range(rings + 1):
        u = i / rings * k
        r = max(_cr([p[0] for p in PROFILE], u), 0.001)
        z = _cr([p[1] for p in PROFILE], u)
        inner = u > INNER_FROM - 0.5
        prof.append((r, z, inner, u))
    loops = []
    for r, z, inner, u in prof:
        w = smooth(z, 1.38 if inner else 1.45, 0.47) ** 1.4            # 1 at the hem lip, 0 up the body
        ring = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            back = 0.5 - 0.5 * math.cos(th)                           # 0 at the front, 1 at the back
            wave = math.cos(LOBES * th + 0.35 + 0.25 * math.sin(2 * th))
            lobe = 0.5 + 0.5 * wave
            A = (0.2 + 0.16 * back) * (1 + 0.28 * math.sin(2 * th + 1.1))
            fold = smooth(z, 2.1, 0.9) * (0.0 if inner else 1.0)
            rr = r * (1 + 0.055 * w * wave + 0.022 * fold * math.cos(2 * LOBES * th + 0.35 + 1.3 * z))
            zz = z - A * w * lobe ** 1.3
            x = math.sin(th) * rr + 0.06 * w
            y = -math.cos(th) * rr + 0.3 * w ** 1.3                    # the hem trails back as it drifts
            peak = math.exp(-(r / 0.42) ** 2) * (0.0 if inner else 1.0)  # a soft little peak on top, swept back
            zz += 0.2 * peak
            y += 0.24 * peak ** 1.5
            v = bm.verts.new((x, y, zz))
            v[lh], v[li] = w, 1.0 if inner else 0.0
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(segs):
            bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    for ring in (loops[0], loops[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        c[lh], c[li] = ring[0][lh], ring[0][li]
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    lift = FLOAT - min(v.co.z for v in bm.verts)
    bm.transform(M((0, 0, lift)))
    return bm


def hit(bvh, x, z):
    """The front surface at (x, z): its point and normal."""
    loc, nor, _, _ = bvh.ray_cast(Vector((x, -6, z)), Vector((0, 1, 0)))
    return loc, nor


EYE = (0.36, 2.28, 0.105, 0.14)          # x, z of the eye centres; half width and half height
MOUTH = (1.93, 0.085, 0.07)              # z of the top edge; half width and depth
BLUSH = (0.6, 2.02)


def build():
    body_paint = Paint("Sheet")
    body = body_mesh()
    bvh = BVHTree.FromBMesh(body)
    g = Prop(NAME)

    def add(bm, mat, at=None):
        layers(bm)
        g.add(bm, mat, at)

    # ---- painted body ---------------------------------------------------------------------------------
    p = body_paint
    hem, inner = p.attr("hem"), p.attr("inner")
    front = (-p.ny).ss(0.25, 0.7)
    p.base("#F8F7FD")
    p.mix("#E6DFF5", p.z.ss(2.8, 1.0))                               # cool in the lower body
    p.mix("#E9E4F6", (-p.nz).ss(0.0, 0.6) * 0.8)                      # cool shade under the curves
    p.mix("#D6C8F3", hem * 0.85)                                     # lavender light in the thin hem
    p.mix("#F4EEFF", (hem.ss(0.75, 1.0)) * 0.7)                      # the lip itself catches the light
    p.mix("#B69CEB", inner)                                          # the glow inside the sheet
    p.mix("#D8C6FF", inner * hem.ss(0.4, 1.0))
    p.shade(0.97 + 0.06 * p.noise(1.3, detail=3.0))                  # a soft cloudy unevenness
    # blush, mouth
    p.mix("#F7C9DC", ellipse(p, BLUSH[0], BLUSH[1], 0.16, 0.09, soft=0.6) * front * 0.8)
    mz, mw, md = MOUTH
    inside = (((p.x / mw) ** 2 + ((p.z - mz) / md) ** 2).sqrt()).ss(1.08, 0.92) * (p.z).ss(mz + 0.008, mz - 0.008)
    p.mix("#4B2B5C", inside * front)
    tongue = (((p.x / 0.05) ** 2 + ((p.z - mz + md) / 0.04) ** 2).sqrt()).ss(1.1, 0.85)
    p.mix("#EE8DB2", tongue * inside * front)
    # a faint lavender ring round each eye, where the original's purple rings were
    ex, ez, ew, eh = EYE
    ring = ellipse(p, ex, ez, ew * 1.55, eh * 1.4, soft=0.35) - ellipse(p, ex, ez, ew * 1.05, eh * 1.05, soft=0.1)
    p.mix("#D9C9F7", ring.clamp() * front * 0.6)
    add(body, p.done())

    # ---- arm nubs -------------------------------------------------------------------------------------
    armp = Paint("Arm")
    armp.base("#F8F7FD").mix("#E6DFF5", armp.z.ss(2.0, 1.2)).shade(0.97 + 0.06 * armp.noise(1.3, detail=3.0))
    armm = armp.done()
    for s, at, tilt in ((-1, (-1.3, -0.26, 1.86), -40), (1, (1.27, -0.2, 1.6), 26)):
        nub = kit.tube([(0, 0, 0), (0.28, 0, 0.0), (0.5, 0, 0.02), (0.6, 0, 0.03)], [0.25, 0.23, 0.17, 0.02], segs=14, rings=12, flat=0.78)
        for v in nub.verts:                                          # mitten: rounder towards the tip
            t = min(max(v.co.x / 0.6, 0), 1)
            v.co.z += 0.03 * math.sin(math.pi * t)
        nub.transform(M((0, 0, 0), rot=(0, 0, 180)) if s < 0 else M())
        add(nub, armm, M(at, rot=(0, tilt * s, s * -24)))

    # ---- eyes: small dark lenses with lavender light low in them and a highlight ------------------------
    ep = Paint("Eye", rough=0.4)
    ep.base("#1D1630").mix("#3A2A63", ep.z.ss(ez + 0.05, ez - 0.06)).mix("#A88AF0", ep.z.ss(ez - 0.04, ez - 0.13) * 0.9)
    eyem = ep.done()
    white = kit.material("Shine", "#FFFFFF", rough=0.3)
    for s in (-1, 1):
        loc, nor = hit(bvh, s * ex, ez)
        lens = kit.ball((ew * 2, eh * 2, 0.08), cuts=4)
        add(place(lens, loc + nor * (0.025 - 0.04), nor), eyem)
        for dx, dz, r in ((-0.035, 0.05, 0.035), (0.04, -0.045, 0.016)):
            l2, n2 = hit(bvh, s * ex + dx, ez + dz)
            add(kit.ball((r * 2, r * 2, r * 1.2), cuts=2), white, M(l2 + n2 * 0.03))

    # ---- glow: a few lavender motes drifting under the hem; the lowest touches the ground ---------------
    glow = kit.material("GLOW_Lavender", "#A98BF5", rough=0.4, emit=1.6)
    for x, y, z, r in ((0.1, 0.25, 0.08, 0.08), (-0.45, 0.55, 0.22, 0.05), (0.52, 0.05, 0.18, 0.04)):
        add(kit.ball((r * 2,) * 3, cuts=2), glow, M((x, y, z)))

    g.build()
    for ob in g.objects:
        print("  %-22s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return g


def bake(g, texture, samples=48):
    """Everything that does not glow becomes Ghost_Body with its colours and crease shading baked into one
    image; the motes stay Ghost_GLOW with their emissive material."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow], texture, name=NAME + "_Body", shade=0.45,
                            soften=3, rough=0.85, samples=samples, uv_angle=70.0, uv_margin=0.004, pack_margin=0.003)
    for ob in glow:
        ob.name = ob.data.name = NAME + "_GLOW"
    g.objects = [body] + glow


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
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "ghost_colour.png"))
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
        face = Vector((0, -1.2, EYE[1] - 0.15))
        for name, d, dist in (("face", (-0.5, -1.0, 0.15), 3.6), ("face front", (0, -1.0, 0.05), 3.4)):
            rig.cams[name] = review._camera("C_" + name.replace(" ", ""), face + Vector(d).normalized() * dist, face, 30)
        if a.quick:
            shots = [(v.strip(), "full") for v in a.views.split(",")]
        else:
            shots = review.STANDARD
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols if a.quick else 4, title="Ghost review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
