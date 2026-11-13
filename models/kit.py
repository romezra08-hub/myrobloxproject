"""Building blocks for making Roblox props in Blender by script.

Runs under Blender's Python, either inside Blender or with the `bpy` module
(`pip install bpy`). One Blender unit is one stud. Front is -Y, up is +Z.

A prop is built from simple closed shapes that overlap, one mesh per material,
so it imports into Roblox as a few MeshParts.
"""
import math
import os

import bpy                # first: it puts Blender's own modules, addon_utils among them, on the path
import addon_utils        # noqa: E402
import bmesh
from mathutils import Euler, Matrix, Vector, noise


def fresh():
    """An empty scene with the renderer and the FBX exporter switched on."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for mod in ("cycles", "io_scene_fbx"):
        addon_utils.enable(mod, default_set=True)


def srgb(hexcode):
    """'#F27F1B' as the linear RGB Blender wants."""
    h = hexcode.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def principled(mat):
    try:
        mat.use_nodes = True
    except Exception:
        pass
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    tree = mat.node_tree
    b = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = next((n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'), None) or tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(b.outputs[0], out.inputs[0])
    return b


def material(name, hexcode, rough=0.55, metal=0.0, emit=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    b, rgb = principled(m), srgb(hexcode)
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    m.diffuse_color = (*rgb, 1.0)
    return m


def furry(mat, strength=0.3, mottle=0.12, fine=26.0, length=7.0, shade_down=0.0):
    """Stop a flat-coloured material looking like plastic: give it the look of short fur.

    Fine light and dark streaks run downwards (`fine` of them per stud across, each about
    `length` times longer than wide), a soft mottling sits on top, and with `shade_down` the
    colour deepens towards the feet. It is worked out in 3D space, so it has no seams, and
    bake_texture bakes it into the colour image that Roblox reads.
    """
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    coord = new("ShaderNodeTexCoord")
    stretch = new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (fine, fine, fine / length)
    link(coord.outputs["Object"], stretch.inputs["Vector"])
    streak = new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value, streak.inputs["Detail"].default_value = 1.0, 2.0
    link(stretch.outputs["Vector"], streak.inputs["Vector"])
    blotch = new("ShaderNodeTexNoise")
    blotch.inputs["Scale"].default_value, blotch.inputs["Detail"].default_value = 2.2, 1.0
    link(coord.outputs["Object"], blotch.inputs["Vector"])

    def times_plus(src, k, c):                       # src * k + c
        m = new("ShaderNodeMath")
        m.operation = 'MULTIPLY_ADD'
        m.inputs[1].default_value, m.inputs[2].default_value = k, c
        link(src, m.inputs[0])
        return m

    v1 = times_plus(streak.outputs[0], 2 * strength, 1 - strength - mottle)
    v2 = new("ShaderNodeMath")
    v2.operation = 'MULTIPLY_ADD'                    # blotch * (2 * mottle) + v1
    v2.inputs[1].default_value = 2 * mottle
    link(blotch.outputs[0], v2.inputs[0])
    link(v1.outputs[0], v2.inputs[2])
    return _tint(mat, coord, v2, shade_down, 0.95)


def scaly(mat, size=0.16, joins=0.32, vary=0.16, shade_down=0.0, rough=0.8):
    """Stop a flat-coloured material looking like plastic: give it a skin of small scales.

    Cells about `size` studs across, each a slightly different shade (`vary`), with darker joins
    between them (`joins`). Like furry(), it is worked out in 3D space, so it has no seams, and
    bake_texture bakes it into the colour image that Roblox reads.
    """
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    coord = new("ShaderNodeTexCoord")
    cells = new("ShaderNodeMapping")
    cells.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / (size * 1.3))     # a little taller than wide
    link(coord.outputs["Object"], cells.inputs["Vector"])
    edge = new("ShaderNodeTexVoronoi")
    edge.feature = 'DISTANCE_TO_EDGE'
    edge.inputs["Scale"].default_value = 1.0
    link(cells.outputs["Vector"], edge.inputs["Vector"])
    inside = new("ShaderNodeMapRange")                 # 0 on a join, 1 well inside a scale
    inside.inputs["From Max"].default_value = 0.14
    link(edge.outputs["Distance"], inside.inputs["Value"])
    cell = new("ShaderNodeTexVoronoi")
    cell.feature = 'F1'
    cell.inputs["Scale"].default_value = 1.0
    link(cells.outputs["Vector"], cell.inputs["Vector"])
    a = new("ShaderNodeMath")
    a.operation = 'MULTIPLY_ADD'                       # inside * joins + (1 - joins)
    a.inputs[1].default_value, a.inputs[2].default_value = joins, 1 - joins
    link(inside.outputs["Result"], a.inputs[0])
    b2 = new("ShaderNodeMath")
    b2.operation = 'MULTIPLY_ADD'                      # each scale's own shade * (2 * vary) + (1 - vary)
    b2.inputs[1].default_value, b2.inputs[2].default_value = 2 * vary, 1 - vary
    link(cell.outputs["Color"], b2.inputs[0])
    both = new("ShaderNodeMath")
    both.operation = 'MULTIPLY'
    link(a.outputs[0], both.inputs[0])
    link(b2.outputs[0], both.inputs[1])
    return _tint(mat, coord, both, shade_down, rough)


def _tint(mat, coord, value, shade_down, rough):
    """Multiply a material's flat colour by the brightness pattern `value`, deepening it towards
    the feet by `shade_down`, and make it matte."""
    tree, b = mat.node_tree, principled(mat)
    base = tuple(b.inputs["Base Color"].default_value)
    new, link = tree.nodes.new, tree.links.new
    if shade_down:
        split_xyz = new("ShaderNodeSeparateXYZ")
        link(coord.outputs["Generated"], split_xyz.inputs[0])
        ramp = new("ShaderNodeMath")
        ramp.operation = 'MULTIPLY_ADD'                # height * shade_down + (1 - shade_down)
        ramp.inputs[1].default_value, ramp.inputs[2].default_value = shade_down, 1 - shade_down
        link(split_xyz.outputs[2], ramp.inputs[0])
        shaded = new("ShaderNodeMath")
        shaded.operation = 'MULTIPLY'
        link(value.outputs[0], shaded.inputs[0])
        link(ramp.outputs[0], shaded.inputs[1])
        value = shaded
    hsv = new("ShaderNodeHueSaturation")
    hsv.inputs["Color"].default_value = base
    link(value.outputs[0], hsv.inputs["Value"])
    link(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return mat


def M(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """A transform: scale, then rotate (degrees, XYZ), then move."""
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    r = Euler([math.radians(a) for a in rot], 'XYZ').to_matrix().to_4x4()
    return Matrix.Translation(loc) @ r @ Matrix.Diagonal((*scale, 1.0))


# ---- shapes: each returns a new bmesh centred on the origin -----------------------------------

def rounded_box(size=(1, 1, 1), n=4.0, cuts=6):
    """A box with its corners rounded off (a superellipsoid). n=2 is a ball, 3 to 4 is the chunky
    pillow shape of a Roblox pet, large n is a sharp box. Quads only, evenly spread."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    sx, sy, sz = (s / 2.0 for s in size)
    for v in bm.verts:
        d = v.co.normalized()
        r = (abs(d.x) ** n + abs(d.y) ** n + abs(d.z) ** n) ** (-1.0 / n)
        v.co = Vector((d.x * r * sx, d.y * r * sy, d.z * r * sz))
    return bm


def ball(size=(1, 1, 1), cuts=4):
    return rounded_box(size, 2.0, cuts)


def _spline(vals, t):
    """Catmull-Rom through a list of numbers or Vectors, t from 0 to len-1."""
    k = min(int(t), len(vals) - 2)
    u = t - k
    p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
    return 0.5 * ((2 * p1) + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def tube(points, radii, segs=12, rings=None, flat=1.0, zigzag=None):
    """Circles lofted along a smooth path through `points`, with a radius at each point.
    Good for tails, legs, horns and tufts. Each face stores how far along it is (0 to 1) in the
    face layer "t", so that a tip can be given another colour with split().
    zigzag=(t, depth) pushes every other point of the ring nearest t forward and the rest back,
    so that a colour change there has a jagged, furry edge; split at tube_ring(t, rings)."""
    pts = [Vector(p) for p in points]
    rings = rings or (len(pts) - 1) * 4
    path = [_spline(pts, i / rings * (len(pts) - 1)) for i in range(rings + 1)]
    rad = [max(1e-4, _spline(list(radii), i / rings * (len(pts) - 1))) for i in range(rings + 1)]
    bm = bmesh.new()
    layer = bm.faces.layers.float.new("t")
    tangent = (path[1] - path[0]).normalized()
    normal = tangent.orthogonal().normalized()
    loops = []
    for i, p in enumerate(path):
        new = (path[min(i + 1, rings)] - path[max(i - 1, 0)]).normalized()
        axis = tangent.cross(new)
        if axis.length > 1e-6:                                   # carry the frame round the bend without twisting
            normal = Matrix.Rotation(tangent.angle(new), 3, axis.normalized()) @ normal
        tangent = new
        side = tangent.cross(normal).normalized()
        loops.append([bm.verts.new(p + (normal * math.cos(a) + side * math.sin(a) * flat) * rad[i])
                      for a in (2 * math.pi * j / segs for j in range(segs))])
        if zigzag and i == round(zigzag[0] * rings):
            for j, v in enumerate(loops[-1]):
                v.co += tangent * zigzag[1] * (1 if j % 2 == 0 else -1)
    for i, (a, b) in enumerate(zip(loops, loops[1:])):
        for j in range(segs):
            f = bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
            f[layer] = (i + 0.5) / rings
    for ring, t in ((loops[0], 0.0), (loops[-1], 1.0)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))[layer] = t
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def tube_ring(t, rings):
    """The value of the face layer "t" at which a tube's zigzag ring sits."""
    return round(t * rings) / float(rings)


# ---- bending shapes out of true ----------------------------------------------------------------

def _span(bm, axis):
    vals = [v.co[axis] for v in bm.verts]
    return min(vals), max(vals)


def taper(bm, axis=2, lo=1.0, hi=1.0, power=1.0):
    """Scale the cross-section from `lo` at the bottom of `axis` to `hi` at the top."""
    a, b = _span(bm, axis)
    for v in bm.verts:
        t = ((v.co[axis] - a) / (b - a)) ** power if b > a else 0.0
        s = lo + (hi - lo) * t
        for k in range(3):
            if k != axis:
                v.co[k] *= s
    return bm


def shear(bm, axis=2, along=1, amount=0.0, power=1.0):
    """Push the top of `axis` sideways along `along` (a lean, or a curve with power > 1)."""
    a, b = _span(bm, axis)
    for v in bm.verts:
        t = (v.co[axis] - a) / (b - a) if b > a else 0.0
        v.co[along] += amount * t ** power
    return bm


def lumpy(bm, amount=0.03, freq=1.2, seed=0.0):
    """Gentle unevenness, so a shape stops looking machine made."""
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        v.co += v.co.normalized() * noise.noise(v.co * freq + off) * amount
    return bm


def cut(bm, co, no):
    """Slice the mesh along a plane (nothing is removed) so a colour edge can follow it cleanly."""
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=Vector(co), plane_no=Vector(no).normalized())
    return bm


def split(bm, pred):
    """Two meshes: the faces for which pred(face) is true, and the rest. Uses up `bm`."""
    keep = [bool(pred(f)) for f in bm.faces]
    yes, no = bm.copy(), bm.copy()
    bmesh.ops.delete(yes, geom=[f for f, k in zip(yes.faces, keep) if not k], context='FACES')
    bmesh.ops.delete(no, geom=[f for f, k in zip(no.faces, keep) if k], context='FACES')
    bm.free()
    return yes, no


def centre(face):
    return face.calc_center_median()


# ---- putting a prop together ----------------------------------------------------------------------

class Prop:
    """Collects shapes by material, then makes one mesh object per material."""

    def __init__(self, name):
        self.name, self.parts, self.objects = name, {}, []

    def add(self, bm, mat, at=None):
        """Add a shape (used up) in material `mat`, moved by the matrix `at`."""
        if at is not None:
            bm.transform(at)
        target = self.parts.setdefault(mat.name, (bmesh.new(), mat))[0]
        tmp = bpy.data.meshes.new("tmp")
        bm.to_mesh(tmp)
        bm.free()
        target.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)

    def build(self, scale=1.0):
        for key, (bm, mat) in self.parts.items():
            if scale != 1.0:
                bm.transform(Matrix.Scale(scale, 4))
            me = bpy.data.meshes.new("%s_%s" % (self.name, key))
            bm.to_mesh(me)
            bm.free()
            me.materials.append(mat)
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
            me.update()
            ob = bpy.data.objects.new(me.name, me)
            bpy.context.scene.collection.objects.link(ob)
            self.objects.append(ob)
        return self.objects

    def triangles(self):
        return {ob.name: sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in self.objects}

    def bounds(self):
        pts = [ob.matrix_world @ Vector(c) for ob in self.objects for c in ob.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return lo, hi


def export_fbx(objects, path):
    """Write an FBX that Roblox Studio's Import 3D reads at the right size and facing."""
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, axis_forward='-Z', axis_up='Y',
                             apply_scale_options='FBX_SCALE_ALL', use_mesh_modifiers=True, path_mode='COPY',
                             embed_textures=True, mesh_smooth_type='FACE')


def bake_texture(objects, path, size=1024, shade=0.6, samples=48, rough=0.65, name=None, soften=3, sheen=0.0,
                 uv_angle=66.0, uv_margin=0.012, pack_margin=None):
    """Join `objects` into one mesh and bake their flat colours, darkened in the creases, into one
    image. This is what stops a flat-coloured model looking like plastic, and it turns several
    MeshParts into one.

    Returns the joined object. Its single material has the image wired straight into Base Color,
    the only wiring Roblox's importer reads. `shade` is how dark the deepest crease gets (0 to 1).
    `soften` blurs the shading by about that many pixels, so that where two shapes meet there is a
    soft shadow and not a thin dark line (on a face those lines read as cracks).
    `sheen` adds the soft pale rim that fuzzy cloth and fur have (it shows in renders here; in
    Roblox the matte look comes from the part's material or a roughness map).
    `uv_angle` and `uv_margin` steer the automatic unwrap. A model made of many small shapes wastes
    most of the image on the gaps between its pieces (the dragon used 15% of it); a smaller margin
    and a wider angle give it far more pixels (39% at 85 degrees and 0.004), at the price of a
    little colour bleeding between neighbouring pieces when seen from far away.
    `pack_margin`, when given, packs the pieces again by their real outlines, turned to any angle,
    with that gap between them. The automatic unwrap packs each piece as its bounding box, which
    wastes most of a triangular wing or a curved feather: re-packed at 0.003, the dragon went from
    28% to 38% of the image and the phoenix from 23% to 41%.
    """
    import numpy as np
    if os.environ.get("PETS_FAST"):                  # a quick, coarser bake for pictures of several pets at once
        size, samples = min(size, 512), min(samples, 16)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device, sc.cycles.samples = 'CPU', samples
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name:
        ob.name = ob.data.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(uv_angle), island_margin=uv_margin)
    if pack_margin is not None:
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(shape_method='CONCAVE', rotate=True, rotate_method='ANY',
                                margin_method='FRACTION', margin=pack_margin)
    bpy.ops.object.mode_set(mode='OBJECT')

    def bake(kind, **kw):
        img = bpy.data.images.new("bake_" + kind, size, size, alpha=False)
        nodes = []
        for slot in ob.material_slots:
            tree = slot.material.node_tree
            n = tree.nodes.new("ShaderNodeTexImage")
            n.image = img
            tree.nodes.active = n
            nodes.append((tree, n))
        bpy.ops.object.bake(type=kind, margin=12, **kw)
        px = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        for tree, n in nodes:
            tree.nodes.remove(n)
        bpy.data.images.remove(img)
        return px.reshape(size, size, 4)

    colour = bake('DIFFUSE', pass_filter={'COLOR'})
    ao = bake('AO')[..., :1]
    for _ in range(2 if soften else 0):                           # two box blurs; reach stays inside the 12-pixel bake margin
        for axis in (0, 1):
            ao = sum(np.roll(ao, d, axis) for d in range(-soften, soften + 1)) / (2 * soften + 1)
    ao = np.clip((ao - 0.25) / 0.75, 0, 1) ** 0.8                 # stretch the useful range of the occlusion
    out = colour.copy()
    out[..., :3] = colour[..., :3] * (1 - shade * (1 - ao))
    out[..., 3] = 1.0
    final = bpy.data.images.new(os.path.splitext(os.path.basename(path))[0], size, size, alpha=False)
    final.pixels.foreach_set(out.ravel())
    final.filepath_raw, final.file_format = path, 'PNG'
    final.save()

    mat = bpy.data.materials.new((name or ob.name) + "_Baked")
    b = principled(mat)
    b.inputs["Roughness"].default_value = rough
    if sheen and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
        if "Sheen Roughness" in b.inputs:
            b.inputs["Sheen Roughness"].default_value = 0.5
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = final
    mat.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    # A plain grey roughness image as well, so that an importer that reads roughness maps makes the
    # surface as matte as it is here and not shiny by default. It sits beside the colour image.
    stem = os.path.splitext(path)[0]
    rough_path = (stem[:-len("_colour")] if stem.endswith("_colour") else stem) + "_rough.png"
    grey = bpy.data.images.new(os.path.splitext(os.path.basename(rough_path))[0], 8, 8, alpha=False)
    grey.pixels.foreach_set([rough, rough, rough, 1.0] * 64)
    grey.filepath_raw, grey.file_format = rough_path, 'PNG'
    grey.save()
    grey.colorspace_settings.name = 'Non-Color'
    rtex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    rtex.image = grey
    mat.node_tree.links.new(rtex.outputs["Color"], b.inputs["Roughness"])
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    ob.data.polygons.foreach_set("material_index", [0] * len(ob.data.polygons))
    ob.data.update()
    return ob
