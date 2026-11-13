# Pet models, made by script

Each pet is a Python script that builds the model in Blender from basic shapes, renders it for
review and exports a file for Roblox Studio. Nothing is copied from other games.

| File | What it is |
|---|---|
| `kit.py` | Shapes, colour helpers, texture baking and the FBX export |
| `review.py` | A fixed set of lights and cameras, so each round is judged from the same views |
| `lineup.py` | Renders all the pets side by side at the same scale (`preview/lineup.png`) |
| `build_all.py` | Rebuilds every pet (Roblox file, texture, review sheet) and the line-up in one go |
| `SetupPets.lua` | Paste into Studio's Command Bar after importing a pet, to set it up in one go |
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

```bash
python models/build_all.py
```

`--quick` renders four views instead of eight.

## Put a pet into Roblox Studio

1. Download `export/<name>.fbx` (its textures are inside it).
2. In Studio: **Home > Import 3D**, pick the file, turn on **Anchored**, then **Import**.
3. Select what was imported in the Explorer, open `SetupPets.lua` here, copy all of it, paste it into
   the **Command Bar** (View > Command Bar) and press Enter. It makes the eyes glossy and any `GLOW`
   part Neon, switches off collisions, welds the parts to the body, puts the pivot under the feet and
   moves the pet to **ReplicatedStorage > Pets**. Ctrl+Z undoes it. It parses as valid Luau but has not been run in Studio yet.
4. One Blender unit is one stud. The front of the pet faces -Z in Studio.

Each pet arrives as two parts: `<Pet>_Body`, which carries the texture, and a small glossy or glowing
part (`Fox_Eye`, `Puppy_Gloss`, `Unicorn_GLOW_Horn`).

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal with short fur and a simple, friendly face | 11,644 | 20 |
| Puppy | Plush toy with stitches, patches and a fleecy nap | 8,926 | 8 |
| Unicorn | Low-poly, flat faces with a painted-card grain | 1,448 | 7 |

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
