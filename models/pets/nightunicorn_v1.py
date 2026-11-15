"""NightUnicorn pet: a night-sky unicorn, remade from the game's oddly shaped black-purple unicorn with a pale
lilac head and horn. Built from scratch by script.

    python models/pets/nightunicorn.py --review out/nightunicorn.png      # render the review sheet
    python models/pets/nightunicorn.py --export models/export/nightunicorn.fbx

Must-haves, checked in every review:
  1. The same pet: a black-purple unicorn with lilac in its head, mane and horn.
  2. A well-made horse: deep chest, arched neck, slender legs standing calm and square, a fine head.
  3. A dark night-purple coat painted like a starry sky: soft nebula patches and small crisp stars.
  4. A flowing lilac and violet mane and tail, a glowing lilac spiral horn (GLOW), silver hooves.
  5. A calm face: soft half-lidded violet eyes. Clearly not the white faceted Unicorn (prancing, gold
     hooves): smooth, dark and starry, standing still. Matte coat with varied roughness; about 3.1 studs
     tall; Body under 12k triangles.

Final: round 1.

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

def two_threads():
    """The machine is shared: render and bake on two threads."""
    r = bpy.context.scene.render
    r.threads_mode, r.threads = 'FIXED', 2


def crusted(name, rough=0.9, size=0.17, joins=0.42, vary=0.2):
    """The vertex paint 'col' under kit.scaly's cells: scales, plates or a cracked crust, by size and joins."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=size, joins=joins, vary=vary, rough=rough)
    t = m.node_tree
    hsv = next(n for n in t.nodes if n.type == 'HUE_SAT')
    a = t.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "col"
    t.links.new(a.outputs["Color"], hsv.inputs["Color"])
    return m


def crystal(r, h, sides=6):
    """A pointed crystal prism, base at the origin, pointing up +Z. g runs 0 at the base to 1 at the tip."""
    return lathe([(0.0, -0.02), (r * 0.9, -0.02), (r, h * 0.12), (r * 0.95, h * 0.72), (0.0, h)], segs=sides)


def _rnd(i, k=0.0):
    h = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return h - math.floor(h)


def aim(bm, at, d, up=(0, 0, 1)):
    """Turn a shape built along +Y (its front) so +Y points along d, keeping +Z near `up`, then move it to `at`."""
    d = Vector(d).normalized()
    q = d.to_track_quat('Y', 'Z')
    bm.transform(M(at) @ q.to_matrix().to_4x4())
    return bm

# ---- the night unicorn ----------------------------------------------------------------------------

NAME = "NightUnicorn"
COL = {"coat": hexc("#2C2048"), "coat_dk": hexc("#160F28"), "coat_lt": hexc("#4E3E80"), "nebula": hexc("#2C3C78"),
       "nebula2": hexc("#5A2E78"), "muzzle": hexc("#5C5076"), "violet": hexc("#6A40B8"), "violet_dk": hexc("#3C2276"),
       "lilac": hexc("#C6A4F0"), "lilac_lt": hexc("#EEE2FC"), "silver": hexc("#C8CAD6"), "silver_dk": hexc("#7C7E90"),
       "pupil": hexc("#0C0818"), "white": hexc("#FFFFFF"), "line": hexc("#0E0A18")}
SCALE = 0.96
BAKE = {"shade": 0.4, "rough": 0.86, "vary": 0.12}
HEAD = Vector((0, -1.04, 2.56))
HEAD_M = M(HEAD, rot=(-38, 0, 0))
NECK = [Vector((0, -0.5, 1.78)), Vector((0, -0.74, 2.12)), Vector((0, -0.92, 2.44))]
CREST = [Vector((0, -0.38, 2.04)), Vector((0, -0.6, 2.42)), Vector((0, -0.84, 2.72)), Vector((0, -0.96, 2.8))]
FACE = HEAD + Vector((0, -0.26, -0.12))
FOCUS = FACE * SCALE
FACE_DIST = 3.4
LEGS = [(-0.19, -0.5, True), (0.19, -0.5, True), (-0.2, 0.62, False), (0.2, 0.62, False)]
TAIL_ROOT = Vector((0, 0.92, 1.8))


def starry(name, rough=0.85):
    """The vertex paint 'col' with a faint mottle, scattered with small crisp stars, worked out in the
    shader so the bake keeps them sharp."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    new, link, attr = _ops(t)
    co = new("ShaderNodeTexCoord")
    vor = new("ShaderNodeTexVoronoi")
    vor.feature = 'F1'
    vor.inputs["Scale"].default_value = 7.0
    link(co.outputs["Object"], vor.inputs["Vector"])
    vor2 = new("ShaderNodeTexVoronoi")
    vor2.feature = 'F1'
    vor2.inputs["Scale"].default_value = 17.0
    link(co.outputs["Object"], vor2.inputs["Vector"])
    mottle = new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value, mottle.inputs["Detail"].default_value = 18.0, 3.0
    link(co.outputs["Object"], mottle.inputs["Vector"])

    def op(kind, *args):
        n = new("ShaderNodeMath")
        n.operation = kind
        for i, v in enumerate(args):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]

    def ramp(x, a, b):
        r = new("ShaderNodeMapRange")
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b
        link(x, r.inputs["Value"])
        return r.outputs["Result"]

    def stars(v, size, keep):
        sep = new("ShaderNodeSeparateColor")
        link(v.outputs["Color"], sep.inputs[0])
        dot = ramp(v.outputs["Distance"], size, size * 0.35)                     # 1 at the centre of a cell
        return op('MULTIPLY', dot, ramp(sep.outputs[0], keep, keep + 0.02))    # only in some cells
    s = op('MAXIMUM', stars(vor, 0.11, 0.55), op('MULTIPLY', stars(vor2, 0.12, 0.7), 0.7))
    hsv = new("ShaderNodeHueSaturation")
    link(attr("col"), hsv.inputs["Color"])
    link(op('MULTIPLY_ADD', mottle.outputs["Fac"], 0.2, 0.9), hsv.inputs["Value"])
    mx = new("ShaderNodeMix")
    mx.data_type = 'RGBA'
    link(s, mx.inputs[0])
    link(hsv.outputs["Color"], mx.inputs[6])
    mx.inputs[7].default_value = (*hexc("#F4EEFF"), 1.0)
    b = kit.principled(m)
    link(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def build():
    coat_m = starry("Coat", rough=0.88)
    hair_m = painted("Mane", dict(strength=0.28, mottle=0.06, fine=60.0, length=8.0), rough=0.8)
    eye_m = kit.material("Eyes", "#8E6AD8", rough=0.06)
    glow = kit.material("GLOW_Horn", "#D2ADFF", rough=0.4, emit=2.2)
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

    # ---- one fused skin: barrel, deep chest, round hindquarters, arched neck, a fine head, slender legs --------
    clay = [ell((0, 0.06, 1.56), (0.31, 0.7, 0.35)),
            ell((0, -0.46, 1.6), (0.33, 0.36, 0.42)),                          # chest
            ell((0, 0.56, 1.64), (0.33, 0.4, 0.4)),                             # hindquarters
            loft(NECK, lambda t: lerp(0.26, 0.15, t), segs=14, rings=10),
            loft(CREST[:3], lambda t: 0.1 * math.sin(math.pi * (0.15 + 0.7 * t)), segs=10, rings=8),    # the arch of the crest
            ell(hd((0, 0.04, 0.02)), (0.16, 0.19, 0.17)),                       # cranium
            loft([hd((0, -0.08, -0.02)), hd((0, -0.28, -0.05)), hd((0, -0.44, -0.07))], lambda t: lerp(0.125, 0.105, t), segs=14, rings=8),
            ell(hd((0, -0.44, -0.08)), (0.11, 0.1, 0.1)),                       # soft muzzle
            ell(hd((0, -0.18, -0.13)), (0.09, 0.14, 0.06))]                      # cheeks under the jaw
    for x, y, front in LEGS:
        if front:
            clay += [ell((x * 1.1, y, 1.3), (0.13, 0.17, 0.28)),
                     loft([Vector((x, y, 1.15)), Vector((x, y - 0.01, 0.78)), Vector((x, y, 0.42)), Vector((x, y - 0.01, 0.2)), Vector((x, y - 0.02, 0.1))],
                          lambda t: 0.05 + 0.04 * (1 - smooth(t, 0.05, 0.4)) + 0.012 * math.exp(-((t - 0.8) / 0.06) ** 2), segs=12, rings=14)]
        else:
            clay += [ell((x * 1.1, y, 1.36), (0.15, 0.26, 0.3)),
                     loft([Vector((x, y + 0.04, 1.2)), Vector((x, y + 0.2, 0.8)), Vector((x, y + 0.08, 0.44)), Vector((x, y + 0.06, 0.2)), Vector((x, y + 0.04, 0.1))],
                          lambda t: 0.052 + 0.055 * (1 - smooth(t, 0.05, 0.35)) + 0.012 * math.exp(-((t - 0.8) / 0.06) ** 2), segs=12, rings=14)]
    skin = fuse(join(clay), voxel=0.018, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = []
    for s in (-1, 1):
        tgt = hd((0.11 * s, -0.02, 0.05))
        o = tgt + R @ Vector((0.9 * s, -0.45, 0.1))
        eyes.append(hit(o, tgt - o))
    nostrils = [hit(hd((0.06 * s, -1.4, -0.06)), R @ Vector((0, 1, 0))) for s in (-1, 1)]

    def carve(co, n):
        d = n * 0.005 * noise.noise(co * 6.0)
        for e, en in eyes:
            d -= en * 0.016 * (1 - smooth((co - e).length, 0.045, 0.075))
        for e, en in nostrils:
            if e is not None:
                d -= en * 0.02 * (1 - smooth(((co - e) * Vector((1, 1, 1.4))).length, 0.012, 0.03))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.2, -0.04))).length, 0.18, 0.4)),
                                                    0.2 * (1 - smooth(Vector(co).z, 0.5, 0.3))), factor=1.0)

    def coat_colour(co, n, g=0.0):
        col = mix(COL["coat_dk"], COL["coat"], smooth(n.z, -0.5, 0.3))
        col = mix(col, COL["coat_lt"], 0.5 * smooth(n.z, 0.4, 1.0) * smooth(noise.noise(co * 2.0), -0.2, 0.5))
        col = mix(col, COL["nebula"], 0.55 * smooth(noise.noise(co * 1.3 + Vector((3, 9, 2))), 0.05, 0.5))       # soft nebula clouds
        col = mix(col, COL["nebula2"], 0.45 * smooth(noise.noise(co * 1.7 + Vector((7, 1, 5))), 0.15, 0.55))
        col = mix(col, COL["coat_dk"], 0.6 * smooth(co.z, 0.7, 0.25))                                            # darker stockings
        if (co - HEAD).length < 0.6:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["muzzle"], 0.7 * smooth(p.y, -0.32, -0.46))                                        # a soft grey-violet muzzle
            for e, en in eyes:
                col = mix(col, COL["line"], 0.8 * (1 - smooth((co - e).length, 0.05, 0.065)))
            for e, en in nostrils:
                if e is not None:
                    col = mix(col, COL["line"], 0.75 * (1 - smooth(((co - e) * Vector((1, 1, 1.4))).length, 0.012, 0.028)))
        return col
    add("skin", skin, coat_m, coat_colour)

    # ---- calm half-lidded violet eyes -------------------------------------------------------------------
    EW, EH, ED = 0.085, 0.07, 0.032
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.7 + Vector((0, -1, 0)) * 0.3).normalized()
        up = (Vector((0, 0, 1)) - en * en.dot(Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(8 * s), 4, en)
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.01) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=3)
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.01 + en * (ED - 0.004)
        pupil = kit.ball((0.036, 0.042, 0.012), cuts=2)
        pupil.transform(Matrix.Translation(front) @ tilt @ basis)
        add("pupils", pupil, coat_m, COL["pupil"])
        add("pupils", ell(front + en * 0.004 + up * 0.016 + ex * 0.012 * s, (0.01, 0.01, 0.004), cuts=2), coat_m, COL["white"])
        lid = kit.ball((EW * 1.16, EH * 1.22, ED * 2.3), cuts=6)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.08 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, coat_m, COL["coat_dk"])
        for k in range(3):                                                              # three soft lilac lashes
            root = e + ex * (0.02 + 0.016 * k) * s + up * (EH * 0.5 - 0.006 * k)
            add("lids", loft([root, root + up * 0.02 + ex * 0.016 * s], lambda t: 0.005 * (1 - t) + 0.0015, segs=4, rings=3), coat_m, COL["lilac"])

    # ---- small pointed ears ------------------------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.08 * s, 0.1, 0.13))
        pts = [root, root + R @ Vector((0.025 * s, 0.02, 0.1)), root + R @ Vector((0.04 * s, 0.03, 0.18))]
        ear = loft(pts, lambda t: 0.06 * (1 - t) ** 0.8 + 0.006, segs=10, rings=8, flat=0.5)

        def ear_col(co, n, g):
            col = mix(COL["coat_dk"], COL["coat"], smooth(n.z, -0.3, 0.5))
            return mix(col, COL["lilac"], 0.5 * smooth(-n.y, 0.4, 0.8) * smooth(g, 0.1, 0.3) * smooth(g, 0.9, 0.7))
        add("ears", ear, coat_m, ear_col)

    # ---- silver hooves ---------------------------------------------------------------------------------------
    for x, y, front in LEGS:
        yy = y - 0.02 if front else y + 0.04
        hoof = lathe([(0.0, 0.0), (0.075, 0.0), (0.072, 0.03), (0.062, 0.1), (0.058, 0.12), (0.0, 0.12)], segs=14)
        for v in hoof.verts:
            v.co.y -= 0.012 * (v.co.z / 0.12)
        hoof.transform(M((x, yy, 0.0)))
        add("hooves", glossy(hoof, 0.6), coat_m, lambda co, n, g: mix(COL["silver_dk"], COL["silver"], smooth(n.z + (-n.y) * 0.5, -0.3, 0.7)))

    # ---- a flowing mane and tail of lilac and violet locks ----------------------------------------------------
    def lock_col(k):
        deep = k % 3 == 0

        def f(co, n, g):
            base = COL["violet_dk"] if deep else COL["violet"]
            col = mix(base, COL["lilac"], smooth(g, 0.15, 0.7))
            return mix(col, COL["lilac_lt"], 0.75 * smooth(g, 0.75, 1.0))
        return f
    for k in range(17):
        t = k / 16.0
        root = kit._spline(CREST, t * 3) + Vector((0, 0, -0.02))
        side = 1 if k % 4 != 1 else -1                                                # most fall to the right
        L = 0.42 + 0.14 * math.sin(t * math.pi) + 0.05 * _rnd(k, 1.3)
        out = Vector((side * (0.14 + 0.05 * _rnd(k, 2.0)), 0.12, -0.05))
        pts = [root, root + out * 0.6 + Vector((0, 0.03, 0.04)), root + out * 1.2 + Vector((0.03 * side, 0.08, -L * 0.45)),
               root + out * 1.3 + Vector((0.07 * side * math.sin(k), 0.14, -L))]
        if k > 13:                                                                     # the forelock falls forward between the ears
            pts = [root, root + R @ Vector((0.0, -0.08, 0.04)), root + R @ Vector((0.03 * (k - 14.5), -0.16, -0.04)), root + R @ Vector((0.05 * (k - 14.5), -0.2, -0.13))]
        lk = loft(pts, lambda tt: 0.065 * (1 - tt) ** 0.7 + 0.008, segs=7, rings=10, flat=0.55)
        add("mane", lk, hair_m, lock_col(k))
    for k in range(9):
        a = math.radians(-60 + 120 * k / 8)
        sway = 0.12 * math.sin(k * 1.7)
        L = 1.1 + 0.15 * _rnd(k, 4.4)
        pts = [TAIL_ROOT + Vector((0.03 * math.sin(a), -0.04, 0)),
               TAIL_ROOT + Vector((0.06 * math.sin(a), 0.22, 0.06)),
               TAIL_ROOT + Vector((0.1 * math.sin(a) + sway, 0.4, -L * 0.35)),
               TAIL_ROOT + Vector((0.12 * math.sin(a) - sway, 0.46, -L * 0.7)),
               TAIL_ROOT + Vector((0.14 * math.sin(a) + sway * 0.5, 0.42, -L))]
        lk = loft(pts, lambda tt: 0.07 * (1 - tt) ** 0.6 + 0.01, segs=7, rings=14, flat=0.6)
        add("tail", lk, hair_m, lock_col(k))

    # ---- a glowing lilac spiral horn ------------------------------------------------------------------------
    base = hd((0, -0.02, 0.17))
    hb = bmesh.new()
    rings_, segs_ = 14, 10
    H = 0.4
    lg = hb.verts.layers.float.new("g")
    loops = []
    for i in range(rings_ + 1):
        u = i / rings_
        r = 0.055 * (1 - u) ** 0.9 + 0.004
        ring = []
        for j in range(segs_):
            a = 2 * math.pi * j / segs_
            rr = r * (1 + 0.22 * math.sin(2 * a + u * 14.0))                        # two spiral ridges
            v = hb.verts.new((rr * math.cos(a), rr * math.sin(a), u * H))
            v[lg] = u
            ring.append(v)
        loops.append(ring)
    for a_, b_ in zip(loops, loops[1:]):
        for j in range(segs_):
            hb.faces.new((a_[j], a_[(j + 1) % segs_], b_[(j + 1) % segs_], b_[j]))
    top = hb.verts.new((0, 0, H + 0.01))
    for j in range(segs_):
        hb.faces.new((loops[-1][j], loops[-1][(j + 1) % segs_], top))
    bot = hb.verts.new((0, 0, 0))
    for j in range(segs_):
        hb.faces.new((loops[0][(j + 1) % segs_], loops[0][j], bot))
    bmesh.ops.recalc_face_normals(hb, faces=hb.faces[:])
    hb.transform(M(base) @ (R @ Matrix.Rotation(math.radians(30), 3, 'X')).to_4x4())
    add("glow", hb, glow)

    lowest = min(v.co.z for bm, _ in c.parts.values() for v in bm.verts)
    for bm, _ in c.parts.values():
        bm.transform(M((0, 0, -lowest)))
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    two_threads()
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
    two_threads()
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
        head = Vector(FACE) * SCALE
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
