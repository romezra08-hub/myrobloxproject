"""Gargoyle pet: a noble guardian statue come to life, remade from the game's original. Built from scratch by script.

    python models/pets/gargoyle.py --review out/gargoyle.png      # render the review sheet
    python models/pets/gargoyle.py --export models/export/gargoyle.fbx

The original is a dark grey stone gargoyle standing with bat wings and a snarling face. The remake
keeps the dark grey stone, the pointed ears, the bat wings and the glowing gold eyes, and turns the
snarl into a guardian's calm. Must-haves, checked in every review:
  1. Crouched on its haunches like a statue on a ledge, forearms down between the knees, hands on
     the ground, wings raised half open behind, a tail curled round the feet.
  2. A dignified face: a heavy level brow, glowing eyes, a strong muzzle with the mouth closed (no
     snarl, no teeth), pointed ears and small horns curving back.
  3. A carved rune on the chest that glows faintly from inside its groove.
  4. Carved, weathered stone: chisel-soft forms, cracks, lighter worn edges, darker hollows with
     moss growing in the cracks and on the upward ledges.
  5. Matte painted texture with crease shading; Body under 10k triangles.

Round 2: darker grey stone like the original; a longer, narrower muzzle with a defined nose pad
and a level lip line that falls slightly at the back (it smiled); a heavier brow blended into the
skull; mane locks laid down along the neck in two rows (they stuck out like tusks); a bigger rune
laid proud in its groove; moss in patches on the upward ledges, with only dark hairline cracks;
thicker forearms; Body back under 10k.

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

NAME = "Gargoyle"


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


def convexity(bm, passes=2):
    """Per vertex: > 0 in a hollow, < 0 on a ridge (scaled by edge length), softened over neighbours."""
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    c = []
    for v in bm.verts:
        acc, L = 0.0, 0.0
        for e in v.link_edges:
            d = e.other_vert(v).co - v.co
            acc += d.dot(v.normal)
            L += d.length * d.length
        c.append(acc / max(L, 1e-9) * 0.1)
    for _ in range(passes):
        c = [(c[v.index] + sum(c[e.other_vert(v).index] for e in v.link_edges)) / (1 + len(v.link_edges)) for v in bm.verts]
    return c


def stone_material(name, rough=0.9):
    """Weathered stone: the vertex paint 'col' (worn edges, dark hollows, moss) under a fine granite
    speckle, with hairline cracks in patches and moss creeping along the cracks on upward faces."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, strength=0.1, mottle=0.16, fine=34.0, length=1.2)
    tree = m.node_tree
    new, link, op, ramp, attr = _ops(tree)
    b = kit.principled(m)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    coord = new("ShaderNodeTexCoord")
    warp = new("ShaderNodeTexNoise")
    warp.inputs["Scale"].default_value, warp.inputs["Detail"].default_value = 1.6, 2.0
    link(coord.outputs["Object"], warp.inputs["Vector"])
    wv = new("ShaderNodeMix")
    wv.data_type = 'VECTOR'
    wv.inputs[0].default_value = 0.22
    link(coord.outputs["Object"], wv.inputs[4])
    link(warp.outputs["Color"], wv.inputs[5])
    vor = new("ShaderNodeTexVoronoi")
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 2.6
    link(wv.outputs[1], vor.inputs["Vector"])
    patch = new("ShaderNodeTexNoise")
    patch.inputs["Scale"].default_value, patch.inputs["Detail"].default_value = 0.9, 1.0
    link(coord.outputs["Object"], patch.inputs["Vector"])
    where = op('MULTIPLY', op('SUBTRACT', patch.outputs[0], 0.46), 8.0)
    where = op('MINIMUM', op('MAXIMUM', where, 0.0), 1.0)
    crack = op('MULTIPLY', op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', vor.outputs["Distance"], 0.035), 1.0)), where)
    mossband = op('MULTIPLY', op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', vor.outputs["Distance"], 0.09), 1.0)), where)
    geo = new("ShaderNodeNewGeometry")
    sep = new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])
    upish = op('MINIMUM', op('MAXIMUM', op('MULTIPLY_ADD', sep.outputs[2], 1.4, 0.2), 0.0), 1.0)
    moss_amt = op('MINIMUM', op('MULTIPLY', op('MULTIPLY', mossband, upish), 0.5), 1.0)
    col = attr("col", "Color")
    mossc = new("ShaderNodeMix")
    mossc.data_type = 'RGBA'
    link(moss_amt, mossc.inputs[0])
    link(col, mossc.inputs[6])
    mossc.inputs[7].default_value = (*hexc("#4E6A2A"), 1.0)
    link(mossc.outputs[2], hsv.inputs["Color"])
    old = hsv.inputs["Value"].links[0].from_socket
    link(op('MULTIPLY', old, op('SUBTRACT', 1.0, op('MULTIPLY', crack, 0.62))), hsv.inputs["Value"])
    return m


def ribbon(tree, pts2d, width, lift, front=(0, -1, 0)):
    """A thin glowing strip laid on the surface along a polyline given in (x, z), found by casting
    rays from the front."""
    pts = []
    for a, b in zip(pts2d, pts2d[1:]):
        n = max(2, int((Vector(b) - Vector(a)).length / 0.03))
        for k in range(n):
            t = k / n
            pts.append((lerp(a[0], b[0], t), lerp(a[1], b[1], t)))
    pts.append(pts2d[-1])
    on = []
    for x, z in pts:
        p, nrm = hit(tree, (x, -4, z), (0, 1, 0))
        on.append((p, nrm))
    rows = [[], []]
    for k, (p, nrm) in enumerate(on):
        a = on[max(k - 1, 0)][0]
        b = on[min(k + 1, len(on) - 1)][0]
        t = (b - a).normalized()
        side = t.cross(nrm).normalized()
        rows[0].append(p + nrm * lift - side * width / 2)
        rows[1].append(p + nrm * lift + side * width / 2)
    return sheet(rows, 0.02)


def wing_parts(s, sh, el, wr, tips, flank, scallop=0.2, billow=0.1, thick=0.05, nu=7, nv=6):
    """A bat wing: (bones, membranes, edges). Fan sectors from the wrist between the finger tips and
    on to the flank, each with a scalloped trailing edge, and the inner skin from the arm to the flank."""
    bones, mems = [], []
    edges = tips + [flank]
    for k in range(len(edges) - 1):
        a, b = edges[k], edges[k + 1]
        sc = scallop * (a - b).length
        towards = (wr - (a + b) / 2).normalized()
        grid = []
        for i in range(nu + 1):
            u = i / nu
            row = []
            for j in range(nv + 1):
                v = j / nv
                e = a.lerp(b, v) + towards * sc * math.sin(math.pi * v) ** 0.9
                p = wr.lerp(e, u) + Vector((0, billow, 0)) * math.sin(math.pi * u) * math.sin(math.pi * v)
                row.append(p)
            grid.append(row)
        mems.append(sheet(grid, thick, lambda i, j, nu=nu: (i / nu)))
    grid = []
    n = 5
    for i in range(n + 1):
        u = i / n
        top = sh.lerp(el, u * 2) if u < 0.5 else el.lerp(wr, (u - 0.5) * 2)
        row = []
        for j in range(n + 1):
            v = j / n
            p = top.lerp(flank, v * (1 - u ** 3))
            p += Vector((0, billow * 0.5, 0)) * math.sin(math.pi * v) * math.sin(math.pi * min(u * 1.2, 1))
            row.append(p)
        grid.append(row)
    mems.append(sheet(grid, thick, lambda i, j: 0.1))
    bones.append(kit.tube([sh, sh.lerp(el, 0.5) + Vector((0, 0, 0.05)), el], [0.12, 0.09, 0.08], segs=7, rings=5))
    bones.append(kit.tube([el, el.lerp(wr, 0.5), wr], [0.08, 0.065, 0.075], segs=7, rings=5))
    bones.append(ell(el, (0.09, 0.09, 0.09), cuts=2))
    bones.append(ell(wr, (0.09, 0.08, 0.09), cuts=2))
    for t in tips:
        mid = wr.lerp(t, 0.5)
        bones.append(kit.tube([wr, mid, t], [0.055, 0.04, 0.012], segs=6, rings=5))
    thumb = wr + Vector((0.03 * s, -0.12, 0.1))
    bones.append(kit.tube([wr, thumb, thumb + Vector((-0.02 * s, -0.08, -0.05))], [0.05, 0.035, 0.006], segs=6, rings=5))
    return bones, mems


# ---- the gargoyle -------------------------------------------------------------------------------

HEAD_C, HEAD_R = (0, -0.5, 2.78), (0.4, 0.4, 0.36)
MUZZLE_C, MUZZLE_R = (0, -0.88, 2.63), (0.2, 0.3, 0.16)
EYE_X, EYE_Z = 0.155, 2.8
STONE = {"base": hexc("#464A52"), "light": hexc("#767A82"), "dark": hexc("#25272C"), "warm": hexc("#534F4A"),
         "moss": hexc("#4A6428"), "moss2": hexc("#6E8838")}
RUNE = [[(0, 1.4), (0, 2.02)], [(0, 1.92), (0.16, 1.72), (0, 1.52), (-0.16, 1.72), (0, 1.92)],
        [(-0.2, 1.42), (0, 1.52), (0.2, 1.42)]]


def build():
    stone = stone_material("Stone")
    glow_m = kit.material("GLOW_Gold", "#FFB23A", rough=0.4, emit=1.6)
    g = Prop(NAME)
    g.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        g.tally[part] = g.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        g.add(bm, mat)

    clay = [ell(HEAD_C, HEAD_R), ell(MUZZLE_C, MUZZLE_R),
            ell((0, -0.7, 2.79), (0.17, 0.3, 0.13), rot=(-10, 0, 0)),       # bridge of the nose, into the brow
            ell((0, -0.8, 2.5), (0.2, 0.26, 0.1)),                           # jaw
            ell((0, -0.95, 2.48), (0.11, 0.1, 0.07)),                        # chin
            ell((0, -0.76, 2.91), (0.36, 0.13, 0.085)),                      # heavy brow
            kit.tube([(0, -0.25, 2.05), (0, -0.38, 2.4), (0, -0.48, 2.66)], [0.32, 0.27, 0.25], segs=12),   # neck
            ell((0, -0.3, 1.78), (0.6, 0.45, 0.58)),                         # chest
            ell((0, -0.15, 1.2), (0.47, 0.42, 0.42)),                        # belly
            ell((0, 0.15, 0.74), (0.55, 0.5, 0.45)),                         # hips
            ]
    for s in (-1, 1):
        clay += [ell((0.27 * s, -0.68, 2.66), (0.13, 0.15, 0.11)),          # cheekbones
                 ell((0.26 * s, -0.6, 1.9), (0.27, 0.16, 0.2), rot=(0, 0, 8 * s)),   # chest muscles
                 ell((0.62 * s, -0.3, 2.1), (0.28, 0.28, 0.28)),             # shoulders
                 ell((0.32 * s, 0.25, 2.1), (0.22, 0.2, 0.3)),               # shoulder blades (wing roots)
                 ]
        # ears: pointed, swept back
        clay.append(kit.tube([(0.26 * s, -0.48, 2.94), (0.42 * s, -0.36, 3.08), (0.6 * s, -0.16, 3.26)],
                             [0.14, 0.09, 0.012], segs=10, rings=10, flat=0.4))
        # arms down between the knees, hands on the ground
        sh, elb, wri = Vector((0.64 * s, -0.32, 2.05)), Vector((0.5 * s, -0.66, 1.32)), Vector((0.3 * s, -0.9, 0.34))
        clay.append(kit.tube([sh, sh.lerp(elb, 0.5) + Vector((0.05 * s, 0, 0)), elb], [0.21, 0.19, 0.15], segs=12))
        clay.append(kit.tube([elb, elb.lerp(wri, 0.4) + Vector((0, -0.04, 0)), wri], [0.15, 0.16, 0.1], segs=12))
        clay.append(ell((0.3 * s, -0.95, 0.12), (0.15, 0.16, 0.11)))
        for k in (-1, 0, 1):
            base = Vector((0.3 * s + 0.075 * k, -1.0, 0.1))
            clay.append(kit.tube([base, base + Vector((0.02 * k, -0.1, -0.02)), base + Vector((0.025 * k, -0.17, -0.05))],
                                 [0.05, 0.045, 0.04], segs=8))
        # hind legs folded: thigh forward to the knee, shin back down, foot forward
        hip, knee, ank = Vector((0.45 * s, 0.25, 0.75)), Vector((0.62 * s, -0.36, 0.95)), Vector((0.62 * s, 0.14, 0.2))
        clay.append(kit.tube([hip, hip.lerp(knee, 0.5) + Vector((0.05 * s, 0, 0.05)), knee], [0.36, 0.3, 0.2], segs=14))
        clay.append(ell((0.52 * s, 0.0, 0.72), (0.3, 0.5, 0.36)))
        clay.append(kit.tube([knee, knee.lerp(ank, 0.5) + Vector((0, 0.05, 0)), ank], [0.19, 0.15, 0.12], segs=12))
        toe0 = Vector((0.62 * s, -0.3, 0.09))
        clay.append(kit.tube([ank, ank.lerp(toe0, 0.5), toe0], [0.13, 0.12, 0.1], segs=10))
        for k in (-1, 0, 1):
            base = Vector((0.62 * s + 0.08 * k, -0.32, 0.08))
            clay.append(kit.tube([base, base + Vector((0.02 * k, -0.1, -0.02)), base + Vector((0.03 * k, -0.18, -0.04))],
                                 [0.06, 0.05, 0.045], segs=8))
    # a mane of carved locks round the neck and shoulders
    for row, (zr, rad, L, n) in enumerate(((2.62, 0.3, 0.3, 11), (2.4, 0.36, 0.34, 12))):
        for k in range(n):
            az = -165 + 330 * (k + 0.5 * row) / n
            if abs(az) < 62:
                continue                                                       # keep the throat clear for the face
            a = math.radians(az)
            root = Vector((rad * math.sin(a), -0.42 - rad * 0.85 * math.cos(a) + 0.08 * row, zr))
            out = Vector((math.sin(a), -math.cos(a) * 0.8, 0)).normalized()
            clay.append(tuft(root, out * 0.3 + Vector((0, 0.1, -1.0)), L, 0.1, droop=0.0, segs=8))
    # the tail, curled round to the front of the right foot, ending in a spade
    tail = [(0, 0.55, 0.45), (0.3, 0.8, 0.16), (0.78, 0.55, 0.08), (0.95, 0.05, 0.08), (0.88, -0.4, 0.08)]
    clay.append(kit.tube(tail, [0.15, 0.12, 0.09, 0.07, 0.05], segs=10))
    clay.append(ell((0.86, -0.55, 0.07), (0.1, 0.16, 0.05), rot=(0, 0, -10)))

    skin = fuse(clay, voxel=0.022, factor=0.5, iterations=3)
    tree = ray(skin)
    eyes = [hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0)) for s in (-1, 1)]
    nose_p = hit(tree, (0, -4, 2.71), (0, 1, 0))[0]
    frames = []
    for s in (-1, 1):
        base, tipp = Vector((0.26 * s, -0.48, 2.94)), Vector((0.6 * s, -0.16, 3.26))
        a = (tipp - base).normalized()
        f = Vector((0.2 * s, -1.0, 0.3))
        f = (f - a * f.dot(a)).normalized()
        frames.append((base, tipp, a, f, a.cross(f)))

    def mouth_d(co):
        """Distance in the side view to the closed lip line, which runs from under the nose back
        along the muzzle to the cheek (level, no snarl)."""
        x = abs(co.x)
        zline = 2.56 - 0.03 * smooth(co.y, -1.05, -0.7)
        return abs(co.z - zline) if (co.y < -0.66 and x < 0.26) else 9.0

    def carve(co, n):
        d = Vector()
        for (p, en), s in zip(eyes, (-1, 1)):
            q = co - p
            r = math.sqrt((q.x / 0.12) ** 2 + (q.z / 0.075) ** 2 + (q.y / 0.18) ** 2)
            d -= en * 0.06 * (1 - smooth(r, 0.5, 1.2))
        # nose pad and nostrils
        q = co - nose_p
        r = math.sqrt((q.x / (0.1 + 0.6 * max(q.z, -0.04))) ** 2 + (q.z / 0.055) ** 2 + (q.y / 0.08) ** 2)
        d += n * 0.035 * (1 - smooth(r, 0.6, 1.1))
        for s in (-1, 1):
            rr = (co - (nose_p + Vector((0.055 * s, -0.01, -0.02)))).length
            d -= n * 0.025 * (1 - smooth(rr, 0.0, 0.035))
        # the closed mouth: a lip crease, and the groove under the nose down to it
        md = mouth_d(co)
        if md < 0.05 and n.z < 0.7:
            d -= n * 0.03 * (1 - smooth(md, 0.0, 0.03))
        if co.y < -0.9:
            dd = math.hypot(co.x, 0) if 2.56 < co.z < 2.68 else 9
            d -= n * 0.012 * (1 - smooth(dd, 0.0, 0.02))
        # breastbone and the line under the chest muscles
        if co.y < -0.5:
            dd = abs(co.x) if 1.3 < co.z < 2.05 else 9
            d -= n * 0.025 * (1 - smooth(dd, 0.0, 0.04))
            lz = 1.72 - 0.35 * co.x * co.x
            dd = abs(co.z - lz) if abs(co.x) < 0.5 else 9
            d -= n * 0.02 * (1 - smooth(dd, 0.0, 0.04))
        # rune groove
        q = Vector((co.x, 0, co.z))
        if co.y < -0.55:
            rd = min(poly_dist(q, [Vector((x, 0, z)) for x, z in line]) for line in RUNE)
            d -= n * 0.03 * (1 - smooth(rd, 0.03, 0.06))
        # cup the ears
        for base, tipp, a, f, sd in frames:
            q = co - base
            L = (tipp - base).length
            t = q.dot(a) / L
            if 0.15 < t < 1.0:
                w = 0.14 * (1 - t) ** 0.9 + 0.01
                u = q.dot(sd) / w
                v = q.dot(f)
                if v > 0 and abs(u) < 1.0:
                    d -= f * v * 0.7 * (1 - u * u) * smooth(t, 0.15, 0.3)
        # weathering: gentle bumps and chips all over
        w = noise.noise(co * 5.0) * 0.012 + noise.noise(co * 11.0 + Vector((3, 1, 2))) * 0.005
        return d + n * w
    sculpt(skin, carve)
    skin = decimate(skin, 6200)
    conv = convexity(skin)

    def stone_colour(co, n, cv=0.0):
        k = noise.noise(co * 1.3)
        c = mix(STONE["base"], STONE["warm"], 0.5 + 0.5 * noise.noise(co * 0.7 + Vector((5, 5, 5))))
        c = mix(c, STONE["light"], smooth(-cv, 0.02, 0.12) * 0.8 + 0.12 * smooth(n.z, 0.3, 1.0))
        c = mix(c, STONE["dark"], smooth(cv, 0.02, 0.12) * 0.75 + smooth(co.z, 0.4, 0.0) * 0.3)
        moss = smooth(cv, 0.03, 0.1) * smooth(n.z, 0.0, 0.5) * smooth(k, 0.0, 0.3)
        moss = max(moss, smooth(n.z, 0.45, 0.9) * smooth(k, -0.05, 0.3))
        c = mix(c, mix(STONE["moss"], STONE["moss2"], 0.5 + 0.5 * noise.noise(co * 4)), moss * 0.9)
        return c
    skin.verts.ensure_lookup_table()
    lay = skin.verts.layers.float_color.new("col")
    for v in skin.verts:
        c = stone_colour(v.co, v.normal, conv[v.index])
        # the lip line and nostrils read a little darker
        if mouth_d(v.co) < 0.025 and v.normal.z < 0.7:
            c = mix(c, STONE["dark"], 0.6)
        v[lay] = (*c, 1.0)
    tree = ray(skin)
    add("skin", skin, stone)

    # ---- eyes and the rune, glowing -------------------------------------------------------------------
    for s in (-1, 1):
        p, n = hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0))
        e = kit.ball((0.17, 0.08, 0.1), cuts=3)
        for v in e.verts:
            if v.co.z > 0.02:
                v.co.z = 0.02 + (v.co.z - 0.02) * 0.3
        e.transform(M(p - n * 0.012, rot=(0, -4 * s, math.degrees(math.atan2(n.x, -n.y)))))
        add("eyes", e, glow_m)
    for line in RUNE:
        add("rune", ribbon(tree, line, 0.045, 0.004), glow_m)

    # ---- horns ------------------------------------------------------------------------------------------
    for s in (-1, 1):
        p, n = hit(tree, (0.17 * s, -0.66, 4.0), (0, 0, -1))
        pts = [p - Vector((0, 0, 0.05)), p + Vector((0.05 * s, 0.1, 0.16)), p + Vector((0.11 * s, 0.32, 0.25)),
               p + Vector((0.14 * s, 0.52, 0.2)), p + Vector((0.14 * s, 0.62, 0.08))]
        h = kit.tube(pts, [0.085, 0.07, 0.05, 0.03, 0.006], segs=8, rings=12)
        # carved growth rings
        for v in h.verts:
            pass
        paint(h, lambda co, nn: stone_colour(co, nn, 0.0))
        add("horns", h, stone)

    # ---- wings, raised half open behind ----------------------------------------------------------------
    for s in (-1, 1):
        sh = Vector((0.32 * s, 0.3, 2.2))
        el = Vector((0.78 * s, 0.62, 2.82))
        wr = Vector((1.06 * s, 0.66, 3.7))
        tips = [Vector((1.3 * s, 0.74, 4.32)), Vector((1.88 * s, 0.86, 3.86)), Vector((2.06 * s, 0.92, 2.96)),
                Vector((1.62 * s, 0.86, 2.02))]
        flank = Vector((0.42 * s, 0.44, 1.5))
        bones, mems = wing_parts(s, sh, el, wr, tips, flank, scallop=0.2, billow=0.1, thick=0.05)
        for b in bones:
            paint(b, lambda co, nn: stone_colour(co, nn, -0.05))
            add("wing bones", b, stone)
        for m_ in mems:
            m_.normal_update()
            paint(m_, lambda co, nn: mix(stone_colour(co, nn, 0.0), STONE["dark"], 0.25))
            add("membrane", m_, stone)
    g.build()
    return g


def bake(g, texture):
    """Everything that does not glow becomes one textured mesh, Gargoyle_Body; the eyes and the
    chest rune are joined into Gargoyle_GLOW, which keeps its emissive material."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow], texture, name=NAME + "_Body",
                            shade=0.55, soften=3, rough=0.92, uv_angle=80.0, uv_margin=0.004, pack_margin=0.003)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    gl = bpy.context.view_layer.objects.active
    gl.name = gl.data.name = NAME + "_GLOW"
    b = kit.principled(body.data.materials[0])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.25          # matte stone
    g.objects = [body, gl]


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
    ap.add_argument("--title", default="Gargoyle review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "gargoyle_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    g = build()
    print("triangles by part:", dict(sorted(g.tally.items(), key=lambda kv: -kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(g, os.path.abspath(a.texture))
    tris = g.triangles()
    lo, hi = g.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f deep, %.2f tall; lowest point z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(g.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.face:
        import review
        rig = review.Rig(g, samples=a.samples, focus=(0, -0.5, 2.2))
        head = Vector((0, -0.8, 2.72))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.12)).normalized() * 3.3, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.05)).normalized() * 3.0, head, 30)
        chest = Vector((0, -0.7, 1.75))
        rig.cams["chest"] = review._camera("C_chest", chest + Vector((-0.3, -1.0, 0.1)).normalized() * 3.2, chest, 30)
        if a.review:
            shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
            print("review sheet", a.review)
        if a.face:
            rig.render(os.path.abspath(a.face), "face front", "full", a.px)


if __name__ == "__main__":
    main()
