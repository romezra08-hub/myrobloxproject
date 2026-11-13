# Pet models, made by script

Each pet is a Python script that builds the model in Blender from basic shapes, renders it for
review and exports a file for Roblox Studio. Nothing is copied from other games.

| File | What it is |
|---|---|
| `kit.py` | Shapes, colour helpers, texture baking and the FBX export |
| `review.py` | A fixed set of lights and cameras, so each round is judged from the same views |
| `lineup.py` | Renders all the pets side by side at the same scale (`preview/lineup.png`) |
| `pets/<name>.py` | The current best version of a pet |
| `pets/<name>_v1.py`, `_v2.py`, ... | Every practice round, kept so a change can be undone |
| `export/<name>.fbx` and `<name>_colour.png` | What goes into Roblox Studio |
| `preview/<name>.png` | The review sheet of the current version |

## Run it

Blender itself is not needed, only its Python module:

```bash
pip install bpy pillow
```

```bash
python models/pets/fox.py --review out/fox.png --export models/export/fox.fbx
```

`--quick` renders four views instead of eight.

## Put a pet into Roblox Studio

1. Download `export/<name>.fbx` (the texture is inside it).
2. In Studio: **Home > Import 3D**, pick the file, turn on **Anchored**, then **Import**.
3. What arrives:
   - **Fox**: two parts, `Fox_Body` (textured) and `Fox_Eye`. Set `Fox_Eye` to a glossy material
     such as SmoothPlastic or Glass.
   - **Puppy**: two parts, `Puppy_Body` (textured) and `Puppy_Gloss` (eyes and nose; make it glossy).
   - **Unicorn**: two parts, `Unicorn_Body` (textured) and `Unicorn_GLOW_Horn`. Set the horn to Neon.
4. One Blender unit is one stud. The front of the pet faces -Z in Studio.

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal with short fur and a simple, friendly face | 11,116 | 19 |
| Puppy | Plush toy with stitches, patches and a fleecy nap | 8,710 | 7 |
| Unicorn | Low-poly, flat faces | 1,448 | 6 |

Each has its colours and soft shading baked into one texture, so it arrives as two parts.

## Why they do not look like plastic

Smooth shapes in one flat colour read as cheap plastic. Three things in `kit.py` work against that,
and all of them end up in the texture Roblox reads:

- `furry(material)` paints short fur or a cloth nap: fine streaks and soft mottling.
- `scaly(material)` paints a skin of small scales with darker joins.
- `bake_texture(...)` adds soft shadow in the creases and writes a matte roughness image
  (`<name>_rough.png`) next to the colour image.

If a pet still looks shiny in Studio, open its body part's SurfaceAppearance and set RoughnessMap to
that `_rough.png` image.

None of them has been checked inside Roblox Studio yet; the renders are from Blender.

## How the practice rounds work

Build, render, look at the render, score it honestly, fix a few of the weakest things, save as a
new version, repeat. A round's score is only what can be seen in the picture.
