"""Penguin pet: a hand-whittled, hand-painted folk-art wooden figure, built from scratch by script.

    python models/pets/penguin.py --review out/penguin.png      # render the review sheet
    python models/pets/penguin.py --export models/export/penguin.fbx

Style: a small penguin a craftsman whittled from one block of pale lime wood and painted with thin
milk paint. Must-haves, checked every review:
  1. Carved, not moulded: every form is made of broad, slightly hollow knife planes that meet in
     crisp ridges, with rows of shallow gouge scallops on the back, the flippers and the hat. The
     cuts vary in size; only the belly and the face are sanded softer.
  2. Thin paint on wood: deep navy back, cream front, ochre beak and feet, a brick-red hat with a
     cream band and pom-pom. The grain shows through, the paint is rubbed off the ridges and high
     spots down to warm bare wood, there is grime in the cuts and a few dents.
  3. A simple friendly face: small glossy dark bead eyes set in drilled sockets with a painted
     cream ring, a carved wedge beak with a cut line, no blush circles, no smile.
  4. Character in the pose: it stands on carved webbed feet on the round base it was cut with,
     leans back a little and turns and tilts its head.
  5. Clearly not the unicorn: hollow, varied cuts and gouge texture, never even flat facets.

How it is made: each part is a dense smooth form, then "carved" by subtracting knife and gouge
cutters from it (numpy). That high-detail carving is decimated to the triangle budget for the game
mesh, and everything the decimation loses (gouges, ridges, wear, grime, paint borders) is baked from
the high-detail carving into the colour texture.
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import Prop  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

TARGET_TRIS = 7300          # the carved body after decimation; the eyes add about 200
BASE_TOP = 0.19             # top of the round base
YAW, ROLL, LEAN = -17.0, 6.0, 4.0    # head turn (towards -X), head tilt, lean back (degrees)
NECK = np.array([0.0, 0.03, 1.95])

PID = dict(body=0, wing=1, tail=2, foot=3, beak=4, crown=5, band=6, pom=7, base=8)


def say(*a):
    print("[penguin]", *a, flush=True)


# ---- small maths ------------------------------------------------------------------------------------

def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def rot(axis, ang):
    """Rotation matrix about `axis` by `ang` radians."""
    a = unit(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def euler(rx, ry, rz):
    """Degrees, applied X then Y then Z (Blender's XYZ order)."""
    return rot((0, 0, 1), math.radians(rz)) @ rot((0, 1, 0), math.radians(ry)) @ rot((1, 0, 0), math.radians(rx))


def tangent(v, n):
    t = np.asarray(v, float) - n * np.dot(v, n)
    if np.linalg.norm(t) < 1e-6:
        t = np.cross(n, (1.0, 0.0, 0.0))
    return unit(t)


def sgnpow(v, p):
    return np.sign(v) * np.abs(v) ** p


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def table(rows):
    """A smooth curve through rows (first column increasing): returns f(x) -> other columns."""
    rows = np.asarray(rows, float)
    t = np.linspace(0, len(rows) - 1, 600)
    fine = np.array([[kit._spline(list(rows[:, k]), ti) for k in range(rows.shape[1])] for ti in t])

    def f(x):
        return np.array([np.interp(x, fine[:, 0], fine[:, k]) for k in range(1, rows.shape[1])])
    return f


# ---- value noise in numpy (for paint, grain and wear, worked out per texel) ---------------------------

def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761 + 12345)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def vnoise(P, seed=0):
    P = np.asarray(P, float)
    i = np.floor(P)
    f = P - i
    i = i.astype(np.int64)
    u = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                out = out + wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, octaves=3, seed=0):
    """Fractal noise, about -0.5 to 0.5."""
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * (vnoise(P * 2.03 ** o, seed + 17 * o) - 0.5)
        norm += amp
        amp *= 0.5
    return tot / norm


# ---- dense smooth forms -----------------------------------------------------------------------------

def loft(rings, cap0=True, cap1=True, closed=False):
    """A skin over rings of points (all rings the same count). Returns vertices and triangles,
    oriented outwards. Vertex r*S + s is point s of ring r."""
    rings = [np.asarray(r, float) for r in rings]
    R, S = len(rings), len(rings[0])
    V = np.concatenate(rings)
    rr, ss = np.meshgrid(np.arange(R if closed else R - 1), np.arange(S), indexing='ij')
    rr, ss = rr.ravel(), ss.ravel()
    r2, s2 = (rr + 1) % R, (ss + 1) % S
    a, b, c, d = rr * S + ss, rr * S + s2, r2 * S + s2, r2 * S + ss
    T = [np.stack([a, b, c], 1), np.stack([a, c, d], 1)]
    s = np.arange(S)
    if cap0 and not closed:
        T.append(np.stack([np.full(S, len(V)), (s + 1) % S, s], 1))
        V = np.vstack([V, rings[0].mean(0)])
    if cap1 and not closed:
        T.append(np.stack([np.full(S, len(V)), (R - 1) * S + s, (R - 1) * S + (s + 1) % S], 1))
        V = np.vstack([V, rings[-1].mean(0)])
    T = np.concatenate(T)
    vol = np.einsum('ij,ij->i', V[T[:, 0]], np.cross(V[T[:, 1]], V[T[:, 2]])).sum()
    if vol < 0:
        T = T[:, [0, 2, 1]]
    return V, T


class Part:
    """One carved piece: dense vertices and triangles plus the per-vertex data the paint needs."""

    def __init__(self, name, V, T, pid, grid=None, wear=0.0):
        self.name, self.V, self.T, self.pid, self.grid = name, np.array(V, float), np.array(T, np.int64), pid, grid
        n = len(self.V)
        self.bias, self.dent, self.sand = np.full(n, float(wear)), np.zeros(n), np.zeros(n)
        self.rest = None
        self._e = None

    def normals(self):
        V, T = self.V, self.T
        fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        n = len(V)
        vn = np.stack([sum(np.bincount(T[:, k], fn[:, c], n) for k in range(3)) for c in range(3)], 1)
        return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)

    def edges(self):
        if self._e is None:
            T = self.T
            e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
            self._e = np.unique(e, axis=0)
        return self._e

    def average(self, X):
        e, n = self.edges(), len(self.V)
        deg = np.maximum(np.bincount(e[:, 0], minlength=n) + np.bincount(e[:, 1], minlength=n), 1)
        if X.ndim == 1:
            return (np.bincount(e[:, 0], X[e[:, 1]], n) + np.bincount(e[:, 1], X[e[:, 0]], n)) / deg
        return np.stack([self.average(X[:, c]) for c in range(X.shape[1])], 1)

    def smooth(self, w, iters=1):
        """Taubin smoothing (does not shrink), `w` per vertex: sanding."""
        w = np.broadcast_to(np.asarray(w, float), (len(self.V),))[:, None]
        for _ in range(iters):
            self.V = self.V + (self.average(self.V) - self.V) * 0.5 * w
            self.V = self.V + (self.average(self.V) - self.V) * -0.53 * w

    def move(self, R=None, t=(0, 0, 0)):
        if R is not None:
            self.V = self.V @ np.asarray(R).T
        self.V = self.V + np.asarray(t, float)


# ---- carving ---------------------------------------------------------------------------------------

class Cut:
    """A cutter pressed into the wood at p along -n. Its bottom is a paraboloid: hollow along the
    stroke t (radius rt0 before the deepest point, rt1 after it) and across it (rb). d is how deep it
    goes at p. A knife plane is a nearly flat, wide cutter; a gouge is narrow across."""
    __slots__ = ("p", "n", "t", "b", "d", "rt0", "rt1", "rb", "reach2")

    def __init__(self, p, n, t, d, rt0, rt1=None, rb=None):
        self.p, self.n = np.asarray(p, float), unit(n)
        self.t = tangent(t, self.n)
        self.b = np.cross(self.n, self.t)
        self.d, self.rt0, self.rt1 = d, rt0, rt1 or rt0
        self.rb = rb or rt0
        reach = 1.7 * math.sqrt(2 * d * max(self.rt0, self.rt1, self.rb)) + 0.02
        self.reach2 = reach * reach


def removal(V, N, cuts, nmin=0.25):
    """How deep the union of the cutters reaches below each vertex, measured along its normal."""
    disp = np.zeros(len(V))
    for c in cuts:
        rel = V - c.p
        idx = np.flatnonzero(np.einsum('ij,ij->i', rel, rel) < c.reach2)
        if idx.size == 0:
            continue
        r = rel[idx]
        x, y, h = r @ c.t, r @ c.b, r @ c.n
        cosn = N[idx] @ c.n
        rt = np.where(x < 0, c.rt0, c.rt1)
        zc = -c.d + x * x / (2 * rt) + y * y / (2 * c.rb)
        rem = (h - zc) / np.maximum(cosn, 0.5)
        # a blade only reaches so far: on hollow surfaces it must not run on and gouge the walls
        ell = np.sqrt(x * x / (2.6 * c.d * rt) + y * y / (2.6 * c.d * c.rb))
        rem = np.minimum(rem, (1.5 * c.d + 0.003) * (1 - smoothstep(0.75, 1.0, ell)))
        rem[(cosn < nmin) | (rem < 0)] = 0.0
        disp[idx] = np.maximum(disp[idx], rem)
    return disp


def apply_cuts(part, cuts):
    N = part.normals()
    disp = removal(part.V, N, cuts)
    part.V = part.V - N * disp[:, None]
    return disp


def sample_sites(V, N, spacing, stroke, rng, idx=None, aspect=1.4, limit=7000):
    """Poisson-disc sites on the vertices, closer along the stroke direction than across it is
    `aspect` times the spacing. spacing(p) gives the local cut size."""
    idx = np.arange(len(V)) if idx is None else np.asarray(idx)
    idx = rng.permutation(idx)[:limit]
    sp = spacing(V[idx]) if callable(spacing) else np.full(len(idx), float(spacing))
    cell = float(sp.max()) * aspect
    grid, sites = {}, []
    for i, s in zip(idx, sp):
        p = V[i]
        t = stroke(p, N[i])
        key = tuple((p // cell).astype(int))
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        q, sj, tj, _ = sites[j]
                        d = p - q
                        al = d @ tj
                        ss = 0.5 * (s + sj)
                        if al * al / (aspect * ss) ** 2 + (d @ d - al * al) / ss ** 2 < 1.0:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault(key, []).append(len(sites))
            sites.append((p.copy(), s, t, N[i].copy()))
    return sites


def knife(part, spacing, stroke, rng, aspect=1.4, curv=1.0, rt=(2.4, 4.5), rb=(6.0, 14.0), tilt=7.0,
          swing=14.0, cov=0.65, mask=None, dmax=0.12):
    """Rough the part out with knife planes: wide, slightly hollow cuts of varied size that meet in
    crisp ridges. Gaps the first pass leaves get smaller clean-up cuts."""
    N = part.normals()
    idx = np.flatnonzero(mask) if mask is not None else None

    def cuts_for(sites, shrink=1.0):
        out = []
        for p, s, t, n in sites:
            s = s * shrink
            t = rot(n, math.radians(rng.normal(0, swing))) @ t
            n2 = rot(tangent(rng.normal(size=3), n), math.radians(rng.normal(0, tilt))) @ n
            r_t, r_b = rng.uniform(*rt), rng.uniform(*rb)
            d = 0.5 * (cov * aspect * s) ** 2 * (curv + 1.0 / r_t) * rng.uniform(0.85, 1.25)
            out.append(Cut(p, n2, t, min(max(d, 0.004), dmax), r_t, r_t, r_b))
        return out

    cuts = cuts_for(sample_sites(part.V, N, spacing, stroke, rng, idx, aspect))
    disp = removal(part.V, N, cuts)
    for k in range(3):                                   # clean-up cuts where the wood was missed
        miss = disp <= 1e-6
        if mask is not None:
            miss &= mask
        if miss.sum() < 4:
            break
        extra = cuts_for(sample_sites(part.V, N, spacing, stroke, rng, np.flatnonzero(miss), aspect), 0.6)
        disp = np.maximum(disp, removal(part.V, N, extra))
        cuts += extra
    part.V = part.V - N * disp[:, None]
    return len(cuts)


def gouges(part, spots, rng, d=(0.016, 0.026), rb=(0.065, 0.09), rt_in=0.9, rt_out=0.12, swing=10.0):
    """Gouge scallops: narrow hollow strokes that start gently and end in a crisp wall.
    spots: (vertex index, stroke direction) pairs."""
    N = part.normals()
    cuts = []
    for i, t in spots:
        n = N[i]
        t = rot(n, math.radians(rng.normal(0, swing))) @ tangent(t, n)
        cuts.append(Cut(part.V[i], n, t, rng.uniform(*d), rt_in * rng.uniform(0.8, 1.2), rt_out * rng.uniform(0.8, 1.2), rng.uniform(*rb)))
    apply_cuts(part, cuts)
    return len(cuts)


def lattice(grid, rows, row_step, col_len, ring_len, keep, rng, jitter=0.3):
    """Staggered rows of spots on a lofted part's (ring, segment) grid. col_len(r) is the length of
    one segment step on ring r, so spots keep about `ring_len` apart round every ring."""
    R, S = grid
    out = []
    for k, r in enumerate(range(rows[0], rows[1], row_step)):
        step = max(2, int(round(ring_len / max(col_len(r), 1e-4))))
        off = (step // 2) * (k % 2)
        for s in range(off, S, step):
            rj = int(np.clip(r + round(rng.normal(0, jitter * row_step * 0.5)), 0, R - 1))
            sj = int(s + round(rng.normal(0, jitter * step * 0.5))) % S
            if keep(rj, sj):
                out.append(rj * S + sj)
    return out


# ---- the parts --------------------------------------------------------------------------------------

BODY = table([  # z, half width, front depth, back depth, centre y
    (0.12, 0.46, 0.42, 0.46, 0.06),
    (0.24, 0.66, 0.60, 0.62, 0.05),
    (0.42, 0.82, 0.76, 0.71, 0.04),
    (0.72, 0.90, 0.84, 0.74, 0.03),
    (1.02, 0.88, 0.82, 0.73, 0.03),
    (1.32, 0.81, 0.75, 0.68, 0.04),
    (1.60, 0.70, 0.65, 0.61, 0.05),
    (1.85, 0.62, 0.59, 0.56, 0.05),
    (2.05, 0.63, 0.61, 0.57, 0.03),
    (2.25, 0.64, 0.62, 0.59, 0.02),
    (2.45, 0.56, 0.54, 0.55, 0.03),
    (2.64, 0.42, 0.40, 0.42, 0.04),
])
BODY_SEG, BODY_DZ, BODY_E = 256, 0.016, 2.3


def body_point(z, a):
    W, Df, Db, yc = BODY(z)
    c, s = np.cos(a), np.sin(a)
    return np.stack([W * sgnpow(c, 2 / BODY_E) + 0 * a, yc + np.where(s < 0, Df, Db) * sgnpow(s, 2 / BODY_E), np.full_like(a, z)], -1)


def make_body():
    zs = np.arange(0.12, 2.64 + 1e-9, BODY_DZ)
    a = np.linspace(0, 2 * math.pi, BODY_SEG, endpoint=False)
    V, T = loft([body_point(z, a) for z in zs])
    return Part("body", V, T, PID["body"], grid=(len(zs), BODY_SEG)), zs


def front_angle(P):
    """Angle round the body from the front centre line, in radians, for rest-frame points."""
    yc = BODY(P[:, 2])[3]
    return np.arctan2(P[:, 0], -(P[:, 1] - yc))


BELLY_TOP = 1.98


def belly_edge(P):
    """Half-angle of the cream belly at the height of each rest-frame point (before wobble)."""
    z = P[:, 2]
    return 0.98 * np.sqrt(np.clip((BELLY_TOP - z) / 0.42, 0.0, 1.0))


def make_wing(side, rng):
    """A flipper: a thin paddle, built hanging from its root at the origin along -Z, then set into
    the body side in relief so only its outer half stands proud."""
    prof = table([(0.0, 0.40, 0.19), (0.15, 0.50, 0.19), (0.45, 0.54, 0.17), (0.72, 0.45, 0.14),
                  (0.90, 0.29, 0.10), (1.0, 0.07, 0.05)])
    S, L = 64, 1.12
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    ts = np.linspace(0, 1, 58)
    rings = []
    for t in ts:
        w, th = prof(t)
        rings.append(np.stack([th / 2 * sgnpow(np.cos(a), 0.8) - 0.03 * math.sin(math.pi * t),
                               w / 2 * sgnpow(np.sin(a), 0.9) + 0.08 * t * t,
                               np.full(S, -L * t)], 1))
    V, T = loft(rings)
    part = Part("wing", V, T, PID["wing"], grid=(len(ts), S))
    part.bias += np.clip((-part.V[:, 2] / L - 0.75) * 1.2, 0, 0.3)          # the tips rub most
    N = part.normals()
    knife(part, 0.16, lambda p, n: tangent((0, 0, -1), n), rng, aspect=1.6, curv=0.4, rt=(1.6, 3.0), cov=0.7)
    outer = lambda r, s: math.cos(2 * math.pi * s / S) > 0.15 and 3 < r < len(ts) - 4
    spots = lattice(part.grid, (4, len(ts) - 3), 4, lambda r: 1.2 / S, 0.1, outer, rng)
    gouges(part, [(i, (0, 0, -1)) for i in spots], rng, d=(0.014, 0.022), rb=(0.05, 0.07), rt_in=0.7, rt_out=0.1)
    part.smooth(0.25, 1)
    # place: root at the shoulder, hanging along the body side, tip a little out and back
    sx = 1 if side > 0 else -1
    U = -unit((0.33 * sx, 0.12, -0.94))
    O = unit(np.array((sx, 0.0, 0.0)) - U * U[0] * sx)
    Y = np.cross(U, O)
    R = np.stack([O, Y, U], 1)
    part.move(R, (0.70 * sx, 0.07, 1.58))
    return part


def make_tail(rng):
    S = 40
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    rings = []
    for t in np.linspace(0, 1, 16):
        w, th = 0.38 * (1 - 0.7 * t), 0.13 * (1 - 0.55 * t)
        c = np.array((0, 0.52 + 0.42 * t, 0.40 - 0.18 * t - 0.05 * t * t))
        rings.append(c + np.stack([w / 2 * sgnpow(np.cos(a), 0.8), np.zeros(S), th / 2 * sgnpow(np.sin(a), 0.8)], 1))
    V, T = loft(rings)
    part = Part("tail", V, T, PID["tail"], wear=0.1)
    knife(part, 0.1, lambda p, n: tangent((0, 1, -0.3), n), rng, aspect=1.5, curv=2.0, rt=(1.5, 3.0))
    return part


def make_foot(side, rng):
    """A webbed foot built along -Y from the heel, flat underneath, three toes with grooves."""
    prof = table([(0.0, 0.22, 0.15), (0.35, 0.30, 0.15), (0.7, 0.40, 0.11), (1.0, 0.44, 0.07)])
    S, L = 72, 0.72
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    ts = np.linspace(0, 1, 40)
    rings = []
    for t in ts:
        w, h = prof(t)
        x = w / 2 * sgnpow(np.cos(a), 0.6)
        z = h * np.clip(np.sin(a), -0.08, None) ** 1.0
        z = np.where(np.sin(a) > 0, h * sgnpow(np.sin(a), 0.75), 0.06 * h * np.sin(a))
        y = np.full(S, -L * t)
        if t > 0.7:                                       # scalloped toe front: notches between three toes
            u = x / (w / 2)
            y = y + 0.07 * ((t - 0.7) / 0.3) ** 1.5 * np.exp(-((np.abs(u) - 0.36) / 0.13) ** 2)
        rings.append(np.stack([x, y, z], 1))
    V, T = loft(rings)
    part = Part("foot", V, T, PID["foot"], grid=(len(ts), S))
    part.bias += np.clip((-part.V[:, 1] / L - 0.75) * 1.0, 0, 0.25)
    knife(part, 0.12, lambda p, n: tangent((0, -1, 0), n), rng, aspect=1.5, curv=1.5, rt=(1.5, 3.0), cov=0.7)
    N = part.normals()
    cuts = []
    for u in (-0.36, 0.36):                               # webbing grooves along the toes
        for t in np.linspace(0.5, 0.97, 9):
            w, h = prof(t)
            p = np.array((u * w / 2, -L * t, h * 0.92))
            i = int(np.argmin(np.linalg.norm(part.V - p, axis=1)))
            cuts.append(Cut(part.V[i], N[i], (0, -1, 0), 0.022, 0.25, 0.25, 0.012))
    apply_cuts(part, cuts)
    part.smooth(0.3, 1)
    sx = 1 if side > 0 else -1
    part.move(euler(0, 0, 19 * sx), (0.30 * sx, -0.12, BASE_TOP - 0.012))
    return part


def make_beak(rng):
    """A carved wedge, built pointing along -Y from its root (buried in the face) at the origin."""
    S, L = 56, 0.46
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    ts = np.linspace(0, 1, 34)
    prof = table([(0.0, 0.34, 0.24), (0.25, 0.32, 0.22), (0.55, 0.21, 0.15), (0.85, 0.09, 0.075), (1.0, 0.03, 0.035)])
    rings = []
    for t in ts:
        w, h = prof(t)
        s = np.sin(a)
        z = np.where(s > 0, 0.56 * h * sgnpow(s, 0.8), 0.44 * h * sgnpow(s, 0.8)) - 0.035 * t * t
        rings.append(np.stack([w / 2 * sgnpow(np.cos(a), 0.75), np.full(S, 0.12 - L * t), z], 1))
    V, T = loft(rings)
    part = Part("beak", V, T, PID["beak"], grid=(len(ts), S))
    part.bias += np.clip((-part.V[:, 1] - 0.18) * 1.4, 0, 0.3)
    knife(part, 0.085, lambda p, n: tangent((0, -1, 0), n), rng, aspect=1.5, curv=4.0, rt=(1.0, 2.0), rb=(3.0, 6.0), cov=0.7)
    N = part.normals()
    cuts = []
    mouth = int(round(-0.1 / (2 * math.pi) * S)) % S          # the cut line, a little below the side
    for side_s in (mouth, (S // 2 - mouth) % S):
        for r in range(8, len(ts) - 2, 2):
            i = r * S + side_s
            cuts.append(Cut(part.V[i], N[i], part.V[i + S] - part.V[i], 0.017, 0.3, 0.3, 0.01))
    tip = len(ts) - 2
    cuts.append(Cut(part.V[tip * S + S // 4 * 3], (0, -1, 0), (1, 0, 0), 0.012, 0.3, 0.3, 0.01))
    apply_cuts(part, cuts)
    part.smooth(0.25, 1)
    return part


def make_hat(rng):
    """Crown, band and pom-pom in the hat's own frame: brim centre at the origin."""
    parts = []
    S = 168
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    prof = table([(0.0, 0.645, 0.0), (0.25, 0.635, 0.20), (0.5, 0.57, 0.42), (0.72, 0.45, 0.60),
                  (0.88, 0.30, 0.72), (1.0, 0.11, 0.79)])
    ts = np.linspace(0, 1, 40)
    rings = []
    for t in ts:
        r, z = prof(t)
        rings.append(np.stack([r * 1.02 * np.cos(a), r * 0.98 * np.sin(a) + 0.16 * t * t, np.full(S, z)], 1))
    V, T = loft(rings)
    crown = Part("crown", V, T, PID["crown"], grid=(len(ts), S))
    crown.bias += np.clip((crown.V[:, 2] - 0.45) * 0.8, 0, 0.2)
    knife(crown, 0.2, lambda p, n: tangent((0, 0, 1), n), rng, aspect=1.3, curv=1.5, rt=(2.0, 3.5))
    circ = lambda r: 2 * math.pi * prof(ts[r])[0] / S
    spots = lattice(crown.grid, (3, len(ts) - 5), 5, circ, 0.13, lambda r, s: True, rng)
    gouges(crown, [(i, (0, 0, 1)) for i in spots], rng, d=(0.015, 0.024), rb=(0.06, 0.08), rt_in=0.8, rt_out=0.11)
    crown.smooth(0.25, 1)
    parts.append(crown)

    # the band: a thick ring of cream at the brim, cut into facets all round
    B, C = 176, 28
    b = np.linspace(0, 2 * math.pi, C, endpoint=False)
    sec = np.stack([0.058 * sgnpow(np.cos(b), 0.55), 0.11 * sgnpow(np.sin(b), 0.6)], 1)
    rings = []
    for ang in np.linspace(0, 2 * math.pi, B, endpoint=False):
        rad = 0.655 + sec[:, 0]
        rings.append(np.stack([rad * 1.02 * math.cos(ang), rad * 0.98 * math.sin(ang), sec[:, 1] + 0.05], 1))
    V, T = loft(rings, closed=True)
    band = Part("band", V, T, PID["band"], wear=0.12)
    knife(band, 0.13, lambda p, n: tangent((0, 0, 1), n), rng, aspect=1.2, curv=3.0, rt=(2.0, 4.0), rb=(1.5, 3.0), cov=0.7)
    band.smooth(0.25, 1)
    parts.append(band)

    # the pom-pom: a ball chip-carved all over
    bm = kit.ball((0.42, 0.42, 0.40), cuts=20)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    T = np.array([[v.index for v in f.verts] for f in bm.faces])
    bm.free()
    pom = Part("pom", V, T, PID["pom"], wear=0.18)
    knife(pom, 0.075, lambda p, n: tangent(rng.normal(size=3), n), rng, aspect=1.0, curv=5.0, rt=(0.6, 1.2), rb=(0.6, 1.2), cov=0.75)
    pom.smooth(0.2, 1)
    pom.move(None, (0.0, 0.2, 0.86))
    parts.append(pom)
    return parts


def make_base(rng):
    S = 224
    a = np.linspace(0, 2 * math.pi, S, endpoint=False)
    prof = [(0.96, 0.0), (1.0, 0.02), (1.03, 0.06), (1.045, 0.10), (1.035, 0.14), (1.0, 0.172), (0.96, BASE_TOP)]
    prof += [(r, BASE_TOP) for r in np.arange(0.93, 0.02, -0.03)]
    rings = [np.stack([r * np.cos(a), r * np.sin(a), np.full(S, z)], 1) for r, z in prof]
    V, T = loft(rings)
    base = Part("base", V, T, PID["base"])
    N = base.normals()
    rim = np.clip(np.hypot(V[:, 0], V[:, 1]) - 0.85, 0, 0.2) * 1.2
    base.bias += rim

    def stroke(p, n):
        return tangent((0, 0, 1), n) if abs(n[2]) < 0.8 else tangent((-p[1], p[0], 0.0), n)
    knife(base, lambda P: np.where(np.abs(P[:, 2] - BASE_TOP) < 1e-3, 0.32, 0.2), stroke, rng, aspect=1.4,
          curv=0.6, rt=(2.0, 4.0), rb=(2.0, 6.0), cov=0.6, dmax=0.04)
    base.smooth(0.2, 1)
    return base


# ---- the whole figure ------------------------------------------------------------------------------

def deform(P):
    """Pose the rest-frame points: turn and tilt the head about the neck, then lean back a little."""
    P = np.array(P, float)
    w = smoothstep(1.72, 2.05, P[:, 2])
    q = P - NECK
    roll, yaw = np.radians(ROLL) * w, np.radians(YAW) * w
    x = q[:, 0] * np.cos(roll) + q[:, 2] * np.sin(roll)
    z = -q[:, 0] * np.sin(roll) + q[:, 2] * np.cos(roll)
    y = q[:, 1]
    x, y = x * np.cos(yaw) - y * np.sin(yaw), x * np.sin(yaw) + y * np.cos(yaw)
    P = NECK + np.stack([x, y, z], 1)
    al = -math.radians(LEAN)
    q = P - np.array((0, 0, BASE_TOP))
    y = q[:, 1] * math.cos(al) - q[:, 2] * math.sin(al)
    z = q[:, 1] * math.sin(al) + q[:, 2] * math.cos(al)
    return np.array((0, 0, BASE_TOP)) + np.stack([q[:, 0], y, z], 1)


def build(seed=4):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    body, zs = make_body()
    S = BODY_SEG
    rest0 = body.V.copy()

    # rough out with the knife: big planes low on the body, smaller ones up on the head
    def spacing(P):
        z = P[:, 2]
        return np.where(z < 1.8, 0.31 + 0.05 * np.sin(P[:, 0] * 3.1 + z * 2.3), 0.21)

    def stroke(p, n):
        if p[2] < 1.85:
            return tangent((0, 0, -1), n)
        return tangent((n[1], -n[0], -0.7), n)          # round the head on a slant
    nk = knife(body, spacing, stroke, rng, aspect=1.45, curv=1.25, rt=(2.2, 4.0), rb=(6.0, 14.0))

    # eye sockets drilled, a few dents
    N = body.normals()
    eyes = []
    for sx in (-1, 1):
        p = body_point(2.22, np.array([-math.pi / 2 + sx * 0.66]))[0]
        i = int(np.argmin(np.linalg.norm(body.V - p, axis=1)))
        eyes.append((body.V[i].copy(), N[i].copy()))
    apply_cuts(body, [Cut(p, n, (0, 0, 1), 0.052, 0.085, 0.085, 0.085) for p, n in eyes])

    # gouge scallops in rows down the back and the back of the head
    ang = np.linspace(0, 2 * math.pi, S, endpoint=False)

    def back(r, s):
        z = zs[r]
        if z < 0.45 or z > 2.28:
            return False
        p = rest0[r * S + s][None]
        phi = abs(front_angle(p)[0])
        lim = belly_edge(p)[0] + 0.22 if z < BELLY_TOP + 0.1 else 0.95
        return phi > lim and rng.random() > 0.06
    circ = lambda r: 2 * math.pi * BODY(zs[r])[0] / S * 0.95
    spots = lattice(body.grid, (int(0.45 / BODY_DZ), len(zs) - 1), 8, circ, 0.14, back, rng)
    ng = gouges(body, [(i, (0, 0, -1)) for i in spots], rng)

    # dents: knocks it took over the years
    dents = []
    for _ in range(9):
        r, s = rng.integers(10, len(zs) - 30), rng.integers(0, S)
        dents.append(r * S + s)
    N = body.normals()
    dc = [Cut(body.V[i], N[i], (0, 0, 1), rng.uniform(0.008, 0.014), 0.05, 0.05, 0.05) for i in dents]
    apply_cuts(body, dc)
    for i in dents:
        d = np.linalg.norm(body.V - body.V[i], axis=1)
        body.dent = np.maximum(body.dent, smoothstep(0.045, 0.02, d))

    # sand the belly and the face: the carver smoothed these, the ridges go soft
    phi = np.abs(front_angle(rest0))
    z = rest0[:, 2]
    belly = smoothstep(belly_edge(rest0) + 0.05, belly_edge(rest0) - 0.15, phi) * (z < BELLY_TOP + 0.02)
    face = smoothstep(0.9, 0.4, phi) * smoothstep(1.95, 2.05, z) * smoothstep(2.45, 2.35, z)
    body.smooth(0.85 * np.maximum(belly, 0.6 * face), 5)
    body.smooth(0.25, 1)
    body.rest = body.V.copy()
    body.bias += 0.25 * smoothstep(0.35, 0.0, phi) * smoothstep(0.5, 0.8, z) * smoothstep(1.4, 1.0, z)   # belly bulge rubbed
    say("body: %d knife cuts, %d gouges, %.1fs" % (nk, ng, time.time() - t0))

    parts = [body]
    for side in (-1, 1):
        parts.append(make_wing(side, rng))
        parts.append(make_foot(side, rng))
    parts.append(make_tail(rng))

    # beak: set into the face, pointing forward and a little down
    bp = body_point(2.07, np.array([-math.pi / 2]))[0]
    i = int(np.argmin(np.linalg.norm(body.rest - bp, axis=1)))
    beak = make_beak(rng)
    beak.move(euler(8, 0, 0), body.rest[i] + np.array((0, 0.02, 0)))
    parts.append(beak)

    hat = make_hat(rng)
    for p in hat:
        p.move(euler(-10, 5, 0), (0.0, 0.04, 2.39))
        parts.append(p)
    parts.append(make_base(rng))
    say("parts carved, %.1fs" % (time.time() - t0))

    for p in parts:                                     # the pose (feet and base stay put)
        if p.rest is None:
            p.rest = p.V.copy()
        if p.pid not in (PID["foot"], PID["base"]):
            p.V = deform(p.V)
    bead = [deform((p - n * 0.024)[None])[0] for p, n in eyes]
    return parts, bead


# ---- into Blender ------------------------------------------------------------------------------------

def mesh_object(name, V, T, mat=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", np.asarray(V, np.float32).ravel())
    me.loops.add(T.size)
    me.loops.foreach_set("vertex_index", np.asarray(T, np.int32).ravel())
    me.polygons.add(len(T))
    me.polygons.foreach_set("loop_start", np.arange(0, T.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate()
    me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_attr(me, name, X):
    X = np.asarray(X, np.float32)
    if X.ndim == 1:
        a = me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set("value", X)
    else:
        a = me.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set("vector", X.ravel())


def convexity(part):
    """Small-scale ridges and broad bulges, both about -1 (hollow) to 1 (sharp ridge)."""
    N = part.normals()
    e = part.edges()
    L = part.average(part.V) - part.V
    el = np.linalg.norm(part.V[e[:, 0]] - part.V[e[:, 1]], axis=1)
    n = len(part.V)
    deg = np.maximum(np.bincount(e[:, 0], minlength=n) + np.bincount(e[:, 1], minlength=n), 1)
    mel = (np.bincount(e[:, 0], el, n) + np.bincount(e[:, 1], el, n)) / deg
    c = -(L * N).sum(1) / np.maximum(mel, 1e-5) ** 2
    c = 0.5 * c + 0.5 * part.average(c)
    big = c.copy()
    for _ in range(30):
        big = part.average(big)
    return np.tanh((c - big) / 7.0), np.tanh(big / 1.5), N


def bake_vertex_ao(ob, name, distance, samples):
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("BakeWorld")
    sc.world.light_settings.distance = distance
    sc.render.engine = 'CYCLES'
    sc.cycles.device, sc.cycles.samples = 'CPU', samples
    me = ob.data
    ca = me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    me.color_attributes.active_color = ca
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
    arr = np.empty(len(me.vertices) * 4, np.float32)
    ca.data.foreach_get("color", arr)
    me.color_attributes.remove(ca)
    return arr[0::4].astype(float)


def make_eyes(bead):
    mat = kit.material("Eyes", "#141012", rough=0.08)
    bm_all = bmesh.new()
    for c in bead:
        b = kit.ball((0.136, 0.136, 0.136), cuts=2)
        b.transform(kit.M(tuple(c)))
        tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(tmp)
        b.free()
        bm_all.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new("Penguin_Eyes")
    bm_all.to_mesh(me)
    bm_all.free()
    me.materials.append(mat)
    me.shade_smooth()
    ob = bpy.data.objects.new("Penguin_Eyes", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def high_object(parts):
    """All carved parts as one dense mesh with the per-vertex data the texture needs."""
    Vs, Ts, off = [], [], 0
    rest, info, shade_pre, nsm = [], [], [], []
    for p in parts:
        cs, cb, N = convexity(p)
        sm = N.copy()
        for _ in range(25):
            sm = p.average(sm)
        sm /= np.maximum(np.linalg.norm(sm, axis=1, keepdims=True), 1e-9)
        Vs.append(p.V)
        Ts.append(p.T + off)
        off += len(p.V)
        rest.append(p.rest * 0.25 + 0.5)
        info.append(np.stack([np.full(len(p.V), p.pid / 16.0), p.dent, p.bias], 1))
        shade_pre.append(np.stack([cs * 0.5 + 0.5, cb * 0.5 + 0.5], 1))
        nsm.append(sm * 0.5 + 0.5)
    V, T = np.concatenate(Vs), np.concatenate(Ts)
    ob = mesh_object("PenguinHigh", V, T, kit.material("BakeSource", "#808080"))
    me = ob.data
    set_attr(me, "rest", np.concatenate(rest))
    set_attr(me, "info", np.concatenate(info))
    set_attr(me, "nsm", np.concatenate(nsm))
    return ob, np.concatenate(shade_pre)


def decimate(high, target):
    ob = bpy.data.objects.new("PenguinLow", high.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.ratio = target / len(high.data.polygons)
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    for name in [a.name for a in me.attributes if not a.name.startswith(".") and a.name not in ("position",)]:
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
    me.shade_smooth()
    return ob


def crisp(ob, angle=28.0):
    """Crisp knife ridges: split the edges sharper than `angle`, smooth inside each plane. Done
    after the unwrap, so the texture islands are not cut up along every ridge."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(angle)]
    bmesh.ops.split_edges(bm, edges=sharp)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()


def emit_bake(high, low, source, size):
    """Bake one value of the dense carving onto the game mesh's texture layout (float image)."""
    tree = high.data.materials[0].node_tree
    em = tree.nodes.get("BakeEmit")
    if em is None:
        em = tree.nodes.new("ShaderNodeEmission")
        em.name = "BakeEmit"
        out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
        tree.links.new(em.outputs[0], out.inputs[0])
    for l in list(em.inputs[0].links):
        tree.links.remove(l)
    tree.links.new(source(tree), em.inputs[0])
    img = bpy.data.images.new("tmp_bake", size, size, alpha=True, float_buffer=True)
    img.pixels.foreach_set(np.zeros(size * size * 4, np.float32))
    ltree = low.data.materials[0].node_tree
    node = ltree.nodes.new("ShaderNodeTexImage")
    node.image = img
    ltree.nodes.active = node
    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, cage_extrusion=0.04, max_ray_distance=0.12, margin=12)
    px = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    ltree.nodes.remove(node)
    bpy.data.images.remove(img)
    return px.reshape(size, size, 4)


def attr_node(name):
    def f(tree):
        n = tree.nodes.new("ShaderNodeAttribute")
        n.attribute_name = name
        return n.outputs["Vector"]
    return f


def geo_node(which, k, c):
    def f(tree):
        g = tree.nodes.new("ShaderNodeNewGeometry")
        m = tree.nodes.new("ShaderNodeVectorMath")
        m.operation = 'MULTIPLY_ADD'
        m.inputs[1].default_value = (k, k, k)
        m.inputs[2].default_value = (c, c, c)
        tree.links.new(g.outputs[which], m.inputs[0])
        return m.outputs[0]
    return f


def lin(hexcode):
    return np.array(kit.srgb(hexcode))


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


PAINT = {  # pid: (sRGB colour, opacity, how much the grain shows)
    PID["body"]: ("#2A3A5E", 0.955, 0.28), PID["wing"]: ("#2A3A5E", 0.955, 0.28), PID["tail"]: ("#2A3A5E", 0.955, 0.28),
    PID["foot"]: ("#D48A32", 0.9, 0.22), PID["beak"]: ("#D48A32", 0.9, 0.22),
    PID["crown"]: ("#A8412F", 0.93, 0.25), PID["band"]: ("#EEE1C3", 0.9, 0.16), PID["pom"]: ("#EEE1C3", 0.9, 0.16),
}
CREAM = "#EEE1C3"


def paint(B, eyes):
    """The colour texture: lime wood with its grain, thin milk paint over it, rubbed through to the
    wood on the ridges, grime in the cuts and dents, and the carving's own shading."""
    size = B["pos"].shape[0]
    valid = (B["pos"][..., 3] > 0.5).ravel()
    g = lambda k: B[k].reshape(-1, 4)[valid]
    P = g("pos")[:, :3] * 4 - 2
    rest = g("rest")[:, :3] * 4 - 2
    Nh = g("nrm")[:, :3] * 2 - 1
    Ns = g("nsm")[:, :3] * 2 - 1
    info, sh, ao = g("info"), g("shade"), g("ao")
    pid = np.round(info[:, 0] * 16).astype(int)
    dent, bias = info[:, 1], info[:, 2]
    cs, cb = sh[:, 0] * 2 - 1, sh[:, 1] * 2 - 1
    ao_s, ao_b = ao[:, 0], ao[:, 1]

    # the wood: rings round a pith off behind the figure, warped a little, and fine fibres
    x0, y0 = -2.3, 3.1
    r = np.hypot(P[:, 0] - x0, P[:, 1] - y0) + 0.09 * fbm(P * (1.2, 1.2, 0.35), 3, 1) + 0.02 * fbm(P * (5, 5, 1.4), 2, 2)
    ring = (r * 7.5) % 1.0
    late = smoothstep(0.55, 0.92, ring) * (1 - smoothstep(0.92, 1.0, ring))
    fib = fbm(P * (55, 55, 5), 2, 3)
    wood = lin("#E9D1A6")[None] * (1 - 0.17 * late)[:, None] * (1 + 0.07 * fib)[:, None]
    wood *= (1 + 0.06 * fbm(P * (2.5, 2.5, 0.7), 2, 4))[:, None]
    wood[:, 2] *= (1 - 0.1 * late)

    # paint, per part, with the belly and the eye rings in cream on the body
    col = wood.copy()
    paint_col = np.zeros_like(wood)
    op = np.zeros(len(P))
    gs = np.zeros(len(P))
    for k, (hx, o, gshow) in PAINT.items():
        m = pid == k
        paint_col[m], op[m], gs[m] = lin(hx), o, gshow
    body = pid == PID["body"]
    phi = np.abs(front_angle(rest))
    edge = belly_edge(rest) + 0.035 * fbm(rest * 3.0, 2, 5) + 0.012 * fbm(rest * 11.0, 2, 6)
    cream = smoothstep(edge + 0.012, edge - 0.012, phi) * (rest[:, 2] < BELLY_TOP + 0.05)
    for c in eyes:
        d = np.linalg.norm(P - c, axis=1) + 0.006 * fbm(P * 30, 2, 7)
        cream = np.maximum(cream, smoothstep(0.106, 0.098, d))
    cream *= body
    paint_col[body] = paint_col[body] * (1 - cream[body, None]) + lin(CREAM)[None] * cream[body, None]
    op[body] = op[body] * (1 - cream[body]) + 0.9 * cream[body]
    gs[body] = gs[body] * (1 - cream[body]) + 0.16 * cream[body]
    brush = 1 + 0.05 * fbm(P * (7, 7, 38), 2, 8) + 0.04 * fbm(P * 4, 2, 9)
    painted = paint_col * ((1 - gs * late) * brush)[:, None]
    op = np.clip(op + 0.025 * fbm(P * 6, 2, 10), 0, 1)
    col = wood * (1 - op[:, None]) + painted * op[:, None]

    # rubbed through to the wood on the ridges and the high spots
    wn = fbm(P * 13, 3, 11) + 0.5 * fbm(P * 41, 2, 12)
    ridge = smoothstep(0.32, 0.62, cs) * smoothstep(-0.05, 0.12, wn + 0.1)
    high = smoothstep(0.55, 0.95, cb + bias) * 0.8
    w = np.maximum(ridge * (0.55 + 0.6 * np.clip(cb + bias, 0, 1)), high) + 0.45 * wn
    wear = smoothstep(0.42, 0.6, w) * (pid != PID["base"])
    worn = wood * lin("#C9A070")[None] / lin("#E9D1A6")[None]
    col = col * (1 - wear[:, None]) + worn * wear[:, None]
    base = pid == PID["base"]
    col[base] = col[base] * (0.93 - 0.12 * np.clip(bias[base], 0, 1))[:, None]

    # grime in the cuts, dents, handling, and the carving's own light and shade
    cav = np.clip(1 - ao_s, 0, 1)
    grime = lin("#4B3B2B")[None]
    col = col * (1 - 0.35 * cav)[:, None]
    col = col * (1 - 0.3 * cav)[:, None] + grime * (0.3 * cav)[:, None]
    col = col * (0.62 + 0.38 * np.clip(ao_b, 0, 1) ** 0.8)[:, None]
    col = col * (1 - 0.35 * dent)[:, None]
    col = col * (1 - 0.18 * np.clip(-cs * 1.5, 0, 1))[:, None] * (1 + 0.12 * np.clip(cs * 1.5, 0, 1))[:, None]
    L = unit((-0.45, -0.7, 0.6))
    facet = np.clip(((Nh - Ns) @ L) * 1.2, -0.2, 0.2)
    col = col * (1 + facet)[:, None]

    out = np.zeros((size * size, 4), np.float32)
    srgb = to_srgb(col)
    out[:, :3] = srgb.mean(0)
    out[valid, :3] = srgb
    out[:, 3] = 1.0
    rough = np.full(size * size, 0.86, np.float32)
    rough[valid] = 0.88 - 0.16 * wear - 0.05 * base
    return out, rough


def bake(pen, texture, high, shade_pre, eyes_at, size=1024):
    """The carving becomes one textured game mesh; the glossy eyes stay a mesh of their own."""
    t0 = time.time()
    ao_s = bake_vertex_ao(high, "ao_s", 0.1, 24)
    ao_b = bake_vertex_ao(high, "ao_b", 0.45, 24)
    set_attr(high.data, "shade", np.concatenate([shade_pre, np.zeros((len(ao_s), 1))], 1))
    set_attr(high.data, "ao", np.stack([ao_s, ao_b, np.zeros_like(ao_s)], 1))
    say("vertex AO %.1fs" % (time.time() - t0))
    low = decimate(high, TARGET_TRIS)
    body = kit.bake_texture([low], texture, name="Penguin_Body", shade=0.0, soften=0, rough=0.86, samples=1,
                            size=size, uv_angle=72.0, pack_margin=0.003)
    crisp(body)
    say("unwrap %.1fs" % (time.time() - t0))
    B = {k: emit_bake(high, body, src, size) for k, src in (
        ("pos", geo_node("Position", 0.25, 0.5)), ("nrm", geo_node("Normal", 0.5, 0.5)), ("rest", attr_node("rest")),
        ("nsm", attr_node("nsm")), ("info", attr_node("info")), ("shade", attr_node("shade")), ("ao", attr_node("ao")))}
    say("transfer bakes %.1fs" % (time.time() - t0))
    if os.environ.get("PENGUIN_DEBUG"):
        np.savez_compressed(os.environ["PENGUIN_DEBUG"], **B)
    out, rough = paint(B, eyes_at)
    tree = body.data.materials[0].node_tree
    for n in tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and n.image.size[0] == size:
            n.image.pixels.foreach_set(out.ravel())
            n.image.save()
        elif n.type == 'TEX_IMAGE' and n.image:
            path = bpy.path.abspath(n.image.filepath_raw)
            img = bpy.data.images.new(os.path.splitext(os.path.basename(path))[0] + "_full", size // 2, size // 2, alpha=False)
            r2 = rough.reshape(size, size)[::2, ::2]
            img.pixels.foreach_set(np.repeat(r2.ravel(), 4).reshape(-1, 4).clip(0, 1).astype(np.float32).ravel())
            img.filepath_raw, img.file_format = path, 'PNG'
            img.save()
            img.colorspace_settings.name = 'Non-Color'
            n.image = img
    say("paint %.1fs" % (time.time() - t0))
    bpy.data.objects.remove(high, do_unlink=True)
    pen.objects = [body] + [ob for ob in pen.objects if ob.name == "Penguin_Eyes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--look", help="render only the close-up view to this PNG (a quick check)")
    ap.add_argument("--quick", action="store_true", help="four views instead of eight")
    ap.add_argument("--px", type=int, default=512)
    ap.add_argument("--shots", help="views to render, e.g. 'front 3/4:full,side:clay' (default: the standard set)")
    ap.add_argument("--texture", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "penguin_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    parts, bead = build()
    pen = Prop("Penguin")
    eyes = make_eyes(bead)
    high, shade_pre = high_object(parts)
    say("dense carving: %d triangles" % len(high.data.polygons))
    pen.objects = [eyes]
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(pen, os.path.abspath(a.texture), high, shade_pre, bead)
    tris = pen.triangles()
    lo, hi = pen.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(pen.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review or a.look:
        import review
        rig = review.Rig(pen, samples=14 if a.quick else 40, focus=(-0.05, -0.45, 2.2))
        if a.look:
            rig.render(os.path.abspath(a.look), "close-up", "full", a.px)
        if a.review:
            os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
            shots = ([("front 3/4", "full"), ("close-up", "full"), ("back 3/4", "full"), ("game distance", "full")]
                     if a.quick else review.STANDARD)
            if a.shots:
                shots = [tuple(x.split(":")) for x in a.shots.split(",")]
            rig.sheet(os.path.abspath(a.review), shots, px=a.px, title="Penguin (whittled folk-art wood) review")
            print("review sheet", a.review)


if __name__ == "__main__":
    main()
