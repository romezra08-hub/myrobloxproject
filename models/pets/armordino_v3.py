"""ArmorDino pet: a sturdy armoured dinosaur, remade from the game's blocky brown-grey dinosaur with
yellow spikes and a cream jaw. Built from scratch by script.

    python models/pets/armordino.py --review out/armordino.png      # render the review sheet
    python models/pets/armordino.py --export models/export/armordino.fbx

Must-haves, checked in every review:
  1. The same pet: a big brown-grey dinosaur with yellow spikes on its back and a cream jaw.
  2. A grown, sturdy armoured dinosaur, not childish: broad low body on four pillar legs, a heavy head
     with small calm eyes under a brow plate, a club tail. Clearly not SailBack (sail-backed lizard)
     or RedRex (red horned dinosaur with green plates).
  3. Stone-grey and earth-brown pebbly hide with rows of keeled bony plates across the back.
  4. A few small amber spikes (flanks and the back corners of the head), a cream underjaw.
  5. Matte, varied roughness; about 3.2 studs tall; Body under 12k triangles.

Final: round 3.

Round 3: brow ridges grown into the skull with a lighter lid over a quarter of the eye, eyes turned more forward (the separate brow plates looked like floating eyebrows and the eyes sleepy); low scutes armouring the top of the head; a narrower snout and smaller beak (it read as a hippo nose).

Round 2: a calmer, older face: smaller eyes under a level lid and a dark brow ridge (pale round brows looked like cartoon eyebrows), a flatter underjaw shaded into the hide instead of a pale lip, a blunt beak; darker keeled plates, largest along the spine, in staggered rows of seven (pale round ones looked like pebbles); plates made from eight-sided lathes to fit the budget; thicker tail and a proper club; more stone grey on the back; slightly bigger spikes; duller nails.

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

# ---- the armoured dinosaur ------------------------------------------------------------------------

NAME = "ArmorDino"
COL = {"hide": hexc("#7C6654"), "hide_dk": hexc("#4F4036"), "hide_gr": hexc("#857F78"), "belly": hexc("#BBA587"),
       "cream": hexc("#D8C8A4"), "cream_dk": hexc("#AE9C78"), "plate": hexc("#857E74"), "plate_lt": hexc("#ABA394"),
       "plate_dk": hexc("#4E463E"), "amber": hexc("#E8A33A"), "amber_dk": hexc("#9C5A1E"), "amber_lt": hexc("#F8D27A"),
       "nail": hexc("#BDB094"), "line": hexc("#2E241E"), "pupil": hexc("#140E0A"), "white": hexc("#FFFFFF")}
SCALE = 1.35
BAKE = {"shade": 0.45, "rough": 0.9, "vary": 0.12}
HEAD = Vector((0, -1.85, 1.3))
FACE = HEAD + Vector((0, -0.3, 0.02))
FOCUS = FACE * SCALE
FACE_DIST = 4.6
TAIL = [Vector((0, 1.3, 1.5)), Vector((0, 1.9, 1.3)), Vector((0.08, 2.45, 1.0)), Vector((0.22, 2.9, 0.78))]
CLUB = Vector((0.28, 3.12, 0.72))
LEGS = [(-0.64, -0.78), (0.64, -0.78), (-0.66, 1.0), (0.66, 1.0)]


def osteoderm(rx, ry, h, keel=0.6):
    """A low oval bony plate with a sharp-ish ridge along its length (local Y), on the XY plane, rising up +Z.
    Few faces: a lathe of eight sides."""
    bm = lathe([(0.0, h), (0.55, 0.78 * h), (0.92, 0.3 * h), (1.0, -0.1 * h), (0.0, -0.45 * h)], segs=8)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
        if v.co.z > 0:
            v.co.z *= 1 - keel * 0.6 * min(abs(v.co.x) / rx, 1.0)
    return bm


def spike(r, h):
    return lathe([(0.0, -0.05), (r, -0.05), (r * 0.85, h * 0.25), (r * 0.45, h * 0.65), (0.0, h)], segs=7)


def build():
    hide_m = crusted("Hide", rough=0.92, size=0.07, joins=0.3, vary=0.14)
    bone_m = painted("Plates", dict(strength=0.08, mottle=0.14, fine=18.0, length=1.5), rough=0.9)
    eye_m = kit.material("Eyes", "#B87A2E", rough=0.08)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def hd(p):
        return HEAD + Vector(p)

    # ---- one fused skin: broad body, pillar legs, heavy head, club tail -------------------------------
    clay = [ell((0, 0.2, 1.45), (0.95, 1.4, 0.7)),
            ell((0, 0.25, 1.72), (0.86, 1.15, 0.5)),                              # the low dome of the back
            ell((0, -0.7, 1.35), (0.82, 0.62, 0.6)),                              # shoulders
            ell((0, 0.95, 1.42), (0.8, 0.62, 0.62)),                              # hips
            loft([Vector((0, -0.9, 1.45)), Vector((0, -1.35, 1.38)), Vector((0, -1.7, 1.33))], lambda t: lerp(0.52, 0.42, t), segs=16, rings=8),
            ell(hd((0, 0.08, 0.08)), (0.5, 0.5, 0.36)),                           # cranium
            ell(hd((0, -0.36, -0.03)), (0.3, 0.44, 0.24)),                        # snout
            ell(hd((0, -0.7, -0.08)), (0.17, 0.15, 0.15)),                        # a blunt beak at the tip
            ell(hd((0, -0.22, -0.16)), (0.33, 0.44, 0.16)),                       # the underjaw
            loft(TAIL, lambda t: lerp(0.52, 0.17, t ** 0.9), segs=14, rings=16),
            ell(CLUB, (0.32, 0.34, 0.22))]
    for s in (-1, 1):
        clay += [ell(CLUB + Vector((0.24 * s, 0.06, 0.0)), (0.22, 0.25, 0.18)),    # the two lobes of the club
                 ell(hd((0.36 * s, 0.18, 0.18)), (0.16, 0.18, 0.13)),             # the back corners of the skull
                 ell(hd((0.27 * s, -0.08, 0.22)), (0.15, 0.13, 0.08))]            # heavy brow ridges over the eyes
    for (x, y), front in zip(LEGS, (True, True, False, False)):
        if front:
            clay += [ell((x, y, 1.0), (0.3, 0.33, 0.45)),
                     loft([Vector((x * 1.02, y - 0.02, 0.85)), Vector((x * 1.03, y - 0.04, 0.42)), Vector((x * 1.03, y - 0.06, 0.15))], lambda t: lerp(0.25, 0.22, t), segs=14, rings=8)]
        else:
            clay += [ell((x, y, 1.1), (0.34, 0.5, 0.55)),
                     loft([Vector((x * 1.02, y + 0.05, 0.8)), Vector((x * 1.03, y, 0.42)), Vector((x * 1.03, y - 0.05, 0.15))], lambda t: lerp(0.27, 0.24, t), segs=14, rings=8)]
        clay.append(ell((x * 1.03, y - 0.1, 0.11), (0.28, 0.31, 0.12)))         # broad round feet
    skin = fuse(join(clay), voxel=0.026, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm

    eyes = []
    for s in (-1, 1):
        target = hd((0.3 * s, -0.12, 0.1))
        e, en = hit(target + Vector((1.2 * s, -0.9, 0.15)), target - (target + Vector((1.2 * s, -0.9, 0.15))))
        eyes.append((e, en))
    nostrils = [hit(hd((0.12 * s, -2, 0.06)), (0, 1, 0)) for s in (-1, 1)]

    def mouth_z(y, x):
        """The line where the cream underjaw meets the snout: level, turning up a little at the back."""
        return HEAD.z - 0.12 - 0.015 * smooth(abs(x), 0.0, 0.3) + 0.04 * smooth(y, HEAD.y - 0.25, HEAD.y + 0.15)

    def in_mouth(co):
        return co.y < HEAD.y + 0.18 and (co - hd((0, -0.35, -0.1))).length < 0.66

    def carve(co, n):
        d = n * 0.02 * noise.noise(co * 2.0) + n * 0.008 * noise.noise(co * 8.0)
        for e, en in eyes:
            d -= en * 0.03 * (1 - smooth((co - e).length, 0.06, 0.11))
        for e, en in nostrils:
            d -= en * 0.025 * (1 - smooth((co - e).length, 0.02, 0.05))
        if in_mouth(co):
            d -= n * 0.02 * (1 - smooth(abs(co.z - mouth_z(co.y, co.x)), 0.004, 0.02))
        if co.z < 0.25:                                                               # toe splits on the feet
            for x, y in LEGS:
                if (Vector((co.x, co.y)) - Vector((x * 1.03, y - 0.1))).length < 0.34 and co.y < y - 0.1:
                    for dx in (-0.09, 0.09):
                        d -= n * 0.02 * (1 - smooth(abs(co.x - x * 1.03 - dx), 0.004, 0.02)) * smooth(co.z, 0.24, 0.12)
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5800, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - FACE).length, 0.35, 0.6)), factor=1.0)

    def hide_colour(co, n, g=0.0):
        col = mix(COL["hide_dk"], COL["hide"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["hide_gr"], 0.75 * smooth(n.z, 0.1, 0.8) * smooth(noise.noise(co * 1.3), -0.5, 0.3))
        col = mix(col, COL["hide_dk"], 0.25 * smooth(noise.noise(co * 4.0 + Vector((3, 1, 2))), 0.2, 0.6))
        col = mix(col, COL["belly"], 0.7 * smooth(-n.z, 0.2, 0.7) * smooth(co.z, 0.6, 0.9))
        band = 0.5 + 0.5 * math.sin(co.y * 7.5)                                          # faint darker bands across the back
        col = mix(col, COL["hide_dk"], 0.25 * smooth(band, 0.7, 1.0) * smooth(n.z, 0.2, 0.7))
        col = mix(col, COL["hide_dk"], 0.35 * smooth(co.z, 0.35, 0.12))                 # dusty darker feet
        if in_mouth(co):
            below = co.z < mouth_z(co.y, co.x)
            if below:
                col = mix(col, mix(COL["cream_dk"], COL["cream"], smooth(-n.z, -0.6, 0.5)), smooth(mouth_z(co.y, co.x) - co.z, 0.0, 0.05))
            col = mix(col, COL["line"], 0.9 * (1 - smooth(abs(co.z - mouth_z(co.y, co.x)), 0.005, 0.014)))
        if co.y < HEAD.y + 0.6 and co.z < HEAD.z - 0.05 and -n.z > 0.3:
            col = mix(col, COL["cream"], 0.8 * smooth(-n.z, 0.3, 0.7))                   # pale throat under the jaw
        for e, en in nostrils:
            col = mix(col, COL["line"], 0.7 * (1 - smooth((co - e).length, 0.015, 0.035)))
        for e, en in eyes:
            col = mix(col, COL["hide_dk"], 0.5 * (1 - smooth((co - e).length, 0.07, 0.11)))
        return col
    add("skin", skin, hide_m, hide_colour)

    # ---- small calm amber eyes under a heavy brow plate ---------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.45 + Vector((0, -1, 0)) * 0.55).normalized()
        up = (Vector((0, 0, 1)) - en * en.dot(Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        frame = Matrix((ex, up, en)).transposed().to_4x4()
        eb = kit.ball((0.115, 0.1, 0.08), cuts=3)
        eb.transform(Matrix.Translation(e - en * 0.012) @ frame)
        add("eyes", eb, eye_m)
        pu = kit.ball((0.05, 0.06, 0.02), cuts=2)
        pu.transform(Matrix.Translation(e + en * 0.026) @ frame)
        add("pupils", pu, hide_m, COL["pupil"])
        add("pupils", ell(e + en * 0.034 + up * 0.02 - ex * 0.015, (0.012, 0.012, 0.006), cuts=2), hide_m, COL["white"])
        lid = kit.ball((0.15, 0.13, 0.11), cuts=6)                                   # a heavy, relaxed upper lid
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.y < 0.03 or v.co.z < -0.005], context='VERTS')
        lid.transform(Matrix.Translation(e - en * 0.008) @ frame @ Matrix.Rotation(math.radians(6 * s), 4, 'Z'))
        add("lids", lid, hide_m, COL["hide"])

    # ---- rows of keeled bony plates across the back, two half-rings on the neck --------------------------
    def plate_col(co, n, g):
        col = mix(COL["plate_dk"], COL["plate"], smooth(n.z, -0.2, 0.5))
        col = mix(col, COL["plate_lt"], 0.6 * smooth(n.z, 0.7, 1.0) * smooth(noise.noise(co * 9.0), -0.2, 0.4))
        col = mix(col, COL["plate_dk"], 0.4 * smooth(noise.noise(co * 22.0), 0.3, 0.6))           # small pits
        return col

    def plate_at(origin, direction, rx, ry, h, along=Vector((0, 1, 0))):
        p, nrm = hit(origin, direction)
        if p is None:
            return
        pl = osteoderm(rx, ry, h)
        z = nrm.normalized()
        y = (along - z * z.dot(along)).normalized()
        x = y.cross(z)
        pl.transform(Matrix.Translation(p - z * h * 0.35) @ Matrix((x, y, z)).transposed().to_4x4())
        add("plates", glossy(pl, 0.1), bone_m, plate_col)

    for i in range(9):
        y = -0.95 + i * 0.27
        stag = 0.5 if i % 2 else 0.0
        size = 1.0 - 0.25 * abs(i - 4) / 4
        for j in range(-3, 4):
            jj = j + stag
            if stag and j == 3:
                continue
            a = math.radians(jj * 24)
            o = Vector((math.sin(a), 0, math.cos(a)))
            k = 1.0 - 0.35 * abs(jj) / 3
            plate_at(Vector((0, y, 1.3)) + o * 3, -o, 0.15 * size * k, 0.14 * size * k, 0.09 * size * k)
    for px, py, r in ((0.0, 0.12, 0.13), (-0.17, 0.08, 0.1), (0.17, 0.08, 0.1), (-0.1, -0.12, 0.09), (0.1, -0.12, 0.09), (0.0, -0.32, 0.1)):
        plate_at(hd((px, py, 2.0)), (0, 0, -1), r, r * 1.1, 0.035)                     # low scutes armouring the head
    for y in (-1.15, -1.45):                                                          # neck half-rings
        for j in (-2, -1, 0, 1, 2):
            a = math.radians(j * 32)
            o = Vector((math.sin(a), 0, math.cos(a)))
            plate_at(Vector((0, y, 1.38)) + o * 3, -o, 0.11, 0.08, 0.06, along=Vector((1, 0, 0)) if j == 0 else Vector((0, 1, 0)))
    for k in range(4):                                                                # pairs down the tail
        t = 0.15 + 0.22 * k
        p = kit._spline(TAIL, t * 3)
        for s in (-1, 1):
            o = Vector((0.7 * s, 0, 0.7))
            plate_at(p + o * 3, -o, 0.11 - 0.015 * k, 0.12 - 0.015 * k, 0.06)

    # ---- a few small amber spikes: along the flanks and at the back corners of the head -------------------
    def spike_col(co, n, g):
        col = mix(COL["amber_dk"], COL["amber"], smooth(g, 0.0, 0.45))
        return mix(col, COL["amber_lt"], 0.7 * smooth(g, 0.7, 1.0))

    def spike_at(origin, direction, r, h, lean):
        p, nrm = hit(origin, direction)
        if p is None:
            return
        sp = spike(r, h)
        facing(sp, p - nrm * 0.03, (nrm + Vector(lean)).normalized())
        add("spikes", glossy(sp, 0.35), bone_m, spike_col)
    for s in (-1, 1):
        for y, h in ((-0.55, 0.24), (-0.05, 0.3), (0.45, 0.28), (0.9, 0.22)):
            o = Vector((math.sin(math.radians(78)) * s, 0, math.cos(math.radians(78))))
            spike_at(Vector((0, y, 1.45)) + o * 3, -o, 0.07, h, (0, 0.25, 0.15))
        spike_at(hd((0.36 * s, 0.25, 0.18)) + Vector((2 * s, 0.6, 0.3)), Vector((-2 * s, -0.6, -0.3)), 0.06, 0.2, (0.3 * s, 0.9, 0.2))
        spike_at(CLUB + Vector((0.35 * s, 0, 0)) + Vector((2 * s, 0, 0.4)), Vector((-2 * s, 0, -0.4)), 0.05, 0.13, (0, 0.2, 0))

    # ---- blunt cream toenails --------------------------------------------------------------------------
    for x, y in LEGS:
        for dx in (-0.15, 0.0, 0.15):
            p, nrm = hit((x * 1.03 + dx, y - 1.5, 0.08), (0, 1, 0))
            if p is None:
                continue
            nail = ell((0, 0, 0), (0.07, 0.05, 0.055), cuts=1)
            nail.transform(M(p + Vector((0, 0.01, -0.01))))
            add("nails", glossy(nail, 0.3), bone_m, lambda co, n, g: mix(COL["cream_dk"], COL["nail"], smooth(n.z, -0.3, 0.6)))

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
