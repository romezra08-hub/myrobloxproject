"""JadeTiger pet: a tiger cub carved from jade, remade from the game's blocky green tiger with a curled
tail. Built from scratch by script.

    python models/pets/jadetiger.py --review out/jadetiger.png      # render the review sheet
    python models/pets/jadetiger.py --export models/export/jadetiger.fbx

Must-haves, checked in every review:
  1. The same pet: a green tiger on four legs with darker stripes and its tail curled up over its back.
  2. Carved stone, not fur: smooth broad carved forms, stripes cut in as grooves of deeper jade, no hair
     streaks; clearly different from the furry pets.
  3. Polished but not plastic jade: cloudy colour variation from deep to pale green, fine pale veins,
     satin with varied roughness.
  4. A tiger cub with a friendly face: big round head, inset amber eyes, small carved smile, round ears;
     a red silk collar with gold trim and a gold coin.
  5. About 3 studs tall; Body under 12k triangles.

Final: round 5.

Round 5 (after review: "a rubbery green cat with a sad, droopy face"): the eyes tilted about the line of sight so they sit level with the outer corners a touch up, under a thinner lid, for an alert gaze (tilted about their own axis they drooped and looked pleading); upright rounded ears (the low tilted ones read as a fold-eared house cat); one smooth tapered tail with bands painted along its length (cut-in rings read as a chain); stripes cut much shallower; shaped legs with shoulders and thighs, slim wrists and ankles and bigger paws; matter, deeper-green jade.

Round 4: bigger pupils (small pupils in big amber eyes stared); a softer rim round the eyes (the dark rim read as a sly look); a little less saturated jade.

Round 3: friendlier eyes under only a sliver of jade lid (the dark heavy lid looked grumpy); the brow marks painted, not cut (cut in, they read as frown lines); the smile as a fine carved line; a deeper, less minty jade; leg stripes only on the outsides and thinner (full rings looked like robot joints).

Round 2: clear tiger stripes: more of them, darker and cut deeper, narrowing to points down the sides, and bands on the legs (they were faint smudges); smaller amber eyes tilted up under a carved lid (the big round eyes stared); smaller cheeks (the ruffs looked like flaps); a pale muzzle and pale spots over the eyes; a thicker tail in a bigger curl.

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

# ---- the jade tiger -------------------------------------------------------------------------------

NAME = "JadeTiger"
COL = {"jade": hexc("#2E7350"), "jade_lt": hexc("#6CAA84"), "jade_dk": hexc("#133B29"), "jade_pale": hexc("#B4D8BE"),
       "stripe": hexc("#0B3221"), "cream": hexc("#A8DDB8"), "red": hexc("#A8242A"), "red_dk": hexc("#6E1418"),
       "gold": hexc("#D9AE4C"), "gold_lt": hexc("#F2D58A"), "gold_dk": hexc("#8E6A24"), "pupil": hexc("#1A0E06"),
       "white": hexc("#FFFFFF"), "nose": hexc("#174A33")}
SCALE = 1.32
BAKE = {"shade": 0.42, "rough": 0.74, "vary": 0.18}
HEAD = Vector((0, -0.74, 1.5))
HEAD_M = M(HEAD, rot=(4, 0, -5))
NECK = [Vector((0, -0.4, 1.14)), Vector((0, -0.58, 1.34))]
TAIL = [Vector((0, 0.62, 1.12)), Vector((0, 0.9, 1.3)), Vector((0, 0.98, 1.7)), Vector((0, 0.8, 1.96)), Vector((0, 0.56, 1.88)),
        Vector((0, 0.52, 1.66)), Vector((0, 0.66, 1.58)), Vector((0, 0.76, 1.7))]
TAIL_S = [kit._spline(TAIL, i / 80 * (len(TAIL) - 1)) for i in range(81)]
TAIL_ARC = [0.0]
for _a, _b in zip(TAIL_S, TAIL_S[1:]):
    TAIL_ARC.append(TAIL_ARC[-1] + (_b - _a).length)
FACE = HEAD + Vector((0, -0.34, -0.04))
FOCUS = FACE * SCALE
FACE_DIST = 3.2
LEGS = [(-0.24, -0.4, True), (0.24, -0.4, True), (-0.25, 0.42, False), (0.25, 0.42, False)]


def veined(name, rough=0.55):
    """The vertex paint 'col' under jade's cloudy depth and fine pale veins, worked out in the shader so the
    bake keeps the veins sharp."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    new, link, attr = _ops(t)
    co = new("ShaderNodeTexCoord")
    mp = new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0.4, 0.2, 0.9)
    mp.inputs["Scale"].default_value = (1.6, 1.6, 4.0)
    link(co.outputs["Object"], mp.inputs["Vector"])
    vein = new("ShaderNodeTexNoise")
    vein.inputs["Scale"].default_value, vein.inputs["Detail"].default_value = 1.4, 4.0
    vein.inputs["Roughness"].default_value = 0.55
    link(mp.outputs["Vector"], vein.inputs["Vector"])
    cloud = new("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value, cloud.inputs["Detail"].default_value = 3.0, 3.0
    link(co.outputs["Object"], cloud.inputs["Vector"])

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
    line = ramp(op('ABSOLUTE', op('SUBTRACT', vein.outputs["Fac"], 0.5)), 0.014, 0.0)
    value = op('ADD', op('MULTIPLY_ADD', cloud.outputs["Fac"], 0.4, 0.8), op('MULTIPLY', line, 0.32))
    hsv = new("ShaderNodeHueSaturation")
    link(attr("col"), hsv.inputs["Color"])
    link(value, hsv.inputs["Value"])
    b = kit.principled(m)
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def build():
    jade_m = veined("Jade", rough=0.66)
    silk_m = painted("Silk", dict(strength=0.12, mottle=0.06, fine=60.0, length=1.0), rough=0.7)
    eye_m = kit.material("Eyes", "#E0A030", rough=0.06)
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

    # ---- one fused carved form: a chunky cub body, big paws, a round head and the curled tail -------------
    clay = [ell((0, 0.05, 1.02), (0.36, 0.6, 0.34)),
            ell((0, -0.3, 1.06), (0.38, 0.34, 0.37)),                           # chest
            ell((0, 0.42, 1.02), (0.35, 0.32, 0.33)),                           # haunches
            loft(NECK, lambda t: 0.27, segs=14, rings=6),
            loft(TAIL, lambda t: 0.1 - 0.035 * t, segs=10, rings=36),
            ell(hd((0, 0.04, 0.04)), (0.42, 0.38, 0.37)),                       # round head
            ell(hd((0, -0.28, -0.1)), (0.21, 0.16, 0.15)),                      # muzzle
            ell(hd((0, -0.22, -0.2)), (0.12, 0.12, 0.08))]                      # chin
    for s in (-1, 1):
        clay += [ell(hd((0.085 * s, -0.33, -0.1)), (0.1, 0.09, 0.09)),            # whisker pads
                 ell(hd((0.25 * s, -0.04, -0.1)), (0.13, 0.13, 0.13))]            # cheeks
    for x, y, front in LEGS:
        if front:
            clay += [ell((x * 1.1, y + 0.02, 0.86), (0.19, 0.24, 0.3)),          # shoulders
                     loft([Vector((x * 1.05, y, 0.78)), Vector((x, y - 0.02, 0.48)), Vector((x, y - 0.03, 0.24)), Vector((x, y - 0.05, 0.12))],
                          lambda t: 0.135 - 0.04 * smooth(t, 0.2, 0.75) + 0.01 * smooth(t, 0.8, 1.0), segs=12, rings=10)]   # forearm to a slim wrist
        else:
            clay += [ell((x * 1.1, y, 0.86), (0.21, 0.3, 0.32)),                # thighs
                     loft([Vector((x * 1.05, y + 0.06, 0.76)), Vector((x, y + 0.14, 0.46)), Vector((x, y + 0.06, 0.24)), Vector((x, y + 0.0, 0.12))],
                          lambda t: 0.14 - 0.045 * smooth(t, 0.2, 0.75) + 0.01 * smooth(t, 0.8, 1.0), segs=12, rings=10)]  # hock to a slim ankle
        clay.append(ell((x, y - 0.08, 0.09), (0.17, 0.21, 0.095)))             # big cub paws
    skin = fuse(join(clay), voxel=0.019, iterations=4)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.15 * s, -1.5, 0.06)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.06)), fwd)
    mouth = [[hit(hd((0, -1.5, -0.1)), fwd)[0], hit(hd((0, -1.5, -0.15)), fwd)[0]]]
    for s in (-1, 1):
        mouth.append([hit(hd((0, -1.5, -0.15)), fwd)[0], hit(hd((0.05 * s, -1.5, -0.185)), fwd)[0], hit(hd((0.11 * s, -1.5, -0.165)), fwd)[0],
                      hit(hd((0.14 * s, -1.5, -0.13)), fwd)[0]])
    mouth = [[p for p in m if p is not None] for m in mouth]

    def stripe(co, n):
        """0..1: inside a tiger stripe. Bands round the body and legs, narrowing to points on the sides."""
        if (co - HEAD).length < 0.55:
            p = HEAD_M.inverted() @ co
            if p.z > 0.12 and p.y < 0.1:                                                    # three marks on the brow
                k = 0.0
                for xm, top in ((-0.09, 0.24), (0.0, 0.3), (0.09, 0.24)):
                    k = max(k, (1 - smooth(abs(p.x - xm), 0.015, 0.03)) * smooth(p.z, 0.12, 0.16) * smooth(p.z, top + 0.04, top))
                return k
            if abs(p.x) > 0.22 and p.z < 0.06 and p.y < 0.05:                                # cheek stripes
                w = 0.5 + 0.5 * math.sin(p.z * 40 + abs(p.x) * 12)
                return smooth(w, 0.72, 0.85) * smooth(abs(p.x), 0.22, 0.3)
            return 0.0
        if poly_dist(co, TAIL) < 0.13:                                                       # bands along the tail
            i = min(range(len(TAIL_S)), key=lambda j: (TAIL_S[j] - co).length)
            return 0.7 * smooth(0.5 + 0.5 * math.sin(TAIL_ARC[i] * 13.0), 0.72, 0.8) * smooth(TAIL_ARC[i], 0.15, 0.25)
        if co.z < 0.25:
            return 0.0
        side = smooth(n.z, -0.4, 0.1)
        if co.z < 0.9 and abs(co.x) > 0.1:                                                  # bands round the legs
            band = 0.5 + 0.5 * math.sin(co.z * 24.0 + 0.8 * math.sin(co.y * 10))
            return smooth(band, 0.8, 0.86) * smooth(co.z, 0.3, 0.45) * smooth(n.x * (1 if co.x > 0 else -1), 0.2, 0.6)
        wob = 0.06 * math.sin(co.z * 11 + co.x * 5) + 0.03 * math.sin(co.x * 17)
        band = 0.5 + 0.5 * math.sin((co.y + wob) * 21.0 + 0.6)
        width = 0.5 + 0.38 * smooth(n.z, 0.95, 0.0)                                          # wide over the back, narrowing to points
        return smooth(band, width, width + 0.06) * side

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 4.0)
        shallow = 0 if (co - HEAD).length < 0.5 or poly_dist(co, TAIL) < 0.13 else 1
        d -= n * 0.009 * stripe(co, n) * shallow                                             # stripes cut in shallow (painted only on the face and tail)
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.075, 0.115))
        if (co - nose_at).length < 0.3:
            d -= n * 0.014 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.005, 0.016))
        if co.z < 0.17 and n.y < 0.3:                                                        # toe grooves on the paws
            for x, y, front in LEGS:
                if abs(co.y - (y - 0.08)) < 0.22 and abs(co.x - x) < 0.18:
                    for dx in (-0.055, 0.0, 0.055):
                        d -= n * 0.018 * (1 - smooth(abs(co.x - x - dx), 0.003, 0.014)) * smooth(co.z, 0.17, 0.1) * (1 if co.y < y - 0.06 else 0)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 7400, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.22, -0.02))).length, 0.22, 0.45)),
                                                    0.35 * (1 - smooth((Vector(co) - HEAD).length, 0.4, 0.6))), factor=1.0)

    def jade_colour(co, n, g=0.0):
        col = mix(COL["jade_dk"], COL["jade"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["jade_lt"], 0.55 * smooth(noise.noise(co * 1.8), -0.1, 0.5))             # cloudy, as if lit from within
        col = mix(col, COL["jade_pale"], 0.35 * smooth(n.z, 0.6, 1.0) * smooth(noise.noise(co * 3.3 + Vector((2, 7, 1))), 0.0, 0.5))
        col = mix(col, COL["jade_dk"], 0.3 * smooth(noise.noise(co * 2.4 + Vector((9, 3, 5))), 0.3, 0.7))
        col = mix(col, COL["cream"], 0.6 * smooth(-n.z, 0.3, 0.8) * smooth(co.z, 0.5, 0.75))            # paler belly
        col = mix(col, COL["stripe"], 0.95 * stripe(co, n))
        if (co - HEAD).length < 0.55:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["jade_pale"], 0.9 * smooth(p.y, -0.22, -0.32) * smooth(p.z, 0.0, -0.07))  # pale muzzle and chin
            col = mix(col, COL["jade_pale"], 0.7 * (1 - smooth((p - Vector((0.13 * (1 if p.x > 0 else -1), -0.24, 0.12))).length, 0.03, 0.07)))  # pale spots over the eyes
            for e, en in eyes:
                col = mix(col, COL["jade_dk"], 0.6 * (1 - smooth((co - e).length, 0.075, 0.095)))
            if (co - nose_at).length < 0.3:
                col = mix(col, COL["stripe"], 0.85 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.005, 0.012)))
        return col
    add("skin", glossy(skin, 0.2), jade_m, jade_colour)

    # ---- inset amber eyes --------------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        tilt = Matrix.Rotation(math.radians(9 * s), 4, Vector((0, -1, 0)))          # level, outer corners a touch up as seen from the front
        basis = tilt @ basis
        eb = kit.ball((0.12, 0.1, 0.08), cuts=3)
        eb.transform(Matrix.Translation(e - en * 0.014) @ basis)
        add("eyes", eb, eye_m)
        lid = kit.ball((0.135, 0.115, 0.095), cuts=6)                                         # a carved upper lid
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < 0.044 or v.co.z < -0.004], context='VERTS')
        lid.transform(Matrix.Translation(e - en * 0.012) @ basis)
        add("lids", glossy(lid, 0.45), jade_m, COL["jade"])
        front = e + en * 0.024
        pu = kit.ball((0.058, 0.066, 0.016), cuts=2)
        pu.transform(Matrix.Translation(front) @ basis)
        add("pupils", pu, jade_m, COL["pupil"])
        add("pupils", ell(front + en * 0.006 + up * 0.015 + ex * 0.018 * s, (0.013, 0.013, 0.005), cuts=2), jade_m, COL["white"])

    for m in mouth:                                                                     # the smile, cut as a fine dark line
        if len(m) > 1:
            add("mouth", loft([p + (p - HEAD).normalized() * 0.002 for p in m], lambda t: 0.007, segs=5, rings=3 * len(m)), jade_m, COL["stripe"])
    nose = ell((0, 0, 0), (0.065, 0.04, 0.04), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.45 + 0.55 * smooth(v.co.z, -0.04, 0.035)
    nose.transform(M(nose_at + fwd * -0.006) @ R.to_4x4())
    add("nose", glossy(nose, 0.6), jade_m, COL["nose"])

    # ---- round cub ears ------------------------------------------------------------------------------------
    for s in (-1, 1):
        ear = kit.ball((0.17, 0.08, 0.21), cuts=4)
        for v in ear.verts:
            if v.co.y < 0:
                v.co.y *= 0.4                                                                  # a shallow carved hollow
            v.co.x *= 1 - 0.25 * smooth(v.co.z, 0.0, 0.1)                                     # rounded, a little narrower at the top
        ear.transform(M(hd((0.22 * s, 0.05, 0.34)), rot=(-4, 0, -12 * s)))                     # upright

        def ear_col(co, n, g):
            col = mix(COL["jade_dk"], COL["jade"], smooth(n.z, -0.3, 0.5))
            return mix(col, COL["jade_pale"], 0.6 * smooth(-n.y, 0.5, 0.9))
        add("ears", glossy(ear, 0.45), jade_m, ear_col)

    # ---- a red silk collar with gold trim and a gold coin -------------------------------------------------
    ctr = kit._spline(NECK, 0.5)
    axis = (NECK[1] - NECK[0]).normalized()
    band = lathe([(0.29, -0.05), (0.31, -0.035), (0.31, 0.035), (0.29, 0.05)], segs=32)
    facing(band, ctr, axis)
    add("collar", band, silk_m, lambda co, n, g: mix(COL["red_dk"], COL["red"], smooth(n.z, -0.4, 0.6)))
    for dz in (-0.05, 0.05):
        trim = lathe([(0.3 + 0.014 * math.cos(t), 0.014 * math.sin(t)) for t in (2 * math.pi * j / 6 for j in range(6))], segs=32, closed=True)
        facing(trim, ctr + axis * dz, axis)
        add("collar", glossy(trim, 0.6), jade_m, lambda co, n, g: mix(COL["gold_dk"], COL["gold"], smooth(n.z, -0.4, 0.6)))
    front = Vector((0, -1, 0)) - axis * axis.dot(Vector((0, -1, 0)))
    front.normalize()
    coin = lathe([(0.0, 0.016), (0.07, 0.014), (0.08, 0.0), (0.07, -0.014), (0.0, -0.016)], segs=20)
    facing(coin, ctr + front * 0.33 - axis * 0.07, (front * 0.9 + Vector((0, 0, -0.2))).normalized())

    def coin_col(co, n, g):
        col = mix(COL["gold_dk"], COL["gold"], smooth(n.z + (-n.y), -0.2, 0.8))
        return mix(col, COL["gold_lt"], 0.5 * smooth(g, 0.3, 0.0))
    add("collar", glossy(coin, 0.65), jade_m, coin_col)

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
