"""IronGolem pet: a friendly mining-construct golem, remade from the game's blocky rust-brown golem with
glaring yellow eyes and yellow horn spikes. Built from scratch by script.

    python models/pets/irongolem.py --review out/irongolem.png      # render the review sheet
    python models/pets/irongolem.py --export models/export/irongolem.fbx

Must-haves, checked in every review:
  1. The same pet: a rust-brown block golem with big arms and fists, short legs, yellow eyes and two
     small horns.
  2. A friendly mining construct: rusty riveted iron plates over dark stone, a caged lantern glowing in
     its chest, soft round glowing eyes under a visor, a small smile; never glaring.
  3. Two small brass horns, scratched and pickaxe-scarred plates, worn bright edges.
  4. Clearly not the slate-and-emerald Golem or the round basalt MagmaCrown: iron, rust and brass, a
     lantern instead of crystals.
  5. Matte stone, satin worn metal (varied roughness); about 3.6 studs tall; Body under 12k triangles.

Final: round 3.

Round 3: rust-brown iron with more rust and dark stains (the plates read as grey stone with orange smears); a domed helmet and a thinner visor brow (the stacked flat slabs read as a hat).

Round 2: bigger, overlapping stone blocks so arms and legs read as one solid body (they were stacked separate lumps), bigger fists; a lantern core that shows in a shallower niche; the smile as a dark carved line; domed pauldrons instead of flat slabs; smaller, patchier rust and more visible pickaxe scratches; smaller brass horns.

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

# ---- the iron golem -------------------------------------------------------------------------------

NAME = "IronGolem"
COL = {"stone": hexc("#3E3B3A"), "stone_lt": hexc("#625C57"), "stone_dk": hexc("#242222"), "iron": hexc("#4E4038"),
       "iron_lt": hexc("#958A80"), "rust": hexc("#8E4420"), "rust_lt": hexc("#B8622E"), "rust_dk": hexc("#5A2A14"),
       "scratch": hexc("#B8B0A6"), "brass": hexc("#C49A46"), "brass_lt": hexc("#E8C878"), "brass_dk": hexc("#7C5A24"),
       "socket": hexc("#141110"), "smile": hexc("#1A1514")}
SCALE = 1.12
BAKE = {"shade": 0.5, "rough": 0.86, "vary": 0.14}
HEAD = Vector((0, -0.14, 2.7))
FACE = HEAD + Vector((0, -0.3, 0.0))
FOCUS = FACE * SCALE
FACE_DIST = 4.0
CORE = Vector((0, -0.52, 1.82))


def box(size, n=3.2, cuts=6):
    return kit.rounded_box(size, n=n, cuts=cuts)


def scarred(name, rough=0.8):
    """The vertex paint 'col' with a soft mottle and, in patches, fine bright scratches like pickaxe scars,
    worked out in the shader so the bake keeps them sharp."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    new, link, attr = _ops(t)
    co = new("ShaderNodeTexCoord")
    mp = new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0.5, 0.8, 0.3)
    mp.inputs["Scale"].default_value = (2.0, 2.0, 26.0)
    link(co.outputs["Object"], mp.inputs["Vector"])
    lines = new("ShaderNodeTexNoise")
    lines.inputs["Scale"].default_value, lines.inputs["Detail"].default_value = 1.0, 0.0
    link(mp.outputs["Vector"], lines.inputs["Vector"])
    patch = new("ShaderNodeTexNoise")
    patch.inputs["Scale"].default_value, patch.inputs["Detail"].default_value = 2.6, 1.0
    link(co.outputs["Object"], patch.inputs["Vector"])
    mottle = new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value, mottle.inputs["Detail"].default_value = 14.0, 3.0
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
    line = ramp(op('ABSOLUTE', op('SUBTRACT', lines.outputs["Fac"], 0.5)), 0.018, 0.0)    # 1 on a thin scratch
    where = ramp(patch.outputs["Fac"], 0.48, 0.6)                                          # only in some patches
    value = op('ADD', op('MULTIPLY_ADD', mottle.outputs["Fac"], 0.3, 0.85), op('MULTIPLY', op('MULTIPLY', line, where), 1.3))
    hsv = new("ShaderNodeHueSaturation")
    link(attr("col"), hsv.inputs["Color"])
    link(value, hsv.inputs["Value"])
    b = kit.principled(m)
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def build():
    stone_m = crusted("Stone", rough=0.94, size=0.16, joins=0.38, vary=0.18)
    iron_m = scarred("Iron", rough=0.7)
    glow = kit.material("GLOW_Lantern", "#FFB54A", rough=0.4, emit=2.4)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def at(bm, loc, rot=(0, 0, 0)):
        bm.transform(M(loc, rot=rot))
        return bm

    # ---- one fused dark stone body: barrel chest, big arms and fists, short stout legs, a low head ------------
    clay = [at(box((1.36, 0.92, 1.0), 3.0), (0, 0, 1.88)),
            at(box((1.1, 0.8, 0.5), 3.0), (0, 0.02, 2.3)),                       # broad top of the chest
            at(box((0.92, 0.62, 0.42), 3.0), (0, 0.02, 1.2)),                     # pelvis
            at(box((0.64, 0.6, 0.54), 3.4), HEAD)]
    for s in (-1, 1):
        clay += [at(box((0.6, 0.62, 0.56), 2.6), (0.86 * s, 0.0, 2.2)),           # shoulders
                 at(box((0.42, 0.44, 0.7), 3.0), (1.0 * s, 0.0, 1.7), (0, -6 * s, 0)),     # upper arms
                 at(box((0.52, 0.54, 0.66), 3.0), (1.08 * s, -0.04, 1.16)),       # forearms
                 at(box((0.6, 0.58, 0.5), 3.2), (1.1 * s, -0.08, 0.7)),           # big fists
                 at(box((0.42, 0.46, 0.56), 3.0), (0.4 * s, 0.02, 0.86)),         # thighs
                 at(box((0.46, 0.5, 0.48), 3.0), (0.42 * s, 0.0, 0.42)),          # shins
                 at(box((0.54, 0.66, 0.26), 3.4), (0.43 * s, -0.08, 0.13))]       # feet
    skin = fuse(join(clay), voxel=0.026, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit(HEAD + Vector((0.15 * s, -3, -0.02)), (0, 1, 0)) for s in (-1, 1)]
    smile = [hit(HEAD + Vector((x, -3, -0.15 + 1.8 * x * x)), (0, 1, 0))[0] for x in (-0.1, -0.06, -0.03, 0.0, 0.03, 0.06, 0.1)]
    core, core_n = hit(CORE + Vector((0, -3, 0)), (0, 1, 0))
    fingers = []
    for s in (-1, 1):
        for k in range(3):
            fingers.append((1.1 * s + (k - 1) * 0.13, 0.42))

    def carve(co, n):
        d = n * 0.02 * noise.noise(co * 2.4) + n * 0.008 * noise.noise(co * 9.0)
        for e, en in eyes:
            d -= en * 0.04 * (1 - smooth(((co - e) * Vector((1, 1, 1.1))).length, 0.07, 0.11))
        d -= n * 0.012 * (1 - smooth(poly_dist(co, smile), 0.006, 0.02)) * (1 if co.y < -0.3 else 0)
        d -= Vector((0, 1, 0)) * 0.05 * (1 - smooth((co - core).length, 0.2, 0.27)) * (1 if co.y < -0.2 else 0)  # the lantern's niche
        if co.z < 0.62 and co.z > 0.42 and co.y < -0.2:                                    # finger grooves on the fists
            for fx, fz in fingers:
                d -= n * 0.02 * (1 - smooth(abs(co.x - fx - 0.065), 0.004, 0.02)) * (1 if abs(co.x - fx) < 0.2 else 0)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5200, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - FACE).length, 0.25, 0.45)), factor=1.0)

    def stone_colour(co, n, g=0.0):
        col = mix(COL["stone_dk"], COL["stone"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["stone_lt"], 0.5 * smooth(n.z, 0.3, 1.0) * smooth(noise.noise(co * 2.0), -0.3, 0.5))
        col = mix(col, COL["rust_dk"], 0.35 * smooth(noise.noise(co * 1.4 + Vector((4, 2, 1))), 0.2, 0.6))       # rust stains run onto the stone
        col = mix(col, COL["stone_dk"], 0.3 * smooth(co.z, 0.35, 0.1))
        for e, en in eyes:
            col = mix(col, COL["socket"], 0.85 * (1 - smooth((co - e).length, 0.09, 0.13)))
        if co.y < -0.3:
            col = mix(col, COL["smile"], 0.9 * (1 - smooth(poly_dist(co, smile), 0.006, 0.014)))
        col = mix(col, COL["socket"], 0.8 * (1 - smooth((co - core).length, 0.21, 0.27)))
        return col
    add("skin", skin, stone_m, stone_colour)

    # ---- rusty riveted iron plates, painted in their own frame before being placed --------------------------
    rivets = []

    def plate(size, loc, rot=(0, 0, 0), bend=(0.0, 0.0), seed=0.0, n=5.0, studs=(), dome=0.0):
        bm = box(size, n, cuts=4)
        sx, sy, sz = (v / 2 for v in size)
        for v in bm.verts:                                                     # curve it to sit on a rounded form
            v.co.y += bend[0] * (v.co.x / sx) ** 2 + bend[1] * (v.co.z / sz) ** 2
            v.co.z -= dome * ((v.co.x / sx) ** 2 + (v.co.y / sy) ** 2)

        def col(co, nn, g):
            e = max(abs(co.x) / sx, abs(co.z) / sz)
            k = Vector((co.x + seed * 3.1, co.y + seed * 1.7, co.z + seed * 2.3))
            c0 = mix(COL["iron"], COL["iron_lt"], 0.4 * smooth(nn.z, 0.2, 1.0))
            r = smooth(noise.noise(k * 3.5) + 0.35 * noise.noise(k * 11.0), -0.25, 0.35)
            c0 = mix(c0, COL["rust"], 0.8 * r)
            c0 = mix(c0, COL["rust_lt"], 0.45 * r * smooth(noise.noise(k * 8.0), 0.15, 0.55))
            c0 = mix(c0, COL["rust_dk"], 0.4 * smooth(noise.noise(k * 6.0 + Vector((5, 5, 5))), 0.2, 0.6))
            c0 = mix(c0, COL["rust_dk"], 0.6 * smooth(co.z / sz, -0.4, -1.0))            # rust collects at the bottom edge
            return mix(c0, COL["iron_lt"], 0.6 * smooth(e, 0.82, 0.97) * (1 - r))          # bright worn edges
        paint(bm, col)
        glossy(bm, 0.25)
        mtx = M(loc, rot=rot)
        bm.transform(mtx)
        add("plates", bm, iron_m)
        for (ux, uz) in studs:                                                   # rivets, in the plate's own units
            p = Vector((ux * (sx - 0.05), -sy + bend[0] * ux * ux + bend[1] * uz * uz, uz * (sz - 0.05)))
            rivets.append(mtx @ p)
    corners = ((-1, 1), (1, 1), (-1, -1), (1, -1))
    plate((1.12, 0.1, 0.3), (0, -0.47, 2.25), (6, 0, 0), bend=(0.1, 0.0), seed=1, studs=corners + ((0, 1), (0, -1)))      # chest
    plate((0.84, 0.1, 0.26), (0, -0.46, 1.4), (-4, 0, 0), bend=(0.08, 0.0), seed=2, studs=corners)                          # belly
    plate((0.74, 0.7, 0.09), HEAD + Vector((0, 0.0, 0.3)), (0, 0, 0), seed=3, n=3.0, studs=(), dome=0.12)                   # a domed helmet
    plate((0.7, 0.08, 0.09), HEAD + Vector((0, -0.31, 0.15)), (-10, 0, 0), bend=(0.06, 0.0), seed=4, studs=((-1, 0), (1, 0)))   # visor brow
    for s in (-1, 1):
        plate((0.72, 0.7, 0.1), (0.9 * s, -0.02, 2.5), (0, 20 * s, 0), seed=5 + s, n=3.4, studs=(), dome=0.16)               # domed pauldrons
        plate((0.52, 0.54, 0.34), (1.08 * s, -0.04, 1.2), (0, 0, 0), seed=7 + s, n=4.0, studs=())                              # bracers
        plate((0.38, 0.1, 0.34), (0.42 * s, -0.24, 0.44), (0, 0, 0), bend=(0.05, 0.0), seed=9 + s, studs=((0, 1), (0, -1)))   # shin guards
        plate((0.3, 0.1, 0.34), (0.4 * s, -0.22, 0.86), (8, 0, 0), bend=(0.04, 0.0), seed=11 + s, studs=((0, 1),))            # thigh plates
    for s in (-1, 1):
        for k in range(4):                                                         # rivets round the bracers and pauldron rims
            a = math.radians(-60 + 40 * k)
            rivets.append(Vector((1.08 * s + 0.27 * math.sin(a) * s, -0.04 - 0.28 * math.cos(a), 1.3)))
            rivets.append(Vector((1.08 * s + 0.27 * math.sin(a) * s, -0.04 - 0.28 * math.cos(a), 1.1)))
    for p in rivets:
        add("rivets", glossy(ell(p, (0.032, 0.032, 0.032), cuts=1), 0.45), iron_m,
            lambda co, nn, g: mix(COL["iron"], COL["iron_lt"], smooth(nn.z, -0.2, 0.8)))

    # ---- the caged lantern in the chest ---------------------------------------------------------------------
    add("glow", ell(core + Vector((0, -0.02, 0)), (0.17, 0.13, 0.17), cuts=3), glow)
    sm = [p + Vector((0, -0.004, 0)) for p in smile if p is not None]
    add("smile", loft(sm, lambda t: 0.011 * math.sin(math.pi * (0.15 + 0.7 * t)) + 0.004, segs=5, rings=16), stone_m, COL["socket"])

    def brass_col(co, nn, g):
        return mix(COL["brass_dk"], COL["brass"], smooth(nn.z, -0.5, 0.5))
    ring = lathe([(0.21 + 0.03 * math.cos(t), 0.03 * math.sin(t)) for t in (2 * math.pi * j / 6 for j in range(6))], segs=24, closed=True)
    facing(ring, core - Vector((0, 0.05, 0)), (0, -1, 0))
    add("lantern", glossy(ring, 0.5), iron_m, brass_col)
    for x in (-0.09, 0.0, 0.09):                                                    # the cage bars
        h = math.sqrt(max(0.2 ** 2 - x * x, 0.0))
        bar = loft([core + Vector((x, -0.06, -h)), core + Vector((x, -0.15, 0)), core + Vector((x, -0.06, h))], lambda t: 0.016, segs=6, rings=8)
        add("lantern", glossy(bar, 0.5), iron_m, brass_col)
    cap = lathe([(0.0, 0.08), (0.08, 0.07), (0.1, 0.0), (0.0, 0.0)], segs=12)
    cap.transform(M(core + Vector((0, -0.06, 0.2))))
    add("lantern", glossy(cap, 0.5), iron_m, brass_col)

    # ---- soft round glowing eyes ---------------------------------------------------------------------------
    for e, en in eyes:
        add("glow", facing(ell((0, 0, 0), (0.07, 0.08, 0.035), cuts=2), e - en * 0.02, (en * 0.5 + Vector((0, -1, 0)) * 0.5).normalized()), glow)

    # ---- two small brass horns -----------------------------------------------------------------------------
    for s in (-1, 1):
        base = HEAD + Vector((0.3 * s, 0.02, 0.28))
        pts = [base - Vector((0.03 * s, 0, 0.04)), base + Vector((0.06 * s, -0.01, 0.07)), base + Vector((0.09 * s, -0.04, 0.15)), base + Vector((0.08 * s, -0.08, 0.2))]
        horn = loft(pts, lambda t: 0.055 * (1 - t) ** 0.9 + 0.008, segs=10, rings=10)

        def horn_col(co, nn, g):
            col = mix(COL["brass_dk"], COL["brass"], smooth(g, 0.0, 0.4))
            return mix(col, COL["brass_lt"], 0.7 * smooth(g, 0.7, 1.0))
        add("horns", glossy(horn, 0.5), iron_m, horn_col)

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
