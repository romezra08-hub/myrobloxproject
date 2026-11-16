"""Stud Bear 2 (work in progress, round N). See the final studbear2.py for the method and history."""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import kit  # noqa: E402  (first: it brings in bpy)
import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

NAME = "StudBear2"
TEX = "studbear2"
SCRATCH = "/tmp/claude-0/-home-user-myrobloxproject/3ebc3f98-354b-587c-92e5-e4969ab0e7cc/scratchpad"
REF = os.path.join(SCRATCH, "sae", "ingame.jpg")
BEFORE = os.path.join(HERE, "..", "..", "preview", "studbear.png")

TARGET_HEIGHT = 3.0
BEVEL = 0.012
BEVEL_ANGLE = 20.0
REGION_ANGLE = 30.0       # faces this close in angle share one stud grid
UV_ANGLE = 66.0
SUPERSAMPLE = 2
STUD_PITCH = 0.042        # studs (after scaling)
STUD_R = 0.0135
STUD_H = 0.010
STUD_LIGHT = 0.25
STUD_LIFT = 0.12
STUD_DARK = 0.6
STUD_TOP = 0.04
STUD_RING = 0.38
EDGE_W = 0.010
EDGE_LIGHT = 0.10
EDGE_MIN_ANGLE = 32.0
STUD_MARGIN = 0.55
AO_SAMPLES = 32
AO_DARK = 0.45
FACET_JITTER = 0.035


def to_object(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def hull_bm(pts):
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def claw(base, fwd, w=0.07, h=0.06, L=0.13):
    """A chunky hooked claw wedge pointing forward and down from a toe."""
    fwd = Vector(fwd).normalized()
    side = fwd.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    b = Vector(base)
    tip = b + fwd * L - up * h * 0.9
    pts = [b + side * w / 2 + up * h / 2, b - side * w / 2 + up * h / 2, b + side * w / 2 - up * h / 2,
           b - side * w / 2 - up * h / 2, b - fwd * 0.08 + up * h * 0.3, tip + side * w * 0.12, tip - side * w * 0.12]
    return hull_bm(pts)



class Ray:
    def __init__(self, bm):
        bm.verts.index_update()
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, d):
        loc, nrm, idx, dist = self.bvh.ray_cast(Vector(origin), Vector(d).normalized(), 20.0)
        return loc, nrm



def crystal(glow, base, axis, r, h, seed):
    """A chunky six-sided ore crystal with a pointed, slightly off-centre tip, its root sunk into the body."""
    axis = Vector(axis).normalized()
    t = axis.cross(Vector((0.3, 0.7, 0.1))).normalized()
    b2 = axis.cross(t)
    pts = []
    rot0 = seed * 1.7
    for k in range(6):
        a = rot0 + k * math.pi / 3
        dirv = t * math.cos(a) + b2 * math.sin(a)
        pts.append(Vector(base) - axis * 0.12 + dirv * r * 0.92)
        pts.append(Vector(base) + axis * h * 0.68 + dirv * r)
    tip = Vector(base) + axis * h + t * r * 0.15 * math.sin(seed * 3.1)
    pts.append(tip)
    hb = hull_bm(pts)
    m = {v: glow.verts.new(v.co) for v in hb.verts}
    for f in hb.faces:
        glow.faces.new([m[v] for v in f.verts])
    hb.free()

def build_gems(glow, ray):
    """A flat glowing diamond set into each gem-carrying plate."""
    for gem in GEMS:
        cen, nrm = gem[0], gem[1]
        up = gem[2] if len(gem) > 2 else Vector((0, 0, 1))
        h, w = gem[3] if len(gem) > 3 else (0.13, 0.085)
        loc, n2 = ray.hit(cen + nrm * 0.4, -nrm)
        if loc is None:
            continue
        t = (up - n2 * n2.dot(up)).normalized()
        sdir = n2.cross(t)
        pts = [loc + t * h, loc - t * h, loc + sdir * w, loc - sdir * w,
               loc + n2 * 0.035 + t * h * 0.35, loc + n2 * 0.035 - t * h * 0.35,
               loc + n2 * 0.035 + sdir * w * 0.35, loc + n2 * 0.035 - sdir * w * 0.35, loc - n2 * 0.03]
        hb = hull_bm(pts)
        m = {v: glow.verts.new(v.co) for v in hb.verts}
        for f in hb.faces:
            glow.faces.new([m[v] for v in f.verts])
        hb.free()


def build_crystals(glow, ray):
    for (cx, cy, cz), lean, parts in CLUSTERS:
        loc, nrm = ray.hit((cx, cy, cz + 2.0), (0, 0, -1))
        if loc is None:
            continue
        ax = (Vector(lean).normalized() + nrm).normalized()
        t = ax.cross(Vector((0, 1, 0))).normalized()
        b2 = ax.cross(t)
        for i, (du, dv, r, h, tilt) in enumerate(parts):
            p0 = Vector((cx, cy, cz)) + t * du + b2 * dv
            l2, n2 = ray.hit(p0 + Vector((0, 0, 2.0)), (0, 0, -1))
            if l2 is None:
                continue
            a = (ax + (t * du + b2 * dv).normalized() * tilt).normalized() if (du or dv) else ax
            crystal(glow, l2, a, r, h, i + cx)



# ---- palette and labels ---------------------------------------------------------------------------------

LABELS = ["body", "cream", "mask", "armour", "paw", "nose", "mouth", "claw", "socket", "toe", "inner"]
COLOURS = {"body": "#9B4818", "cream": "#F4E6C6", "inner": "#E6C79A", "mask": "#2A2523", "armour": "#34353C", "paw": "#2D2A2A", "toe": "#4C4E57",
           "nose": "#1E1A19", "mouth": "#3A1A16", "claw": "#EFE3C8", "socket": "#1C1B1E"}
ROUGH = {"body": 0.78, "cream": 0.72, "inner": 0.75, "mask": 0.7, "armour": 0.45, "paw": 0.6, "toe": 0.5, "nose": 0.3, "mouth": 0.85,
         "claw": 0.45, "socket": 0.6}
NO_STUDS = {"nose", "mouth", "claw", "socket"}
TEAL = "#2EF2E2"


def L(name):
    return LABELS.index(name)


# ---- building blocks: every part is a designed low-poly solid -------------------------------------------

def loft(rings, label):
    """A closed solid through a list of rings (each a list of points, all the same count), capped flat."""
    bm = bmesh.new()
    vs = [[bm.verts.new(Vector(p)) for p in r] for r in rings]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for k in range(n):
            bm.faces.new((vs[i][k], vs[i][(k + 1) % n], vs[i + 1][(k + 1) % n], vs[i + 1][k]))
    bm.faces.new(vs[0])
    bm.faces.new(list(reversed(vs[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.material_index = L(label)
    return bm


def hull(points, label, sym=False):
    pts = [Vector(p) for p in points]
    if sym:
        pts += [Vector((-p.x, p.y, p.z)) for p in pts if abs(p.x) > 1e-6]
    bm = hull_bm(pts)
    for f in bm.faces:
        f.material_index = L(label)
    return bm


def oct_xz(y, wt, w, wb, zt, zu, zl, zb, cx=0.0):
    """A chamfered cross-section in the x-z plane at depth y: flat top, upper chamfers, flat sides, lower
    chamfers, flat bottom."""
    pts = [(wt, zt), (w, zu), (w, zl), (wb, zb), (-wb, zb), (-w, zl), (-w, zu), (-wt, zt)]
    return [Vector((cx + x, y, z)) for x, z in pts]


def ring_xz(y, half, cx=0.0):
    """A cross-section in the x-z plane at depth y from its right half (x > 0, top to bottom), mirrored."""
    pts = list(half) + [(-x, z) for x, z in reversed(half)]
    return [Vector((cx + x, y, z)) for x, z in pts]


def ring_axis(c, axis, a, b, ch):
    """A chamfered rectangle (half sizes a across, b front-back, chamfer ch) perpendicular to `axis`."""
    w = Vector(axis).normalized()
    side = Vector((1, 0, 0))
    u = (side - w * side.dot(w)).normalized()
    v = w.cross(u)
    if v.y > 0:
        v = -v
    c = Vector(c)
    prof = [(a - ch, b), (a, b - ch), (a, -b + ch), (a - ch, -b), (-a + ch, -b), (-a, -b + ch), (-a, b - ch),
            (-a + ch, b)]
    return [c + u * x + v * y for x, y in prof]


def seg(p0, p1, s0, s1, ch, label):
    """A leg block from p0 to p1, half sizes s0 at p0 and s1 at p1."""
    ax = Vector(p1) - Vector(p0)
    return loft([ring_axis(p0, ax, s0[0], s0[1], ch), ring_axis(p1, ax, s1[0], s1[1], ch)], label)


def block(c, h, base, top, ch, top_shift=(0, 0), label="paw"):
    """A paw block on the ground: rectangle `base` (half x, half y) at z=0, smaller `top` at z=h."""
    r0 = ring_axis((c[0], c[1], 0.0), (0, 0, 1), base[0], base[1], ch)
    r1 = ring_axis((c[0] + top_shift[0], c[1] + top_shift[1], h), (0, 0, 1), top[0], top[1], ch * 0.85)
    return loft([r0, r1], label)


def mirror_bm(bm):
    out = bm.copy()
    for v in out.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(out, faces=out.faces[:])
    return out


def _behind(p, planes, eps=1e-6):
    return all((p - Vector(c)).dot(Vector(n)) <= eps for c, n in planes)


def _in_box(p, box):
    lo, hi = box
    return all(lo[i] <= p[i] <= hi[i] for i in range(3))


def paint(bm, label, planes, box=((-9, -9, -9), (9, 9, 9)), only=None):
    """Cut the outline of a colour region into a part with planes (crisp straight edges) and label the faces
    inside it."""
    for c, n in planes:
        faces = [f for f in bm.faces if any(_in_box(v.co, box) for v in f.verts)]
        if not faces:
            continue
        geom = list(set(v for f in faces for v in f.verts)) + list(set(e for f in faces for e in f.edges)) + faces
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=Vector(c), plane_no=Vector(n).normalized())
    for f in bm.faces:
        p = f.calc_center_median()
        if _in_box(p, box) and _behind(p, planes) and (only is None or f.material_index in [L(o) for o in only]):
            f.material_index = L(label)


def paint_sym(bm, label, planes, box, only=None):
    """paint() on the right side and its mirror on the left."""
    paint(bm, label, planes, box, only)
    pl = [((-c[0], c[1], c[2]), (-n[0], n[1], n[2])) for c, n in planes]
    (lx, ly, lz), (hx, hy, hz) = box
    paint(bm, label, pl, ((-hx, ly, lz), (-lx, hy, hz)), only)


# ---- the bear ------------------------------------------------------------------------------------------

HEAD_PIVOT = Vector((0.0, -1.0, 2.05))
HEAD_YAW = -18.0      # towards -X, the hero camera
HEAD_PITCH = -4.0     # nose up a little
HEAD_ROLL = 3.0
HEAD_SCALE = 1.14
PAW_STEP = 0.20       # the left front leg a step forward
HIND_STEP = 0.10      # and the right hind leg a step back: a walking stance
HEAD_SHIFT = Vector((0.0, -0.08, -0.07))   # head a little forward and lower
LEG_SQUASH = 0.2      # everything below LEG_Z0 squashed this much: short, chunky legs
LEG_Z0 = 1.0
Y_SCALE = 0.96       # a touch shorter overall, to keep the length within 4 studs


def head_matrix():
    R = (Matrix.Rotation(math.radians(HEAD_YAW), 4, 'Z') @ Matrix.Rotation(math.radians(HEAD_ROLL), 4, 'Y')
         @ Matrix.Rotation(math.radians(HEAD_PITCH), 4, 'X') @ Matrix.Scale(HEAD_SCALE, 4))
    return Matrix.Translation(HEAD_PIVOT + HEAD_SHIFT) @ R @ Matrix.Translation(-HEAD_PIVOT)


def torso():
    """Deep brisket and shoulder hump, a tucked waist, a rounded rump: 10-sided sections."""
    t = loft([ring_xz(-1.22, [(0.26, 1.92), (0.46, 1.80), (0.56, 1.50), (0.46, 1.05), (0.24, 0.86)]),
              ring_xz(-0.95, [(0.40, 2.22), (0.70, 2.04), (0.86, 1.62), (0.74, 1.00), (0.36, 0.74)]),
              ring_xz(-0.50, [(0.42, 2.36), (0.74, 2.12), (0.86, 1.66), (0.76, 1.04), (0.40, 0.80)]),
              ring_xz(0.05, [(0.42, 2.14), (0.72, 1.98), (0.80, 1.62), (0.70, 1.08), (0.40, 0.88)]),
              ring_xz(0.50, [(0.38, 1.98), (0.64, 1.86), (0.70, 1.56), (0.62, 1.12), (0.36, 0.98)]),
              ring_xz(0.92, [(0.40, 1.96), (0.66, 1.84), (0.74, 1.52), (0.64, 1.10), (0.36, 0.98)]),
              ring_xz(1.16, [(0.34, 1.90), (0.58, 1.78), (0.65, 1.50), (0.56, 1.12), (0.32, 1.02)]),
              ring_xz(1.30, [(0.20, 1.76), (0.36, 1.68), (0.42, 1.46), (0.36, 1.18), (0.18, 1.10)])], "body")
    # graphic back stripes: wedges that lean back and taper down the flank
    for a, b in ((-0.10, 0.10), (0.36, 0.54), (0.80, 0.94)):
        paint(t, "mask", [((0, a, 2.2), (0, -1, -0.30)), ((0, b, 2.2), (0, 1, -0.12))],
              ((-2, -1.5, 1.30), (2, 2, 3)))
    # cream chest chevron
    paint_sym(t, "cream", [((0, 0, 0.92), (1.5, 0, -1)), ((0, 0, 1.80), (0, 0, 1)), ((0, 0, 0), (-1, 0, 0))],
              ((0, -2, 0), (2, -0.9, 3)))
    return t


def tail():
    return loft([ring_axis((0, 1.18, 1.56), (0, 1, 0.7), 0.19, 0.17, 0.06),
                 ring_axis((0, 1.40, 1.74), (0, 1, 0.7), 0.17, 0.15, 0.05),
                 ring_axis((0, 1.50, 1.84), (0, 1, 0.7), 0.10, 0.09, 0.03)], "body")


def claw_part(base, fwd, w, L_):
    b = claw(base, fwd, w=w, h=w * 0.85, L=L_)
    for f in b.faces:
        f.material_index = L("claw")
    return b


def toes_and_claws(cx, cy, xs, size, h, claw_w, claw_l):
    """Chunky toe blocks in a row, each with a top that slopes down to the front, and a cream claw."""
    out = []
    for dx in xs:
        r0 = ring_axis((cx + dx, cy, 0.0), (0, 0, 1), size[0], size[1], 0.035)
        r1 = ring_axis((cx + dx, cy + size[1] * 0.25, h), (0, 0, 1), size[0] * 0.86, size[1] * 0.70, 0.03)
        # slope the top: its front edge lower than its back
        for p in r1:
            p.z -= max(0.0, (cy + size[1] * 0.25) - p.y) * 0.9
        out.append(loft([r0, r1], "toe"))
        out.append(claw_part((cx + dx, cy - size[1] + 0.03, 0.08), (dx * 0.5, -1, 0), claw_w, claw_l))
    return out


def front_leg():
    """Right front leg: upper arm, armoured forearm, big paw with three toes and cream claws."""
    p = []
    p.append(seg((0.62, -0.70, 1.55), (0.68, -0.82, 0.90), (0.30, 0.28), (0.29, 0.29), 0.12, "body"))
    ua0, ua1 = Vector((0.62, -0.70, 1.55)), Vector((0.68, -0.82, 0.90))
    c = ua0 + (ua1 - ua0) * 0.80                 # a narrow elbow band
    h = (ua1 - ua0).normalized() * 0.04
    p.append(seg(c - h, c + h, (0.325, 0.315), (0.325, 0.315), 0.12, "armour"))
    top, bot = Vector((0.68, -0.86, 0.95)), Vector((0.72, -0.96, 0.16))
    p.append(seg(top, bot, (0.29, 0.31), (0.27, 0.30), 0.08, "body"))
    ax = bot - top
    for t in (0.30, 0.58):                       # segmented armour bands round the forearm
        c = top + ax * t
        h = ax.normalized() * 0.055
        p.append(seg(c - h, c + h, (0.33, 0.35), (0.33, 0.35), 0.10, "armour"))
    p.append(block((0.72, -1.00), 0.23, (0.34, 0.42), (0.30, 0.35), 0.09, (0, 0.05)))
    p += toes_and_claws(0.72, -1.36, (-0.215, 0.0, 0.215), (0.115, 0.17), 0.26, 0.075, 0.13)
    return p


def hind_leg():
    p = []
    hh = loft([oct_xz(0.40, 0.16, 0.24, 0.16, 1.58, 1.45, 0.95, 0.85, 0.56),
               oct_xz(0.82, 0.22, 0.32, 0.22, 1.74, 1.55, 0.85, 0.70, 0.56),
               oct_xz(1.22, 0.18, 0.26, 0.18, 1.62, 1.48, 0.95, 0.82, 0.56)], "body")
    for a, b in ((0.66, 0.80), (0.98, 1.10)):      # two stripes across the haunch, leaning back
        paint(hh, "mask", [((0, a, 1.6), (0, -1, -0.45)), ((0, b, 1.6), (0, 1, -0.25))], ((0.3, 0, 1.05), (2, 2, 3)))
    p.append(hh)
    top, bot = Vector((0.60, 0.92, 0.90)), Vector((0.62, 0.86, 0.16))
    p.append(seg(top, bot, (0.26, 0.28), (0.25, 0.27), 0.08, "body"))
    c = top + (bot - top) * 0.5
    h = (bot - top).normalized() * 0.055
    p.append(seg(c - h, c + h, (0.30, 0.32), (0.30, 0.32), 0.09, "armour"))
    p.append(block((0.62, 0.78), 0.20, (0.28, 0.34), (0.25, 0.29), 0.08, (0, 0.03)))
    p += toes_and_claws(0.62, 0.48, (-0.18, 0.0, 0.18), (0.10, 0.14), 0.22, 0.065, 0.11)
    return p


def _shell(outer, inner, y0, y1, label="armour", k=0.88):
    prof = outer + inner
    cx = sum(x for x, z in prof) / len(prof)
    cz = sum(z for x, z in prof) / len(prof)

    def ring(y, kk):
        return [Vector((cx + (x - cx) * kk, y, cz + (z - cz) * kk)) for x, z in prof]
    return loft([ring(y0 - 0.06, k), ring(y0, 1.0), ring(y1, 1.0), ring(y1 + 0.06, k)], label)


def pauldron():
    """Shoulder armour over the shoulder joint: a curved plate of even thickness whose lower edge comes to a
    point, so from the side it is a shield, not a slab."""
    def prof(zb):
        return [(0.70, 2.04), (0.93, 1.92), (1.05, 1.70), (1.08, zb), (0.96, zb), (0.92, 1.64), (0.80, 1.78),
                (0.64, 1.88)]

    def ring(y, zb, k=1.0):
        pr = prof(zb)
        cx = sum(x for x, z in pr) / len(pr)
        cz = sum(z for x, z in pr) / len(pr)
        return [Vector((cx + (x - cx) * k, y, cz + (z - cz) * k)) for x, z in pr]
    return [loft([ring(-1.10, 1.62, 0.9), ring(-1.04, 1.56), ring(-0.80, 1.22), ring(-0.54, 1.56),
                  ring(-0.48, 1.62, 0.9)], "armour")]


# calm, confident eye: a level top that rises a touch to the outer corner, a fuller lower edge
EYE_SHAPE = [(-0.12, 0.0), (-0.07, 0.055), (0.07, 0.066), (0.13, 0.022), (0.08, -0.045), (-0.06, -0.05)]
EYE_SCALE = 1.1
EYE_AT = (0.34, 2.33)       # x, z of the right eye centre on the face
EYE_DEPTH = 0.05
FRAME_K = 1.45       # the dark frame: the eye shape enlarged,
FRAME_OUT = 0.05     # pulled out to the side
FRAME_UP = 0.025     # and up at the outer corner


def cranium():
    """Broad head, widest at the cheeks, a V-shaped face: 12-sided sections. A dark chevron on the forehead."""
    h = loft([ring_xz(-0.98, [(0.22, 2.52), (0.38, 2.46), (0.46, 2.24), (0.48, 2.04), (0.38, 1.88), (0.20, 1.82)]),
                 ring_xz(-1.26, [(0.32, 2.76), (0.54, 2.64), (0.64, 2.38), (0.70, 2.08), (0.58, 1.82), (0.30, 1.72)]),
                 ring_xz(-1.56, [(0.32, 2.74), (0.52, 2.62), (0.62, 2.40), (0.68, 2.08), (0.56, 1.80), (0.30, 1.72)]),
                 ring_xz(-1.76, [(0.26, 2.66), (0.44, 2.56), (0.54, 2.40), (0.58, 2.10), (0.48, 1.86), (0.28, 1.78)]),
                 ring_xz(-1.90, [(0.12, 2.58), (0.20, 2.52), (0.24, 2.42), (0.26, 2.12), (0.22, 1.94), (0.14, 1.88)])],
                "body")
    paint_chevron(h)
    return h


def paint_chevron(bm):
    """Forehead chevron: a dark V between two pairs of planes, its point down towards the nose."""
    paint_sym(bm, "mask", [((0.0, -1.5, 2.50), (-1, 0, 0.0)),
                           ((0.0, 0, 2.47), (0.95, 0, -1)), ((0.0, 0, 2.66), (-0.95, 0, 1)), ((0, -1.30, 0), (0, 1, 0))],
              ((0, -2.2, 2.3), (1, -1.2, 3)))


def head_parts():
    p = [cranium()]
    # brow shelf over the eyes, following the V of the face
    # forehead and brow as one bold facet: from the crown it slopes down to a crisp brow edge over the eyes
    brow = hull([(0.50, -1.72, 2.52), (0.52, -1.66, 2.43), (0.24, -1.98, 2.51), (0.24, -1.92, 2.425),
                 (0.0, -2.02, 2.52), (0.0, -1.97, 2.44), (0.30, -1.42, 2.752), (0.0, -1.42, 2.752),
                 (0.50, -1.44, 2.64)], "body", sym=True)
    paint_chevron(brow)
    p.append(brow)
    # jowls: faceted wedges at the lower sides of the face, pointing out and back
    for s_ in (1, -1):
        b = hull([(0.50, -1.64, 2.12), (0.70, -1.42, 2.13), (0.82, -1.20, 1.92), (0.68, -1.34, 1.76),
                  (0.46, -1.62, 1.86), (0.52, -1.28, 2.06), (0.50, -1.30, 1.80)], "body")
        p.append(b if s_ > 0 else mirror_bm(b))
    # boxy cream muzzle and a recessed cream jaw under it
    p.append(loft([oct_xz(-1.70, 0.26, 0.34, 0.28, 2.24, 2.16, 1.92, 1.84),
                   oct_xz(-2.18, 0.20, 0.27, 0.22, 2.16, 2.10, 1.97, 1.92)], "cream"))
    p.append(loft([oct_xz(-1.66, 0.20, 0.26, 0.18, 1.93, 1.88, 1.78, 1.72),
                   oct_xz(-2.10, 0.16, 0.20, 0.14, 1.93, 1.89, 1.80, 1.76)], "cream"))
    # wedge nose on top of the muzzle front
    p.append(hull([(0.12, -2.02, 2.23), (0.13, -2.21, 2.21), (0.0, -2.245, 2.06), (0.05, -2.06, 2.10),
                   (0.0, -2.10, 2.05), (0.0, -2.0, 2.24)], "nose", sym=True))
    # rounded ears with cream inner planes
    for s in (1, -1):
        c = Vector((0.44, -1.20, 2.82))
        n = Vector((0.25, -1, 0.12)).normalized()
        e = loft([ring_axis(c - n * 0.05, n, 0.20, 0.20, 0.085), ring_axis(c + n * 0.06, n, 0.20, 0.20, 0.085)], "body")
        i = loft([ring_axis(c, n, 0.11, 0.11, 0.045), ring_axis(c + n * 0.085, n, 0.105, 0.105, 0.045)], "inner")
        p += [e, i] if s > 0 else [mirror_bm(e), mirror_bm(i)]
    return p


def eye_frame(head):
    """Centre, view direction, outer-corner and up directions of the right eye, on the face plane."""
    ray = Ray(head)
    loc, n = ray.hit((EYE_AT[0], -3.0, EYE_AT[1]), (0, 1, 0))
    d = Vector(n).normalized()
    u = Vector((0, 0, 1)).cross(d).normalized()
    if u.x < 0:
        u = -u
    v = d.cross(u).normalized()
    if v.z < 0:
        v = -v
    return loc, d, u, v


def eye_cutter_and_glow(head):
    loc, d, u, v = eye_frame(head)
    poly = [loc + u * a * EYE_SCALE + v * b * EYE_SCALE for a, b in EYE_SHAPE]
    cut = loft([[p + d * 0.25 for p in poly], [p - d * EYE_DEPTH for p in poly]], "socket")
    # an angular dark frame round the eye, raised a little off the face, sweeping out and back
    # a dark wedge under and behind the eye (none above it: the brow sits there), pointing back to the ear
    fr2 = [(-0.15, -0.005), (-0.08, 0.035), (0.10, 0.06), (0.30, 0.075), (0.24, -0.02), (0.09, -0.085), (-0.07, -0.08)]
    fr = [loc + u * a * EYE_SCALE + v * b * EYE_SCALE for a, b in fr2]
    frame = loft([[p + d * 0.018 for p in fr], [p - d * 0.12 for p in fr]], "mask")
    # the glowing lens: a low faceted gem on the socket floor
    g = bmesh.new()
    k = 0.95
    lens = [loc + (p - loc) * k - d * (EYE_DEPTH - 0.008) for p in poly]
    back = [q - d * 0.04 for q in lens]
    cen = loc - d * (EYE_DEPTH - 0.022) + u * 0.005
    vl = [g.verts.new(q) for q in lens]
    vb = [g.verts.new(q) for q in back]
    vc = g.verts.new(cen)
    n = len(vl)
    for i in range(n):
        j = (i + 1) % n
        g.faces.new((vl[i], vl[j], vc))
        g.faces.new((vb[j], vb[i], vl[i], vl[j]))
    g.faces.new(list(reversed(vb)))
    bmesh.ops.recalc_face_normals(g, faces=g.faces[:])
    return cut, frame, g


def mouth_cutters():
    """A calm closed-mouth line: a level centre and corners that turn up a touch."""
    def slot(x0, z0, x1, z1):
        h = 0.028
        return hull([(x0, -2.40, z0 - h), (x0, -2.40, z0 + h), (x1, -2.40, z1 - h), (x1, -2.40, z1 + h),
                     (x0, -2.06, z0), (x1, -2.06, z1)], "mouth")
    return [slot(-0.075, 1.935, 0.075, 1.935), slot(0.07, 1.935, 0.15, 1.955), slot(-0.07, 1.935, -0.15, 1.955)]


CLUSTERS = [  # (centre on the spine, lean, [(offset u, offset v, radius, height, tilt)])
    ((0.0, -0.50, 2.3), (-0.3, 0.15, 1.0),
     [(0.0, 0.0, 0.17, 0.78, 0.0), (0.17, 0.08, 0.12, 0.52, 0.45), (-0.16, 0.06, 0.115, 0.48, -0.5),
      (0.03, -0.18, 0.095, 0.36, 0.35), (-0.04, 0.20, 0.08, 0.30, -0.2)]),
    ((0.0, 0.05, 2.1), (0.2, 0.3, 1.0),
     [(0.0, 0.0, 0.11, 0.42, 0.0), (0.12, -0.06, 0.08, 0.28, 0.5), (-0.10, 0.10, 0.075, 0.24, -0.45)]),
]
GEMS = []
HEAD_GEMS = []


def boolean(base_bm, others, op):
    """Exact boolean of `others` into `base_bm` (union or difference). Face labels ride on material indices."""
    mats = [bpy.data.materials.get("LAB_" + n) or bpy.data.materials.new("LAB_" + n) for n in LABELS]

    def mk(bm, name, link):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        link.objects.link(ob)
        return ob
    sc = bpy.context.scene
    base = mk(base_bm, "bool_base", sc.collection)
    coll = bpy.data.collections.new("bool_ops")
    sc.collection.children.link(coll)
    obs = [mk(b, "op%d" % i, coll) for i, b in enumerate(others)]
    mod = base.modifiers.new("B", 'BOOLEAN')
    mod.operation = op
    mod.operand_type = 'COLLECTION'
    mod.collection = coll
    mod.solver = 'EXACT'
    mod.material_mode = 'INDEX'
    select([base], base)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    out = bmesh.new()
    out.from_mesh(base.data)
    for ob in obs + [base]:
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    bpy.data.collections.remove(coll)
    return out


def build():
    """Designed parts, posed, joined into one solid; sockets and mouth cut; glow added; scaled; bevelled."""
    import time
    t0 = time.time()
    parts = [torso(), tail()]
    fl = front_leg()
    parts += fl
    for b in fl:
        m = mirror_bm(b)
        m.transform(Matrix.Translation((0, -PAW_STEP, 0)))
        parts.append(m)
    hl = hind_leg()
    parts += [mirror_bm(b) for b in hl]
    for b in hl:
        b.transform(Matrix.Translation((0, HIND_STEP, 0)))
    parts += hl
    for pa in pauldron():
        parts += [pa, mirror_bm(pa)]
    hp = head_parts()
    cut_r, frame_r, glow_r = eye_cutter_and_glow(hp[0])
    hp += [frame_r, mirror_bm(frame_r)]
    cutters_h = [cut_r, mirror_bm(cut_r)] + mouth_cutters()
    glow = bmesh.new()
    for g in (glow_r, mirror_bm(glow_r)):
        g.verts.index_update()
        m = {v: glow.verts.new(v.co) for v in g.verts}
        for f in g.faces:
            glow.faces.new([m[v] for v in f.verts])
    M = head_matrix()
    for b in hp + cutters_h:
        b.transform(M)
    fg = Vector((0.0, -1.66, 2.73))
    HEAD_GEMS[:] = [(M @ fg, (M.to_3x3() @ Vector((0, -0.45, 1))).normalized(), M.to_3x3() @ Vector((0, 1, 0)),
                     (0.10, 0.065))]
    glow.transform(M)
    parts += hp
    base = parts[0]
    body = boolean(base, parts[1:], 'UNION')
    body = boolean(body, cutters_h, 'DIFFERENCE')
    print("joined: %d faces (%.1fs)" % (len(body.faces), time.time() - t0))
    bmesh.ops.dissolve_limit(body, angle_limit=math.radians(0.5), use_dissolve_boundaries=False,
                             verts=body.verts[:], edges=body.edges[:], delimit={'MATERIAL'})
    bmesh.ops.remove_doubles(body, verts=body.verts[:], dist=1e-5)
    for b in (body, glow):
        for v in b.verts:
            v.co.z -= LEG_SQUASH * min(v.co.z, LEG_Z0)
    ray = Ray(body)
    build_crystals(glow, ray)
    GEMS[:] = [(Vector((1.06, -0.78, 1.55)), Vector((1, 0, 0.15))), (Vector((-1.06, -0.78, 1.55)), Vector((-1, 0, 0.15)))]
    for sx, dy in ((1, 0.0), (-1, -PAW_STEP)):     # a small glowing diamond on the front of each upper forearm band
        GEMS.append((Vector((0.69 * sx, -1.0 + dy, 0.575)), Vector((0, -1, 0)), Vector((0, 0, 1)), (0.075, 0.06)))
    GEMS.extend(HEAD_GEMS)
    build_gems(glow, ray)
    k = TARGET_HEIGHT / max(v.co.z for v in body.verts)     # the body (ears) sets the height; crystals may rise a little above
    for b in (body, glow):
        b.transform(Matrix.Diagonal((k, k * Y_SCALE, k, 1.0)))
        b.normal_update()
    bmesh.ops.triangulate(body, faces=[f for f in body.faces if len(f.verts) > 4], quad_method='BEAUTY', ngon_method='BEAUTY')
    if BEVEL > 0:
        bmesh.ops.dissolve_degenerate(body, dist=1e-5, edges=body.edges[:])
        body.normal_update()
        bad = set(v for e in body.edges if len(e.link_faces) != 2 for v in e.verts)
        bad |= set(v for v in body.verts if not v.is_manifold)
        claw_i = L("claw")
        edges = [e for e in body.edges if len(e.link_faces) == 2 and e.calc_length() > BEVEL * 2.5
                 and not any(v in bad for v in e.verts)
                 and all(f.material_index != claw_i and f.calc_area() > 1e-6 for f in e.link_faces)
                 and math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)) > BEVEL_ANGLE]
        bmesh.ops.bevel(body, geom=edges, offset=BEVEL, offset_type='OFFSET', segments=1, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(body, faces=body.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    lab = body.faces.layers.int.new("lab")
    for f in body.faces:
        f[lab] = f.material_index
        f.material_index = 0
    body.normal_update()
    return body, glow, k


# ---- texture: regions, analytic studs, bake ---------------------------------------------------------------

def stud_regions(bm, angle=REGION_ANGLE):
    """Neighbouring faces of one label within `angle` of the group's largest face share one stud grid."""
    lab = bm.faces.layers.int["lab"]
    cosmax = math.cos(math.radians(angle))
    order = sorted(bm.faces, key=lambda f: -f.calc_area())
    rid = {}
    regions = []
    for seed in order:
        if seed in rid:
            continue
        n0 = seed.normal.copy()
        reg = [seed]
        rid[seed] = len(regions)
        stack = [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in rid or g[lab] != seed[lab] or g.normal.dot(n0) < cosmax:
                        continue
                    rid[g] = len(regions)
                    reg.append(g)
                    stack.append(g)
        regions.append(reg)
    return regions, rid


def region_frames(bm, regions, rid):
    """For each region: its plane frame (U across, V up, N out) and its outline as 2D segments, each marked
    convex (a ridge, gets a highlight) or not."""
    lab = bm.faces.layers.int["lab"]
    out = []
    for i, reg in enumerate(regions):
        area = sum(f.calc_area() for f in reg)
        n = sum((f.normal * f.calc_area() for f in reg), Vector())
        n = n.normalized() if n.length > 0 else reg[0].normal.copy()
        c = sum((f.calc_center_median() * f.calc_area() for f in reg), Vector()) / max(area, 1e-9)
        v = Vector((0, 0, 1)) - n * n.z
        if v.length < 0.3:
            v = Vector((0, -1, 0)) - n * (-n.y)
        v.normalize()
        u = v.cross(n).normalized()
        segs, convex = [], []
        rs = set(reg)
        for f in reg:
            for e in f.edges:
                others = [g for g in e.link_faces if g is not f]
                if others and all(g in rs for g in others):
                    continue
                a, b = e.verts[0].co - c, e.verts[1].co - c
                segs.append((a.dot(u), a.dot(v), b.dot(u), b.dot(v)))
                cv = 0.0
                if others:
                    g = others[0]
                    # a ridge: the neighbour falls away behind this face's plane, by a real angle
                    d = (g.calc_center_median() - f.calc_center_median()).dot(f.normal)
                    ang = math.degrees(f.normal.angle(g.normal, 0.0))
                    if d < -1e-4 and ang > EDGE_MIN_ANGLE:
                        cv = min(1.0, (ang - EDGE_MIN_ANGLE) / 25.0)
                convex.append(cv)
        name = LABELS[reg[0][lab]]
        studs = name not in NO_STUDS and area > STUD_PITCH ** 2 * 1.5 and n.z > -0.75
        out.append(dict(c=np.array(c[:]), u=np.array(u[:]), v=np.array(v[:]), n=np.array(n[:]),
                        segs=np.array(segs, np.float32).reshape(-1, 4), convex=np.array(convex, np.float32),
                        studs=studs, area=area))
    return out


def _seg_dist(px, py, S):
    """Distances from points (px, py) to every segment in S (k, 4): an (n, k) array."""
    ax, ay, bx, by = S[:, 0][None], S[:, 1][None], S[:, 2][None], S[:, 3][None]
    ex, ey = bx - ax, by - ay
    L2 = np.maximum(ex * ex + ey * ey, 1e-12)
    t = np.clip(((px[:, None] - ax) * ex + (py[:, None] - ay) * ey) / L2, 0, 1)
    dx, dy = ax + ex * t - px[:, None], ay + ey * t - py[:, None]
    return np.sqrt(dx * dx + dy * dy)


def stud_field(P, rid_px, frames, pitch, r, H):
    """Per texel: stud height gradient (in the region's U, V), a stud mask for the shading, the ring of shadow
    round each stud, and the distance to a convex facet edge."""
    n = len(P)
    gu = np.zeros(n, np.float32)
    gv = np.zeros(n, np.float32)
    top = np.zeros(n, np.float32)
    ringv = np.zeros(n, np.float32)
    shade = np.zeros(n, np.float32)
    edge = np.full(n, 9.0, np.float32)
    U = np.zeros((n, 3), np.float32)
    V = np.zeros((n, 3), np.float32)
    order = np.argsort(rid_px, kind='stable')
    rs = rid_px[order]
    cuts = np.flatnonzero(np.diff(rs)) + 1
    starts = np.concatenate([[0], cuts])
    ends = np.concatenate([cuts, [len(rs)]])
    L = np.array([-0.45, 0.89])          # light in the region frame: from above, a little from the left
    for s0, s1 in zip(starts, ends):
        k = rs[s0]
        if k < 0 or k >= len(frames):
            continue
        F = frames[k]
        idx = order[s0:s1]
        d = P[idx] - F["c"]
        q_u = d @ F["u"]
        q_v = d @ F["v"]
        U[idx] = F["u"]
        V[idx] = F["v"]
        S = F["segs"]
        if len(S):
            dist_e = _seg_dist(q_u, q_v, S)
            cv = F["convex"]
            if cv.any():
                # distance scaled up where the ridge is soft, so soft ridges get a thinner, fainter light
                edge[idx] = np.where(cv[None] > 0, dist_e / np.maximum(cv[None], 1e-3), 9.0).min(1)
        if not F["studs"]:
            continue
        # world-anchored phase so neighbouring regions with the same frame line up
        off_u = F["c"] @ F["u"]
        off_v = F["c"] @ F["v"]
        wu, wv = q_u + off_u, q_v + off_v
        cu = np.round(wu / pitch) * pitch
        cv_ = np.round(wv / pitch) * pitch
        du, dv = wu - cu, wv - cv_
        rad = np.sqrt(du * du + dv * dv)
        ok = np.ones(len(idx), bool)
        if len(S):
            ok = _seg_dist(cu - off_u, cv_ - off_v, S).min(1) > r * STUD_MARGIN
        # flat-topped stud with a rounded shoulder of width b
        b = r * 0.35
        t = np.clip((r - rad) / b, 0, 1)
        dh = np.where((t > 0) & (t < 1), 6 * t * (1 - t) / b, 0.0) * H        # d height / d(-rad)
        inv = 1.0 / np.maximum(rad, 1e-6)
        g_u = -dh * du * inv
        g_v = -dh * dv * inv
        gu[idx] = np.where(ok, g_u, 0)
        gv[idx] = np.where(ok, g_v, 0)
        top[idx] = np.where(ok, t * t * (3 - 2 * t), 0)
        # contact shadow: just outside the stud, stronger away from the light
        ring = np.clip(1 - (rad - r) / (r * 0.55), 0, 1) * (rad > r * 0.98)
        away = 0.5 - 0.5 * (du * L[0] + dv * L[1]) * inv
        ringv[idx] = np.where(ok, ring * (0.35 + 0.65 * away), 0)
        sl = (g_u * L[0] + g_v * L[1])       # slope towards the light
        shade[idx] = np.where(ok, -sl / max(H * 6 / b, 1e-6), 0)
    return gu, gv, top, ringv, shade, edge, U, V


def emit_material(name, kind):
    """An emission-only material that outputs a value to bake: position, normal, tangent, colour, roughness
    or the region id."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    for nd in list(t.nodes):
        t.nodes.remove(nd)
    out = t.nodes.new("ShaderNodeOutputMaterial")
    em = t.nodes.new("ShaderNodeEmission")
    t.links.new(em.outputs[0], out.inputs[0])

    def pack(sock, scale, offset):
        vm = t.nodes.new("ShaderNodeVectorMath")
        vm.operation = 'MULTIPLY_ADD'
        t.links.new(sock, vm.inputs[0])
        vm.inputs[1].default_value = (scale,) * 3
        vm.inputs[2].default_value = (offset,) * 3
        return vm.outputs[0]
    if kind in ("pos", "nrm"):
        g = t.nodes.new("ShaderNodeNewGeometry")
        sock = g.outputs["Position"] if kind == "pos" else g.outputs["True Normal"]
        t.links.new(pack(sock, 0.125 if kind == "pos" else 0.5, 0.5), em.inputs["Color"])
    elif kind == "tan":
        tg = t.nodes.new("ShaderNodeTangent")
        tg.direction_type = 'UV_MAP'
        t.links.new(pack(tg.outputs[0], 0.5, 0.5), em.inputs["Color"])
    else:
        names = {"col": ("cr", "cg", "cb"), "rough": ("rough",) * 3, "rid": ("rid_a", "rid_b", "rid_a")}[kind]
        comb = t.nodes.new("ShaderNodeCombineColor")
        for i, nm in enumerate(names):
            a = t.nodes.new("ShaderNodeAttribute")
            a.attribute_type, a.attribute_name = 'GEOMETRY', nm
            t.links.new(a.outputs["Fac"], comb.inputs[i])
        t.links.new(comb.outputs[0], em.inputs["Color"])
    return m


def glow_material():
    m = bpy.data.materials.new("GLOW_Crystal")
    b = kit.principled(m)
    rgb = kit.srgb(TEAL)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Emission Color"].default_value = (*rgb, 1)
    b.inputs["Emission Strength"].default_value = 2.5
    b.inputs["Roughness"].default_value = 0.2
    return m


def select(obs, active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def save_png(arr, path, srgb):
    from PIL import Image
    a = arr[..., :3]
    if srgb:
        a = to_srgb(a)
    a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]
    Image.fromarray(a, "RGB").save(path)


def box_blur(a, r):
    for axis in (0, 1):
        a = sum(np.roll(a, d, axis) for d in range(-r, r + 1)) / (2 * r + 1)
    return a


def face_attrs(ob, bm_regions, rid, frames):
    """Write per-face colour, roughness and region id attributes on the low mesh."""
    me = ob.data
    lab = [0] * len(me.polygons)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    ll = bm.faces.layers.int["lab"]
    labs = [f[ll] for f in bm.faces]
    bm.free()
    cols = np.zeros((len(me.polygons), 3), np.float32)
    rough = np.zeros(len(me.polygons), np.float32)
    rida = np.zeros(len(me.polygons), np.float32)
    ridb = np.zeros(len(me.polygons), np.float32)
    for i, li in enumerate(labs):
        name = LABELS[li]
        r = rid[i]
        c = np.array(kit.srgb(COLOURS[name]), np.float32)
        j = (math.sin(r * 12.9898) * 43758.5453) % 1.0
        c = c * (1.0 + FACET_JITTER * (j - 0.5) * 2)
        cols[i] = c
        rough[i] = ROUGH[name]
        rida[i] = (r % 64) / 63.0
        ridb[i] = (r // 64) / 63.0
    for nm, vals in (("cr", cols[:, 0]), ("cg", cols[:, 1]), ("cb", cols[:, 2]), ("rough", rough),
                     ("rid_a", rida), ("rid_b", ridb)):
        at = me.attributes.get(nm) or me.attributes.new(nm, 'FLOAT', 'FACE')
        at.data.foreach_set("value", vals)
    return labs


def bake(body, frames, rid_of_face, texture_dir):
    """Bake the body: per-texel position, normal, tangent, colour, roughness and region id come out of
    Blender; the studs, their shading, the edge light and the normal map are computed here per texel."""
    final = 512 if os.environ.get("PETS_FAST") else 1024
    size = final * SUPERSAMPLE
    margin = max(3, size // 160)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    world = sc.world or bpy.data.worlds.new("BakeWorld")
    sc.world = world
    mats = {k: emit_material("SB_Emit_" + k, k) for k in ("pos", "nrm", "tan", "col", "rough", "rid")}
    body.data.materials.clear()
    body.data.materials.append(mats["col"])

    def run(kind, mat, samples=1, fill=None, margin_px=None):
        body.data.materials[0] = mat
        img = bpy.data.images.new("bake_" + kind, size, size, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color'
        if fill is not None:
            img.pixels.foreach_set(np.tile(np.array([*fill, 1.0], dtype=np.float32), size * size))
        tree = mat.node_tree
        n = tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        tree.nodes.active = n
        select([body], body)
        sc.cycles.samples = samples
        bpy.ops.object.bake(type=kind if kind == "AO" else 'EMIT',
                            margin=margin if margin_px is None else margin_px, margin_type='EXTEND')
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        tree.nodes.remove(n)
        bpy.data.images.remove(img)
        return px.reshape(size, size, 4)[..., :3].copy()

    cov = run("cov", mats["col"], fill=(-1.0, -1.0, -1.0), margin_px=0)
    inside = (cov[..., 0] >= 0)
    pos = (run("pos", mats["pos"]) - 0.5) / 0.125
    nrm = run("nrm", mats["nrm"]) * 2 - 1
    tan = run("tan", mats["tan"]) * 2 - 1
    col = run("col", mats["col"])
    rough = run("rough", mats["rough"])[..., 0]
    ridc = run("rid", mats["rid"])
    world.light_settings.distance = 0.6
    ao = run("AO", mats["col"], samples=AO_SAMPLES)[..., 0]
    rid_px = (np.round(ridc[..., 0] * 63) + 64 * np.round(ridc[..., 1] * 63)).astype(np.int64)
    filled = (np.abs(pos).sum(-1) > 0)
    rid_px = np.where(filled, rid_px, -1)
    # ---- the studs, per texel
    H, W = rid_px.shape
    flat = rid_px.reshape(-1)
    P = pos.reshape(-1, 3)
    gu, gv, top, ring, shade, edge, U, V = stud_field(P, flat, frames, STUD_PITCH, STUD_R, STUD_H)
    N = nrm.reshape(-1, 3)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
    T = tan.reshape(-1, 3)
    T = T - N * (T * N).sum(1, keepdims=True)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-6)
    B = np.cross(N, T)
    n_w = N - gu[:, None] * U - gv[:, None] * V
    n_w /= np.maximum(np.linalg.norm(n_w, axis=1, keepdims=True), 1e-6)
    nt = np.stack([(n_w * T).sum(1), (n_w * B).sum(1), (n_w * N).sum(1)], 1)
    nt = np.where(np.isfinite(nt), nt, np.array([0, 0, 1.0]))
    # ---- colour
    c = col.reshape(-1, 3)
    out = c * (1.0 + STUD_LIGHT * np.clip(shade, 0, None)[:, None] * 4)
    out = out + (1.0 - out) * np.clip(shade, 0, None)[:, None] * STUD_LIFT * 4
    out = out * (1.0 + STUD_DARK * np.clip(shade, None, 0)[:, None] * 4)
    out = out * (1.0 + STUD_TOP * top[:, None])
    out = out * (1.0 - STUD_RING * ring[:, None])
    ew = EDGE_W
    hl = np.clip(1 - edge / ew, 0, 1)
    out = out + (1.0 - out) * (EDGE_LIGHT * hl)[:, None]
    a = np.clip(ao.reshape(-1), 0, 1)
    a = box_blur(a.reshape(H, W), 2 * SUPERSAMPLE).reshape(-1)
    out = out * (1.0 - AO_DARK * (1.0 - a))[:, None]
    out = out.reshape(H, W, 3)
    r = np.clip(rough.reshape(-1) - 0.12 * top + 0.15 * ring, 0, 1).reshape(H, W, 1)
    nt = nt.reshape(H, W, 3)
    os.makedirs(texture_dir, exist_ok=True)
    paths = {k: os.path.join(texture_dir, "%s_%s.png" % (TEX, k)) for k in ("colour", "rough", "normal")}
    k = SUPERSAMPLE

    def down(x):
        return x.reshape(final, k, final, k, x.shape[-1]).mean(axis=(1, 3))
    save_png(down(np.clip(out, 0, 1)), paths["colour"], True)
    save_png(np.repeat(down(r), 3, -1), paths["rough"], False)
    nn = down(nt)
    nn /= np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-6)
    save_png(nn * 0.5 + 0.5, paths["normal"], False)
    # ---- final material from the files on disk
    m = bpy.data.materials.new(NAME + "_Body")
    b = kit.principled(m)
    t = m.node_tree
    tc = t.nodes.new("ShaderNodeTexImage")
    tc.image = bpy.data.images.load(paths["colour"])
    t.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    tr = t.nodes.new("ShaderNodeTexImage")
    tr.image = bpy.data.images.load(paths["rough"])
    tr.image.colorspace_settings.name = 'Non-Color'
    t.links.new(tr.outputs["Color"], b.inputs["Roughness"])
    tn = t.nodes.new("ShaderNodeTexImage")
    tn.image = bpy.data.images.load(paths["normal"])
    tn.image.colorspace_settings.name = 'Non-Color'
    nm = t.nodes.new("ShaderNodeNormalMap")
    nm.space = 'TANGENT'
    t.links.new(tn.outputs["Color"], nm.inputs["Color"])
    t.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    body.data.materials.clear()
    body.data.materials.append(m)
    for nmx in ("cr", "cg", "cb", "rough", "rid_a", "rid_b", "lab"):
        if nmx in body.data.attributes:
            body.data.attributes.remove(body.data.attributes[nmx])
    return paths, (nm, b)


def make_objects(bm, glow):
    regions, rid = stud_regions(bm)
    frames = region_frames(bm, regions, rid)
    bm.faces.index_update()
    rid_of_face = [rid[f] for f in bm.faces]
    body = to_object(bm, NAME + "_Body")
    body.data.shade_flat()
    g = to_object(glow, NAME + "_GLOW")
    g.data.shade_flat()
    g.data.materials.append(glow_material())
    g.visible_diffuse = g.visible_glossy = False     # like Roblox Neon: it glows but lights nothing round it
    face_attrs(body, regions, rid_of_face, frames)
    select([body], body)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(UV_ANGLE), island_margin=0.003)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(shape_method='CONCAVE', rotate=True, rotate_method='ANY', margin_method='FRACTION',
                            margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    return body, g, frames, rid_of_face


def peek_material():
    m = bpy.data.materials.new("SB_Peek")
    b = kit.principled(m)
    t = m.node_tree
    comb = t.nodes.new("ShaderNodeCombineColor")
    for i, nm in enumerate(("cr", "cg", "cb")):
        a = t.nodes.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', nm
        t.links.new(a.outputs["Fac"], comb.inputs[i])
    t.links.new(comb.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    return m


# ---- review rig: sunny, game-like ---------------------------------------------------------------------

def _aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def _camera(name, loc, target, fov):
    data = bpy.data.cameras.new(name)
    data.angle = math.radians(fov)
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    _aim(ob, target)
    return ob


class SunRig:
    SKY = (0.56, 0.72, 0.95)
    SUN = Vector((0.42, 0.62, -0.66))

    def __init__(self, objs, head, samples=40):
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = 'CPU', samples, True
        sc.view_settings.view_transform = 'Standard'
        pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        self.lo, self.hi = lo, hi
        c = (lo + hi) / 2
        size = max(hi - lo)
        self.world = bpy.data.worlds.new("SunnyWorld")
        sc.world = self.world
        self.bg = next(n for n in self.world.node_tree.nodes if n.type == 'BACKGROUND')
        self.bg.inputs[0].default_value = (*self.SKY, 1)
        self.bg.inputs[1].default_value = 0.85
        g = kit.rounded_box((80, 80, 0.2), n=20, cuts=0)
        me = bpy.data.meshes.new("Ground")
        g.to_mesh(me)
        g.free()
        me.materials.append(kit.material("GroundLight", "#D3D0C8", rough=0.9))
        self.ground = bpy.data.objects.new("Ground", me)
        self.ground.location = (0, 0, lo.z - 0.1)
        sc.collection.objects.link(self.ground)
        d = bpy.data.objects.new("Dummy", bpy.data.meshes.new("Dummy"))
        db = kit.rounded_box((2, 1, 5), n=8, cuts=2)
        db.to_mesh(d.data)
        db.free()
        d.data.materials.append(kit.material("DummyBlue", "#5C7C99", rough=0.7))
        d.location = (hi.x + 2.0, c.y + 1.0, lo.z + 2.5)
        sc.collection.objects.link(d)
        self.dummy = d
        sun = bpy.data.lights.new("Sun", 'SUN')
        sun.energy, sun.angle, sun.color = 3.6, math.radians(3), (1.0, 0.97, 0.9)
        self.sun = bpy.data.objects.new("Sun", sun)
        self.sun.rotation_euler = self.SUN.to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(self.sun)
        fl = bpy.data.lights.new("SkyFill", 'AREA')
        fl.energy, fl.size, fl.color = 260.0, 6.0, (0.85, 0.92, 1.0)
        self.fill = bpy.data.objects.new("SkyFill", fl)
        self.fill.location = c + Vector((4.5, -3.5, 2.0))
        _aim(self.fill, c)
        sc.collection.objects.link(self.fill)
        dist = size * 2.25
        head = Vector(head)
        hump = Vector((0, -0.25, hi.z * 0.82))
        self.cams = {
            "front 3/4": _camera("C_front34", c + Vector((-0.55, -1.0, 0.3)).normalized() * dist, c, 34),
            "front": _camera("C_front", c + Vector((0, -1.0, 0.08)).normalized() * dist, c, 34),
            "side": _camera("C_side", c + Vector((-1.0, -0.02, 0.1)).normalized() * dist, c, 34),
            "back 3/4": _camera("C_back34", c + Vector((-0.6, 1.0, 0.4)).normalized() * dist, c, 34),
            "close-up": _camera("C_close", hump + Vector((-0.5, -0.6, 0.5)).normalized() * 3.4, hump, 30),
            "game distance": _camera("C_game", Vector((c.x - 2.5, c.y - 10, lo.z + 4.0)), c + Vector((1.2, 0, 0.3)), 70),
            "face 3/4": _camera("C_face", head + Vector((-0.6, -1.0, 0.15)).normalized() * 4.0, head, 30),
            "face front": _camera("C_facef", head + Vector((0, -1.0, 0.06)).normalized() * 4.0, head, 30),
            "face close": _camera("C_faceclose", head + Vector((-0.55, -1.0, 0.12)).normalized() * 3.3, head, 30),
            "hero": _camera("C_hero", c + Vector((-0.62, -1.0, 0.22)).normalized() * dist * 0.9, c + Vector((0, 0, 0.05)), 32),
        }
        self.clay = kit.material("Clay", "#B8B4AE", rough=0.6)
        self.black = bpy.data.materials.new("Black")
        b = kit.principled(self.black)
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Roughness"].default_value = 1.0

    def render(self, path, view, look="full", px=512, normal_link=None):
        sc, layer = bpy.context.scene, bpy.context.view_layer
        sc.camera = self.cams[view]
        sc.render.resolution_x = sc.render.resolution_y = px
        sc.render.filepath = path
        sil = look == "silhouette"
        layer.material_override = {"clay": self.clay, "silhouette": self.black}.get(look)
        self.ground.hide_render = sil
        self.dummy.hide_render = view != "game distance"
        self.bg.inputs[0].default_value = (1, 1, 1, 1) if sil else (*self.SKY, 1)
        self.sun.hide_render = self.fill.hide_render = sil
        cut = None
        if look == "studio" and normal_link:
            nm, b = normal_link
            for lk in list(b.inputs["Normal"].links):
                b.id_data.links.remove(lk)
            cut = (nm, b)
            self.bg.inputs[0].default_value = (0.5, 0.52, 0.56, 1)
            self.sun.rotation_euler = Vector((0.3, 0.35, -0.89)).to_track_quat('-Z', 'Y').to_euler()
            self.sun.data.energy = 3.0
            self.fill.hide_render = True
        bpy.ops.render.render(write_still=True)
        if cut:
            nm, b = cut
            b.id_data.links.new(nm.outputs["Normal"], b.inputs["Normal"])
            self.sun.rotation_euler = self.SUN.to_track_quat('-Z', 'Y').to_euler()
            self.sun.data.energy = 3.6
            self.fill.hide_render = False
        layer.material_override = None
        return path


def ref_tiles(px):
    from PIL import Image
    ref = Image.open(REF).convert("RGB")
    out = []
    for box, label in (((18, 95, 422, 540), "style reference: Steal an Egg (tiger)"),
                       ((458, 90, 862, 500), "style reference: Steal an Egg (wolf)")):
        crop = ref.crop(box)
        k = px / max(crop.size)
        crop = crop.resize((int(crop.size[0] * k), int(crop.size[1] * k)), Image.LANCZOS)
        tile = Image.new("RGB", (px, px), (18, 20, 24))
        tile.paste(crop, ((px - crop.size[0]) // 2, (px - crop.size[1]) // 2))
        out.append((tile, label))
    return out


def contact(out, tiles, px, cols, title=""):
    from PIL import Image, ImageDraw
    rows = (len(tiles) + cols - 1) // cols
    top = 28 if title else 0
    sheet = Image.new("RGB", (cols * px, rows * px + top), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((8, 7), title, fill=(235, 235, 235))
    for i, (img, label) in enumerate(tiles):
        x, y = (i % cols) * px, (i // cols) * px + top
        sheet.paste(img.resize((px, px)), (x, y))
        draw.rectangle((x, y, x + 8 + 6 * len(label), y + 16), fill=(0, 0, 0))
        draw.text((x + 4, y + 2), label, fill=(255, 255, 255))
    sheet.save(out)


SHOTS = [("hero", "full"), ("front", "full"), ("side", "full"), ("back 3/4", "full"),
         ("face close", "full"), ("face front", "full"), ("game distance", "full"), ("front 3/4", "clay"),
         ("game distance", "silhouette"), ("front 3/4", "studio")]


def review(rig, out, px, title, normal_link):
    from PIL import Image, ImageOps
    folder = os.path.splitext(out)[0] + "_views"
    os.makedirs(folder, exist_ok=True)
    tiles = []
    for view, look in SHOTS:
        p = os.path.join(folder, "%s_%s.png" % (view.replace(" ", "").replace("/", ""), look))
        rig.render(p, view, look, px, normal_link)
        label = "%s, %s" % (view, look) if look != "studio" else "Studio-like: colour map only, no normal map"
        tiles.append((Image.open(p).convert("RGB"), label))
    grey = ImageOps.grayscale(tiles[0][0]).convert("RGB")
    tiles.insert(8, (grey, "hero, greyscale (value check)"))
    tiles += ref_tiles(px)
    contact(out, tiles, px, 4, title)


def before_tile(size):
    """The previous bear's hero render, cropped from its review sheet."""
    from PIL import Image
    im = Image.open(BEFORE).convert("RGB")
    t = im.size[0] // 4
    return im.crop((0, 28 + 18, t, 28 + t)).resize((size, int(size * (t - 18) / t)), Image.LANCZOS)


def style_compare(rig, out, px=900, normal_link=None):
    """The reference pets on the left, the new bear's hero render on the right, the face close-up and the
    previous bear ("before") beside it."""
    from PIL import Image, ImageDraw
    folder = os.path.splitext(out)[0] + "_views"
    os.makedirs(folder, exist_ok=True)
    hero = rig.render(os.path.join(folder, "hero.png"), "hero", "full", px, normal_link)
    face = rig.render(os.path.join(folder, "face.png"), "face close", "full", px, normal_link)
    ref = Image.open(REF).convert("RGB")
    W = int(px * 0.62)
    crops = []
    for box in ((18, 95, 422, 540), (458, 90, 862, 500)):
        c = ref.crop(box)
        k = W / c.size[0]
        crops.append(c.resize((W, int(c.size[1] * k)), Image.LANCZOS))
    hh = px
    sheet = Image.new("RGB", (W + px + px // 2 + 40, hh + 70), (20, 22, 27))
    d = ImageDraw.Draw(sheet)
    y = 60
    for c in crops:
        c2 = c.resize((W, min(c.size[1], (hh - 10) // 2)), Image.LANCZOS) if c.size[1] > (hh - 10) // 2 else c
        sheet.paste(c2, (10, y))
        y += c2.size[1] + 10
    d.text((14, 20), "style reference: Steal an Egg", fill=(255, 220, 90))
    sheet.paste(Image.open(hero).convert("RGB"), (W + 20, 60))
    d.text((W + 24, 20), "Stud Bear 2 (Mine an Egg) - hero render", fill=(235, 235, 235))
    f = Image.open(face).convert("RGB").resize((px // 2, px // 2), Image.LANCZOS)
    sheet.paste(f, (W + px + 30, 60))
    d.text((W + px + 34, 40), "face close-up", fill=(235, 235, 235))
    b = before_tile(px // 2 - 60)
    yb = 60 + px // 2 + 50
    sheet.paste(b, (W + px + 30, yb))
    d.text((W + px + 34, yb - 20), "before", fill=(235, 235, 235))
    sheet.save(out)


def stats(objs):
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = objs[0].data
    if me.uv_layers:
        uv = me.uv_layers.active.data
        a2 = 0.0
        for pl in me.polygons:
            p = [uv[i].uv for i in pl.loop_indices]
            a2 += abs(sum(p[i].x * p[(i + 1) % len(p)].y - p[(i + 1) % len(p)].x * p[i].y for i in range(len(p)))) / 2
        a3 = sum(pl.area for pl in me.polygons)
        print("texture: %.0f%% used, about %.0f px per stud at 1024" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    return tris, lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review")
    ap.add_argument("--export")
    ap.add_argument("--peek")
    ap.add_argument("--compare")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--title", default="Stud Bear 2 review")
    ap.add_argument("--texdir", default=os.path.join(HERE, "..", "..", "export", "style_test"))
    a = ap.parse_args()
    kit.fresh()
    bm, glow, k = build()
    body, g, frames, rid_of_face = make_objects(bm, glow)
    head = (head_matrix() @ Vector((0.0, -1.70, 2.30))) * k
    head.y *= Y_SCALE
    if a.peek:
        body.data.materials.append(peek_material())
        stats([body, g])
        rig = SunRig([body, g], head, samples=16)
        from PIL import Image
        folder = os.path.splitext(os.path.abspath(a.peek))[0] + "_views"
        os.makedirs(folder, exist_ok=True)
        tiles = []
        for view, look in (("hero", "full"), ("face front", "full"), ("side", "full"), ("front 3/4", "clay")):
            p = rig.render(os.path.join(folder, "%s_%s.png" % (view.replace(" ", "").replace("/", ""), look)), view, look, a.px)
            tiles.append((Image.open(p).convert("RGB"), view + ", " + look))
        contact(os.path.abspath(a.peek), tiles, a.px, 4, "peek")
        return
    import time
    t0 = time.time()
    paths, normal_link = bake(body, frames, rid_of_face, os.path.abspath(a.texdir))
    print("bake %.1fs" % (time.time() - t0))
    objs = [body, g]
    stats(objs)
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(objs, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.compare:
        rig = SunRig(objs, head, samples=a.samples)
        if a.review:
            review(rig, os.path.abspath(a.review), a.px, a.title, normal_link)
            print("review sheet", a.review)
        if a.compare:
            style_compare(rig, os.path.abspath(a.compare), normal_link=normal_link)


if __name__ == "__main__":
    main()
