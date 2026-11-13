"""All the pets side by side in one picture, at the same scale.

    python models/lineup.py --out models/preview/lineup.png

Each pet is built and baked on its own, well away from the others, so that one pet's shading
is not darkened by its neighbours, and then they are stood in a row.
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

ROW = [("fox", -3.5, -20), ("puppy", 0.0, -12), ("unicorn", 3.8, 55)]      # script, place along the row, turn in degrees


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
    ap.add_argument("--width", type=int, default=1600)
    a = ap.parse_args()
    kit.fresh()
    tmp = tempfile.mkdtemp()
    props = []
    for i, (name, x, turn) in enumerate(ROW):
        mod = __import__(name)
        prop = mod.build()
        mod.bake(prop, os.path.join(tmp, name + ".png"))
        for ob in prop.objects:
            ob.location.x = 200 + 40 * i                 # out of the way while the next one is baked
        props.append(prop)
    for prop, (name, x, turn) in zip(props, ROW):
        for ob in prop.objects:
            ob.location.x, ob.rotation_euler.z = x, math.radians(turn)
    bpy.context.view_layer.update()

    import review
    group = Group(props)
    rig = review.Rig(group)
    lo, hi = group.bounds()
    c = (lo + hi) / 2
    target = Vector((c.x + 0.6, c.y, lo.z + (hi.z - lo.z) * 0.42))
    cam = review._camera("C_lineup", target + Vector((-0.3, -1.0, 0.26)).normalized() * 25.0, target, 30)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = a.width, int(a.width * 0.5)
    sc.render.filepath = os.path.abspath(a.out)
    bpy.ops.render.render(write_still=True)
    print("lineup", a.out)


if __name__ == "__main__":
    main()
