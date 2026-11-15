"""Cerberus pet: a loyal three-headed guardian pup, remade from the game's dark three-headed dog with
orange markings and a candle-flame tail. Built from scratch by script.

    python models/pets/cerberus.py --review out/cerberus.png      # render the review sheet
    python models/pets/cerberus.py --export models/export/cerberus.fbx

Must-haves, checked in every review:
  1. The same creature: a dark charcoal dog with three heads on one sturdy pup body, ember-orange
     markings (brows, muzzles, chest, paws) and a tail that rises like a candle to a flame.
  2. Three friendly heads, alert and happy (open smiles, a tongue), never snarling.
  3. A spiked collar on each neck.
  4. A glowing flame on the tip of the tail.
  5. Matte painted fur with crease shading; 3-4.5 studs tall; Body under 9k triangles.

Round 4: body shortened and legs moved in for pup proportions; a deeper closed smile on the right head; mottled fur sheen.

Round 3: wider D-shaped open smile; a softer two-row chest ruff with the orange bib lowered below it (the first ruff over the bib read as teeth); fluffy thighs; a bigger flame.

Round 2: broad soft ears folding forward (the thin upright ones read as horns); brown eyes; cheek tufts, chest ruff, toe grooves; trimmed to budget.

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




# ---- the guardian pup ------------------------------------------------------------------------------

NAME = "Cerberus"
COL = {"fur": hexc("#2A2830"), "sheen": hexc("#47444F"), "under": hexc("#1E1D23"),
       "ember": hexc("#E4782A"), "ember_lt": hexc("#F2A04E"), "ember_dk": hexc("#B8521C"),
       "mouth": hexc("#4A1418"), "tongue": hexc("#E2667A"), "tongue_dk": hexc("#B8445A"), "nose": hexc("#0D0C10"),
       "pupil": hexc("#120A06"), "white": hexc("#FFFFFF"), "leather": hexc("#8E2420"), "leather_dk": hexc("#5E1512"),
       "steel": hexc("#D2CEC6"), "steel_dk": hexc("#8E8A86"), "ear_in": hexc("#5A3A34")}
SCALE = 1.15
BAKE = {"shade": 0.45, "rough": 0.88}
# heads: (centre, rotation in degrees (pitch, roll, yaw), mouth style)
HEADS = [((0.0, -1.02, 2.32), (-8, 0, 0), "open"),
         ((-0.70, -0.80, 2.12), (-4, -10, -27), "tongue"),
         ((0.70, -0.80, 2.12), (-4, 10, 27), "smile")]
NECKS = [[(0, -0.5, 1.45), (0, -0.78, 1.85), (0, -0.93, 2.12)],
         [(-0.3, -0.48, 1.42), (-0.52, -0.66, 1.76), (-0.63, -0.74, 1.95)],
         [(0.3, -0.48, 1.42), (0.52, -0.66, 1.76), (0.63, -0.74, 1.95)]]
FACE = Vector((0, -1.45, 2.3)) * SCALE
FOCUS = Vector((0, -1.0, 2.2)) * SCALE
FACE_DIST = 4.6
TAIL = [Vector((0, 0.95, 1.3)), Vector((0, 1.22, 1.5)), Vector((0, 1.32, 1.85)), Vector((0, 1.3, 2.22))]


def head_matrix(h):
    return M(h[0], rot=h[1])


def head_clay(h):
    """The fused forms of one head, in place."""
    m = head_matrix(h)
    parts = [ell((0, 0.02, 0.02), (0.33, 0.31, 0.3)),            # cranium
             ell((0, -0.13, 0.1), (0.24, 0.2, 0.16)),             # brow
             ell((0, -0.3, -0.08), (0.165, 0.21, 0.13)),          # snout
             ell((0, -0.24, -0.19), (0.13, 0.17, 0.075))]         # chin
    for s in (-1, 1):
        parts += [ell((0.075 * s, -0.36, -0.12), (0.105, 0.13, 0.09)),     # muzzle pads
                  ell((0.18 * s, -0.1, -0.07), (0.15, 0.15, 0.14))]        # cheeks
    for b in parts:
        b.transform(m)
    return parts


def build():
    fur_m = painted("Fur", dict(strength=0.32, mottle=0.12, fine=40.0, length=6.0), rough=0.9)
    eye_m = kit.material("Eyes", "#9A5418", rough=0.1)
    glow = kit.material("GLOW_Flame", "#FFA126", rough=0.4, emit=2.5)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat):
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    mats = [head_matrix(h) for h in HEADS]
    inv = [m.inverted() for m in mats]
    rots = [m.to_3x3() for m in mats]

    # ---- one fused skin: body, legs, necks, heads, tail ------------------------------------------------
    clay = [ell((0, 0.13, 1.15), (0.5, 0.72, 0.46)), ell((0, -0.4, 1.28), (0.58, 0.45, 0.52)),
            ell((0, 0.65, 1.18), (0.47, 0.42, 0.45)),
            loft(TAIL, lambda t: lerp(0.12, 0.085, t), segs=10, rings=12)]
    for pts in NECKS:
        clay.append(loft(pts, lambda t: lerp(0.25, 0.21, t), segs=12, rings=6))
    for h in HEADS:
        clay += head_clay(h)
    for s in (-1, 1):
        clay += [ell((0.33 * s, -0.45, 1.02), (0.22, 0.27, 0.36)),                # shoulders
                 loft([(0.33 * s, -0.5, 0.9), (0.33 * s, -0.54, 0.45), (0.33 * s, -0.56, 0.16)],
                      lambda t: lerp(0.17, 0.14, t), segs=12, rings=6),
                 ell((0.33 * s, -0.66, 0.1), (0.18, 0.23, 0.11)),                 # fore paws
                 ell((0.33 * s, 0.64, 0.98), (0.23, 0.36, 0.4)),                  # thighs
                 loft([(0.34 * s, 0.76, 0.74), (0.35 * s, 0.87, 0.42), (0.34 * s, 0.78, 0.15)],
                      lambda t: lerp(0.16, 0.13, t), segs=12, rings=6),
                 ell((0.34 * s, 0.7, 0.1), (0.17, 0.22, 0.1))]                    # hind paws
    def tuft(at, d, length=0.14, r=0.06):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.03))], lambda t: r * (1 - t) ** 0.9 + 0.006, segs=8, rings=5)
    for m in mats:                                                          # cheek tufts
        r = m.to_3x3()
        for s in (-1, 1):
            for k, (y, z) in enumerate(((-0.06, -0.08), (0.03, -0.14), (-0.13, -0.17))):
                at = m @ Vector((0.26 * s, y, z))
                clay.append(tuft(at, r @ Vector((0.9 * s, 0.3, -0.55 - 0.2 * k)), length=0.12 - 0.015 * k, r=0.055))
    for row in range(2):                                                    # a soft chest ruff below the collars
        for k in range(8 + row):
            x = -0.46 + (0.92 / (7 + row)) * k + 0.02 * math.sin(k * 2.3)
            at = Vector((x, -0.74 - 0.1 * (1 - abs(x) / 0.5) + 0.04 * row, 1.46 - 0.1 * abs(x) - 0.07 * row))
            clay.append(tuft(at, (0.4 * x + 0.15 * math.sin(k * 1.7 + row), -0.5, -0.85),
                             length=0.11 + 0.03 * math.sin(k * 2.9 + row * 1.3), r=0.05))
    for s in (-1, 1):                                                       # fluffy backs of the thighs
        for k in range(3):
            at = Vector((0.4 * s, 0.88 + 0.04 * k, 0.98 - 0.13 * k))
            clay.append(tuft(at, (0.3 * s, 0.6, -0.75), length=0.12, r=0.06))
    for k in range(6):                                                      # an ember cup of fur round the flame
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 1.1))
        clay.append(tuft(TAIL[-1] + Vector((math.cos(a), math.sin(a), 0)) * 0.05, d, length=0.1, r=0.045))
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm

    # per head: eyes, nose, mouth, in head space
    face = []
    for m, r, h in zip(mats, rots, HEADS):
        eyes = [hit(m @ Vector((0.135 * s, -1.0, 0.06)), r @ Vector((0, 1, 0))) for s in (-1, 1)]
        nose, _ = hit(m @ Vector((0, -1.0, -0.03)), r @ Vector((0, 1, 0)))
        face.append({"eyes": eyes, "nose": nose, "style": h[2]})

    MOUTH = Vector((0, -0.43, -0.185))

    def mouth_in(p, style):
        """0..1: inside the open D-shaped smile (corners up), in head space."""
        if style == "smile" or p.y > -0.28:
            return 0.0
        u = p.x / 0.13
        if abs(u) > 1.05:
            return 0.0
        top, bot = -0.15 + 0.03 * u * u, -0.225 + 0.065 * u * u
        return smooth(p.z, bot - 0.004, bot + 0.012) * smooth(p.z, top + 0.004, top - 0.012) * smooth(abs(u), 1.02, 0.8)

    def nearest_head(co):
        best, bi = 9.0, 0
        for i, h in enumerate(HEADS):
            d = (co - Vector(h[0])).length
            if d < best:
                best, bi = d, i
        return bi, best

    def smile_dist(p, style):
        if style == "smile":
            lines = [[Vector((-0.16, -0.31, -0.11)), Vector((-0.08, -0.41, -0.165)), Vector((0, -0.45, -0.15)),
                      Vector((0.08, -0.41, -0.165)), Vector((0.16, -0.31, -0.11))]]
        else:
            lines = [[Vector((-0.17, -0.3, -0.1)), Vector((-0.13, -0.37, -0.125))], [Vector((0.17, -0.3, -0.1)), Vector((0.13, -0.37, -0.125))]]
        lines.append([Vector((0, -0.5, -0.09)), Vector((0, -0.47, -0.15))])
        return min(poly_dist(p, ln) for ln in lines)

    def carve(co, n):
        i, d0 = nearest_head(co)
        clump = n * 0.012 * noise.noise(Vector((co.x * 9, co.y * 9, co.z * 2.2)))
        if co.z < 0.22 and n.z < 0.7 and n.y < 0.2:                           # toe grooves on the paws
            for px in (0.33, -0.33, 0.34, -0.34):
                for dx in (-0.055, 0.055):
                    if abs(co.x - (px + dx)) < 0.02 and abs(co.y - (-0.66 if abs(px) < 0.335 else 0.7)) < 0.3:
                        clump -= n * 0.025 * (1 - smooth(abs(co.x - (px + dx)), 0.004, 0.02)) * smooth(co.z, 0.2, 0.1)
        if d0 > 0.6:
            return clump
        p = inv[i] @ co
        d = Vector()
        for e, en in face[i]["eyes"]:
            d -= en * 0.035 * (1 - smooth((co - e).length, 0.06, 0.12))
        if p.y < -0.25:
            d += rots[i] @ Vector((0, 0.1, 0.0)) * mouth_in(p, face[i]["style"])
            deep = 0.03 if face[i]["style"] == "smile" else 0.018
            d -= n * deep * (1 - smooth(smile_dist(p, face[i]["style"]), 0.009, 0.03))
        return d
    sculpt(skin, carve)

    def keep(co):
        co = Vector(co)
        return max(0.75 * (1 - smooth((co - Vector(h[0]) - mats[i].to_3x3() @ Vector((0, -0.3, -0.05))).length, 0.25, 0.5))
                   for i, h in enumerate(HEADS))
    skin = decimate(skin, 5000, keep=keep, factor=1.0)

    tail_tip = TAIL[-1]

    def fur_colour(co, n, g=0.0):
        col = mix(COL["fur"], COL["sheen"], 0.55 * smooth(n.z, 0.2, 1.0))
        col = mix(col, COL["under"], 0.5 * smooth(-n.z, 0.2, 0.9))
        col = mix(col, COL["sheen"], 0.35 * smooth(noise.noise(Vector((co.x * 7, co.y * 7, co.z * 1.8))), 0.1, 0.5))
        ember = 0.0
        i, d0 = nearest_head(co)
        if d0 < 0.6 and co.z > 1.75:
            p = inv[i] @ co
            pn = inv[i].to_3x3() @ n
            ember = max(ember, smooth(p.z, 0.0, -0.07) * smooth(p.y, -0.06, -0.2))          # lower muzzle
            for s in (-1, 1):
                ember = max(ember, 1 - smooth(((p - Vector((0.17 * s, -0.17, -0.1))) * Vector((1, 1.2, 1.1))).length, 0.08, 0.12))
                brow = (p - Vector((0.13 * s, -0.27, 0.15))) * Vector((1, 0.6, 1.25))
                ember = max(ember, 1 - smooth(brow.length, 0.04, 0.06))
            if p.y < -0.25:
                m_in = smooth(mouth_in(p, face[i]["style"]), 0.1, 0.5)
                wide = 1.5 if face[i]["style"] == "smile" else 1.0
                line = 1 - smooth(smile_dist(p, face[i]["style"]), 0.006 * wide, 0.018 * wide)
                col = mix(col, COL["fur"], 0)
                col_e = mix(COL["ember"], COL["ember_lt"], 0.5 * smooth(pn.z, -0.2, 0.6))
                col = mix(col, col_e, ember)
                col = mix(col, COL["mouth"], max(m_in, 0.8 * line))
                return col
        # chest bib, paws, tail tip
        bib = (co - Vector((0, -0.86, 1.03))) * Vector((1 / 0.27, 1 / 0.35, 1 / 0.2))
        ember = max(ember, (1 - smooth(bib.length, 0.8, 1.0)) * smooth(-n.y, 0.1, 0.4))
        wav = 0.03 * math.sin(co.x * 40) + 0.03 * math.sin(co.y * 33)
        ember = max(ember, 1 - smooth(co.z, 0.36 + wav, 0.44 + wav))
        ember = max(ember, 1 - smooth((co - tail_tip).length, 0.12, 0.3))
        col_e = mix(COL["ember"], COL["ember_lt"], 0.4 * smooth(n.z, 0.0, 0.8))
        col_e = mix(col_e, COL["ember_dk"], 0.35 * smooth(-n.z, 0.0, 0.8))
        col = mix(col, col_e, ember)
        return col
    add("skin", paint(skin, fur_colour), fur_m)

    # ---- faces: eyes, pupils, noses, tongues, ears -----------------------------------------------------------
    for i, (m, r, f) in enumerate(zip(mats, rots, face)):
        for e, en in f["eyes"]:
            add("eyes", facing(ell((0, 0, 0), (0.078, 0.088, 0.045), cuts=3), e - en * 0.008, en), eye_m)
            pp = e + en * 0.03
            add("pupils", flat_paint(facing(ell((0, 0, 0), (0.06, 0.068, 0.02), cuts=1), pp, en), COL["pupil"]), fur_m)
            add("pupils", flat_paint(ell(pp + en * 0.016 + r @ Vector((-0.022, 0, 0.026)), (0.018, 0.018, 0.016), cuts=1), COL["white"]), fur_m)
        nose = ell((0, 0, 0), (0.085, 0.06, 0.055), cuts=2)
        for v in nose.verts:
            v.co.x *= 0.75 + 0.35 * smooth(v.co.z, -0.055, 0.055)
        nose.transform(M(f["nose"]) @ r.to_4x4())
        add("nose", flat_paint(nose, COL["nose"]), fur_m)
        if f["style"] in ("open", "tongue"):
            mc = m @ MOUTH
            fwd, down = r @ Vector((0, -1, 0)), r @ Vector((0, 0, -1))
            length = 0.16 if f["style"] == "tongue" else 0.07
            tg = loft([mc + fwd * 0.0, mc + fwd * 0.07 + down * 0.02, mc + fwd * (0.04 + length) + down * (0.02 + length * 0.7)],
                      lambda t: 0.06 * (0.8 + 0.2 * math.sin(math.pi * t)) * (1 - 0.3 * t ** 3), segs=10, rings=8, flat=0.4)
            add("tongue", paint(tg, lambda co, n, g: COL["tongue"]), fur_m)
        for s in (-1, 1):
            root = Vector((0.2 * s, 0.06, 0.18))
            pts = [root, root + Vector((0.07 * s, 0.0, 0.15)), root + Vector((0.11 * s, -0.04, 0.27)), root + Vector((0.12 * s, -0.15, 0.3)),
                   root + Vector((0.11 * s, -0.22, 0.25))]
            ear = loft([m @ p for p in pts], lambda t: 0.16 * (1 - t) ** 0.8 + 0.025, segs=8, rings=10, flat=0.34)
            rr = r

            def ear_col(co, n, g, rr=rr):
                ln = rr.inverted() @ n
                col = mix(COL["fur"], COL["sheen"], 0.5 * smooth(n.z, 0.2, 1.0))
                return mix(col, COL["ear_in"], 0.6 * smooth(-ln.y, 0.2, 0.7) * smooth(g, 0.05, 0.3))
            add("ears", paint(ear, ear_col), fur_m)

    # ---- spiked collars, one on each neck ------------------------------------------------------------------
    for k, pts in enumerate(NECKS):
        a, b = Vector(pts[0]), Vector(pts[2])
        ctr = Vector(kit._spline([Vector(p) for p in pts], 1.1))
        axis = (Vector(pts[2]) - Vector(pts[1])).normalized()
        rad = 0.235
        ring = lathe([(rad + 0.045 * math.cos(t), 0.05 * math.sin(t)) for t in (2 * math.pi * j / 6 for j in range(6))], segs=22, closed=True)
        facing(ring, ctr, axis)
        add("collar", paint(ring, lambda co, n, g: mix(COL["leather"], COL["leather_dk"], 0.5 * smooth(-n.z, 0.0, 0.8))), fur_m)
        q = axis.to_track_quat('Z', 'Y').to_matrix()
        for j in range(7):
            ang = 2 * math.pi * (j + 0.5) / 7
            out = q @ Vector((math.cos(ang), math.sin(ang), 0))
            if out.y > 0.55 and out.z < 0.3:                        # none pointing into the body
                continue
            spike = lathe([(0.042, 0.0), (0.03, 0.04), (0.01, 0.08), (0.0, 0.088)], segs=7)
            facing(spike, ctr + out * (rad + 0.07), out)
            add("spikes", paint(spike, lambda co, n, g: mix(COL["steel"], COL["steel_dk"], 0.5 * smooth(-n.z, -0.2, 0.8))), fur_m)

    # ---- the candle flame on the tail ------------------------------------------------------------------------
    base = tail_tip + Vector((0, 0, 0.03))
    fl = []
    flame = loft([base, base + Vector((0.0, -0.01, 0.12)), base + Vector((-0.04, 0.01, 0.28)), base + Vector((0.0, 0.0, 0.42)),
                  base + Vector((0.05, -0.01, 0.52))],
                 lambda t: 0.135 * math.sin(math.pi * min(t * 2.2 + 0.25, 1.0) * 0.5) ** 0.7 * (1 - t) ** 1.1 + 0.004, segs=12, rings=14)
    fl.append(flame)
    for s, h, lean in ((-1, 0.3, 0.0), (1, 0.36, 0.02)):
        lick = loft([base + Vector((0.05 * s, 0.0, 0.06)), base + Vector((0.11 * s, lean, 0.17)), base + Vector((0.1 * s, lean, h))],
                    lambda t: 0.06 * (1 - t) ** 0.9 + 0.003, segs=8, rings=6)
        fl.append(lick)
    for b in fl:
        b.transform(M(base) @ M(scale=1.3) @ M(-base))
        add("flame", b, glow)
    c.build(scale=SCALE)
    return c


def bake(c, texture):
    """Everything that neither glows nor is an eye becomes one textured mesh, <Name>_Body; anything in a
    GLOW_ material is joined into <Name>_GLOW and the glossy eyes into <Name>_Eyes. Objects are matched
    by name prefix, since Blender renames shared materials ("Eyes.001") when several pets share a scene."""
    pre = NAME + "_"
    glow = [ob for ob in c.objects if ob.name.startswith(pre + "GLOW")]
    eyes = [ob for ob in c.objects if ob.name.startswith(pre + "Eyes")]
    body = kit.bake_texture([ob for ob in c.objects if ob not in glow and ob not in eyes], texture, name=pre + "Body",
                            shade=BAKE["shade"], soften=3, rough=BAKE["rough"], uv_angle=66.0, uv_margin=0.004,
                            pack_margin=0.003)
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
