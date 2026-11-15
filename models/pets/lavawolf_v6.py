"""LavaWolf pet: a handsome wolf of cooled lava, remade from the game's blocky, noisy orange-brown fire
wolf. Built from scratch by script.

    python models/pets/lavawolf.py --review out/lavawolf.png      # render the review sheet
    python models/pets/lavawolf.py --export models/export/lavawolf.fbx

Must-haves, checked in every review:
  1. The same pet: a fiery orange-and-dark wolf standing on four legs.
  2. Handsome and proud: head held high, deep chest, long legs, a low brush tail; mouth closed.
  3. Dark basalt fur with glowing orange cracks (GLOW) sunk into it, and an ember mane of flame-shaped
     locks round the neck and shoulders, darker at the roots.
  4. A calm face: amber eyes under soft lids, a dark nose, tall ears with ember insides.
  5. Clearly not the grey Wolf (silver locks, violet crystals): black and ember, sleek short coat.
     Matte with varied roughness; about 3 studs tall; Body under 12k triangles.

Final: round 6.

Round 6: longer, broader flame locks lying flatter, with a stronger flicker and the ember starting halfway up (with only the tips lit they read as thorns); a lower row wrapping under the chest and sweeping down instead of three locks on the throat (they looked like fangs); deeper joins in the basalt crust.

Round 5 (after review: "the tubular spikes read as carrots or a porcupine"): the mane rebuilt as twenty-odd flat flame-shaped locks in three overlapping rows that lie on the neck and sweep back, dark rock at the root and glowing ember only towards the tips, three more down the throat; shorter ears; thicker upper legs and lower legs, bigger paws; the basalt as broken rock (a crust of plates with deep joins and lumpy carving) instead of flat fur.

Round 4: the chest ruff is a few broad flame locks curling out from under the throat (the long strands on the chest hung like a grass skirt).

Round 3: the eyes tilted up at the outer corners under a lighter lid (they drooped and looked sad); an ember line swept back from each eye and paler cheeks so the dark face reads; a ruff of ember locks hanging on the chest (from the front it was a plain black column); fewer faces in the skin, locks and cracks to fit the budget.

Round 2: a handsome wolf head: a longer, narrower muzzle, a broad flat skull with brows, a smaller nose, smaller deeper-amber eyes under a calm half lid (round yellow eyes stared and the short muzzle read as a puppy); the ember mane swept back along the neck like flames, thicker on top (the locks stuck out sideways like a spiked collar); a thicker neck and chest, sturdier forelegs.

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

# ---- the lava wolf --------------------------------------------------------------------------------

NAME = "LavaWolf"
COL = {"basalt": hexc("#2E2826"), "basalt_lt": hexc("#5A4C46"), "basalt_dk": hexc("#1A1615"), "heat": hexc("#9C3A18"),
       "heat_lt": hexc("#E06A26"), "ember": hexc("#E8642A"), "ember_dk": hexc("#8E2A14"), "ember_lt": hexc("#FFB04A"),
       "eye_rim": hexc("#140E0C"), "pupil": hexc("#120A06"), "white": hexc("#FFFFFF"), "nose": hexc("#121010"),
       "ear_in": hexc("#B4441E")}
SCALE = 1.0
BAKE = {"shade": 0.45, "rough": 0.88, "vary": 0.14}
HEAD = Vector((0, -1.02, 2.2))
HEAD_M = M(HEAD, rot=(-6, 0, 0))
NECK = [Vector((0, -0.5, 1.45)), Vector((0, -0.74, 1.8)), Vector((0, -0.92, 2.08))]
TAIL = [Vector((0, 0.86, 1.42)), Vector((0, 1.12, 1.3)), Vector((0, 1.32, 1.02)), Vector((0, 1.42, 0.74)), Vector((0, 1.5, 0.52))]
FACE = HEAD + Vector((0, -0.32, -0.06))
FOCUS = FACE
FACE_DIST = 3.4
LEGS = [(-0.2, -0.52, True), (0.2, -0.52, True), (-0.22, 0.62, False), (0.22, 0.62, False)]


def blade(L, w, th=0.02, cuts=3, curve=0.0):
    """A pointed leaf along +X from the origin (width along Z, thickness along Y); g runs root 0 to tip 1."""
    bm = kit.ball((1, 1, 1), cuts=cuts)
    lg = bm.verts.layers.float.new("g")
    for v in bm.verts:
        u = min(max(v.co.x + 0.5, 0.0), 1.0)
        f = math.sin(math.pi * (0.08 + 0.92 * u ** 0.75)) ** 0.7 * (1 - 0.2 * u) + 0.03
        v.co = Vector((u * L, v.co.y * 2 * th * (0.4 + 0.6 * f) + curve * L * u * u, v.co.z * 2 * w * f))
        v[lg] = u
    return bm


def flame(L, w, seed):
    """A flat flame-shaped lock: a leaf with a flicker to one side near its tip, lifting slightly off the skin."""
    bm = blade(L, w, th=0.018, cuts=3, curve=0.05)
    lg = bm.verts.layers.float["g"]
    side = 1 if _rnd(seed, 2.0) > 0.5 else -1
    for v in bm.verts:
        u = v[lg]
        v.co.z += side * 0.22 * L * math.sin(u * 3.0) * u                                # a flame's flicker
    return bm


def frame_to(bm, at, d, n):
    """Local X -> d, local Y -> n (made perpendicular), local Z -> their cross."""
    d = Vector(d).normalized()
    n = (Vector(n) - d * d.dot(Vector(n))).normalized()
    bm.transform(M(at) @ Matrix((d, n, d.cross(n))).transposed().to_4x4())
    return bm


def build():
    fur_m = crusted("Basalt", rough=0.92, size=0.085, joins=0.44, vary=0.22)
    lock_m = painted("Mane", dict(strength=0.12, mottle=0.08, fine=30.0, length=3.0), rough=0.86)
    eye_m = kit.material("Eyes", "#D98A2A", rough=0.06)
    glow = kit.material("GLOW_Lava", "#FF7A22", rough=0.4, emit=2.4)
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

    # ---- one fused skin: deep chest, lean waist, long legs, a wedge head and a brush tail -----------
    clay = [ell((0, 0.08, 1.38), (0.35, 0.7, 0.34)),
            ell((0, -0.4, 1.42), (0.41, 0.44, 0.47)),                           # deep chest
            ell((0, 0.6, 1.4), (0.34, 0.37, 0.35)),                              # hips
            loft(NECK, lambda t: lerp(0.35, 0.25, t), segs=14, rings=8),
            loft(TAIL, lambda t: 0.1 + 0.07 * math.sin(math.pi * min(t * 1.2, 1.0)) - 0.06 * t ** 3, segs=12, rings=18),
            ell(hd((0, 0.06, 0.02)), (0.25, 0.27, 0.21)),                        # a broad, flat-topped skull
            loft([hd((0, -0.1, -0.03)), hd((0, -0.32, -0.08)), hd((0, -0.54, -0.11))], lambda t: lerp(0.14, 0.072, t), segs=14, rings=10),
            ell(hd((0, -0.32, -0.15)), (0.085, 0.2, 0.05))]                       # lower jaw
    for s in (-1, 1):
        clay += [ell(hd((0.14 * s, -0.06, -0.06)), (0.11, 0.13, 0.11)),           # cheeks
                 ell(hd((0.1 * s, -0.08, 0.08)), (0.09, 0.1, 0.06))]              # brows
    for x, y, front in LEGS:
        s = 1 if x > 0 else -1
        if front:
            clay += [ell((x * 1.1, y, 1.18), (0.2, 0.25, 0.36)),
                     loft([Vector((x, y - 0.02, 1.0)), Vector((x, y - 0.04, 0.55)), Vector((x, y - 0.03, 0.22)), Vector((x, y - 0.06, 0.1))],
                          lambda t: 0.09 + 0.06 * (1 - smooth(t, 0.1, 0.6)), segs=12, rings=10)]
        else:
            clay += [ell((x * 1.1, y, 1.18), (0.22, 0.35, 0.37)),
                     loft([Vector((x, y + 0.1, 1.0)), Vector((x, y + 0.26, 0.6)), Vector((x, y + 0.14, 0.3)), Vector((x, y + 0.1, 0.1))],
                          lambda t: 0.085 + 0.07 * (1 - smooth(t, 0.05, 0.45)), segs=12, rings=10)]
        py = y - 0.1 if front else y + 0.04
        clay.append(ell((x, py, 0.07), (0.12, 0.165, 0.07)))
    skin = fuse(join(clay), voxel=0.02, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.115 * s, -1.5, 0.045)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.07)), fwd)

    # ---- glowing cracks wandering over the coat, kept off the face ------------------------------------------
    def off_face(p):
        q = HEAD_M.inverted() @ p
        return not (q.y < 0.05 and abs(q.x) < 0.3 and q.z > -0.3 and (p - HEAD).length < 0.6)
    cracks = []

    def wander(start, d, steps, step, seed):
        p, _, _, _ = tree.find_nearest(Vector(start))
        d = Vector(d).normalized()
        pts = [p]
        for i in range(steps):
            j = Vector((_rnd(seed + i, 3.1) - 0.5, _rnd(seed + i, 5.7) - 0.5, _rnd(seed + i, 9.3) - 0.5))
            d = (d + j * 1.0).normalized()
            q, n, _, _ = tree.find_nearest(p + d * step)
            if not off_face(q):
                break
            d = (q - p).normalized()
            p = q
            pts.append(p)
        return pts
    for k, (start, d, n) in enumerate((((0.36, -0.3, 1.5), (0, 0.3, -1), 9), ((-0.36, -0.25, 1.55), (0, 0.4, -1), 9),
                                       ((0.32, 0.25, 1.5), (0, 1, -0.4), 8), ((-0.33, 0.3, 1.45), (0, 1, -0.6), 8),
                                       ((0.3, 0.62, 1.55), (0, 0.3, -1), 9), ((-0.3, 0.66, 1.5), (0, 0.2, -1), 9),
                                       ((0.22, -0.55, 1.0), (0, -0.1, -1), 8), ((-0.22, -0.55, 1.0), (0, -0.1, -1), 8),
                                       ((0.0, 0.2, 1.72), (0.3, 1, 0), 8), ((0, 1.3, 1.05), (0, 0.4, -1), 6),
                                       ((0.2, -0.62, 1.95), (0.5, 0.2, -1), 5), ((-0.2, -0.62, 1.95), (-0.5, 0.2, -1), 5))):
        main = wander(start, d, n, 0.085, k * 37 + 3)
        cracks.append(main)
        if k < 6 and len(main) > 5:
            cracks.append(wander(main[3], Vector((0, 0, -1)) + Vector(d) * 0.3, 4, 0.075, k * 53 + 11))

    def crack_d(co):
        return min(poly_dist(co, cr) for cr in cracks if len(cr) > 2)

    def carve(co, n):
        d = n * 0.014 * noise.noise(co * 7.0) + n * 0.006 * noise.noise(co * 19.0)        # broken-rock lumps
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth((co - e).length, 0.06, 0.1))
        d -= n * 0.018 * (1 - smooth(crack_d(co), 0.008, 0.03))
        if co.z < 0.14 and n.y < 0.3:                                              # toe grooves
            for x, y, front in LEGS:
                py = y - 0.1 if front else y + 0.04
                if abs(co.y - py) < 0.16 and abs(co.x - x) < 0.11:
                    for dx in (-0.033, 0.033):
                        d -= n * 0.014 * (1 - smooth(abs(co.x - x - dx), 0.003, 0.012)) * smooth(co.z, 0.13, 0.07)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.2, -0.04))).length, 0.2, 0.42)),
                                                    0.3 * (1 - smooth(crack_d(Vector(co)), 0.02, 0.06))), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(COL["basalt_dk"], COL["basalt"], smooth(n.z, -0.5, 0.3))
        col = mix(col, COL["basalt_lt"], 0.45 * smooth(n.z, 0.4, 1.0) * smooth(noise.noise(co * 2.6), -0.2, 0.5))
        cd = crack_d(co)
        col = mix(col, COL["heat"], 0.85 * (1 - smooth(cd, 0.025, 0.09)))                 # warm rock round each crack
        col = mix(col, COL["heat_lt"], 0.8 * (1 - smooth(cd, 0.008, 0.03)))
        col = mix(col, COL["heat"], 0.5 * smooth(co.z, 0.3, 0.1))                          # paws glow faintly where they touch
        tdist = poly_dist(co, TAIL)
        if tdist < 0.2:
            col = mix(col, COL["ember"], 0.9 * smooth((co - TAIL[0]).length, 0.6, 0.95))   # an ember tail tip
            col = mix(col, COL["ember_lt"], 0.7 * smooth((co - TAIL[0]).length, 0.85, 1.05))
        if (co - HEAD).length < 0.55:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["basalt_lt"], 0.35 * smooth(p.y, -0.2, -0.35) * smooth(n.z, 0.2, 0.8))   # the bridge of the nose
            col = mix(col, COL["basalt_lt"], 0.4 * smooth(abs(p.x), 0.1, 0.18) * smooth(p.z, 0.0, -0.1))           # paler cheeks
            for e, en in eyes:
                col = mix(col, COL["eye_rim"], 0.8 * (1 - smooth((co - e).length, 0.06, 0.08)))
                q = HEAD_M.inverted() @ e
                u, v = abs(p.x) - abs(q.x), p.z - q.z                                        # an ember line swept back from each eye
                if u > 0.02 and p.x * q.x > 0:
                    col = mix(col, COL["heat_lt"], 0.85 * (1 - smooth(abs(v - 0.35 * (u - 0.02)), 0.006, 0.016)) * smooth(u, 0.02, 0.04) * smooth(u, 0.16, 0.11))
            mouth = [hd((0.0, -0.52, -0.15)), hd((0.05, -0.46, -0.16)), hd((0.1, -0.3, -0.15)), hd((0.13, -0.18, -0.125))]
            mouth_l = [Vector((-v.x, v.y, v.z)) for v in mouth]
            md = min(poly_dist(co, mouth), poly_dist(co, mouth_l))
            col = mix(col, COL["heat"], 0.85 * (1 - smooth(md, 0.006, 0.016)))
        return col
    add("skin", skin, fur_m, fur_colour)
    for cr in cracks:
        if len(cr) < 3:
            continue
        lift = [p - tree.find_nearest(p)[1] * 0.006 for p in cr]
        add("glow", loft(lift, lambda t: 0.016 * math.sin(math.pi * min(0.12 + t, 1.0)) ** 0.5 + 0.003, segs=4, rings=len(cr)), glow)

    # ---- calm amber eyes with soft lids ----------------------------------------------------------------
    EW, EH, ED = 0.095, 0.062, 0.036
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(12 * s), 4, en)
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.014) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=3)
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.014 + en * (ED - 0.006)
        pupil = kit.ball((0.038, 0.046, 0.014), cuts=2)
        pupil.transform(Matrix.Translation(front) @ tilt @ basis)
        add("pupils", pupil, fur_m, COL["pupil"])
        add("pupils", ell(front + en * 0.006 + up * 0.02 + ex * 0.016 * s, (0.012, 0.012, 0.006), cuts=2), fur_m, COL["white"])
        lid = kit.ball((EW * 1.15, EH * 1.2, ED * 2.3), cuts=6)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.16 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, fur_m, COL["basalt"])

    nose = ell((0, 0, 0), (0.058, 0.04, 0.036), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.6 + 0.4 * smooth(v.co.z, -0.045, 0.03)
    nose.transform(M(nose_at + fwd * -0.01) @ R.to_4x4())
    add("nose", glossy(nose, 0.45), fur_m, COL["nose"])

    # ---- tall ears with ember insides ------------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.13 * s, 0.08, 0.17))
        pts = [root, root + Vector((0.03 * s, 0.01, 0.11)), root + Vector((0.05 * s, 0.03, 0.21)), root + Vector((0.065 * s, 0.045, 0.28))]
        ear = loft(pts, lambda t: 0.13 * (1 - t) ** 0.85 + 0.006, segs=12, rings=12, flat=0.42)
        for v in ear.verts:
            gg = v[ear.verts.layers.float["g"]]
            off = v.co - kit._spline(pts, gg * 3)
            if off.y < 0:
                v.co.y -= off.y * 0.6 * smooth(gg, 0.05, 0.25) * smooth(gg, 1.0, 0.8)

        def ear_col(co, n, g):
            col = mix(COL["basalt_dk"], COL["basalt"], smooth(n.z, -0.3, 0.5))
            inner = smooth(-n.y, 0.3, 0.75) * smooth(g, 0.05, 0.2) * smooth(g, 0.9, 0.7)
            return mix(col, COL["ear_in"], 0.85 * inner)
        add("ears", ear, fur_m, ear_col)

    # ---- an ember mane: flame-shaped locks round the neck and shoulders ---------------------------------------
    def lock_col(co, n, g):
        col = mix(COL["basalt_dk"], COL["basalt"], smooth(n.z, -0.4, 0.6))
        col = mix(col, COL["ember_dk"], smooth(g, 0.22, 0.5))                           # dark rock at the root, ember towards the tip
        col = mix(col, COL["ember"], smooth(g, 0.55, 0.8))
        return mix(col, COL["ember_lt"], 0.9 * smooth(g, 0.85, 1.0))
    axis = (NECK[2] - NECK[0]).normalized()

    def lay(start, nrm, want, L, w, k):
        """A flat flame lock lying on the skin at `start`, swept along `want` (kept tangent to the skin)."""
        d = (want - nrm * nrm.dot(want)).normalized()
        b = flame(L, w, k)
        frame_to(b, start - nrm * 0.012, d, nrm)
        add("mane", b, lock_m, lock_col)
    k = 0
    for row, (along, ring, span) in enumerate(((0.0, 7, 160), (0.35, 7, 130), (0.72, 6, 120))):   # three overlapping rows that hug the neck
        for j in range(ring):
            a = math.radians(-span + 2 * span * (j + 0.5 * (row % 2)) / (ring - 0.5))
            base = kit._spline(NECK, along * 2)
            side = Vector((math.sin(a), 0, math.cos(a)))
            side = (side - axis * axis.dot(side)).normalized()
            start, nrm = tree.ray_cast(base + side * 0.8, -side)[:2]
            if start is None:
                continue
            top = smooth(side.z, -0.3, 0.9)
            want = Vector((0, 1.0, 0.3 + 0.25 * top)) if side.z > -0.4 else Vector((side.x * 0.6, 0.5, -1.0))   # under the chest they sweep down
            lay(start, nrm, want, 0.38 + 0.14 * top + 0.05 * _rnd(k, 7.0), 0.1 + 0.025 * top, k)
            k += 1

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
