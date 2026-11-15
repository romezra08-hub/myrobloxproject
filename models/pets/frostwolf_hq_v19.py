"""FrostWolf pet, hero-quality remake: a midnight-blue frost wolf with a ridge of glowing ice crystals.
Built from scratch by script, on the Dragon's methods (models/pets/dragon.py).

    python models/pets/frostwolf_hq_v1.py --review out/frostwolf.png
    python models/pets/frostwolf_hq_v1.py --export models/export/frostwolf.fbx

Style: a believable fantasy creature in the same family as the Dragon, not a cartoon. The owner turned
down the big-eyed half-realistic look ("cursed"), a cute chibi ("simulator") and low-poly ("ruins it").
Must-haves:
  1. Real wolf anatomy, a little heroic: deep chest, strong shoulders, narrow waist, legs with upper
     muscle, a wrist and a hock, big paws with toes and claws. A long tapered muzzle, a brow, cheekbones,
     tall pointed ears, a strong jaw, a short neck set into a mane.
  2. Fur as modelled clumps: pointed locks that flow one way, layered like the Dragon's plates: a thick
     mane and chest ruff, cheek ruffs, back, haunch and elbow clumps, a bushy tail made of clumps.
  3. Clean painted gradients: midnight blue on the back to pale frost on the belly, chest and muzzle,
     darker tips. No blotches.
  4. Sharp faceted ice crystals of varied size along the spine from neck to mid-back (GLOW, pale cyan).
  5. Small glowing pale-cyan eyes in sockets under the brow, no whites, irises or lids. Mouth closed
     with a dark lip line. Calm and confident.
  6. Matte, a 1024 colour bake plus a baked roughness map. Body up to about 16k triangles. About 3 studs
     tall, up to about 5 long. Feet at z=0, facing -Y.

Round 19: a few chest locks still hung below the bib between the forelegs as white blades: the lowest
chest locks are shorter, and any lock whose root faces even partly down now runs back along the belly.

Round 18: the chest locks still showed dark notched outlines and their lowest tips hung below the chest
as white blades: chest locks lie flat with a shallower furrow, locks on the underside run back along the
belly instead of hanging, and after the bake most of the crease shading is taken back out of the chest
locks (0.14 instead of 0.4), so they merge. The crest is 7% lower than round 17 (its tallest point rose
0.75 above the fur beside it).

Round 17 (after the coordinator's review: faces read grumpy, smug or sleepy; the chest read as
plates; the crest was small): finer brows set higher with a gap above the eye, a fuller almond tilted up at
the outer corner; the dark lip tube is gone and the mouth is a short soft line painted per pixel along the
upper lip, its corner a touch higher than its front. The chest is long thin locks in columns (no stagger), so
they run in streaks over each other; the coat gradient is painted per vertex across every lock, the chest and body
locks have no dark outline and nearly no tip darkening, and the crease shading is softer (0.4). The crest
is about 25% taller, more upright and thicker.

Round 16: finish. Rime: the tips of the locks round the crystal roots turn frost white (they read as
frosted by the crystals), and the frost seams between those locks are stronger and reach a little further.

Round 15: the first ring of mane locks, right behind the skull, folded into a flat grey sheet beside the
jaw in the straight-front view: removed (the cheek ruff and the next ring cover the neck). Slightly finer
brows, so they read as a brow ridge rather than drawn eyebrows.

Round 14: up close the eye was a dot of light in a big dark almond (a flat lens sinking into the curved
head at its ends): eye and socket are now laid onto the curve of the head, so the glow fills a thin dark
rim, and the brow ridge, which covered most of the eye (its rays ran downhill onto it), now sits just
above it. The cheekbone ridge still read as a pale lower lid: removed, the cheek corner of the skull
carries it.

Round 13: the tail tip splayed into a white paper star and the tail sat on the rump like a separate
sausage: the core now runs on into a soft pale point, the last ring of locks lies along it, and ten locks
off the rump run into the tail root. The hips read pale beside the dark mane: the flanks are darker.

Round 12: pose and finish. The head is held higher with the nose a little down (proud rather than
hunting), the neck raised to match. A slightly cooler palette (indigo in the dark, icy cyan in the pale),
the fur round the crystals a little glossier, like rime, and each lock a slightly different roughness.

Round 11: a close look at the face: the cheekbone ridge sat right under the eye as a pale bar and read
as a lower lid (sleepy), so it now runs lower and further back; the white ear tufts looked like thorns
on the ear edges (removed); the chin stuck out past the upper lip (the jaw is shorter and tapers up);
the eyes are 10% larger.

Round 10: from the front it was a narrow column on doll legs: the forelegs stand 10% wider under a
broader chest, a flexor mass down the back of each forearm, a dewclaw on the inside of the wrist, the
pale stripe kept to the wrist, the lower legs darkening into the paws (darker tips), slate claws that
read against them.

Round 9: the locks on the flanks, back, haunches and shoulders read as feathers or scales (pale bodies,
dark tips, in neat rows): they are fewer, longer, narrower and flatter, with a deeper furrow, and use a
softer clump material whose tips are barely darker. The back has two rows instead of four.

Round 8: identity. The original is known by its spiky white crest, which barely showed: nine bigger
crystals (up to 0.9 tall before scaling) with five- and six-sided satellites leaning out, and frost
seams like the Dragon's ember seams: the crevices between the locks round the crystal roots are lit
pale cyan after the bake. Shorter ear tufts (they poked out over the ear tips), more roughness variation.

Round 7: from the front the head read long and narrow, like a fox: the muzzle is 10% shorter, the
cheekbones wider, a furrow runs down the forehead between heavier brows, and the bridge of the muzzle is
frost blue instead of a dark stripe. The crown locks next to the ears stood up as spikes: removed.

Round 6: the face was smooth and plain next to the Dragon's: small locks on the crown, under the eyes
and pale tufts in the ears, pale brow marks over the dark eye mask, nostrils, a lip corner that lifts a
touch (it drooped into a frown from the front), stronger fur streaks everywhere, and the tail-tip locks
close into a point (they splayed like a broom).

Round 5: the legs were faceted tubes with a hard shin edge: a round 12-sided profile, thicker forearms,
cannons and wrists, bigger paws (1.3), and locks flowing down over the outer shoulders and thighs with
tufts behind the wrists and hocks. The crystal ridge is 20% taller so it reads at game distance.

Round 4: the locks read as a pile of petals or feathers: they are wider and flatter, overlap more and
have a furrow down the middle (two strands joining at the tip), with more varied length and curve. The
back locks lie flat (the back line was spiky), a thicker tail with wider locks, a pale stripe down the
front of the forelegs, and the legs 0.12 shorter for a sturdier, heroic stance.

Round 3: the neck ran straight down from the skull, which turned the skin's frame and put the first
crystal on the chest and pale fur on top of the mane: the neck now runs back at about 50 degrees, and
placement uses rays straight out from the centre line. The head is held higher (proud), the whole wolf
scaled to 0.9. The mane is dark down its sides and pale only at the throat and chest (it was a white
bib like the grey Wolf's). Bigger crystals, shorter cheek locks (they stuck out as spikes), stronger
brows and cheekbones.

Round 2: the clumps read as paper shards: they are now narrower, thick with a round back and smoothly
shaded, lie flatter (only the tip lifts), and all follow one flow field (out from the head over the mane,
down the chest, back along the body); a lock whose flow ran straight into the surface used to point at
random. The head outline bows through its corners (it was a faceted box), lighter brows, the eye sat
behind its socket and was invisible, cheaper toes and claws.

Round 1: first build. Skin of neck and trunk (the Dragon's Skin), head from section tables (shell),
lofted legs with muscle masses, paws with toes and claws, about 230 draped fur clumps, ice crystals.
"""
import argparse
import bisect
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import kit  # noqa: E402  (first: it brings in bpy, which puts bmesh and mathutils on the path)
from kit import M, Prop, rounded_box  # noqa: E402

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

NAME = "FrostWolf"
SCALE = 0.9                       # the whole wolf is built a little large, then scaled to about 3 studs tall
HEAD_AT = (-0.04, -1.45, 2.9)     # the back of the skull
HEAD_ROT = (9, 2, -13)             # nose a little down, a slight tilt, turned towards -X (where the cameras are)
HEAD_SIZE = 1.0
THREADS = 3
LEG_DROP = 0.12                    # the lower legs are shortened by this much after building

# The upper head as sections from the back of the skull to the nose (nose towards -y):
# y, top z, half width of the top plane, cheek z, cheek half width, lip z, lip half width.
SKULL = [
    (0.12, 0.10, 0.07, 0.00, 0.18, -0.14, 0.12),
    (0.02, 0.27, 0.13, 0.04, 0.30, -0.19, 0.22),
    (-0.12, 0.33, 0.165, 0.03, 0.37, -0.20, 0.26),
    (-0.28, 0.31, 0.165, 0.00, 0.325, -0.19, 0.24),
    (-0.41, 0.225, 0.125, -0.03, 0.22, -0.17, 0.185),
    (-0.55, 0.18, 0.1, -0.05, 0.16, -0.16, 0.15),
    (-0.71, 0.155, 0.085, -0.06, 0.13, -0.15, 0.125),
    (-0.85, 0.135, 0.07, -0.065, 0.11, -0.145, 0.105),
    (-0.93, 0.105, 0.055, -0.065, 0.085, -0.135, 0.08),
    (-0.97, 0.055, 0.032, -0.07, 0.05, -0.12, 0.045),
]
# The lower jaw: y, top z, top half width, jaw-corner z, jaw-corner half width, chin-keel z.
JAW = [
    (0.02, -0.16, 0.21, -0.30, 0.21, -0.34),
    (-0.10, -0.17, 0.23, -0.34, 0.21, -0.40),
    (-0.33, -0.17, 0.19, -0.31, 0.16, -0.36),
    (-0.56, -0.16, 0.14, -0.27, 0.12, -0.31),
    (-0.74, -0.15, 0.115, -0.235, 0.095, -0.26),
    (-0.85, -0.145, 0.088, -0.21, 0.068, -0.228),
    (-0.9, -0.14, 0.045, -0.185, 0.035, -0.195),
]

# colours (sRGB) along the coat: 0 the spine, 1 the belly; above 1 the tail tip
PAL = [(0.0, "#10173A"), (0.3, "#1A2856"), (0.52, "#2D477E"), (0.74, "#84A9D3"), (0.95, "#C8DDF0"), (1.15, "#E6F3FA")]
DARK = "#0B0E1A"
GLOW_HEX = "#8FE3FF"


# ---- small helpers ----------------------------------------------------------------------------------

def _cr(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def _super(a, n):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2.0 / n), c), math.copysign(abs(s) ** (2.0 / n), s)


def _table(points, x):
    if x <= points[0][0]:
        return points[0][1]
    for (x0, v0), (x1, v1) in zip(points, points[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def smooth(x, a, b):
    """0 at a, 1 at b, smooth in between (a may be larger than b)."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


V = Vector

_PAL = [(p, Vector(kit.srgb(h))) for p, h in PAL]


def band(b):
    """The coat colour (linear RGB) at band value b: 0 midnight spine ... 1 pale belly, 1.15 tail tip."""
    if b <= _PAL[0][0]:
        return _PAL[0][1].copy()
    for (p0, c0), (p1, c1) in zip(_PAL, _PAL[1:]):
        if b <= p1:
            return c0.lerp(c1, smooth(b, p0, p1))
    return _PAL[-1][1].copy()


VERT_LAYERS = ("fu", "fq", "fs", "gloss", "grad", "frost", "soft")


def ensure_layers(bm):
    for name in VERT_LAYERS:
        if bm.verts.layers.float.get(name) is None:
            bm.verts.layers.float.new(name)
    if bm.verts.layers.float_color.get("col") is None:
        bm.verts.layers.float_color.new("col")
    if bm.faces.layers.float.get("boost") is None:
        bm.faces.layers.float.new("boost")
    return bm


def set_layer(bm, name, value):
    ensure_layers(bm)
    lay = bm.verts.layers.float[name]
    for v in bm.verts:
        v[lay] = value(v) if callable(value) else value
    return bm


def paint(bm, fn):
    """Vertex colour 'col' = fn(co, normal) (linear RGB)."""
    ensure_layers(bm)
    bm.normal_update()
    lay = bm.verts.layers.float_color["col"]
    for v in bm.verts:
        c = fn(v.co, v.normal)
        v[lay] = (c[0], c[1], c[2], 1.0)
    return bm


def sharpen(bm, degrees):
    lim = math.radians(degrees)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    return bm


def profile_round(k=10, n=2.0):
    return [_super(math.pi / 2 + 2 * math.pi * j / k, n) for j in range(k)]


P_LEG = [(0, 1.0), (0.62, 0.68), (0.9, 0.05), (0.75, -0.6), (0.3, -0.92), (-0.3, -0.92), (-0.75, -0.6), (-0.9, 0.05), (-0.62, 0.68)]
P_CLAW = [(0, 1.0), (0.62, 0.25), (0.5, -0.55), (0, -0.8), (-0.5, -0.55), (-0.62, 0.25)]
P_LIMB = [(0.0, 1.0), (0.5, 0.86), (0.86, 0.48), (1.0, 0.0), (0.88, -0.5), (0.5, -0.88), (0.0, -1.0), (-0.5, -0.88),
          (-0.88, -0.5), (-1.0, 0.0), (-0.86, 0.48), (-0.5, 0.86)]
P_CLAW5 = [(0, 1.0), (0.6, 0.15), (0.35, -0.7), (-0.35, -0.7), (-0.6, 0.15)]
P_BROW = [(0, 1.0), (0.95, -0.2), (0.55, -0.7), (-0.55, -0.7), (-0.95, -0.2)]


def loft(points, radii, profile, up=(0, 0, 1), rings=None):
    """The 2D `profile` carried along a smooth path through `points`, its up side turned towards `up`.
    Radii are numbers or (side, up) pairs. Each vertex stores how far along it is in 'grad'."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = rings or (n - 1) * 4
    ups = [Vector(u) for u in up] if isinstance(up[0], (tuple, list, Vector)) else [Vector(up)] * n
    rad = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]
    bm = ensure_layers(bmesh.new())
    lay = bm.verts.layers.float["grad"]
    path = [_cr(pts, i / rings * (n - 1)) for i in range(rings + 1)]
    loops, m = [], len(profile)
    for i, p in enumerate(path):
        u = i / rings * (n - 1)
        t = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        z = _cr(ups, u)
        z = z - t * z.dot(t)
        z = z.normalized() if z.length > 1e-6 else t.orthogonal().normalized()
        x = z.cross(t)
        rx = max(_cr([r[0] for r in rad], u), 1e-3)
        rz = max(_cr([r[1] for r in rad], u), 1e-3)
        ring = []
        for a, b in profile:
            v = bm.verts.new(p + x * (a * rx) + z * (b * rz))
            v[lay] = i / rings
            ring.append(v)
        loops.append(ring)
    for a, b in zip(loops, loops[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    for ring, tip in ((loops[0], path[0]), (loops[-1], path[-1])):
        c = bm.verts.new(tip)
        c[lay] = ring[0][lay]
        for j in range(m):
            bm.faces.new((ring[j], ring[(j + 1) % m], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def mass(points, radii, up, rings=None):
    """A muscle: a smooth teardrop mass along `points`."""
    return loft(points, radii, profile_round(10, 2.2), up=up, rings=rings or (len(points) - 1) * 3)


def lens(outline, thick, rows=((0.55, 0.8), (1.0, 0.0)), centre=(0.0, 0.0)):
    """A flat blade or pebble in the XZ plane: `thick` through the middle, thinning to a sharp rim."""
    bm = ensure_layers(bmesh.new())
    cx, cz = centre
    n = len(outline)
    rim = [bm.verts.new((a, 0.0, b)) for a, b in outline]
    for sgn in (1, -1):
        mid = bm.verts.new((cx, sgn * thick / 2, cz))
        prev = None
        for rho, k in rows:
            loop = rim if k == 0.0 else [bm.verts.new((cx + (a - cx) * rho, sgn * thick / 2 * k, cz + (b - cz) * rho)) for a, b in outline]
            for j in range(n):
                if prev is None:
                    bm.faces.new((mid, loop[j], loop[(j + 1) % n]))
                else:
                    bm.faces.new((prev[j], loop[j], loop[(j + 1) % n], prev[(j + 1) % n]))
            prev = loop
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def facing(origin, out, along):
    """A transform for a shape lying on a surface: X runs `along`, Y looks out along `out`."""
    y = Vector(out).normalized()
    x = Vector(along)
    x = (x - y * x.dot(y)).normalized()
    z = x.cross(y)
    if z.z < 0:
        y, z = -y, -z
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


class Skin:
    """A smooth skin over sections along a path (the Dragon's): positions are (s, angle), s along the
    path from the head end, the angle round the section in degrees, 90 at the spine, -90 at the belly.
    Each section is x, y, z, half width, height above, depth below, squareness, keel."""

    def __init__(self, sections, shoulders, samples=40):
        k = len(sections) - 1
        centres = [Vector(sec[:3]) for sec in sections]
        self.samples = samples
        self.pts = [_cr(centres, i / samples) for i in range(k * samples + 1)]
        self.par = [[_cr([sec[j] for sec in sections], i / samples) for j in range(3, 8)] for i in range(k * samples + 1)]
        self.len = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.len.append(self.len[-1] + (b - a).length)
        self.L = self.len[-1]
        n = len(self.pts)
        self.T = [(self.pts[min(i + 1, n - 1)] - self.pts[max(i - 1, 0)]).normalized() for i in range(n)]
        up = Vector((0, 0, 1))
        self.U = [(up - t * up.dot(t)).normalized() for t in self.T]
        for i in range(shoulders * samples - 1, -1, -1):
            u, axis = self.U[i + 1], self.T[i + 1].cross(self.T[i])
            if axis.length > 1e-9:
                u = Matrix.Rotation(self.T[i + 1].angle(self.T[i]), 3, axis.normalized()) @ u
            self.U[i] = (u - self.T[i] * u.dot(self.T[i])).normalized()
        self.kd = KDTree(n)
        for i, p in enumerate(self.pts):
            self.kd.insert(p, i)
        self.kd.balance()

    def s_of(self, index):
        x = index * self.samples
        i = min(int(x), len(self.len) - 2)
        return self.len[i] + (self.len[i + 1] - self.len[i]) * (x - i)

    def index_of(self, s):
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.len) - 2)
        return (i + (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)) / self.samples

    def at(self, s):
        s = min(max(s, 0.0), self.L)
        i = min(max(bisect.bisect_right(self.len, s) - 1, 0), len(self.pts) - 2)
        f = (s - self.len[i]) / max(self.len[i + 1] - self.len[i], 1e-9)
        c = self.pts[i].lerp(self.pts[i + 1], f)
        t = self.T[i].lerp(self.T[i + 1], f).normalized()
        u = self.U[i].lerp(self.U[i + 1], f)
        u = (u - t * u.dot(t)).normalized()
        w, a, b, n, keel = (p + (q - p) * f for p, q in zip(self.par[i], self.par[i + 1]))
        return c, t, u, t.cross(u), w, a, b, n, keel

    def bare(self, s, th):
        c, t, u, side, w, a, b, n, keel = self.at(s)
        x, y = _super(math.radians(th), n)
        h = (a * y + keel * y ** 16) if y > 0 else b * y
        return c + side * (w * x) + u * h

    def normal(self, s, th):
        ds = self.bare(min(s + 0.02, self.L), th) - self.bare(max(s - 0.02, 0.0), th)
        dt = self.bare(s, th + 2.0) - self.bare(s, th - 2.0)
        nrm = dt.cross(ds).normalized()
        return nrm if nrm.dot(self.bare(s, th) - self.at(s)[0]) > 0 else -nrm

    def point(self, s, th, lift=0.0):
        p = self.bare(s, th)
        return p + self.normal(s, th) * lift if lift else p

    def angle_of(self, p):
        """(index along the skin, angle round it) of the skin section nearest the point p."""
        _, k, _ = self.kd.find(p)
        c, t, u = self.pts[k], self.T[k], self.U[k]
        side = t.cross(u)
        r = p - c
        return k / self.samples, math.degrees(math.atan2(r.dot(u), abs(r.dot(side)) + 1e-9))

    def rings(self, k=0.4, lo=0.08, hi=0.2):
        s, out = 0.0, [0.0]
        while True:
            w, a, b = self.at(s)[4:7]
            s += min(max(k * (w + a + b) / 3.0, lo), hi)
            if s >= self.L - lo * 0.6:
                break
            out.append(s)
        return out + [self.L]

    def mesh(self, segs=24, cuts=()):
        bm = ensure_layers(bmesh.new())
        ss = self.rings()
        loops = [[bm.verts.new(self.bare(s, 90.0 + 360.0 * j / segs)) for j in range(segs)] for s in ss]
        for a, b in zip(loops, loops[1:]):
            for j in range(segs):
                bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
        for ring, s in ((loops[0], 0.0), (loops[-1], self.L)):
            c = bm.verts.new(self.at(s)[0])
            for j in range(segs):
                bm.faces.new((ring[j], ring[(j + 1) % segs], c))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        edges = []
        for cut in cuts:
            i = min(range(len(ss)), key=lambda k: abs(ss[k] - self.s_of(cut)))
            ring = loops[i]
            for j in range(segs):
                e = bm.edges.get((ring[j], ring[(j + 1) % segs]))
                if e:
                    edges.append(e)
        if edges:
            bmesh.ops.split_edges(bm, edges=edges)
        return bm


def shell(sections, corners, per=3, m=2, back_cap=0.0, nose_cap=0.0, soft=0.0):
    """A closed shell lofted along -Y through `sections`; corners(section) gives its outline. With
    `soft` above 0 the outline bows out through the corners (a closed spline) instead of running
    straight between them: rounded, but the planes still read."""
    k = len(sections) - 1
    width = len(sections[0])
    rings = []
    for i in range(k * per + 1):
        sec = [_cr([s[j] for s in sections], i / per) for j in range(width)]
        cs = corners(sec)
        pts = []
        nc = len(cs)
        for i0 in range(nc):
            a, b = Vector(cs[i0]), Vector(cs[(i0 + 1) % nc])
            p0, p3 = Vector(cs[i0 - 1]), Vector(cs[(i0 + 2) % nc])
            for f in range(m):
                u = f / m
                straight = a.lerp(b, u)
                curve = 0.5 * ((2 * a) + (b - p0) * u + (2 * p0 - 5 * a + 4 * b - p3) * u * u + (3 * a - p0 - 3 * b + p3) * u ** 3)
                q = straight.lerp(curve, soft)
                pts.append((q.x, q.y))
        rings.append((sec[0], pts))
    bm = ensure_layers(bmesh.new())
    loops = [[bm.verts.new((x, y, z)) for x, z in pts] for y, pts in rings]
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    for ring, dy in ((loops[0], -back_cap), (loops[-1], nose_cap)):
        c = sum((v.co for v in ring), Vector()) / n
        tip = bm.verts.new((c.x, c.y - dy, c.z))
        for j in range(n):
            bm.faces.new((ring[j], ring[(j + 1) % n], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def skull_at(y):
    rows = SKULL
    for a, b in zip(rows, rows[1:]):
        if b[0] <= y <= a[0]:
            f = (y - a[0]) / (b[0] - a[0])
            return tuple(p + (q - p) * f for p, q in zip(a, b))
    return rows[0] if y > rows[0][0] else rows[-1]


def skull_corners(sec):
    y, zt, wt, zc, wc, zb, wb = sec
    furrow = 0.045 * smooth(y, -0.1, -0.24) * smooth(y, -0.52, -0.38)       # a furrow down the forehead between the brows
    return [(0, zt + 0.035 - furrow), (-wt, zt), (-wc, zc), (-wb, zb), (0, zb - 0.01), (wb, zb), (wc, zc), (wt, zt)]


def jaw_corners(sec):
    y, zt, wt, zj, wj, zk = sec
    return [(0, zt), (-wt, zt), (-wj, zj), (0, zk), (wj, zj), (wt, zt)]


class Surface:
    """Finds points exactly on a set of meshes, so that details sit on them."""

    def __init__(self, *bms):
        verts, polys = [], []
        for bm in bms:
            base = len(verts)
            bm.verts.index_update()
            verts += [v.co.copy() for v in bm.verts]
            polys += [[base + v.index for v in f.verts] for f in bm.faces]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def ray(self, origin, direction, dist=10.0):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), dist)
        return loc, nrm

    def hit(self, origin, direction, out=0.0):
        loc, nrm = self.ray(origin, direction)
        if loc is None:
            raise ValueError("nothing in the way of the ray from %s" % (tuple(origin),))
        return loc + nrm * out, nrm


# ---- fur clumps ---------------------------------------------------------------------------------------

CLUMP_U = (0.0, 0.26, 0.52, 0.76)          # rows from the root; the tip is a single point at 1
CLUMP_Q = (-1.0, -0.45, 0.0, 0.45, 1.0)    # across


def _clump_width(u):
    grow = 0.66 + 0.34 * math.sin(0.5 * math.pi * min(u / 0.3, 1.0))
    return grow * (1.0 if u <= 0.3 else ((1.0 - u) / 0.7) ** 0.8)


def clump(surf, p, n, flow, length, width, lift=0.07, thick=0.045, tuck=0.03, bend=0.0, seed=0.0, hug=1.0, groove=0.45):
    """A pointed lock of fur lying on `surf` from its root `p` (surface normal `n`) along `flow`: a closed
    blade with a ridge down its middle, its root buried, rising like a roof tile towards a free tip.
    `bend` curves it sideways; `hug` (0 to 1) is how closely it follows the surface (0: a straight plane);
    `groove` sinks a furrow down its middle, so each lock reads as two strands joining at the tip.
    Vertex layers: fu (0 root to 1 tip), fq (-1 to 1 across), fs (a random number for this clump)."""
    n = Vector(n).normalized()
    d = Vector(flow)
    d = d - n * d.dot(n)
    if d.length < 0.25 * Vector(flow).length:            # flow almost straight into the surface: fall back to backwards
        d = Vector((0, 1, -0.3)) - n * Vector((0, 1, -0.3)).dot(n)
    d.normalize()
    side = n.cross(d)
    bm = ensure_layers(bmesh.new())
    lu, lq, ls = (bm.verts.layers.float[k] for k in ("fu", "fq", "fs"))

    def place(u, q, top):
        flat = p + d * (u * length) + side * (q * width * _clump_width(u) + bend * length * u * u)
        sp, sn = flat, n
        if hug > 0:
            loc, nrm = surf.ray(flat + n * 0.5, -n, 1.0)
            if loc is not None and (loc - flat).length < 0.28 and nrm.dot(n) > 0.4:
                sp = flat.lerp(loc, hug)
                sn = n.lerp(nrm, hug * 0.7).normalized()
            else:                                          # off the edge of the surface: droop rather than stick out
                sp = flat - n * (0.16 * hug * u * u * length)
        base = -tuck + (lift + tuck) * u ** 2.2
        h = base
        if top:
            lobe = max(1.0 - q * q, 0.0) ** 0.6 * (1.0 - groove * math.exp(-(q / 0.3) ** 2) * min(u / 0.2, 1.0) * (1.0 - u))
            h += thick * lobe * math.sin(math.pi * min(u, 1.0) ** 0.6)
        v = bm.verts.new(sp + sn * h)
        v[lu], v[lq], v[ls] = u, q, seed
        return v

    top, bot = [], []
    for u in CLUMP_U:
        rt, rb = [], []
        for j, q in enumerate(CLUMP_Q):
            if u == 0.0 or j in (0, len(CLUMP_Q) - 1):        # the root row and the rim are shared
                v = place(u, q, False)
                rt.append(v)
                rb.append(v)
            else:
                rt.append(place(u, q, True))
                rb.append(place(u, q, False))
        top.append(rt)
        bot.append(rb)
    tip = place(1.0, 0.0, False)
    for sheet, flip in ((top, False), (bot, True)):
        for a, b in zip(sheet, sheet[1:]):
            for j in range(len(CLUMP_Q) - 1):
                f = (a[j], a[j + 1], b[j + 1], b[j])
                bm.faces.new(f[::-1] if flip else f)
        last = sheet[-1]
        for j in range(len(CLUMP_Q) - 1):
            f = (last[j], last[j + 1], tip)
            bm.faces.new(f[::-1] if flip else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def drape(bm, surf, p, n, base):
    """Lay a flat shape built on the plane through p (normal n) onto the curve of `surf`: each vertex keeps
    its height above that plane, measured from the surface instead, plus `base`."""
    n = Vector(n).normalized()
    for v in bm.verts:
        h = (v.co - p).dot(n)
        flat = v.co - n * h
        loc, nrm = surf.ray(flat + n * 0.3, -n, 0.6)
        if loc is not None:
            v.co = loc + n * (base + h)
    return bm


def crystal(r, h, sides=6, seed=0.0, chisel=0.3):
    """A sharp ice crystal: a slightly tapering prism with a faceted point, base buried below z=0."""
    rnd = random.Random(seed)
    bm = ensure_layers(bmesh.new())
    rings = []
    turn = rnd.uniform(0, math.pi)
    for z, k in ((-0.12 * h, 1.0), (0.6 * h, 0.82)):
        ring = []
        for j in range(sides):
            a = turn + 2 * math.pi * j / sides
            rr = r * k * rnd.uniform(0.85, 1.12)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z + rnd.uniform(-0.04, 0.04) * h)))
        rings.append(ring)
    tip = bm.verts.new((r * chisel * rnd.uniform(-0.5, 0.5), r * chisel * rnd.uniform(-0.5, 0.5), h))
    a, b = rings
    for j in range(sides):
        bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        bm.faces.new((b[j], b[(j + 1) % sides], tip))
    bm.faces.new(a[::-1])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ---- materials ---------------------------------------------------------------------------------------

def _math(tree, op, a, b, c=None):
    n = tree.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b) if c is None else (a, b, c)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            tree.links.new(v, n.inputs[i])
    return n.outputs[0]


def _attr(tree, name, out="Fac"):
    a = tree.nodes.new("ShaderNodeAttribute")
    a.attribute_type, a.attribute_name = 'GEOMETRY', name
    return a.outputs[out]


def fur_material(name, scale=(30.0, 30.0, 4.0), strength=0.12, rough=0.9, lip=None):
    """Short fur: the vertex colour 'col' under fine streaks running along the axis with the smallest scale.
    With `lip` (see lip_line) a short soft dark line is painted along each upper lip, per pixel, so it is
    a crisp colour change and not a groove in the mesh."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    b = kit.principled(m)
    coord = t.nodes.new("ShaderNodeTexCoord")
    mp = t.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    t.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 1.0, 3.0
    t.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    v = _math(t, 'MULTIPLY_ADD', nz.outputs["Fac"], 2 * strength, 1 - strength)
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    t.links.new(_attr(t, "col", "Color"), hsv.inputs["Color"])
    t.links.new(v, hsv.inputs["Value"])
    out = hsv.outputs["Color"]
    if lip:
        out = lip_line(t, coord, out, **lip)
    t.links.new(out, b.inputs["Base Color"])
    return m


def lip_line(t, coord, colour, H, a, b, w=(0.005, 0.013), dark=DARK, amount=0.85):
    """Shader nodes: darken `colour` along the segment a-b ((y, z) in head space, on both sides of the
    muzzle). The baked object's coordinates are the built ones, scaled by SCALE and lowered by LEG_DROP,
    so they are taken back into head space first."""
    new, link = t.nodes.new, t.links.new
    loc, rot, sca = H.decompose()
    m1 = new("ShaderNodeMapping")
    m1.inputs["Scale"].default_value = (1.0 / SCALE,) * 3
    m1.inputs["Location"].default_value = Vector((0, 0, LEG_DROP)) - loc
    link(coord.outputs["Object"], m1.inputs["Vector"])
    m2 = new("ShaderNodeMapping")
    m2.inputs["Rotation"].default_value = rot.to_matrix().inverted().to_euler('XYZ')
    m2.inputs["Scale"].default_value = (1.0 / sca.x,) * 3
    link(m1.outputs["Vector"], m2.inputs["Vector"])
    sep = new("ShaderNodeSeparateXYZ")
    link(m2.outputs["Vector"], sep.inputs[0])
    comb = new("ShaderNodeCombineXYZ")
    link(sep.outputs[1], comb.inputs[1])
    link(sep.outputs[2], comb.inputs[2])
    A, B = Vector((0, a[0], a[1])), Vector((0, b[0], b[1]))
    ab = B - A

    def vec(op, x, y=None):
        n = new("ShaderNodeVectorMath")
        n.operation = op
        for i, val in enumerate((x, y)):
            if val is None:
                continue
            if isinstance(val, Vector):
                n.inputs[i].default_value = val
            else:
                link(val, n.inputs[i])
        return n
    ap = vec('SUBTRACT', comb.outputs[0], A)
    dot = vec('DOT_PRODUCT', ap.outputs[0], ab)
    tt = _math(t, 'MINIMUM', _math(t, 'MAXIMUM', _math(t, 'DIVIDE', dot.outputs["Value"], ab.length_squared), 0.0), 1.0)
    sc = vec('SCALE', ab)
    sc.inputs["Scale"].default_value = 1.0
    link(tt, sc.inputs["Scale"])
    near = vec('SUBTRACT', ap.outputs[0], sc.outputs[0])
    dist = vec('LENGTH', near.outputs[0])

    def ramp(x, lo, hi):
        r = new("ShaderNodeMapRange")
        r.interpolation_type = 'SMOOTHSTEP'
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = lo, hi
        link(x, r.inputs["Value"])
        return r.outputs["Result"]
    k = _math(t, 'SUBTRACT', 1.0, ramp(dist.outputs["Value"], w[0], w[1]))
    k = _math(t, 'MULTIPLY', k, ramp(tt, 0.0, 0.35))                                   # fades in from the front
    k = _math(t, 'MULTIPLY', k, ramp(_math(t, 'ABSOLUTE', sep.outputs[0], 0.0), 0.05, 0.09))
    mix = new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    link(_math(t, 'MULTIPLY', k, amount), mix.inputs[0])
    link(colour, mix.inputs[6])
    mix.inputs[7].default_value = (*kit.srgb(dark), 1.0)
    return mix.outputs[2]


def clump_material(name, strength=0.16, tipdark=0.3, rough=0.9, edge=0.14):
    """A fur clump: its colour 'col', fine strands along it, darker towards its tip and rim."""
    m = kit.material(name, "#808080", rough=rough)
    t = m.node_tree
    b = kit.principled(m)
    comb = t.nodes.new("ShaderNodeCombineXYZ")
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fq"), 9.0), comb.inputs[0])
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fu"), 1.3), comb.inputs[1])
    t.links.new(_math(t, 'MULTIPLY', _attr(t, "fs"), 13.0), comb.inputs[2])
    nz = t.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 1.0, 2.0
    t.links.new(comb.outputs[0], nz.inputs["Vector"])
    v = _math(t, 'MULTIPLY_ADD', nz.outputs["Fac"], 2 * strength, 1 - strength)
    fu = _attr(t, "fu")
    tip = _math(t, 'MULTIPLY_ADD', _math(t, 'MULTIPLY', fu, fu), -tipdark, 1.0)
    fq = _attr(t, "fq")
    q4 = _math(t, 'POWER', _math(t, 'ABSOLUTE', fq, 0.0), 4.0)
    edge = _math(t, 'MULTIPLY_ADD', q4, -edge, 1.0)
    v = _math(t, 'MULTIPLY', _math(t, 'MULTIPLY', v, tip), edge)
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    t.links.new(_attr(t, "col", "Color"), hsv.inputs["Color"])
    t.links.new(v, hsv.inputs["Value"])
    # rime: near the crystals (vertex value "frost") the tips turn frost white instead of darker
    rime = t.nodes.new("ShaderNodeMix")
    rime.data_type = 'RGBA'
    t.links.new(_math(t, 'MULTIPLY', _math(t, 'MULTIPLY', _attr(t, "frost"), _math(t, 'POWER', fu, 1.6)), 0.6), rime.inputs[0])
    t.links.new(hsv.outputs["Color"], rime.inputs[6])
    rime.inputs[7].default_value = (*kit.srgb("#CFEFFF"), 1.0)
    t.links.new(rime.outputs[2], b.inputs["Base Color"])
    return m


# ---- hidden faces and the texture layout (the Dragon's) ---------------------------------------------

def _hemisphere():
    out = [Vector((0, 0, 1))]
    for tilt, n in ((25, 6), (50, 9), (72, 12), (86, 14)):
        t = math.radians(tilt)
        for j in range(n):
            a = 2 * math.pi * (j + 0.5 * (tilt // 25 % 2)) / n
            out.append(Vector((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t))))
    return out


OPEN_FULL = 0.4


def cull_and_weigh(parts, keep=("GLOW",)):
    """Delete the faces no camera can see (buried in another shape, under a clump, flat on the floor)
    and mark barely seen ones with the face value "hid", so the unwrap gives them less texture."""
    verts, polys = [], []
    for bm, _ in parts.values():
        base = len(verts)
        bm.verts.index_update()
        verts += [v.co.copy() for v in bm.verts]
        polys += [[base + v.index for v in f.verts] for f in bm.faces]
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = _hemisphere()
    removed = 0
    for key, (bm, _) in parts.items():
        lh = bm.faces.layers.float.get("hid") or bm.faces.layers.float.new("hid")
        lb = bm.faces.layers.float.get("boost")
        if any(k in key for k in keep):
            continue
        bm.normal_update()
        dead = []
        for f in bm.faces:
            n = f.normal
            if n.length < 0.5:
                continue
            c = f.calc_center_median()
            if c.z < 0.02 and n.z < -0.9:
                dead.append(f)
                continue
            rot = n.to_track_quat('Z', 'Y').to_matrix()
            world = [rot @ d for d in dirs]
            o = c + n * 0.003
            free = sum(1 for d in world if bvh.ray_cast(o, d, 60.0)[0] is None)
            if free == 0:
                seen = False
                for p in [c.lerp(v.co, 0.8) for v in f.verts[:8]]:
                    o = p + n * 0.003
                    if any(bvh.ray_cast(o, d, 60.0)[0] is None for d in world):
                        seen = True
                        break
                if not seen:
                    o = c - n * 0.003
                    if sum(1 for d in world if bvh.ray_cast(o, -d, 60.0)[0] is None) < len(dirs) // 3:
                        dead.append(f)
                        continue
            f[lh] = max(0.0, min(1.0, 1.0 - free / len(dirs) / OPEN_FULL)) - (f[lb] if lb else 0.0)
        removed += sum(len(f.verts) - 2 for f in dead)
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return removed


UV_ANGLE, UV_MARGIN, PACK_MARGIN = 85.0, 0.004, 0.003
HIDDEN_SHARE = 0.25
HEAD_BOOST = 0.6


def weigh_islands(ob, keep=HIDDEN_SHARE):
    """After the unwrap: shrink texture islands that are mostly hidden, grow the boosted (head) ones."""
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    lh = bm.faces.layers.float.get("hid")
    if lh is None:
        return
    bm.faces.ensure_lookup_table()
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            continue
        f0, f1 = lf
        same = True
        for v in e.verts:
            u0 = next(l[uvl].uv for l in f0.loops if l.vert is v)
            u1 = next(l[uvl].uv for l in f1.loops if l.vert is v)
            if (u0 - u1).length_squared > 1e-12:
                same = False
                break
        if same:
            parent[find(f0.index)] = find(f1.index)
    islands = {}
    for f in bm.faces:
        islands.setdefault(find(f.index), []).append(f)
    for faces in islands.values():
        area = sum(f.calc_area() for f in faces) or 1.0
        w = sum(f[lh] * f.calc_area() for f in faces) / area
        if abs(w) <= 0.01:
            continue
        k = 1.0 - (1.0 - keep) * w
        loops = [l for f in faces for l in f.loops]
        c = sum((l[uvl].uv for l in loops), Vector((0.0, 0.0))) / len(loops)
        for l in loops:
            l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(me)


class _OpsProxy:
    def __init__(self, ops, pack):
        self._ops, self._pack = ops, pack

    def __getattr__(self, k):
        if k == "uv":
            return _UvProxy(self._ops.uv, self._pack)
        return getattr(self._ops, k)


class _UvProxy:
    def __init__(self, uv, pack):
        self._uv, self._pack = uv, pack

    def __getattr__(self, k):
        return self._pack if k == "pack_islands" else getattr(self._uv, k)


# ---- the frost wolf ----------------------------------------------------------------------------------

def head_matrix():
    return M(HEAD_AT, rot=HEAD_ROT, scale=HEAD_SIZE)


SPINE = None      # filled by build(): the Skin, used by the colour rules
ROOTS = []        # filled by build(): the roots of the main crystals, for the frost in the fur seams


def _seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (a + ab * t - p).length


def body_band(p):
    k, ang = SPINE.angle_of(p)
    mane = smooth(k, 4.6, 3.6)              # the mane is dark down its sides, pale only at the throat and chest
    return 1.0 - smooth(ang, lerp(-72.0, -78.0, mane), lerp(42.0, 15.0, mane))


EYE_H = []        # the eyes in head space, filled by build()


def head_band(hl):
    """The band value on the head, from head-space coordinates: a midnight crown fading to a frost
    muzzle and pale cheeks, a dark mask round each eye and a dark line from it back towards the ear."""
    top, cz = skull_at(hl.y)[1], skull_at(hl.y)[3]
    v = smooth(hl.z, top - 0.02, cz - 0.07)
    b_top = lerp(0.1, 0.56, smooth(hl.y, -0.36, -0.8))
    b = lerp(b_top, 0.92, v)
    for e in EYE_H:
        if (hl.x > 0) != (e.x > 0):
            continue
        d = ((hl - e) * Vector((1.0, 0.8, 1.3))).length
        b = lerp(b, 0.08, 1.0 - smooth(d, 0.05, 0.12))
        bm_ = ((hl - (e + Vector((-0.012 if e.x > 0 else 0.012, -0.035, 0.075)))) * Vector((1.3, 0.9, 2.2))).length
        b = lerp(b, 0.62, 1.0 - smooth(bm_, 0.022, 0.05))
        a2, b2 = e + Vector((0.01 if e.x > 0 else -0.01, 0.08, 0.02)), e + Vector((0.03 if e.x > 0 else -0.03, 0.26, 0.09))
        ab = b2 - a2
        t = max(0.0, min(1.0, (hl - a2).dot(ab) / ab.length_squared))
        b = lerp(b, 0.12, 0.85 * (1.0 - smooth((a2 + ab * t - hl).length, 0.025, 0.065)) * (1.0 - 0.5 * t))
    return b


def build():
    global SPINE
    ROOTS[:] = []
    EYE_H[:] = []
    fur_body = fur_material("FurBody", scale=(34.0, 6.0, 34.0), strength=0.14)      # streaks run along the body (y)
    fur_leg = fur_material("FurLeg", scale=(34.0, 34.0, 6.0), strength=0.13)        # streaks run down the legs (z)
    ya, yb = -0.68, -0.47           # the mouth: short, following the upper lip, its corner a touch higher than its front
    fur_face = fur_material("FurFace", scale=(52.0, 9.0, 52.0), strength=0.11,
                            lip=dict(H=head_matrix(), a=(ya, skull_at(ya)[5] + 0.004), b=(yb, skull_at(yb)[5] + 0.006)))
    clump_m = clump_material("Clump")
    clump_soft = clump_material("ClumpSoft", strength=0.2, tipdark=0.1, edge=0.0)    # body locks: tips barely darker, so they read as fur, not scales
    clump_chest = clump_material("ClumpChest", strength=0.16, tipdark=0.08, edge=0.0)  # the pale chest: no outlines at all
    dark = kit.material("Dark", DARK, rough=0.6)
    nose_m = kit.material("Nose", "#0D101B", rough=0.45)
    claw_m = kit.material("Claw", "#5A6374", rough=0.45)
    glow = kit.material("GLOW_Frost", GLOW_HEX, rough=0.25, emit=1.4)

    w = Prop(NAME)
    w.tally = {}
    H = head_matrix()
    Hinv = H.inverted()
    HR = H.to_3x3().normalized()
    rnd = random.Random(7)

    def hs(p):
        return tuple(H @ Vector(p))

    def colour(region, co, n):
        if region == "head":
            return band(head_band(Hinv @ co))
        if region == "jaw":
            return band(0.93)
        if region == "ruff":                       # cheek ruff: frost below, deep blue above, like the mane
            hl = Hinv @ co
            return band(lerp(0.3, 0.88, smooth(hl.z, 0.02, -0.2)))
        if region == "leg":
            return band(leg_band(co, n))
        if region == "tail":
            return band(tail_band(co))
        if region == "ear":
            return band(0.06)
        if region == "earin":
            return band(0.8)
        if region == "paw":
            return band(0.17)
        return band(body_band(co))

    base = []          # (part, bm, material, region, boost) in world space: the surfaces the fur lies on

    def add_base(part, bm, mat, region, crease=40.0, boost=0.0, colour_fn=None):
        ensure_layers(bm)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
        paint(bm, colour_fn or (lambda co, n: colour(region, co, n)))
        base.append((part, bm, mat, crease, boost))

    def add(part, bm, mat, crease=40.0, boost=0.0):
        ensure_layers(bm)
        lb = bm.faces.layers.float["boost"]
        for f in bm.faces:
            f[lb] = boost
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
            v.co.z -= LEG_DROP * smooth(v.co.z, 0.3, 1.15)       # shorter, sturdier legs
        if crease:
            sharpen(bm, crease)
        if ROOTS and mat is not glow:                       # fur near the crystal roots gets frost in its seams
            lf = bm.verts.layers.float["frost"]
            for v in bm.verts:
                d = min(_seg(v.co, a_, b_) for a_, b_ in zip(ROOTS, ROOTS[1:]))
                v[lf] = 1.0 - smooth(d, 0.14, 0.5)
            lg = bm.verts.layers.float["gloss"]
            for v in bm.verts:
                v[lg] = max(v[lg], 0.22 * v[lf])
        w.tally[part] = w.tally.get(part, 0) + sum(len(f.verts) - 2 for f in bm.faces)
        w.add(bm, mat)

    # ---- neck and trunk: one skin ----------------------------------------------------------------------
    spine = [
        (*hs((0, -0.15, -0.02)), 0.20, 0.22, 0.24, 2.2, 0.0),     # 0 inside the head
        (*hs((0, 0.14, -0.14)), 0.28, 0.27, 0.32, 2.2, 0.0),      # 1 behind the skull
        (0.0, -1.13, 2.48, 0.40, 0.36, 0.48, 2.25, 0.0),          # 2 the neck, thick with the mane
        (0.0, -0.96, 2.08, 0.50, 0.44, 0.62, 2.3, 0.01),          # 3 neck base, the chest below
        (0.0, -0.76, 1.84, 0.56, 0.46, 0.7, 2.35, 0.02),          # 4 withers and deep chest
        (0.0, -0.32, 1.80, 0.46, 0.42, 0.56, 2.4, 0.02),          # 5 behind the shoulders
        (0.0, 0.15, 1.82, 0.37, 0.36, 0.38, 2.4, 0.02),           # 6 narrow waist
        (0.0, 0.62, 1.85, 0.42, 0.37, 0.44, 2.4, 0.02),           # 7 hips
        (0.0, 1.02, 1.80, 0.37, 0.33, 0.42, 2.3, 0.01),           # 8 rump
        (0.0, 1.28, 1.76, 0.22, 0.21, 0.25, 2.2, 0.0),            # 9 tail root
        (0.0, 1.36, 1.76, 0.08, 0.08, 0.08, 2.2, 0.0),            # 10
    ]
    skin = Skin(spine, 4)
    SPINE = skin
    add_base("skin", skin.mesh(segs=24, cuts=(2.6, 5.2, 7.6)), fur_body, "body", crease=0)

    # ---- legs --------------------------------------------------------------------------------------------
    legs = []          # (sx, front, key points) for the clump placement

    def leg_band_fn(co, n):
        sx = 1.0 if co.x > 0 else -1.0
        inner = smooth(-n.x * sx, 0.1, 0.75)
        b = 0.30 + 0.36 * inner
        b += 0.14 * smooth(-n.y, 0.4, 0.9) * smooth(co.z, 0.95, 0.6) * smooth(co.z, 0.3, 0.5)
        b = lerp(b, 0.16, smooth(co.z, 0.5, 0.18))            # darker socks down to the paws
        top = smooth(co.z, 1.05, 1.65)
        return lerp(b, body_band(co), top)

    global leg_band
    leg_band = leg_band_fn

    def paw(x, y, yaw, size):
        F = M((x, y, 0), rot=(0, 0, yaw), scale=size)
        pad = rounded_box((0.27, 0.30, 0.17), n=3.2, cuts=2)
        pad.transform(F @ M((0, 0.02, 0.085)))
        add_base("paws", pad, fur_leg, "paw", crease=0)
        for tx, ty, s in ((-0.105, -0.105, 0.92), (-0.04, -0.15, 1.0), (0.04, -0.15, 1.0), (0.105, -0.105, 0.92)):
            toe = kit.ball((0.09 * s, 0.13 * s, 0.11 * s), cuts=1)
            ensure_layers(toe)
            toe.transform(F @ M((tx, ty, 0.052)))
            add_base("toes", toe, fur_leg, "paw", crease=0)
            claw = [(tx * 1.05, ty - 0.055 * s, 0.065), (tx * 1.08, ty - 0.095 * s, 0.045), (tx * 1.1, ty - 0.118 * s, 0.0)]
            bm = loft(claw, [0.024, 0.017, 0.003], P_CLAW5, up=(0, -0.3, 1), rings=3)
            bm.transform(F)
            set_layer(bm, "gloss", 0.35)
            add_base("claws", bm, claw_m, "paw", crease=50)

    for sx in (-1, 1):
        step = 0.16 if sx < 0 else 0.0
        fx = sx * 1.1                                  # the forelegs stand a little wider: a broader, stronger front
        elbow = V((0.39 * fx, -0.76, 1.04))
        wrist = V((0.37 * fx, -0.90 - step, 0.36))
        foot = V((0.37 * fx, -0.95 - step, 0.12))
        arm = [(0.27 * fx, -0.82, 2.05), (0.40 * fx, -1.08, 1.62), tuple(elbow), tuple(elbow.lerp(wrist, 0.45) + V((0, -0.02, 0))),
               tuple(wrist), tuple(foot)]
        add_base("legs", loft(arm, [(0.22, 0.31), (0.22, 0.28), (0.18, 0.21), (0.15, 0.165), (0.1, 0.115), (0.11, 0.12)],
                              P_LIMB, up=(0, -1, 0), rings=18), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * fx, -0.92, 2.0), (0.47 * fx, -1.02, 1.70), (0.47 * fx, -0.98, 1.40), (0.43 * fx, -0.90, 1.20)],
                                [(0.16, 0.20), (0.17, 0.22), (0.12, 0.15), (0.04, 0.05)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.38 * fx, -0.62, 1.72), (0.45 * fx, -0.66, 1.38), (0.43 * fx, -0.72, 1.10)],
                                [(0.16, 0.17), (0.15, 0.16), (0.05, 0.05)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.42 * fx, -0.86, 1.0), (0.42 * fx, -0.88 - 0.4 * step, 0.75), (0.39 * fx, -0.90 - 0.8 * step, 0.48)],
                                [(0.10, 0.12), (0.09, 0.10), (0.03, 0.03)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        carpal = kit.ball((0.10, 0.10, 0.10), cuts=2)
        carpal.transform(M(wrist + V((0, 0.08, 0.03))))
        add_base("wrists", ensure_layers(carpal), fur_leg, "leg", crease=0)
        # the flexor mass down the back of the forearm, and a dewclaw on the inside of the wrist
        add_base("muscle", mass([(0.4 * fx, -0.66, 1.0), (0.39 * fx, -0.72 - 0.3 * step, 0.76), (0.375 * fx, -0.8 - 0.7 * step, 0.5)],
                                [(0.1, 0.1), (0.085, 0.09), (0.03, 0.03)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        dew = [tuple(wrist + V((-0.07 * sx, 0.02, -0.04))), tuple(wrist + V((-0.1 * sx, -0.02, -0.1))), tuple(wrist + V((-0.1 * sx, -0.05, -0.15)))]
        bm = loft(dew, [0.03, 0.02, 0.004], P_CLAW5, up=(-sx, -0.3, 0), rings=3)
        set_layer(bm, "gloss", 0.35)
        add_base("claws", bm, claw_m, "paw", crease=50)
        paw(foot.x, foot.y - 0.07, 4 * fx, 1.3)
        legs.append((sx, True, elbow, wrist))

        stifle = V((0.43 * sx, 0.50, 1.06))
        hock = V((0.41 * sx, 1.08, 0.50))
        foot = V((0.41 * sx, 1.00, 0.12))
        thigh = [(0.28 * sx, 0.82, 1.98), (0.40 * sx, 0.64, 1.50), tuple(stifle), (0.42 * sx, 0.80, 0.78), tuple(hock),
                 (0.41 * sx, 1.05, 0.34), tuple(foot)]
        add_base("legs", loft(thigh, [(0.29, 0.41), (0.26, 0.36), (0.17, 0.2), (0.14, 0.17), (0.105, 0.125), (0.1, 0.115), (0.11, 0.12)],
                              P_LIMB, up=(0, -1, 0), rings=24), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.30 * sx, 1.05, 2.05), (0.42 * sx, 1.00, 1.70), (0.45 * sx, 0.92, 1.35), (0.42 * sx, 0.82, 1.05)],
                                [(0.16, 0.21), (0.18, 0.23), (0.14, 0.18), (0.04, 0.05)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.36 * sx, 0.62, 1.85), (0.47 * sx, 0.52, 1.50), (0.46 * sx, 0.48, 1.20), (0.43 * sx, 0.50, 1.04)],
                                [(0.16, 0.20), (0.18, 0.22), (0.13, 0.15), (0.04, 0.04)], up=(0, -1, 0)), fur_leg, "leg", crease=0)
        add_base("muscle", mass([(0.43 * sx, 0.62, 1.0), (0.43 * sx, 0.80, 0.86), (0.42 * sx, 0.98, 0.66), (0.41 * sx, 1.07, 0.54)],
                                [(0.10, 0.12), (0.10, 0.12), (0.06, 0.07), (0.03, 0.03)], up=(0, 1, 0)), fur_leg, "leg", crease=0)
        hk = kit.ball((0.09, 0.10, 0.10), cuts=2)
        hk.transform(M(hock + V((0, 0.05, 0.0))))
        add_base("hocks", ensure_layers(hk), fur_leg, "leg", crease=0)
        paw(foot.x, foot.y - 0.06, 3 * sx, 1.26)
        legs.append((sx, False, stifle, hock))

    # chest muscle: two pectoral masses under the ruff, between the front legs
    for sx in (-1, 1):
        add_base("muscle", mass([(0.12 * sx, -1.08, 1.95), (0.22 * sx, -1.20, 1.60), (0.26 * sx, -1.05, 1.28), (0.27 * sx, -0.9, 1.15)],
                                [(0.2, 0.2), (0.22, 0.22), (0.16, 0.16), (0.04, 0.04)], up=(0, -1, 0)), fur_body, "body", crease=0)

    # ---- tail: a thick core, covered in clumps later ------------------------------------------------------
    TAIL = [(0.0, 1.22, 1.86), (0.0, 1.52, 2.0), (0.05, 1.84, 1.98), (0.12, 2.1, 1.8), (0.16, 2.24, 1.54), (0.18, 2.28, 1.3),
            (0.18, 2.26, 1.12), (0.18, 2.22, 1.0)]
    tail_r = [0.16, 0.22, 0.26, 0.25, 0.2, 0.13, 0.065, 0.01]
    tail_bm = loft(TAIL, tail_r, profile_round(12), up=(0, 0, 1), rings=30)
    tail_path = [_cr([V(p) for p in TAIL], i / 60 * (len(TAIL) - 1)) for i in range(61)]

    def tail_t(co):
        k = min(range(len(tail_path)), key=lambda i: (tail_path[i] - co).length_squared)
        return k / 60.0, tail_path[k]

    def tail_band_fn(co):
        t, c = tail_t(co)
        r = co - c
        up = r.z / max(r.length, 1e-6)
        b = 0.18 + 0.45 * smooth(-up, -0.2, 0.9)
        return lerp(b, 1.12, smooth(t, 0.5, 0.85))

    global tail_band
    tail_band = tail_band_fn
    add_base("tail core", tail_bm, fur_body, "tail", crease=0)

    # ---- head: built in head space, then turned into place ------------------------------------------------
    skull = shell(SKULL, skull_corners, per=3, m=3, back_cap=0.05, nose_cap=0.01, soft=0.75)
    face = Surface(skull)
    jaw = shell(JAW, jaw_corners, per=2, m=3, back_cap=0.04, nose_cap=0.01, soft=0.7)
    head_parts = [("head", skull, fur_face, "head"), ("head", jaw, fur_face, "jaw")]
    eyes = []
    for sx in (-1, 1):
        pe, _ = face.hit((0.55 * sx, -0.62, 0.15), (-0.75 * sx, 0.6, -0.04))
        pn = face.hit((0.55 * sx, -0.62, 0.15), (-0.75 * sx, 0.6, -0.04))[1]
        # level brows: offsets from the eye in head space, laid onto the surface along its normal; the inner
        # end a touch higher (a calm brow; an inner end lower than the outer reads as a scowl)
        brow = [face.hit(pe + Vector((0, dy, dz)) + pn * 0.3, -pn, out=0.008)[0]
                for dy, dz in ((-0.07, 0.15), (-0.015, 0.142), (0.055, 0.128), (0.125, 0.11))]
        head_parts.append(("brows", loft(brow, [(0.007, 0.005), (0.022, 0.015), (0.025, 0.017), (0.015, 0.01)], P_BROW,
                                         up=(0.7 * sx, 0, 1), rings=10), fur_face, "head"))
        # cheek ruff volume behind the jaw, for the cheek clumps
        head_parts.append(("ruff", mass([(0.20 * sx, -0.22, -0.13), (0.29 * sx, 0.02, -0.12), (0.28 * sx, 0.22, -0.06)],
                                        [(0.11, 0.12), (0.15, 0.16), (0.10, 0.12)], up=(0, 0, 1)), fur_face, "ruff"))
        # the eye: a small glowing almond in a dark socket under the brow
        p, nrm = face.hit((0.55 * sx, -0.62, 0.15), (-0.75 * sx, 0.6, -0.04))
        eyes.append((p, nrm))
        EYE_H.append(p.copy())
        along = Vector((0.0, 1.0, 0.22))
        eye = [(-0.5, -0.02), (-0.3, 0.14), (0.0, 0.205), (0.3, 0.175), (0.5, 0.06), (0.3, -0.1), (0.0, -0.14), (-0.3, -0.11)]
        # both are laid onto the curve of the head, so the glow fills its thin dark rim (a flat eye sank
        # into the head at its ends and showed as a dot of light in a dark almond, like a cartoon pupil)
        sock = lens([(a * 0.158, b * 0.196) for a, b in eye], 0.02, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        sock.transform(facing(p, nrm, along))
        head_parts.append(("socket", drape(sock, face, p, nrm, 0.0), dark, None))
        e = lens([(a * 0.138, b * 0.17) for a, b in eye], 0.02, rows=((0.6, 0.9), (1.0, 0.0)), centre=(0.0, 0.03))
        e.transform(facing(p, nrm, along))
        head_parts.append(("eyes", drape(e, face, p, nrm, 0.007), glow, None))
        # the closed mouth: a dark lip line along the upper lip, back to the corner under the eye
    # nose: a dark wedge on the tip of the muzzle
    nose = rounded_box((0.12, 0.10, 0.085), n=2.6, cuts=2)
    for v in nose.verts:
        v.co.x *= 1.0 - 0.25 * smooth(v.co.z, 0.04, -0.04)
    nose.transform(M((0, -0.955, 0.075), rot=(-12, 0, 0)))
    set_layer(nose, "gloss", 0.5)
    head_parts.append(("nose", nose, nose_m, None))
    # ears: tall and pointed, cupped, angled a little out
    ears = []
    for sx in (-1, 1):
        ear = ear_shape()
        E = M((0.15 * sx, -0.02, 0.22), rot=(-10, 14 * sx, 22 * sx))
        ear.transform(E)
        head_parts.append(("ears", ear, fur_face, "earcol"))
        ears.append((sx, E))
    for part, bm, mat, region in head_parts:
        ensure_layers(bm)
        bm.transform(H)
        if region == "earcol":
            paint(bm, ear_colour(H, ears))
            base.append((part, bm, mat, 40.0, HEAD_BOOST))
        elif region is None:
            if mat is not glow:
                paint(bm, lambda co, n: Vector(kit.srgb(DARK)))
            base.append((part, bm, mat, 0.0 if mat is glow else 40.0, HEAD_BOOST))
        else:
            add_base(part, bm, mat, region, crease=38.0, boost=HEAD_BOOST)

    # ---- every base surface is in place: the fur lies on them --------------------------------------------
    surf = Surface(*[bm for _, bm, mat, _, _ in base if mat is not glow and mat is not dark])
    n_clumps = [0]

    def put(origin, toward, flow, L, W, region, lift=0.07, thick=0.045, bend=0.0, hug=1.0, boost=0.0, var=0.05, shade=1.0, mat=None, groove=0.45):
        o = Vector(origin)
        dvec = Vector(toward) - o
        p, nrm = surf.ray(o, dvec, dvec.length * 1.5)
        if p is None:
            return None
        under = smooth(-nrm.z, 0.1, 0.6)                  # on the underside: run back along the belly, never hang
        if under > 0:
            flow = Vector(flow).normalized().lerp(V((0, 1, -0.15)).normalized(), under)
        bm = clump(surf, p, nrm, flow, L, W, lift=lift, thick=thick, bend=bend, seed=rnd.random(), hug=hug, groove=groove)
        if mat is not None and mat.name.startswith("ClumpChest"):
            set_layer(bm, "soft", 1.0)
        f = shade * (1.0 + var * (rnd.random() - 0.5) * 2)
        paint(bm, lambda co, n, f=f: colour(region, co, nrm) * f)          # per vertex: the coat's gradient runs across the locks
        set_layer(bm, "gloss", 0.12 * rnd.random())
        add("clumps", bm, mat or clump_m, crease=75, boost=boost)
        n_clumps[0] += 1
        return p

    O = H @ V((0, -0.3, -0.05))     # the mane's fur radiates from here, in the middle of the head

    def flow_at(p):
        """Which way the fur runs at p: out from the head and back over the mane, down the throat and
        chest, backwards along the back, back and down on the flanks."""
        if p.y < -0.3:
            f = (p - O).normalized()
            f.y = max(f.y, 0.35)                    # never forwards
            f = f.normalized() * 0.5 + V((0, 0.5, -0.7))
            front = smooth(-p.y, 0.85, 1.3) * smooth(p.z, 2.15, 1.65)
            return f.lerp(V((0, 0.2, -1)), front)
        k, ang = skin.angle_of(p)
        return V((0, 1, -0.15 - 0.95 * smooth(ang, 40, -40)))

    def on_skin(index, th, L, W, lift=0.05, thick=0.06, bend=0.0, region="body", mat=None, groove=0.45):
        s = skin.s_of(index)
        c = skin.at(s)[0]
        bare = skin.bare(s, th)
        o = bare + (bare - c).normalized() * 0.9
        return put(o, c, flow_at(bare), L, W, region, lift=lift, thick=thick, bend=bend, mat=mat, groove=groove, var=0.03 if mat else 0.05)

    # ---- ice crystals: a crest along the spine from the neck to mid back, before the fur so that the fur
    # round their roots can be frosted --------------------------------------------------------------------
    roots = []
    for k, (idx, h) in enumerate(((1.5, 0.42), (2.05, 0.68), (2.6, 0.92), (3.15, 1.05), (3.7, 1.0), (4.25, 0.84), (4.8, 0.64),
                                  (5.3, 0.45), (5.75, 0.29))):
        s = skin.s_of(idx)
        c, t, u = skin.at(s)[:3]
        p, nrm = surf.hit(c + u * 1.2, -u)
        roots.append(p.copy())
        up = (u + V((0, 0, 0.6))).normalized()
        lean = (up * 0.9 + t * 0.32 + skin.at(s)[3] * rnd.uniform(-0.08, 0.08)).normalized()
        cr = crystal(0.07 + 0.09 * h, h, seed=k, sides=6 if k % 3 else 5)
        q = lean.to_track_quat('Z', 'Y')
        cr.transform(M(p - u * 0.04) @ q.to_matrix().to_4x4())
        add("ice", cr, glow, crease=15)
        for sx in (-1, 1):
            if h < 0.3 and (sx > 0) == (k % 2 == 0):
                continue
            s2, th2 = s + rnd.uniform(-0.1, 0.1), 90.0 - (24 + rnd.uniform(-4, 6)) * sx
            o2 = skin.at(s2)[0] + (skin.bare(s2, th2) - skin.at(s2)[0]).normalized() * 1.2
            p2, n2 = surf.ray(o2, skin.at(s2)[0] - o2)
            if p2 is None:
                continue
            lean2 = (n2 * 0.6 + up * 0.3 + t * 0.35 + skin.at(s)[3] * (0.38 * -sx)).normalized()
            h2 = h * rnd.uniform(0.45, 0.66)
            cr = crystal(0.05 + 0.07 * h2, h2, seed=k * 3 + sx, sides=5 if (k + sx) % 2 else 6)
            cr.transform(M(p2 - n2 * 0.03) @ lean2.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            add("ice", cr, glow, crease=15)
    ROOTS[:] = roots

    # the mane: staggered rings of locks round the neck and chest, longest at the bottom (the bib)
    rings = [(1.65, 0.4, 13), (2.1, 0.44, 13), (2.55, 0.47, 13), (3.0, 0.5, 13), (3.45, 0.5, 12),
             (3.9, 0.46, 12), (4.35, 0.4, 11)]
    for r, (idx, L, m) in enumerate(rings):
        for j in range(m):
            th = 90.0 + 360.0 * (j + 0.5 * (r % 2)) / m + rnd.uniform(-4, 4)
            low = -math.sin(math.radians(th))          # 1 at the belly side, -1 on the spine
            if low > 0.2:
                # the chest: long thin locks in columns (no stagger, every other ring), so each runs over the
                # roots of the next ones in streaks flowing down instead of tiling like plates
                th = 90.0 + 360.0 * j / m + rnd.uniform(-3, 3)
                Lc = L * 1.4 * rnd.uniform(0.9, 1.12) * (1.0 - 0.45 * smooth(low, 0.55, 0.95))
                on_skin(idx + rnd.uniform(-0.04, 0.04), th, Lc, 0.1 * rnd.uniform(0.9, 1.1),
                        lift=0.004, thick=0.04, bend=rnd.uniform(-0.1, 0.1), mat=clump_chest, groove=0.4)
                continue
            Lk = L * (1.0 + 0.3 * smooth(low, 0.0, 1.0)) * rnd.uniform(0.78, 1.18)
            on_skin(idx + rnd.uniform(-0.07, 0.07), th, Lk, 0.13 * rnd.uniform(0.85, 1.15),
                    lift=0.04 + 0.02 * r / len(rings), thick=0.05, bend=rnd.uniform(-0.18, 0.18))
    # the back: two rows of long flat locks either side of the spine, behind the mane
    for side_th in (90 - 30, 90 + 30):
        idx = 4.75 + (0.25 if side_th > 90 else 0.0)
        while idx < 8.1:
            on_skin(idx, side_th + rnd.uniform(-5, 5), 0.34 * rnd.uniform(0.85, 1.15), 0.085, lift=0.006, thick=0.03,
                    bend=rnd.uniform(-0.1, 0.1), mat=clump_soft, groove=0.6)
            idx += 0.5
    # lower flanks and belly fringe, and the haunches
    for th in (-30.0, 210.0):
        for k in range(5):
            on_skin(4.75 + 0.42 * k, th + rnd.uniform(-5, 5), 0.34, 0.09, lift=0.025, thick=0.032, mat=clump_soft, groove=0.6)
    for th in (14.0, 166.0, 40.0, 140.0):
        for k in range(3):
            on_skin(6.95 + 0.45 * k + (0.2 if th in (40.0, 140.0) else 0.0), th + rnd.uniform(-5, 5), 0.34, 0.09, lift=0.012,
                    thick=0.03, mat=clump_soft, groove=0.6)

    # legs: feathering behind the elbows, britches down the back of the thighs
    for sx, front, a, b in legs:
        if front:
            for k in range(3):
                z = a.z - 0.05 - 0.13 * k
                o = V((a.x + 0.02 * sx, a.y + 0.6, z))
                put(o, V((a.x, a.y - 0.05, z)), (0, 0.35, -1), 0.24 - 0.03 * k, 0.085, "leg", lift=0.035, thick=0.045)
        else:
            for k in range(5):
                z = 1.75 - 0.17 * k
                y = 0.95 + 0.06 * k
                o = V((a.x + 0.05 * sx * (k % 2), y + 0.8, z))
                put(o, V((a.x * 0.8, y - 0.2, z)), (0, 0.3, -1), 0.28, 0.1, "leg", lift=0.04, thick=0.05)
    # outer upper legs: locks flowing down over the shoulder and the thigh, and tufts behind wrist and hock
    for sx, front, a, b in legs:
        rows = (((1.62, (-1.08, -0.86)), (1.42, (-1.0, -0.78)), (1.22, (-0.92,))) if front else
                ((1.72, (0.62, 0.86)), (1.5, (0.56, 0.8, 1.0)), (1.28, (0.62, 0.9))))
        for z, ys in rows:
            for y in ys:
                o = V((1.3 * sx, y, z))
                put(o, V((0.2 * sx, y, z)), (0, 0.25 if front else 0.45, -1), 0.3 * rnd.uniform(0.9, 1.1), 0.095, "leg",
                    lift=0.015, thick=0.032, bend=rnd.uniform(-0.1, 0.1), mat=clump_soft, groove=0.6)
        c = b + V((0, 0.4, 0.05 if front else 0.12))
        put(c, b + V((0, 0, 0.05 if front else 0.12)), (0, 0.5, -1), 0.17, 0.08, "leg", lift=0.025, thick=0.035)

    # head: cheek ruff locks sweeping back, and a crest of locks off the back of the skull
    for sx in (-1, 1):
        for k, (y, z, L) in enumerate(((-0.24, -0.14, 0.18), (-0.08, -0.17, 0.21), (0.08, -0.14, 0.22), (-0.12, -0.03, 0.17),
                                       (0.06, -0.01, 0.19), (0.2, -0.08, 0.2))):
            o = H @ V((0.75 * sx, y, z))
            tgt = H @ V((0.0, y, z))
            flow = HR @ V((0.2 * sx, 1.0, -0.5))
            put(o, tgt, flow, L, 0.08, "ruff", lift=0.035, thick=0.045, boost=HEAD_BOOST)

    for k, (xx, yy) in enumerate(((-0.065, -0.22), (0.065, -0.2), (0.0, -0.1))):
        o = H @ V((xx, yy, 0.9))
        put(o, H @ V((xx, yy, 0.0)), HR @ V((xx * 1.5, 1.0, -0.2)), 0.17, 0.065, "head", lift=0.008, thick=0.022, boost=HEAD_BOOST,
            var=0.03)
    for sx in (-1, 1):
        for yy, zz in ((-0.24, -0.05), (-0.12, -0.07)):
            o = H @ V((0.8 * sx, yy, zz))
            put(o, H @ V((0.0, yy, zz)), HR @ V((0.15 * sx, 1.0, -0.35)), 0.16, 0.06, "head", lift=0.01, thick=0.022,
                boost=HEAD_BOOST, var=0.02)

    # tail: rings of locks running to the tip, the last ones closing into a point
    rings_t = 9
    for r in range(rings_t):
        t = 0.04 + 0.74 * r / (rings_t - 2) if r < rings_t - 1 else 0.84
        i = t * (len(TAIL) - 1)
        c = _cr([V(p) for p in TAIL], i)
        tan = (_cr([V(p) for p in TAIL], min(i + 0.05, len(TAIL) - 1)) - c).normalized()
        ref = V((0, 0, 1)) - tan * tan.z
        ref.normalize()
        sd = tan.cross(ref)
        m = 7 if r < rings_t - 1 else 6
        for j in range(m):
            a = 2 * math.pi * (j + 0.5 * (r % 2)) / m + rnd.uniform(-0.15, 0.15)
            out = ref * math.cos(a) + sd * math.sin(a)
            tip = r == rings_t - 1
            L = 0.24 if tip else 0.36 + 0.08 * math.sin(math.pi * t)
            put(c + out * 0.8, c, tan, L, 0.11 if tip else 0.15, "tail", lift=0.0 if tip else 0.03 + 0.02 * math.sin(math.pi * t),
                thick=0.04 if tip else 0.05, bend=rnd.uniform(-0.1, 0.1), hug=0.6 if tip else 1.0)
    # the tail root: locks off the rump running into the tail
    for idx in (8.45, 8.85):
        for th in (40.0, 70.0, 110.0, 140.0, 90.0):
            on_skin(idx + rnd.uniform(-0.05, 0.05), th + rnd.uniform(-6, 6), 0.32, 0.11, lift=0.02, thick=0.04, region="tail")

    # the base surfaces join the prop last, so the clumps above could be draped on them
    for part, bm, mat, crease, boost in base:
        add(part, bm, mat, crease=crease, boost=boost)

    print("  fur clumps: %d" % n_clumps[0])
    lowest = min(v.co.z for bm, _ in w.parts.values() for v in bm.verts)
    cut = cull_and_weigh(w.parts)
    print("  hidden faces removed: %d triangles (lowest point %.3f)" % (cut, lowest))
    w.build(scale=SCALE)
    for ob in w.objects:
        print("  %-26s %6d triangles" % (ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return w


def leg_band(co, n):          # replaced in build()
    return 0.3


def tail_band(co):            # replaced in build()
    return 0.3


def ear_shape():
    """A tall pointed ear in its own space: base on z=0, x across, front facing -y, cupped."""
    outline = [(-0.5, 0.0), (-0.47, 0.32), (-0.32, 0.66), (0.0, 1.0), (0.24, 0.7), (0.42, 0.36), (0.5, 0.0), (0.0, -0.06)]
    W, Hh = 0.25, 0.44
    rings = [(1.0, 0.0, 0.0), (0.85, -0.016, 0.032), (0.6, 0.016, 0.052), (0.3, 0.032, 0.066)]
    cx, cz = 0.0, 0.33
    bm = ensure_layers(bmesh.new())
    lg = bm.verts.layers.float["grad"]
    n = len(outline)
    rim = [bm.verts.new((a * W, 0.0, b * Hh)) for a, b in outline]
    for v in rim:
        v[lg] = 1.0
    fronts, backs = [rim], [rim]
    for rho, fy, by in rings[1:]:
        f, b = [], []
        for a, z in outline:
            x, zz = (cx + (a - cx) * rho) * W, (cz + (z - cz) * rho) * Hh
            vf, vb = bm.verts.new((x, fy, zz)), bm.verts.new((x, by, zz))
            vf[lg], vb[lg] = 0.0 + rho * 0.8, 1.0
            f.append(vf)
            b.append(vb)
        fronts.append(f)
        backs.append(b)
    for loops, cy, gv in ((fronts, 0.035, 0.0), (backs, 0.07, 1.0)):
        c = bm.verts.new((cx * W, cy, cz * Hh))
        c[lg] = gv
        for a, b in zip(loops, loops[1:]):
            for j in range(n):
                bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
        last = loops[-1]
        for j in range(n):
            bm.faces.new((last[j], last[(j + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ear_colour(H, ears):
    """Ears: midnight on the back and rim, frost-grey in the cup, darker towards the tip."""
    inv = [((H @ E).inverted(), (H @ E).to_3x3().normalized().inverted()) for sx, E in ears]

    def fn(co, n):
        loc, nl = min(((m @ co, r @ n) for m, r in inv), key=lambda ln: abs(ln[0].x) + abs(ln[0].y))
        h = loc.z / 0.44
        inner = smooth(-nl.y, 0.25, 0.7) * smooth(loc.y, -0.012, 0.012) * (1.0 - smooth(h, 0.62, 0.9))
        return band(lerp(0.06, 0.66, inner)) * (1.0 - 0.3 * smooth(h, 0.7, 1.0))
    return fn


def rough_map(body, texture, base, vary=0.1):
    """A baked roughness image the size of the colour image: `base`, lower where a shape was marked
    glossy (vertex layer 'gloss'), broken up by fine and broad noise. Saved as <name>_rough.png."""
    import numpy as np
    baked = body.data.materials[0]
    nodes = baked.node_tree.nodes

    def feeding(socket):
        return next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == socket for l in n.outputs[0].links))
    colour_node, rough_node = feeding("Base Color"), feeding("Roughness")
    size = colour_node.image.size[0]
    m = bpy.data.materials.new("RoughBake")
    kit.principled(m)
    t = m.node_tree
    new, link = t.nodes.new, t.links.new
    for nd in list(t.nodes):
        t.nodes.remove(nd)
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
    r = _math(t, 'ADD', _math(t, 'MULTIPLY', a.outputs["Fac"], -0.65 * base), base)
    r = _math(t, 'ADD', r, _math(t, 'MULTIPLY', _math(t, 'SUBTRACT', fine.outputs["Fac"], 0.5), 2 * vary))
    r = _math(t, 'ADD', r, _math(t, 'MULTIPLY', _math(t, 'SUBTRACT', broad.outputs["Fac"], 0.5), vary))
    r = _math(t, 'MAXIMUM', _math(t, 'MINIMUM', r, 1.0), 0.05)
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


BAKE_SHADE = 0.4              # how dark the deepest crease gets in the bake
CHEST_SHADE = 0.14            # ... and on the chest locks, so they merge into soft fur instead of outlined plates


def soften_chest(ob, size, shade, soft_shade, soften=3):
    """After the bake: on the chest locks (vertex value "soft") take most of the crease shading back out, so
    neighbouring locks merge instead of each being outlined like a plate. The crease shading is baked again
    the way kit.bake_texture made it, and the colour is scaled by the ratio of the two strengths."""
    import numpy as np
    sc = bpy.context.scene
    baked = ob.data.materials[0]
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    m = bpy.data.materials.new("SoftMask")
    kit.principled(m)
    tree = m.node_tree
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(_attr(tree, "soft"), em.inputs["Color"])
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    tree.links.new(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new("soft_mask", size, size, alpha=False, float_buffer=True)
    tn = tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tree.nodes.active = tn
    ob.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    def grab():
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        return px.reshape(size, size, 4)[..., :1].copy()
    keep = sc.cycles.samples
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    mask = np.clip(grab(), 0.0, 1.0)
    sc.cycles.samples = keep
    bpy.ops.object.bake(type='AO', margin=12)
    ao = grab()
    ob.data.materials[0] = baked
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)
    for _ in range(2):
        for axis in (0, 1):
            ao = sum(np.roll(ao, d, axis) for d in range(-soften, soften + 1)) / (2 * soften + 1)
    ao = np.clip((ao - 0.25) / 0.75, 0, 1) ** 0.8
    ratio = np.clip((1 - soft_shade * (1 - ao)) / (1 - shade * (1 - ao)), 1.0, 1.7)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    px[..., :3] = np.clip(px[..., :3] * (1 + mask * (ratio - 1)), 0.0, 1.0)
    tex.pixels.foreach_set(px.ravel())


FROST = "#BDF3FF"             # the glow in the seams of the fur round the crystal roots
FROST_REACH = 0.12
FROST_FROM, FROST_TO, FROST_MAX = 0.12, 0.55, 0.85


def frost_seams(ob, path, size):
    """After the bake (the Dragon's ember seams, in ice): where the fur near the crystals (vertex value
    "frost") sinks into a tight crevice between locks, turn the colour towards glowing pale cyan, as if
    the frost were lit from inside. Two quick bakes in the texture's own layout: the mask and a short
    reach crevice shading."""
    import numpy as np
    sc = bpy.context.scene
    keep_samples = sc.cycles.samples
    world = sc.world
    if world is None:
        world = sc.world = bpy.data.worlds.new("BakeWorld")
    keep_reach = world.light_settings.distance
    world.light_settings.distance = FROST_REACH
    baked = ob.data.materials[0]
    m = bpy.data.materials.new("FrostMask")
    kit.principled(m)
    tree = m.node_tree
    em = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(_attr(tree, "frost"), em.inputs["Color"])
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    tree.links.new(em.outputs[0], out.inputs[0])
    img = bpy.data.images.new("frost_mask", size, size, alpha=False, float_buffer=True)
    tn = tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    tree.nodes.active = tn
    ob.data.materials[0] = m
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    def grab():
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        return px.reshape(size, size, 4)[..., :1].copy()
    sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', margin=12)
    mask = np.clip(grab(), 0.0, 1.0)
    sc.cycles.samples = 24
    bpy.ops.object.bake(type='AO', margin=12)
    ao = grab()
    ao = (ao + np.roll(ao, 1, 0) + np.roll(ao, -1, 0) + np.roll(ao, 1, 1) + np.roll(ao, -1, 1)) / 5.0
    ob.data.materials[0] = baked
    sc.cycles.samples = keep_samples
    world.light_settings.distance = keep_reach
    crev = np.clip(((1.0 - ao) - FROST_FROM) / (FROST_TO - FROST_FROM), 0.0, 1.0)
    k = mask * FROST_MAX * crev * crev * (3 - 2 * crev)
    tex = next(n.image for n in baked.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.size[0] == size)
    px = np.empty(size * size * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    px[..., :3] = px[..., :3] * (1 - k) + np.array(kit.srgb(FROST), dtype=np.float32) * k
    tex.pixels.foreach_set(px.ravel())
    tex.filepath_raw, tex.file_format = path, 'PNG'
    tex.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(m)


def threads():
    r = bpy.context.scene.render
    r.threads_mode, r.threads = 'FIXED', THREADS


def bake(wolf, texture):
    """Everything that does not glow becomes one textured mesh, FrostWolf_Body (colour and soft crease
    shading baked into a 1024 image, 512 under PETS_FAST, packed by real outlines, barely seen surfaces
    given less of it, plus a baked roughness image). The glowing parts (crystals and eyes) join into
    FrostWolf_GLOW. Objects are matched by name prefix, since Blender renames shared materials
    ("GLOW_Frost.001") when several pets share a scene."""
    threads()
    pre = NAME + "_"
    glow = [ob for ob in wolf.objects if ob.name.startswith(pre + "GLOW")]
    real_pack = bpy.ops.uv.pack_islands

    def pack(**kw):
        weigh_islands(bpy.context.view_layer.objects.active)
        return real_pack(**kw)
    saved = bpy.ops
    bpy.ops = _OpsProxy(saved, pack)
    try:
        body = kit.bake_texture([ob for ob in wolf.objects if ob not in glow], texture, name=pre + "Body",
                                shade=BAKE_SHADE, soften=3, rough=0.88, uv_angle=UV_ANGLE, uv_margin=UV_MARGIN, pack_margin=PACK_MARGIN)
    finally:
        bpy.ops = saved
    size = 512 if os.environ.get("PETS_FAST") else 1024
    soften_chest(body, size, BAKE_SHADE, CHEST_SHADE)
    frost_seams(body, texture, size)
    rough_map(body, texture, 0.88, 0.1)
    me = body.data
    if "hid" in me.attributes:
        hid = [dd.value for dd in me.attributes["hid"].data]
        uv = me.uv_layers.active.data
        a2 = a3 = 0.0
        for pl, h in zip(me.polygons, hid):
            if h > 0.01:
                continue
            pts = [uv[i].uv for i in pl.loop_indices]
            a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
            a3 += pl.area
        print("seen surfaces: about %.0f pixels to a stud" % ((a2 * 1024 * 1024 / max(a3, 1e-9)) ** 0.5))
    junk = ("hid", "boost", "grad", "fu", "fq", "fs", "gloss", "col", "frost", "soft")
    for name in junk:
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
    bpy.ops.object.select_all(action='DESELECT')
    for ob in glow:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = glow[0]
    if len(glow) > 1:
        bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = g.data.name = pre + "GLOW"
    for name in junk:
        if name in g.data.attributes:
            g.data.attributes.remove(g.data.attributes[name])
    wolf.objects = [body, g]


def face_point():
    return (head_matrix() @ Vector((0, -0.5, 0.05)) - Vector((0, 0, LEG_DROP))) * SCALE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", help="write a review contact sheet to this PNG")
    ap.add_argument("--export", help="write an FBX for Roblox Studio to this path")
    ap.add_argument("--peek", help="quick look while building: these views, unbaked, to this PNG")
    ap.add_argument("--views", default="front 3/4,face,face front,side")
    ap.add_argument("--look", default="full")
    ap.add_argument("--px", type=int, default=480)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--title", default=NAME + " review")
    ap.add_argument("--texture", default=os.path.join(HERE, "..", "export", NAME.lower() + "_colour.png"))
    a = ap.parse_args()
    kit.fresh()
    threads()
    wolf = build()
    print("triangles by part:", dict(sorted(wolf.tally.items(), key=lambda kv: -kv[1])))
    head = face_point()

    def rig_for(samples):
        import review
        lo, hi = wolf.bounds()
        rig = review.Rig(wolf, samples=samples, focus=(head.x * 0.5, head.y + 0.9, head.z - 0.7))
        rig.cams["face"] = review._camera("C_face", head + Vector((-0.72, -0.9, 0.16)).normalized() * 3.3, head + Vector((0, 0.15, 0.02)), 30)
        rig.cams["face front"] = review._camera("C_facefront", head + Vector((0.0, -1.0, 0.07)).normalized() * 3.3, head + Vector((0, 0.15, 0.0)), 30)
        threads()
        return rig, review

    if a.peek:
        rig, _ = rig_for(a.samples)
        rig.sheet(os.path.abspath(a.peek), [(v.strip(), a.look) for v in a.views.split(",")], px=a.px, cols=a.cols, title="peek")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.texture)), exist_ok=True)
    bake(wolf, os.path.abspath(a.texture))
    tris = wolf.triangles()
    lo, hi = wolf.bounds()
    print("triangles:", tris, "total", sum(tris.values()))
    print("size in studs: %.2f wide, %.2f long, %.2f tall; lowest point z=%.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, lo.z))
    if a.export:
        os.makedirs(os.path.dirname(os.path.abspath(a.export)), exist_ok=True)
        kit.export_fbx(wolf.objects, os.path.abspath(a.export))
        print("exported", a.export)
    if a.review:
        rig, review = rig_for(a.samples)
        os.makedirs(os.path.dirname(os.path.abspath(a.review)), exist_ok=True)
        shots = review.STANDARD + [("face", "full"), ("face front", "full")]
        rig.sheet(os.path.abspath(a.review), shots, px=a.px, cols=a.cols, title=a.title)
        print("review sheet", a.review)


if __name__ == "__main__":
    main()
