"""HornedDemon pet: a majestic infernal ram-beast, remade from the game's original. Built from scratch by script.

    python models/pets/horneddemon.py --review out/horneddemon.png      # render the review sheet
    python models/pets/horneddemon.py --export models/export/horneddemon.fbx

The original is a red four-legged demon with big black curled ram horns, black bat wings and a
golden crown. The remake keeps the red body on four legs, the black ram horns, the black wings and
the gold, and makes it majestic and calm. Must-haves, checked every review:
  1. A proud four-legged stance, chest forward and head held high, wings raised.
  2. A deep red armoured body: shingled plates down the back and the chest.
  3. Glossy black curled ram horns; black wings with red membranes; a small gold circlet.
  4. A calm, dignified ram face: glowing ember eyes under a strong level brow, the mouth closed,
     a short goatee; never menacing.
  5. Matte painted texture with crease shading; Body under 10k triangles.

Round 9: the back plates start behind the withers (the first one stood up on the slope of the
neck like a red fin); a brighter, narrower painted gloss along the tops of the horn ridges.

Round 8: the horn curl turned to face out and forward, so from the front each horn reads as a
big C round the face like the original's (it curled in a plane seen edge-on from the front and
read as a black wig); three broad breast plates instead of four narrow ones (from the front they
read as a zip); the head a little less enlarged.

Round 7: the head and everything on it a tenth bigger, so the calm face carries at game distance
and the beast reads less like a horse; the hide grain a little stronger.

Round 6: the crest painted black along each lock (it came out red); muscle and bone forms
picked out in the hide colour, lighter on the bulges and darker in the hollows, so the red is not
one flat plastic tone.

Round 5: the neck crest rooted on the surface of the neck (the locks were buried inside it);
thicker lower legs (they read as a deer's); the nose a soft darker pad instead of a smudge.

Round 4: the armour made to read: thicker, longer back plates with lighter crimson tops and
near-black rims, and four overlapping breast plates down the front of the chest in place of the
carved bands (they read as throat wrinkles); a bigger crest of black locks; a stronger hide grain;
lighter horns for the budget.

Round 3: a shorter face: the muzzle pulled in and the nose set higher, no goatee (from the front
the face read as a long sad horse with a lump under the chin); a crest of black flame-locks down
the neck; the shoulder and hip plates dropped (they read as saddle bags) and the back plates
wider, draping further down the sides; deeper ember eyes; darker belly and lighter back.

Round 2: stockier and more majestic (it read as a long-legged goat): a heavier chest, barrel and
neck on shorter, thicker legs, a bigger head; the horns now curl tightly round beside the ears
instead of looping up and away behind the head, with deeper ridges and a painted gloss; separate
armour plates shingled down the back and over the shoulders and hips; a shorter, blunter Roman
face with almond ember eyes; no dark smudges on the nose and beard; a deeper red.

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

NAME = "HornedDemon"


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



# ---- the horned demon ---------------------------------------------------------------------------

HEAD = Vector((0, -1.16, 2.72))
HS = 1.05                                            # head scale
EYE_X, EYE_Z = 0.18 * HS, 2.72 + 0.05 * HS
C = {"red": hexc("#7E1614"), "red_hi": hexc("#9E2618"), "red_lo": hexc("#3E0A0A"), "plate": hexc("#9A1E16"),
     "plate_hi": hexc("#C03A20"), "plate_edge": hexc("#2A0808"), "black": hexc("#141014"), "black_hi": hexc("#A4A8B8"),
     "muzzle": hexc("#6A1412"), "nose": hexc("#3A0E0E"), "gold": hexc("#D89A28"), "gold_lo": hexc("#7A4A14"),
     "gold_hi": hexc("#F8CC5C"), "beard": hexc("#4A0E0E")}


def seg_t(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.dot(ab)))
    return (p - (a + ab * t)).length, t


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


def build():
    fur = painted("Hide", dict(strength=0.28, mottle=0.16, fine=30.0, length=5.0), rough=0.9)
    goldm = painted("Gold", dict(strength=0.04, mottle=0.08, fine=20.0, length=2.0), rough=0.6)
    mem_m = membrane_material("Membrane", [(0.0, "#3A0A0A"), (0.5, "#7A1410"), (1.0, "#A8221A")])
    glow_m = kit.material("GLOW_Ember", "#FF6418", rough=0.4, emit=2.0)
    g = Prop(NAME)
    g.tally = {}

    def gold_colour(co, n):
        c = mix(C["gold_lo"], C["gold"], 0.35 + 0.65 * smooth(n.z, -0.6, 0.4))
        return mix(c, C["gold_hi"], 0.4 * smooth(n.z, 0.5, 1.0))

    def add(part, bm, mat):
        if mat is goldm:
            paint(bm, gold_colour)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        g.tally[part] = g.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        g.add(bm, mat)

    H = HEAD
    clay = [ell(H, (0.3, 0.32, 0.3)),                                            # skull
            ell(H + Vector((0, -0.28, -0.12)), (0.18, 0.22, 0.16), rot=(-20, 0, 0)),   # blunt muzzle
            ell(H + Vector((0, -0.24, 0.0)), (0.13, 0.22, 0.11), rot=(-30, 0, 0)),     # Roman nose bridge
            ell(H + Vector((0, -0.44, -0.18)), (0.14, 0.1, 0.11)),                # nose
            ell(H + Vector((0, -0.3, -0.25)), (0.13, 0.15, 0.07), rot=(-12, 0, 0)),    # lower jaw
            ell(H + Vector((0, -0.15, 0.13)), (0.3, 0.12, 0.09)),                 # strong level brow
            limb([(0, -0.58, 1.72), (0, -0.88, 2.22), (0, -1.04, 2.56)], [0.44, 0.35, 0.28], segs=14),  # neck
            ell((0, -0.55, 1.5), (0.6, 0.56, 0.6)),                               # deep chest
            ell((0, 0.05, 1.46), (0.56, 0.76, 0.52)),                             # barrel
            ell((0, 0.72, 1.5), (0.5, 0.45, 0.47)),                               # hips
            ]
    # tail: a long whip ending in a spade
    tail = [(0, 1.08, 1.62), (0, 1.38, 1.4), (0.12, 1.55, 0.95), (0.3, 1.5, 0.55), (0.42, 1.3, 0.35)]
    clay.append(kit.tube([Vector(p) for p in tail], [0.11, 0.08, 0.06, 0.05, 0.04], segs=10))
    clay.append(ell((0.48, 1.18, 0.3), (0.06, 0.14, 0.1), rot=(20, 0, -30)))
    for s in (-1, 1):
        clay += [ell(H + Vector((0.19 * s, -0.12, -0.1)), (0.13, 0.15, 0.13)),      # cheeks
                 ell((0.44 * s, -0.6, 1.55), (0.26, 0.36, 0.44)),                  # shoulder muscle
                 ell((0.4 * s, 0.72, 1.36), (0.26, 0.4, 0.44)),                    # thigh
                 ]
        # ears: small, out to the sides under the horns
        clay.append(kit.tube([H + Vector((0.24 * s, 0.0, -0.08)), H + Vector((0.36 * s, -0.02, -0.14)), H + Vector((0.48 * s, -0.04, -0.2))],
                             [0.07, 0.06, 0.01], segs=8, rings=8, flat=0.45))
        # front leg: straight and proud
        sh, elb, fet = Vector((0.42 * s, -0.64, 1.3)), Vector((0.42 * s, -0.66, 0.82)), Vector((0.4 * s, -0.72, 0.28))
        clay.append(limb([sh, sh.lerp(elb, 0.5), elb], [0.27, 0.22, 0.18]))
        clay.append(limb([elb, elb.lerp(fet, 0.5) + Vector((0, 0.02, 0)), fet], [0.18, 0.155, 0.14]))
        clay.append(limb([fet, fet + Vector((0, -0.02, -0.12)), fet + Vector((0, -0.04, -0.22))], [0.1, 0.12, 0.15]))   # fetlock tuft
        clay.append(limb([Vector((0.4 * s, -0.76, 0.17)), Vector((0.4 * s, -0.78, 0.08)), Vector((0.4 * s, -0.79, 0.0))], [0.14, 0.16, 0.17]))  # hoof
        # hind leg: thigh, hock back, cannon down
        hip, sti, hock, fet = Vector((0.4 * s, 0.72, 1.25)), Vector((0.42 * s, 0.56, 0.86)), Vector((0.4 * s, 0.84, 0.55)), Vector((0.39 * s, 0.78, 0.27))
        clay.append(limb([hip, hip.lerp(sti, 0.5), sti], [0.3, 0.24, 0.19]))
        clay.append(limb([sti, sti.lerp(hock, 0.5), hock], [0.2, 0.17, 0.15]))
        clay.append(limb([hock, hock.lerp(fet, 0.5), fet], [0.15, 0.14, 0.14]))
        clay.append(limb([fet, fet + Vector((0, -0.02, -0.12)), fet + Vector((0, -0.04, -0.2))], [0.1, 0.12, 0.15]))
        clay.append(limb([Vector((0.39 * s, 0.74, 0.17)), Vector((0.39 * s, 0.72, 0.08)), Vector((0.39 * s, 0.71, 0.0))], [0.14, 0.16, 0.17]))
    # a crest of black flame-locks down the back of the neck
    locks = []
    back = Vector((0, 0.84, 0.46)).normalized()
    for k in range(6):
        t = k / 5
        root = Vector((0, lerp(-1.02, -0.62, t), lerp(2.6, 1.85, t))) + back * (lerp(0.27, 0.42, t) - 0.04)
        L = 0.42 - 0.1 * t
        tip = root + Vector((0, 0.3 + 0.1 * t, 0.26 - 0.08 * t)).normalized() * L
        locks.append((root, tip))
        clay.append(kit.tube([root - Vector((0, 0.0, 0.06)), root.lerp(tip, 0.5) + Vector((0, -0.03, 0.04)), tip],
                             [0.1, 0.075, 0.008], segs=8, rings=6, flat=0.5))
    for bm in clay:                                   # the head and all on it a little bigger
        if all((v.co - H).length < 0.78 for v in bm.verts):
            for v in bm.verts:
                v.co = H + (v.co - H) * HS
    skin = fuse(clay, voxel=0.022, factor=0.5, iterations=3)
    tree = BVHTree.FromBMesh(skin)
    eyes = [hit(tree, (EYE_X * s, H.y - 2, EYE_Z), (0, 1, 0)) for s in (-1, 1)]
    nose_p = hit(tree, (0, -4, H.z - 0.19), (0, 1, 0))[0]

    def plate_info(co, n):
        """Armour: (how far into a plate 0..1 from its front edge, 1 at its raised rear rim, mask)."""
        # back plates: bands across the spine from the withers to the rump
        back = 0.0
        u = (co.y + 0.62 - 0.08 * co.x * co.x) / 0.24
        # chest scutes: bands down the front of the chest and throat
        chest = 0.0
        w = (2.15 - co.z - 0.3 * co.x * co.x) / 0.19
        if chest > back:
            return w - math.floor(w), chest, w
        return u - math.floor(u), back, u

    def legs_dark(co):
        return smooth(co.z, 0.62, 0.3)

    def mouth_d(co):
        zline = nose_p.z - 0.1 - 0.12 * smooth(co.y, H.y - 0.62, H.y - 0.3)
        return abs(co.z - zline) if (co.y < H.y - 0.3 and abs(co.x) < 0.14) else 9.0

    def carve(co, n):
        d = Vector()
        f, m, _ = plate_info(co, n)
        d += n * (0.06 * f ** 1.6 - 0.015) * m                               # shingled plates, the rear rim raised
        for (p, en), s in zip(eyes, (-1, 1)):
            q = co - p
            r = math.sqrt((q.x / 0.1) ** 2 + (q.z / 0.075) ** 2 + (q.y / 0.12) ** 2)
            d -= en * 0.04 * (1 - smooth(r, 0.5, 1.25))
        for s in (-1, 1):
            rr = (co - (nose_p + Vector((0.06 * s, 0.0, 0.02)))).length
            d -= n * 0.025 * (1 - smooth(rr, 0.0, 0.035))
        md = mouth_d(co)
        if md < 0.04 and n.z < 0.6:
            d -= n * 0.018 * (1 - smooth(md, 0.0, 0.02))
        return d + n * noise.noise(co * 6.0) * 0.008
    sculpt(skin, carve)
    skin = decimate(skin, 4950)

    cur = {"cv": 0.0}

    def skin_colour(co, n):
        cv = cur["cv"]
        f, m, idx = plate_info(co, n)
        c = mix(C["red"], C["red_hi"], 0.5 + 0.5 * noise.noise(co * 1.8))
        c = mix(c, C["red_lo"], smooth(n.z, -0.2, -0.8) * 0.6)
        pc = mix(C["plate"], C["plate_hi"], smooth(f, 0.55, 0.95))
        pc = mix(pc, C["plate_edge"], 1 - smooth(f, 0.0, 0.1))
        c = mix(c, pc, m)
        hz = smooth(co.y, H.y + 0.05, H.y - 0.15) * smooth(co.z, 2.45, 2.55)
        c = mix(c, C["muzzle"], hz * smooth(co.y, H.y - 0.25, H.y - 0.45) * 0.8)
        c = mix(c, C["nose"], hz * 0.55 * (1 - smooth((co - nose_p).length, 0.05, 0.1)))
        if mouth_d(co) < 0.015 and n.z < 0.6:
            c = mix(c, C["nose"], 0.8)
        crest = 0.0
        for a_, b_ in locks:
            cd, ct = seg_t(co, a_, b_)
            crest = max(crest, smooth(cd, 0.13, 0.08) * smooth(ct, 0.05, 0.3))
        c = mix(c, C["red_hi"], smooth(n.z, 0.4, 0.9) * 0.35)
        c = mix(c, C["red_lo"], smooth(co.z, 1.2, 0.9) * smooth(n.z, 0.0, -0.6) * 0.5)
        c = mix(c, C["black"], max(crest * 0.92, legs_dark(co)))
        c = mix(c, C["black_hi"], smooth(co.z, 0.16, 0.06) * smooth(n.z, -0.2, 0.3) * 0.25)
        tail_tip = smooth(co.y, 1.35, 1.5) * smooth(co.z, 1.2, 0.9)
        c = mix(c, C["black"], tail_tip * 0.0 + smooth((co - Vector((0.46, 1.2, 0.32))).length, 0.25, 0.12))
        for (p, en) in eyes:
            c = mix(c, C["red_lo"], (1 - smooth((co - p).length, 0.07, 0.13)) * 0.7)
        k = (1 + 0.4 * smooth(-(cv + 0.07), 0.03, 0.16)) * (1 - 0.4 * smooth(cv + 0.07, 0.03, 0.12))
        return tuple(x * k for x in c)
    conv = convexity(skin)
    skin.verts.ensure_lookup_table()
    lay = skin.verts.layers.float_color.new("col")
    for v in skin.verts:
        cur["cv"] = conv[v.index]
        v[lay] = (*skin_colour(v.co, v.normal), 1.0)
    tree = BVHTree.FromBMesh(skin)
    add("skin", skin, fur)

    # ---- ember eyes ------------------------------------------------------------------------------------
    for s in (-1, 1):
        p, n = hit(tree, (EYE_X * s, H.y - 2, EYE_Z), (0, 1, 0))
        e = kit.ball((0.18, 0.06, 0.1), cuts=3)
        for v in e.verts:
            k = min(abs(v.co.x) / 0.09, 1.0)
            v.co.z *= (1 - k ** 2) ** 0.5
            if v.co.z > 0.0:
                v.co.z *= 0.75
        e.transform(M(p - n * 0.012, rot=(0, 0, math.degrees(math.atan2(n.x, -n.y)))))
        add("eyes", e, glow_m)

    # ---- glossy black ram horns, curling round past the ears -----------------------------------------
    for s in (-1, 1):
        root, _ = hit(tree, (0.16 * s, H.y + 0.04, 5), (0, 0, -1))
        b = math.radians(48)
        e_back = Vector((s * math.sin(b), math.cos(b), 0))
        e_axis = Vector((s * math.cos(b), -math.sin(b), 0))
        e_up = Vector((0, 0, 1))
        cen = H + Vector((0.36 * s, 0.1, -0.06))
        q = root - cen
        u0, v0 = q.dot(e_back), q.dot(e_up)
        a0 = q.dot(e_axis)
        th0, r0 = math.atan2(u0, v0), math.hypot(u0, v0)
        pts, rad = [root - Vector((0, 0, 0.06))], [0.14]
        N = 24
        for i in range(1, N + 1):
            t = i / N
            th = th0 + t * math.radians(340)
            r = r0 * (1 - 0.42 * t)
            a = a0 + 0.26 * smooth(t, 0.0, 0.5) + 0.08 * t
            pts.append(cen + e_back * (r * math.sin(th)) + e_up * (r * math.cos(th)) + e_axis * a)
            rad.append(0.14 * (1 - 0.8 * t) + 0.006)
        h = kit.tube(pts, rad, segs=8, rings=42)
        lay = h.verts.layers.float_color.new("col")
        tl = h.faces.layers.float.get("t")
        h.normal_update()
        for v in h.verts:
            ts = [f[tl] for f in v.link_faces]
            t = sum(ts) / len(ts)
            ridge = 0.5 + 0.5 * math.cos(t * 2 * math.pi * 9)
            v.co += v.normal * 0.02 * ridge * (1 - t)
            hi = smooth(v.normal.z, 0.62, 0.97) * 0.95 + smooth(-v.normal.y, 0.7, 0.97) * 0.35
            c = mix(C["black"], C["black_hi"], hi * ridge ** 2)
            c = mix(c, hexc("#050405"), (1 - ridge) * 0.6)
            v[lay] = (*mix(c, hexc("#3A3036"), 0.4 * smooth(t, 0.85, 1.0)), 1.0)
        add("horns", h, fur)

    # ---- armour plates shingled down the back, over the shoulders and the hips ---------------------------
    def plate(p, nrm, size, fwd, lift, bend):
        bm = kit.rounded_box(size, n=3.0, cuts=2)
        for v in bm.verts:
            v.co.z -= bend * v.co.x * v.co.x - lift * (v.co.y / size[1])
        z = nrm.normalized()
        x = fwd.cross(z).normalized()
        y = z.cross(x)
        from mathutils import Matrix
        rot = Matrix((x, y, z)).transposed().to_4x4()
        bm.transform(Matrix.Translation(p + z * 0.015) @ rot)

        def col(co, nn):
            q = co - p
            u = q.dot(y) / (size[1] / 2)
            w = q.dot(x) / (size[0] / 2)
            c = mix(C["plate"], C["plate_hi"], smooth(u, -0.3, 0.85))
            c = mix(c, C["plate_edge"], max(smooth(abs(w), 0.72, 0.95), smooth(abs(u), 0.78, 0.98)))
            return mix(c, C["plate_edge"], smooth(nn.dot(z), 0.2, -0.4))
        paint(bm, col)
        return bm
    for k in range(6):
        y = -0.36 + 0.24 * k
        p, nrm = hit(tree, (0, y, 5), (0, 0, -1))
        w = 0.8 + 0.1 * math.sin(math.pi * k / 5)
        add("plates", plate(p, nrm, (w, 0.36, 0.08), Vector((0, 1, 0)), 0.05, 1.25), fur)
    for k, (z, w, L) in enumerate(((1.98, 0.64, 0.4), (1.7, 0.56, 0.36), (1.45, 0.44, 0.32))):   # breast plates, overlapping downwards
        p, nrm = hit(tree, (0, -4, z), (0, 1, 0))
        add("plates", plate(p, nrm, (w, L, 0.07), Vector((0, 0, -1)), 0.05, 1.5), fur)

    # ---- a small gold circlet with an ember at the front -------------------------------------------------
    ring = []
    for k in range(18):
        a = 2 * math.pi * k / 18
        q, _ = hit(tree, (0.4 * math.sin(a) * 0.0 + H.x, H.y, H.z + 0.1), (math.sin(a), -math.cos(a), 0.35))
        ring.append(q if q is not None else H)
    ring = ring + ring[:3]
    add("circlet", kit.tube(ring, [0.028] * len(ring), segs=5, rings=len(ring)), goldm)
    front = ring[0]
    point = [front + Vector((0, -0.01, -0.01)), front + Vector((0, -0.03, 0.08)), front + Vector((0, -0.03, 0.16))]
    add("circlet", kit.tube(point, [0.045, 0.03, 0.004], segs=5, rings=4, flat=0.5), goldm)
    add("gem", ell(front + Vector((0, -0.03, 0.0)), (0.035, 0.022, 0.035), cuts=2), glow_m)

    # ---- black wings with red membranes, raised ----------------------------------------------------------
    for s in (-1, 1):
        sh = Vector((0.3 * s, -0.4, 2.0))
        el = Vector((0.8 * s, -0.2, 2.65))
        wr = Vector((1.12 * s, -0.08, 3.38))
        tips = [Vector((1.36 * s, 0.05, 3.98)), Vector((1.92 * s, 0.3, 3.62)), Vector((2.08 * s, 0.6, 2.86)),
                Vector((1.6 * s, 0.82, 2.18))]
        flank = Vector((0.38 * s, 0.4, 1.95))
        bones, mems = wing(s, sh, el, wr, tips, flank, scallop=0.2, billow=0.1)
        for bn in bones:
            paint(bn, lambda co, nn: mix(C["black"], C["black_hi"], 0.35 * smooth(nn.z, 0.2, 1.0)))
            add("wing bones", bn, fur)
        for m_ in mems:
            add("membrane", m_, mem_m)
    g.build()
    return g


def bake(g, texture):
    """Everything that does not glow becomes one textured mesh, HornedDemon_Body; the eyes and the
    circlet's ember are joined into HornedDemon_GLOW, which keeps its emissive material."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow], texture, name=NAME + "_Body",
                            shade=0.6, soften=3, rough=0.85, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
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
        b.inputs["Specular IOR Level"].default_value = 0.3
    g.objects = [body, gl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--views", default="front 3/4,face,face front,side,back 3/4,game distance")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--quick", action="store_true", help="with --review: the --views list instead of the full eight")
    ap.add_argument("--title", default="HornedDemon review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "horneddemon_colour.png"))
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
        rig = review.Rig(g, samples=a.samples, focus=(0, -0.8, 2.4))
        head = HEAD + Vector((0, -0.25, -0.05))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.6, -1.0, 0.15)).normalized() * 3.2, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.08)).normalized() * 2.9, head, 30)
        shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
