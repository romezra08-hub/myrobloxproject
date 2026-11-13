"""A fixed review rig: the same lights, cameras and passes every round, so that renders of
one version can be compared with the next. See the quality loop in models/README.md."""
import math
import os

import bpy
from mathutils import Vector

import kit


def _aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def _light(name, loc, target, watts, size, colour=(1, 1, 1)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.size, data.color = watts, size, colour
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    _aim(ob, target)
    return ob


def _camera(name, loc, target, fov):
    data = bpy.data.cameras.new(name)
    data.angle = math.radians(fov)
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    _aim(ob, target)
    return ob


class Rig:
    def __init__(self, prop, samples=40, focus=None):
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = 'CPU', samples, True
        sc.view_settings.view_transform = 'Standard'
        lo, hi = prop.bounds()
        c, size = (lo + hi) / 2, max(hi - lo)
        self.c, self.size, self.height = c, size, hi.z - lo.z
        self.world = bpy.data.worlds.new("ReviewWorld")
        sc.world = self.world
        try:
            self.world.use_nodes = True
        except Exception:
            pass
        self.bg = next(n for n in self.world.node_tree.nodes if n.type == 'BACKGROUND')
        self._world((0.045, 0.05, 0.06))
        # mid-grey ground, so floating parts show by their shadows
        ground = kit.rounded_box((80, 80, 0.2), n=20, cuts=0)
        self.ground = self._object("ReviewGround", ground, kit.material("ReviewGrey", "#8A8D91", rough=0.9), (0, 0, lo.z - 0.1))
        # a 5-stud block, the height of a Roblox character, for scale
        dummy = kit.rounded_box((2, 1, 5), n=8, cuts=2)
        self.dummy = self._object("ReviewDummy", dummy, kit.material("ReviewDummy", "#5C7C99", rough=0.7), (hi.x + 1.6, hi.y + 1.4, lo.z + 2.5))
        _light("Key", c + Vector((-0.9, -1.2, 1.5)) * size * 1.6, c, 165 * size * size, size * 1.6)
        _light("Fill", c + Vector((1.3, -0.8, 0.4)) * size * 1.6, c, 55 * size * size, size * 2.2, (0.85, 0.92, 1.0))
        _light("Rim", c + Vector((0.5, 1.3, 1.1)) * size * 1.6, c, 150 * size * size, size * 1.2, (1.0, 0.95, 0.85))
        d = size * 2.7
        look = Vector(focus) if focus else c + Vector((0, 0, self.height * 0.2))
        self.cams = {
            "front 3/4": _camera("C_front34", c + Vector((-0.55, -1.0, 0.3)).normalized() * d, c, 34),
            "front": _camera("C_front", c + Vector((0, -1.0, 0.08)).normalized() * d, c, 34),
            "side": _camera("C_side", c + Vector((-1.0, -0.02, 0.1)).normalized() * d, c, 34),
            "back 3/4": _camera("C_back34", c + Vector((-0.6, 1.0, 0.4)).normalized() * d, c, 34),
            "top": _camera("C_top", c + Vector((0, -0.08, 1.0)).normalized() * d, c, 34),
            "close-up": _camera("C_close", look + Vector((-0.35, -1.0, 0.12)).normalized() * size * 1.35, look, 30),
            "game distance": _camera("C_game", Vector((c.x - 3.5, c.y - 17, lo.z + 5.5)), c + Vector((1.5, 0, 0.5)), 70),
        }
        self.clay = kit.material("ReviewClay", "#8E8A84", rough=0.7)
        self.black = bpy.data.materials.new("ReviewBlack")
        b = kit.principled(self.black)
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Roughness"].default_value = 1.0
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.0
        self.wire = self._wire_material()

    def _world(self, rgb, strength=1.0):
        self.bg.inputs[0].default_value = (*rgb, 1.0)
        self.bg.inputs[1].default_value = strength

    def _object(self, name, bm, mat, loc):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.location = loc
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def _wire_material(self):
        m = bpy.data.materials.new("ReviewWire")
        b = kit.principled(m)
        b.inputs["Roughness"].default_value = 0.8
        t = m.node_tree
        w = t.nodes.new("ShaderNodeWireframe")
        w.use_pixel_size = True
        w.inputs[0].default_value = 0.9
        ramp = t.nodes.new("ShaderNodeMix")
        ramp.data_type = 'RGBA'
        ramp.inputs[6].default_value = (0.72, 0.72, 0.7, 1)
        ramp.inputs[7].default_value = (0.02, 0.02, 0.03, 1)
        t.links.new(w.outputs[0], ramp.inputs[0])
        t.links.new(ramp.outputs[2], b.inputs["Base Color"])
        return m

    def render(self, path, view, look="full", px=512):
        """look: full, clay, wire or silhouette."""
        sc, layer = bpy.context.scene, bpy.context.view_layer
        sc.camera = self.cams[view]
        sc.render.resolution_x = sc.render.resolution_y = px
        sc.render.filepath = path
        outline = look == "silhouette"
        layer.material_override = {"clay": self.clay, "wire": self.wire, "silhouette": self.black}.get(look)
        self.ground.hide_render = self.dummy.hide_render = outline
        self._world((1, 1, 1) if outline else (0.045, 0.05, 0.06), 1.0)
        for ob in sc.objects:
            if ob.type == 'LIGHT':
                ob.hide_render = outline
        bpy.ops.render.render(write_still=True)
        layer.material_override = None
        return path

    def sheet(self, out, shots, px=512, cols=4, title=""):
        """Render the (view, look) pairs and paste them into one labelled contact sheet."""
        from PIL import Image, ImageDraw
        folder = os.path.splitext(out)[0] + "_views"
        os.makedirs(folder, exist_ok=True)
        tiles = []
        for view, look in shots:
            p = os.path.join(folder, "%s_%s.png" % (view.replace(" ", "").replace("/", ""), look))
            self.render(p, view, look, px)
            tiles.append((Image.open(p).convert("RGB"), "%s, %s" % (view, look)))
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * px, rows * px + (28 if title else 0)), (18, 20, 24))
        draw = ImageDraw.Draw(sheet)
        if title:
            draw.text((8, 7), title, fill=(235, 235, 235))
        for i, (img, label) in enumerate(tiles):
            x, y = (i % cols) * px, (i // cols) * px + (28 if title else 0)
            sheet.paste(img, (x, y))
            draw.rectangle((x, y, x + 8 + 7 * len(label), y + 18), fill=(0, 0, 0))
            draw.text((x + 4, y + 3), label, fill=(255, 255, 255))
        sheet.save(out)
        return out


STANDARD = [("front 3/4", "full"), ("front", "full"), ("side", "full"), ("back 3/4", "full"),
            ("close-up", "full"), ("game distance", "full"), ("front 3/4", "clay"), ("game distance", "silhouette")]
