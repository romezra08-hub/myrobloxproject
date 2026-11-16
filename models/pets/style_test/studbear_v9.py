"""Stud Bear, style test: one sculpted bear reduced to flat facets, covered in fine Roblox studs, in the look of the
newer pets in "Steal an Egg" (style only: nothing is copied). Built from scratch by script.

    python models/pets/style_test/studbear.py --peek out/peek.png          # quick unbaked look
    python models/pets/style_test/studbear.py --review models/preview/studbear.png \
        --compare models/preview/studbear_style_compare.png --export models/export/style_test/studbear.fbx

Method:
  1. Sculpt: the whole bear is one signed-distance field (ellipsoids, round cones and boxes joined with smooth
     unions), meshed by surface nets on a 0.02 stud grid: one continuous form, no loose parts.
  2. Facets: Blender's collapse decimate, symmetric in x, finer on the face and paws; flat shading.
  3. Design on the facets: colour regions per face, armour plates lifted off the form along its facets, claws.
  4. Glow (StudBear_GLOW, GLOW_Crystal): angular eyes laid into carved sockets, ore crystal clusters.
  5. Pose by deforming the faceted mesh: head raised and turned, the left front paw forward.
  6. Texture: per texel position, normal, tangent and region id are baked; the studs (a grid in each flat
     region's own plane), their shading, the facet edge light and the tangent normal map are computed per texel.
"""
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

NAME = "StudBear"
TEX = "studbear"
SCRATCH = "/tmp/claude-0/-home-user-myrobloxproject/3ebc3f98-354b-587c-92e5-e4969ab0e7cc/scratchpad"
REF = os.path.join(SCRATCH, "sae", "ingame.jpg")

TARGET_HEIGHT = 3.0
FPAW = ((0.78, -1.00, 0.17), (0.37, 0.44, 0.17))     # front paw block: centre, half size (right side)
HPAW = ((0.64, 0.80, 0.16), (0.32, 0.40, 0.16))
VOXEL = 0.02
FACETS = 1400             # triangles after the collapse
FINE_FACTOR = 0.0         # how much finer the facets stay on the face and paws
PLATE_T = 0.075           # armour plate thickness (before scaling)
HEAD_YAW = -22.0          # degrees, towards -X
HEAD_PITCH = 8.0 
HEAD_ROLL = 4.0          # degrees: a slight curious tilt
         # degrees, nose up
PAW_STEP = 0.22
EYE_SCALE = 1.36
EYE_DEPTH = 0.035         # socket floor behind the deepest face point under the eye
SOCKET_PAD = 1.0
LENS_PAD = 0.97
BROW = True              # the separate brow shelf read as a frown
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
BEVEL = 0.011
BEVEL_ANGLE = 24.0
EDGE_W = 0.010
EDGE_LIGHT = 0.10
EDGE_MIN_ANGLE = 32.0
STUD_MARGIN = 0.55
EYE_TILT = 5.0           # degrees: raises the inner corner, for a calm look
AO_SAMPLES = 32
AO_DARK = 0.45
FACET_JITTER = 0.035

# ---- signed distance sculpting ------------------------------------------------------------------------

def rot(deg):
    ax, ay, az = np.radians(deg)
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Pts:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def mirror(self):
        return Pts(np.abs(self.x), self.y, self.z)

    def local(self, c, deg=None):
        x, y, z = self.x - c[0], self.y - c[1], self.z - c[2]
        if deg is None:
            return x, y, z
        R = rot(deg).T
        return (R[0, 0] * x + R[0, 1] * y + R[0, 2] * z,
                R[1, 0] * x + R[1, 1] * y + R[1, 2] * z,
                R[2, 0] * x + R[2, 1] * y + R[2, 2] * z)


def ellipsoid(p, c, r, deg=None):
    x, y, z = p.local(c, deg)
    k0 = np.sqrt((x / r[0]) ** 2 + (y / r[1]) ** 2 + (z / r[2]) ** 2)
    k1 = np.sqrt((x / r[0] ** 2) ** 2 + (y / r[1] ** 2) ** 2 + (z / r[2] ** 2) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def cone(p, a, b, r1, r2):
    """Round cone (a capsule with different end radii)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = b - a
    l2 = ba.dot(ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    px, py, pz = p.x - a[0], p.y - a[1], p.z - a[2]
    y = px * ba[0] + py * ba[1] + pz * ba[2]
    z = y - l2
    qx, qy, qz = px * l2 - ba[0] * y, py * l2 - ba[1] * y, pz * l2 - ba[2] * y
    x2 = qx * qx + qy * qy + qz * qz
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d_mid = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
    d_b = np.sqrt(x2 + z2) * il2 - r2
    d_a = np.sqrt(x2 + y2) * il2 - r1
    return np.where(np.sign(z) * a2 * z2 > k, d_b, np.where(np.sign(y) * a2 * y2 < k, d_a, d_mid))


def rbox(p, c, half, r, deg=None):
    x, y, z = p.local(c, deg)
    qx, qy, qz = np.abs(x) - half[0] + r, np.abs(y) - half[1] + r, np.abs(z) - half[2] + r
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r


def plane(p, c, n):
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    return (p.x - c[0]) * n[0] + (p.y - c[1]) * n[1] + (p.z - c[2]) * n[2]


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def U(k, *ds):
    d = ds[0]
    for e in ds[1:]:
        d = smin(d, e, k)
    return d


# ---- the bear ----------------------------------------------------------------------------------------

def toes(m, c, half, n=4, r=(0.095, 0.11, 0.115)):
    """A row of toe pads along the front of a paw block."""
    d = None
    for i in range(n):
        x = c[0] + (i - (n - 1) / 2) * (2 * half[0] - 2 * r[0]) / (n - 1)
        e = ellipsoid(m, (x, c[1] - half[1] + r[1] * 0.6, r[2] * 0.95), r)
        d = e if d is None else np.minimum(d, e)
    return d


def bear_base(p):
    """The whole bear as one field: negative inside. Symmetric in x (paired parts use the mirrored points)."""
    m = p.mirror()
    # trunk: a massive chest and shoulder hump tapering to smaller hips
    chest = ellipsoid(p, (0, -0.55, 1.38), (0.90, 0.95, 0.82))
    brisket = ellipsoid(p, (0, -1.0, 1.22), (0.60, 0.42, 0.55))
    hump = ellipsoid(p, (0, -0.42, 2.00), (0.68, 0.62, 0.50))
    belly = ellipsoid(p, (0, 0.45, 1.28), (0.72, 0.80, 0.60))
    rump = ellipsoid(p, (0, 0.95, 1.32), (0.60, 0.52, 0.52))
    tail = ellipsoid(p, (0, 1.45, 1.52), (0.19, 0.16, 0.18))
    trunk = U(0.35, chest, brisket, hump, belly, rump)
    trunk = smin(trunk, tail, 0.08)
    # front legs: shoulder mass, thick arm with an elbow, wrist, big paw with toes
    shoulder = ellipsoid(m, (0.58, -0.66, 1.36), (0.40, 0.50, 0.55))
    arm = cone(m, (0.68, -0.68, 1.20), (0.75, -0.80, 0.48), 0.42, 0.36)
    elbow = ellipsoid(m, (0.70, -0.46, 0.92), (0.28, 0.26, 0.30))
    wrist = cone(m, (0.75, -0.80, 0.48), (0.78, -0.90, 0.22), 0.36, 0.37)
    fpc, fph = FPAW
    fpaw = smin(rbox(m, fpc, fph, 0.12), toes(m, fpc, fph, r=(0.10, 0.115, 0.12)), 0.03)
    fleg = U(0.12, shoulder, arm, elbow, wrist)
    fleg = smin(fleg, fpaw, 0.10)
    # hind legs: haunch, shin, paw
    thigh = ellipsoid(m, (0.50, 0.78, 1.08), (0.38, 0.55, 0.60))
    shin = cone(m, (0.58, 0.90, 0.75), (0.63, 0.88, 0.26), 0.32, 0.28)
    hpc, hph = HPAW
    hpaw = smin(rbox(m, hpc, hph, 0.11), toes(m, hpc, hph, r=(0.085, 0.1, 0.105)), 0.03)
    hleg = U(0.12, thigh, shin)
    hleg = smin(hleg, hpaw, 0.10)
    body = U(0.22, trunk, fleg, hleg)
    # neck and head: big and broad, wide cheeks, a short broad muzzle
    neck = cone(p, (0, -0.85, 1.70), (0, -1.32, 2.12), 0.58, 0.50)
    skull = ellipsoid(p, (0, -1.42, 2.42), (0.64, 0.55, 0.52))
    skull = smax(skull, plane(p, (0, -1.80, 2.62), (0, -0.55, 0.83)), 0.10)       # broad flat forehead
    cheek = ellipsoid(m, (0.40, -1.68, 2.12), (0.36, 0.36, 0.30))
    muzzle = ellipsoid(p, (0, -1.98, 2.13), (0.31, 0.36, 0.24))
    muzzle = smax(muzzle, plane(p, (0, -2.0, 2.29), (0, -0.25, 1)), 0.06)          # flat bridge
    muzzle = smax(muzzle, plane(m, (0.25, -2.0, 2.1), (1, -0.25, 0)), 0.06)        # flat sides
    chin = ellipsoid(p, (0, -1.92, 1.95), (0.22, 0.26, 0.12))
    nose = ellipsoid(p, (0, -2.26, 2.27), (0.13, 0.075, 0.08))
    nose = smax(nose, plane(p, (0, -2.26, 2.32), (0, -0.3, 1)), 0.02)
    brow = ellipsoid(m, (0.25, -1.83, 2.62), (0.20, 0.11, 0.055), (0, 0, 10))           # a soft brow ridge, above a gap
    ear = ellipsoid(m, (0.48, -1.28, 2.86), (0.20, 0.10, 0.20), (0, -25, 0))
    ear = smax(ear, -ellipsoid(m, (0.50, -1.36, 2.88), (0.12, 0.06, 0.12), (0, -25, 0)), 0.03)
    head = U(0.2, skull, cheek)
    head = U(0.12, head, muzzle, chin)
    if BROW:
        head = smin(head, brow, 0.10)
    head = smin(head, nose, 0.05)
    head = smin(head, ear, 0.07)
    d = smin(body, neck, 0.25)
    d = smin(d, head, 0.2)
    return smax(d, -p.z, 0.0)          # flat on the ground


def eye_frame(sx=1):
    """Centre, view direction, outer-corner direction and up direction of one eye (before posing)."""
    c = np.array([EYE_C.x * sx, EYE_C.y, EYE_C.z])
    d = np.array([EYE_D.x * sx, EYE_D.y, EYE_D.z])
    u = np.cross([0, 0, 1.0], d)
    u /= np.linalg.norm(u)
    if u[0] * sx < 0:
        u = -u
    v = np.cross(d, u)
    v /= np.linalg.norm(v)
    if v[2] < 0:
        v = -v
    return c, d, u, v


def eye_outline(pad=1.0):
    """The eye shape in the eye's (u, v) plane, tilted and scaled."""
    ct, st = math.cos(math.radians(EYE_TILT)), math.sin(math.radians(EYE_TILT))
    return [((a0 * ct + b0 * st) * EYE_SCALE * pad, (-a0 * st + b0 * ct) * EYE_SCALE * pad) for a0, b0 in EYE_SHAPE]


_FLOOR = {}


def eye_floor():
    """Depth (along the eye direction, from EYE_C) of the flat socket floor: a little behind the deepest point
    of the face under the eye outline."""
    if "t" not in _FLOOR:
        c, d, u, v = eye_frame(1)
        ts = np.linspace(-0.4, 0.4, 801)
        deepest = 1.0
        for a, b in eye_outline() + [(0.0, 0.0)]:
            q = c + u * a + v * b
            P = q[None] + ts[:, None] * d[None]
            f = bear_base(Pts(P[:, 0], P[:, 1], P[:, 2]))
            k = np.flatnonzero((f[:-1] < 0) & (f[1:] >= 0))
            t = ts[k[-1]] if len(k) else 0.0
            deepest = min(deepest, t)
        _FLOOR["t"] = deepest - EYE_DEPTH
    return _FLOOR["t"]


def poly_sdf(a, b, poly):
    """Signed distance to a closed 2D polygon (negative inside)."""
    dmin = np.full(a.shape, 1e9, np.float32)
    inside = np.zeros(a.shape, bool)
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        t = np.clip(((a - x0) * ex + (b - y0) * ey) / (ex * ex + ey * ey), 0, 1)
        dx, dy = a - x0 - ex * t, b - y0 - ey * t
        dmin = np.minimum(dmin, dx * dx + dy * dy)
        cond = (y0 > b) != (y1 > b)
        xi = x0 + (b - y0) * ex / (ey if ey != 0 else 1e-12)
        inside ^= cond & (a < xi)
    dist = np.sqrt(dmin)
    return np.where(inside, -dist, dist)


def bear(p):
    """The bear with its eye sockets: the eye shape cut straight into the face to an even depth."""
    d = bear_base(p)
    m = p.mirror()
    c, dv, u, v = eye_frame(1)
    x, y, z = m.x - c[0], m.y - c[1], m.z - c[2]
    a = x * u[0] + y * u[1] + z * u[2]
    b = x * v[0] + y * v[1] + z * v[2]
    w = x * dv[0] + y * dv[1] + z * dv[2]
    sock = np.maximum(poly_sdf(a, b, eye_outline(SOCKET_PAD)), -d - EYE_DEPTH)    # an even-depth recess
    sock = np.maximum(sock, np.abs(w) - 0.4)
    return smax(d, -sock, 0.006)


# ---- meshing ------------------------------------------------------------------------------------------

def surface_nets(F, origin, h):
    """One vertex per grid cell the surface crosses (the mean of its edge crossings), one quad per crossed
    grid edge."""
    nx, ny, nz = F.shape
    inside = F < 0
    corners = [(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
             if sum(abs(corners[a][t] - corners[b][t]) for t in range(3)) == 1]
    S = np.zeros((nx - 1, ny - 1, nz - 1, 3), np.float32)
    C = np.zeros((nx - 1, ny - 1, nz - 1), np.float32)

    def sl(c):
        return F[c[0]:nx - 1 + c[0], c[1]:ny - 1 + c[1], c[2]:nz - 1 + c[2]]
    for a, b in edges:
        fa, fb = sl(corners[a]), sl(corners[b])
        msk = (fa < 0) != (fb < 0)
        t = np.where(msk, fa / np.where(msk, fa - fb, 1.0), 0.0)
        for ax in range(3):
            pa, pb = corners[a][ax], corners[b][ax]
            S[..., ax] += np.where(msk, pa + t * (pb - pa), 0.0)
        C += msk
    act = C > 0
    idx = -np.ones(C.shape, np.int64)
    idx[act] = np.arange(int(act.sum()))
    I, J, K = np.nonzero(act)
    verts = (S[act] / C[act][:, None] + np.stack([I, J, K], 1)) * h + np.asarray(origin)
    quads = []
    dims = (nx, ny, nz)
    for ax in range(3):
        o = [0, 0, 0]
        o[ax] = 1
        a = inside[:nx - o[0], :ny - o[1], :nz - o[2]]
        b = inside[o[0]:, o[1]:, o[2]:]
        ii, jj, kk = np.nonzero(a != b)
        flip = a[ii, jj, kk]
        u, v = [(1, 2), (2, 0), (0, 1)][ax]
        P0 = np.stack([ii, jj, kk], 1)
        ok = (P0[:, u] >= 1) & (P0[:, v] >= 1) & (P0[:, ax] < dims[ax] - 1)
        P0, flip = P0[ok], flip[ok]
        cs = []
        for du, dv in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            Q = P0.copy()
            Q[:, u] += du
            Q[:, v] += dv
            cs.append(idx[Q[:, 0], Q[:, 1], Q[:, 2]])
        q = np.stack(cs, 1)
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    quads = np.concatenate(quads)
    return verts, quads[(quads >= 0).all(1)]


def sculpt(field=None, lo=(-1.3, -2.55, -0.06), hi=(1.3, 1.75, 3.15), h=VOXEL):
    n = [int(round((b - a) / h)) + 1 for a, b in zip(lo, hi)]
    if n[0] % 2 == 0:
        n[0] += 1                          # an odd count keeps x=0 on the grid: the mesh comes out symmetric
    xs = (np.arange(n[0]) - (n[0] - 1) / 2) * h
    ys = lo[1] + np.arange(n[1]) * h
    zs = lo[2] + np.arange(n[2]) * h
    X, Y, Z = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32), zs.astype(np.float32), indexing='ij')
    F = (field or bear)(Pts(X, Y, Z)).astype(np.float32)
    verts, quads = surface_nets(F, (xs[0], ys[0], zs[0]), h)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts.tolist()]
    for q in quads.tolist():
        try:
            bm.faces.new([vs[i] for i in q])
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # surface nets can pinch where two sheets touch diagonally: a voxel remesh makes it cleanly manifold
    ob = to_object(bm, "remesh_tmp")
    bm.free()
    ob.data.remesh_voxel_size = h * 0.7
    ob.data.remesh_voxel_adaptivity = 0.0
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.voxel_remesh()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bpy.data.objects.remove(ob)
    for _ in range(4):
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    return bm


def to_object(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---- facets -------------------------------------------------------------------------------------------

MAG_C = np.array([0.0, -1.85, 2.30])    # the face: magnified while decimating, so it keeps finer facets
MAG_A = 1.7
MAG_S = 0.55


def _magnify(P, inverse=False):
    """A smooth radial magnification round MAG_C (r -> r * (1 + A exp(-r^2/s^2))), or its inverse."""
    Q = P - MAG_C
    r = np.linalg.norm(Q, axis=1)
    f = lambda x: x * (1 + MAG_A * np.exp(-(x / MAG_S) ** 2))
    if not inverse:
        r2 = f(r)
    else:
        lo, hi = np.zeros_like(r), r.copy()
        for _ in range(48):
            mid = (lo + hi) / 2
            big = f(mid) > r
            hi = np.where(big, mid, hi)
            lo = np.where(big, lo, mid)
        r2 = (lo + hi) / 2
    k = np.where(r > 1e-9, r2 / np.maximum(r, 1e-9), 1.0)
    return MAG_C + Q * k[:, None]


def facet(bm, target=FACETS):
    """Collapse the dense sculpt to large flat facets, symmetric in x. The face is magnified while the
    decimate runs, so its errors count for more and it keeps smaller facets."""
    co = np.array([v.co[:] for v in bm.verts])
    for v, p in zip(bm.verts, _magnify(co)):
        v.co = Vector(p)
    ob = to_object(bm, "facet_tmp")
    mod = ob.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = target / max(1, len(ob.data.polygons) * 2)
    mod.use_symmetry = True
    mod.symmetry_axis = 'X'
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    out = bmesh.new()
    out.from_mesh(ob.data)
    bpy.data.objects.remove(ob)
    co = np.array([v.co[:] for v in out.verts])
    for v, p in zip(out.verts, _magnify(co, inverse=True)):
        v.co = Vector(p)
    return clean(out)


def clean(src):
    """Rebuild a mesh face by face: the decimate and the plane cuts can leave doubled edges and faces (fins),
    which make later operations crash. Doubles are dropped, fins trimmed, the small holes left are filled.
    The face label layer is carried over."""
    bm = bmesh.new()
    lab_src = src.faces.layers.int.get("lab")
    lab = bm.faces.layers.int.new("lab") if lab_src is not None else None
    src.verts.index_update()
    vs = [bm.verts.new(v.co) for v in src.verts]
    for f in src.faces:
        ids = [v.index for v in f.verts]
        if len(set(ids)) < 3:
            continue
        try:
            nf = bm.faces.new([vs[i] for i in ids])
        except ValueError:
            continue
        if lab is not None:
            nf[lab] = f[lab_src]
    src.free()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for e in list(bm.edges):
        if e.is_valid and len(e.link_faces) > 2:
            extra = sorted(e.link_faces, key=lambda f: f.calc_area())[:len(e.link_faces) - 2]
            bmesh.ops.delete(bm, geom=extra, context='FACES')
    edge = [e for e in bm.edges if len(e.link_faces) == 1]
    if edge:
        bmesh.ops.remove_doubles(bm, verts=list(set(v for e in edge for v in e.verts)), dist=1e-4)
        edge = [e for e in bm.edges if len(e.link_faces) == 1]
    if edge:
        res = bmesh.ops.holes_fill(bm, edges=edge, sides=12)
        if lab is not None:
            for f in res["faces"]:
                nb = [g for e in f.edges for g in e.link_faces if g is not f]
                if nb:
                    f[lab] = nb[0][lab]
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    # any hole holes_fill left: walk its boundary loop and close it with one face
    left = set(e for e in bm.edges if len(e.link_faces) == 1)
    while left:
        e0 = left.pop()
        loop = [e0.verts[0], e0.verts[1]]
        while True:
            nxt = [e for e in loop[-1].link_edges if e in left]
            if not nxt:
                break
            e = nxt[0]
            left.discard(e)
            v = e.other_vert(loop[-1])
            if v is loop[0]:
                break
            loop.append(v)
        if len(loop) >= 3:
            try:
                nf = bm.faces.new(loop)
                if lab is not None:
                    nb = [g for ed in nf.edges for g in ed.link_faces if g is not nf]
                    if nb:
                        nf[lab] = nb[0][lab]
            except ValueError:
                pass
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    return bm


# ---- design: colour regions, plates, claws ---------------------------------------------------------------

BROWN = "#723A1A"
BROWN_DK = "#4F2915"
LEG = "#4F2915"
PLATE = "#56606A"
PLATE_EDGE = "#3A4148"
CREAM = "#EBCB98"
CREAM_DK = "#D9B47E"
CHAR = "#35302E"
CHAR_LT = "#4A4440"
NOSE = "#26201E"
SOCKET = "#2E1A10"
TEAL = "#3CF2E0"

COLOURS = {"body": BROWN, "brow": BROWN_DK, "plate": PLATE, "plate_side": PLATE_EDGE, "muzzle": CREAM,
           "chest": CREAM, "ear": CREAM_DK, "pad": CREAM, "paw": CHAR, "claw": CHAR_LT, "nose": NOSE,
           "socket": BROWN_DK, "leg": LEG}
ROUGH = {"body": 0.78, "brow": 0.78, "plate": 0.5, "plate_side": 0.55, "muzzle": 0.72, "chest": 0.72,
         "ear": 0.75, "pad": 0.72, "paw": 0.6, "claw": 0.45, "nose": 0.35, "socket": 0.7, "leg": 0.78}
NO_STUDS = {"nose", "socket", "claw", "plate_side"}
LABELS = sorted(COLOURS)

EYE_C = Vector((0.28, -1.93, 2.415))       # right eye centre (the left mirrors it), before posing
EYE_D = Vector((0.34, -0.93, 0.12)).normalized()

# Colour regions and plates are cut into the facets with planes, so every boundary is a straight crisp edge.
# Each: (label, half-spaces [(point, normal)] the region lies behind, a box (lo, hi) limiting the cuts,
#        mirrored to both sides?, lift (plates are raised off the form))
def _eye_planes():
    """An angular six-sided socket round the right eye, as half-spaces."""
    up = Vector((0, 0, 1))
    u = up.cross(EYE_D).normalized()
    if u.x < 0:
        u = -u
    v = EYE_D.cross(u).normalized()
    if v.z < 0:
        v = -v
    k = EYE_SCALE
    out = []
    for ang, dist in ((90, 0.075), (35, 0.13), (-30, 0.135), (-90, 0.075), (-150, 0.125), (150, 0.12)):
        a = math.radians(ang)
        n = u * math.cos(a) + v * math.sin(a)
        out.append((tuple(EYE_C + n * dist * k), tuple(n)))
    return out


# Each: (label, half-spaces [(point, normal)] the region lies behind, a box (lo, hi) limiting the cuts,
#        mirrored to both sides?, lift (plates are raised off the form), gem on it?)
REGIONS = [
    ("paw", [((0, 0, 0.30), (0, 0, 1))], ((-2, -3, -1), (2, 3, 0.5)), False, 0.0, False),
    ("muzzle", [((0, -1.86, 0), (0.42, 1, 0)), ((0, -1.86, 0), (-0.42, 1, 0)),
                ((0, -1.9, 2.30), (0, 0.25, 1)), ((0, 0, 1.78), (0, 0, -1))],
     ((-0.6, -2.6, 1.6), (0.6, -1.55, 2.5)), False, 0.0, False),
    ("nose", [((0, -2.17, 0), (0, 1, 0)), ((0, 0, 2.17), (0, 0, -1)), ((0.15, 0, 0), (1, 0, 0)),
              ((-0.15, 0, 0), (-1, 0, 0))], ((-0.4, -2.6, 1.9), (0.4, -1.9, 2.6)), False, 0.0, False),
    ("chest", [((0, -0.86, 0), (0, 1, 0)), ((0, 0, 0.98), (0.68, 0, -0.73)), ((0, 0, 1.30), (-0.68, 0, 0.73)),
               ((0.58, 0, 0), (1, 0, 0)), ((0.0, 0, 0), (-1, 0, 0))],
     ((-0.001, -1.7, 0.6), (0.8, -0.6, 2.0)), True, 0.0, False),
    # shoulder pauldron: a shield over the shoulder, pointing down
    ("ear", [], ((-0.75, -1.6, 2.6), (0.75, -1.1, 3.2)), False, 0.0, False),
    ("plate", [((0.60, 0, 0), (-1, 0, 0)), ((0, 0, 1.86), (0, 0.35, 1)), ((0, 0, 1.12), (0, 0, -1)),
               ((0, -1.00, 0), (0, -1, 0)), ((0, -0.30, 0), (0, 1, 0)),
               ((0, -0.86, 1.36), (0, -0.7, -0.7)), ((0, -0.44, 1.36), (0, 0.7, -0.7))],
     ((0.45, -1.3, 0.8), (1.3, 0.0, 2.1)), True, PLATE_T, True),
    # haunch plate
    ("plate", [((0.58, 0, 0), (-1, 0, 0)), ((0, 0, 1.52), (0, -0.3, 1)), ((0, 0, 0.92), (0, 0, -1)),
               ((0, 0.45, 0), (0, -1, 0)), ((0, 1.10, 0), (0, 1, 0)),
               ((0, 0.58, 1.05), (0, -0.7, -0.7)), ((0, 0.98, 1.05), (0, 0.7, -0.7))],
     ((0.40, 0.2, 0.6), (1.3, 1.5, 1.8)), True, PLATE_T, False),
]

def _inner_ear(f):
    c = f.calc_center_median()
    p = Pts(np.array([abs(c.x)]), np.array([c.y]), np.array([c.z]))
    return ellipsoid(p, (0.50, -1.38, 2.88), (0.15, 0.08, 0.15), (0, -25, 0))[0] < 0 and f.normal.y < -0.1


PREDICATES = {"ear": _inner_ear}

GEMS = []    # (centre, normal) of each plate that carries a glowing gem


def ensure_layers(bm):
    return bm.faces.layers.int.get("lab") or bm.faces.layers.int.new("lab")


def _mirror(planes, box, sx):
    if sx > 0:
        return planes, box
    pl = [((-c[0], c[1], c[2]), (-n[0], n[1], n[2])) for c, n in planes]
    (lx, ly, lz), (hx, hy, hz) = box
    return pl, ((-hx, ly, lz), (-lx, hy, hz))


def _in_box(p, box):
    lo, hi = box
    return all(lo[i] <= p[i] <= hi[i] for i in range(3))


def _behind(p, planes, eps=1e-5):
    return all((p - Vector(c)).dot(Vector(n)) <= eps for c, n in planes)


def cut_regions(bm):
    """Cut each region's outline into the facets, label the faces inside, lift the plates."""
    lab = ensure_layers(bm)
    for f in bm.faces:
        f[lab] = LABELS.index("body")
    for name, planes, box, mirror, lift, gem in REGIONS:
        for sx in ((1, -1) if mirror else (1,)):
            pl, bx = _mirror(planes, box, sx)
            for c, n in pl:
                faces = [f for f in bm.faces if _in_box(f.calc_center_median(), bx)]
                if not faces:
                    continue
                geom = list(set(v for f in faces for v in f.verts)) + list(set(e for f in faces for e in f.edges)) + faces
                bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=Vector(c), plane_no=Vector(n).normalized())
            inside = [f for f in bm.faces if _in_box(f.calc_center_median(), bx) and _behind(f.calc_center_median(), pl)]
            if name in PREDICATES:
                inside = [f for f in inside if PREDICATES[name](f)]
            if lift > 0:
                inside = [f for f in inside if LABELS[f[lab]] == "body"]
                res = lift_plate(bm, inside, lift)
                if gem and res:
                    GEMS.append(res)
            else:
                for f in inside:
                    f[lab] = LABELS.index(name)
    bm.normal_update()


def lift_plate(bm, faces, thick):
    """Raise a patch of facets off the form: the faces are extruded out along their mean normal; the walls
    are labelled plate_side."""
    lab = ensure_layers(bm)
    if len(faces) < 2:
        return None
    bm.normal_update()
    nrm = sum((f.normal * f.calc_area() for f in faces), Vector()).normalized()
    area = sum(f.calc_area() for f in faces)
    cen = sum((f.calc_center_median() * f.calc_area() for f in faces), Vector()) / area
    res = bmesh.ops.extrude_face_region(bm, geom=faces)
    new_verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    nv = set(new_verts)
    for v in new_verts:
        v.co += nrm * thick
    for f in (g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)):
        f[lab] = LABELS.index("plate" if all(v in nv for v in f.verts) else "plate_side")
    # the original faces under the plate are left behind by the extrude: remove them
    bmesh.ops.delete(bm, geom=[f for f in faces if f.is_valid], context='FACES')
    loose = [e for e in bm.edges if not e.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='EDGES')
    lv = [v for v in bm.verts if not v.link_faces]
    if lv:
        bmesh.ops.delete(bm, geom=lv, context='VERTS')
    return cen + nrm * thick, nrm


def hull_bm(pts):
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def merge_into(dst, src, label):
    """Append the bmesh `src` into `dst` with every face given `label`."""
    lab = ensure_layers(dst)
    m = {}
    for v in src.verts:
        m[v] = dst.verts.new(v.co)
    for f in src.faces:
        try:
            nf = dst.faces.new([m[v] for v in f.verts])
            nf[lab] = LABELS.index(label)
        except ValueError:
            pass
    src.free()


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


def add_claws(bm):
    for sx in (-1, 1):
        for (c, half), n, rr, L in ((FPAW, 4, 0.10, 0.14), (HPAW, 4, 0.085, 0.11)):
            for i in range(n):
                x = c[0] + (i - (n - 1) / 2) * (2 * half[0] - 2 * rr) / (n - 1)
                yb = c[1] - half[1] + rr * 0.1
                splay = (x - c[0]) * 0.5
                merge_into(bm, claw((sx * x, yb, 0.10), (sx * splay, -1, 0), w=rr * 0.75, L=L), "claw")


# ---- glow: eyes and ore crystals ------------------------------------------------------------------------

class Ray:
    def __init__(self, bm):
        bm.verts.index_update()
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, origin, d):
        loc, nrm, idx, dist = self.bvh.ray_cast(Vector(origin), Vector(d).normalized(), 20.0)
        return loc, nrm


# calm, confident almond: a nearly level top that rises a touch to the outer corner, a fuller lower curve
EYE_SHAPE = [(-0.12, 0.004), (-0.075, 0.052), (0.0, 0.074), (0.08, 0.068), (0.15, 0.032), (0.09, -0.027),
             (0.0, -0.045), (-0.075, -0.034)]


def build_eyes(glow, ray):
    up = Vector((0, 0, 1))
    for sx in (1, -1):
        c = Vector((EYE_C.x * sx, EYE_C.y, EYE_C.z))
        d = Vector((EYE_D.x * sx, EYE_D.y, EYE_D.z))
        u = up.cross(d).normalized() * -sx     # towards the outer corner
        if u.x * sx < 0:
            u = -u
        v = d.cross(u).normalized()
        if v.z < 0:
            v = -v
        cn, dn, un, vn = eye_frame(sx)
        c, d, u, v = Vector(cn), Vector(dn), Vector(un), Vector(vn)
        # a lens of two rings and a centre, each point laid on the socket floor along the view direction
        rings = []
        for f in (1.0, 0.55):
            ring = []
            for a, b in eye_outline(LENS_PAD):
                p = c + (u * a + v * b) * f
                loc, _ = ray.hit(p + d * 0.6, -d)
                ring.append((loc if loc is not None else p) + d * 0.010)
            rings.append(ring)
        loc, _ = ray.hit(c + d * 0.6, -d)
        cen = (loc if loc is not None else c) + d * 0.010
        outer, inner = rings
        k = len(outer)
        vo = [glow.verts.new(p) for p in outer]
        vi = [glow.verts.new(p) for p in inner]
        vb = [glow.verts.new(p - d * 0.05) for p in outer]
        vc = glow.verts.new(cen)
        for i in range(k):
            j = (i + 1) % k
            glow.faces.new((vo[i], vo[j], vi[j], vi[i]))
            glow.faces.new((vi[i], vi[j], vc))
            glow.faces.new((vb[i], vb[j], vo[j], vo[i]))
    bmesh.ops.recalc_face_normals(glow, faces=glow.faces[:])


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


CLUSTERS = [  # (centre on the hump, lean, [(offset u, offset v, radius, height, tilt)])
    ((-0.26, -0.38, 2.5), (-0.35, 0.1, 1.0),
     [(0.0, 0.0, 0.15, 0.72, 0.0), (0.16, 0.09, 0.11, 0.48, 0.45), (-0.15, 0.07, 0.10, 0.44, -0.5),
      (0.03, -0.17, 0.095, 0.36, 0.35), (-0.05, 0.19, 0.08, 0.28, -0.2)]),
    ((0.30, -0.20, 2.45), (0.4, 0.15, 1.0),
     [(0.0, 0.0, 0.13, 0.58, 0.0), (0.15, -0.07, 0.095, 0.38, 0.5), (-0.10, 0.13, 0.09, 0.33, -0.45)]),
]


def build_gems(glow, ray):
    """A flat glowing diamond set into each gem-carrying plate."""
    for cen, nrm in GEMS:
        loc, n2 = ray.hit(cen + nrm * 0.4, -nrm)
        if loc is None:
            continue
        up = Vector((0, 0, 1))
        t = (up - n2 * n2.dot(up)).normalized()
        sdir = n2.cross(t)
        h, w = 0.13, 0.085
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


# ---- pose ---------------------------------------------------------------------------------------------

def _ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def pose_points(P):
    """Head raised a little and turned towards the viewer's side (-X), the left front paw a step forward."""
    P = P.copy()
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    w = _ss(-0.88, -1.30, y) * _ss(1.30, 1.75, z)
    piv = np.array([0.0, -0.95, 1.85])
    Q = P - piv
    pitch = np.radians(HEAD_PITCH) * w
    yaw = np.radians(HEAD_YAW) * w
    # raise (about x), then turn (about z)
    cy_, sy_ = np.cos(pitch), np.sin(pitch)
    qy = Q[:, 1] * cy_ - Q[:, 2] * sy_
    qz = Q[:, 1] * sy_ + Q[:, 2] * cy_
    qx = Q[:, 0]
    roll = np.radians(HEAD_ROLL) * w
    cr_, sr_ = np.cos(roll), np.sin(roll)
    qx, qz = qx * cr_ - qz * sr_, qx * sr_ + qz * cr_
    cz_, sz_ = np.cos(yaw), np.sin(yaw)
    rx = qx * cz_ - qy * sz_
    ry = qx * sz_ + qy * cz_
    P = np.stack([rx, ry, qz], 1) + piv
    wp = _ss(-0.32, -0.52, x) * _ss(-0.15, -0.45, y) * _ss(1.35, 0.55, z)
    P[:, 1] -= PAW_STEP * wp
    return P


def pose_bm(bm):
    co = np.array([v.co[:] for v in bm.verts])
    if len(co) == 0:
        return
    P = pose_points(co)
    for v, p in zip(bm.verts, P):
        v.co = Vector(p)
    bm.normal_update()


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


# ---- build ---------------------------------------------------------------------------------------------

def build():
    """Sculpt, facet, paint, plates, claws, glow, pose, scale. Returns (body bmesh, glow bmesh, scale)."""
    import time
    t0 = time.time()
    dense = sculpt()
    print("sculpt: %d faces (%.1fs)" % (len(dense.faces), time.time() - t0))
    bm = facet(dense)
    dense.free()
    print("facets: %d triangles" % len(bm.faces))
    cut_regions(bm)
    bm = clean(bm)
    add_claws(bm)
    glow = bmesh.new()
    ray = Ray(bm)
    build_eyes(glow, ray)
    build_crystals(glow, ray)
    build_gems(glow, ray)
    pose_bm(bm)
    pose_bm(glow)
    zs = [v.co.z for v in bm.verts] + [v.co.z for v in glow.verts]
    k = TARGET_HEIGHT / max(zs)
    for b in (bm, glow):
        b.transform(Matrix.Scale(k, 4))
        b.normal_update()
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    if BEVEL > 0:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.normal_update()
        lab = bm.faces.layers.int["lab"]
        claw_i = LABELS.index("claw")
        bad = set(v for e in bm.edges if len(e.link_faces) != 2 for v in e.verts)
        bad |= set(v for v in bm.verts if not v.is_manifold)
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_length() > BEVEL * 2.5
                 and not any(v in bad for v in e.verts)
                 and all(f[lab] != claw_i and f.calc_area() > 1e-6 for f in e.link_faces)
                 and math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)) > BEVEL_ANGLE]
        bmesh.ops.bevel(bm, geom=edges, offset=BEVEL, offset_type='OFFSET', segments=1, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.normal_update()
    return bm, glow, k


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
         ("face 3/4", "full"), ("face front", "full"), ("close-up", "full"), ("game distance", "full"),
         ("front 3/4", "clay"), ("game distance", "silhouette"), ("front 3/4", "studio")]


def review(rig, out, px, title, normal_link):
    from PIL import Image
    folder = os.path.splitext(out)[0] + "_views"
    os.makedirs(folder, exist_ok=True)
    tiles = []
    for view, look in SHOTS:
        p = os.path.join(folder, "%s_%s.png" % (view.replace(" ", "").replace("/", ""), look))
        rig.render(p, view, look, px, normal_link)
        label = "%s, %s" % (view, look) if look != "studio" else "Studio-like: colour map only, no normal map"
        tiles.append((Image.open(p).convert("RGB"), label))
    tiles += ref_tiles(px)
    contact(out, tiles, px, 4, title)


def style_compare(rig, out, px=900, normal_link=None):
    """Crops of the reference pets beside a large hero render and the face close-up."""
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
    d.text((W + 24, 20), "Stud Bear (Mine an Egg) - hero render", fill=(235, 235, 235))
    f = Image.open(face).convert("RGB").resize((px // 2, px // 2), Image.LANCZOS)
    sheet.paste(f, (W + px + 30, 60))
    d.text((W + px + 34, 20), "face close-up", fill=(235, 235, 235))
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
    ap.add_argument("--title", default="Stud Bear review")
    ap.add_argument("--texdir", default=os.path.join(HERE, "..", "..", "export", "style_test"))
    a = ap.parse_args()
    kit.fresh()
    bm, glow, k = build()
    body, g, frames, rid_of_face = make_objects(bm, glow)
    head = Vector(pose_points(np.array([[0.0, -1.75, 2.35]]))[0]) * k
    if a.peek:
        body.data.materials.append(peek_material())
        stats([body, g])
        rig = SunRig([body, g], head, samples=16)
        from PIL import Image
        folder = os.path.splitext(os.path.abspath(a.peek))[0] + "_views"
        os.makedirs(folder, exist_ok=True)
        tiles = []
        for view, look in (("hero", "full"), ("face front", "full"), ("face 3/4", "full"), ("front 3/4", "clay")):
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
