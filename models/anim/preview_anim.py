"""Preview the pets' idle and walk animations in Blender, with the same maths as PetAnimator.lua.

    python models/anim/preview_anim.py                 # every pet
    python models/anim/preview_anim.py fox golem       # only these
    python models/anim/preview_anim.py --list          # the style each pet uses

For each pet it writes, into models/preview/anim/:
    <name>_idle.gif, <name>_walk.gif   the two clips (the walk moves forward at 16 studs/s, the
                                       camera following, over a checked floor)
    <name>_strip.png                   8 frames of each clip in two rows, for reviewing
and prints how low the lowest point of the pet goes (it must never go under the floor).

The motion maths below is a line-by-line port of PetAnimator.offset, and every number (the styles,
the per-pet table, the tuning constants) is read straight out of models/PetAnimator.lua, so the
preview shows exactly what the game will do. Change the Luau and this follows; change a formula in
one and change it in the other.

Each pet is built with its own script (build() then bake(), or made()), with PETS_FAST=1 for a quick
coarse texture, and kept in a cache (.blend), so a second run only renders. --rebuild ignores it.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.dirname(HERE)
LUA = os.path.join(MODELS, "PetAnimator.lua")
OUT = os.path.join(MODELS, "preview", "anim")


# ---- the tables and constants, read from PetAnimator.lua ------------------------------------------

def _block(src, start):
    """The text of the table that opens on the line starting with `start`, up to its closing brace
    at the start of a line."""
    i = src.index(start)
    j = src.index("\n}", i)
    return src[src.index("{", i) + 1:j]


def _numbers(text):
    return {k: float(v) for k, v in re.findall(r"\b(\w+)\s*=\s*(-?\d+(?:\.\d+)?)\b", text)}


def load_lua(path=LUA):
    src = open(path).read()
    consts = {k: float(v) for k, v in re.findall(r"^local (\w+) = (-?\d+(?:\.\d+)?)\b", src, re.M)}
    consts["TAU"] = 2 * math.pi
    defaults = _numbers(_block(src, "local DEFAULTS"))
    styles = {}
    for name, body in re.findall(r"^\t(\w+) = \{\n(.*?)^\t\},", _block(src, "PetAnimator.STYLES"), re.M | re.S):
        styles[name] = _numbers(body)
    pets = {}
    for name, body in re.findall(r"^\t(\w+) = \{\s*(.*?)\s*\},", _block(src, "PetAnimator.PETS"), re.M | re.S):
        entry = _numbers(body)
        entry["style"] = re.search(r'style = "(\w+)"', body).group(1)
        pets[name] = entry
    amp_fields = re.findall(r'"(\w+)"', _block(src, "local AMP_FIELDS"))
    period_fields = re.findall(r'"(\w+)"', _block(src, "local PERIOD_FIELDS"))
    return consts, defaults, styles, pets, amp_fields, period_fields


C, DEFAULTS, STYLES, PETS, AMP_FIELDS, PERIOD_FIELDS = load_lua()


# ---- the port of PetAnimator's maths ---------------------------------------------------------------

def profile(pet_name, style_name=None):
    entry = PETS.get(pet_name.lower(), {"style": "walker"})
    style = STYLES.get(style_name or entry["style"], STYLES["walker"])
    p = dict(DEFAULTS)
    p.update(style)
    for key, value in entry.items():
        if key not in ("style", "amp", "speed"):
            p[key] = value
    amp, speed = entry.get("amp", 1), entry.get("speed", 1)
    for key in AMP_FIELDS:
        p[key] *= amp
    for key in PERIOD_FIELDS:
        p[key] /= speed
    p["walkHz"] *= speed
    return p


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def ease(x):
    return x * x * (3 - 2 * x)


def look_shape(u):
    if u < 0 or u >= 1:
        return 0.0
    if u < 0.18:
        return ease(u / 0.18)
    if u < 0.45:
        return 1.0
    if u < 0.63:
        return 1 - 1.65 * ease((u - 0.45) / 0.18)
    if u < 0.85:
        return -0.65
    return -0.65 * (1 - ease((u - 0.85) / 0.15))


def raise_shape(u):
    if u < 0 or u >= 1:
        return 0.0
    return ease(min(u / 0.15, 1)) * ease(min((1 - u) / 0.15, 1))


def walk_hz(p, height, speed):
    size_factor = clamp(math.sqrt(C["REF_SIZE"] / max(height, 0.1)), 0.5, 1.4)
    speed_factor = clamp(0.6 + 0.4 * speed / C["REF_SPEED"], 0.6, 1.2)
    return p["walkHz"] * size_factor * speed_factor


def new_state(width, height, length, seed):
    return {"time": seed * 97, "cycle": (seed * 7) % 1, "blend": 0.0, "speed": 0.0, "turn": 0.0, "heading": 0.0,
            "hasHeading": False, "height": height, "width": width, "length": length}


def offset_parts(p, state, t, speed):
    """PetAnimator.offset, returning (x, y, cy, rx, ry, rz): the CFrame is
    CFrame.new(x, y + cy, 0) * CFrame.fromEulerAnglesYXZ(rx, ry, rz) * CFrame.new(0, -cy, 0)."""
    TAU = C["TAU"]
    h = state["height"]
    e = ease(clamp(state["blend"], 0, 1))
    i = 1 - e
    x, y = 0.0, p["hover"] * h
    pitch = yaw = roll = 0.0

    breath_angle = TAU * t / p["breathPeriod"]
    y += i * p["breath"] * h * (0.5 - 0.5 * math.cos(breath_angle))
    pitch += i * p["breathPitch"] * math.sin(breath_angle)
    u = (t % p["lookEvery"]) / p["lookTime"]
    look = look_shape(u)
    yaw += i * p["look"] * look
    roll += i * p["lookTilt"] * look
    pitch -= i * p["lookRaise"] * raise_shape(u)
    sway = math.sin(TAU * t / p["swayPeriod"])
    roll += i * p["sway"] * sway
    x += i * p["swaySide"] * h * sway
    yaw += i * p["spin"] * math.sin(TAU * t / p["spinPeriod"])
    figure_angle = TAU * t / p["figurePeriod"]
    x += i * p["figure"] * h * math.sin(figure_angle)
    y += i * p["figure"] * h * 0.5 * math.sin(2 * figure_angle)
    roll += i * p["figureBank"] * math.cos(figure_angle)
    if p["idleHop"] > 0:
        since = t % p["idleHopEvery"]
        if since < p["idleHopTime"]:
            hx = since / p["idleHopTime"]
            y += i * p["idleHop"] * h * math.sin(math.pi * hx)
            pitch -= i * p["idleHopTilt"] * math.sin(TAU * hx)
        else:
            r = (since - p["idleHopTime"]) / p["wobbleTime"]
            if r < 1:
                roll += i * p["wobble"] * math.sin(TAU * 1.5 * r) * (1 - r) * (1 - r)

    amp = e * clamp(0.55 + 0.45 * speed / C["REF_SPEED"], 0.55, 1.15)
    beat_pos = state["cycle"] * p["beats"]
    beat = math.floor(beat_pos)
    bx = beat_pos - beat
    hop = nod_shape = wob = 0.0
    if bx < p["duty"]:
        hx = bx / p["duty"]
        s = math.sin(math.pi * hx)
        hop = s * s + (s - s * s) * p["sharp"]
        nod_shape = math.sin(TAU * hx)
    else:
        r = (bx - p["duty"]) / (1 - p["duty"])
        wob = math.sin(TAU * 1.5 * r) * (1 - r) * (1 - r)
    hop *= (1 - p["skip"]) if beat % 2 == 1 else (1 + p["skip"])
    swing = math.sin(math.pi * beat_pos)
    impact = (bx / C["IMPACT_TIME"]) * math.exp(1 - bx / C["IMPACT_TIME"])
    y += amp * p["bounce"] * h * hop
    pitch += amp * (p["lean"] - p["nod"] * nod_shape + p["impact"] * impact)
    roll += amp * (p["roll"] * swing + p["wobble"] * wob)
    yaw += amp * p["yaw"] * swing
    x += amp * p["side"] * h * swing

    roll += clamp(state["turn"] * p["bank"], -p["bankMax"], p["bankMax"])

    rx, ry, rz = -math.radians(pitch), math.radians(yaw), math.radians(roll)
    cy = p["pivot"] * h
    lowest = (y + cy - cy * math.cos(rz) * math.cos(rx)
              - abs(p["foot"] * state["width"] * 0.5 * math.sin(rz) * math.cos(rx))
              - abs(p["foot"] * state["length"] * 0.5 * math.sin(rx)))
    if lowest < 0:
        y -= lowest
    return x, y, cy, rx, ry, rz


def step(p, state, dt, heading, speed):
    """PetAnimator:Step without the model: advances the state; heading is the base's yaw in radians.
    Then offset_parts(p, state, state["time"], state["speed"]) is what Step would apply."""
    TAU = C["TAU"]
    s = state
    dts = clamp(dt, 0, 0.1)
    s["time"] += dt
    s["speed"] += (speed - s["speed"]) * (1 - math.exp(-C["SPEED_RATE"] * dts))
    s["cycle"] = (s["cycle"] + dt * walk_hz(p, s["height"], s["speed"])) % 2
    target = clamp((speed - C["WALK_START"]) / (C["WALK_FULL"] - C["WALK_START"]), 0, 1)
    s["blend"] += (target - s["blend"]) * (1 - math.exp(-C["BLEND_RATE"] * dts))
    rate = 0.0
    if s["hasHeading"] and dt > 0:
        delta = (heading - s["heading"] + math.pi) % TAU - math.pi
        rate = clamp(delta / dt, -C["TURN_MAX"], C["TURN_MAX"])
    s["heading"], s["hasHeading"] = heading, True
    s["turn"] += (rate - s["turn"]) * (1 - math.exp(-C["TURN_RATE"] * dts))


def offset_matrix(p, state, t, speed):
    """The offset as a 4x4 matrix in Roblox's axes (X right, Y up, -Z forward), as nested lists."""
    x, y, cy, rx, ry, rz = offset_parts(p, state, t, speed)
    cx_, sx_ = math.cos(rx), math.sin(rx)
    cy_, sy_ = math.cos(ry), math.sin(ry)
    cz_, sz_ = math.cos(rz), math.sin(rz)
    Rx = [[1, 0, 0], [0, cx_, -sx_], [0, sx_, cx_]]
    Ry = [[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]]
    Rz = [[cz_, -sz_, 0], [sz_, cz_, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
    R = mul(mul(Ry, Rx), Rz)                       # fromEulerAnglesYXZ: Z first, then X, then Y
    # translate(x, y + cy, 0) * R * translate(0, -cy, 0)
    t_ = [x - R[0][1] * cy, y + cy - R[1][1] * cy, -R[2][1] * cy]
    return [R[0] + [t_[0]], R[1] + [t_[1]], R[2] + [t_[2]], [0, 0, 0, 1]]


# Roblox axes to Blender's: Blender (x, y, z) = (-X, Z, Y) of Roblox; pets face -Y here and -Z there.
M = [[-1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]


def to_blender(m):
    from mathutils import Matrix
    mm = Matrix(M)
    return mm @ Matrix(m) @ mm.transposed()


# ---- rendering ---------------------------------------------------------------------------------

def list_styles():
    from build_all import pets as all_pets
    for name in all_pets() + [n for n in PETS if n not in all_pets()]:
        entry = PETS.get(name)
        extra = {k: v for k, v in (entry or {}).items() if k != "style"}
        print("%-12s %-8s %s%s" % (name, entry["style"] if entry else "walker (no entry)", extra or "",
                                  "" if os.path.exists(os.path.join(MODELS, "pets", name + ".py")) else "  [no model yet]"))


class Pet:
    def __init__(self, objects):
        self.objects = objects

    def bounds(self):
        from mathutils import Vector
        pts = [ob.matrix_world @ Vector(c) for ob in self.objects for c in ob.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return lo, hi


def load_pet(name, cache, rebuild):
    """Build and bake the pet with its own script, or open it from the cache."""
    import bpy
    import addon_utils
    import kit
    blend = os.path.join(cache, name + ".blend")
    script = os.path.join(MODELS, "pets", name + ".py")
    if not rebuild and os.path.exists(blend) and os.path.getmtime(blend) > os.path.getmtime(script):
        bpy.ops.wm.open_mainfile(filepath=blend)
        for mod in ("cycles",):
            addon_utils.enable(mod, default_set=True)
        objects = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH']
        return Pet(objects)
    os.environ["PETS_FAST"] = "1"
    kit.fresh()
    sc = bpy.context.scene
    sc.render.threads_mode, sc.render.threads = 'FIXED', THREADS
    mod = __import__(name)
    texture = os.path.join(cache, name + "_colour.png")
    if hasattr(mod, "made"):
        prop = mod.made(texture)
    else:
        prop = mod.build()
        mod.bake(prop, texture)
    keep = set(prop.objects)
    for ob in list(bpy.context.scene.objects):          # anything a script left lying around
        if ob not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    return Pet(list(prop.objects))


def checker_floor(ground):
    import bpy
    import kit
    m = bpy.data.materials.new("AnimFloor")
    b = kit.principled(m)
    b.inputs["Roughness"].default_value = 0.9
    t = m.node_tree
    co = t.nodes.new("ShaderNodeTexCoord")
    ch = t.nodes.new("ShaderNodeTexChecker")
    ch.inputs["Color1"].default_value = (*kit.srgb("#8A8D91"), 1)
    ch.inputs["Color2"].default_value = (*kit.srgb("#787B80"), 1)
    ch.inputs["Scale"].default_value = 120.0          # squares of about 2 studs (Generated spans the 240-stud floor)
    t.links.new(co.outputs["Generated"], ch.inputs["Vector"])
    t.links.new(ch.outputs["Color"], b.inputs["Base Color"])
    ground.data.materials.clear()
    ground.data.materials.append(m)


def render_pet(name, a):
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector
    import review

    pet = load_pet(name, a.cache, a.rebuild)
    sc = bpy.context.scene
    sc.render.threads_mode, sc.render.threads = 'FIXED', THREADS
    bpy.context.view_layer.update()
    lo, hi = pet.bounds()
    pivot = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    width, length, height = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
    p = profile(name)
    rel = {ob: Matrix.Translation(-pivot) @ ob.matrix_world.copy() for ob in pet.objects}
    verts = {}
    for ob in pet.objects:                              # for measuring the lowest point exactly
        co = np.empty(len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        verts[ob] = np.c_[co, np.ones(len(co))]

    rig = review.Rig(pet, samples=a.samples)
    rig.ground.scale = (3, 3, 1)
    checker_floor(rig.ground)
    sc.cycles.use_adaptive_sampling = True
    sc.render.resolution_x, sc.render.resolution_y = a.px, int(a.px * 0.75)
    sc.render.image_settings.file_format = 'PNG'
    follow = bpy.data.objects.new("Follow", None)      # camera and lights travel with a walking pet
    sc.collection.objects.link(follow)
    for ob in sc.objects:
        if ob.type == 'LIGHT':
            ob.parent = follow
    # 5-stud blocks along the far side of the path, so one is always in view
    d0 = rig.dummy
    d0.location = (hi.x + 2.6, pivot.y + 2.0, lo.z + 2.5)
    for k in range(1, 9):
        d = d0.copy()
        d.location.y = d0.location.y - 10.0 * k
        sc.collection.objects.link(d)
    hover_top = height * (1 + p["hover"] + p["breath"] + p["figure"] + 0.05)
    span = max(width, length, hover_top, 2.0)
    target = Vector((pivot.x, pivot.y, lo.z + hover_top * 0.45))
    view = Vector((-1.0, -0.55, 0.33)).normalized()
    dist = (span * 0.6 + 0.6) / (math.tan(math.radians(15)) * 0.75)   # 30 degrees is the width; the height is 3/4 of it
    cam = review._camera("C_anim", target + view * dist, target, 30)
    cam.parent = follow
    sc.camera = cam

    folder = os.path.join(a.cache, name + "_frames")
    os.makedirs(folder, exist_ok=True)
    stats = {}
    clips = {}
    for clip in ("idle", "walk"):
        state = new_state(width, height, length, 0.0)
        frames = a.frames
        if clip == "idle":
            duration = min(p["lookEvery"], 7.0)
            t0, speed = p["lookEvery"] - 0.4, 0.0
            state["blend"] = 0.0
        else:
            speed = a.speed
            hz = walk_hz(p, height, speed)
            loop = (2.0 / p["beats"]) / hz                 # seconds until the walk repeats exactly
            duration = loop * max(1, round(1.3 / loop))
            t0 = 0.0
            state["blend"] = 1.0
        lows, lifts, paths = [], [], []
        for f in range(frames):
            dt = duration * f / frames
            t = t0 + dt
            if clip == "walk":
                state["cycle"] = (hz * dt) % 2
            base = Matrix.Translation(pivot + Vector((0, -speed * dt, 0)))
            off = to_blender(offset_matrix(p, state, t, speed))
            follow.location = (0, -speed * dt, 0)
            low = 1e9
            for ob in pet.objects:
                ob.matrix_world = base @ off @ rel[ob]
                w = np.array(ob.matrix_world)
                low = min(low, float((verts[ob] @ w.T)[:, 2].min()))
            lows.append(low - lo.z)
            png = os.path.join(folder, "%s_%02d.png" % (clip, f))
            paths.append(png)
            if not a.no_render:
                sc.render.filepath = png
                bpy.ops.render.render(write_still=True)
        stats[clip] = {"lowest": round(min(lows), 3), "highest_low": round(max(lows), 3),
                       "duration": round(duration, 2)}
        clips[clip] = (paths, duration)
    for ob in pet.objects:
        ob.matrix_world = Matrix.Translation(pivot) @ rel[ob]

    if a.no_render:
        return stats
    write_outputs(name, clips, stats, a.px)
    return stats


def write_outputs(name, clips, stats, px):
    """The two GIFs and the review strip: 8 frames of each clip, then all its frames averaged, which
    shows how far the pet moves (the blur) even when the movement is small."""
    from PIL import Image, ImageDraw
    os.makedirs(OUT, exist_ok=True)
    strip_rows = []
    for clip, (paths, duration) in clips.items():
        imgs = [Image.open(q).convert("RGB") for q in paths]
        gif = [im.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in imgs]
        gif[0].save(os.path.join(OUT, "%s_%s.gif" % (name, clip)), save_all=True, append_images=gif[1:],
                    duration=max(20, int(round(1000 * duration / len(imgs) / 10.0)) * 10), loop=0, optimize=True)
        mean = imgs[0]
        for k, im in enumerate(imgs[1:], 2):
            mean = Image.blend(mean, im, 1.0 / k)
        step = max(1, len(imgs) // 8)
        strip_rows.append((clip, imgs[::step][:8] + [mean], duration))
    w, h = px, int(px * 0.75)
    strip = Image.new("RGB", (9 * w, 2 * (h + 20)), (18, 20, 24))
    draw = ImageDraw.Draw(strip)
    for r, (clip, imgs, duration) in enumerate(strip_rows):
        y = r * (h + 20)
        draw.text((6, y + 4), "%s  %s (%s)  %.2f s, every %.2f s shown   lowest point %+.3f studs" % (
            name, clip, p_style(name), duration, duration / 8, stats[clip]["lowest"]), fill=(235, 235, 235))
        draw.text((8 * w + 6, y + 4), "all frames averaged", fill=(235, 235, 235))
        for k, im in enumerate(imgs):
            strip.paste(im, (k * w, y + 20))
    strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(os.path.join(OUT, name + "_strip.png"), optimize=True)


def p_style(name):
    return PETS.get(name, {"style": "walker"})["style"]


THREADS = 2


def main():
    global THREADS
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--list", action="store_true", help="print each pet's style and stop")
    ap.add_argument("--px", type=int, default=320)
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--speed", type=float, default=16.0, help="walking speed in studs per second")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "petanim_cache"))
    ap.add_argument("--rebuild", action="store_true", help="build the pets again even if cached")
    ap.add_argument("--no-render", action="store_true", help="only measure the lowest points")
    ap.add_argument("--one", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    THREADS = a.threads
    sys.path.insert(0, MODELS)
    sys.path.insert(0, os.path.join(MODELS, "pets"))
    if a.list:
        list_styles()
        return
    os.makedirs(a.cache, exist_ok=True)
    if a.one:                                          # one pet, in this process
        stats = render_pet(a.names[0], a)
        print("ANIMSTATS " + json.dumps({a.names[0]: stats}), flush=True)
        return
    from build_all import pets as all_pets
    names = a.names or all_pets()
    passthrough = [arg for arg in sys.argv[1:] if arg not in names]
    for name in names:                                 # each pet in a fresh process: no leftovers between them
        if not os.path.exists(os.path.join(MODELS, "pets", name + ".py")):
            print("skipped %s: no pets/%s.py yet" % (name, name), flush=True)
            continue
        run = subprocess.run([sys.executable, os.path.abspath(__file__), name, "--one"] + passthrough,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        line = [ln for ln in run.stdout.splitlines() if ln.startswith("ANIMSTATS ")]
        print(line[-1][10:] if line else "FAILED %s\n%s" % (name, run.stdout[-3000:]), flush=True)


if __name__ == "__main__":
    main()
