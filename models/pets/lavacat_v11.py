"""LavaCat pet: a cute-cool fire cat, remade from the game's original. Built from scratch by script.

    python models/pets/lavacat.py --review out/lavacat.png      # render the review sheet
    python models/pets/lavacat.py --export models/export/lavacat.fbx

The original is a red cat-like beast with a scowling face, a flame-orange chest and a dragon-like
tail. The remake keeps the red cat standing on four legs, the orange chest, the dark ears and the
raised tail, and makes it a friendly fire cat. Must-haves, checked every review:
  1. Deep red fur fading to flame orange on the chest, face, paws and tail tip.
  2. A fluffy flame-shaped tail raised behind.
  3. Big friendly amber eyes; a small smile; no scowl.
  4. Small glowing ember stripes on the back and flame marks on the brow.
  5. Matte painted fur with crease shading; Body under 10k triangles.

Round 11: the eyes a little rounder and taller with a gentler tilt (they read slightly sly), a
rounder pupil, a flat catchlight (it stood out like a pearl), a thinner outline, and the lower
lid lifted higher so the eyes smile.

Round 10: the face again (the big round eyes with small pupils stared like bug eyes): eyes about
30% smaller, almond-to-round with the outer corners tilted up, set flatter into proper sockets
with a dark outline; the amber iris fills the eye round a big soft vertical pupil, with one
catchlight on the light's side; a soft upper lid with a dark lash edge over the top quarter and a
little lift from below, so it looks relaxed and happy; a shorter tail, thicker and fluffier under
the flame.

Round 9: no lash caps on the eyes (up close each read as a small dark nub on top of the eye).

Round 8: shallower eye sockets, the eyes set a touch further out and a lighter ring round them
(a dark crease under each eye read as a tear mark).

Round 7: smaller pupils set a little higher (their lower edge showed under each eye as a dark
speck); fur tufts at the elbows, the haunches and under the belly so the outline is fluffier.

Round 6: rounded shoulders (the tops of the front legs stood out of the chest as flat-topped
pads); toe grooves on the front of each paw.

Round 5: shorter legs (the body is built at full height, then everything above the paws is
lowered on a smooth ramp), so it sits lower and cuter under its big head; shorter chest tufts
that lie down along the chest (they hung like icicles).

Round 4: no heavy upper lids (with the flat mouth they looked bored): only a thin dark lash line
on top of each eye; a wider, deeper ':3' smile with its corners clearly lifted; stray specks the
skin left above the ear tips removed.

Round 3: ears built as proper wide-based cones (the taper made them thin spikes above the
skull); a clear ':3' smile with lifted corners (it read as a small frown); level upper lids
covering a little more of each eye (tilted lids looked worried); a flame-shaped brow mark, broad at
the base (the diamond read as a gem).

Round 2: bigger solid ears standing up (they were thin hollow stubs that read as horns); a
clean small smile (the wavy line looked nervous); smaller, flatter sparkles in the eyes and a soft
upper lid so they look content rather than startled; no tuft on the crown (it read as a horn); a
thicker tail with a bigger, fluffier flame; one flame mark on the brow (three slashes looked like
an angry sign); slimmer, more orange stripes; sturdier legs.

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

NAME = "LavaCat"


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


def fuse(bms, voxel=0.02, factor=0.5, iterations=3):
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


def flat(bm, rgb):
    return paint(bm, lambda co, n: rgb)


def hit(tree, origin, direction):
    loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
    return loc, nrm


def ell(c, r, rot=(0, 0, 0), cuts=5):
    """An ellipsoid with radii r (kit.ball takes the full size)."""
    bm = kit.ball(tuple(2 * x for x in r), cuts=cuts)
    bm.transform(M(c, rot=rot))
    return bm


def limb(pts, radii, segs=12):
    return kit.tube([Vector(p) for p in pts], radii, segs=segs)


def sheet(grid, thick, layer_fn=None):
    """A thin closed sheet from a grid of points: two skins `thick` apart, stitched round the edge.
    layer_fn(i, j) gives each vertex a float 'g' (0 at the wing arm, 1 at the edge)."""
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


def wing(s, sh, el, wr, tips, flank, scallop=0.2, billow=0.1, thick=0.045, nu=4, nv=4):
    """A bat wing: (bones, membranes). Fan sectors from the wrist between the finger tips and on to
    the flank, each with a scalloped trailing edge, and the inner skin from the arm to the flank."""
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
                row.append(wr.lerp(e, u) + Vector((0, billow, 0)) * math.sin(math.pi * u) * math.sin(math.pi * v))
            grid.append(row)
        mems.append(sheet(grid, thick, lambda i, j, nu=nu: i / nu))
    grid = []
    n = 4
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
    mems.append(sheet(grid, thick, lambda i, j: 0.15))
    bones.append(kit.tube([sh, sh.lerp(el, 0.5) + Vector((0, 0, 0.05)), el], [0.11, 0.085, 0.075], segs=6, rings=3))
    bones.append(kit.tube([el, el.lerp(wr, 0.5), wr], [0.075, 0.06, 0.07], segs=6, rings=3))
    bones.append(ell(el, (0.085, 0.085, 0.085), cuts=2))
    bones.append(ell(wr, (0.085, 0.075, 0.085), cuts=2))
    for t in tips:
        bones.append(kit.tube([wr, wr.lerp(t, 0.5), t], [0.05, 0.036, 0.01], segs=5, rings=4))
    thumb = wr + Vector((0.03 * s, -0.12, 0.1))
    bones.append(kit.tube([wr, thumb, thumb + Vector((-0.02 * s, -0.08, -0.05))], [0.045, 0.032, 0.006], segs=6, rings=4))
    return bones, mems


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

    def attr(name, out="Fac"):
        a = new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', name
        return a.outputs[out]
    return new, link, op, attr


def painted(name, streak, rough=0.9):
    """The vertex paint 'col' under kit.furry's fine streaks and mottling."""
    m = kit.material(name, "#808080", rough=rough)
    kit.furry(m, **streak)
    new, link, op, attr = _ops(m.node_tree)
    hsv = next(n for n in m.node_tree.nodes if n.type == 'HUE_SAT')
    link(attr("col", "Color"), hsv.inputs["Color"])
    return m


def rock_material(name):
    """Rock skin: the vertex paint under a fine speckle and small dark pores."""
    m = painted(name, dict(strength=0.1, mottle=0.14, fine=30.0, length=1.3))
    tree = m.node_tree
    new, link, op, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    old = hsv.inputs["Value"].links[0].from_socket
    coord = new("ShaderNodeTexCoord")
    pit = new("ShaderNodeTexVoronoi")
    pit.inputs["Scale"].default_value = 30.0
    link(coord.outputs["Object"], pit.inputs["Vector"])
    pore = op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', pit.outputs["Distance"], 0.12), 1.0))
    link(op('MULTIPLY', old, op('SUBTRACT', 1.0, op('MULTIPLY', pore, 0.42))), hsv.inputs["Value"])
    return m


def membrane_material(name, stops, rough=0.85):
    """Wing skin: a colour ramp from the arm (g=0) to the edge (g=1), with soft mottling."""
    m = kit.material(name, stops[0][1], rough=rough)
    kit.furry(m, strength=0.05, mottle=0.1, fine=12.0, length=3.0)
    tree = m.node_tree
    new, link, op, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    rp = new("ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*hexc(stops[0][1]), 1.0)
    els[1].position, els[1].color = stops[-1][0], (*hexc(stops[-1][1]), 1.0)
    for pos, h in stops[1:-1]:
        els.new(pos).color = (*hexc(h), 1.0)
    coord = new("ShaderNodeTexCoord")
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 2.2, 3.0
    link(coord.outputs["Object"], nz.inputs["Vector"])
    link(op('MULTIPLY_ADD', op('SUBTRACT', nz.outputs[0], 0.5), 0.25, attr("g")), rp.inputs["Fac"])
    link(rp.outputs["Color"], hsv.inputs["Color"])
    return m


def cracks(co, size=0.3, warp=0.06):
    """Molten seams: (distance to the nearest seam in studs, a 0..1 shade for this plate)."""
    q = co + noise.noise_vector(co * 2.2) * warp
    d, p = noise.voronoi(q / size)
    a, b = p[0], p[1]
    gap = (d[1] * d[1] - d[0] * d[0]) / max(2 * (b - a).length, 1e-6)
    shade = 0.5 + 0.5 * noise.noise(a * 3.7)
    tilt = (q - a * size).dot(noise.noise_vector(a * 5.1))
    return gap * size, shade, tilt



# ---- the lava cat -------------------------------------------------------------------------------

DROP = 0.12
HEAD = Vector((0, -0.62, 1.85 - DROP))
EYE_X, EYE_Z = 0.22, 1.9 - DROP
C = {"red": hexc("#B3241C"), "red_dark": hexc("#7A1612"), "orange": hexc("#F07A2A"), "flame": hexc("#FFB848"),
     "ear": hexc("#3A0E0C"), "nose": hexc("#5A1A18"), "line": hexc("#3A0C0A"), "pupil": hexc("#1A0806"),
     "white": hexc("#FFF6E8"), "whisker": hexc("#FFE6C8"), "stripe": hexc("#8A1410")}


def seg_t(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.dot(ab)))
    return (p - (a + ab * t)).length, t


def poly_t(p, pts):
    """Distance to a polyline and how far along it (0..1) the nearest point is."""
    best, bt = 9.0, 0.0
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        d, t = seg_t(p, a, b)
        if d < best:
            best, bt = d, (k + t) / (len(pts) - 1)
    return best, bt


TAIL0 = [Vector(p) for p in ((0, 0.9, 1.12), (0, 1.22, 1.22), (0.04, 1.42, 1.62), (0.0, 1.38, 1.94), (-0.04, 1.3, 2.22))]
TAIL = [p - Vector((0, 0, DROP)) for p in TAIL0]


def drop_specks(bm, keep=300):
    """Delete loose bits of the skin smaller than `keep` vertices (a voxel remesh can leave the very
    tip of a thin shape floating on its own)."""
    bm.verts.ensure_lookup_table()
    seen, small = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp, stack = [], [v]
        seen.add(v.index)
        while stack:
            a = stack.pop()
            comp.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        if len(comp) < keep:
            small += comp
    bmesh.ops.delete(bm, geom=small, context='VERTS')
    return bm


def build():
    fur = painted("Fur", dict(strength=0.26, mottle=0.12, fine=30.0, length=5.0), rough=0.92)
    eye_m = kit.material("Eyes_Amber", "#FFAA1E", rough=0.12, coat=1.0)
    glow_m = kit.material("GLOW_Ember", "#FF8A28", rough=0.4, emit=2.0)
    g = Prop(NAME)
    g.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        g.tally[part] = g.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        g.add(bm, mat)

    H = HEAD + Vector((0, 0, DROP))                  # built at full height, lowered below
    TL = TAIL0
    clay = [ell(H, (0.55, 0.5, 0.47)),                                            # big round head
            ell(H + Vector((0, -0.3, -0.16)), (0.3, 0.24, 0.2)),                   # lower face
            ell(H + Vector((0, -0.44, -0.22)), (0.09, 0.06, 0.05)),                # chin
            limb([(0, -0.35, 1.1), (0, -0.5, 1.45), (0, -0.58, 1.6)], [0.3, 0.27, 0.28]),   # neck
            ell((0, -0.3, 1.0), (0.42, 0.42, 0.44)),                               # chest
            ell((0, 0.22, 0.98), (0.38, 0.55, 0.38)),                              # body
            ell((0, 0.68, 1.0), (0.39, 0.36, 0.38)),                               # haunches
            ]
    for s in (-1, 1):
        clay += [ell(H + Vector((0.09 * s, -0.42, -0.12)), (0.11, 0.08, 0.08)),     # whisker pads
                 ell(H + Vector((0.34 * s, -0.22, -0.16)), (0.24, 0.22, 0.22)),     # cheek fluff
                 ]
        for k in range(3):                                                         # cheek ruff tufts
            root = H + Vector((0.46 * s, -0.12 + 0.08 * k, -0.18 - 0.07 * k))
            clay.append(kit.tube([root, root + Vector((0.14 * s, 0.04, -0.05)), root + Vector((0.24 * s, 0.1, -0.12))],
                                 [0.09, 0.06, 0.008], segs=8, rings=6))
        # ears: big, cupped triangles
        e = kit.ball((0.42, 0.2, 0.84), cuts=5)
        for v in e.verts:
            t = min(max((v.co.z + 0.06) / 0.48, 0.0), 1.0)
            k = 1 - 0.93 * t ** 0.9
            v.co.x *= k
            v.co.y *= k
            if v.co.y < 0:
                v.co.y += 0.035 * (1 - min(abs(v.co.x) / max(0.21 * k, 1e-3), 1) ** 2) * smooth(t, 0.05, 0.2) * (1 - smooth(t, 0.7, 0.9))
        e.transform(M(H + Vector((0.27 * s, 0.03, 0.36)), rot=(-6, 18 * s, -14 * s)))
        clay.append(e)
        # legs: short and sturdy; front pair straight, hind pair with a bend
        sh, paw = Vector((0.22 * s, -0.38, 0.98)), Vector((0.24 * s, -0.5, 0.12))
        clay.append(ell((0.25 * s, -0.4, 0.86), (0.2, 0.23, 0.27)))                # rounded shoulder
        clay.append(limb([sh, sh.lerp(paw, 0.5), paw], [0.22, 0.17, 0.16]))
        clay.append(ell((0.24 * s, -0.56, 0.09), (0.15, 0.19, 0.1)))
        hip, hock, paw = Vector((0.27 * s, 0.7, 0.85)), Vector((0.28 * s, 0.86, 0.38)), Vector((0.27 * s, 0.74, 0.12))
        clay.append(ell((0.27 * s, 0.66, 0.78), (0.2, 0.3, 0.32)))
        clay.append(limb([hip, hip.lerp(hock, 0.5), hock], [0.2, 0.17, 0.14]))
        clay.append(limb([hock, hock.lerp(paw, 0.5), paw], [0.16, 0.15, 0.15]))
        clay.append(ell((0.27 * s, 0.66, 0.09), (0.15, 0.19, 0.1)))
    # fluff at the elbows, haunches and belly
    for s in (-1, 1):
        for root, d in (((0.3 * s, -0.3, 0.72), (0.06 * s, 0.14, -0.1)), ((0.36 * s, 0.6, 0.98), (0.1 * s, 0.14, -0.06)),
                        ((0.34 * s, 0.76, 0.86), (0.08 * s, 0.16, -0.1)), ((0.16 * s, 0.25, 0.64), (0.03 * s, 0.05, -0.12))):
            root, d = Vector(root), Vector(d)
            clay.append(kit.tube([root, root + d * 0.6 + Vector((0, 0, 0.02)), root + d * 1.2],
                                 [0.08, 0.05, 0.006], segs=8, rings=6))
    # chest fluff tufts
    for k, (x, z) in enumerate(((0, 1.28), (-0.14, 1.18), (0.14, 1.18), (-0.06, 1.05), (0.07, 1.04), (0, 0.92))):
        root = Vector((x, -0.62, z))
        clay.append(kit.tube([root, root + Vector((x * 0.3, -0.06, -0.07)), root + Vector((x * 0.5, -0.06, -0.13))],
                             [0.08, 0.055, 0.008], segs=8, rings=6))
    # the tail: rising behind, ending in a fluffy flame
    clay.append(kit.tube(TL, [0.16, 0.19, 0.23, 0.26, 0.26], segs=12))
    flames = []
    for k, (dx, dy, h, lean) in enumerate(((0, 0, 0.72, 0), (0.15, 0.02, 0.5, 1), (-0.15, 0.0, 0.54, -1), (0.06, 0.15, 0.48, 0.5),
                                            (-0.06, -0.13, 0.46, -0.4), (0.1, -0.1, 0.36, 1.2), (-0.1, 0.12, 0.38, -1.2))):
        root = TL[-1] + Vector((dx, dy, -0.05))
        tip = root + Vector((lean * 0.14, -0.04 + dy * 0.6, h))
        mid = root.lerp(tip, 0.5) + Vector((-lean * 0.06 + 0.04, 0.03, 0))
        flames.append((root, tip))
        clay.append(kit.tube([root, mid, tip], [0.17, 0.11, 0.01], segs=10, rings=8))
    for k in range(8):                                                             # fluffy tufts along the tail
        t = 0.28 + 0.09 * k
        i = min(int(t * (len(TL) - 1)), len(TL) - 2)
        u = t * (len(TL) - 1) - i
        p = TL[i].lerp(TL[i + 1], u)
        side = 1 if k % 2 == 0 else -1
        clay.append(kit.tube([p, p + Vector((0.15 * side, 0.1, 0.03)), p + Vector((0.24 * side, 0.18, 0.12))],
                             [0.1, 0.06, 0.006], segs=8, rings=6))
    for bm in clay:
        for v in bm.verts:
            v.co.z -= DROP * smooth(v.co.z, 0.12, 0.85)
    H = HEAD
    skin = fuse(clay, voxel=0.02, factor=0.5, iterations=3)
    drop_specks(skin)
    tree = BVHTree.FromBMesh(skin)
    eyes = [hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0)) for s in (-1, 1)]
    nose_p = hit(tree, (0, -4, H.z - 0.09), (0, 1, 0))[0]

    def mouth_d(co):
        """Distance in the front view to the small ':3' smile under the nose."""
        if co.y > nose_p.y + 0.12:
            return 9.0
        x = abs(co.x)
        if x < 0.12:
            zline = nose_p.z - 0.085 + 6.0 * (x - 0.05) ** 2
            d = abs(co.z - zline)
        else:
            d = 9.0
        if x < 0.012 and nose_p.z - 0.068 < co.z < nose_p.z - 0.03:
            d = min(d, x)
        return d

    def carve(co, n):
        d = Vector()
        for (p, en) in eyes:
            r = (co - p).length
            d -= en * 0.03 * (1 - smooth(r, 0.06, 0.13))                       # sockets for the eyes
        md = mouth_d(co)
        if md < 0.03:
            d -= n * 0.014 * (1 - smooth(md, 0.0, 0.018))
        if co.z < 0.2:
            for px, py in ((0.24, -0.56), (0.27, 0.66)):
                for s in (-1, 1):
                    if co.y < py - 0.06 and abs(co.x - px * s) < 0.12:
                        for off in (-0.05, 0.05):
                            gx = abs(co.x - (px * s + off))
                            d -= n * 0.016 * (1 - smooth(gx, 0.0, 0.016)) * smooth(co.z, 0.0, 0.03)
        return d + n * noise.noise(co * 7.0) * 0.006
    sculpt(skin, carve)
    skin = decimate(skin, 6400)

    def orange_amt(co, n):
        j = noise.noise(co * 9.0) * 0.05                                       # a jagged, furry edge
        chest = smooth(-n.y, 0.0, 0.4) * smooth(abs(co.x), 0.34 + j, 0.22 + j) * smooth(co.y, -0.2, -0.4) * smooth(co.z, 0.55, 0.7) * smooth(co.z, 1.5 + j, 1.35 + j)
        face = smooth(co.z, H.z - 0.02 + j, H.z - 0.1 + j) * smooth(co.y, H.y - 0.2, H.y - 0.32) * smooth(abs(co.x), 0.3 + j, 0.2 + j)
        cheek = smooth(co.z, H.z - 0.1 + j, H.z - 0.22 + j) * smooth(abs(co.x), 0.3, 0.5) * smooth(co.y, H.y + 0.1, H.y - 0.1)
        paws = smooth(co.z, 0.26 + j, 0.16 + j)
        tdist, tt = poly_t(co, TAIL)
        tail = smooth(co.z, 1.85 + j, 2.1 + j) * smooth(co.y, 1.0, 1.15)
        return max(chest, face, cheek, paws, tail)

    def fur_colour(co, n):
        c = mix(C["red"], C["red_dark"], smooth(n.z, 0.3, 0.9) * smooth(co.z, 0.8, 1.2) * 0.6 * smooth(co.y, H.y + 0.3, H.y + 0.6))
        # soft darker tabby bands across the back and down the legs
        band = 0.5 + 0.5 * math.sin(co.y * 22.0 + noise.noise(co * 3.0) * 2.0)
        c = mix(c, C["stripe"], smooth(band, 0.75, 0.95) * smooth(n.z, 0.2, 0.7) * smooth(co.y, -0.1, 0.1) * smooth(co.y, 0.95, 0.8) * 0.6)
        o = orange_amt(co, n)
        c = mix(c, C["orange"], o)
        c = mix(c, C["flame"], smooth(co.z, 2.25, 2.65) * smooth(co.y, 1.0, 1.15))
        # ears: dark inside with an orange rim
        for s in (-1, 1):
            ec = H + Vector((0.36 * s, -0.02, 0.62))
            q = co - ec
            if q.length < 0.36 and n.y < -0.25 and co.z > H.z + 0.36:
                c = mix(c, C["ear"], smooth(-n.y, 0.25, 0.55) * smooth(abs(q.x), 0.14, 0.08))
        c = mix(c, C["nose"], 1 - smooth((co - nose_p).length, 0.035, 0.06))
        if mouth_d(co) < 0.015:
            c = mix(c, C["line"], 0.85)
        for (p, en) in eyes:
            c = mix(c, C["red_dark"], (1 - smooth((co - p).length, 0.1, 0.14)) * 0.3)
        return c
    paint(skin, fur_colour)
    tree = BVHTree.FromBMesh(skin)
    add("skin", skin, fur)

    # ---- cat eyes: amber almonds tilted up at the outer corners, a big soft pupil, one catchlight -----
    EW, EH, ED = 0.21, 0.19, 0.05                    # eye width, height, depth (half of each is a radius)

    def almond(w, h, d):
        bm = kit.ball((w, d, h), cuts=4)
        for v in bm.verts:
            k = min(abs(v.co.x) / (w / 2), 1.0)
            v.co.z *= (1 - k ** 2) ** 0.3            # rounder in the middle, a soft point at the corners
        return bm
    for s in (-1, 1):
        p, n = hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0))
        yaw = math.degrees(math.atan2(n.x, -n.y)) * 0.6
        place = M(p - n * 0.012, rot=(0, -8 * s, yaw))
        look = (place.to_3x3() @ Vector((0, -1, 0))).normalized()
        e = almond(EW, EH, 2 * ED)
        e.transform(place)
        add("eyes", e, eye_m)
        rim = almond(EW * 1.09, EH * 1.09, 2 * ED * 0.8)                       # a dark outline round the eye
        rim.transform(place @ M((0, 0.012, 0)))
        flat(rim, C["line"])
        add("rims", rim, fur)
        front = p - n * 0.012 + look * (ED - 0.006)
        pupil = kit.ball((0.1, 0.02, 0.13), cuts=3)
        pupil.transform(M(front, rot=(0, 0, yaw)))
        flat(pupil, C["pupil"])
        add("pupils", pupil, fur)
        sp = ell(front + Vector((-0.03, -0.006, 0.036)), (0.02, 0.004, 0.02), cuts=2)   # one catchlight, on the key light's side
        flat(sp, C["white"])
        add("sparkles", sp, fur)
        # a soft upper lid over the top quarter, its edge a dark lash line, and a little lift from below
        lid = almond(EW * 1.08, EH * 1.08, 2 * ED * 1.15)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if v.co.z < EH * 0.22 or v.co.y > 0.004], context='VERTS')
        lid.transform(place @ M((0, 0.004, 0)))
        paint(lid, lambda co, nn, top=place @ Vector((0, 0, EH * 0.22)): mix(C["red"], C["line"], 1 - smooth(co.z - top.z, 0.008, 0.03)))
        add("lids", lid, fur)
        low = almond(EW * 1.06, EH * 1.06, 2 * ED * 1.1)
        bmesh.ops.delete(low, geom=[v for v in low.verts if v.co.z > -EH * 0.26 or v.co.y > 0.004], context='VERTS')
        low.transform(place @ M((0, 0.004, 0)))
        flat(low, mix(C["red"], C["orange"], 0.55))
        add("lids", low, fur)

    # ---- whiskers ----------------------------------------------------------------------------------------------
    for s in (-1, 1):
        for k in range(3):
            root = H + Vector((0.14 * s, -0.42, -0.1 - 0.035 * k))
            p2 = root + Vector((0.2 * s, 0.02, 0.02 - 0.03 * k))
            p3 = root + Vector((0.38 * s, 0.08, -0.02 - 0.07 * k))
            w = kit.tube([root, p2, p3], [0.009, 0.007, 0.002], segs=4, rings=4)
            flat(w, C["whisker"])
            add("whiskers", w, fur)

    # ---- glowing ember stripes on the back and flame marks on the brow -----------------------------------------
    def stripe(pts, width, lift=0.004, flame=False):
        on = []
        for q in pts:
            loc, nrm = hit(tree, q[0], q[1])
            if loc is not None:
                on.append((loc, nrm))
        rows = [[], []]
        for k, (p, nrm) in enumerate(on):
            a = on[max(k - 1, 0)][0]
            b = on[min(k + 1, len(on) - 1)][0]
            t = (b - a).normalized()
            side = t.cross(nrm).normalized()
            u = k / (len(on) - 1)
            w = width * ((u ** 0.7 * (1 - u) ** 0.25 * 1.6) if flame else (math.sin(math.pi * u) ** 0.6 + 0.08))
            rows[0].append(p + nrm * lift - side * w / 2)
            rows[1].append(p + nrm * lift + side * w / 2)
        return sheet(rows, 0.012)
    for k, y0 in enumerate((0.12, 0.36, 0.58)):
        pts = []
        for i in range(11):
            u = i / 10
            x = lerp(-0.34, 0.34, u)
            y = y0 - 0.1 * (1 - (2 * u - 1) ** 2) + 0.03 * math.sin(u * 9 + k)
            pts.append(((x, y, 3.0), (0, 0, -1)))
        add("stripes", stripe(pts, 0.036), glow_m)
    for x, top, bot in ((0.0, 0.36, 0.17),):
        pts = []
        for i in range(8):
            u = i / 7
            z = H.z + lerp(top, bot, u)
            pts.append(((x + 0.02 * math.sin(u * 5.5), -4, z), (0, 1, 0)))
        add("brow marks", stripe(pts, 0.08, flame=True), glow_m)
    g.build()
    return g


def bake(g, texture):
    """Everything that is neither glossy nor glowing becomes one textured mesh, LavaCat_Body; the
    amber eyes stay glossy as LavaCat_Eyes and the ember stripes become LavaCat_GLOW."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    eyes = [ob for ob in g.objects if "Eyes" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow and ob not in eyes], texture, name=NAME + "_Body",
                            shade=0.55, soften=3, rough=0.92, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003, sheen=0.3)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    gl = bpy.context.view_layer.objects.active
    gl.name = gl.data.name = NAME + "_GLOW"
    ey = eyes[0]
    ey.name = ey.data.name = NAME + "_Eyes"
    b = kit.principled(body.data.materials[0])
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.3
    g.objects = [body, ey, gl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--views", default="front 3/4,face,face front,side,back 3/4,game distance")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default="LavaCat review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "lavacat_colour.png"))
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
    if a.review:
        import review
        rig = review.Rig(g, samples=a.samples, focus=(0, -0.6, 1.6))
        head = HEAD + Vector((0, -0.3, -0.05))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.6, -1.0, 0.12)).normalized() * 3.0, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.05)).normalized() * 2.8, head, 30)
        shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
