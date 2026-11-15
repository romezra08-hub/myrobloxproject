"""MagmaCrown pet: a little magma golem-king, remade from the game's blocky brown lava lump with orange
crystal spikes and a purple crystal beside it. Built from scratch by script.

    python models/pets/magmacrown.py --review out/magmacrown.png      # render the review sheet
    python models/pets/magmacrown.py --export models/export/magmacrown.fbx

Must-haves, checked in every review:
  1. The same creature: a dark lava rock lump crowned with orange crystals, with purple crystals.
  2. A little golem-king, clearly not the big slate Golem: one round, chubby basalt boulder with
     stubby arms and feet, soft cooled-lava lumps instead of slabs, orange and purple instead of green.
  3. Glowing orange cracks wandering over the rock, sunk into grooves, with warm rock round them.
  4. A friendly glowing face: two soft oval eyes and a wide smile.
  5. A crown of orange crystals on the head, amethyst shards on each shoulder.
  6. Matte rock with roughness variation, glossy crystals; about 3 studs tall; Body under 12k.

Round 2: cracks stop at the face (one ran into the smile like a scar); a cooled-lava crust of plates with deep joins on the rock (it looked like smooth grey clay); thinner cracks sunk into their grooves (they sat on top like worms); fewer cracks to keep the glow part small.

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
# ---- the magma crown ------------------------------------------------------------------------------

NAME = "MagmaCrown"
COL = {"basalt": hexc("#3A3331"), "basalt_lt": hexc("#5E5550"), "basalt_dk": hexc("#231E1D"), "heat": hexc("#A8401C"),
       "heat_lt": hexc("#E0702A"), "cry": hexc("#FF9A34"), "cry_lt": hexc("#FFD27A"), "cry_dk": hexc("#D2581C"),
       "ame": hexc("#8E52D6"), "ame_lt": hexc("#C9A0F4"), "ame_dk": hexc("#5A2E98"), "socket": hexc("#1A1210")}
SCALE = 1.0
BAKE = {"shade": 0.5, "rough": 0.88, "vary": 0.14}
BODY_C = Vector((0, 0, 1.18))
FACE = Vector((0, -0.75, 1.42))
FOCUS = FACE
FACE_DIST = 4.2


def _rnd(i, k=0.0):
    h = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return h - math.floor(h)


def crystal(r, h, sides=6):
    """A pointed crystal prism, base at the origin, pointing up +Z. g runs 0 at the base to 1 at the tip."""
    return lathe([(0.0, -0.02), (r * 0.9, -0.02), (r, h * 0.12), (r * 0.95, h * 0.72), (0.0, h)], segs=sides)


def crusted(name, rough=0.9, size=0.17):
    """The vertex paint 'col' under kit.scaly's cells, here large and with deep joins: a cooled lava crust."""
    m = kit.material(name, "#808080", rough=rough)
    kit.scaly(m, size=size, joins=0.42, vary=0.2, rough=rough)
    t = m.node_tree
    hsv = next(n for n in t.nodes if n.type == 'HUE_SAT')
    a = t.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', "col"
    t.links.new(a.outputs["Color"], hsv.inputs["Color"])
    return m


def in_face(p):
    return p.y < -0.3 and abs(p.x) < 0.5 and 1.0 < p.z < 1.85


def build():
    rock_m = crusted("Basalt", rough=0.9, size=0.17)
    glow = kit.material("GLOW_Magma", "#FF8A26", rough=0.4, emit=2.4)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- one fused rounded basalt boulder: body-head, stubby arms and feet ------------------------------
    clay = [ell(BODY_C, (0.84, 0.74, 0.9)),
            ell(BODY_C + Vector((0, 0.05, -0.35)), (0.9, 0.78, 0.6)),                 # a heavier base
            ell(BODY_C + Vector((0, -0.12, 0.52)), (0.62, 0.55, 0.42))]               # a rounded crown of the head
    for s in (-1, 1):
        clay += [ell((0.82 * s, -0.04, 1.1), (0.3, 0.3, 0.36)),                       # shoulders
                 ell((0.98 * s, -0.12, 0.72), (0.26, 0.26, 0.3)),                      # arms
                 ell((1.0 * s, -0.2, 0.46), (0.25, 0.25, 0.22)),                       # fists
                 ell((0.42 * s, -0.12, 0.17), (0.3, 0.38, 0.2))]                       # feet
    for k in range(14):                                                                # big soft lumps, like cooled lava
        a = k * 2.4
        z = 0.5 + 1.4 * _rnd(k, 1.0)
        rr = 0.75 * math.sqrt(max(1 - ((z - BODY_C.z) / 1.0) ** 2, 0.2))
        at = Vector((rr * math.cos(a), rr * math.sin(a) * 0.9, z))
        if at.y < -0.4 and abs(at.x) < 0.45 and 1.05 < z < 1.75:
            continue                                                                   # keep the face smooth
        clay.append(ell(at, (0.22, 0.22, 0.18)))
    skin = fuse(join(clay), voxel=0.024, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm

    # ---- the face: two glowing eyes and a wide glowing smile in soft sockets ---------------------------------
    eyes = [hit((0.24 * s, -3, 1.5), (0, 1, 0)) for s in (-1, 1)]
    smile = [hit((x, -3, 1.24 + 1.2 * x * x), (0, 1, 0))[0] for x in (-0.22, -0.15, -0.075, 0.0, 0.075, 0.15, 0.22)]

    # ---- glowing cracks wandering over the rock -------------------------------------------------------------
    cracks = []

    def wander(start, d, steps, step, seed):
        p, _, _, _ = tree.find_nearest(Vector(start))
        d = Vector(d).normalized()
        pts = [p]
        for i in range(steps):
            j = Vector((_rnd(seed + i, 3.1) - 0.5, _rnd(seed + i, 5.7) - 0.5, _rnd(seed + i, 9.3) - 0.5))
            d = (d + j * 1.1).normalized()
            q, n, _, _ = tree.find_nearest(p + d * step)
            if in_face(q):
                break
            d = (q - p).normalized()
            p = q
            pts.append(p)
        return pts
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.3
        z = 0.45 + 1.3 * _rnd(k, 2.2)
        start = BODY_C + Vector((math.cos(a), math.sin(a), (z - BODY_C.z)))
        if in_face(start) or (start.y < -0.2 and abs(start.x) < 0.7 and 0.95 < z < 1.9):
            a += 1.2                                                                   # not across the face
            start = BODY_C + Vector((math.cos(a), math.sin(a), (z - BODY_C.z)))
        d = Vector((-math.sin(a), math.cos(a), 0.6 * (_rnd(k, 4.4) - 0.5)))
        main = wander(start, d, 9, 0.09, k * 31)
        cracks.append(main)
        if k % 3 == 0 and len(main) > 5:
            cracks.append(wander(main[4], Vector((0, 0, -1)) + d * 0.3, 5, 0.08, k * 47 + 7))

    def crack_d(co):
        return min(poly_dist(co, cr) for cr in cracks)

    def carve(co, n):
        d = n * 0.03 * noise.noise(co * 2.2) + n * 0.01 * noise.noise(co * 9.0)
        for e, en in eyes:
            d -= en * 0.06 * (1 - smooth(((co - e) * Vector((1.3, 1, 1))).length, 0.1, 0.17))
        if co.y < -0.4:
            d -= n * 0.03 * (1 - smooth(poly_dist(co, smile), 0.02, 0.06))
        cd = crack_d(co)
        d -= n * 0.022 * (1 - smooth(cd, 0.01, 0.035))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 7500, keep=lambda co: 0.6 * (1 - smooth((Vector(co) - FACE).length, 0.25, 0.5)), factor=1.0)

    def rock_colour(co, n, g=0.0):
        col = mix(COL["basalt_dk"], COL["basalt"], smooth(n.z, -0.6, 0.1))
        col = mix(col, COL["basalt_lt"], 0.5 * smooth(n.z, 0.3, 1.0) * smooth(noise.noise(co * 3.0), -0.2, 0.5))
        cd = crack_d(co)
        col = mix(col, COL["heat"], 0.85 * (1 - smooth(cd, 0.03, 0.12)))                 # warm rock round each crack
        col = mix(col, COL["heat_lt"], 0.8 * (1 - smooth(cd, 0.01, 0.04)))
        if co.y < -0.3:
            for e, en in eyes:
                col = mix(col, COL["socket"], 0.6 * (1 - smooth(((co - e) * Vector((1.3, 1, 1))).length, 0.1, 0.16)))
            col = mix(col, COL["heat"], 0.7 * (1 - smooth(poly_dist(co, smile), 0.03, 0.07)))
        return col
    add("skin", skin, rock_m, rock_colour)

    for cr in cracks:
        if len(cr) < 3:
            continue
        lift = [p - (tree.find_nearest(p)[1]) * 0.008 for p in cr]
        add("glow", loft(lift, lambda t: 0.019 * math.sin(math.pi * min(0.15 + t, 1.0)) ** 0.5 + 0.004, segs=4, rings=len(cr) + 3), glow)
    for e, en in eyes:
        add("glow", facing(ell((0, 0, 0), (0.085, 0.115, 0.04), cuts=2), e - en * 0.03, en), glow)
    add("glow", loft([p - Vector((0, 0.0, 0)) for p in smile], lambda t: 0.028 * math.sin(math.pi * min(0.1 + t * 0.8 / 0.9, 1.0)) ** 0.4 + 0.008, segs=6, rings=14), glow)

    # ---- the crown: a ring of orange crystals on top of the head --------------------------------------------
    top, _ = hit((0, -0.12, 4), (0, 0, -1))
    for k in range(7):
        a = 2 * math.pi * k / 7 + math.pi / 2
        out = Vector((math.cos(a), math.sin(a), 0))
        h = 0.42 if k == 0 else 0.34 + 0.06 * math.cos(a * 2)
        base, nrm = hit(top + out * 0.34 + Vector((0, 0, 1)), (0, 0, -1))
        cr = crystal(0.085, h)
        cr.transform(Matrix.Rotation(math.radians(18), 4, Vector((-out.y, out.x, 0))) @ Matrix.Rotation(a, 4, 'Z'))
        cr.transform(M(base - Vector((0, 0, 0.04))))

        def cry_col(co, n, g):
            col = mix(COL["cry_dk"], COL["cry"], smooth(g, 0.0, 0.5))
            col = mix(col, COL["cry_lt"], 0.7 * smooth(g, 0.6, 1.0))
            return mix(col, COL["cry_lt"], 0.35 * smooth(n.z, 0.5, 1.0))
        add("crown", glossy(cr, 0.6), rock_m, cry_col)
    cr = crystal(0.11, 0.55)
    cr.transform(M(top - Vector((0, 0, 0.05))))
    add("crown", glossy(cr, 0.6), rock_m, lambda co, n, g: mix(mix(COL["cry_dk"], COL["cry"], smooth(g, 0.0, 0.5)), COL["cry_lt"], 0.7 * smooth(g, 0.6, 1.0)))

    # ---- amethyst shards on the shoulders ------------------------------------------------------------------------
    for s in (-1, 1):
        sh, sn = hit((0.86 * s, -0.04, 3), (0, 0, -1))
        for k, (dx, dy, tilt, h, r) in enumerate(((0.0, 0.0, 12, 0.4, 0.08), (0.12, 0.08, 34, 0.28, 0.065), (-0.1, 0.1, -8, 0.24, 0.06), (0.06, -0.12, 26, 0.22, 0.055))):
            cr = crystal(r, h)
            cr.transform(M(rot=(tilt * 0.5, tilt * s, 0)))
            cr.transform(M(sh + Vector((dx * s, dy, -0.05))))

            def ame_col(co, n, g):
                col = mix(COL["ame_dk"], COL["ame"], smooth(g, 0.0, 0.5))
                return mix(col, COL["ame_lt"], 0.6 * smooth(g, 0.65, 1.0) + 0.25 * smooth(n.z, 0.5, 1.0))
            add("amethyst", glossy(cr, 0.65), rock_m, ame_col)

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
