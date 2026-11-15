"""DuskBat pet: a fluffy dusk-purple fruit bat, remade from the game's purple bat with a cat-like face.
Built from scratch by script.

    python models/pets/duskbat.py --review out/duskbat.png      # render the review sheet
    python models/pets/duskbat.py --export models/export/duskbat.fbx

Must-haves, checked in every review:
  1. The same creature: a round purple bat standing with its wings spread wide.
  2. A fruit bat, clearly not the red InfernoBat: a plump soft body, a fox-like muzzle, big soft
     rounded ears, a cream bib of fluff (no spiky ruff), no flames, no horns.
  3. Big gentle dark eyes with catchlights and a tiny smile.
  4. Translucent-looking lilac wings: membranes on visible finger bones, each panel a smooth scallop
     (never torn or jagged), lighter towards the edges.
  5. Matte painted fur with roughness variation; about 3 studs tall; Body under 12k triangles.

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
# ---- the dusk bat ----------------------------------------------------------------------------------

NAME = "DuskBat"
COL = {"fur": hexc("#5C4884"), "fur_lt": hexc("#7C66A6"), "fur_dk": hexc("#3C2E5E"), "cream": hexc("#EEE2CA"),
       "cream_dk": hexc("#CDBB9E"), "muzzle": hexc("#8C78AE"), "nose": hexc("#2A1E30"), "mouth": hexc("#3A2238"),
       "ear_in": hexc("#C9A0D8"), "bone": hexc("#4A3868"), "bone_lt": hexc("#6A5490"), "mem": hexc("#B48CDC"),
       "mem_lt": hexc("#DCC4F2"), "mem_edge": hexc("#9A72C6"), "white": hexc("#FFFFFF"), "claw": hexc("#2E2430")}
SCALE = 1.0
BAKE = {"shade": 0.4, "rough": 0.9, "vary": 0.1}
HEAD = Vector((0, -0.14, 2.12))
HEAD_M = M(HEAD, rot=(-4, 0, 0))
FACE = HEAD + Vector((0, -0.35, -0.04))
FOCUS = FACE
FACE_DIST = 3.6


def membrane(W, edges, sags, thick=0.016, nr=6, ns=8):
    """A thin wing membrane fanned out from the wrist W to a chain of edge points. Between each pair of
    edge points the trailing edge curves in towards the wrist by that sector's sag (a smooth scallop,
    never torn). Each vertex keeps g = how far out from the wrist (0..1) for painting, and the layer
    'bone' = how close it is to a finger line (1 on a bone)."""
    bm = bmesh.new()
    lg = bm.verts.layers.float.new("g")
    lb = bm.verts.layers.float.new("bone")
    W = Vector(W)
    # one continuous grid over all sectors: s runs along the edge chain
    cols = []
    for k in range(len(edges) - 1):
        a, b = Vector(edges[k]), Vector(edges[k + 1])
        for j in range(ns if k < len(edges) - 2 else ns + 1):
            s = j / ns
            e = a.lerp(b, s)
            e = e + (W - e) * sags[k] * math.sin(math.pi * s)
            cols.append((e, min(s, 1 - s)))
    nrm = (Vector(edges[0]) - W).cross(Vector(edges[-1]) - W).normalized()
    grids = []
    for side in (1, -1):
        g = []
        for e, sb in cols:
            row = []
            for i in range(nr + 1):
                r = i / nr
                p = W + (e - W) * r + nrm * side * thick * 0.5 * (1 - 0.5 * r)
                p += nrm * 0.06 * math.sin(math.pi * r) * (1 - 2 * sb) * 0.5           # a soft billow
                v = bm.verts.new(p)
                v[lg] = r
                v[lb] = 1 - smooth(sb, 0.0, 0.12)
                row.append(v)
            g.append(row)
        grids.append(g)
    top, bot = grids
    n = len(cols)
    for j in range(n - 1):
        for i in range(nr):
            bm.faces.new((top[j][i], top[j + 1][i], top[j + 1][i + 1], top[j][i + 1]))
            bm.faces.new((bot[j][i], bot[j][i + 1], bot[j + 1][i + 1], bot[j + 1][i]))
    ring = [(0, i) for i in range(nr + 1)] + [(j, nr) for j in range(1, n)] + \
           [(n - 1, i) for i in range(nr - 1, -1, -1)] + [(j, 0) for j in range(n - 2, 0, -1)]
    for (j0, i0), (j1, i1) in zip(ring, ring[1:] + ring[:1]):
        if top[j0][i0] is top[j1][i1]:
            continue
        try:
            bm.faces.new((top[j0][i0], bot[j0][i0], bot[j1][i1], top[j1][i1]))
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build():
    fur_m = painted("Fur", dict(strength=0.32, mottle=0.12, fine=50.0, length=4.0), rough=0.94)
    eye_m = kit.material("Eyes", "#24161C", rough=0.05)
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

    def tuft(at, d, length=0.12, r=0.06):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.02))], lambda t: r * (1 - t) ** 0.9 + 0.006, segs=8, rings=5)

    # ---- one fused skin: a plump round body, a round head with a fox-like muzzle, little legs ---------
    clay = [ell((0, 0.02, 1.3), (0.5, 0.44, 0.6)),
            ell((0, -0.12, 1.62), (0.42, 0.38, 0.36)),                         # chest
            ell(hd((0, 0.03, 0.03)), (0.4, 0.37, 0.37)),                       # head
            ell(hd((0, -0.3, -0.09)), (0.15, 0.2, 0.13)),                      # muzzle
            ell(hd((0, -0.44, -0.08)), (0.09, 0.12, 0.08))]                    # snout tip
    for s in (-1, 1):
        clay += [ell(hd((0.2 * s, -0.12, -0.1)), (0.17, 0.17, 0.15)),         # cheeks
                 loft([(0.22 * s, 0.0, 0.85), (0.24 * s, -0.04, 0.45), (0.24 * s, -0.08, 0.12)], lambda t: lerp(0.12, 0.08, t), segs=10, rings=6),
                 ell((0.24 * s, -0.16, 0.06), (0.1, 0.15, 0.06))]              # feet
    for row in range(3):                                                       # a soft cream bib of fluff
        for k in range(7 - row):
            x = -0.24 + 0.48 * k / max(6 - row, 1)
            at = Vector((x, -0.4 + 0.12 * abs(x) + 0.03 * row, 1.72 - 0.16 * row - 0.15 * x * x))
            clay.append(tuft(at, (0.3 * x, -0.6, -0.8), length=0.12, r=0.07))
    for k in range(10):                                                        # a fluffy crown and back
        a = k * 2.4
        at = Vector((0.3 * math.sin(a), 0.1 + 0.2 * math.cos(a), 1.75 + 0.05 * math.sin(k)))
        clay.append(tuft(at, (0.6 * math.sin(a), 0.5, 0.3), length=0.12, r=0.07))
    skin = fuse(join(clay), voxel=0.02, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    fwd = R @ Vector((0, 1, 0))
    eyes = [hit(hd((0.165 * s, -1.5, 0.07)), fwd) for s in (-1, 1)]
    nose_at, _ = hit(hd((0, -1.5, -0.06)), fwd)
    smile = [hit(hd((x, -1.5, -0.15 + 2.5 * x * x)), fwd)[0] for x in (-0.07, -0.035, 0.0, 0.035, 0.07)]

    def carve(co, n):
        d = n * 0.014 * noise.noise(Vector((co.x * 10, co.y * 10, co.z * 3)))
        for e, en in eyes:
            d -= en * 0.04 * (1 - smooth((co - e).length, 0.08, 0.15))
        if (co - nose_at).length < 0.25:
            d -= n * 0.012 * (1 - smooth(poly_dist(co, smile), 0.005, 0.016))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 6000, keep=lambda co: 0.8 * (1 - smooth((Vector(co) - hd((0, -0.25, -0.05))).length, 0.25, 0.48)), factor=1.0)

    def fur_colour(co, n, g=0.0):
        col = mix(COL["fur_dk"], COL["fur"], smooth(n.z, -0.6, 0.2))
        col = mix(col, COL["fur_lt"], 0.45 * smooth(n.z, 0.4, 1.0))
        col = mix(col, COL["fur_dk"], 0.25 * smooth(noise.noise(Vector((co.x * 7, co.y * 7, co.z * 2))), 0.15, 0.6))
        bib = (co - Vector((0, -0.42, 1.5))) * Vector((1 / 0.3, 1 / 0.4, 1 / 0.36))
        col = mix(col, mix(COL["cream"], COL["cream_dk"], 0.4 * smooth(-n.z, 0.0, 0.6)), (1 - smooth(bib.length, 0.75, 1.0)) * smooth(-n.y, 0.0, 0.3))
        col = mix(col, COL["fur_dk"], 0.6 * smooth(co.z, 0.5, 0.2))
        if (co - HEAD).length < 0.6:
            p = HEAD_M.inverted() @ co
            col = mix(col, COL["muzzle"], 0.7 * smooth(p.y, -0.22, -0.34))
            col = mix(col, COL["cream"], 0.55 * smooth(p.y, -0.25, -0.35) * smooth(p.z, -0.1, -0.16))           # pale chin
            if (co - nose_at).length < 0.25:
                col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.005, 0.012))
        return col
    add("skin", skin, fur_m, fur_colour)

    # ---- big gentle eyes -----------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        en = (en * 0.4 + R @ Vector((0, -1, 0)) * 0.6).normalized()
        add("eyes", facing(ell((0, 0, 0), (0.1, 0.11, 0.065), cuts=3), e - en * 0.02, en), eye_m)
        add("glints", ell(e + en * 0.04 + R @ Vector((-0.03, 0, 0.035)), (0.026, 0.012, 0.026), cuts=2), fur_m, COL["white"])
        add("glints", ell(e + en * 0.036 + R @ Vector((0.028, 0, -0.03)), (0.012, 0.008, 0.012), cuts=1), fur_m, COL["white"])
    nose = ell((0, 0, 0), (0.05, 0.03, 0.035), cuts=2)
    for v in nose.verts:
        v.co.x *= 0.6 + 0.4 * smooth(v.co.z, -0.035, 0.035)
    nose.transform(M(nose_at) @ R.to_4x4())
    add("nose", glossy(nose, 0.45), fur_m, COL["nose"])

    # ---- big soft ears ---------------------------------------------------------------------------------
    for s in (-1, 1):
        root = hd((0.2 * s, 0.04, 0.26))
        pts = [root, root + R @ Vector((0.06 * s, -0.01, 0.16)), root + R @ Vector((0.12 * s, 0.0, 0.32)), root + R @ Vector((0.15 * s, 0.02, 0.42))]
        ear = loft(pts, lambda t: 0.16 * math.sin(math.pi * min(0.3 + t * 0.8, 1.0)) ** 0.6 + 0.015, segs=12, rings=12, flat=0.4)
        for v in ear.verts:
            gg = v[ear.verts.layers.float["g"]]
            off = v.co - kit._spline(pts, gg * 3)
            if off.y < 0:
                v.co.y -= off.y * 0.6 * smooth(gg, 0.05, 0.25) * smooth(gg, 1.0, 0.85)

        def ear_col(co, n, g):
            col = mix(COL["fur_dk"], COL["fur"], smooth(n.z, -0.3, 0.5))
            return mix(col, COL["ear_in"], 0.8 * smooth(-n.y, 0.3, 0.75) * smooth(g, 0.06, 0.2) * smooth(g, 0.95, 0.8))
        add("ears", ear, fur_m, ear_col)

    # ---- wings: lilac membranes on finger bones, spread wide and soft ------------------------------------
    for s in (-1, 1):
        S = Vector((0.38 * s, 0.04, 1.78))
        Wr = Vector((1.0 * s, -0.12, 2.3))
        tips = [Vector((1.48 * s, -0.16, 2.62)), Vector((1.92 * s, -0.02, 2.18)), Vector((1.78 * s, 0.1, 1.6)), Vector((1.25 * s, 0.14, 1.12))]
        H = Vector((0.42 * s, 0.1, 1.05))
        edges = [S, tips[0], tips[1], tips[2], tips[3], H]
        sags = [0.04, 0.16, 0.18, 0.18, 0.16]
        mem = membrane(Wr, edges, sags)
        lb = mem.verts.layers.float["bone"]

        def mem_col(co, n, g):
            return mix(mix(COL["mem"], COL["mem_lt"], smooth(g, 0.25, 0.85)), COL["mem_edge"], 0.5 * smooth(g, 0.93, 1.0))
        paint(mem, mem_col)
        lay = mem.verts.layers.float_color["col"]
        for v in mem.verts:                                                    # darker along the finger lines
            k = v[lb] * 0.6
            v[lay] = (*mix(tuple(v[lay])[:3], COL["bone_lt"], k), 1.0)
        add("wings", glossy(mem, 0.3), fur_m)
        # arm and finger bones, raised under the membrane
        add("bones", loft([S, S.lerp(Wr, 0.5) + Vector((0, -0.04, 0.06)), Wr], lambda t: lerp(0.07, 0.045, t), segs=8, rings=8), fur_m,
            lambda co, n, g: mix(COL["fur"], COL["bone"], smooth(g, 0.2, 0.5)))
        for k, t in enumerate(tips):
            add("bones", loft([Wr, Wr.lerp(t, 0.5) + Vector((0, -0.02, 0.02)), t], lambda u: 0.03 * (1 - u) + 0.008, segs=6, rings=8), fur_m, COL["bone"])
        thumb = Wr + Vector((0.02 * s, -0.12, 0.1))
        add("bones", loft([Wr, thumb], lambda u: 0.03 * (1 - u) + 0.006, segs=6, rings=4), fur_m, COL["claw"])
        add("wings", tuft(S + Vector((0, -0.02, 0.06)), (s, -0.2, 0.3), length=0.16, r=0.09), fur_m, COL["fur"])   # furry shoulder

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
