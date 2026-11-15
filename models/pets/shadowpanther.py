"""ShadowPanther pet: a sleek black panther, remade from the game's snarling black panther with a red
open mouth and a pink tail tip. Built from scratch by script.

    python models/pets/shadowpanther.py --review out/shadowpanther.png      # render the review sheet
    python models/pets/shadowpanther.py --export models/export/shadowpanther.fbx

Must-haves, checked in every review:
  1. The same creature: a black big cat on four legs with a long tail rising to a bright tip.
  2. Sleek and cool, an adult cat and not a cub: long muscular body mid-stride, broad head held low and
     forward, short rounded ears.
  3. A calm face: gold-green almond eyes under dark lids, mouth closed, no teeth, no snarl.
  4. Dark charcoal fur with faint rosettes that show in the light, a softer grey muzzle.
  5. A small glowing violet flame on the tip of the tail (the original's pink tip) and a violet collar gem.
  6. Matte painted fur with roughness variation; about 3-3.5 studs tall; Body under 12k triangles.

Final: round 7.

Round 7: the sheen widened halfway back and made bluer, so the back, head and legs catch it at game distance (as a thin rim it vanished); a slightly shallower muzzle with wider whisker pads (from the front the long muzzle foreshortened into a round disc).

Round 6: the sheen narrowed to a true rim along the top and the outer legs (spread wide it turned the whole cat purple-grey); the head tipped further down, a broad flat nose bridge and pad, flatter whisker pads set wider and a smaller chin, so the muzzle stops pouting from the front; a smaller, deeper violet collar gem and tail flame.

Round 5: a big cat, not a house cat: a longer, lower body, heavier shoulders and forelegs, a broader, longer muzzle with a nose pad and a strong chin, smaller ears set wider, a thick long tail; a blue-violet sheen painted along the top of the back, head and tail and the outsides of the legs so the form reads on the dark fur (it was a dark blob at game distance); stronger rosettes; a slim dark collar with a glowing violet gem.

Round 4: darker charcoal; a smaller chin and flatter whisker pads (the muzzle pouted from the front), wider cheeks and a broader nose for a big-cat face; a teardrop flame on the tail (it ended in a needle).

Round 3: rosettes drawn in the material with Voronoi rings (as vertex colour they were too coarse to show at all), kept off the face; goldener, slightly smaller eyes, slimmer whisker pads, two whiskers a side; a violet flame tapering to a point on the tail.

Round 2: a panther, not a house cat: heavier chest, shoulders and thighs, thicker legs and bigger paws, a smaller flatter head carried lower with a longer muzzle, small ears set back; darker charcoal with stronger rosettes; a rounder tail-tip flame (it looked like a bulb on a stalk).

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
from mathutils import Matrix, Vector, noise  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402



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


def glossy(bm, value):
    """Mark a shape as smoother than the fur (0 matte, 1 glossy) in the vertex layer 'gloss', which
    rough_map bakes into the roughness image."""
    lay = bm.verts.layers.float.get("gloss") or bm.verts.layers.float.new("gloss")
    for v in bm.verts:
        v[lay] = value
    return bm


def rough_map(body, texture, base, vary=0.1):
    """Replace the kit's plain grey roughness image with a baked one the same size as the colour image:
    `base` roughness, lower where a shape was marked glossy(), broken up by fine and broad noise so the
    surface never reads as one even plastic sheen. Written next to the colour image as <name>_rough.png."""
    import numpy as np
    baked = body.data.materials[0]
    nodes = baked.node_tree.nodes
    def feeding(socket):
        return next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == socket for l in n.outputs[0].links))
    colour_node, rough_node = feeding("Base Color"), feeding("Roughness")
    print("rough_map: colour image", colour_node.image.name, tuple(colour_node.image.size))
    size = colour_node.image.size[0]                        # the kit's own bake size (512 under PETS_FAST)
    m = bpy.data.materials.new("RoughBake")
    m.use_nodes = True
    t = m.node_tree
    new, link = t.nodes.new, t.links.new
    for n in list(t.nodes):
        t.nodes.remove(n)
    out = new("ShaderNodeOutputMaterial")
    em = new("ShaderNodeEmission")
    link(em.outputs[0], out.inputs[0])
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "gloss"
    co = new("ShaderNodeTexCoord")
    fine = new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 38.0, 3.0
    broad = new("ShaderNodeTexNoise")
    broad.inputs["Scale"].default_value, broad.inputs["Detail"].default_value = 3.5, 2.0
    link(co.outputs["Object"], fine.inputs["Vector"])
    link(co.outputs["Object"], broad.inputs["Vector"])

    def op(kind, x, y):
        n = new("ShaderNodeMath")
        n.operation = kind
        for i, v in enumerate((x, y)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]
    g = op('MULTIPLY', a.outputs["Fac"], -0.65 * base)
    r = op('ADD', g, base)
    r = op('ADD', r, op('MULTIPLY', op('SUBTRACT', fine.outputs["Fac"], 0.5), 2 * vary))
    r = op('ADD', r, op('MULTIPLY', op('SUBTRACT', broad.outputs["Fac"], 0.5), vary))
    r = op('MAXIMUM', op('MINIMUM', r, 1.0), 0.05)
    link(r, em.inputs["Color"])
    img = bpy.data.images.new(os.path.splitext(os.path.basename(texture))[0].replace("_colour", "") + "_rough", size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    tn = new("ShaderNodeTexImage")
    tn.image = img
    t.nodes.active = tn
    body.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    sc = bpy.context.scene
    old = sc.cycles.samples
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    sc.cycles.samples = old
    body.data.materials[0] = baked
    bpy.data.materials.remove(m)
    stem = os.path.splitext(texture)[0]
    img.filepath_raw = (stem[:-len("_colour")] if stem.endswith("_colour") else stem) + "_rough.png"
    img.file_format = 'PNG'
    img.save()
    grey = rough_node.image
    rough_node.image = img
    if grey and grey.users == 0:
        name = grey.name
        bpy.data.images.remove(grey)
        img.name = name
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return float(px[0::4].min()), float(px[0::4].max())
# ---- the shadow panther ---------------------------------------------------------------------------

NAME = "ShadowPanther"
COL = {"fur": hexc("#18171C"), "sheen": hexc("#302E37"), "under": hexc("#151418"), "rosette": hexc("#0A090C"),
       "rosette_in": hexc("#3A3446"), "muzzle": hexc("#33313A"), "line": hexc("#0C0B0E"), "nose": hexc("#17151A"),
       "pupil": hexc("#0A0806"), "white": hexc("#FFFFFF"), "ear_in": hexc("#4A3E48"), "whisker": hexc("#B8B4C0"),
       "lid": hexc("#1A191E"), "rim": hexc("#7A7CB6"), "collar": hexc("#2A2236"), "collar_lt": hexc("#4A3E5E")}
SCALE = 1.12
BAKE = {"shade": 0.4, "rough": 0.86, "vary": 0.12}
HEAD = Vector((0, -1.66, 1.92))
HEAD_M = M(HEAD, rot=(-13, 0, 6))
NECK = [Vector((0, -0.85, 1.5)), Vector((0, -1.2, 1.7)), Vector((0, -1.48, 1.84))]
TAIL = [Vector((0, 1.45, 1.48)), Vector((0.06, 1.98, 1.32)), Vector((0.14, 2.42, 1.52)), Vector((0.14, 2.6, 1.98)),
        Vector((0.04, 2.48, 2.42))]
FACE = HEAD + Vector((0, -0.32, -0.04))
FOCUS = FACE * SCALE
FACE_DIST = 4.0


def _hash(i, j, k):
    h = math.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return h - math.floor(h)


def rosette(co, cell=0.28):
    """0..1: a broken dark ring round jittered cells, the leopard's rosettes, worked out in 3D."""
    p = co / cell
    bi, bj, bk = math.floor(p.x), math.floor(p.y), math.floor(p.z)
    best, bc = 9.0, None
    for i in (bi - 1, bi, bi + 1):
        for j in (bj - 1, bj, bj + 1):
            for k in (bk - 1, bk, bk + 1):
                c = Vector((i + 0.2 + 0.6 * _hash(i, j, k), j + 0.2 + 0.6 * _hash(j, k, i), k + 0.2 + 0.6 * _hash(k, i, j)))
                d = (p - c).length
                if d < best:
                    best, bc = d, c
    ring = 1 - smooth(abs(best - 0.3), 0.05, 0.12)
    broken = smooth(noise.noise(co * 14.0), -0.3, 0.2)
    inside = 1 - smooth(best, 0.18, 0.3)
    return ring * broken, inside


def rosettes(m, cell=0.3, strength=0.75):
    """Leopard rosettes drawn in the material, fine enough for the texture (vertex colour is too coarse
    for them): broken dark rings round Voronoi cells with a slightly warmer centre, only where the
    vertex layer 'spot' allows (none on the face). Baked into the colour image like the fur streaks."""
    t = m.node_tree
    new, link = t.nodes.new, t.links.new
    b = kit.principled(m)
    src = b.inputs["Base Color"].links[0].from_socket
    co = new("ShaderNodeTexCoord")
    vor = new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.0 / cell
    vor.inputs["Randomness"].default_value = 0.8
    link(co.outputs["Object"], vor.inputs["Vector"])

    def math_(op, a, b_=None):
        n = new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]

    def ramp(x, a, b_):
        n = new("ShaderNodeMapRange")
        n.interpolation_type = 'SMOOTHSTEP'
        n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b_
        link(x, n.inputs["Value"])
        return n.outputs["Result"]
    d = vor.outputs["Distance"]
    ring = math_('SUBTRACT', 1.0, ramp(math_('ABSOLUTE', math_('SUBTRACT', d, 0.36)), 0.05, 0.13))
    brk = new("ShaderNodeTexNoise")
    brk.inputs["Scale"].default_value = 9.0
    link(co.outputs["Object"], brk.inputs["Vector"])
    ring = math_('MULTIPLY', ring, ramp(brk.outputs["Fac"], 0.42, 0.55))
    a = new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "spot"
    ring = math_('MULTIPLY', math_('MULTIPLY', ring, a.outputs["Fac"]), strength)
    inside = math_('MULTIPLY', math_('SUBTRACT', 1.0, ramp(d, 0.12, 0.3)), math_('MULTIPLY', a.outputs["Fac"], 0.35))
    warm = new("ShaderNodeMix")
    warm.data_type = 'RGBA'
    link(inside, warm.inputs[0])
    link(src, warm.inputs[6])
    warm.inputs[7].default_value = (*COL["rosette_in"], 1.0)
    dark = new("ShaderNodeMix")
    dark.data_type = 'RGBA'
    link(ring, dark.inputs[0])
    link(warm.outputs[2], dark.inputs[6])
    dark.inputs[7].default_value = (*COL["rosette"], 1.0)
    link(dark.outputs[2], b.inputs["Base Color"])
    return m


def spot_layer(bm, fn):
    lay = bm.verts.layers.float.get("spot") or bm.verts.layers.float.new("spot")
    for v in bm.verts:
        v[lay] = fn(v.co)
    return bm


def build():
    fur_m = rosettes(painted("Fur", dict(strength=0.26, mottle=0.1, fine=46.0, length=5.0), rough=0.88), cell=0.3, strength=0.95)
    eye_m = kit.material("Eyes", "#C4B446", rough=0.06)
    glow = kit.material("GLOW_Tail", "#8A4CFF", rough=0.4, emit=1.3)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def hd(p):
        return HEAD_M @ Vector(p)

    # ---- one fused skin: a long muscular body mid-stride, neck, broad head, long tail ------------------
    clay = [ell((0, 0.2, 1.32), (0.52, 1.15, 0.44)),
            ell((0, -0.62, 1.38), (0.58, 0.55, 0.6)),                         # chest
            ell((0, 1.05, 1.36), (0.5, 0.5, 0.48)),                           # hips
            loft(NECK, lambda t: lerp(0.42, 0.33, t), segs=16, rings=8),
            loft(TAIL, lambda t: lerp(0.14, 0.09, t), segs=12, rings=26),
            ell(hd((0, 0.04, 0.0)), (0.34, 0.36, 0.27)),                      # cranium
            ell(hd((0, -0.15, 0.08)), (0.3, 0.22, 0.12)),                     # brow
            ell(hd((0, -0.32, -0.11)), (0.24, 0.26, 0.15)),                   # broad, longer muzzle
            ell(hd((0, -0.42, -0.02)), (0.13, 0.08, 0.07)),                   # broad nose bridge and pad
            ell(hd((0, -0.26, -0.22)), (0.15, 0.18, 0.075))]                  # strong chin
    for s in (-1, 1):
        clay += [ell(hd((0.11 * s, -0.41, -0.11)), (0.1, 0.075, 0.06)),        # whisker pads
                 ell(hd((0.23 * s, -0.06, -0.08)), (0.18, 0.18, 0.16)),       # cheeks
                 ell((0.33 * s, -0.62, 1.16), (0.3, 0.42, 0.55)),             # heavy shoulders
                 ell((0.34 * s, 1.08, 1.18), (0.29, 0.48, 0.5))]              # thighs
    # legs mid-stride: left fore and right hind reach forward
    fore = {-1: [(-0.33, -0.68, 1.0), (-0.33, -0.9, 0.56), (-0.33, -1.06, 0.15)],
            1: [(0.33, -0.62, 1.0), (0.33, -0.58, 0.56), (0.33, -0.46, 0.15)]}
    hind = {-1: [(-0.34, 1.15, 0.92), (-0.35, 1.45, 0.52), (-0.34, 1.38, 0.15)],
            1: [(0.34, 1.1, 0.92), (0.35, 1.22, 0.48), (0.34, 0.98, 0.15)]}
    paws = []
    for s in (-1, 1):
        clay.append(loft(fore[s], lambda t: lerp(0.25, 0.17, t), segs=12, rings=8))
        clay.append(loft(hind[s], lambda t: lerp(0.21, 0.15, t), segs=12, rings=8))
        for leg in (fore[s], hind[s]):
            p = Vector(leg[-1])
            paws.append(p)
            clay.append(ell(p + Vector((0, -0.07, -0.03)), (0.2, 0.25, 0.12)))
    skin = fuse(join(clay), voxel=0.024, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.14 * s, -1.5, 0.03)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.04)), fwd)
    mouth = [[hit(hd((0, -1.5, -0.08)), fwd)[0], hit(hd((0, -1.5, -0.15)), fwd)[0]]]
    for s in (-1, 1):
        mouth.append([hit(hd((0, -1.5, -0.15)), fwd)[0], hit(hd((0.05 * s, -1.5, -0.17)), fwd)[0], hit(hd((0.11 * s, -1.5, -0.155)), fwd)[0]])

    def carve(co, n):
        d = n * 0.012 * noise.noise(Vector((co.x * 9, co.y * 9, co.z * 2.5)))
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.07, 0.12))
        if (co - nose_at).length < 0.3:
            d -= n * 0.012 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.005, 0.016))
        for p in paws:                                                       # toe grooves
            if (co - p).length < 0.25 and n.y < 0.2 and co.z < 0.2:
                for dx in (-0.05, 0.05):
                    d -= n * 0.022 * (1 - smooth(abs(co.x - p.x - dx), 0.004, 0.018)) * smooth(co.z, 0.2, 0.1)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 8500, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.22, -0.05))).length, 0.22, 0.45)),
                                                    0.4 * (1 - smooth((Vector(co) - HEAD).length, 0.4, 0.6))), factor=1.0)
    eye_frames = []
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.35 + R @ Vector((0, -1, 0)) * 0.65).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        eye_frames.append((e, en, en.cross(up).normalized() * -s, up))

    def fur_colour(co, n, g=0.0):
        col = mix(COL["fur"], COL["sheen"], 0.8 * smooth(n.z, 0.0, 1.0))
        col = mix(col, COL["under"], 0.5 * smooth(-n.z, 0.2, 0.9))
        col = mix(col, COL["sheen"], 0.25 * smooth(noise.noise(Vector((co.x * 6, co.y * 6, co.z * 2))), 0.15, 0.6))
        # a soft blue-violet sheen along the top of the back, head and tail and down the outsides of the legs,
        # like a rim light, so the form reads on the dark fur
        rim = 0.65 * smooth(n.z, 0.62, 0.97)
        if co.z < 1.05:
            rim = max(rim, 0.45 * smooth(abs(n.x), 0.7, 0.98) * smooth(n.z, -0.25, 0.15))
        col = mix(col, COL["rim"], rim * (0.75 + 0.25 * noise.noise(co * 8.0)))
        if (co - HEAD).length < 0.55:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["muzzle"], 0.7 * smooth(p.y, -0.2, -0.3) * smooth(p.z, 0.0, -0.06))
            if (co - nose_at).length < 0.3:
                col = mix(col, COL["line"], 0.9 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.005, 0.012)))
            for (e, en, ex, ey), s in zip(eye_frames, (-1, 1)):
                q = co - e
                if q.dot(en) < -0.08:
                    continue
                u, v = q.dot(ex), q.dot(ey)
                # small dark spots above the eyes, like a big cat's brow
                for (su, sv) in ((0.02, 0.11), (0.08, 0.1), (-0.04, 0.13)):
                    col = mix(col, COL["rosette"], 0.6 * (1 - smooth(math.hypot(u - su, v - sv), 0.012, 0.025)))
        return col
    spot_layer(skin, lambda co: smooth((co - HEAD).length, 0.35, 0.5) * smooth(co.z, 0.3, 0.6))
    add("skin", skin, fur_m, fur_colour)

    # ---- calm gold-green almond eyes with dark lash lids --------------------------------------------
    EW, EH, ED = 0.13, 0.09, 0.042

    def almond(w, h, d, cuts=4):
        bm = kit.ball((w, h, d), cuts=cuts)
        for v in bm.verts:
            k = min(abs(v.co.x) / (w / 2), 1.0)
            v.co.y *= (1 - k ** 2) ** 0.3
        return bm

    for (e, en, ex, ey), s in zip(eye_frames, (-1, 1)):
        tilt = Matrix.Rotation(math.radians(8 * s), 4, en)
        basis = Matrix((ex, ey, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.018) @ tilt @ basis
        eb = almond(EW, EH, ED * 2)
        eb.transform(place)
        add("eyes", eb, eye_m)
        rim = almond(EW * 1.12, EH * 1.15, ED * 1.7)
        rim.transform(place)
        add("rims", rim, fur_m, COL["line"])
        front = e - en * 0.018 + en * (ED - 0.008)
        pupil = kit.ball((0.045, 0.085, 0.02), cuts=3)
        pupil.transform(Matrix.Translation(front) @ tilt @ basis)
        add("pupils", pupil, fur_m, COL["pupil"])
        add("glints", ell(front + en * 0.006 + ey * 0.028 - ex * 0.022 * s, (0.017, 0.017, 0.007), cuts=2), fur_m, COL["white"])
        lid = almond(EW * 1.12, EH * 1.16, ED * 2.25, cuts=10)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.16 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, fur_m, COL["lid"])
        low = almond(EW * 1.1, EH * 1.12, ED * 2.2, cuts=10)
        bmesh.ops.delete(low, geom=[v for v in low.verts if v.co.y > -EH * 0.32 or v.co.z < -0.004], context='VERTS')
        low.transform(place)
        add("lids", low, fur_m, COL["lid"])

    nose = ell((0, 0, 0), (0.1, 0.05, 0.055), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.5 + 0.5 * smooth(v.co.z, -0.045, 0.045)
    nose.transform(M(nose_at) @ R.to_4x4())
    add("nose", glossy(nose, 0.45), fur_m, COL["nose"])

    # ---- short rounded ears ---------------------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.26 * s, 0.12, 0.14))
        pts = [root, root + Vector((0.05 * s, 0.0, 0.06)), root + Vector((0.08 * s, 0.02, 0.11)), root + Vector((0.085 * s, 0.03, 0.135))]
        ear = loft(pts, lambda t: 0.095 * (1 - t ** 2) ** 0.6 + 0.018, segs=12, rings=10, flat=0.42)
        for v in ear.verts:
            gg = v[ear.verts.layers.float["g"]]
            off = v.co - kit._spline(pts, gg * 3)
            if off.y < 0:
                v.co.y -= off.y * 0.6 * smooth(gg, 0.05, 0.3) * smooth(gg, 1.0, 0.8)

        def ear_col(co, n, g):
            col = mix(COL["fur"], COL["sheen"], 0.6 * smooth(n.z, 0.1, 1.0))
            return mix(col, COL["ear_in"], 0.7 * smooth(-n.y, 0.3, 0.75) * smooth(g, 0.05, 0.2) * smooth(g, 0.95, 0.75))
        add("ears", ear, fur_m, ear_col)

    # ---- whiskers --------------------------------------------------------------------------------------
    for s in (-1, 1):
        for k in range(2):
            root = hd((0.11 * s, -0.43, -0.13 - 0.03 * k))
            w = loft([root, root + Vector((0.13 * s, 0.03, 0.005 - 0.015 * k)), root + Vector((0.24 * s, 0.09, -0.02 - 0.035 * k))],
                     lambda t: 0.0055 * (1 - t) + 0.0015, segs=4, rings=5)
            add("whiskers", w, fur_m, COL["whisker"])

    # ---- a glowing violet tail tip -------------------------------------------------------------------
    tip = TAIL[-1]
    tan = (TAIL[-1] - TAIL[-2]).normalized()
    flame = loft([tip - tan * 0.06, tip + tan * 0.07 + Vector((0, 0.01, 0)), tip + tan * 0.17 - Vector((0, 0.02, 0)), tip + tan * 0.27 - Vector((0, 0.05, 0))],
                 lambda t: 0.1 * math.sin(math.pi * (0.25 + 0.75 * t)) ** 0.8 + 0.002, segs=12, rings=12)
    add("glow", flame, glow)

    # ---- a slim dark collar with a glowing violet gem --------------------------------------------------
    ctr = kit._spline(NECK, 0.75)
    axis = (kit._spline(NECK, 0.85) - kit._spline(NECK, 0.65)).normalized()
    ring = lathe([(0.4 + 0.028 * math.cos(t), 0.032 * math.sin(t)) for t in (2 * math.pi * j / 8 for j in range(8))], segs=28, closed=True)
    facing(ring, ctr, axis)
    add("collar", glossy(ring, 0.4), fur_m, lambda co, n, g: mix(COL["collar"], COL["collar_lt"], smooth(n.z, 0.0, 0.8)))
    front = Vector((0, -1, 0)) - axis * axis.dot(Vector((0, -1, 0)))
    front.normalize()
    gem = ell((0, 0, 0), (0.04, 0.03, 0.055), cuts=3)
    for v in gem.verts:
        k = 0.55 + 0.45 * smooth(v.co.z, 0.055, -0.02)
        v.co.x *= k
        v.co.y *= k
    gem.transform(M(ctr + front * 0.44 + Vector((0, 0, -0.05))))
    add("glow", gem, glow)

    lowest = min(v.co.z for bm, _ in c.parts.values() for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    parts = [ob for ob in c.objects if ob not in glow and ob not in eyes]
    if "before_bake" in globals():
        before_bake(parts)
    body = kit.bake_texture(parts, texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
    if "after_bake" in globals():
        after_bake(body)
    rough_map(body, texture, BAKE["rough"], BAKE.get("vary", 0.1))
    out = [body]
    for group, label in ((glow, "GLOW"), (eyes, "Eyes")):
        if not group:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for ob in group:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        g = bpy.context.view_layer.objects.active
        g.name = g.data.name = pre + label
        out.append(g)
    c.objects = out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,front,side,back 3/4")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default=NAME + " review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", NAME.lower() + "_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=FOCUS)
        head = Vector(FACE)
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * FACE_DIST, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * FACE_DIST * 0.94, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
