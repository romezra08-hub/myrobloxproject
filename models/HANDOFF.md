# Hand-off: Mine an Egg models

For a new Claude session (for example one on the PC with the Roblox Studio MCP). Read this, then
`models/README.md`.

## What exists (all made by script in headless Blender, nothing copied)
- **Pets** (`models/pets/<name>.py`, exports in `models/export/`, sheets in `models/preview/`):
  fox, puppy, cat, bunny, penguin, turtle, unicorn, dragon, phoenix, griffin, golem, wolf, driller.
  Remade or polished on 13–14 Nov: unicorn, penguin, turtle (tortoise), wolf, cat, griffin, driller.
  Golem and phoenix were being polished in the cloud session when this was written.
- **Eggs** (`models/eggs/eggs.py`): meadow, ember, phoenix, storm, crystal, shadow.
- **Pickaxes** (`models/tools/pickaxes.py`): wooden, iron, gold, emerald, ember.
- **Ore rocks** (`models/props/ores.py`): stone, coal, iron, gold, emerald, ember, egg geode.
- **Studio scripts**: `SetupPets.lua` sets up pets, eggs (Eggs folder) and ore rocks (Ores folder, solid);
  `SetupTools.lua` turns pickaxes into Tools. Paste into the Command Bar after Import 3D.
- Nothing has been checked inside Roblox Studio yet.

## What the user wants
- Pets that look good: not plastic, not childish (big creatures), never creepy, not like a generic simulator.
  Each pet a different style.
- Next step the user asked for: remake the pets that **already exist in their Mine an Egg place**.
  The cloud session could not see the place. With the Studio MCP, list the pets in the place,
  judge which look weak or creepy, and remake those in the same way (rounds, honest review of renders).
- Import the finished FBX files into the place and run the setup scripts.

## How to work
- Blender: `pip install bpy pillow` (bpy 5.3 worked; Cycles on CPU).
- Build one pet: `python models/pets/fox.py --review out.png --export models/export/fox.fbx`.
- Line-up of all pets: `python models/lineup.py`.
- Commit messages end with the co-author and session lines used in the git log.
- The user is cost-conscious; keep about two build agents at a time.
