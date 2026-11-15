"""SunDragon pet: an elegant golden sun dragon, remade from the game's stiff, blocky yellow dragon with red
spines. Built from scratch by script.

    python models/pets/sundragon.py --review out/sundragon.png      # render the review sheet
    python models/pets/sundragon.py --export models/export/sundragon.fbx

Must-haves, checked in every review:
  1. The same pet: a yellow dragon on four legs with red spines down its back.
  2. Elegant, not stiff: a slender body on long legs, an S-curved neck held high, a long slim tail.
  3. Warm yellow-gold scales with a paler belly, a red-orange sun-ray frill behind the head and red-orange
     spines, small wings folded along its sides, a flame tuft at the tail tip (GLOW).
  4. A confident, friendly face: amber eyes, swept-back horns, a small smile.
  5. Clearly not the obsidian Dragon (black, red, wings raised): gold and red, wings folded, a frill.
     Matte scales with varied roughness; about 3 studs tall; Body under 12k triangles.

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

# ---- the sun dragon -------------------------------------------------------------------------------

NAME = "SunDragon"
COL = {"gold": hexc("#EDBB45"), "gold_lt": hexc("#F8D978"), "gold_dk": hexc("#BC8424"), "belly": hexc("#F7E3A6"),
       "red": hexc("#D2401E"), "red_dk": hexc("#8E2414"), "orange": hexc("#F0782A"), "flame": hexc("#FFC24A"),
       "horn": hexc("#F6E2B0"), "horn_dk": hexc("#B48A50"), "line": hexc("#5A2A12"), "pupil": hexc("#1A0C06"),
       "white": hexc("#FFFFFF"), "claw": hexc("#E8D6B0")}
SCALE = 1.0
BAKE = {"shade": 0.42, "rough": 0.82, "vary": 0.14}
HEAD = Vector((0, -1.08, 2.42))
HEAD_M = M(HEAD, rot=(-8, 0, 0))
NECK = [Vector((0, -0.42, 1.4)), Vector((0, -0.72, 1.66)), Vector((0, -0.84, 2.0)), Vector((0, -0.96, 2.3))]
TAIL = [Vector((0, 0.72, 1.26)), Vector((0, 1.12, 1.1)), Vector((0.18, 1.5, 0.8)), Vector((0.42, 1.78, 0.56)), Vector((0.62, 1.92, 0.5)),
        Vector((0.78, 1.96, 0.6))]
FACE = HEAD + Vector((0, -0.28, -0.04))
FOCUS = FACE
FACE_DIST = 3.2
LEGS = [(-0.2, -0.42, True), (0.2, -0.42, True), (-0.21, 0.56, False), (0.21, 0.56, False)]


def blade(L, w, th=0.02, cuts=3, curve=0.0, tip=1.0):
    """A pointed leaf along +X from the origin (width along Z, thickness along Y); g runs root 0 to tip 1."""
    bm = kit.ball((1, 1, 1), cuts=cuts)
    lg = bm.verts.layers.float.new("g")
    for v in bm.verts:
        u = min(max(v.co.x + 0.5, 0.0), 1.0)
        f = math.sin(math.pi * (0.06 + 0.94 * u ** 0.8)) ** (0.6 * tip) * (1 - 0.15 * u) + 0.03
        v.co = Vector((u * L, v.co.y * 2 * th * (0.4 + 0.6 * f) + curve * L * u * u, v.co.z * 2 * w * f))
        v[lg] = u
    return bm


def frame_to(bm, at, d, n):
    """Local X -> d, local Y -> n (made perpendicular), local Z -> their cross."""
    d = Vector(d).normalized()
    n = (Vector(n) - d * d.dot(Vector(n))).normalized()
    bm.transform(M(at) @ Matrix((d, n, d.cross(n))).transposed().to_4x4())
    return bm


def build():
    scale_m = crusted("Scales", rough=0.82, size=0.075, joins=0.3, vary=0.14)
    fin_m = painted("Fins", dict(strength=0.1, mottle=0.08, fine=30.0, length=3.0), rough=0.78)
    eye_m = kit.material("Eyes", "#F0A030", rough=0.06)
    glow = kit.material("GLOW_Sun", "#FFA63A", rough=0.4, emit=2.4)
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

    # ---- one fused skin: slender body, long legs, an S-curved neck, a fine head and a long slim tail ---------
    clay = [ell((0, 0.12, 1.24), (0.3, 0.62, 0.3)),
            ell((0, -0.32, 1.28), (0.33, 0.36, 0.37)),                         # chest
            ell((0, 0.56, 1.24), (0.29, 0.32, 0.31)),                           # hips
            loft(NECK, lambda t: lerp(0.24, 0.13, t), segs=14, rings=14),
            loft(TAIL, lambda t: 0.2 * (1 - t) ** 1.1 + 0.035, segs=12, rings=28),
            ell(hd((0, 0.04, 0.03)), (0.19, 0.23, 0.17)),                       # cranium
            loft([hd((0, -0.12, -0.02)), hd((0, -0.3, -0.06)), hd((0, -0.44, -0.09))], lambda t: lerp(0.13, 0.075, t), segs=14, rings=8),
            ell(hd((0, -0.24, -0.11)), (0.09, 0.2, 0.05))]                      # lower jaw
    for s in (-1, 1):
        clay += [ell(hd((0.1 * s, -0.04, 0.07)), (0.08, 0.12, 0.06))]            # brow ridges
    for x, y, front in LEGS:
        if front:
            clay += [ell((x * 1.12, y, 1.08), (0.14, 0.18, 0.28)),
                     loft([Vector((x * 1.1, y, 0.9)), Vector((x * 1.05, y - 0.06, 0.5)), Vector((x, y - 0.02, 0.2)), Vector((x, y - 0.08, 0.07))],
                          lambda t: 0.06 + 0.04 * (1 - smooth(t, 0.1, 0.6)), segs=12, rings=10)]
        else:
            clay += [ell((x * 1.12, y, 1.08), (0.16, 0.28, 0.3)),
                     loft([Vector((x * 1.1, y + 0.08, 0.9)), Vector((x * 1.08, y + 0.24, 0.5)), Vector((x, y + 0.1, 0.22)), Vector((x, y + 0.02, 0.07))],
                          lambda t: 0.062 + 0.055 * (1 - smooth(t, 0.05, 0.45)), segs=12, rings=10)]
        py = y - 0.14 if front else y - 0.06
        clay.append(ell((x, py, 0.055), (0.08, 0.13, 0.055)))
    skin = fuse(join(clay), voxel=0.018, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = []
    for s in (-1, 1):
        tgt = hd((0.11 * s, -0.08, 0.04))
        o = tgt + R @ Vector((0.9 * s, -0.9, 0.1))
        eyes.append(hit(o, tgt - o))
    nostrils = [hit(hd((0.04 * s, -1.5, -0.03)), fwd) for s in (-1, 1)]
    mouth = []
    for s in (-1, 1):
        pts = []
        for k in range(6):
            y = -0.44 + 0.065 * k
            z = -0.105 + 0.02 * smooth(k, 3, 5)
            p = hit(hd((0.6 * s, y, z)), R @ Vector((-s, 0, 0)))[0]
            if p is not None:
                pts.append(p)
        mouth.append(pts)
    SPINE = [kit._spline(NECK, t) for t in (0.4, 1.0, 1.6, 2.2, 2.8)] + [Vector((0, -0.2, 1.62)), Vector((0, 0.2, 1.56)), Vector((0, 0.6, 1.56))]

    def carve(co, n):
        d = n * 0.006 * noise.noise(co * 5.0)
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.05, 0.085))
        for e, en in nostrils:
            if e is not None:
                d -= en * 0.015 * (1 - smooth((co - e).length, 0.012, 0.03))
        if (co - HEAD).length < 0.6:
            md = min(poly_dist(co, m) for m in mouth if len(m) > 1)
            d -= n * 0.012 * (1 - smooth(md, 0.004, 0.014))
        if co.z > 0.6 and co.z < 1.2 and abs(co.y) < 0.7 and n.z < -0.2:                  # belly plate grooves
            d -= n * 0.008 * smooth(0.5 + 0.5 * math.cos(co.y * 30), 0.85, 1.0)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6200, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.18, -0.02))).length, 0.18, 0.38)),
                                                    0.3 * (1 - smooth((Vector(co) - HEAD).length, 0.3, 0.5))), factor=1.0)

    def scale_colour(co, n, g=0.0):
        col = mix(COL["gold_dk"], COL["gold"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["gold_lt"], 0.45 * smooth(n.z, 0.4, 1.0) * smooth(noise.noise(co * 3.0), -0.2, 0.5))
        col = mix(col, COL["orange"], 0.35 * smooth(poly_dist(co, SPINE), 0.16, 0.05) * smooth(n.z, 0.2, 0.8))   # warmer down the spine
        col = mix(col, COL["belly"], 0.85 * smooth(-n.z, 0.15, 0.6) * smooth(co.z, 0.55, 0.8))                 # pale belly and throat
        col = mix(col, COL["belly"], 0.8 * smooth(-n.y - n.z, 0.6, 1.2) * smooth(co.z, 1.3, 1.6) * smooth(co.y, -0.2, -0.6))
        col = mix(col, COL["orange"], 0.5 * smooth(co.z, 0.3, 0.08))                                           # sun-burnt feet
        tl = poly_dist(co, TAIL)
        if tl < 0.24:
            col = mix(col, COL["orange"], 0.7 * smooth((co - TAIL[0]).length, 1.0, 1.4))
        if (co - HEAD).length < 0.5:
            for e, en in eyes:
                col = mix(col, COL["line"], 0.75 * (1 - smooth((co - e).length, 0.058, 0.075)))
            for e, en in nostrils:
                if e is not None:
                    col = mix(col, COL["line"], 0.8 * (1 - smooth((co - e).length, 0.01, 0.022)))
            md = min(poly_dist(co, m) for m in mouth if len(m) > 1)
            col = mix(col, COL["line"], 0.85 * (1 - smooth(md, 0.005, 0.012)))
        return col
    add("skin", glossy(skin, 0.15), scale_m, scale_colour)

    # ---- amber eyes with a confident level lid ---------------------------------------------------------
    EW, EH, ED = 0.1, 0.075, 0.036
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.5 + R @ Vector((0, -1, 0)) * 0.5).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(10 * s), 4, en)
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.012) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=3)
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.012 + en * (ED - 0.005)
        pupil = kit.ball((0.026, 0.05, 0.014), cuts=2)
        pupil.transform(Matrix.Translation(front) @ tilt @ basis)
        add("pupils", pupil, scale_m, COL["pupil"])
        add("pupils", ell(front + en * 0.005 + up * 0.018 + ex * 0.014 * s, (0.011, 0.011, 0.005), cuts=2), scale_m, COL["white"])
        lid = kit.ball((EW * 1.14, EH * 1.2, ED * 2.25), cuts=6)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.22 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, scale_m, COL["gold_dk"])

    # ---- swept-back horns ----------------------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.09 * s, 0.12, 0.12))
        pts = [root, root + R @ Vector((0.04 * s, 0.14, 0.06)), root + R @ Vector((0.07 * s, 0.3, 0.06)), root + R @ Vector((0.08 * s, 0.42, 0.12))]
        horn = loft(pts, lambda t: 0.045 * (1 - t) ** 0.9 + 0.005, segs=10, rings=10)
        add("horns", glossy(horn, 0.35), fin_m, lambda co, n, g: mix(COL["horn_dk"], COL["horn"], smooth(g, 0.0, 0.6)))

    # ---- a sun-ray frill behind the head ----------------------------------------------------------------------
    def ray_col(co, n, g):
        col = mix(COL["gold"], COL["orange"], smooth(g, 0.1, 0.5))
        return mix(col, COL["red"], 0.85 * smooth(g, 0.55, 0.9))
    centre = hd((0, 0.14, -0.04))
    back = R @ Vector((0, 1, 0))
    for k in range(11):
        a = math.radians(-115 + 230 * k / 10)
        out = R @ Vector((math.sin(a), 0, math.cos(a)))
        d = (out + back * 0.55).normalized()
        L = 0.32 + 0.08 * math.cos(a * 1.2)
        b = blade(L, 0.06, th=0.014, cuts=3, curve=0.04)
        frame_to(b, centre + out * 0.1, d, back)
        add("frill", b, fin_m, ray_col)

    # ---- red-orange spines from the head to the tail tip ------------------------------------------------------
    def spine_col(co, n, g):
        return mix(COL["red_dk"], COL["red"], smooth(g, 0.0, 0.4))
    path = SPINE + [kit._spline(TAIL, t) for t in (0.6, 1.2, 1.8, 2.4, 3.0, 3.6)]
    for k, p in enumerate(path[1:]):
        top, nrm = hit(p + Vector((0, 0, 1.5)), (0, 0, -1))
        if top is None:
            continue
        h = 0.16 if 2 < k < 9 else 0.11
        if k >= 9:
            h = 0.11 - 0.012 * (k - 9)
        sp = lathe([(0.0, -0.03), (0.05, -0.03), (0.035, h * 0.5), (0.0, h)], segs=6)
        for v in sp.verts:
            v.co.x *= 0.45
        sp.transform(M(rot=(-28, 0, 0)))
        sp.transform(M(top - Vector((0, 0, 0.02))))
        add("spines", sp, fin_m, spine_col)

    # ---- small wings folded along the sides -----------------------------------------------------------------
    def wing_col(co, n, g):
        col = mix(COL["red_dk"], COL["red"], smooth(g, 0.0, 0.5))
        return mix(col, COL["orange"], 0.6 * smooth(g, 0.6, 1.0))
    for s in (-1, 1):
        shoulder, sn = hit(Vector((0.6 * s, -0.25, 1.52)), Vector((-s, 0, -0.25)))
        add("wings", loft([shoulder - sn * 0.03, shoulder + Vector((0.06 * s, 0.25, 0.1)), shoulder + Vector((0.07 * s, 0.6, 0.04))],
                          lambda t: 0.045 - 0.02 * t, segs=8, rings=8), scale_m, COL["gold_dk"])               # the folded arm
        for k, (L, droop) in enumerate(((0.62, 0.15), (0.55, 0.35), (0.46, 0.55))):
            root = shoulder + Vector((0.07 * s, 0.22 + 0.12 * k, 0.06 - 0.03 * k))
            d = Vector((0.06 * s, 1.0, -droop))
            b = blade(L, 0.1, th=0.012, cuts=3, curve=0.0, tip=0.7)
            frame_to(b, root, d, Vector((s, 0, 0.15)))
            add("wings", b, fin_m, wing_col)

    # ---- three-toed feet with pale claws ----------------------------------------------------------------
    for x, y, front in LEGS:
        py = y - 0.14 if front else y - 0.06
        for dx in (-0.05, 0.0, 0.05):
            p, nrm = hit((x + dx, py - 1, 0.05), (0, 1, 0))
            if p is None:
                continue
            cl = lathe([(0.0, 0.0), (0.022, 0.0), (0.0, 0.07)], segs=6)
            cl.transform(M(p + Vector((0, 0.005, -0.01)), rot=(100, 0, 0)))
            add("claws", glossy(cl, 0.4), fin_m, COL["claw"])

    # ---- a flame tuft at the tail tip, glowing at its heart ------------------------------------------------------
    tip = TAIL[-1]
    tang = (TAIL[-1] - TAIL[-2]).normalized()
    for k in range(7):
        a = 2 * math.pi * k / 7
        side = tang.orthogonal().normalized()
        side = Matrix.Rotation(a, 3, tang) @ side
        d = (tang * 0.6 + side * 0.5 + Vector((0, 0, 0.7))).normalized()
        b = blade(0.3 + 0.06 * math.sin(k * 2.3), 0.07, th=0.025, cuts=3, curve=0.08)
        frame_to(b, tip - tang * 0.04, d, side.cross(d))

        def flame_col(co, n, g):
            col = mix(COL["red"], COL["orange"], smooth(g, 0.0, 0.45))
            return mix(col, COL["flame"], 0.9 * smooth(g, 0.55, 0.95))
        add("tuft", b, fin_m, flame_col)
    core = blade(0.28, 0.06, th=0.05, cuts=2)
    frame_to(core, tip, (tang * 0.3 + Vector((0, 0, 1))).normalized(), Vector((1, 0, 0)))
    add("glow", core, glow)

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
