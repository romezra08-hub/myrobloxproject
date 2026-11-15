"""FrostWolf pet: a midnight-blue arctic wolf, remade from the game's navy-blue wolf with white ice spikes
on its back. Built from scratch by script.

    python models/pets/frostwolf.py --review out/frostwolf.png      # render the review sheet
    python models/pets/frostwolf.py --export models/export/frostwolf.fbx

Must-haves, checked in every review:
  1. The same pet: a navy-blue wolf with pale ice spikes along its back and a tail curled up.
  2. Thick, fluffy winter fur: a full ruff, clumpy tufts at the cheeks, chest and tail, fading from
     midnight blue to white at the chest, under the jaw and at the tail tip.
  3. A ridge of a few clear-blue ice crystals along the spine.
  4. A friendly face: pale blue eyes, open and soft, a small smile, rounded ears with white fluff inside.
  5. Clearly not the grey Wolf (silver locks, violet crystals) or the LavaWolf (black and ember, sleek):
     stockier and fluffier, blue and white. Matte with varied roughness; about 3 studs tall; Body under 12k.

Final: round 2.

Round 2: a longer muzzle with white only under it and on the lower cheek fluff, a smaller bib starting lower (the big white lower face read as a beard and looked grumpy); the eyes tilted up at the outer corners (they drooped); chest tufts spread outward, fluffy flanks and hocks, deeper fur grooves and stronger streaks (it looked smooth); a tail of smaller tufts with a round tip (the tip split like fingers); bigger ice crystals; blue-grey ear insides; scaled up to about 2.8 studs.

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

# ---- the frost wolf -------------------------------------------------------------------------------

NAME = "FrostWolf"
COL = {"navy": hexc("#1F2B4E"), "navy_lt": hexc("#3A5288"), "navy_dk": hexc("#141B33"), "frost": hexc("#7E9CCB"),
       "white": hexc("#EEF3FA"), "white_sh": hexc("#C4D0E2"), "ice": hexc("#9ED6F4"), "ice_dk": hexc("#4E92D0"),
       "ice_lt": hexc("#E9F8FF"), "pupil": hexc("#0E1226"), "glint": hexc("#FFFFFF"), "nose": hexc("#151A2A"),
       "line": hexc("#10162A"), "ear_in": hexc("#AFC0DC")}
SCALE = 1.14
BAKE = {"shade": 0.42, "rough": 0.9, "vary": 0.1}
HEAD = Vector((0, -0.98, 2.0))
HEAD_M = M(HEAD, rot=(-2, 0, 4))
NECK = [Vector((0, -0.48, 1.42)), Vector((0, -0.72, 1.72)), Vector((0, -0.9, 1.92))]
TAIL = [Vector((0, 0.84, 1.48)), Vector((0, 1.14, 1.56)), Vector((0, 1.34, 1.8)), Vector((0, 1.3, 2.08)), Vector((0, 1.12, 2.2))]
SPINE = [Vector((0, -0.62, 1.86)), Vector((0, -0.3, 1.8)), Vector((0, 0.1, 1.76)), Vector((0, 0.5, 1.74)), Vector((0, 0.84, 1.62))]
FACE = HEAD + Vector((0, -0.3, -0.05))
FOCUS = FACE * SCALE
FACE_DIST = 3.4
LEGS = [(-0.22, -0.5, True), (0.22, -0.5, True), (-0.24, 0.6, False), (0.24, 0.6, False)]


def tuft(at, d, length=0.16, r=0.06):
    at, d = Vector(at), Vector(d).normalized()
    return loft([at - d * 0.04, at + d * length * 0.5, at + d * length + Vector((0, 0, -0.015))], lambda t: r * (1 - t) ** 0.9 + 0.008, segs=8, rings=5)


def build():
    fur_m = painted("Fur", dict(strength=0.42, mottle=0.12, fine=34.0, length=7.0), rough=0.93)
    ice_m = painted("Ice", dict(strength=0.05, mottle=0.08, fine=8.0, length=2.0), rough=0.35)
    eye_m = kit.material("Eyes", "#A9DAF4", rough=0.06)
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

    # ---- one fused skin: stocky body, sturdy legs, a fluffy ruff, a broad head and a bushy curled tail ------
    clay = [ell((0, 0.08, 1.4), (0.38, 0.68, 0.38)),
            ell((0, -0.38, 1.42), (0.43, 0.44, 0.48)),                          # deep chest
            ell((0, 0.58, 1.42), (0.36, 0.38, 0.37)),                            # hips
            loft(NECK, lambda t: lerp(0.34, 0.26, t), segs=14, rings=8),
            loft(TAIL, lambda t: 0.12 + 0.07 * math.sin(math.pi * min(t * 1.1, 1.0)) - 0.05 * t ** 3, segs=12, rings=18),
            ell(hd((0, 0.04, 0.03)), (0.29, 0.29, 0.26)),                        # cranium
            loft([hd((0, -0.12, -0.05)), hd((0, -0.3, -0.09)), hd((0, -0.46, -0.11))], lambda t: lerp(0.15, 0.085, t), segs=14, rings=8),
            ell(hd((0, -0.3, -0.15)), (0.09, 0.17, 0.055))]
    for s in (-1, 1):
        clay += [ell(hd((0.17 * s, -0.06, -0.07)), (0.14, 0.14, 0.13))]          # full cheeks
    for x, y, front in LEGS:
        if front:
            clay += [ell((x * 1.1, y, 1.2), (0.19, 0.23, 0.33)),
                     loft([Vector((x, y - 0.02, 1.0)), Vector((x, y - 0.04, 0.55)), Vector((x, y - 0.03, 0.22)), Vector((x, y - 0.06, 0.1))],
                          lambda t: 0.085 + 0.05 * (1 - smooth(t, 0.1, 0.6)), segs=12, rings=10)]
        else:
            clay += [ell((x * 1.1, y, 1.2), (0.21, 0.33, 0.35)),
                     loft([Vector((x, y + 0.1, 1.0)), Vector((x, y + 0.24, 0.6)), Vector((x, y + 0.13, 0.3)), Vector((x, y + 0.1, 0.1))],
                          lambda t: 0.085 + 0.06 * (1 - smooth(t, 0.05, 0.45)), segs=12, rings=10)]
        py = y - 0.1 if front else y + 0.04
        clay.append(ell((x, py, 0.07), (0.115, 0.15, 0.07)))
    # clumpy tufts: the ruff round the neck, cheek fluff, the chest, elbows and the tail
    for k in range(22):
        a = math.radians(-160 + 320 * k / 21)
        base = kit._spline(NECK, 0.6 + 0.6 * _rnd(k, 1.0))
        side = Vector((math.sin(a), 0, math.cos(a)))
        at = base + side * 0.3
        d = side * 0.5 + Vector((0, 0.55, -0.35))
        if side.z < -0.2:
            d = side * 0.4 + Vector((0, -0.1, -0.9))
        clay.append(tuft(at, d, 0.2 + 0.06 * _rnd(k, 2.0), 0.085))
    for s in (-1, 1):
        for k in range(3):
            clay.append(tuft(hd((0.24 * s, 0.0 - 0.04 * k, -0.08 - 0.05 * k)), Vector((0.6 * s, 0.6, -0.5)), 0.14, 0.06))     # cheek fluff
        clay.append(tuft((0.32 * s, -0.42, 1.12), Vector((0.2 * s, 0.4, -1)), 0.16, 0.07))                                    # elbows
    for k in range(7):
        x = 0.1 * (k - 3)
        clay.append(tuft((x, -0.76 + 0.03 * abs(k - 3), 1.32 - 0.05 * abs(k - 3) + 0.04 * _rnd(k, 3.0)), Vector((x * 3, -0.5, -0.8)), 0.13, 0.07))   # chest
    for s in (-1, 1):                                                                # fluffy flanks and haunches
        for k in range(7):
            y = -0.2 + 0.16 * k
            z = 1.35 + 0.15 * math.sin(k * 1.9)
            clay.append(tuft((0.33 * s, y, z), Vector((0.5 * s, 0.8, -0.35)), 0.12, 0.06))
        clay.append(tuft((0.3 * s, 0.75, 0.95), Vector((0.2 * s, 0.6, -1)), 0.14, 0.07))                               # hocks
    for k in range(20):
        t = 0.15 + 0.75 * k / 19
        p = kit._spline(TAIL, t * 4)
        a = k * 2.4
        side = Vector((math.cos(a), 0.0, math.sin(a)))
        tan = (kit._spline(TAIL, min(t * 4 + 0.1, 4)) - p).normalized()
        clay.append(tuft(p + side * 0.1, (tan * 0.8 + side * 0.45), 0.14, 0.06))
    clay.append(ell(TAIL[-1] + Vector((0, -0.02, 0.0)), (0.12, 0.12, 0.11)))           # a round fluffy tip
    skin = fuse(join(clay), voxel=0.019, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.125 * s, -1.5, 0.05)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.075)), fwd)
    mouth = []
    for s in (-1, 1):
        mouth.append([hit(hd((0, -1.5, -0.15)), fwd)[0], hit(hd((0.05 * s, -1.5, -0.165)), fwd)[0], hit(hd((0.1 * s, -1.5, -0.15)), fwd)[0],
                      hit(hd((0.135 * s, -1.5, -0.125)), fwd)[0]])
    mouth.append([hit(hd((0, -1.5, -0.1)), fwd)[0], hit(hd((0, -1.5, -0.15)), fwd)[0]])
    mouth = [[p for p in m if p is not None] for m in mouth]

    def carve(co, n):
        d = n * 0.018 * noise.noise(Vector((co.x * 11, co.y * 11, co.z * 2.5)))         # fur grooves
        for e, en in eyes:
            d -= en * 0.018 * (1 - smooth((co - e).length, 0.065, 0.1))
        if (co - nose_at).length < 0.3:
            d -= n * 0.01 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.004, 0.014))
        if co.z < 0.14 and n.y < 0.3:
            for x, y, front in LEGS:
                py = y - 0.1 if front else y + 0.04
                if abs(co.y - py) < 0.17 and abs(co.x - x) < 0.12:
                    for dx in (-0.036, 0.036):
                        d -= n * 0.014 * (1 - smooth(abs(co.x - x - dx), 0.003, 0.012)) * smooth(co.z, 0.13, 0.07)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 7600, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.2, -0.04))).length, 0.2, 0.42)),
                                                    0.3 * (1 - smooth((Vector(co) - HEAD).length, 0.35, 0.55))), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(COL["navy_dk"], COL["navy"], smooth(n.z, -0.5, 0.3))
        col = mix(col, COL["navy_lt"], 0.55 * smooth(n.z, 0.35, 1.0) * smooth(noise.noise(Vector((co.x * 5, co.y * 5, co.z * 1.5))), -0.3, 0.5))
        col = mix(col, COL["frost"], 0.25 * smooth(noise.noise(Vector((co.x * 14, co.y * 14, co.z * 3))), 0.35, 0.7))   # frosted hair tips
        # white chest, throat and belly
        bib = (co - Vector((0, -0.8, 1.38))) * Vector((1 / 0.26, 1 / 0.3, 1 / 0.42))
        col = mix(col, COL["white"], 0.95 * (1 - smooth(bib.length, 0.65, 1.0)))
        col = mix(col, COL["white_sh"], 0.8 * smooth(-n.z, 0.2, 0.7) * smooth(co.z, 0.7, 1.0))
        # the tail fades to a white tip
        if poly_dist(co, TAIL) < 0.4 and co.y > 0.9:
            col = mix(col, COL["white"], smooth((co - TAIL[0]).length, 0.55, 0.85))
        col = mix(col, COL["navy_lt"], 0.35 * smooth(co.z, 0.25, 0.05))                     # lighter toes
        if (co - HEAD).length < 0.55:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["white"], 0.95 * smooth(p.z, -0.1, -0.14) * smooth(p.y, -0.1, -0.22))      # white under the muzzle and jaw
            col = mix(col, COL["frost"], 0.55 * smooth(p.y, -0.22, -0.36) * smooth(p.z, -0.02, -0.09))    # a frosted muzzle
            col = mix(col, COL["white"], 0.85 * smooth(abs(p.x), 0.2, 0.27) * smooth(p.z, -0.05, -0.14))  # and the cheek fluff
            for e, en in eyes:                                                                 # pale brows over the eyes
                b = co - (e + Vector((0.02 * (1 if e.x > 0 else -1), 0, 0.085)))
                col = mix(col, COL["frost"], 0.7 * (1 - smooth((b * Vector((1, 1, 2.2))).length, 0.025, 0.05)))
                col = mix(col, COL["line"], 0.8 * (1 - smooth((co - e).length, 0.068, 0.088)))
            if (co - nose_at).length < 0.3:
                col = mix(col, COL["line"], 0.9 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.005, 0.012)))
        return col
    add("skin", skin, fur_m, fur_colour)

    # ---- pale blue friendly eyes -------------------------------------------------------------------------
    EW, EH, ED = 0.1, 0.08, 0.038
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        up = (R @ Vector((0, 0, 1)) - en * en.dot(R @ Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        tilt = Matrix.Rotation(math.radians(8 * s), 4, en)
        basis = Matrix((ex, up, en)).transposed().to_4x4()
        place = Matrix.Translation(e - en * 0.014) @ tilt @ basis
        eb = kit.ball((EW, EH, ED * 2), cuts=3)
        eb.transform(place)
        add("eyes", eb, eye_m)
        front = e - en * 0.014 + en * (ED - 0.006)
        pupil = kit.ball((0.045, 0.052, 0.016), cuts=2)
        pupil.transform(Matrix.Translation(front) @ tilt @ basis)
        add("pupils", pupil, fur_m, COL["pupil"])
        add("pupils", ell(front + en * 0.006 + up * 0.022 + ex * 0.018 * s, (0.014, 0.014, 0.006), cuts=2), fur_m, COL["glint"])
        lid = kit.ball((EW * 1.12, EH * 1.16, ED * 2.25), cuts=6)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < EH * 0.3 or v.co.z < -0.004], context='VERTS')
        lid.transform(place)
        add("lids", lid, fur_m, COL["navy"])

    nose = ell((0, 0, 0), (0.075, 0.05, 0.048), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.6 + 0.4 * smooth(v.co.z, -0.045, 0.03)
    nose.transform(M(nose_at + fwd * -0.01) @ R.to_4x4())
    add("nose", glossy(nose, 0.45), fur_m, COL["nose"])

    # ---- rounded ears with white fluff inside ---------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.14 * s, 0.07, 0.17))
        pts = [root, root + Vector((0.04 * s, 0.01, 0.12)), root + Vector((0.07 * s, 0.03, 0.22)), root + Vector((0.08 * s, 0.04, 0.28))]
        ear = loft(pts, lambda t: 0.14 * (1 - t ** 1.6) ** 0.7 + 0.012, segs=12, rings=12, flat=0.45)
        for v in ear.verts:
            gg = v[ear.verts.layers.float["g"]]
            off = v.co - kit._spline(pts, gg * 3)
            if off.y < 0:
                v.co.y -= off.y * 0.55 * smooth(gg, 0.05, 0.25) * smooth(gg, 1.0, 0.8)

        def ear_col(co, n, g):
            col = mix(COL["navy_dk"], COL["navy"], smooth(n.z, -0.3, 0.5))
            inner = smooth(-n.y, 0.3, 0.75) * smooth(g, 0.05, 0.2) * smooth(g, 0.9, 0.7)
            return mix(col, COL["ear_in"], 0.9 * inner)
        add("ears", ear, fur_m, ear_col)

    # ---- a ridge of clear-blue ice crystals along the spine -----------------------------------------------
    def ice_col(co, n, g):
        col = mix(COL["ice_dk"], COL["ice"], smooth(g, 0.0, 0.5))
        col = mix(col, COL["ice_lt"], 0.8 * smooth(g, 0.65, 1.0))
        return mix(col, COL["ice_lt"], 0.4 * smooth(n.z + n.x * 0.3, 0.4, 1.0))
    for k, (t, h, r, lean) in enumerate(((0.35, 0.26, 0.07, 0), (0.85, 0.38, 0.085, 6), (1.35, 0.44, 0.095, -4), (1.9, 0.36, 0.085, 5), (2.45, 0.26, 0.07, -3))):
        p = kit._spline(SPINE, t)
        top, nrm = hit(p + Vector((0, 0, 2)), (0, 0, -1))
        cr = crystal(r, h)
        cr.transform(M(rot=(-18, lean, k * 23)))
        cr.transform(M(top - Vector((0, 0, 0.05))))
        add("ice", glossy(cr, 0.75), ice_m, ice_col)
        for s in (-1, 1):
            if k in (1, 2, 3):
                cr = crystal(r * 0.6, h * 0.5)
                cr.transform(M(rot=(-12, 30 * s, k * 40)))
                cr.transform(M(top + Vector((0.07 * s, 0.05, -0.06))))
                add("ice", glossy(cr, 0.75), ice_m, ice_col)

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
