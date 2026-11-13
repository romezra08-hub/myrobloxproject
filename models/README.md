# Pet models, made by script

Each pet is a Python script that builds the model in Blender from basic shapes, renders it for
review and exports a file for Roblox Studio. Nothing is copied from other games.

| File | What it is |
|---|---|
| `kit.py` | Shapes, colour helpers, texture baking and the FBX export |
| `review.py` | A fixed set of lights and cameras, so each round is judged from the same views |
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
   - **Puppy**: five flat-coloured parts (tan, cream, brown, collar, and the glossy eyes and nose).
     Fabric suits the fur parts.
   - **Unicorn**: six flat-coloured parts. Set `GLOW_Horn` to Neon.
4. One Blender unit is one stud. The front of the pet faces -Z in Studio.

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal, soft shading baked into a texture | 11,144 | 13 |
| Puppy | Plush toy with stitches and patches | 8,710 | 5 |
| Unicorn | Low-poly, flat faces | 1,448 | 5 |

None of them has been checked inside Roblox Studio yet; the renders are from Blender.

## How the practice rounds work

Build, render, look at the render, score it honestly, fix a few of the weakest things, save as a
new version, repeat. A round's score is only what can be seen in the picture.
