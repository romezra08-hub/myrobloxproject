"""PlumedLion pet: a proud lion wearing a sunburst mane of feathers, remade from the game's turkey lion.
Built from scratch by script.

    python models/pets/plumedlion.py --review out/plumedlion.png      # render the review sheet
    python models/pets/plumedlion.py --export models/export/plumedlion.fbx

The original is a tan lion whose mane is a fan of brown turkey feathers, with red feather wings. The
remake keeps that and makes it noble. Must-haves, checked in every review:
  1. A golden-tan lion standing four-square: deep chest, sturdy legs with big paws, cream muzzle,
     chin and belly, a tufted tail.
  2. A majestic mane of layered bronze-brown feathers fanning round the head like a sunburst, each
     barred near the tip and pale at the end like a turkey's fan.
  3. Two red feather wings folded high above the back.
  4. A calm, noble lion face: almond amber eyes with dark rims, a broad nose, whisker pads, a
     closed mouth, small round ears.
  5. Matte painted fur and feathers with crease shading; 3-4.5 studs tall; Body under 9k triangles.

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
from mathutils import Vector, noise  # noqa: E402
from kit import M, Prop  # noqa: E402

NAME = "PlumedLion"


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
            from mathutils import Matrix
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


def blade(root, along, normal, length, width, bend=0.06, cup=0.03, thick=0.02, nu=3, nv=1, tip=0.6):
    """One feather: a thin closed blade from `root` along `along`, its flat face towards `normal`,
    widest about `tip` of the way out and rounded at the end, bowed by `bend` towards the normal and
    cupped by `cup`. Each vertex keeps 'g' (0 root to 1 tip) and 'h' (0 on the shaft to 1 at the edge)."""
    d = Vector(along).normalized()
    n = Vector(normal)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    lh = bm.verts.layers.float.new("h")
    cols = 2 * nv + 1
    top, bot = [], []
    for i in range(nu + 1):
        u = i / nu
        w = width * (0.3 + 0.7 * math.sin(min(u / tip, 1.0) * math.pi / 2))
        if u > tip:
            k = (u - tip) / (1 - tip)
            w *= math.sqrt(max(1 - k * k, 0.0)) + 0.03 * (1 - k)
        tr, br = [], []
        for j in range(cols):
            v = j / nv - 1.0
            p = Vector(root) + d * (u * length) + s * (v * w) + n * (bend * u * u - cup * (1 - v * v) * math.sin(math.pi * u))
            h = thick * (0.5 if abs(v) < 0.99 else 0.25) * (1 - 0.6 * u)
            a, b = bm.verts.new(p + n * h), bm.verts.new(p - n * h)
            a[lg] = b[lg] = u
            a[lh] = b[lh] = abs(v)
            tr.append(a)
            br.append(b)
        top.append(tr)
        bot.append(br)
    for i in range(nu):
        for j in range(cols - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    ring = [(0, j) for j in range(cols)] + [(i, cols - 1) for i in range(1, nu + 1)] + \
           [(nu, j) for j in range(cols - 2, -1, -1)] + [(i, 0) for i in range(nu - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((top[i0][j0], bot[i0][j0], bot[i1][j1], top[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def feather_material(name, stops, shaft=0.45, jitter=0.06, rough=0.85):
    """Feathers coloured along their length by a ramp of (position, hex) stops on 'g', the stops
    wobbled by noise so bars are not ruler-straight, a darker shaft down the middle ('h' near 0)
    and kit.furry's fine streaks on top."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, strength=0.1, mottle=0.06, fine=60.0, length=3.0)
    tree = m.node_tree
    new, link, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')

    def op(kind, a, b):
        x = new("ShaderNodeMath")
        x.operation = kind
        for k, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                x.inputs[k].default_value = v
            else:
                link(v, x.inputs[k])
        return x.outputs[0]
    coord = new("ShaderNodeTexCoord")
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 6.0, 2.0
    link(coord.outputs["Object"], nz.inputs["Vector"])
    g = op('ADD', attr("g", "Fac"), op('MULTIPLY', op('SUBTRACT', nz.outputs[0], 0.5), jitter * 2))
    rp = new("ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*hexc(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*hexc(stops[-1][1]), 1.0)
    for pos, hx in stops[1:-1]:
        e = els.new(pos)
        e.color = (*hexc(hx), 1.0)
    link(g, rp.inputs["Fac"])
    dark = op('MULTIPLY', op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', attr("h", "Fac"), 0.14), 1.0)), shaft)
    mx = new("ShaderNodeMix")
    mx.data_type = 'RGBA'
    link(dark, mx.inputs[0])
    link(rp.outputs["Color"], mx.inputs[6])
    mx.inputs[7].default_value = (0.03, 0.015, 0.008, 1.0)
    link(mx.outputs[2], hsv.inputs["Color"])
    return m


# ---- the lion -----------------------------------------------------------------------------------

FUR = {"tan": hexc("#D49A50"), "back": hexc("#B07834"), "cream": hexc("#F1DDB2"), "liner": hexc("#2E1A10"),
       "nose": hexc("#4A2A26"), "ear_in": hexc("#8A5A34"), "tuft": hexc("#5A3418"), "pupil": hexc("#120A06")}
HEAD = Vector((0, -0.95, 2.0))
MANE_C = Vector((0, -0.72, 1.98))


def build():
    from mathutils.bvhtree import BVHTree
    fur_m = painted("Fur", dict(strength=0.2, mottle=0.1, fine=34.0, length=5.0), rough=0.9)
    mane_m = feather_material("ManeFeather", [(0.0, "#3E2210"), (0.3, "#7A4420"), (0.58, "#B0702E"), (0.66, "#C58A40"),
                                              (0.7, "#2E1A0E"), (0.8, "#2E1A0E"), (0.85, "#E6C68C"), (1.0, "#F2DDAE")])
    wing_m = feather_material("WingFeather", [(0.0, "#4E0A10"), (0.35, "#951A22"), (0.75, "#C22B30"), (0.9, "#D9483E"),
                                              (1.0, "#E8705A")], shaft=0.35)
    covert_m = feather_material("CovertFeather", [(0.0, "#7A1218"), (0.6, "#B8282E"), (1.0, "#D85844")], shaft=0.3)
    eye_m = kit.material("Eyes", "#D8962A", rough=0.12)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    # ---- the clay: one fused skin for body, legs, head and ears ----------------------------------------
    clay = [ell((0, 0.25, 1.15), (0.52, 0.95, 0.48)), ell((0, -0.42, 1.2), (0.54, 0.5, 0.56)),
            ell((0, 0.85, 1.12), (0.5, 0.5, 0.5)),
            loft([(0, -0.45, 1.35), (0, -0.7, 1.7), (0, -0.85, 1.9)], lambda t: lerp(0.42, 0.36, t), segs=12, rings=6),
            ell(HEAD, (0.47, 0.44, 0.44)),                                        # cranium
            ell((0, -1.3, 1.86), (0.3, 0.28, 0.22)),                              # muzzle
            ell((0, -1.28, 2.02), (0.15, 0.3, 0.12)),                             # bridge of the nose
            ell((0, -1.22, 2.14), (0.34, 0.14, 0.1)),                             # brow
            ell((0, -1.36, 1.66), (0.15, 0.14, 0.1))]                             # chin
    for s in (-1, 1):
        clay += [ell((0.12 * s, -1.47, 1.82), (0.15, 0.13, 0.12)),                # whisker pads
                 ell((0.3 * s, -1.12, 1.84), (0.2, 0.2, 0.2)),                    # cheeks
                 ell((0.36 * s, -0.86, 2.36), (0.14, 0.07, 0.15), rot=(10, -25 * s, 0)),   # ears
                 ell((0.32 * s, -0.42, 1.0), (0.24, 0.3, 0.42)),                  # shoulders
                 loft([(0.32 * s, -0.48, 0.9), (0.33 * s, -0.55, 0.45), (0.33 * s, -0.6, 0.15)],
                      lambda t: lerp(0.2, 0.15, t), segs=12, rings=6),
                 ell((0.33 * s, -0.7, 0.11), (0.19, 0.25, 0.12)),                 # fore paws
                 ell((0.33 * s, 0.85, 0.95), (0.26, 0.4, 0.44)),                  # thighs
                 loft([(0.34 * s, 0.98, 0.75), (0.35 * s, 1.08, 0.38), (0.34 * s, 0.98, 0.14)],
                      lambda t: lerp(0.18, 0.14, t), segs=12, rings=6),
                 ell((0.34 * s, 0.9, 0.1), (0.18, 0.24, 0.11))]                   # hind paws
    skin = fuse(join(clay), voxel=0.024, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit((0.2 * s, -2.5, 2.05), (0, 1, 0)) for s in (-1, 1)]
    nose_at, _ = hit((0, -2.5, 1.93), (0, 1, 0))
    mouth = [nose_at + Vector((0, 0.03, -0.1)), nose_at + Vector((0, 0.05, -0.17))]
    lips = [[mouth[1], mouth[1] + Vector((0.08 * s, 0.03, -0.03)), mouth[1] + Vector((0.15 * s, 0.1, -0.02))] for s in (-1, 1)]

    def carve(co, n):
        d = Vector()
        for p, en in eyes:
            q = co - p
            d -= en * 0.04 * (1 - smooth(q.length, 0.06, 0.12))
            rb = math.sqrt((q.x / 0.13) ** 2 + ((q.z - 0.09) / 0.045) ** 2 + (q.y / 0.12) ** 2)
            d += n * 0.025 * (1 - smooth(rb, 0.4, 1.0))                  # a soft brow over each eye
        if co.y < -1.2:
            r = min(poly_dist(co, mouth), poly_dist(co, lips[0]), poly_dist(co, lips[1]))
            d -= n * 0.025 * (1 - smooth(r, 0.008, 0.03))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 3400, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - Vector((0, -1.3, 1.95))).length, 0.3, 0.6)), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(FUR["tan"], FUR["back"], smooth(n.z, 0.3, 0.9) * smooth(co.z, 1.2, 1.6) * (co.y > -0.6))
        col = mix(col, FUR["back"], 0.3 * smooth(noise.noise(co * 2.5), 0.0, 0.6))
        belly = smooth(n.z, -0.2, -0.7) * smooth(co.z, 1.2, 0.8)
        chest = smooth(co.y, -0.6, -0.85) * smooth(co.z, 1.7, 1.3) * smooth(-n.y, 0.2, 0.7)
        col = mix(col, FUR["cream"], max(belly, chest) * 0.85)
        if co.y < -1.1:                                                   # cream muzzle, chin and eye marks
            m = (co - Vector((0, -1.42, 1.8))) * Vector((1.0, 1.0, 1.4))
            col = mix(col, FUR["cream"], 1 - smooth(m.length, 0.2, 0.28))
            for p, en in eyes:
                q = co - (p + Vector((0, 0, -0.07)))
                col = mix(col, FUR["cream"], 0.8 * (1 - smooth(q.length, 0.04, 0.09)))
            col = mix(col, mix(FUR["tan"], FUR["back"], 0.6), 0.6 * (1 - smooth(abs(co.x), 0.05, 0.1)) * smooth(co.z, 1.95, 2.05) * smooth(co.z, 2.25, 2.15))
            r = min(poly_dist(co, mouth), poly_dist(co, lips[0]), poly_dist(co, lips[1]))
            col = mix(col, FUR["liner"], 1 - smooth(r, 0.01, 0.025))
        for s in (-1, 1):                                                 # inside the ears
            q = co - Vector((0.36 * s, -0.92, 2.37))
            col = mix(col, FUR["ear_in"], (1 - smooth(q.length, 0.05, 0.11)) * smooth(-n.y, 0.3, 0.7))
        if co.z < 0.25:                                                   # paler paws
            col = mix(col, FUR["cream"], 0.35)
        return col
    add("skin", paint(skin, fur_colour), fur_m)

    # ---- face details -------------------------------------------------------------------------------------
    for (p, en), s in zip(eyes, (-1, 1)):
        rot = M(rot=(0, -12 * s, 0)).to_3x3()
        eye = facing(ell((0, 0, 0), (0.085, 0.058, 0.045), cuts=3), Vector(), en)
        eye.transform(M(p - en * 0.012))
        add("eyes", eye, eye_m)
        add("pupils", flat_paint(facing(ell((0, 0, 0), (0.032, 0.036, 0.02), cuts=1), p + en * 0.026, en), FUR["pupil"]), fur_m)
        # the dark rim round the almond, rising to the outer corner
        side = Vector((1, 0, 0)).cross(en).cross(en) * -1
        ax = (Vector((1, 0, 0)) - en * en.x).normalized()
        up = en.cross(ax).normalized() * (1 if en.cross(ax).z > 0 else -1)
        pts = []
        for k in range(15):
            a = 2 * math.pi * k / 14
            x, z = math.cos(a) * 0.098, math.sin(a) * 0.066
            z += 0.02 * (x * s / 0.098)
            pts.append(p + ax * x + up * z + en * 0.004)
        add("eye rims", flat_paint(loft(pts, lambda t: 0.014, segs=6, rings=28), FUR["liner"]), fur_m)
    nose = ell((0, 0, 0), (0.11, 0.07, 0.075), cuts=2)
    for v in nose.verts:                                                  # broad at the top, narrowing down
        v.co.x *= 1 + 0.35 * smooth(v.co.z, -0.07, 0.07) - 0.35
    nose.transform(M(nose_at + Vector((0, 0.01, 0.0))))
    add("nose", flat_paint(nose, FUR["nose"]), fur_m)

    # ---- the tail with a tuft --------------------------------------------------------------------------------
    tail = [Vector((0, 1.25, 1.25)), Vector((0, 1.6, 1.0)), Vector((0.1, 1.85, 1.05)), Vector((0.16, 2.0, 1.4)), Vector((0.1, 1.98, 1.7))]
    add("tail", paint(loft(tail, lambda t: lerp(0.09, 0.06, t), segs=8, rings=14), fur_colour), fur_m)
    tip = tail[-1]
    tuft = [ell(tip + Vector((0, 0, 0.08)), (0.11, 0.11, 0.15), cuts=2)]
    for k in range(6):
        a = 2 * math.pi * k / 6
        dvec = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1.0)).normalized()
        tuft.append(loft([tip + dvec * 0.05, tip + dvec * 0.2 + Vector((0, 0, 0.06)), tip + dvec * 0.3 + Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.02))],
                         lambda t: lerp(0.07, 0.006, t), segs=6, rings=4))
    add("tail", paint(decimate(fuse(join(tuft), voxel=0.02, iterations=2), 260), lambda co, n, g: FUR["tuft"]), fur_m)

    # ---- the feather mane: a sunburst in three rows round the head -------------------------------------------
    rows = [(18, 0.38, 0.0, 1.0, 0.27, 0.15), (16, 0.36, 0.5, 0.72, 0.24, 0.02), (14, 0.34, 0.25, 0.48, 0.2, -0.1)]
    for count, rr, phase, L, W, dy in rows:
        for k in range(count):
            a = 2 * math.pi * (k + phase) / count
            radial = Vector((math.cos(a), 0, math.sin(a)))
            lift = 0.65 + 0.35 * max(0.0, math.sin(a)) - 0.25 * max(0.0, -math.sin(a))
            root = MANE_C + radial * rr * Vector((1.15, 1, 1.0)) + Vector((0, dy, 0))
            d = (radial + Vector((0, -0.18, 0))).normalized()
            add("mane", blade(root, d, Vector((0, -1, 0)), L * lift, W, bend=-0.05, cup=0.03, thick=0.025, tip=0.62), mane_m)

    # ---- red wings folded high above the back ------------------------------------------------------------------
    for s in (-1, 1):
        S = Vector((0.36 * s, -0.05, 1.55))
        U = Vector((0.42 * s, 0.32, 1.0)).normalized()          # up the leading edge
        B = Vector((0.12 * s, 1.0, -0.35)).normalized()          # back along the folded feathers
        N = U.cross(B) * s                                       # outward face
        T = S + U * 1.95
        arm = loft([S, S + U * 0.7 + B * 0.05, T], lambda t: lerp(0.11, 0.05, t), segs=8, rings=8)
        add("wing arms", paint(arm, lambda co, n, g: hexc("#8E1820")), fur_m)
        for k in range(8):                                       # primaries carry on past the tip
            t = k / 7
            root = S + U * lerp(1.95, 1.2, t)
            d = (U * lerp(1.0, 0.45, t) + B * lerp(0.15, 0.9, t)).normalized()
            add("wings", blade(root, d, N, lerp(0.85, 0.95, t), 0.15, bend=-0.03, tip=0.55, thick=0.022), wing_m)
        for k in range(7):                                       # secondaries hang back from the forearm
            t = k / 6
            root = S + U * lerp(1.15, 0.3, t)
            d = (B + U * lerp(0.3, -0.1, t)).normalized()
            add("wings", blade(root, d, N, lerp(0.95, 0.75, t), 0.17, bend=-0.03, tip=0.65, thick=0.022), wing_m)
        for k in range(8):                                       # a row of coverts over the roots
            t = k / 7
            root = S + U * lerp(1.75, 0.25, t) + N * 0.04
            d = (B * 0.9 + U * lerp(0.6, 0.0, t)).normalized()
            add("coverts", blade(root, d, N, lerp(0.38, 0.42, t), 0.13, bend=-0.02, tip=0.6, thick=0.02), covert_m)
    c.build()
    return c


def bake(c, texture):
    """Everything but the eyes becomes one textured mesh, PlumedLion_Body; the glossy amber eyes stay
    a small mesh of their own, PlumedLion_Eyes."""
    eyes = [ob for ob in c.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in eyes], texture, name=NAME + "_Body",
                            shade=0.5, soften=3, rough=0.88, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    for ob in eyes:
        ob.name = ob.data.name = NAME + "_Eyes"
    c.objects = [body] + eyes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--face", help="also write a tight picture of the face to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,side,back 3/4,game distance")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default="PlumedLion review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "plumedlion_colour.png"))
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
        rig = review.Rig(c, samples=a.samples, focus=(0, -0.6, 1.8))
        head = Vector((0, -1.3, 1.95))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.15)).normalized() * 3.0, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.06)).normalized() * 2.8, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
