"""All the pets side by side in one picture, at the same scale.

    python models/lineup.py --out models/preview/lineup.png

Every pet with a current script in pets/ is included. Each is built and baked on its own, well
away from the others, so that one pet's shading is not darkened by its neighbours, and then they
are stood in a row with a gap between them.
"""
import argparse
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pets"))
import kit  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from build_all import pets  # noqa: E402

ORDER = ["fox", "puppy", "cat", "bunny", "penguin", "turtle", "unicorn", "dragon", "phoenix", "griffin", "golem", "wolf", "driller"]     # left to right; any other pet follows these
TURN = {"fox": -20, "unicorn": 55, "dragon": 38, "wolf": 40, "driller": 40}                  # degrees; long pets are turned to show their side
GAP = 1.1


class Group:
    """Several props treated as one, for the review rig."""

    def __init__(self, props):
        self.props = props

    def bounds(self):
        los, his = zip(*(p.bounds() for p in self.props))
        return (Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los))),
                Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "preview", "lineup.png"))
    ap.add_argument("--width", type=int, default=1800)
    a = ap.parse_args()
    os.environ["PETS_FAST"] = "1"                        # coarser textures are fine at this size, and much quicker
    have = pets()
    row = [n for n in ORDER if n in have] + [n for n in have if n not in ORDER]
    kit.fresh()
    tmp = tempfile.mkdtemp()
    props = []
    for i, name in enumerate(row):
        mod = __import__(name)
        prop = mod.build()
        mod.bake(prop, os.path.join(tmp, name + "_colour.png"))
        for ob in prop.objects:
            ob.location.x = 300 + 60 * i                 # out of the way while the next one is baked
        props.append(prop)
    edge = 0.0
    for prop, name in zip(props, row):                   # stand them in a row, each just clear of the last
        for ob in prop.objects:
            ob.location.x, ob.rotation_euler.z = 0.0, math.radians(TURN.get(name, -12))
        bpy.context.view_layer.update()
        lo, hi = prop.bounds()
        for ob in prop.objects:
            ob.location.x = edge - lo.x
            ob.location.y = -(lo.y + hi.y) / 2
        edge += (hi.x - lo.x) + GAP
    bpy.context.view_layer.update()

    import review
    group = Group(props)
    rig = review.Rig(group, samples=28)
    rig.ground.scale = (6, 6, 1)                         # a long row would otherwise run off the edge of the floor
    lo, hi = group.bounds()
    wide, tall = hi.x - lo.x + 3.2, hi.z - lo.z          # room for the 5-stud block on the right
    target = Vector(((lo.x + hi.x) / 2 - 1.0, 0, lo.z + tall * 0.4))  # left of centre: the near (left) end looks bigger
    half = math.radians(15)
    aspect = min(0.6, max(0.34, (tall * 1.35 + 0.8) / wide))
    away = (wide / 2 + 1.0) / math.tan(half)
    cam = review._camera("C_lineup", target + Vector((-0.28, -1.0, 0.24)).normalized() * away, target, 30)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = a.width, int(a.width * aspect)
    sc.render.filepath = os.path.abspath(a.out)
    bpy.ops.render.render(write_still=True)
    print("lineup", a.out, row)


if __name__ == "__main__":
    main()
