"""Moth pet: a beautiful fluffy moth, remade from the game's dark moth with big brown and orange
eye-spotted wings. Built from scratch by script.

    python models/pets/moth.py --review out/moth.png      # render the review sheet
    python models/pets/moth.py --export models/export/moth.fbx

Must-haves, checked in every review:
  1. The same creature: a dark moth with a white fluffy collar and big raised brown and orange wings.
  2. A soft fuzzy body: a cream ruff round the neck, a fluffy head and a banded furry abdomen.
  3. Big feathery antennae.
  4. Large dark eyes with a highlight and a tiny smile (no staring yellow eyes).
  5. Wings in brown, orange and cream with soft swirl patterns, no eye spots.
  6. Matte painted textures with crease shading; 3-4.5 studs tall; Body under 9k triangles.
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




# ---- the fluffy moth -------------------------------------------------------------------------------

NAME = "Moth"
COL = {"head": hexc("#3B2A24"), "head_lt": hexc("#5C4436"), "ruff": hexc("#F1E6D2"), "ruff_dk": hexc("#CDBDA2"),
       "thorax": hexc("#4A3428"), "band": hexc("#6E4A34"), "band_lt": hexc("#D8C2A0"), "leg": hexc("#2E221E"),
       "mouth": hexc("#7A2E2E"), "white": hexc("#FFFFFF"), "ant": hexc("#D8B888"), "ant_dk": hexc("#8A6444"),
       "w_dark": hexc("#4E2E22"), "w_brown": hexc("#8A5434"), "w_tan": hexc("#B98A5E"), "w_orange": hexc("#E37A2B"),
       "w_amber": hexc("#F0A040"), "w_cream": hexc("#F4E4C4")}
SCALE = 1.0
BAKE = {"shade": 0.42, "rough": 0.9}
H = Vector((0, -0.28, 2.05))                 # head
T = Vector((0, 0.0, 1.62))                   # thorax
AXIS = (H - T).normalized()
FACE = H + Vector((0, -0.25, 0.0))
FOCUS = FACE
FACE_DIST = 3.6


def wing(root, span, chord, L, width, nu=14, nv=8, thick=0.022, camber=0.04):
    """A thin wing slab. u runs along the span (0 root to 1 tip), v across the chord (0 leading edge,
    1 trailing edge); width(u) is the chord at u. Every corner carries (u, v) in the UV layer "WingUV",
    which reads the wing's painted pattern image (see wing_image)."""
    span, chord = Vector(span).normalized(), Vector(chord).normalized()
    nrm = span.cross(chord).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("WingUV")
    uvs = {}
    grids = []
    for side in (1, -1):
        g = []
        for i in range(nu + 1):
            u = i / nu
            row = []
            w = width(u)
            for j in range(nv + 1):
                v = j / nv
                p = root + span * (u * L) + chord * ((v - 0.35) * w) + nrm * (camber * math.sin(math.pi * v) * (0.3 + u) + side * thick * 0.5 * (1 - 0.6 * u))
                vert = bm.verts.new(p)
                uvs[vert] = (u, v)
                row.append(vert)
            g.append(row)
        grids.append(g)
    top, bot = grids
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    ring = [(0, j) for j in range(nv + 1)] + [(i, nv) for i in range(1, nu + 1)] + \
           [(nu, j) for j in range(nv - 1, -1, -1)] + [(i, 0) for i in range(nu - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((top[i0][j0], bot[i0][j0], bot[i1][j1], top[i1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        for lp in f.loops:
            u, v = uvs[lp.vert]
            lp[uvl].uv = (min(max(u, 0.004), 0.996), min(max(v, 0.008), 0.992))
    return bm


def wing_image(name, colour, L, width, W=384, Hh=192):
    """Paint a wing pattern into an image: pixel (u, v) gets colour(u, v, x, y), x and y in studs."""
    img = bpy.data.images.new(name, W, Hh, alpha=False, float_buffer=True)
    px = []
    for j in range(Hh):
        v = (j + 0.5) / Hh
        for i in range(W):
            u = (i + 0.5) / W
            px += [*colour(u, v, u * L, v * width(u)), 1.0]
    img.pixels.foreach_set(px)
    img.pack()
    return img


def wing_mat(name, img):
    m = kit.material(name, "#808080", rough=0.9)
    tree = m.node_tree
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "WingUV"
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tree.links.new(uv.outputs[0], tex.inputs[0])
    tree.links.new(tex.outputs[0], kit.principled(m).inputs["Base Color"])
    return m


def before_bake(parts):
    """Bake into a fresh first UV layer, leaving the wings' pattern layer for the bake to read."""
    for ob in parts:
        uvs = ob.data.uv_layers
        if "UVMap" not in uvs:
            uvs.new(name="UVMap")
        uvs.active = uvs["UVMap"]
        uvs["UVMap"].active_render = True


def after_bake(body):
    uvs = body.data.uv_layers
    if "WingUV" in uvs:
        uvs.remove(uvs["WingUV"])


def swirl(x, y, cx, cy, size, turns=1.6):
    """0..1: a soft cream spiral curl of radius `size` centred on (cx, cy)."""
    dx, dy = x - cx, y - cy
    r = math.hypot(dx, dy)
    if r > size:
        return 0.0
    a = math.atan2(dy, dx) / (2 * math.pi)
    f = (a - r / size * turns) % 1.0
    line = 1 - smooth(abs(f - 0.5), 0.07, 0.16)
    return line * smooth(r, size, size * 0.75) * smooth(r, 0.0, size * 0.15)


def grain(x, y, k=40.0):
    return noise.noise(Vector((x * k, y * k * 0.35, 0.5)))


def veins(u, v, n=5):
    """0..1: thin darker wing veins fanning out from the root."""
    best = 1.0
    for k in range(1, n):
        vk = k / n + 0.06 * (u - 0.5)
        best = min(best, abs(v - vk))
    return (1 - smooth(best, 0.004, 0.012)) * smooth(u, 0.1, 0.25) * smooth(u, 0.9, 0.8)


def fore_colour(u, v, x, y):
    col = mix(COL["w_dark"], COL["w_brown"], smooth(u, 0.05, 0.4))
    col = mix(col, COL["w_tan"], 0.35 * smooth(v, 0.3, 0.0) * smooth(u, 0.2, 0.5))
    u0 = 0.47 + 0.04 * math.sin(v * 8.0)
    col = mix(col, COL["w_orange"], 1 - smooth(abs(u - u0), 0.07, 0.15))
    col = mix(col, COL["w_amber"], 0.6 * (1 - smooth(abs(u - u0), 0.0, 0.06)))
    col = mix(col, COL["w_cream"], 0.9 * swirl(x, y, 1.22, 0.42, 0.26))
    col = mix(col, COL["w_cream"], 0.8 * swirl(x, y, 0.62, 0.48, 0.15, turns=1.3))
    m = 0.86 + 0.018 * math.sin(v * 22.0)
    col = mix(col, COL["w_dark"], 0.6 * smooth(u, m - 0.02, m + 0.02))
    col = mix(col, COL["w_cream"], 0.85 * (1 - smooth(abs(u - m), 0.006, 0.02)))
    col = mix(col, COL["w_tan"], 0.7 * smooth(u, 0.96, 0.99))
    col = mix(col, COL["w_dark"], 0.35 * smooth(v, 0.85, 1.0))
    col = mix(col, COL["w_dark"], 0.3 * veins(u, v))
    col = tuple(ch * (1 + 0.08 * grain(x, y)) for ch in col)
    return mix(col, COL["w_tan"], 0.8 * smooth(u, 0.13, 0.03))                # fuzzy root


def hind_colour(u, v, x, y):
    col = mix(COL["w_brown"], COL["w_orange"], smooth(u, 0.05, 0.35))
    col = mix(col, COL["w_amber"], 0.5 * (1 - smooth(abs(u - 0.5), 0.05, 0.2)))
    col = mix(col, COL["w_cream"], 0.85 * swirl(x, y, 0.72, 0.4, 0.2, turns=1.4))
    m = 0.8 + 0.02 * math.sin(v * 18.0)
    col = mix(col, COL["w_dark"], 0.75 * smooth(u, m - 0.02, m + 0.03))
    col = mix(col, COL["w_cream"], 0.8 * (1 - smooth(abs(u - (m + 0.08)), 0.006, 0.02)))
    col = mix(col, COL["w_brown"], 0.3 * veins(u, v, 4))
    col = tuple(ch * (1 + 0.08 * grain(x, y)) for ch in col)
    return mix(col, COL["w_tan"], 0.8 * smooth(u, 0.15, 0.04))


def build():
    fur_m = painted("Fur", dict(strength=0.36, mottle=0.12, fine=46.0, length=4.0), rough=0.95)
    fore_w = lambda u: 0.98 * math.sin(math.pi * min(0.12 + u * 0.95, 1.0) * 0.5) ** 0.5 * (1 - u ** 3) ** 0.5 + 0.06
    hind_w = lambda u: 0.85 * math.sin(math.pi * min(0.15 + u * 0.9, 1.0) * 0.5) ** 0.5 * (1 - u ** 2.5) ** 0.5 + 0.06
    fore_m = wing_mat("WingFore", wing_image("MothForewing", fore_colour, 1.95, fore_w))
    hind_m = wing_mat("WingHind", wing_image("MothHindwing", hind_colour, 1.3, hind_w, W=256, Hh=160))
    eye_m = kit.material("Eyes", "#1C1412", rough=0.06)
    c = Prop(NAME)
    c.tally = {}

    def add(part, bm, mat, col=None):
        if col is not None:
            paint(bm, col) if callable(col) else flat_paint(bm, col)
        c.tally[part] = c.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        c.add(bm, mat)

    def tuft(at, d, length=0.18, r=0.07):
        at, d = Vector(at), Vector(d).normalized()
        return loft([at, at + d * length * 0.55, at + d * length + Vector((0, 0, -0.02))], lambda t: r * (1 - t) ** 0.9 + 0.006, segs=8, rings=5)

    # ---- the fluffy body: head, ruff, thorax, abdomen ---------------------------------------------------
    abdomen = [T + Vector((0, 0.1, -0.1)), Vector((0, 0.32, 1.05)), Vector((0, 0.46, 0.55)), Vector((0, 0.48, 0.2))]
    clay = [ell(H, (0.37, 0.34, 0.35)), ell(H + Vector((0, -0.12, -0.08)), (0.27, 0.22, 0.22)),
            ell(T, (0.4, 0.4, 0.42)),
            loft(abdomen, lambda t: 0.38 * (1 - 0.72 * t ** 1.4) * (1 + 0.05 * math.sin(t * math.pi * 9)), segs=14, rings=18)]
    side = AXIS.cross(Vector((1, 0, 0))).normalized()
    ruff_c = H.lerp(T, 0.55)
    for row, (k_n, rad, back) in enumerate(((22, 0.36, 0.3), (19, 0.33, 0.7), (15, 0.3, 1.1))):
        for k in range(k_n):
            a = 2 * math.pi * (k + 0.5 * row) / k_n
            out = Vector((1, 0, 0)) * math.cos(a) + side * math.sin(a)
            at = ruff_c + out * rad - AXIS * 0.06 * row
            clay.append(tuft(at, out - AXIS * back + Vector((0, 0, 0.1 * math.sin(k * 1.7))), length=0.15 + 0.04 * math.sin(k * 2.1 + row), r=0.065))
    for k in range(5):                                                         # a soft crest on the head
        a = math.radians(-50 + 25 * k)
        d = Vector((math.sin(a) * 0.6, 0.35, 1.0))
        clay.append(tuft(H + Vector((0.2 * math.sin(a), 0.06, 0.28)), d, length=0.16, r=0.07))
    for s in (-1, 1):                                                          # cheek fluff
        clay.append(tuft(H + Vector((0.3 * s, -0.04, -0.08)), (s, 0.2, -0.5), length=0.15, r=0.07))
    for k in range(7):                                                         # fluffy rings round the abdomen
        t = 0.12 + 0.11 * k
        p = kit._spline(abdomen, t * 3)
        r = 0.38 * (1 - 0.72 * t ** 1.4)
        for s in (-1, 1):
            clay.append(tuft(p + Vector((r * 0.9 * s, 0, 0)), (s, 0.3, -0.4), length=0.1, r=0.05))
    skin = fuse(join(clay), voxel=0.022, iterations=3)
    tree = BVHTree.FromBMesh(skin)

    def hit(origin, direction=(0, 1, 0)):
        loc, nrm, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
        return loc, nrm
    eyes = [hit(H + Vector((0.16 * s, -2, 0.04))) for s in (-1, 1)]
    smile = [hit(H + Vector((x, -2, -0.15 + 0.8 * x * x)))[0] for x in (-0.07, -0.035, 0.0, 0.035, 0.07)]

    def carve(co, n):
        d = n * 0.02 * noise.noise(Vector((co.x * 11, co.y * 11, co.z * 3)))
        for e, en in eyes:
            d -= en * 0.05 * (1 - smooth((co - e).length, 0.1, 0.17))
        if co.y < H.y - 0.2:
            d -= n * 0.015 * (1 - smooth(poly_dist(co, smile), 0.006, 0.02))
        return d
    sculpt(skin, carve)
    skin = decimate(skin, 3900, keep=lambda co: 0.7 * (1 - smooth((Vector(co) - FACE).length, 0.2, 0.45)), factor=1.0)

    def fur_colour(co, n, g=0.0):
        dh = (co - H).length
        col = mix(COL["head"], COL["head_lt"], 0.5 * smooth(n.z, 0.2, 1.0))
        rd = (co - ruff_c).length
        col = mix(col, COL["ruff"], smooth(rd, 0.62, 0.42) * smooth(dh, 0.3, 0.42))
        tpos = (co - abdomen[0]).dot((abdomen[-1] - abdomen[0]).normalized())
        if co.z < T.z - 0.3:
            bands = 0.5 + 0.5 * math.sin(tpos * 18.0)
            ab = mix(COL["band"], COL["band_lt"], smooth(bands, 0.55, 0.85))
            col = mix(col, ab, smooth(co.z, T.z - 0.3, T.z - 0.5))
        col = mix(col, COL["mouth"], 1 - smooth(poly_dist(co, smile), 0.006, 0.016)) if co.y < H.y - 0.2 else col
        return col
    add("skin", skin, fur_m, fur_colour)

    # ---- eyes ------------------------------------------------------------------------------------------
    for (e, en), s in zip(eyes, (-1, 1)):
        add("eyes", facing(ell((0, 0, 0), (0.14, 0.15, 0.09), cuts=3), e - en * 0.02, en), eye_m)
        add("glints", ell(e + en * 0.07 + Vector((-0.045, 0, 0.055)), (0.032, 0.022, 0.032), cuts=1), fur_m, COL["white"])
        add("glints", ell(e + en * 0.07 + Vector((0.04, 0, -0.045)), (0.014, 0.01, 0.014), cuts=1), fur_m, COL["white"])

    # ---- feathery antennae -------------------------------------------------------------------------------
    for s in (-1, 1):
        shaft = [H + Vector((0.11 * s, -0.12, 0.3)), H + Vector((0.2 * s, -0.25, 0.62)), H + Vector((0.38 * s, -0.3, 0.92)), H + Vector((0.58 * s, -0.26, 1.08))]
        add("antennae", loft(shaft, lambda t: lerp(0.03, 0.014, t), segs=6, rings=14), fur_m, COL["ant_dk"])
        nb = 20
        for k in range(nb):
            t = 0.12 + 0.84 * k / (nb - 1)
            p = kit._spline(shaft, t * 3)
            tan = (kit._spline(shaft, min(t * 3 + 0.05, 3)) - kit._spline(shaft, max(t * 3 - 0.05, 0))).normalized()
            sd = tan.cross(Vector((0, -1, 0))).normalized()
            ln = 0.17 * math.sin(math.pi * min(max((t - 0.05) / 0.95, 0), 1)) ** 0.6 + 0.025
            for side_ in (-1, 1):
                b = loft([p, p + (sd * side_ * 0.7 + tan * 0.7).normalized() * ln], lambda q: lerp(0.01, 0.005, q), segs=3, rings=1)
                add("antennae", b, fur_m, COL["ant"])

    # ---- legs, tucked under -------------------------------------------------------------------------------
    for s in (-1, 1):
        for k in range(3):
            root = T + Vector((0.14 * s, -0.26 + 0.14 * k, -0.22 - 0.08 * k))
            knee = root + Vector((0.2 * s, -0.12 + 0.05 * k, -0.06))
            foot = knee + Vector((0.04 * s, -0.08 + 0.06 * k, -0.2))
            add("legs", loft([root, knee, foot], lambda t: lerp(0.05, 0.03, t), segs=6, rings=6), fur_m,
                lambda co, n, g: mix(COL["head_lt"], COL["leg"], smooth(g, 0.4, 0.9)))

    # ---- wings ---------------------------------------------------------------------------------------------
    for s in (-1, 1):
        th = math.radians(42)
        sweep = M(rot=(0, 0, -16 * s)).to_3x3()
        span = sweep @ Vector((s * math.cos(th), 0, math.sin(th)))
        chord = sweep @ Vector((s * math.sin(th), 0.0, -math.cos(th)))
        fw = wing(T + Vector((0.22 * s, 0.12, 0.18)), span, chord, 1.95, fore_w)
        add("wings", fw, fore_m)
        th2 = math.radians(-12)
        span2 = sweep @ Vector((s * math.cos(th2), 0.05, math.sin(th2)))
        chord2 = sweep @ Vector((s * math.sin(th2), 0.05, -math.cos(th2)))
        hw = wing(T + Vector((0.2 * s, 0.16, -0.12)), span2, chord2, 1.3, hind_w, nu=11, nv=7)
        add("wings", hw, hind_m)

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
