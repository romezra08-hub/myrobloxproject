"""Cloud Spirit pet: a friendly storm-cloud spirit, remade from the game's original. Built from scratch by script.

    python models/pets/cloudspirit.py --review out/cloudspirit.png      # render the review sheet
    python models/pets/cloudspirit.py --export models/export/cloudspirit.fbx

The original is a white fluffy cloud head ringed with grey puffs, with tiny purple eyes, a small red
mouth and white wispy tendrils hanging down like a jellyfish; the grey puffs read as a ring of extra
eyes. The remake keeps the white cloud, the grey puffs round it, the small purple eyes and red mouth
and the hanging white wisps, and makes it a friendly little storm cloud. Must-haves:
  1. A puffy white-to-pale-grey cumulus body with a few billowing puffs (no ring of eye-like domes).
  2. One simple calm face: two eyes only and a small smile.
  3. Soft trailing wisps of mist below, like rain streaks; the lowest touches the ground.
  4. A few small glowing pale-blue raindrops and a tiny lightning spark.
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

NAME = "CloudSpirit"
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


def hit(bvh, x, z):
    loc, nor, _, _ = bvh.ray_cast(Vector((x, -6, z)), Vector((0, 1, 0)))
    return loc, nor


# ---- the cloud: overlapping puffs merged into one surface -------------------------------------------

# (x, y, z, radius) of each puff. The big front puff carries the face.
PUFFS = [(0.0, 0.0, 2.45, 0.98), (-0.25, 0.12, 3.05, 0.72), (0.5, 0.15, 2.95, 0.62), (-0.95, 0.1, 2.35, 0.62),
         (0.98, 0.08, 2.3, 0.6), (0.1, 0.55, 2.6, 0.8), (-0.55, 0.5, 2.85, 0.55)]
# The smaller grey puffs round the waist (angle from the front in degrees, height, radius).
RING = [(48, 1.95, 0.42), (95, 2.0, 0.46), (140, 1.92, 0.44), (185, 2.0, 0.48), (228, 1.94, 0.44), (270, 2.02, 0.46),
        (314, 1.95, 0.42)]
BOTTOM = 1.7              # the cloud's base is flattened below this height


def cloud_mesh(target=4600):
    bm = bmesh.new()
    for x, y, z, r in PUFFS:
        b = kit.ball((2 * r,) * 3, cuts=6)
        b.transform(M((x, y, z)))
        _merge(bm, b)
    for deg, z, r in RING:
        th = math.radians(deg)
        b = kit.ball((2 * r,) * 3, cuts=5)
        b.transform(M((math.sin(th) * 1.08, -math.cos(th) * 1.0 + 0.2, z)))
        _merge(bm, b)
    me = bpy.data.meshes.new("cloud_src")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("cloud_src", me)
    bpy.context.scene.collection.objects.link(ob)
    rm = ob.modifiers.new("remesh", 'REMESH')
    rm.mode, rm.voxel_size = 'VOXEL', 0.04
    sm = ob.modifiers.new("smooth", 'SMOOTH')
    sm.factor, sm.iterations = 0.6, 4
    dg = bpy.context.evaluated_depsgraph_get()
    n = len(ob.evaluated_get(dg).data.polygons)
    dec = ob.modifiers.new("decimate", 'DECIMATE')
    dec.ratio = target / (2.0 * n)
    dg = bpy.context.evaluated_depsgraph_get()
    out = bmesh.new()
    out.from_mesh(ob.evaluated_get(dg).to_mesh())
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    for v in out.verts:                                                  # a flatter base, like a real cumulus
        if v.co.z < BOTTOM:
            v.co.z = BOTTOM - (BOTTOM - v.co.z) * 0.45
    bmesh.ops.triangulate(out, faces=out.faces[:])
    return out


def _merge(bm, other):
    me = bpy.data.meshes.new("tmp")
    other.to_mesh(me)
    other.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


EYE = (0.3, 2.42, 0.085, 0.115)          # x, z of the eye centres; half width and half height
MOUTH = (2.2, 0.075, 0.05)               # z of the top edge; half width and depth
BLUSH = (0.55, 2.2)


def cloud_paint():
    p = Paint("Cloud")
    front = (-p.ny).ss(0.25, 0.7)
    rr = (p.x * p.x + (p.y - 0.15) * (p.y - 0.15)).sqrt()
    p.base("#FFFFFF")
    p.mix("#E9EDF4", p.z.ss(2.9, 2.0))                                    # whiter on top
    p.mix("#C6CEDC", (-p.nz).ss(0.1, 0.8) * 0.9)                          # pale storm grey underneath
    p.mix("#B3BCCC", p.z.ss(1.9, 1.5) * 0.8)
    ring = rr.ss(0.95, 1.2) * p.z.ss(2.5, 2.2)                           # the grey puffs round the waist
    p.mix("#CDD3DE", ring * 0.8)
    p.shade(0.96 + 0.08 * p.noise(2.0, detail=3.0))
    # face
    p.mix("#F7C6D2", ellipse(p, BLUSH[0], BLUSH[1], 0.14, 0.08, soft=0.6) * front * 0.75)
    ex, ez, ew, eh = EYE
    eye = ellipse(p, ex, ez, ew, eh, soft=0.12) * front
    p.mix("#2A2050", eye)
    p.mix("#6F5BC0", eye * p.z.ss(ez - 0.02, ez - 0.1) * 0.85)           # the original's purple, low in the eye
    p.mix("#FFFFFF", ellipse(p, ex - 0.025, ez + 0.04, 0.028, 0.032, soft=0.3) * front)
    p.mix("#FFFFFF", ellipse(p, ex + 0.03, ez - 0.05, 0.012, 0.012, soft=0.3) * front * 0.8)
    mz, mw, md = MOUTH
    inside = (((p.x / mw) ** 2 + ((p.z - mz) / md) ** 2).sqrt()).ss(1.1, 0.9) * (p.z).ss(mz + 0.008, mz - 0.008)
    p.mix("#B8344A", inside * front)
    p.mix("#F0899A", inside * front * (((p.x / 0.045) ** 2 + ((p.z - mz + md) / 0.035) ** 2).sqrt()).ss(1.1, 0.8))
    return p.done()


# ---- mist wisps hanging below, and the glowing raindrops --------------------------------------------

# Each wisp: start (x, y) under the cloud, length, sway, base radius.
WISPS = [(-0.62, -0.25, 1.75, 0.12, 0.11), (-0.22, -0.4, 1.35, -0.08, 0.09), (0.25, -0.3, 1.6, 0.1, 0.1),
         (0.68, -0.15, 1.3, -0.1, 0.09), (-0.85, 0.35, 1.45, 0.09, 0.1), (-0.2, 0.45, 1.85, -0.1, 0.12),
         (0.45, 0.5, 1.55, 0.1, 0.1), (0.95, 0.4, 1.2, -0.07, 0.08)]


def wisp(x, y, length, sway, r0):
    top = BOTTOM + 0.1
    pts, rad = [], []
    for i in range(6):
        t = i / 5
        pts.append((x + sway * math.sin(t * 3.3), y + 0.28 * t ** 1.4, top - length * t))
        rad.append(r0 * (1 - 0.92 * t ** 0.8) + 0.004)
    return kit.tube(pts, rad, segs=8, rings=12)


def mist_paint():
    p = Paint("Mist")
    p.base("#FFFFFF")
    p.mix("#D5E2F0", p.z.ss(1.5, 0.7))
    p.mix("#B4CCE6", p.z.ss(0.8, 0.1))
    p.shade(0.95 + 0.1 * p.noise(6.0, detail=2.0, stretch=(1, 1, 0.15)))
    return p.done()


def drop(r):
    bm = kit.ball((2 * r, 2 * r, 2 * r), cuts=2)
    for v in bm.verts:                                                   # a teardrop, its point up
        if v.co.z > 0:
            k = v.co.z / r
            v.co.x *= 1 - 0.85 * k
            v.co.y *= 1 - 0.85 * k
            v.co.z *= 1 + 0.9 * k
    return bm


def spark(points, r=0.022):
    return kit.tube(points, [r] * len(points), segs=5, rings=(len(points) - 1) * 2)


def build():
    g = Prop(NAME)
    cloud = cloud_mesh()
    g.add(cloud, cloud_paint())
    mist = mist_paint()
    wisps = [wisp(*w) for w in WISPS]
    lowest = min(min(v.co.z for v in w.verts) for w in wisps)
    for w in wisps:                                                      # the lowest wisp tip touches the ground
        g.add(w, mist, M((0, 0, -lowest)))
    glow = kit.material("GLOW_Rain", "#A8DCFF", rough=0.4, emit=2.0)
    for x, y, z, r in ((-0.42, -0.35, 0.95, 0.07), (0.48, -0.25, 0.62, 0.06), (0.05, -0.2, 0.4, 0.055),
                       (-0.75, 0.2, 0.5, 0.05), (0.8, 0.3, 1.05, 0.05)):
        g.add(drop(r), glow, M((x, y, z)))
    g.add(spark([(1.42, -0.1, 2.15), (1.58, -0.12, 1.98), (1.5, -0.12, 1.92), (1.66, -0.14, 1.74)]), glow)
    g.build()
    for ob in g.objects:
        print("  %-22s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return g


def bake(g, texture, samples=48):
    """The cloud and its mist become CloudSpirit_Body with colours and crease shading baked into one image;
    the raindrops and the spark stay CloudSpirit_GLOW with their emissive material."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow], texture, name=NAME + "_Body", shade=0.5,
                            soften=3, rough=0.9, samples=samples, uv_angle=70.0, uv_margin=0.004, pack_margin=0.003)
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
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "cloudspirit_colour.png"))
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
        face = Vector((0, -0.9, EYE[1] - 0.12))
        for name, d, dist in (("face", (-0.5, -1.0, 0.15), 3.4), ("face front", (0, -1.0, 0.05), 3.2)):
            rig.cams[name] = review._camera("C_" + name.replace(" ", ""), face + Vector(d).normalized() * dist, face, 30)
        shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols if a.quick else 4, title="Cloud Spirit review")
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
