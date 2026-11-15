"""FireDemon pet: a proud fire elemental imp-knight, remade from the game's original. Built from scratch by script.

    python models/pets/firedemon.py --review out/firedemon.png      # render the review sheet
    python models/pets/firedemon.py --export models/export/firedemon.fbx

The original is a hunched red-orange demon with bat wings, a spiky golden crown and a snarling
face. The remake keeps the red-orange body, the darker forearms and shins, the bat wings, the small
dark horns and the golden crown, and makes it a proud imp-knight. Must-haves, checked every review:
  1. An upright heroic stance: chest out, fists on the hips, wings raised behind.
  2. Cracked molten-rock skin: plates of red-orange rock with glowing seams between them.
  3. A crown of flame-shaped gold spikes.
  4. A calm noble face: a level brow, glowing eyes, a closed mouth (no snarl, no teeth).
  5. Matte painted texture with crease shading; Body under 10k triangles.

Round 5: bigger eyes with an arched upper lid, a straighter lower lid and the outer corners just
lifted (the flat top and round bottom looked sad and weary); no lower lip bump (the chin read as
two lumps); a smaller chin; wavier flame spikes with small side tongues; lighter wing bones and
membranes for the budget.

Round 4: the face again (it read as a smug goblin with staring eyes): long almond eyes with
pointed corners, set deeper under a bolder level brow; a firm, straight mouth with a small lower
lip; the nose bridge brought forward so it shows.

Round 3: a more refined face: a straight nose bridge running down from the brow, a smaller muzzle,
jaw and chin, higher cheekbones, a nearly level mouth (the smile looked smug), soot round the eyes
and lighter cheekbones and bridge so the face is not one flat orange; lighter claws, horns and
buckle for the budget.

Round 2: seams far narrower on bigger plates (it read as a giraffe pattern), plates varied in
shade; bigger, more open eyes under a higher brow and a hint of a smile (it looked bored); richer
gold with fewer, bolder flame spikes; lighter crown, wings and belt for the budget.

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

NAME = "FireDemon"


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
    m = painted(name, dict(strength=0.07, mottle=0.12, fine=30.0, length=1.3))
    tree = m.node_tree
    new, link, op, attr = _ops(tree)
    hsv = next(n for n in tree.nodes if n.type == 'HUE_SAT')
    old = hsv.inputs["Value"].links[0].from_socket
    coord = new("ShaderNodeTexCoord")
    pit = new("ShaderNodeTexVoronoi")
    pit.inputs["Scale"].default_value = 30.0
    link(coord.outputs["Object"], pit.inputs["Vector"])
    pore = op('SUBTRACT', 1.0, op('MINIMUM', op('DIVIDE', pit.outputs["Distance"], 0.12), 1.0))
    link(op('MULTIPLY', old, op('SUBTRACT', 1.0, op('MULTIPLY', pore, 0.3))), hsv.inputs["Value"])
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
    return gap * size, shade


# ---- the fire demon -----------------------------------------------------------------------------

HEAD = Vector((0, -0.1, 3.05))
EYE_X, EYE_Z = 0.15, 3.07
C = {"body": hexc("#C4401C"), "hot": hexc("#E0602A"), "crust": hexc("#6A2014"), "belly": hexc("#E2813A"),
     "dark": hexc("#3C1A14"), "darker": hexc("#24100C"), "seam": hexc("#FF8A2A"), "edge": hexc("#EE6A26"), "lip": hexc("#5A1810"),
     "gold": hexc("#D89A28"), "gold_lo": hexc("#7A4A14"), "gold_hi": hexc("#F8CC5C"), "horn": hexc("#2A1612"),
     "claw": hexc("#1E1210")}


def build():
    rock = rock_material("Rock")
    goldm = painted("Gold", dict(strength=0.04, mottle=0.08, fine=20.0, length=2.0), rough=0.6)
    mem_m = membrane_material("Membrane", [(0.0, "#5A140E"), (0.55, "#8E2414"), (1.0, "#C2441C")])
    glow_m = kit.material("GLOW_Ember", "#FF7A1E", rough=0.4, emit=2.4)
    g = Prop(NAME)
    g.tally = {}

    def gold_colour(co, n):
        up = smooth(co.z, HEAD.z + 0.25, HEAD.z + 0.75)
        c = mix(C["gold_lo"], C["gold"], 0.35 + 0.65 * smooth(n.z, -0.6, 0.4))
        return mix(c, C["gold_hi"], 0.55 * up)

    def add(part, bm, mat):
        if mat is goldm:
            paint(bm, gold_colour)
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        g.tally[part] = g.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        g.add(bm, mat)

    H = HEAD
    clay = [ell(H, (0.4, 0.38, 0.38)),
            ell(H + Vector((0, -0.28, 0.14)), (0.35, 0.13, 0.085)),           # level brow ridge
            ell(H + Vector((0, -0.3, -0.16)), (0.17, 0.14, 0.11)),           # muzzle
            ell(H + Vector((0, -0.39, -0.02)), (0.06, 0.07, 0.13), rot=(-14, 0, 0)),  # nose bridge
            ell(H + Vector((0, -0.44, -0.1)), (0.08, 0.06, 0.055)),          # nose tip
            ell(H + Vector((0, -0.22, -0.3)), (0.2, 0.15, 0.09)),            # jaw
            ell(H + Vector((0, -0.29, -0.32)), (0.075, 0.06, 0.05)),         # chin
            limb([(0, 0.0, 2.4), (0, -0.04, 2.6), (0, -0.08, 2.8)], [0.22, 0.2, 0.2]),    # neck
            ell((0, 0.0, 2.15), (0.55, 0.36, 0.42)),                         # chest
            ell((0, -0.04, 1.68), (0.4, 0.3, 0.34)),                         # belly
            ell((0, 0.02, 1.32), (0.4, 0.3, 0.27)),                          # pelvis
            ]
    for s in (-1, 1):
        clay += [ell(H + Vector((0.24 * s, -0.24, -0.03)), (0.13, 0.11, 0.08)),  # cheekbones
                 ell((0.22 * s, -0.26, 2.24), (0.24, 0.12, 0.17), rot=(0, 0, 8 * s)),   # chest muscles
                 ell((0.58 * s, 0.0, 2.38), (0.22, 0.22, 0.22)),             # shoulders
                 ell((0.3 * s, 0.2, 2.3), (0.22, 0.18, 0.26)),               # shoulder blades
                 ]
        # ears: pointed, swept out and back
        clay.append(kit.tube([H + Vector((0.34 * s, -0.04, 0.04)), H + Vector((0.5 * s, 0.02, 0.1)), H + Vector((0.68 * s, 0.1, 0.2))],
                             [0.11, 0.07, 0.01], segs=10, rings=10, flat=0.4))
        # arms: fists on the hips, elbows out
        sh, elb, wri = Vector((0.62 * s, 0.0, 2.32)), Vector((0.98 * s, 0.12, 1.86)), Vector((0.56 * s, -0.04, 1.47))
        clay.append(limb([sh, sh.lerp(elb, 0.5) + Vector((0.03 * s, 0, 0.03)), elb], [0.18, 0.17, 0.14]))
        clay.append(limb([elb, elb.lerp(wri, 0.45) + Vector((0, 0, 0.02)), wri], [0.15, 0.17, 0.12]))
        clay.append(ell((0.5 * s, -0.04, 1.42), (0.13, 0.14, 0.15)))          # fist
        # legs: straight and set apart
        hip, knee, ank = Vector((0.27 * s, 0.02, 1.28)), Vector((0.32 * s, -0.06, 0.74)), Vector((0.34 * s, 0.02, 0.2))
        clay.append(limb([hip, hip.lerp(knee, 0.5) + Vector((0.03 * s, 0, 0)), knee], [0.26, 0.23, 0.17]))
        clay.append(limb([knee, knee.lerp(ank, 0.45) + Vector((0, 0.03, 0)), ank], [0.17, 0.16, 0.12]))
        clay.append(ell((0.34 * s, -0.1, 0.11), (0.15, 0.24, 0.11)))          # foot
    skin = fuse(clay, voxel=0.02, factor=0.5, iterations=3)
    tree = BVHTree.FromBMesh(skin)
    eyes = [hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0)) for s in (-1, 1)]
    nose_p = hit(tree, (0, -4, H.z - 0.08), (0, 1, 0))[0]

    def face_zone(co):
        """1 on the face (kept smooth and calm), 0 elsewhere."""
        return smooth(co.z, 2.68, 2.78) * smooth(co.y, H.y - 0.12, H.y - 0.24) * smooth(abs(co.x), 0.34, 0.26)

    def dark_zone(co):
        """1 on the cooled-rock forearms and shins (the original's darker limbs)."""
        jag = noise.noise(co * 6.0) * 0.05
        shin = smooth(co.z, 0.82 + jag, 0.7 + jag)
        fore = 0.0
        for s in (-1, 1):
            elb, wri = Vector((0.98 * s, 0.12, 1.86)), Vector((0.5 * s, -0.04, 1.42))
            ab = wri - elb
            t = max(0.0, min(1.0, (co - elb).dot(ab) / ab.dot(ab)))
            dd = (co - (elb + ab * t)).length
            fore = max(fore, smooth(t, 0.12 + jag, 0.3 + jag) * smooth(dd, 0.3, 0.22))
        return max(shin, fore)

    def mouth_d(co):
        zline = nose_p.z - 0.13 + 0.5 * co.x * co.x
        return abs(co.z - zline) if (co.y < H.y - 0.3 and abs(co.x) < 0.12) else 9.0

    info = {}

    def crack_at(co):
        key = (round(co.x, 4), round(co.y, 4), round(co.z, 4))
        if key not in info:
            gap, shade = cracks(co, size=0.3 if dark_zone(co) > 0.5 else 0.4)
            mask = (1 - face_zone(co)) * smooth(noise.noise(co * 1.1 + Vector((4, 2, 9))), -0.45, -0.2)
            info[key] = (gap, shade, mask)
        return info[key]

    # the glowing core: a thin strip under every seam, a little below the skin
    skin.normal_update()
    core = skin.copy()
    drop = []
    for v in core.verts:
        gap, shade, mask = crack_at(v.co)
        if gap > 0.03 or mask < 0.3:
            drop.append(v)
    bmesh.ops.delete(core, geom=drop, context='VERTS')
    core.normal_update()
    for v in core.verts:
        v.co -= v.normal * 0.012

    def carve(co, n):
        d = Vector()
        gap, shade, mask = crack_at(co)
        # seams and gently domed plates
        d -= n * 0.035 * (1 - smooth(gap, 0.006, 0.024)) * mask
        d += n * (0.012 * smooth(gap, 0.02, 0.1) + 0.014 * (shade - 0.5)) * mask
        for (p, en), s in zip(eyes, (-1, 1)):
            q = co - p
            r = math.sqrt((q.x / 0.14) ** 2 + (q.z / 0.085) ** 2 + (q.y / 0.2) ** 2)
            d -= en * 0.065 * (1 - smooth(r, 0.5, 1.25))
        for s in (-1, 1):
            rr = (co - (nose_p + Vector((0.05 * s, -0.01, -0.025)))).length
            d -= n * 0.022 * (1 - smooth(rr, 0.0, 0.032))
        md = mouth_d(co)
        if md < 0.04 and n.z < 0.7:
            d -= n * 0.022 * (1 - smooth(md, 0.0, 0.022))
        w = noise.noise(co * 5.0) * 0.012
        return d + n * w * (1 - 0.7 * face_zone(co))
    sculpt(skin, carve)
    skin = decimate(skin, 5800)
    core = decimate(core, 3200)
    flat(core, (1, 1, 1))

    def skin_colour(co, n):
        gap, shade, mask = crack_at(co)
        base = mix(C["body"], C["hot"], 0.5 + 0.5 * noise.noise(co * 1.6))
        base = mix(base, C["belly"], smooth(abs(co.x), 0.26, 0.12) * smooth(co.y, -0.1, -0.28) * smooth(co.z, 1.25, 1.4) * smooth(co.z, 2.2, 2.05))
        base = mix(base, C["dark"], dark_zone(co))
        base = mix(base, C["crust"] if dark_zone(co) < 0.5 else C["darker"], (0.5 - 0.5 * shade) * 0.45 * mask)
        crust = smooth(noise.noise(co * 7.0), 0.1, 0.5) * smooth(gap, 0.05, 0.12) * 0.4 * mask
        base = mix(base, C["crust"] if dark_zone(co) < 0.5 else C["darker"], crust)
        base = mix(base, C["edge"], (1 - smooth(gap, 0.02, 0.07)) * mask * 0.6)
        base = mix(base, C["seam"], (1 - smooth(gap, 0.0, 0.028)) * mask * 0.9)
        if mouth_d(co) < 0.018 and n.z < 0.7:
            base = mix(base, C["lip"], 0.7)
        fz = face_zone(co)
        for (p, en) in eyes:
            base = mix(base, C["crust"], fz * 0.55 * (1 - smooth((co - p).length, 0.07, 0.15)))
        bridge = (1 - smooth(abs(co.x), 0.02, 0.07)) * smooth(co.z, H.z - 0.12, H.z - 0.02) * smooth(co.z, H.z + 0.12, H.z + 0.04)
        cheek = max(1 - smooth((co - Vector((0.25 * sx, H.y - 0.32, H.z - 0.04))).length, 0.02, 0.1) for sx in (-1, 1))
        base = mix(base, C["edge"], fz * 0.7 * max(bridge, cheek))
        return base
    paint(skin, skin_colour)
    tree = BVHTree.FromBMesh(skin)
    add("skin", skin, rock)
    add("core", core, glow_m)

    # ---- eyes: calm glowing almonds ------------------------------------------------------------------
    for s in (-1, 1):
        p, n = hit(tree, (EYE_X * s, -4, EYE_Z), (0, 1, 0))
        e = kit.ball((0.24, 0.07, 0.13), cuts=4)
        for v in e.verts:                                                  # an almond: pointed corners, arched top
            k = min(abs(v.co.x) / 0.12, 1.0)
            v.co.z *= (1 - k ** 2) ** 0.6
            if v.co.z < 0.0:
                v.co.z *= 0.6
            v.co.z -= 0.01 * (1 - k ** 2)
        e.transform(M(p - n * 0.016, rot=(0, 4 * s, math.degrees(math.atan2(n.x, -n.y)))))
        add("eyes", e, glow_m)

    # ---- horns: small, dark, curving out from the temples ---------------------------------------------
    for s in (-1, 1):
        p, n = hit(tree, (0.27 * s, H.y - 0.12, 5), (0, 0, -1))
        pts = [p - n * 0.05, p + Vector((0.1 * s, 0.0, 0.1)), p + Vector((0.26 * s, 0.04, 0.16)), p + Vector((0.36 * s, 0.08, 0.3))]
        h = kit.tube(pts, [0.075, 0.06, 0.035, 0.006], segs=7, rings=8)
        paint(h, lambda co, nn: mix(C["horn"], C["crust"], 0.3 * smooth(nn.z, 0.3, 1.0)))
        add("horns", h, rock)

    # ---- crown of flame-shaped gold spikes ---------------------------------------------------------------
    ring_z, rx, ry = H.z + 0.26, 0.31, 0.29
    band = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        band.append(Vector((rx * math.sin(a), H.y - ry * math.cos(a), ring_z + 0.03 * math.cos(a))))
    bpts = band + band[:3]
    b = kit.tube(bpts, [0.045] * len(bpts), segs=5, rings=len(bpts), flat=1.6)
    add("crown", b, goldm)
    spikes = [(0, 0.48), (36, 0.34), (-36, 0.34), (80, 0.3), (-80, 0.3), (130, 0.26), (-130, 0.26), (180, 0.28)]
    for az, L in spikes:
        a = math.radians(az)
        root = Vector((rx * math.sin(a), H.y - ry * math.cos(a), ring_z + 0.03 * math.cos(a)))
        out = Vector((math.sin(a), -math.cos(a), 0))
        side = Vector((math.cos(a), math.sin(a), 0))
        lean = out * 0.2 + Vector((0, 0, 1))
        wig = 0.075 * (1 if az >= 0 else -1)
        pts = [root - Vector((0, 0, 0.03)), root + lean * L * 0.35 + side * wig, root + lean * L * 0.7 - side * wig * 0.8,
               root + lean * L + side * wig * 0.6]
        sp = kit.tube(pts, [0.095, 0.085, 0.05, 0.005], segs=6, rings=6, flat=0.5)
        # turn the flattened side to face out
        add("crown", sp, goldm)
        if L > 0.27:                                                      # a small flame tongue beside each spike
            r2 = root + lean * L * 0.25
            sd = side * (-1 if az > 0 else 1) * (1.6 if L > 0.4 else 1.0)
            tongue = [r2, r2 + sd * 0.07 + Vector((0, 0, 0.08)), r2 + sd * 0.08 + Vector((0, 0, 0.17))]
            add("crown", kit.tube(tongue, [0.035, 0.025, 0.003], segs=5, rings=5, flat=0.5), goldm)

    # ---- wings, raised behind ---------------------------------------------------------------------------------
    for s in (-1, 1):
        sh = Vector((0.3 * s, 0.32, 2.42))
        el = Vector((0.72 * s, 0.6, 2.95))
        wr = Vector((1.02 * s, 0.66, 3.62))
        tips = [Vector((1.28 * s, 0.74, 4.22)), Vector((1.86 * s, 0.84, 3.84)), Vector((2.06 * s, 0.88, 2.98)),
                Vector((1.62 * s, 0.84, 2.1))]
        flank = Vector((0.36 * s, 0.38, 1.62))
        bones, mems = wing(s, sh, el, wr, tips, flank, scallop=0.2, billow=0.1)
        for bn in bones:
            paint(bn, lambda co, nn: mix(C["dark"], C["crust"], 0.4 * smooth(nn.z, 0.0, 1.0)))
            add("wing bones", bn, rock)
        for m_ in mems:
            add("membrane", m_, mem_m)

    # ---- belt with a gold buckle, claws ------------------------------------------------------------------------
    belt = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        belt.append(Vector((0.405 * math.sin(a), 0.02 - 0.315 * math.cos(a), 1.47 - 0.03 * math.cos(a))))
    bp = belt + belt[:3]
    bt = kit.tube(bp, [0.05] * len(bp), segs=5, rings=len(bp), flat=1.5)
    paint(bt, lambda co, nn: C["darker"])
    add("belt", bt, rock)
    p, n = hit(tree, (0, -4, 1.44), (0, 1, 0))
    add("buckle", ell(p + Vector((0, -0.04, 0)), (0.11, 0.04, 0.1), cuts=2), goldm)
    for s in (-1, 1):
        for k in (-1, 0, 1):
            base = Vector((0.34 * s + 0.07 * k, -0.3, 0.07))
            c = kit.tube([base, base + Vector((0.01 * k, -0.08, -0.01)), base + Vector((0.015 * k, -0.13, -0.06))],
                         [0.04, 0.03, 0.006], segs=5, rings=3)
            paint(c, lambda co, nn: C["claw"])
            add("claws", c, rock)

    g.build()
    return g


def bake(g, texture):
    """Everything that does not glow becomes one textured mesh, FireDemon_Body; the seams' core
    and the eyes are joined into FireDemon_GLOW, which keeps its emissive material."""
    glow = [ob for ob in g.objects if "GLOW" in ob.name]
    body = kit.bake_texture([ob for ob in g.objects if ob not in glow], texture, name=NAME + "_Body",
                            shade=0.6, soften=3, rough=0.88, uv_angle=66.0, uv_margin=0.004, pack_margin=0.003)
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
    ap.add_argument("--title", default="FireDemon review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", "firedemon_colour.png"))
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
        rig = review.Rig(g, samples=a.samples, focus=(0, -0.3, 2.6))
        head = HEAD + Vector((0, -0.2, 0.05))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.5, -1.0, 0.12)).normalized() * 3.0, head, 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0, -1.0, 0.05)).normalized() * 2.7, head, 30)
        shots = [(v.strip(), "full") for v in a.views.split(",")] if a.quick else review.STANDARD
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
