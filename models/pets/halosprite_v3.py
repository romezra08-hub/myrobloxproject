"""HaloSprite pet: a gentle celestial sprite, remade from the game's golden angel (one big eyeball inside a
gold ring with long white blade wings, which read as creepy). Built from scratch by script.

    python models/pets/halosprite.py --review out/halosprite.png      # render the review sheet
    python models/pets/halosprite.py --export models/export/halosprite.fbx

Must-haves, checked in every review:
  1. The same pet: a round white-and-gold winged thing inside a tilted gold ring, with white wings.
  2. Gentle, never creepy: a small round pearl body with a cute face and two eyes (no lone eyeball).
  3. A glowing gold halo ring tilted round the body, a few tiny gold star sparkles (GLOW).
  4. Two soft feathered wings, shorter than the original's blades; a wispy tail instead of feet,
     its tip at z=0.
  5. Pearl with a soft gold glow, satin not plastic; about 3 studs tall; Body under 12k triangles.

Final: round 3.

Round 3: one tail flowing out of a teardrop body (two wisps under a wide round body read as a tooth); a rounder top of the head, a swept-back wisp instead of the onion curl; a scatter of tiny gold freckles on the pearl.

Round 2: bigger soft wings of round-tipped feathers (the small spiky fans read as leaves); no cheek lumps (they looked like jowls); stronger blush; a warm gold glow round the pearl edge; thinner tail with a second wisp; sharp four-point sparkles; a deeper gold halo.

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

# ---- the halo sprite ------------------------------------------------------------------------------

NAME = "HaloSprite"
COL = {"pearl": hexc("#F7F2EA"), "pearl_sh": hexc("#D6CFE4"), "pearl_pk": hexc("#F7E1E3"), "pearl_bl": hexc("#E2ECF6"),
       "gold": hexc("#F0C25A"), "gold_dk": hexc("#C08A30"), "gold_lt": hexc("#FFE6A0"), "blush": hexc("#F2A9B4"),
       "line": hexc("#6A4638"), "white": hexc("#FFFFFF"), "feather": hexc("#FBF8F2"), "feather_sh": hexc("#DCD6E2")}
SCALE = 1.1
BAKE = {"shade": 0.38, "rough": 0.8, "vary": 0.12}
BODY_C = Vector((0, 0, 1.55))
FACE = Vector((0, -0.55, 1.55))
FOCUS = FACE * SCALE
FACE_DIST = 3.0
TAIL = [Vector((0, 0.04, 1.25)), Vector((0.02, 0.1, 0.95)), Vector((0.14, 0.2, 0.66)), Vector((0.26, 0.26, 0.4)),
        Vector((0.22, 0.24, 0.16)), Vector((0.06, 0.18, 0.04)), Vector((-0.08, 0.12, 0.1)), Vector((-0.1, 0.1, 0.24))]


def feather(L, w, th=0.03, cuts=3, curve=0.06):
    """A soft rounded feather lying along +X from the origin, its width along Z and its thickness along Y.
    g runs 0 at the root to 1 at the tip."""
    bm = kit.ball((1, 1, 1), cuts=cuts)
    lg = bm.verts.layers.float.new("g")
    for v in bm.verts:
        u = min(max(v.co.x + 0.5, 0.0), 1.0)
        f = math.sqrt(max(1 - (2 * u - 1) ** 2, 0.0)) * (0.55 + 0.45 * smooth(u, 0.0, 0.6)) + 0.04
        x = u * L
        z = v.co.z * 2 * w * f + curve * L * u * u
        y = v.co.y * 2 * th * (0.4 + 0.6 * f) + 0.5 * curve * L * u * u
        v.co = Vector((x, y, z))
        v[lg] = u
    return bm


def place_frame(bm, at, d, n):
    """Local X -> d, local Y -> n (made perpendicular), local Z -> their cross."""
    d = Vector(d).normalized()
    n = (Vector(n) - d * d.dot(Vector(n))).normalized()
    z = d.cross(n)
    m = Matrix((d, n, z)).transposed().to_4x4()
    bm.transform(M(at) @ m)
    return bm


def sparkle(r, th=0.03):
    """A four-pointed star in the XZ plane, `r` from the centre to a point."""
    bm = lathe([(0.0, -1.0), (1.0, 0.0), (0.0, 1.0)], segs=16)
    bm.transform(M(rot=(90, 0, 0)))
    for v in bm.verts:
        a = math.atan2(v.co.z, v.co.x)
        k = 0.12 + 0.88 * abs(math.cos(2 * a)) ** 12
        rr = math.hypot(v.co.x, v.co.z)
        v.co.x *= r * k
        v.co.z *= r * k
        v.co.y *= th * (1 - 0.6 * rr)
    return bm


def build():
    pearl_m = painted("Pearl", dict(strength=0.05, mottle=0.06, fine=12.0, length=2.0), rough=0.6)
    plume_m = painted("Plumes", dict(strength=0.1, mottle=0.05, fine=44.0, length=5.0), rough=0.88)
    eye_m = kit.material("Eyes", "#2E2236", rough=0.06)
    glow = kit.material("GLOW_Halo", "#FFC444", rough=0.4, emit=2.2)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- one fused pearl skin: a round body with a soft wispy tail -----------------------------------
    clay = [ell(BODY_C + Vector((0, 0, 0.03)), (0.6, 0.56, 0.6)),
            ell(BODY_C + Vector((0, 0.03, -0.3)), (0.44, 0.42, 0.42)),                  # the lower half narrows into the tail
            loft(TAIL, lambda t: 0.4 * (1 - t) ** 1.6 + 0.016, segs=16, rings=30)]
    tip = loft([Vector((0, 0.0, 2.08)), Vector((0.0, 0.04, 2.24)), Vector((0.0, 0.14, 2.32)), Vector((0.0, 0.22, 2.28))],
               lambda t: 0.075 * (1 - t) ** 1.2 + 0.014, segs=10, rings=10)            # a small wisp on top, swept back
    clay.append(tip)
    skin = fuse(join(clay), voxel=0.018, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm

    eyes = [hit((0.2 * s, -3, 1.62), (0, 1, 0)) for s in (-1, 1)]
    smile = [hit((x, -3, 1.42 + 2.2 * x * x), (0, 1, 0))[0] for x in (-0.07, -0.045, -0.02, 0.0, 0.02, 0.045, 0.07)]

    def carve(co, n):
        d = n * 0.004 * noise.noise(co * 6.0)
        for e, en in eyes:
            d -= en * 0.02 * (1 - smooth(((co - e) * Vector((1.0, 1, 0.8))).length, 0.08, 0.14))
        if co.y < -0.3:
            d -= n * 0.008 * (1 - smooth(poly_dist(co, smile), 0.006, 0.018))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 5200, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - FACE).length, 0.25, 0.45)), factor=1.0)

    freckles = []
    for k in range(70):
        d = Vector((_rnd(k, 1.1) - 0.5, _rnd(k, 2.3) - 0.5, _rnd(k, 3.7) - 0.5)).normalized()
        if d.y < -0.2 and d.z < 0.5:                                                            # not on the face
            continue
        freckles.append(tree.find_nearest(BODY_C + d * 0.7)[0])
    freckles = [f for f in freckles if f.z > 1.2]

    def pearl_colour(co, n, g=0.0):
        col = mix(COL["pearl_sh"], COL["pearl"], smooth(n.z, -0.7, 0.2))
        col = mix(col, COL["pearl_pk"], 0.5 * smooth(noise.noise(co * 2.5), 0.0, 0.6))          # pearly shifts of hue
        col = mix(col, COL["pearl_bl"], 0.4 * smooth(noise.noise(co * 2.5 + Vector((5, 1, 3))), 0.1, 0.6))
        rim = 1 - abs(n.y)                                                                      # a warm gold glow round the edge
        col = mix(col, COL["gold_lt"], 0.35 * smooth(rim, 0.55, 0.95) * smooth(co.z, 2.0, 1.2))
        low = smooth(co.z, 1.15, 0.35)                                                          # the tail warms into gold
        col = mix(col, COL["gold_lt"], 0.75 * low)
        col = mix(col, COL["gold"], 0.6 * smooth(co.z, 0.6, 0.12))
        col = mix(col, COL["gold_lt"], 0.5 * smooth(co.z, 2.1, 2.3))                           # and the wisp on top
        fd = min((co - f).length for f in freckles)                                            # a scatter of tiny gold freckles
        col = mix(col, COL["gold"], 0.8 * (1 - smooth(fd, 0.016, 0.032)))
        if co.y < -0.2:
            for e, en in eyes:                                                                  # blush under each eye
                b = ((co - (e + Vector((0.08 * (1 if e.x > 0 else -1), 0.0, -0.14)))) * Vector((1, 1, 1.6))).length
                col = mix(col, COL["blush"], 0.75 * (1 - smooth(b, 0.035, 0.085)))
            col = mix(col, COL["line"], 0.9 * (1 - smooth(poly_dist(co, smile), 0.006, 0.013)))
        return col
    add("skin", glossy(skin, 0.3), pearl_m, pearl_colour)

    # ---- two big soft eyes with catchlights ----------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + Vector((0, -1, 0)) * 0.6).normalized()
        up = (Vector((0, 0, 1)) - en * en.dot(Vector((0, 0, 1)))).normalized()
        ex = up.cross(en).normalized()
        eb = kit.ball((0.13, 0.17, 0.08), cuts=3)
        eb.transform(Matrix.Translation(e - en * 0.01) @ Matrix((ex, up, en)).transposed().to_4x4())
        add("eyes", eb, eye_m)
        front = e + en * 0.028
        add("glints", ell(front + up * 0.035 - ex * 0.022 * s * -1, (0.024, 0.026, 0.01), cuts=2), pearl_m, COL["white"])
        add("glints", ell(front - up * 0.04 + ex * 0.02 * s * -1, (0.011, 0.011, 0.006), cuts=2), pearl_m, COL["white"])

    # ---- two soft feathered wings, shorter than the original's blades ------------------------------------
    for s in (-1, 1):
        root = Vector((0.36 * s, 0.4, 1.72))
        for k in range(6):                                                                      # long flight feathers
            a = math.radians(-6 + 15 * k)
            d = Vector((s * math.cos(a), 0.3, math.sin(a) * 1.1))
            L = 1.12 - 0.07 * abs(k - 2.6) ** 1.5
            f = feather(L, 0.15, th=0.025, curve=0.07)
            at = root + Vector((0.02 * s * k, 0.03 * k, -0.04 * k))
            place_frame(f, at, d, Vector((0, 1, 0)))

            def fcol(co, n, g, at=at, d=d.normalized(), L=L):
                q = co - at
                along = q.dot(d)
                lat = (q - d * along).length
                barb = 0.5 + 0.5 * math.sin((along + lat * 2.2) * 70.0)
                col = mix(COL["feather_sh"], COL["feather"], smooth(n.z + 0.4 * (-n.y), -0.6, 0.4))
                col = mix(col, COL["feather_sh"], 0.25 * barb * smooth(g, 0.15, 0.4))
                col = mix(col, COL["gold_lt"], 0.75 * smooth(g, 0.72, 0.95))
                return mix(col, COL["gold_dk"], 0.6 * (1 - smooth(lat, 0.004, 0.012)) * smooth(g, 0.05, 0.2) * smooth(g, 0.85, 0.6))
            add("wings", f, plume_m, fcol)
        for k in range(5):                                                                      # shorter coverts over their roots
            a = math.radians(2 + 16 * k)
            d = Vector((s * math.cos(a), 0.2, math.sin(a)))
            L = 0.62 - 0.04 * abs(k - 2)
            f = feather(L, 0.15, th=0.03, curve=0.05)
            at = root + Vector((-0.04 * s, -0.07, -0.02 * k + 0.02))
            place_frame(f, at, d, Vector((0, 1, 0)))

            def ccol(co, n, g):
                col = mix(COL["feather_sh"], COL["feather"], smooth(n.z + 0.4 * (-n.y), -0.6, 0.4))
                return mix(col, COL["gold_lt"], 0.45 * smooth(g, 0.75, 1.0))
            add("wings", f, plume_m, ccol)

    # ---- a glowing gold halo tilted round the body, a forehead star and sparkles ---------------------------
    ring = lathe([(0.86 + 0.04 * math.cos(t), 0.024 * math.sin(t)) for t in (2 * math.pi * j / 6 for j in range(6))], segs=56, closed=True)
    ring.transform(M(BODY_C + Vector((0, 0.02, 0.02)), rot=(24, -10, 0)))
    add("glow", ring, glow)
    star_at, star_n = hit((0, -3, 1.9), (0, 1, 0))
    st = sparkle(0.06, th=0.03)
    place_frame(st, star_at - star_n * 0.004, Vector((1, 0, 0)), star_n * -1)
    add("glow", st, glow)
    for at, r, spin in (((-0.98, -0.25, 2.35), 0.11, 0), ((1.0, -0.35, 1.05), 0.09, 20), ((0.78, -0.2, 2.62), 0.065, 10), ((-0.75, -0.45, 0.7), 0.06, 30)):
        st = sparkle(r, th=0.035)
        st.transform(M(at, rot=(0, spin, 0)))
        add("glow", st, glow)

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
