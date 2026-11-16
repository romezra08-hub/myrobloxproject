"""Crystal Fox, style test: a hard-surface, faceted pet covered in Roblox studs. Built from scratch by script.

    python models/pets/style_test/crystalfox_v1.py --peek out/peek.png          # quick unbaked look
    python models/pets/style_test/crystalfox_v1.py --review out/r1.png --export models/export/style_test/crystalfox.fbx

Round 1: first build.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402  (first: it brings in bpy)
import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from kit import M  # noqa: E402
from dragon import cull_and_weigh, weigh_islands  # noqa: E402

NAME = "CrystalFox"
TEX = "crystalfox"
SCRATCH = "/tmp/claude-0/-home-user-myrobloxproject/3ebc3f98-354b-587c-92e5-e4969ab0e7cc/scratchpad"
REF = os.path.join(SCRATCH, "sae", "ingame.jpg")

# ---- palette -------------------------------------------------------------------------------------
AMBER = "#E2701C"
AMBER_DK = "#B9520F"
AMBER_LT = "#F08A2C"
CREAM = "#F3E7D3"
CREAM_DK = "#E2D2B8"
CHAR = "#2F2C30"
CHAR_LT = "#47434A"
BONE = "#E9DECB"
TEAL = "#38F0E0"

TARGET_HEIGHT = 3.0
STUD_PITCH = 0.066        # studs, after scaling
STUD_R = 0.021
STUD_H = 0.016
BEVEL = 0.022
STUD_REGION_ANGLE = 16.0  # faces this close in angle share one stud grid
CREASE = 20.0            # only edges sharper than this get a chamfer
HEAD_AT = Vector((0.0, -0.92, 1.9))
HEAD_SIZE = 1.18
BODY = Matrix.Diagonal((1.0, 0.85, 0.88, 1.0))
HEAD_ROT = (4, -3, -17)  # nose a touch down, a small roll, turned towards -X (the cameras)


def hexc(h):
    return Vector(kit.srgb(h))


def rnd(i, k=0.0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)


# ---- shapes ----------------------------------------------------------------------------------------

def hull(pts, bevel=BEVEL):
    """A convex block through the points: flat planes (coplanar triangles merged), every edge chamfered so
    it catches a highlight. The chamfer faces carry the face value "cham" = 1."""
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context='VERTS')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(3.5), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:])
    lc = bm.faces.layers.float.new("cham")
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(CREASE)]
    if bevel > 0 and sharp:
        r = bmesh.ops.bevel(bm, geom=sharp, offset=bevel, offset_type='OFFSET', segments=1, profile=0.5,
                            affect='EDGES', clamp_overlap=True)
        for f in r["faces"]:
            f[lc] = 1.0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def frame(origin, z, up=(0, 0, 1)):
    """Matrix taking local (u, v, w) to origin + u*x + v*y + w*z, with z the given normal and y as close to `up`."""
    z = Vector(z).normalized()
    up = Vector(up)
    x = up.cross(z)
    if x.length < 1e-4:
        x = Vector((0, 1, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def xf(pts, m):
    return [m @ Vector(p) for p in pts]


def slab(outline, thick, m, back=0.85, bevel=BEVEL):
    """A plate: a convex 2D outline (u, v) as the front face at w=0, a slightly smaller copy at w=-thick."""
    pts = [(u, v, 0.0) for u, v in outline] + [(u * back, v * back, -thick) for u, v in outline]
    return hull(xf(pts, m), bevel)


def ring(c, d, rx, ry, sides=8, up=(0, 0, 1), phase=0.5):
    d = Vector(d).normalized()
    up = Vector(up)
    x = up.cross(d)
    if x.length < 1e-4:
        x = Vector((1, 0, 0))
    x.normalize()
    y = d.cross(x)
    out = []
    for k in range(sides):
        a = 2 * math.pi * (k + phase) / sides
        out.append(Vector(c) + x * math.cos(a) * rx + y * math.sin(a) * ry)
    return out


def seg(stations, sides=8, up=(0, 0, 1), phase=0.5, bevel=BEVEL):
    """A faceted limb segment: the hull of rings. stations: [(centre, rx, ry), ...]."""
    pts = []
    cs = [Vector(s[0]) for s in stations]
    for i, (c, rx, ry) in enumerate(stations):
        d = cs[min(i + 1, len(cs) - 1)] - cs[max(i - 1, 0)]
        pts += ring(c, d, rx, ry, sides, up, phase)
    return hull(pts, bevel)


def crystal(base, d, r, h, sides=6, twist=0.0, lean=0.12):
    d = Vector(d).normalized()
    side = d.orthogonal().normalized()
    pts = ring(base - d * 0.06, d, r * 0.8, r * 0.8, sides, phase=twist)
    pts += ring(base + d * h * 0.62, d, r, r, sides, phase=twist)
    pts.append(base + d * h + side * r * lean)
    return hull(pts, 0.0)


# ---- the model ----------------------------------------------------------------------------------------

class Fox:
    LAYERS = ("cr", "cg", "cb", "rough", "cham", "stud", "boost", "part")

    def __init__(self):
        self.body = bmesh.new()
        self.glow = bmesh.new()
        self.L = {k: self.body.faces.layers.float.new(k) for k in self.LAYERS}
        self.tally = {}
        self.count = 0
        self.objects = []
        self.default = None

    def add(self, bm, col, label, rough=0.55, stud=True, boost=0.0, at=None, vary=0.035):
        at = at if at is not None else self.default
        if at is not None:
            bm.transform(at)
        self.count += 1
        base = hexc(col)
        k = 1.0 + (rnd(self.count, 3.1) - 0.5) * 2 * vary
        lc = bm.faces.layers.float.get("cham")
        vmap = {v: self.body.verts.new(v.co) for v in bm.verts}
        bm.normal_update()
        n = 0
        for f in bm.faces:
            nf = self.body.faces.new([vmap[v] for v in f.verts])
            shade = 0.9 + 0.1 * (f.normal.z * 0.5 + 0.5)        # a whisper of sky light from above
            c = base * k * shade
            nf[self.L["cr"]], nf[self.L["cg"]], nf[self.L["cb"]] = c
            nf[self.L["rough"]] = rough
            nf[self.L["cham"]] = f[lc] if lc else 0.0
            nf[self.L["stud"]] = 1.0 if stud else 0.0
            nf[self.L["boost"]] = boost
            nf[self.L["part"]] = self.count
            n += len(f.verts) - 2
        self.tally[label] = self.tally.get(label, 0) + n
        bm.free()

    def add_glow(self, bm, label, at=None):
        at = at if at is not None else self.default
        if at is not None:
            bm.transform(at)
        vmap = {v: self.glow.verts.new(v.co) for v in bm.verts}
        n = 0
        for f in bm.faces:
            self.glow.faces.new([vmap[v] for v in f.verts])
            n += len(f.verts) - 2
        self.tally[label] = self.tally.get(label, 0) + n
        bm.free()


def build_head(fox, H):
    B = 0.5  # head boost for the texture
    # cranium
    pts = []
    for s in (-1, 1):
        pts += [(s * 0.24, -0.16, 0.32), (s * 0.22, 0.2, 0.30), (s * 0.40, -0.05, 0.12), (s * 0.38, 0.22, 0.10),
                (s * 0.25, 0.38, 0.0), (s * 0.2, 0.32, -0.2), (s * 0.32, -0.30, 0.12), (s * 0.14, -0.36, 0.17),
                (s * 0.36, -0.1, -0.16), (s * 0.22, 0.15, -0.28), (s * 0.30, -0.28, -0.12)]
    pts += [(0, -0.22, 0.35), (0, 0.25, 0.31), (0, 0.42, 0.05), (0, 0.1, -0.31)]
    fox.add(hull(pts), AMBER, "head", boost=B, at=H)
    # muzzle core (cream) and its amber bridge
    pts = []
    for sx in (-1, 1):
        pts += [(sx * 0.22, -0.27, 0.06), (sx * 0.24, -0.25, -0.18), (sx * 0.15, -0.55, 0.03), (sx * 0.15, -0.55, -0.15),
                (sx * 0.08, -0.8, -0.02), (sx * 0.07, -0.78, -0.11)]
    pts += [(0, -0.3, -0.24), (0, -0.75, -0.13)]
    fox.add(hull(pts), CREAM, "head", boost=B, at=H)
    pts = []
    for sx in (-1, 1):
        pts += [(sx * 0.16, -0.2, 0.25), (sx * 0.15, -0.29, 0.11), (sx * 0.075, -0.78, -0.005), (sx * 0.07, -0.76, 0.045)]
    pts += [(0, -0.22, 0.29), (0, -0.76, 0.065), (0, -0.45, 0.165)]
    fox.add(hull(pts, 0.016), AMBER, "head", boost=B, at=H)
    # nose
    pts = []
    for sx in (-1, 1):
        pts += [(sx * 0.07, -0.86, 0.02), (sx * 0.08, -0.78, 0.065), (sx * 0.05, -0.84, -0.05), (sx * 0.085, -0.75, 0.0)]
    pts += [(0, -0.885, 0.045), (0, -0.77, -0.075), (0, -0.76, 0.085)]
    fox.add(hull(pts, 0.014), CHAR, "head", boost=B, at=H, rough=0.35)
    # chin: small and set back, so the muzzle stays slim
    pts = []
    for sx in (-1, 1):
        pts += [(sx * 0.09, -0.6, -0.12), (sx * 0.15, -0.3, -0.19), (sx * 0.06, -0.58, -0.17), (sx * 0.12, -0.3, -0.27)]
    pts += [(0, -0.64, -0.15), (0, -0.3, -0.29)]
    fox.add(hull(pts, 0.016), CREAM_DK, "head", boost=B, at=H)
    for s in (-1, 1):
        # mouth: only the back corner, turned up a little: a calm smirk
        for p, q in (((s * 0.115, -0.56, -0.145), (s * 0.16, -0.44, -0.15)), ((s * 0.16, -0.44, -0.15), (s * 0.2, -0.36, -0.12))):
            pts = []
            for e in (p, q):
                pts += [(e[0] + s * 0.012, e[1], e[2] + 0.01), (e[0] + s * 0.012, e[1], e[2] - 0.01),
                        (e[0] - s * 0.02, e[1], e[2] + 0.01), (e[0] - s * 0.02, e[1], e[2] - 0.01)]
            fox.add(hull(pts, 0.004), CHAR, "head", boost=B, at=H, stud=False)
        # cheeks
        pts = [(s * 0.29, -0.34, -0.0), (s * 0.43, -0.06, -0.04), (s * 0.35, -0.26, -0.22), (s * 0.45, 0.08, -0.2),
               (s * 0.22, -0.22, -0.30), (s * 0.30, 0.12, -0.32), (s * 0.2, -0.36, -0.08), (s * 0.28, 0.1, 0.0)]
        fox.add(hull(pts), CREAM, "head", boost=B, at=H)
        # cheek ruff spikes
        for tip, root, w in (((s * 0.56, 0.2, -0.33), (s * 0.38, 0.0, -0.2), 0.12),
                             ((s * 0.52, 0.3, -0.15), (s * 0.38, 0.12, -0.07), 0.1)):
            r = Vector(root)
            t = Vector(tip)
            pts = [t, r + Vector((0, -w, 0.04)), r + Vector((0, w, -0.04)), r + Vector((-s * 0.06, 0, w)),
                   r + Vector((-s * 0.06, 0, -w))]
            fox.add(hull(pts, 0.014), CREAM, "head", boost=B, at=H)
        # eye socket (charcoal) and glowing eye
        n = Vector((s * 0.5, -1.0, 0.15)).normalized()
        ec = Vector((s * 0.2, -0.33, 0.065))
        em = frame(ec, n)
        flip = 1 if s > 0 else -1
        sock = [(flip * u * 1.15, v * 1.15) for u, v in ((-0.1, -0.045), (-0.085, 0.05), (0.07, 0.085), (0.13, 0.05), (0.09, -0.06))]
        fox.add(slab(sock, 0.08, em, bevel=0.01), CHAR, "eyes", boost=B, stud=False, rough=0.4, at=H)
        eye = [(flip * u * 1.2, v * 1.2) for u, v in ((-0.075, -0.025), (-0.065, 0.03), (0.06, 0.06), (0.1, 0.035), (0.06, -0.035))]
        fox.add_glow(slab(eye, 0.03, em @ M((0, 0, 0.012)), bevel=0.0), "eyes", at=H)
        # brow plate: thin, a little above the eye and nearly level, so the look is calm, not cross
        pts = [(s * 0.09, -0.385, 0.185), (s * 0.35, -0.255, 0.215), (s * 0.09, -0.355, 0.235), (s * 0.34, -0.215, 0.26),
               (s * 0.085, -0.34, 0.165), (s * 0.35, -0.21, 0.19)]
        fox.add(hull(pts, 0.012), AMBER_DK, "head", boost=B, at=H)
        # ear: amber outer, cream inner plate, charcoal tip
        base = Vector((s * 0.235, 0.04, 0.24))
        up = Vector((s * 0.36, 0.18, 1.0)).normalized()
        fwd = Vector((s * 0.25, -1.0, 0.1)).normalized()
        fwd = (fwd - up * fwd.dot(up)).normalized()
        side = up.cross(fwd).normalized()
        h = 0.68

        def E(a, b, c):
            return base + side * a + fwd * b + up * c
        outer = [E(-0.19, 0.06, 0), E(0.19, 0.06, 0), E(-0.17, -0.12, 0), E(0.17, -0.12, 0),
                 E(-0.13, 0.03, h * 0.45), E(0.13, 0.03, h * 0.45), E(0, -0.06, h * 0.5), E(0.0, 0.0, h)]
        fox.add(hull(outer), AMBER, "ears", boost=B, at=H)
        inner = [E(-0.13, 0.075, 0.04), E(0.13, 0.075, 0.04), E(0, 0.075, h * 0.78), E(-0.1, 0.03, 0.02),
                 E(0.1, 0.03, 0.02), E(0, 0.03, h * 0.7)]
        fox.add(hull(inner, 0.012), CREAM, "ears", boost=B, at=H)
        tip = [E(-0.085, 0.08, h * 0.6), E(0.085, 0.08, h * 0.6), E(-0.08, -0.07, h * 0.6), E(0.08, -0.07, h * 0.6),
               E(0, 0.01, h * 1.03)]
        fox.add(hull(tip, 0.012), CHAR, "ears", boost=B, at=H)
    # forehead gem
    gm = frame(Vector((0, -0.25, 0.30)), Vector((0, -0.55, 1.0)))
    fox.add(slab([(0, 0.07), (0.05, 0.0), (0, -0.06), (-0.05, 0.0)], 0.04, gm @ M((0, 0, -0.005)), bevel=0.008),
            CHAR, "head", boost=B, stud=False, at=H)
    fox.add_glow(slab([(0, 0.05), (0.032, 0.0), (0, -0.04), (-0.032, 0.0)], 0.03, gm @ M((0, 0, 0.012)), bevel=0.0),
                 "gems", at=H)


def build():
    fox = Fox()
    H = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)
    build_head(fox, H)
    fox.default = BODY

    # ---- torso
    def sym(lst):
        out = []
        for p in lst:
            out.append(p)
            if p[0] != 0:
                out.append((-p[0], p[1], p[2]))
        return out
    chest = sym([(0.30, -0.95, 1.58), (0.38, -0.98, 1.25), (0.24, -0.85, 0.76), (0.40, -0.35, 1.66), (0.42, -0.30, 1.15),
                 (0.28, -0.35, 0.70), (0, -0.9, 1.66), (0, -0.35, 1.74), (0, -0.7, 0.68)])
    fox.add(hull(chest), AMBER, "torso")
    mid = sym([(0.36, -0.45, 1.62), (0.38, -0.45, 1.05), (0.26, -0.45, 0.76), (0.34, 0.35, 1.58), (0.36, 0.35, 1.05),
               (0.24, 0.35, 0.82), (0, -0.45, 1.70), (0, 0.35, 1.66), (0, 0, 0.74)])
    fox.add(hull(mid), AMBER, "torso")
    hip = sym([(0.38, 0.2, 1.60), (0.42, 0.25, 1.05), (0.24, 0.25, 0.92), (0.34, 0.85, 1.55), (0.36, 0.88, 1.10),
               (0.2, 0.8, 0.95), (0, 0.2, 1.68), (0, 0.85, 1.62), (0, 0.95, 1.3)])
    fox.add(hull(hip), AMBER, "torso")
    belly = sym([(0.2, -0.6, 0.76), (0.22, 0.4, 0.84), (0.12, -0.5, 0.7), (0.12, 0.35, 0.78), (0.26, -0.1, 0.9)])
    fox.add(hull(belly), CREAM_DK, "torso")
    # back plates, overlapping like armour from the shoulders to the hips, each with a chevron tail
    for i in range(5):
        y0 = -0.84 + i * 0.36
        y1 = y0 + 0.44
        zt = 1.745 - 0.025 * i - (0.02 if i == 4 else 0.0)
        w = 0.3 - 0.01 * i
        pts = sym([(0, y0, zt + 0.045), (w, y0 + 0.04, zt - 0.13), (0, y1 + 0.08, zt + 0.02), (w * 0.9, y1 - 0.04, zt - 0.15),
                   (0, y0 + 0.02, zt - 0.02), (w, y0 + 0.05, zt - 0.19), (0, y1 + 0.05, zt - 0.04), (w * 0.9, y1 - 0.04, zt - 0.21)])
        fox.add(hull(pts, 0.016), AMBER_DK, "back plates")
    # chest bib: stacked cream shields
    for k, (z, w, hgt, y) in enumerate(((1.52, 0.30, 0.34, -1.02), (1.26, 0.26, 0.3, -1.03), (1.03, 0.2, 0.26, -0.97))):
        m = frame(Vector((0, y, z)), Vector((0, -1.0, -0.25 - 0.1 * k)))
        fox.add(slab([(-w, hgt * 0.45), (w, hgt * 0.45), (w * 0.8, -hgt * 0.1), (0, -hgt * 0.55), (-w * 0.8, -hgt * 0.1)],
                     0.12, m), CREAM, "chest")
    # neck
    fox.add(seg([((0, -0.72, 1.5), 0.3, 0.26), ((0, -0.9, 1.75), 0.27, 0.25), ((0, -1.0, 1.92), 0.24, 0.22)], sides=8),
            AMBER, "neck")
    m = frame(Vector((0, -1.12, 1.75)), Vector((0, -1.0, -0.5)))
    fox.add(slab([(-0.26, 0.16), (0.26, 0.16), (0.22, -0.08), (0, -0.2), (-0.22, -0.08)], 0.16, m), CREAM, "chest")

    for s in (-1, 1):
        # ---- front leg
        x = s * 0.27
        fox.add(seg([((x, -0.6, 1.3), 0.21, 0.22), ((x * 1.02, -0.62, 0.95), 0.18, 0.19), ((x, -0.62, 0.72), 0.16, 0.16)]),
                AMBER, "front legs")
        fox.add(seg([((x, -0.62, 0.8), 0.15, 0.15), ((x, -0.64, 0.45), 0.14, 0.14), ((x, -0.64, 0.2), 0.135, 0.135)]),
                CHAR, "front legs")
        # shoulder: a faceted deltoid mass that grows out of the chest into the leg
        sh = [(s * 0.30, -0.9, 1.55), (s * 0.45, -0.78, 1.4), (s * 0.47, -0.5, 1.44), (s * 0.32, -0.36, 1.62),
              (s * 0.47, -0.62, 1.02), (s * 0.40, -0.84, 0.95), (s * 0.40, -0.42, 0.98), (s * 0.31, -0.62, 0.78),
              (s * 0.22, -0.62, 1.6)]
        fox.add(hull(sh), AMBER, "shoulders")
        sh2 = [(s * 0.465, -0.8, 1.2), (s * 0.49, -0.48, 1.25), (s * 0.48, -0.63, 0.98), (s * 0.43, -0.82, 1.0),
               (s * 0.44, -0.46, 1.02), (s * 0.41, -0.8, 1.22), (s * 0.43, -0.5, 1.28)]
        fox.add(hull(sh2, 0.016), AMBER_DK, "shoulders")
        # shin guard
        m = frame(Vector((x, -0.75, 0.48)), Vector((0, -1.0, 0.08)))
        fox.add(slab([(-0.1, 0.18), (0.1, 0.18), (0.11, -0.12), (0, -0.2), (-0.11, -0.12)], 0.08, m), CHAR_LT, "front legs")
        # crystal socket on the shoulder and crystals
        sc = Vector((s * 0.33, -0.32, 1.62))
        fox.add(hull([sc + Vector(p) for p in ((s * 0.12, 0.1, -0.08), (-s * 0.1, 0.1, -0.08), (s * 0.12, -0.12, -0.08),
                                                  (-s * 0.1, -0.12, -0.08), (s * 0.08, 0.06, 0.07), (-s * 0.06, 0.06, 0.07),
                                                  (s * 0.08, -0.08, 0.07), (-s * 0.06, -0.08, 0.07))]), CHAR, "crystals")
        for d, r, hh, tw in (((s * 0.5, 0.25, 1.0), 0.075, 0.44, 0.1), ((s * 0.95, 0.1, 0.55), 0.055, 0.3, 0.3),
                             ((s * 0.1, 0.6, 0.85), 0.05, 0.27, 0.6)):
            fox.add_glow(crystal(sc + Vector((0, 0, 0.03)), d, r, hh, twist=tw), "crystals")

        # ---- hind leg
        x = s * 0.29
        thigh = [(x + s * 0.12, 0.35, 1.5), (x - s * 0.12, 0.35, 1.5), (x + s * 0.13, 0.78, 1.45), (x - s * 0.1, 0.78, 1.45),
                 (x + s * 0.12, 0.3, 0.9), (x - s * 0.1, 0.3, 0.9), (x + s * 0.1, 0.7, 0.8), (x - s * 0.08, 0.7, 0.8),
                 (x + s * 0.06, 0.42, 0.62), (x - s * 0.06, 0.52, 0.62)]
        fox.add(hull(thigh), AMBER, "hind legs")
        hz = [(s * 0.30, 0.28, 1.6), (s * 0.46, 0.42, 1.46), (s * 0.47, 0.76, 1.42), (s * 0.34, 0.92, 1.52),
              (s * 0.49, 0.55, 1.02), (s * 0.43, 0.84, 0.95), (s * 0.42, 0.33, 0.98), (s * 0.35, 0.47, 0.64),
              (s * 0.31, 0.72, 0.7)]
        fox.add(hull(hz), AMBER, "hind legs")
        hz2 = [(s * 0.485, 0.5, 1.36), (s * 0.495, 0.76, 1.3), (s * 0.5, 0.62, 1.14), (s * 0.44, 0.48, 1.38),
               (s * 0.45, 0.8, 1.32), (s * 0.455, 0.62, 1.1)]
        fox.add(hull(hz2, 0.016), AMBER_DK, "hind legs")
        fox.add(seg([((x, 0.48, 0.7), 0.14, 0.15), ((x, 0.62, 0.42), 0.13, 0.13), ((x, 0.66, 0.3), 0.12, 0.12)]), CHAR, "hind legs")
        fox.add(seg([((x, 0.67, 0.34), 0.12, 0.12), ((x, 0.62, 0.15), 0.125, 0.125)]), CHAR, "hind legs")

        # ---- paws: block, three toes, bone claws
        for py, px in ((-0.66, s * 0.27), (0.56, s * 0.29)):
            paw = [(px + 0.17, py - 0.17, 0.0), (px - 0.17, py - 0.17, 0.0), (px + 0.16, py + 0.17, 0.0),
                   (px - 0.16, py + 0.17, 0.0), (px + 0.15, py - 0.13, 0.16), (px - 0.15, py - 0.13, 0.16),
                   (px + 0.14, py + 0.15, 0.24), (px - 0.14, py + 0.15, 0.24)]
            fox.add(hull(paw), CHAR, "paws")
            for k, dx in enumerate((-0.105, 0.0, 0.105)):
                tx = px + dx
                ty = py - 0.2 - (0.02 if k == 1 else 0.0)
                toe = [(tx + 0.05, ty - 0.08, 0.0), (tx - 0.05, ty - 0.08, 0.0), (tx + 0.055, ty + 0.06, 0.0),
                       (tx - 0.055, ty + 0.06, 0.0), (tx + 0.045, ty - 0.06, 0.11), (tx - 0.045, ty - 0.06, 0.11),
                       (tx + 0.05, ty + 0.06, 0.14), (tx - 0.05, ty + 0.06, 0.14)]
                fox.add(hull(toe, 0.014), CHAR_LT, "paws")
                claw = [(tx + 0.03, ty - 0.07, 0.0), (tx - 0.03, ty - 0.07, 0.0), (tx + 0.025, ty - 0.07, 0.06),
                        (tx - 0.025, ty - 0.07, 0.06), (tx, ty - 0.15, 0.0), (tx, ty - 0.13, 0.025)]
                fox.add(hull(claw, 0.006), BONE, "paws", stud=False, rough=0.4)

    # ---- tail: a faceted core under overlapping shard plates pointing to the tip, amber to a cream tip
    path = [Vector(p) for p in ((0, 0.8, 1.4), (0.04, 1.15, 1.5), (0.1, 1.45, 1.75), (0.13, 1.62, 2.08),
                                (0.12, 1.66, 2.42), (0.06, 1.56, 2.75))]
    radii = [0.13, 0.3, 0.4, 0.4, 0.3, 0.02]

    def at(t):
        return kit._spline(path, t * (len(path) - 1)), max(kit._spline(radii, t * (len(radii) - 1)), 0.02)

    def tangent(t):
        return (at(min(t + 0.01, 1))[0] - at(max(t - 0.01, 0))[0]).normalized()
    sts = []
    for t in (0.0, 0.15, 0.32, 0.5, 0.66, 0.78):
        p, r = at(t)
        sts.append((p, r * 0.92, r * 0.92))
    fox.add(seg(sts, sides=8, up=(1, 0, 0), phase=0.0), AMBER, "tail")
    a0, r0 = at(0.74)
    a1, r1 = at(0.86)
    tipp, _ = at(1.0)
    pts = ring(a0, a1 - a0, r0 * 0.95, r0 * 0.95, 8, up=(1, 0, 0), phase=0.0) + \
        ring(a1, tipp - a0, r1 * 1.0, r1 * 1.0, 8, up=(1, 0, 0), phase=0.0) + [tipp + (tipp - a1).normalized() * 0.08]
    fox.add(hull(pts), CREAM, "tail")
    rows = 5
    for k in range(rows):
        t = 0.1 + k * 0.14
        for j, ang in enumerate((-120, -60, 0, 60, 120)):
            tt = t + (0.07 if j % 2 else 0.0)
            if tt > 0.86:
                continue
            p, r = at(tt)
            tg = tangent(tt)
            ref = Vector((0, 0, 1)) - tg * tg.z
            ref.normalize()
            side = tg.cross(ref)
            a = math.radians(ang + 8 * math.sin(k * 1.7))
            radial = (ref * math.cos(a) + side * math.sin(a)).normalized()
            L = 0.4 + 0.16 * math.sin(math.pi * tt)
            w = 0.26 + 0.12 * math.sin(math.pi * tt)
            nrm = (radial - tg * 0.12).normalized()
            m = frame(p + radial * r * 0.86, nrm, tg)
            outline = [(0, -0.03), (w * 0.5, L * 0.32), (w * 0.12, L * 0.92), (0, L), (-w * 0.12, L * 0.92), (-w * 0.5, L * 0.32)]
            col = CREAM if tt > 0.7 else (AMBER_LT if (j + k) % 2 else AMBER)
            fox.add(slab(outline, 0.07, m, back=0.8, bevel=0.016), col, "tail")
    for t, d, r, hh in ((0.42, (0.2, 0.3, 1.0), 0.06, 0.34), (0.5, (-0.5, 0.5, 0.8), 0.045, 0.24),
                        (0.56, (0.7, 0.6, 0.5), 0.04, 0.2)):
        p, rr = at(t)
        dd = Vector(d).normalized()
        fox.add_glow(crystal(p + dd * rr * 0.75, dd, r, hh, twist=0.2), "crystals")
    return fox


# ---- finishing: scale, cull, studs ----------------------------------------------------------------------

def finish(fox):
    """Scale to height, delete the faces nobody can see, then make the stud layer (a separate bmesh)."""
    for bm in (fox.body, fox.glow):
        bm.normal_update()
    zs = [v.co.z for v in fox.body.verts] + [v.co.z for v in fox.glow.verts]
    k = TARGET_HEIGHT / max(zs)
    for bm in (fox.body, fox.glow):
        bm.transform(Matrix.Scale(k, 4))
    fox.scale = k
    removed = cull_and_weigh({"Body": (fox.body, None), "GLOW": (fox.glow, None)}, keep=("GLOW",))
    print("hidden faces removed: %d triangles" % removed)


def _seg_dist2(q, a, b):
    ex, ey = b[0] - a[0], b[1] - a[1]
    L2 = ex * ex + ey * ey or 1e-12
    t = max(0.0, min(1.0, ((q[0] - a[0]) * ex + (q[1] - a[1]) * ey) / L2))
    dx, dy = a[0] + ex * t - q[0], a[1] + ey * t - q[1]
    return dx * dx + dy * dy


def _inside(q, poly):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > q[1]) != (yj > q[1]) and q[0] < (xj - xi) * (q[1] - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def stud_regions(bm, ok, angle=STUD_REGION_ANGLE):
    """Group neighbouring stud-able faces whose normals are within `angle` of the region's first (largest) face,
    so a gently faceted surface gets one continuous stud grid."""
    cosmax = math.cos(math.radians(angle))
    left = sorted((f for f in bm.faces if ok(f)), key=lambda f: -f.calc_area())
    region_of = {}
    regions = []
    for seed in left:
        if seed in region_of:
            continue
        n0 = seed.normal.copy()
        reg = [seed]
        region_of[seed] = len(regions)
        stack = [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g is f or g in region_of or not ok(g) or g.normal.dot(n0) < cosmax:
                        continue
                    region_of[g] = len(regions)
                    reg.append(g)
                    stack.append(g)
        regions.append(reg)
    return regions


def make_studs(fox, pitch=STUD_PITCH, r=STUD_R, h=STUD_H, sides=10):
    """A Roblox stud grid on every open plate, as a separate mesh. Each region of nearly flat faces gets one grid in
    its average plane, kept clear of the region's outline; every stud is dropped onto the facet under it."""
    bm = fox.body
    verts, polys = [], []
    for src in (fox.body, fox.glow):
        src.verts.index_update()
        base = len(verts)
        verts += [v.co.copy() for v in src.verts]
        polys += [[base + v.index for v in f.verts] for f in src.faces]
    bvh = BVHTree.FromPolygons(verts, polys)
    out = bmesh.new()
    lst, lc, lh = bm.faces.layers.float["stud"], bm.faces.layers.float["cham"], bm.faces.layers.float["hid"]
    margin = r * 1.2 + 0.004
    bm.normal_update()

    def ok(f):
        return f[lst] > 0.5 and f[lc] < 0.5 and f[lh] < 0.95
    count = 0
    for reg in stud_regions(bm, ok):
        area = sum(f.calc_area() for f in reg)
        if area < pitch * pitch * 0.8:
            continue
        n = sum((f.normal * f.calc_area() for f in reg), Vector()).normalized()
        c = sum((f.calc_center_median() * f.calc_area() for f in reg), Vector()) / area
        u = Vector((0, 0, 1)) - n * n.z
        if u.length < 0.35:
            u = Vector((0, 1, 0)) - n * n.y
        u.normalize()
        v = n.cross(u)

        def P2(co):
            d = co - c
            return (d.dot(u), d.dot(v))
        rs = set(reg)
        polys2 = [(f, [P2(x.co) for x in f.verts]) for f in reg]
        bound = [(P2(e.verts[0].co), P2(e.verts[1].co)) for f in reg for e in f.edges
                 if sum(1 for g in e.link_faces if g in rs) < 2]
        allp = [q for _, pl in polys2 for q in pl]
        us = [q[0] for q in allp]
        vs = [q[1] for q in allp]
        nu = int((max(us) - min(us) - 2 * margin) / pitch)
        nv = int((max(vs) - min(vs) - 2 * margin) / pitch)
        if nu < 0 or nv < 0:
            continue
        u0 = (max(us) + min(us)) / 2 - nu * pitch / 2
        v0 = (max(vs) + min(vs)) / 2 - nv * pitch / 2
        m2 = margin * margin
        for i in range(nu + 1):
            for j in range(nv + 1):
                q = (u0 + i * pitch, v0 + j * pitch)
                face = next((f for f, pl in polys2 if _inside(q, pl)), None)
                if face is None or any(_seg_dist2(q, a, b) < m2 for a, b in bound):
                    continue
                fn = face.normal
                P0 = c + u * q[0] + v * q[1]
                d = n.dot(fn)
                if abs(d) < 0.5:
                    continue
                t = (face.verts[0].co - P0).dot(fn) / d
                P = P0 + n * t
                o = P + fn * 0.003
                if bvh.ray_cast(o, fn, 0.06)[0] is not None:
                    continue
                hit = bvh.ray_cast(o, fn, 6.0)
                if hit[0] is not None and hit[1].dot(fn) > 0:
                    continue
                fu = (u - fn * fn.dot(u)).normalized()
                fv = fn.cross(fu)
                rings = []
                for rad, w in ((r, -0.004), (r, h * 0.62), (r * 0.72, h)):
                    rings.append([out.verts.new(P + (fu * math.cos(a) + fv * math.sin(a)) * rad + fn * w)
                                  for a in (2 * math.pi * k / sides for k in range(sides))])
                for A, B in zip(rings, rings[1:]):
                    for k in range(sides):
                        out.faces.new((A[k], A[(k + 1) % sides], B[(k + 1) % sides], B[k]))
                out.faces.new(rings[-1])
                count += 1
    bmesh.ops.recalc_face_normals(out, faces=out.faces[:])
    print("studs:", count)
    return out


# ---- objects, materials, baking -----------------------------------------------------------------------

def to_object(bm, name, free=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    if free:
        bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.shade_flat()
    return ob


def attr_material(name, emit=False, which="col"):
    """Base colour (or an emission, for baking) from the face values."""
    m = bpy.data.materials.new(name)
    b = kit.principled(m)
    t = m.node_tree
    comb = t.nodes.new("ShaderNodeCombineColor")
    names = {"col": ("cr", "cg", "cb"), "rough": ("rough",) * 3, "cham": ("cham",) * 3}[which]
    for i, nm in enumerate(names):
        a = t.nodes.new("ShaderNodeAttribute")
        a.attribute_type, a.attribute_name = 'GEOMETRY', nm
        t.links.new(a.outputs["Fac"], comb.inputs[i])
    if emit:
        em = t.nodes.new("ShaderNodeEmission")
        t.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in t.nodes if n.type == 'OUTPUT_MATERIAL')
        t.links.new(em.outputs[0], out.inputs[0])
    else:
        t.links.new(comb.outputs[0], b.inputs["Base Color"])
        t.links.new(t.nodes.new("ShaderNodeAttribute").outputs["Fac"], b.inputs["Roughness"])
        t.nodes[-1].attribute_name = "rough"
    return m


def glow_material():
    m = bpy.data.materials.new("GLOW_Crystal")
    b = kit.principled(m)
    rgb = kit.srgb(TEAL)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Emission Color"].default_value = (*rgb, 1)
    b.inputs["Emission Strength"].default_value = 2.2
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


def masked_blur(a, w, r):
    """The average of `a` over nearby pixels where w=1: fills the holes where w=0."""
    return box_blur(a * w, r) / np.maximum(box_blur(w, r), 1e-4)


def bake(fox, texture_dir):
    """The body: unwrap, bake colour/roughness/chamfer from the face values, normals and occlusion from the stud
    version onto the plate version, then mix them into the colour image. Writes <tex>_colour/_rough/_normal.png."""
    size = 512 if os.environ.get("PETS_FAST") else 1024
    margin = max(3, size // 160)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    high_bm = make_studs(fox)            # the studs alone: rays that miss them leave the pixel as it was
    low_bm = fox.body
    bmesh.ops.triangulate(low_bm, faces=low_bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    low = to_object(low_bm, NAME + "_Body")
    high = to_object(high_bm, NAME + "_High", free=True)
    glow = to_object(fox.glow, NAME + "_GLOW")
    gm = glow_material()
    glow.data.materials.append(gm)
    high.data.materials.append(attr_material("CF_High"))
    fox.high = high
    # unwrap
    select([low], low)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), island_margin=0.002)
    weigh_islands(low)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(shape_method='CONCAVE', rotate=True, rotate_method='ANY', margin_method='FRACTION',
                            margin=0.0045)
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = {w: attr_material("CF_Emit_" + w, emit=True, which=w) for w in ("col", "rough", "cham")}
    low.data.materials.append(mats["col"])
    world = sc.world or bpy.data.worlds.new("BakeWorld")
    sc.world = world

    def run(kind, img_name, mat=None, samples=1, objs=None, fill=None, **kw):
        if mat is not None:
            low.data.materials[0] = mat
        img = bpy.data.images.new(img_name, size, size, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color'
        if fill is not None:
            img.pixels.foreach_set(np.tile(np.array([*fill, 1.0], dtype=np.float32), size * size))
        tree = low.data.materials[0].node_tree
        n = tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        tree.nodes.active = n
        select(objs or [low], low)
        sc.cycles.samples = samples
        bpy.ops.object.bake(type=kind, margin=margin if fill is None else 0, margin_type='EXTEND', **kw)
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        tree.nodes.remove(n)
        bpy.data.images.remove(img)
        return px.reshape(size, size, 4)[..., :3].copy()

    col = run('EMIT', "b_col", mats["col"], 1)
    rough = run('EMIT', "b_rough", mats["rough"], 1)[..., :1]
    cham = run('EMIT', "b_cham", mats["cham"], 1)[..., :1]
    nl = run('NORMAL', "b_nlow", None, 4, normal_space='OBJECT')
    world.light_settings.distance = 0.05
    ao_s = run('AO', "b_aos", None, 64)[..., :1]                     # plate seams and the ring round each stud
    world.light_settings.distance = 0.5
    ao_l = run('AO', "b_aol", None, 48)[..., :1]
    s2a = dict(use_selected_to_active=True, cage_extrusion=0.03, max_ray_distance=0.06)
    nt = run('NORMAL', "b_nt", None, 4, objs=[low, high], fill=(0.5, 0.5, 1.0), normal_space='TANGENT', **s2a)
    nh = run('NORMAL', "b_nh", None, 4, objs=[low, high], fill=(0.0, 0.0, 0.0), normal_space='OBJECT', **s2a)
    world.light_settings.distance = 0.05
    ao_t = run('AO', "b_aot", None, 32, objs=[low, high], fill=(-1.0, -1.0, -1.0), **s2a)[..., :1]
    mask = (np.linalg.norm(nh * 2 - 1, axis=-1, keepdims=True) < 1.5).astype(np.float32)   # unbaked (0,0,0) decodes to length 1.73
    mask = mask * (ao_t >= 0)
    nh = np.where(mask > 0, nh, nl)
    ao_s = np.where(mask > 0, np.clip(ao_t, 0, 1) * 0.15 + 0.85, ao_s)     # stud tops are open to the sky
    ao_l = np.where(mask > 0, masked_blur(ao_l, 1 - mask, 6), ao_l)
    # widen the untouched flat area of the tangent normal map into the bake margin
    nt = np.where(mask > 0, nt, np.array([0.5, 0.5, 1.0], dtype=np.float32))
    # ---- mix
    dn = (nh * 2 - 1) - (nl * 2 - 1)
    L = np.array([-0.35, -0.45, 0.82], dtype=np.float32)
    L /= np.linalg.norm(L)
    emb = np.clip((dn * L).sum(-1, keepdims=True), -0.6, 0.6)
    out = col * (1.0 + 1.7 * emb) * (1.0 + 0.1 * mask)
    out *= 1.0 + 0.16 * cham
    out *= 0.42 + 0.58 * np.clip((ao_s - 0.1) / 0.8, 0, 1) ** 1.1
    out *= 1.0 - 0.4 * (1.0 - np.clip(ao_l, 0, 1))
    os.makedirs(texture_dir, exist_ok=True)
    paths = {k: os.path.join(texture_dir, "%s_%s.png" % (TEX, k)) for k in ("colour", "rough", "normal")}
    save_png(out, paths["colour"], True)
    r = np.clip(rough + 0.25 * (1 - ao_s), 0, 1)
    save_png(np.repeat(r, 3, -1), paths["rough"], False)
    save_png(nt, paths["normal"], False)
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
    fox.normal_link = (nm, b)
    low.data.materials.clear()
    low.data.materials.append(m)
    for nmx in ("cr", "cg", "cb", "rough", "cham", "stud", "boost", "part", "hid"):
        if nmx in low.data.attributes:
            low.data.attributes.remove(low.data.attributes[nmx])
    high.hide_render = True
    high.hide_set(True)
    fox.objects = [low, glow]
    return paths


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

    def __init__(self, objs, head, samples=40):
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = 'CPU', samples, True
        sc.view_settings.view_transform = 'Standard'
        self.objs = objs
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
        self.sun.rotation_euler = Vector((0.42, 0.62, -0.66)).to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(self.sun)
        fl = bpy.data.lights.new("SkyFill", 'AREA')
        fl.energy, fl.size, fl.color = 260.0, 6.0, (0.85, 0.92, 1.0)
        self.fill = bpy.data.objects.new("SkyFill", fl)
        self.fill.location = c + Vector((4.5, -3.5, 2.0))
        _aim(self.fill, c)
        sc.collection.objects.link(self.fill)
        dist = size * 2.7
        head = Vector(head)
        self.cams = {
            "front 3/4": _camera("C_front34", c + Vector((-0.55, -1.0, 0.3)).normalized() * dist, c, 34),
            "front": _camera("C_front", c + Vector((0, -1.0, 0.08)).normalized() * dist, c, 34),
            "side": _camera("C_side", c + Vector((-1.0, -0.02, 0.1)).normalized() * dist, c, 34),
            "back 3/4": _camera("C_back34", c + Vector((-0.6, 1.0, 0.4)).normalized() * dist, c, 34),
            "close-up": _camera("C_close", Vector((-0.2, -0.5, 1.45)) + Vector((-0.6, -1.0, 0.25)).normalized() * 3.2,
                                Vector((-0.2, -0.5, 1.45)), 30),
            "game distance": _camera("C_game", Vector((c.x - 2.5, c.y - 10, lo.z + 4.0)), c + Vector((1.2, 0, 0.3)), 70),
            "face 3/4": _camera("C_face", head + Vector((-0.6, -1.0, 0.15)).normalized() * 4.3, head + Vector((0, 0, 0.12)), 30),
            "face front": _camera("C_facef", head + Vector((0, -1.0, 0.06)).normalized() * 4.2, head + Vector((0, 0, 0.12)), 30),
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
        studio = look == "studio"
        cut = None
        if studio and normal_link:
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
            self.sun.rotation_euler = Vector((0.42, 0.62, -0.66)).to_track_quat('-Z', 'Y').to_euler()
            self.sun.data.energy = 3.6
            self.fill.hide_render = False
        layer.material_override = None
        return path

    def sheet(self, out, shots, px=512, cols=4, title="", normal_link=None, compare=True):
        from PIL import Image, ImageDraw
        folder = os.path.splitext(out)[0] + "_views"
        os.makedirs(folder, exist_ok=True)
        tiles = []
        for view, look in shots:
            p = os.path.join(folder, "%s_%s.png" % (view.replace(" ", "").replace("/", ""), look))
            self.render(p, view, look, px, normal_link)
            label = "%s, %s" % (view, look) if look != "studio" else "Studio-like: colour map only, no normal map"
            tiles.append((Image.open(p).convert("RGB"), label))
        self.tiles = {(v, lk): os.path.join(folder, "%s_%s.png" % (v.replace(" ", "").replace("/", ""), lk))
                      for v, lk in shots}
        if compare:
            ref = Image.open(REF).convert("RGB")
            for box, label in (((18, 95, 422, 540), "style reference: Steal an Egg (tiger)"),
                               ((458, 90, 862, 500), "style reference: Steal an Egg (wolf)")):
                crop = ref.crop(box)
                k = px / max(crop.size)
                crop = crop.resize((int(crop.size[0] * k), int(crop.size[1] * k)), Image.LANCZOS)
                tile = Image.new("RGB", (px, px), (18, 20, 24))
                tile.paste(crop, ((px - crop.size[0]) // 2, (px - crop.size[1]) // 2))
                tiles.append((tile, label))
        rows = (len(tiles) + cols - 1) // cols
        top = 28 if title else 0
        sheet = Image.new("RGB", (cols * px, rows * px + top), (18, 20, 24))
        draw = ImageDraw.Draw(sheet)
        if title:
            draw.text((8, 7), title, fill=(235, 235, 235))
        for i, (img, label) in enumerate(tiles):
            x, y = (i % cols) * px, (i // cols) * px + top
            sheet.paste(img, (x, y))
            draw.rectangle((x, y, x + 8 + 6 * len(label), y + 16), fill=(0, 0, 0))
            draw.text((x + 4, y + 2), label, fill=(255, 255, 255))
        sheet.save(out)
        return out


SHOTS = [("front 3/4", "full"), ("front", "full"), ("side", "full"), ("back 3/4", "full"),
         ("face 3/4", "full"), ("face front", "full"), ("close-up", "full"), ("game distance", "full"),
         ("front 3/4", "clay"), ("game distance", "silhouette"), ("front 3/4", "studio")]


def style_compare(rig, out, px=900, normal_link=None):
    """Crops of the reference pets beside a large hero render and the face close-up."""
    from PIL import Image, ImageDraw
    folder = os.path.splitext(out)[0] + "_views"
    os.makedirs(folder, exist_ok=True)
    hero = rig.render(os.path.join(folder, "hero.png"), "hero", "full", px, normal_link)
    face = rig.render(os.path.join(folder, "face.png"), "face 3/4", "full", px // 2 * 2 // 2 * 2, normal_link)
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
    d.text((W + 24, 20), "Crystal Fox (Mine an Egg) - hero render", fill=(235, 235, 235))
    f = Image.open(face).convert("RGB").resize((px // 2, px // 2), Image.LANCZOS)
    sheet.paste(f, (W + px + 30, 60))
    d.text((W + px + 34, 20), "face close-up", fill=(235, 235, 235))
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review")
    ap.add_argument("--export")
    ap.add_argument("--peek")
    ap.add_argument("--compare")
    ap.add_argument("--views", default="front 3/4,face 3/4,side,back 3/4")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--title", default="Crystal Fox review")
    ap.add_argument("--texdir", default=os.path.join(HERE, "..", "..", "export", "style_test"))
    a = ap.parse_args()
    kit.fresh()
    fox = build()
    finish(fox)
    head = M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE) @ Vector((0, -0.25, 0.0)) * fox.scale
    print("triangles by part:", dict(sorted(fox.tally.items(), key=lambda kv: -kv[1])))
    if a.peek:
        low = to_object(fox.body, NAME + "_Body")
        low.data.materials.append(attr_material("CF_Flat"))
        glow = to_object(fox.glow, NAME + "_GLOW")
        glow.data.materials.append(glow_material())
        rig = SunRig([low, glow], head, samples=16)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), "full") for v in a.views.split(",")], px=a.px,
                  title="peek", compare=False)
        return
    paths = bake(fox, os.path.abspath(a.texdir))
    body, glow = fox.objects
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in fox.objects}
    pts = [o.matrix_world @ Vector(c) for o in fox.objects for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest z=%.4f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    me = body.data
    uv = me.uv_layers.active.data
    a2 = 0.0
    for pl in me.polygons:
        p = [uv[i].uv for i in pl.loop_indices]
        a2 += abs(sum(p[i].x * p[(i + 1) % len(p)].y - p[(i + 1) % len(p)].x * p[i].y for i in range(len(p)))) / 2
    a3 = sum(pl.area for pl in me.polygons)
    print("texture: %.0f%% used, about %.0f px per stud at 1024" % (a2 * 100, (a2 * 1024 * 1024 / a3) ** 0.5))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(fox.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.compare:
        rig = SunRig(fox.objects, head, samples=a.samples)
        if a.review:
            rig.sheet(os.path.abspath(a.review), SHOTS, px=a.px, title=a.title, normal_link=fox.normal_link)
            print("review sheet", a.review)
        if a.compare:
            style_compare(rig, os.path.abspath(a.compare), normal_link=fox.normal_link)


if __name__ == "__main__":
    main()
