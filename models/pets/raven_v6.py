"""Raven pet: a sleek, glossy raven, remade from the game's original crow. Built from scratch by script.

    python models/pets/raven.py --review out/raven.png      # render the review sheet
    python models/pets/raven.py --export models/export/raven.fbx

The original is a black crow with spread wings and glowing red eyes. The remake keeps the black bird
with its wings spread, and makes it a raven with a clever, warm face. Must-haves, checked in every review:
  1. Standing proud on its feet with its wings spread wide in display, about 6 studs across.
  2. Layered feathers you can count: fingered primaries, secondaries, two covert rows, a wedge
     tail, shaggy throat hackles and nasal bristles over the beak.
  3. Black feathers with a blue-violet sheen strong enough to read from game distance.
  4. An intelligent face: warm amber glossy eyes with a dark pupil (never red), a heavy, sharp,
     dark-grey beak with a clean closed line.
  5. Matte painted texture with crease shading; Body under 10k triangles.

Round 6: from the side the tail was seen edge-on as a thin spike: it fans wider and tilts down, its
feathers stepped in height, so the wedge reads from the side too; the wing sheen a shade darker so
the wings stay black first and blue second.

Round 5: the raised "ear" tufts made it read as a horned owl: gone, the nape ruff is fuller instead.
The sheen on each feather was a hard blue band like a painted paddle: now a soft gradient that
fades out towards the root and the edges and drifts between blue and violet from feather to feather.

Round 4: shoulders with scapular feathers and marginal coverts all along the arm, so no bare tube
shows at the wing root; small raised "ear" tufts over the eyes, as a displaying raven lifts them, to
break the smooth dome from the front; lighter feet, bristles and pupils for the budget.

Round 3: marginal coverts laid over the front of the arm (a bare tube showed at the wing root); a
flatter crown with ruffled nape feathers and cheek feathers so the head is not a smooth dome, a
small brow ridge over each eye; the eyes further forward and set in; longer, sharper throat hackles;
less sheen on the breast.

Round 2: it read as a purple bird: black now leads and the blue-violet sheen sits only on the upper
faces and across the middle of each vane. Small amber eyes set into the head with a flat pupil (they
bulged like toy eyes); a taller arched beak blended into a flatter, longer head; a thin leading edge
with the coverts laid over it (it was a sausage); pointed throat hackles in two rows and rows of
breast feathers; lighter feathers and feet for the budget (Body was 17.5k).

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
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M, Prop  # noqa: E402

NAME = "Raven"


# ---- helpers: fused clay forms, sculpting and vertex paint -------------------------------------

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


def join(bms):
    out = bmesh.new()
    for b in bms:
        tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(tmp)
        b.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return out


def fuse(bms, voxel=0.022, factor=0.5, iterations=4):
    """Melt overlapping closed shapes into one skin (a voxel remesh), softened a little at the joins."""
    ob = _object(join(bms), "fuse")
    r = ob.modifiers.new("r", 'REMESH')
    r.mode, r.voxel_size, r.adaptivity = 'VOXEL', voxel, 0.0
    if iterations:
        s = ob.modifiers.new("s", 'SMOOTH')
        s.factor, s.iterations = factor, iterations
    return _evaluated(ob)


def decimate(bm, target):
    """Bring a dense skin down to about `target` triangles."""
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    ob = _object(bm, "dec")
    bm.free()
    if tris > target:
        d = ob.modifiers.new("d", 'DECIMATE')
        d.ratio = target / tris
        d.use_collapse_triangulate = True
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


def paint(bm, fn):
    """Give every vertex the colour fn(co, normal) -> (r, g, b) linear, in the attribute 'col'."""
    bm.normal_update()
    lay = bm.verts.layers.float_color.get("col") or bm.verts.layers.float_color.new("col")
    for v in bm.verts:
        v[lay] = (*fn(v.co, v.normal), 1.0)
    return bm


def flat_paint(bm, rgb):
    return paint(bm, lambda co, n: rgb)


def ray(bm):
    return BVHTree.FromBMesh(bm)


def hit(tree, origin, direction):
    loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
    return loc, nrm


def ell(c, r, rot=(0, 0, 0), cuts=5):
    """An ellipsoid with radii r (kit.ball takes the full size)."""
    bm = kit.ball(tuple(2 * x for x in r), cuts=cuts)
    bm.transform(M(c, rot=rot))
    return bm


def on_ell(c, r, az, el):
    """A point and the outward normal on an ellipsoid; az from -Y (front) towards +X, el up, degrees."""
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    p = Vector(c) + Vector((d.x * r[0], d.y * r[1], d.z * r[2]))
    n = Vector((d.x / r[0], d.y / r[1], d.z / r[2])).normalized()
    return p, n


def tuft(root, direction, length, radius, droop=0.0, segs=8):
    d = Vector(direction).normalized()
    r0 = Vector(root) - d * radius * 0.6
    mid = Vector(root) + d * length * 0.5 + Vector((0, 0, -droop * 0.4))
    tip = Vector(root) + d * length + Vector((0, 0, -droop))
    return kit.tube([r0, mid, tip], [radius, radius * 0.62, 0.008], segs=segs, rings=6)


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length, t


def poly_dist(p, pts):
    return min(seg_dist(p, a, b)[0] for a, b in zip(pts, pts[1:]))


def sheet(grid, thick, layer_fn=None):
    """A thin closed sheet from a grid of points (rows of equal length): two skins `thick` apart,
    stitched round the edge. layer_fn(i, j) gives each vertex a float 'g' (for the material)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    R, C = len(grid), len(grid[0])
    P = [[Vector(p) for p in row] for row in grid]

    def normal(i, j):
        du = P[min(i + 1, R - 1)][j] - P[max(i - 1, 0)][j]
        dv = P[i][min(j + 1, C - 1)] - P[i][max(j - 1, 0)]
        n = du.cross(dv)
        return n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))
    top, bot = [], []
    for i in range(R):
        tr, br = [], []
        for j in range(C):
            n = normal(i, j)
            edge = i in (0, R - 1) or j in (0, C - 1)
            h = thick * (0.35 if edge else 0.5)
            a, b = bm.verts.new(P[i][j] + n * h), bm.verts.new(P[i][j] - n * h)
            if layer_fn:
                a[lg] = b[lg] = layer_fn(i, j)
            tr.append(a)
            br.append(b)
        top.append(tr)
        bot.append(br)
    for i in range(R - 1):
        for j in range(C - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    ring = [(0, j) for j in range(C)] + [(i, C - 1) for i in range(1, R)] + \
           [(R - 1, j) for j in range(C - 2, -1, -1)] + [(i, 0) for i in range(R - 2, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((top[i0][j0], bot[i0][j0], bot[i1][j1], top[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def mirror_x(bm):
    """A copy of the shape mirrored across x=0 (normals fixed)."""
    m = bm.copy()
    m.transform(M(scale=(-1, 1, 1)))
    bmesh.ops.reverse_faces(m, faces=m.faces[:])
    return m


# ---- materials ----------------------------------------------------------------------------------

def _ops(tree):
    new, link = tree.nodes.new, tree.links.new

    def op(kind, a, b=None, c=None):
        m = new("ShaderNodeMath")
        m.operation = kind
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[k].default_value = v
            else:
                link(v, m.inputs[k])
        return m.outputs[0]

    def ramp(src, stops):
        rp = new("ShaderNodeValToRGB")
        els = rp.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*hexc(stops[0][1]), 1.0)
        els[1].position, els[1].color = stops[-1][0], (*hexc(stops[-1][1]), 1.0)
        for pos, h in stops[1:-1]:
            e = els.new(pos)
            e.color = (*hexc(h), 1.0)
        link(src, rp.inputs["Fac"])
        return rp.outputs["Color"]

    def attr(name, out="Fac"):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs[out]
    return new, link, op, ramp, attr


def painted(name, streak, rough=0.9):
    """Fur or hide: the vertex paint 'col' under kit.furry's fine streaks and mottling."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, **streak)
    new, link, op, ramp, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col", "Color"), hsv.inputs["Color"])
    return m


def membrane_material(name, stops, rough=0.8):
    """Wing skin: a colour ramp along the wing (g: 0 at the arm, 1 at the edge), its border broken
    into flame tongues by noise, with faint darker veins running out along the fingers."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, strength=0.06, mottle=0.08, fine=14.0, length=3.0)
    tree = m.node_tree
    new, link, op, ramp, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    coord = new("ShaderNodeTexCoord")
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 2.6, 3.0
    link(coord.outputs["Object"], nz.inputs["Vector"])
    g = op('MULTIPLY_ADD', op('SUBTRACT', nz.outputs[0], 0.5), 0.34, attr("g"))
    link(ramp(g, stops), hsv.inputs["Color"])
    return m


def blade(root, along, normal, length, width, bend=0.08, cup=0.02, thick=0.018, nu=6, nv=2, tip=0.55, notch=0.0):
    """One feather: a thin closed blade from `root` along `along`, its flat face towards `normal`.
    It is widest about `tip` of the way out and rounds off at the end; it bows by `bend` towards the
    normal (so rows lie over each other) and cups by `cup`. Each vertex keeps 'g' (0 root to 1 tip)
    and 'h' (0 on the shaft to 1 at the edge) for the material. notch narrows the tip (fingered primaries)."""
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
        w = width * (0.35 + 0.65 * math.sin(min(u / tip, 1.0) * math.pi / 2))
        if u > tip:
            k = (u - tip) / (1 - tip)
            w *= math.sqrt(max(1 - k * k, 0.0)) * (1 - notch * k) + 0.02 * (1 - k)
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


def feather_material(name, black, sheen, edge, rough=0.75):
    """Raven feathers: near-black with a blue-violet sheen across the middle of each feather's vane
    and along its upper half, a fine darker shaft line, darker edges and root."""
    m = kit.material(name, black, rough=rough)
    kit.furry(m, strength=0.08, mottle=0.06, fine=30.0, length=6.0)
    tree = m.node_tree
    new, link, op, ramp, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    g, h = attr("g"), attr("h")

    def band(src, a, b, c, dd):                        # 0 below a, 1 from b to c, 0 above dd
        up = op('MINIMUM', op('MAXIMUM', op('DIVIDE', op('SUBTRACT', src, a), b - a), 0.0), 1.0)
        down = op('MINIMUM', op('MAXIMUM', op('DIVIDE', op('SUBTRACT', dd, src), dd - c), 0.0), 1.0)
        return op('MULTIPLY', up, down)
    gloss = op('MULTIPLY', band(g, 0.05, 0.6, 0.85, 1.05), band(h, -0.1, 0.0, 0.2, 1.05))
    gloss = op('POWER', gloss, 1.6)
    coord = new("ShaderNodeTexCoord")
    hue = new("ShaderNodeTexNoise")
    hue.inputs["Scale"].default_value, hue.inputs["Detail"].default_value = 1.8, 1.0
    link(coord.outputs["Object"], hue.inputs["Vector"])
    tint = new("ShaderNodeMix")
    tint.data_type = 'RGBA'
    link(hue.outputs[0], tint.inputs[0])
    tint.inputs[6].default_value = (*hexc(sheen), 1.0)
    tint.inputs[7].default_value = (*hexc("#352878"), 1.0)
    shaft = op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', h, 0.09), 1.0))
    mx = new("ShaderNodeMix")
    mx.data_type = 'RGBA'
    link(gloss, mx.inputs[0])
    mx.inputs[6].default_value = (*hexc(black), 1.0)
    link(tint.outputs[2], mx.inputs[7])
    mx2 = new("ShaderNodeMix")
    mx2.data_type = 'RGBA'
    link(op('MULTIPLY', shaft, 0.55), mx2.inputs[0])
    link(mx.outputs[2], mx2.inputs[6])
    mx2.inputs[7].default_value = (*hexc(edge), 1.0)
    link(mx2.outputs[2], hsv.inputs["Color"])
    return m


def yloft(sections, segs=14, tip=True):
    """A closed shape through cross-sections (y, cx, cz, half-width, half-height-up, half-height-down)
    taken across the y axis, closed to a point at the last one when tip."""
    bm = bmesh.new()
    rings = []
    for k, (y, cx, cz, w, hu, hd) in enumerate(sections):
        if tip and k == len(sections) - 1:
            rings.append([bm.verts.new((cx, y, cz))])
            continue
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            c, s_ = math.cos(a), math.sin(a)
            ring.append(bm.verts.new((cx + w * c, y, cz + (hu if s_ > 0 else hd) * s_)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            if len(b) == 1:
                bm.faces.new((a[j], a[(j + 1) % segs], b[0]))
            else:
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    bm.faces.new(rings[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- the raven ----------------------------------------------------------------------------------

HEAD_C, HEAD_R = (0, -0.42, 2.36), (0.31, 0.4, 0.28)
EYE_X, EYE_Z = 0.2, 2.44
BLACK, SHEEN, EDGE = "#0A0A10", "#26347E", "#040406"
PLUME = {"black": hexc("#0A0A10"), "sheen": hexc("#1F2B6A"), "violet": hexc("#2C2266"), "under": hexc("#060609")}


def build():
    plume = painted("Plumage", dict(strength=0.16, mottle=0.08, fine=26.0, length=4.0), rough=0.8)
    feathers = feather_material("Feather", BLACK, SHEEN, EDGE)
    covert = feather_material("Covert", BLACK, "#30287A", EDGE)
    beak_m = painted("Beak", dict(strength=0.08, mottle=0.06, fine=30.0, length=3.0), rough=0.55)
    leg_m = painted("Leg", dict(strength=0.1, mottle=0.1, fine=30.0, length=1.5), rough=0.7)
    eye_m = kit.material("Eyes", "#D98A1E", rough=0.12)
    r = Prop(NAME)
    r.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        r.tally[part] = r.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        r.add(bm, mat)

    # ---- the clay: body, neck, head, thighs, throat hackles, nasal bristles --------------------------
    clay = [ell((0, -0.2, 1.45), (0.52, 0.55, 0.6)), ell((0, 0.04, 1.02), (0.42, 0.5, 0.42)),
            kit.tube([(0, 0.05, 1.45), (0, 0.5, 1.0), (0, 0.75, 0.72)], [0.42, 0.3, 0.16], segs=14),
            ell((0, -0.3, 1.92), (0.34, 0.36, 0.38)), ell(HEAD_C, HEAD_R),
            ell((0, -0.6, 2.37), (0.18, 0.22, 0.17))]                         # forehead down to the beak
    # ruffled nape and cheek feathers
    for az, el, L in ((150, 30, 0.2), (180, 40, 0.22), (210, 30, 0.2), (165, 5, 0.2), (195, 5, 0.2), (180, 62, 0.16)):
        p, nn = on_ell(HEAD_C, HEAD_R, az, el)
        clay.append(tuft(p - nn * 0.05, nn * 0.4 + Vector((0, 1.0, -0.35)), L, 0.08, droop=0.0, segs=6))
    for s in (-1, 1):
        p, nn = on_ell(HEAD_C, HEAD_R, 70 * s, -25)
        clay.append(tuft(p - nn * 0.04, nn * 0.3 + Vector((0, 0.8, -0.8)), 0.18, 0.07, segs=6))
        # a fuller ruff at the back of the cheeks
        p, nn = on_ell(HEAD_C, HEAD_R, 115 * s, 10)
        clay.append(tuft(p - nn * 0.05, nn * 0.4 + Vector((0, 1.0, -0.4)), 0.2, 0.08, segs=6))
        # shoulders with scapular feathers
        clay.append(ell((0.4 * s, 0.02, 1.84), (0.19, 0.2, 0.17)))
        for k in range(3):
            p = Vector(((0.32 + 0.09 * k) * s, -0.12 + 0.05 * k, 1.9 - 0.04 * k))
            clay.append(tuft(p, Vector((0.5 * s, -0.15, -1.0)), 0.24, 0.07, segs=6))
    # rows of breast feathers, overlapping downwards
    for row, (z, n, L) in enumerate(((1.62, 7, 0.26), (1.38, 8, 0.28), (1.14, 7, 0.26))):
        for k in range(n):
            az = -60 + 120 * (k + 0.5 * (row % 2)) / (n - 1 + 0.5 * (row % 2))
            p, nn = on_ell((0, -0.2, 1.45), (0.52, 0.55, 0.6), az, (z - 1.45) / 0.6 * 70)
            clay.append(tuft(p - nn * 0.05, nn * 0.25 + Vector((0, 0, -1)), L, 0.08, droop=0.0, segs=6))
    for s in (-1, 1):
        clay.append(ell((0.22 * s, 0.0, 0.74), (0.17, 0.21, 0.24)))           # feathered thighs
    for row, (z, xs) in enumerate(((2.12, (-0.16, -0.08, 0.0, 0.08, 0.16)), (1.98, (-0.2, -0.12, -0.04, 0.04, 0.12, 0.2)))):
        for x in xs:
            p = Vector((x, -0.6 + 0.4 * abs(x) + 0.04 * row, z))
            clay.append(tuft(p, Vector((x * 0.6, -0.4, -1.0)), 0.3 - 0.25 * abs(x), 0.06, droop=0.0, segs=6))
    skin = fuse(clay, voxel=0.02, factor=0.5, iterations=4)
    tree = ray(skin)
    eyes = [hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0)) for s in (-1, 1)]
    eyes = [hit(tree, (EYE_X * s * 3.5, -0.64, EYE_Z), (-s, 0.2, 0)) for s in (-1, 1)]

    def carve(co, n):
        d = Vector()
        for p, en in eyes:
            q = co - p
            rr = q.length
            d -= en * 0.04 * (1 - smooth(rr, 0.03, 0.09))
            # a small brow ridge over the eye
            rb = math.sqrt((q.y / 0.11) ** 2 + ((q.z - 0.075) / 0.03) ** 2 + (q.x / 0.12) ** 2)
            d += n * 0.022 * (1 - smooth(rb, 0.4, 1.0))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 3300)

    def plume_colour(co, n):
        c = PLUME["black"]
        top = smooth(n.z, 0.25, 0.95) * (0.55 + 0.45 * smooth(co.z, 1.6, 2.2))
        c = mix(c, mix(PLUME["sheen"], PLUME["violet"], 0.5 + 0.5 * noise.noise(co * 2.0)), top * 0.75)
        c = mix(c, PLUME["under"], smooth(n.z, -0.2, -0.8) * 0.8)
        for p, en in eyes:
            c = mix(c, PLUME["under"], 1 - smooth((co - p).length, 0.065, 0.1))
        return c
    paint(skin, plume_colour)
    tree = ray(skin)
    add("skin", skin, plume)

    # ---- beak, nasal bristles, eyes ----------------------------------------------------------------------
    beak = yloft([(-0.58, 0, 2.32, 0.13, 0.15, 0.12), (-0.74, 0, 2.33, 0.105, 0.13, 0.095),
                  (-0.9, 0, 2.31, 0.08, 0.11, 0.07), (-1.04, 0, 2.26, 0.052, 0.085, 0.045),
                  (-1.14, 0, 2.19, 0.028, 0.06, 0.025), (-1.2, 0, 2.1, 0, 0, 0)], segs=12)

    def beak_colour(co, n):
        c = mix(hexc("#1E2025"), hexc("#3A3E46"), smooth(co.y, -0.8, -1.18))
        line = 2.27 - 0.12 * smooth(co.y, -0.8, -1.18) ** 1.6
        c = mix(c, hexc("#0E0F12"), (1 - smooth(abs(co.z - line), 0.006, 0.02)) * smooth(-0.6, -0.68, co.y))
        return c
    add("beak", paint(beak, beak_colour), beak_m)
    for k in range(3):
        x = (k - 1) * 0.06
        root = Vector((x, -0.6, 2.42 - abs(x) * 0.6))
        b = tuft(root, Vector((x * 0.8, -1.0, -0.3)), 0.2 - abs(x) * 0.5, 0.045, segs=5)
        add("bristles", flat_paint(b, PLUME["black"]), plume)
    for (p, en), s in zip(eyes, (-1, 1)):
        e = ell(p - en * 0.022, (0.05, 0.05, 0.05), cuts=3)
        add("eyes", e, eye_m)
        pup = ell(p + en * 0.026, (0.021, 0.021, 0.021), cuts=1)
        for v in pup.verts:
            v.co -= en * 0.6 * (v.co - (p + en * 0.026)).dot(en)              # flatten it onto the eye
        add("pupils", flat_paint(pup, hexc("#050506")), beak_m)

    # ---- legs and feet ---------------------------------------------------------------------------------
    for s in (-1, 1):
        hip, ank = Vector((0.2 * s, -0.02, 0.62)), Vector((0.21 * s, -0.08, 0.06))
        leg = kit.tube([hip, hip.lerp(ank, 0.5), ank], [0.06, 0.045, 0.045], segs=6, rings=6)
        add("legs", flat_paint(leg, hexc("#24262B")), leg_m)
        for ang in (-28, 0, 28, 180):
            a = math.radians(ang)
            dirv = Vector((math.sin(a) * 0.9, -math.cos(a), 0)) if ang != 180 else Vector((0, 1, 0))
            L = 0.22 if ang != 180 else 0.15
            toe = kit.tube([ank, ank + dirv * L * 0.6 + Vector((0, 0, -0.03)), ank + dirv * L + Vector((0, 0, -0.04))],
                           [0.035, 0.03, 0.025], segs=5, rings=3)
            add("legs", flat_paint(toe, hexc("#24262B")), leg_m)
            tipp = ank + dirv * L + Vector((0, 0, -0.04))
            claw = kit.tube([tipp, tipp + dirv * 0.05, tipp + dirv * 0.08 + Vector((0, 0, -0.03))], [0.022, 0.015, 0.003], segs=4, rings=2)
            add("legs", flat_paint(claw, hexc("#101114")), leg_m)

    # ---- wings in display ------------------------------------------------------------------------------
    front = Vector((0, -1, 0))
    for s in (-1, 1):
        S, E, W, T = (Vector((0.42 * s, 0.05, 1.85)), Vector((1.05 * s, 0.12, 2.38)), Vector((1.6 * s, 0.16, 2.92)),
                      Vector((2.08 * s, 0.2, 3.2)))
        arm = kit.tube([S, E, W, T], [0.08, 0.06, 0.05, 0.03], segs=6, rings=10)
        add("wing arm", paint(arm, plume_colour), plume)
        # primaries: from the hand, fanning from out-and-up to down-and-out; the outer five fingered
        n_p = 9
        for k in range(n_p):
            t = k / (n_p - 1)
            root = W.lerp(T, 1 - t * 0.9)
            ang = math.radians(lerp(32, -58, t))
            d = Vector((math.cos(ang) * s, 0.04 * s, math.sin(ang)))
            L = lerp(1.05, 0.95, t) * (1 - 0.15 * (t - 0.5) ** 2)
            add("primaries", blade(root + Vector((0, 0.012 * k, 0)), d, front, L, lerp(0.12, 0.16, t), bend=-0.06, nu=5, nv=1,
                                   tip=0.5 if k < 5 else 0.62, notch=0.5 if k < 5 else 0.0, thick=0.02), feathers)
        # secondaries along the forearm, hanging down and a little out
        n_s = 8
        for k in range(n_s):
            t = k / (n_s - 1)
            root = W.lerp(E, t * 0.95) + Vector((0, 0.01 * k, 0))
            ang = math.radians(lerp(-62, -84, t))
            d = Vector((math.cos(ang) * s, 0.0, math.sin(ang)))
            add("secondaries", blade(root, d, front, lerp(0.92, 0.85, t), 0.17, bend=-0.05, tip=0.7, thick=0.022, nu=4, nv=1), feathers)
        # tertials near the body
        for k in range(3):
            t = k / 2
            root = E.lerp(S, 0.2 + 0.55 * t)
            d = Vector((0.2 * s, 0.1, -1))
            add("secondaries", blade(root + Vector((0, 0.03, 0)), d, front, lerp(0.8, 0.62, t), 0.16, bend=-0.04, tip=0.7, nu=4, nv=1), feathers)
        # marginal coverts: small feathers over the front of the arm, pointing out along it and down
        for k in range(9):
            t = k / 8
            root = S.lerp(E, 0.1 + 1.8 * t) if t < 0.5 else E.lerp(W, (t - 0.5) * 2 * 1.1)
            along = ((E - S) if t < 0.5 else (W - E)).normalized()
            d = (along * 0.55 + Vector((0, 0, -1))).normalized()
            add("coverts", blade(root + front * 0.06 + Vector((0, 0, 0.06)), d, front, 0.24, 0.11, bend=-0.02, tip=0.6,
                                 nu=3, nv=1), covert)
        # two covert rows over the bases, in front
        for row, (L, w, off, count) in enumerate(((0.5, 0.15, -0.05, 9), (0.3, 0.12, -0.08, 8))):
            for k in range(count):
                t = k / (count - 1)
                root = (T.lerp(W, t * 2) if t < 0.5 else W.lerp(E, (t - 0.5) * 2 * 0.9 + 0.0))
                root = root.lerp(E.lerp(S, 0.3), max(0, t - 0.92) * 4)
                ang = math.radians(lerp(10, -80, min(t * 1.4, 1.0)))
                d = Vector((math.cos(ang) * s, 0.0, math.sin(ang)))
                root = root + front * (-off) * -1 + Vector((0, 0, -0.02 * row))
                add("coverts", blade(root + front * (0.05 + 0.03 * row) + Vector((0, 0, 0.04 * row)), d, front, L, w, bend=-0.03,
                                     tip=0.65, nu=3, nv=1), covert)

    # ---- the wedge tail -------------------------------------------------------------------------------------
    for k in range(9):
        t = (k - 4) / 4
        root = Vector((0.05 * t, 0.62, 0.86 + 0.03 * abs(t)))
        d = Vector((0.5 * t, 0.62, -0.72 + 0.12 * abs(t))).normalized()
        L = 0.95 - 0.25 * abs(t)
        nrm = Vector((-0.5 * t, 0.55, 0.8))
        add("tail", blade(root, d, nrm, L, 0.15, bend=0.04, cup=0.03, tip=0.7, thick=0.03, nu=4, nv=1), feathers)
    r.build()
    return r


def bake(r, texture):
    """Everything but the eyes becomes one textured mesh, Raven_Body; the glossy amber eyes stay a
    small mesh of their own, Raven_Eyes."""
    eyes = [ob for ob in r.objects if ob.name.endswith("_Eyes")]
    body = kit.bake_texture([ob for ob in r.objects if ob not in eyes], texture, name=NAME + "_Body",
                            shade=0.5, soften=3, rough=0.8, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
    for ob in eyes:
        ob.name = ob.data.name = NAME + "_Eyes"
    b = kit.principled(body.data.materials[0])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.3
    r.objects = [body] + eyes


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
    ap.add_argument("--title", default="Raven review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "raven_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    r = build()
    print("triangles by part:", dict(sorted(r.tally.items(), key=lambda kv: -kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(r, os.path.abspath(a.texture))
    tris = r.triangles()
    lo, hi = r.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(r.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(r, samples=a.samples, focus=(0, -0.4, 2.0))
        head = Vector((0, -0.7, 2.35))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.6, -1.0, 0.12)).normalized() * 3.0, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.05)).normalized() * 2.8, head, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face", "full", a.px)


if __name__ == "__main__":
    main()
