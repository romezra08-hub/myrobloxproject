"""Grizzly pet: a powerful but likeable grizzly bear, remade from the game's big brown bear with spikes
down its back and long claws. Built from scratch by script.

    python models/pets/grizzly.py --review out/grizzly.png      # render the review sheet
    python models/pets/grizzly.py --export models/export/grizzly.fbx

Must-haves, checked in every review:
  1. The same creature: a big brown bear on all fours with something along its back.
  2. Powerful and adult, not childish: a heavy body, a big shoulder hump, thick legs, a broad head
     carried low, small eyes.
  3. Thick layered fur: overlapping rows of locks on the hump, shoulders and flanks, a cheek ruff,
     grizzled pale tips on the back, darker legs.
  4. A calm face: small dark eyes under soft lids, a broad dark nose, a closed mouth; short claws.
  5. No spikes: a few mossy stones caught in the fur of the hump, so it belongs in the mine.
  6. Matte painted fur with roughness variation; 3-4.5 studs tall; Body under 12k triangles.

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
# ---- the grizzly -----------------------------------------------------------------------------------

NAME = "Grizzly"
COL = {"fur": hexc("#6A4630"), "fur_lt": hexc("#A47C54"), "fur_dk": hexc("#3C281B"), "tip": hexc("#C49A6C"),
       "muzzle": hexc("#9E7C5C"), "muzzle_dk": hexc("#6E523C"), "nose": hexc("#1C1412"), "mouth": hexc("#2A1A14"),
       "claw": hexc("#D8CCB4"), "claw_dk": hexc("#8A7E6C"), "ear_in": hexc("#4A3224"), "white": hexc("#FFFFFF"),
       "stone": hexc("#8A8680"), "stone_dk": hexc("#5E5A56"), "moss": hexc("#6E9A3A"), "moss_dk": hexc("#456A24")}
SCALE = 1.0
BAKE = {"shade": 0.45, "rough": 0.92, "vary": 0.1}
HEAD = Vector((0, -1.72, 1.72))
HEAD_M = M(HEAD, rot=(-10, 0, 7))
FACE = HEAD + Vector((0, -0.35, -0.08))
FOCUS = FACE
FACE_DIST = 4.6


def build():
    fur_m = painted("Fur", dict(strength=0.38, mottle=0.12, fine=44.0, length=6.0), rough=0.94)
    eye_m = kit.material("Eyes", "#24150E", rough=0.05)
    c = Prop(NAME)
    c.tally = {}
    R = HEAD_M.to_3x3()

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def hd(p):
        return HEAD_M @ Vector(p)

    def tuft(at, d, length=0.18, r=0.09, droop=0.3, flat=0.6):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length * 0.9 + Vector((0, 0, -length * droop))],
                    lambda t: r * (1 - t) ** 0.8 + 0.008, segs=8, rings=5, flat=flat)

    # ---- one fused skin: a heavy body with a shoulder hump, thick legs, broad head ---------------------
    clay = [ell((0, 0.2, 1.55), (0.72, 1.15, 0.68)),
            ell((0, -0.65, 1.6), (0.7, 0.6, 0.72)),                            # chest
            ell((0, -0.5, 2.06), (0.56, 0.52, 0.36)),                          # shoulder hump
            ell((0, 1.05, 1.62), (0.66, 0.55, 0.62)),                          # rump
            loft([(0, -0.95, 1.8), (0, -1.3, 1.76), (0, -1.55, 1.72)], lambda t: lerp(0.5, 0.42, t), segs=16, rings=6),
            ell(hd((0, 0.02, 0.03)), (0.43, 0.4, 0.38)),                       # cranium
            ell(hd((0, -0.34, -0.13)), (0.22, 0.3, 0.18)),                     # muzzle
            ell(hd((0, -0.28, -0.24)), (0.16, 0.2, 0.08)),                     # chin
            ell((0, 1.62, 1.75), (0.13, 0.12, 0.12))]                          # stub tail
    for s in (-1, 1):
        clay += [ell(hd((0.27 * s, -0.06, -0.1)), (0.23, 0.22, 0.2)),         # cheeks
                 ell((0.44 * s, -0.72, 1.3), (0.3, 0.38, 0.55)),              # shoulders
                 loft([(0.43 * s, -0.75, 1.15), (0.44 * s, -0.82, 0.62), (0.43 * s, -0.86, 0.22)], lambda t: lerp(0.29, 0.23, t), segs=14, rings=8),
                 ell((0.43 * s, -0.98, 0.12), (0.25, 0.3, 0.13)),             # fore paws
                 ell((0.46 * s, 1.05, 1.35), (0.33, 0.52, 0.56)),             # thighs
                 loft([(0.46 * s, 1.12, 1.15), (0.47 * s, 1.26, 0.64), (0.46 * s, 1.12, 0.22)], lambda t: lerp(0.28, 0.22, t), segs=14, rings=8),
                 ell((0.46 * s, 1.0, 0.12), (0.24, 0.32, 0.13))]              # hind paws
    # layered fur: overlapping rows of locks sweeping back and down over the hump, shoulders and flanks
    for row in range(6):
        ang = math.radians(15 + 30 * row)                                      # from the flank up to the spine
        for k in range(9):
            y = -0.95 + 0.27 * k + 0.12 * (row % 2)
            hump = 0.32 * smooth(y, -0.1, -0.5) * smooth(y, -1.0, -0.75)
            for s in (-1, 1):
                if row == 5 and s == 1:
                    continue
                side = math.cos(ang) * s
                up = math.sin(ang)
                at = Vector((0.66 * side, y, 1.55 + (0.64 + hump) * up))
                d = Vector((side * 0.45, 0.85, -0.35 - 0.3 * (1 - up)))
                clay.append(tuft(at, d, length=0.22 + 0.03 * math.sin(k * 1.7 + row), r=0.1, droop=0.25))
    for s in (-1, 1):
        for k in range(5):                                                     # a cheek ruff
            at = hd((0.36 * s, 0.0 + 0.07 * k, -0.08 - 0.04 * k))
            clay.append(tuft(at, R @ Vector((s * 0.7, 0.5, -0.5)), length=0.17, r=0.08))
        for k in range(4):                                                     # feathering on the backs of the forelegs
            clay.append(tuft((0.44 * s, -0.6, 1.05 - 0.15 * k), (0.3 * s, 0.8, -0.6), length=0.17, r=0.08))
    skin = fuse(join(clay), voxel=0.026, iterations=2)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.18 * s, -1.5, 0.08)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.08)), fwd)
    mouth = [[hit(hd((0, -1.5, -0.12)), fwd)[0], hit(hd((0, -1.5, -0.19)), fwd)[0]]]
    for s in (-1, 1):
        mouth.append([hit(hd((0, -1.5, -0.19)), fwd)[0], hit(hd((0.06 * s, -1.5, -0.215)), fwd)[0], hit(hd((0.12 * s, -1.5, -0.2)), fwd)[0]])

    def carve(co, n):
        d = n * 0.02 * noise.noise(Vector((co.x * 8, co.y * 8, co.z * 2)))
        for e, en in eyes:
            d -= en * 0.025 * (1 - smooth((co - e).length, 0.05, 0.1))
        if (co - nose_at).length < 0.35:
            d -= n * 0.014 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.006, 0.018))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 9000, keep=lambda co: max(0.8 * (1 - smooth((Vector(co) - hd((0, -0.3, -0.08))).length, 0.25, 0.5)),
                                                    0.4 * (1 - smooth((Vector(co) - HEAD).length, 0.45, 0.65))), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(COL["fur_dk"], COL["fur"], smooth(n.z, -0.6, 0.1))
        col = mix(col, COL["fur_lt"], 0.55 * smooth(n.z, 0.35, 1.0))
        # grizzled pale tips on the hump and back
        griz = smooth(noise.noise(Vector((co.x * 9, co.y * 9, co.z * 4))), 0.1, 0.5) * smooth(n.z, 0.4, 0.9) * smooth(co.z, 1.8, 2.3)
        col = mix(col, COL["tip"], 0.5 * griz)
        col = mix(col, COL["fur_dk"], 0.3 * smooth(noise.noise(Vector((co.x * 4, co.y * 4, co.z * 1.5))), 0.2, 0.7))
        col = mix(col, COL["fur_dk"], 0.6 * smooth(co.z, 0.85, 0.35))                       # dark legs
        if (co - HEAD).length < 0.65:
            p = HEAD_M.inverted() @ co
            mz = smooth(p.y, -0.24, -0.36)
            col = mix(col, mix(COL["muzzle"], COL["muzzle_dk"], 0.4 * smooth(-p.z, 0.15, 0.3)), mz)
            col = mix(col, COL["muzzle"], 0.3 * smooth(p.z, 0.1, 0.18) * smooth(p.y, -0.15, -0.3))           # pale brow bridge
            if (co - nose_at).length < 0.35:
                col = mix(col, COL["mouth"], 0.9 * (1 - smooth(min(poly_dist(co, m) for m in mouth), 0.006, 0.014)))
        return col
    add("skin", skin, fur_m, fur_colour)

    # ---- small calm eyes, a broad nose, round ears ----------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        add("eyes", facing(ell((0, 0, 0), (0.06, 0.058, 0.035), cuts=3), e - en * 0.008, en), eye_m)
        add("glints", ell(e + en * 0.026 + R @ Vector((-0.017, 0, 0.018)), (0.014, 0.008, 0.014), cuts=1), fur_m, COL["white"])
        lid = facing(ell((0, 0, 0), (0.07, 0.066, 0.042), cuts=4), e - en * 0.006, en)
        bmesh.ops.delete(lid, geom=[v for v in lid.verts if (v.co - e).dot(R @ Vector((0, 0, 1))) < 0.022], context='VERTS')
        add("lids", lid, fur_m, COL["fur_dk"])
    nose = ell((0, 0, 0), (0.12, 0.07, 0.07), cuts=3)
    for v in nose.verts:
        v.co.x *= 0.7 + 0.3 * smooth(v.co.z, -0.07, 0.07)
    nose.transform(M(nose_at + fwd * -0.01) @ R.to_4x4())
    add("nose", glossy(nose, 0.5), fur_m, COL["nose"])
    for s in (-1, 1):
        root = hd((0.29 * s, 0.1, 0.27))
        ear = loft([root, root + R @ Vector((0.05 * s, 0.0, 0.08)), root + R @ Vector((0.07 * s, 0.01, 0.13))],
                   lambda t: 0.1 * math.sin(math.pi * min(0.35 + t * 0.8, 1.0)) ** 0.5 + 0.02, segs=12, rings=8, flat=0.5)
        add("ears", ear, fur_m, lambda co, n, g: mix(COL["fur"], COL["ear_in"], 0.7 * smooth(-n.y, 0.3, 0.7) * smooth(g, 0.1, 0.3)))

    # ---- short claws peeking from each paw --------------------------------------------------------------------
    for (x, y) in ((-0.43, -0.98), (0.43, -0.98), (-0.46, 1.0), (0.46, 1.0)):
        front_y = y - (0.28 if y < 0 else 0.3)
        for k in range(4):
            cx = x + (k - 1.5) * 0.085
            root, _ = hit((cx, front_y - 0.5, 0.09), (0, 1, 0))
            if root is None:
                continue
            claw = loft([root + Vector((0, 0.02, 0)), root + Vector((0, -0.05, -0.01)), root + Vector((0, -0.08, -0.05))],
                        lambda t: 0.028 * (1 - t) ** 0.7 + 0.006, segs=6, rings=4, flat=0.8)
            add("claws", glossy(claw, 0.4), fur_m, lambda co, n, g: mix(COL["claw"], COL["claw_dk"], smooth(g, 0.3, 1.0)))

    # ---- a few mossy stones caught in the fur of the hump (the original's back spikes, now from the mine) -----
    for k, (y, x, r) in enumerate(((-0.62, 0.05, 0.11), (-0.3, -0.12, 0.09), (0.05, 0.1, 0.08), (0.4, -0.06, 0.07))):
        top, tn = hit((x, y, 4), (0, 0, -1))
        st = ell((0, 0, 0), (r * 1.2, r, r * 0.75), cuts=3)
        kit.lumpy(st, amount=r * 0.25, freq=8.0, seed=k)
        st.transform(M(top + tn * r * 0.2, rot=(10 * k, -15 + 9 * k, 30 * k)))
        add("stones", st, fur_m, lambda co, n, g: mix(mix(COL["stone_dk"], COL["stone"], smooth(n.z, -0.2, 0.7)),
                                                       COL["moss"], smooth(n.z, 0.55, 0.85) * smooth(noise.noise(co * 25.0), -0.3, 0.2)))
        for j in range(3):                                                    # a little moss beside each stone
            a = j * 2.1 + k
            at = top + Vector((math.cos(a) * r * 1.3, math.sin(a) * r * 1.3, -0.02))
            add("moss", tuft(at, (math.cos(a), math.sin(a), 0.8), length=0.07, r=0.035, droop=0.0, flat=1.0), fur_m,
                lambda co, n, g: mix(COL["moss_dk"], COL["moss"], smooth(g, 0.0, 0.8)))

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
