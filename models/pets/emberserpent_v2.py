"""EmberSerpent pet: a friendly coiled serpent-dragon, remade from the game's coiled red horned snake.
Built from scratch by script.

    python models/pets/emberserpent.py --review out/emberserpent.png      # render the review sheet
    python models/pets/emberserpent.py --export models/export/emberserpent.fbx

Must-haves, checked in every review:
  1. The same creature: a red snake coiled on the ground with its head raised and two horns.
  2. Friendly, never menacing: a big round head with a short snout, soft round amber eyes with
     catchlights, a wide smile, no fangs.
  3. Red scales on the back warming to orange on the sides and a cream-gold belly with bands.
  4. Two small swept-back cream horns, soft orange ear fins and a rounded crest down the neck.
  5. Glowing ember plates down the front of the raised neck.
  6. Matte painted scales with roughness variation; about 3 studs tall; Body under 12k triangles.

Round 2: almost two coils, a smaller loop resting on the wide one, and a thicker S-curved neck (it was one ring and a straight pole); finer, softer scales (the big cells read as cracked earth); a smaller snout so the smile shows; one broad fan fin per side (three spines read as little hands); fewer, rounder crest fins; the ember plates now curved scutes hugging the neck (flat pills looked stuck on).

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
# ---- the ember serpent ----------------------------------------------------------------------------

NAME = "EmberSerpent"
COL = {"red": hexc("#C42E28"), "red_dk": hexc("#8E1E1C"), "orange": hexc("#EC6A2A"), "belly": hexc("#F6C46C"),
       "belly_dk": hexc("#E3A04E"), "horn": hexc("#F4E4C4"), "horn_tip": hexc("#E89A4A"), "fin": hexc("#F39236"),
       "fin_dk": hexc("#D0602A"), "mouth": hexc("#5E1414"), "pupil": hexc("#1A0A06"), "white": hexc("#FFFFFF"),
       "blush": hexc("#F2805A"), "nostril": hexc("#6A1A16")}
SCALE = 1.0
BAKE = {"shade": 0.42, "rough": 0.78, "vary": 0.12}
HEAD = Vector((0, -0.42, 2.0))
HEAD_M = M(HEAD, rot=(-6, 0, 0))
FACE = HEAD + Vector((0, -0.35, -0.05))
FOCUS = FACE
FACE_DIST = 3.6


def scaled(name, rough=0.8, size=0.09):
    """The vertex paint 'col' under kit.scaly's small scales with darker joins."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=size, joins=0.22, vary=0.1, rough=rough)
    t = m.node_tree
    hsv = next(n for n in t.nodes if n.type == 'HUE_SAT')
    a = t.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "col"
    t.links.new(a.outputs["Color"], hsv.inputs["Color"])
    return m


COIL_N = 22
NECK_PTS = 4


def body_path():
    """The coil (almost two turns: a wide loop on the ground, the tail tip outside at the front, and a
    smaller loop resting on top of it) and the neck rising from the back of the top loop in an S to the
    head. The coil's centre line already sits at its tube radius above the ground."""
    total = COIL_N + NECK_PTS
    coil_end = (COIL_N - 1) / (total - 1)
    pts = []
    for i in range(COIL_N):
        u = i / (COIL_N - 1)
        th = math.pi * (-0.2 + 3.7 * u)
        r = 1.04 - 0.5 * u
        z = radius(i / (total - 1), coil_end) * 0.92 + 0.4 * smooth(u, 0.45, 0.68)
        pts.append(Vector((r * math.cos(th), r * math.sin(th), z)))
    end = pts[-1]
    pts += [Vector((end.x * 0.5, end.y + 0.05, end.z + 0.45)), Vector((0, 0.3, 1.4)), Vector((0, -0.12, 1.72)),
            HEAD + Vector((0, 0.3, -0.24))]
    return pts, coil_end


def radius(t, coil_end):
    """Tube radius along the path: a thin tail tip swelling into the body, a slimmer neck."""
    if t < coil_end:
        u = t / coil_end
        return 0.05 + 0.22 * smooth(u, 0.0, 0.55)
    u = (t - coil_end) / (1 - coil_end)
    return 0.27 - 0.06 * smooth(u, 0.0, 0.7)


def build():
    skin_m = scaled("Scales", rough=0.8, size=0.055)
    eye_m = kit.material("Eyes", "#E8A02A", rough=0.06)
    glow = kit.material("GLOW_Ember", "#FF8A2A", rough=0.4, emit=2.2)
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

    pts, coil_end = body_path()
    rings = 150
    path = [kit._spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    # lift each ring so the coil rests on the ground
    lifted = path
    tube = loft(pts, lambda t: radius(t, coil_end), segs=16, rings=150)
    clay = [tube,
            ell(hd((0, 0.02, 0.03)), (0.38, 0.38, 0.33)),                     # cranium
            ell(hd((0, -0.27, -0.08)), (0.24, 0.24, 0.16)),                    # snout
            ell(hd((0, -0.2, -0.19)), (0.2, 0.2, 0.09))]                       # jaw
    for s in (-1, 1):
        clay += [ell(hd((0.22 * s, -0.05, -0.1)), (0.17, 0.2, 0.16)),         # cheeks
                 ell(hd((0.15 * s, -0.12, 0.16)), (0.13, 0.15, 0.08))]        # brow
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.18 * s, -1.5, 0.06)), fwd) for s in (-1, 1)]
    smile = [hit(hd((x, -1.5, -0.17 + 0.9 * x * x)), fwd)[0] for x in (-0.2, -0.13, -0.065, 0.0, 0.065, 0.13, 0.2)]
    nostrils = [hit(hd((0.07 * s, -1.5, -0.02)), fwd) for s in (-1, 1)]

    def carve(co, n):
        d = n * 0.006 * noise.noise(Vector((co.x * 9, co.y * 9, co.z * 9)))
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.08, 0.14))
        for p, pn in nostrils:
            d -= pn * 0.015 * (1 - smooth((co - p).length, 0.012, 0.03))
        if (co - HEAD).length < 0.6:
            d -= n * 0.02 * (1 - smooth(poly_dist(co, smile), 0.008, 0.025))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 8000, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.25, -0.05))).length, 0.25, 0.5)), factor=1.0)

    def nearest_t(co):
        best, bi = 9.0, 0
        for i, p in enumerate(lifted):
            d = (co - p).length_squared
            if d < best:
                best, bi = d, i
        return bi / rings, lifted[bi]

    def scale_colour(co, n, g=0.0):
        col = mix(COL["orange"], COL["red"], smooth(n.z, -0.2, 0.6))
        col = mix(col, COL["red_dk"], 0.35 * smooth(n.z, 0.7, 1.0) * smooth(noise.noise(co * 3.0), -0.2, 0.4))
        if (co - HEAD).length > 0.5:
            t, centre = nearest_t(co)
            off = (co - centre).normalized()
            if t <= coil_end:
                inward = -Vector((centre.x, centre.y, 0)).normalized()
                belly = max(smooth(off.z, -0.3, -0.7), smooth(off.dot(inward), 0.4, 0.8) * smooth(off.z, 0.3, -0.1))
            else:
                belly = smooth(-off.y, 0.45, 0.8)                    # the front of the rising neck
            band = 0.5 + 0.5 * math.sin(t * 260)
            bc = mix(COL["belly"], COL["belly_dk"], smooth(band, 0.75, 0.95))
            col = mix(col, bc, belly)
            col = mix(col, COL["fin"], smooth(t, 0.12, 0.0) * 0.8)                         # an orange tail tip
        else:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["belly"], smooth(p.z, -0.17, -0.24) * smooth(p.y, 0.1, -0.1))  # pale chin
            col = mix(col, COL["orange"], 0.5 * smooth(p.y, -0.25, -0.4))                      # warmer snout
            for s in (-1, 1):
                col = mix(col, COL["blush"], 0.5 * (1 - smooth((p - Vector((0.24 * s, -0.24, -0.08))).length, 0.03, 0.09)))
            col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.007, 0.018))
            for q, qn in nostrils:
                col = mix(col, COL["nostril"], 1 - smooth((co - q).length, 0.012, 0.024))
        return col
    add("skin", skin, skin_m, scale_colour)

    # ---- soft round eyes ------------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        add("eyes", facing(ell((0, 0, 0), (0.095, 0.105, 0.05), cuts=3), e - en * 0.012, en), eye_m)
        pp = e + en * 0.026
        add("pupils", facing(ell((0, 0, 0), (0.06, 0.068, 0.018), cuts=2), pp, en), skin_m, COL["pupil"])
        add("glints", ell(pp + en * 0.016 + R @ Vector((-0.025, 0, 0.03)), (0.022, 0.012, 0.022), cuts=1), skin_m, COL["white"])
        add("glints", ell(pp + en * 0.014 + R @ Vector((0.025, 0, -0.025)), (0.01, 0.006, 0.01), cuts=1), skin_m, COL["white"])

    # ---- two small swept-back horns and soft ear fins ----------------------------------------------------
    for s in (-1, 1):
        root = hd((0.16 * s, 0.08, 0.24))
        pts_h = [root - R @ Vector((0, 0, 0.04)), root + R @ Vector((0.03 * s, 0.1, 0.1)), root + R @ Vector((0.06 * s, 0.26, 0.14)), root + R @ Vector((0.07 * s, 0.38, 0.1))]
        horn = loft(pts_h, lambda t: 0.06 * (1 - t) ** 0.8 + 0.008, segs=10, rings=12)
        add("horns", glossy(horn, 0.5), skin_m, lambda co, n, g: mix(COL["horn"], COL["horn_tip"], smooth(g, 0.5, 1.0)))
        base = hd((0.31 * s, 0.1, 0.02))
        tip = base + R @ Vector((0.16 * s, 0.2, 0.06))
        fin = loft([base, base + (tip - base) * 0.5 + R @ Vector((0.02 * s, 0, 0.03)), tip],
                   lambda t: 0.1 * math.sin(math.pi * min(0.3 + t, 1.0)) ** 0.7 + 0.012, segs=10, rings=8, flat=0.25)
        add("fins", fin, skin_m, lambda co, n, g: mix(COL["fin_dk"], COL["fin"], smooth(g, 0.0, 0.7)))

    # ---- a soft orange crest of rounded fins down the neck ---------------------------------------------------
    neck_start = coil_end + 0.02
    for k in range(5):
        t = neck_start + (1 - neck_start) * (0.2 + 0.15 * k)
        if t > 0.97:
            break
        i = int(t * rings)
        p, q = lifted[i], lifted[min(i + 1, rings)]
        tan = (q - p).normalized()
        back = Vector((0, 1, 0)) - tan * tan.dot(Vector((0, 1, 0)))
        back.normalize()
        r = radius(t, coil_end)
        at = p + back * (r * 0.85)
        fin = loft([at - back * 0.02, at + back * 0.08 + tan * 0.05], lambda u: 0.07 * (1 - u * u) ** 0.5 + 0.01, segs=8, rings=5, flat=0.35)
        add("crest", fin, skin_m, lambda co, n, g: mix(COL["fin_dk"], COL["fin"], smooth(g, 0.0, 0.8)))

    # ---- glowing ember scutes hugging the front of the neck --------------------------------------------------
    for k in range(8):
        t0 = neck_start + (1 - neck_start) * (0.04 + 0.105 * k)
        t1 = t0 + (1 - neck_start) * 0.08
        if t1 > 0.93:
            break
        seg = [kit._spline(pts, tt * (len(pts) - 1)) for tt in (t0, (t0 + t1) / 2, t1)]
        rr = radius((t0 + t1) / 2, coil_end) * 1.05
        band = loft(seg, lambda u: rr, segs=20, rings=3)
        tan = (seg[2] - seg[0]).normalized()
        front = Vector((0, -1, 0.15)) - tan * tan.dot(Vector((0, -1, 0.15)))
        front.normalize()
        mid = seg[1]
        bmesh.ops.delete(band, geom=[f for f in band.faces if (f.calc_center_median() - mid).normalized().dot(front) < 0.5], context='FACES')
        add("glow", band, glow)

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
