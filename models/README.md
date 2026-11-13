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
part (`Fox_Eye`, `Puppy_Gloss`, `Unicorn_GLOW_Horn`, `Dragon_GLOW`, `Bunny_Eyes`, `Cat_Gloss`, `Penguin_Eyes`, `Turtle_Eyes`, `Phoenix_GLOW`).

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal with short fur and a simple, friendly face | 11,644 | 20 |
| Puppy | Plush toy with stitches, patches and a fleecy nap | 8,926 | 8 |
| Unicorn | Low-poly, flat faces with a painted-card grain | 1,828 | 8 |
| Dragon | Adult obsidian fire dragon: wedge head, horn crown, raised red wings, glowing ember eyes and chest seams, 10.2 studs tall | 18,304 | 11 (6 since the redesign) |
| Bunny | Crochet toy with rows of yarn stitches and a scarf | 8,290 | 4 |
| Cat | Needle-felted grey tabby with a collar and bell | 9,996 | 5 |
| Penguin | Carved, hand-painted wooden toy with a bobble hat | 5,506 | 3 |
| Turtle | Storybook turtle with a plated shell and a sprout on top | 6,562 | 2 |
| Phoenix | Fire bird off a coat of arms: raised blade-feather wings, flame crest and train, glowing eyes and chest ember, 9.3 studs tall | 17,572 | 6 |

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

Known weak points, from the last review of each:

- Dragon: the texture fills only 28% of the image, so the small body scales turn to noise at mid
  range. The body barrel and thighs are smooth masses, the horns read grey-brown rather than black
  with bone tips, and at game distance the small head loses its face detail apart from the eyes.
- Bunny: the stitches are painted, not raised, and the pom-pom tail is not fluffy enough.
- Cat: leg and tail stripes are evenly spaced bands, and the outline is smooth.
- Fox: about 11,600 triangles, heavy for a pet if many are on screen.
- Unicorn: the horn is stacked steps, not a true spiral.
- Penguin: the wood is only half convincing. The forms are smooth like clay, with no chisel marks,
  and on the navy the grain can read as brushed felt.
- Turtle: only two rounds. The shell plates are smooth and pillow-like, the skin is a bright lime
  green, and from straight in front at a distance the head merges with the shell.
- Phoenix: the texture fills only 23% of the image (the hundreds of curved feathers pack poorly),
  so the drawn feather shafts blur away. Up close the head is a rounded, slightly boxy shape, the
  backs of the wings are plain with the wing arm reading as a dark rod, and the rows of chest
  feathers are an even spiky pattern.

## How the practice rounds work

Build, render, look at the render, score it honestly, fix a few of the weakest things, save as a
new version, repeat. A round's score is only what can be seen in the picture.
