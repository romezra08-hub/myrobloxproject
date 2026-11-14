# Pet models, made by script

Each pet is a Python script that builds the model in Blender from basic shapes, renders it for
review and exports a file for Roblox Studio. Nothing is copied from other games.

| File | What it is |
|---|---|
| `kit.py` | Shapes, colour helpers, texture baking and the FBX export |
| `review.py` | A fixed set of lights and cameras, so each round is judged from the same views |
| `lineup.py` | Renders all the pets side by side at the same scale (`preview/lineup.png`) |
| `build_all.py` | Rebuilds every pet (Roblox file, texture, review sheet) and the line-up in one go |
| `SetupPets.lua` | Paste into Studio's Command Bar after importing a pet or an egg, to set it up in one go |
| `SetupTools.lua` | The same for a pickaxe: turns it into a Tool a player can hold |
| `pets/<name>.py` | The current best version of a pet |
| `pets/<name>_v1.py`, `_v2.py`, ... | Every practice round, kept so a change can be undone |
| `eggs/eggs.py` | All six hatching eggs (`--only storm` builds one); `eggs_v1.py`... are its rounds |
| `props/ores.py` | All seven mineable ore rocks (`--only gold` builds one); `ores_v1.py`... are its rounds |
| `tools/pickaxes.py` | All five pickaxes (`--only gold` builds one); `pickaxes_v1.py`... are its rounds |
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
   moves the pet to **ReplicatedStorage > Pets** (an egg goes to **ReplicatedStorage > Eggs**). Ctrl+Z undoes it. It parses as valid Luau but has not been run in Studio yet.
4. One Blender unit is one stud. The front of the pet faces -Z in Studio.

Each pet arrives as two parts: `<Pet>_Body`, which carries the texture, and a small glossy or glowing
part (`Fox_Eye`, `Puppy_Gloss`, `Unicorn_GLOW_Horn`, `Dragon_GLOW`, `Bunny_Eyes`, `Cat_Gloss`, `Penguin_Eyes`, `Turtle_Eyes`, `Phoenix_GLOW`, `Griffin_GLOW`, `Golem_GLOW`, `Wolf_GLOW`, `Driller_GLOW`).

## Put a pickaxe into Roblox Studio

1. Import `export/<name>_pickaxe.fbx` the same way, but leave **Anchored** off.
2. Select it, then paste all of `SetupTools.lua` into the Command Bar and press Enter. The textured
   part becomes the tool's `Handle`, any `GLOW` part turns Neon and is welded on, and the grip is set
   so the hand holds the shaft near the bottom with the head up and the pick forward. The tool goes to
   **ReplicatedStorage > Tools**; put a copy in **StarterPack** and press Play to try it.
3. If it sits wrong in the hand, change the tool's **Grip** settings in Properties
   (`GripPos` moves it, `GripForward`/`GripUp` turn it). Like the pet script, this has only been
   checked as valid Luau, not yet run in Studio.

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal with short fur and a simple, friendly face | 11,644 | 20 |
| Puppy | Plush toy with stitches, patches and a fleecy nap | 8,926 | 8 |
| Unicorn | Moonlight unicorn as a faceted low-poly sculpture: prancing horse, pearl-silver coat, sapphire-to-violet mane and tail, twisted glowing crystal horn, gold hooves | 5,864 | 15 (7 since the remake) |
| Dragon | Adult obsidian fire dragon: wedge head, horn crown, raised red wings, glowing ember eyes and chest seams, 10.2 studs tall | 18,304 | 11 (6 since the redesign) |
| Bunny | Crochet toy with rows of yarn stitches and a scarf | 8,290 | 4 |
| Cat | Needle-felted grey tabby with a collar and bell | 9,996 | 5 |
| Penguin | Whittled folk-art figure: knife-cut and gouged pale wood under thin worn milk paint, carved bobble hat, on a round oiled base | 7,437 | 12 (9 since the remake) |
| Turtle | Old forest tortoise in a naturalist storybook style: high domed shell with ridged growth rings, moss with mushrooms and a fern on top, olive scaly skin, calm amber eyes | 8,960 | 13 (11 since the remake) |
| Phoenix | Fire bird off a coat of arms: raised blade-feather wings, flame crest and train, glowing eyes and chest ember, 9.3 studs tall | 17,572 | 6 |
| Griffin | Storm griffin: white eagle head with glowing blue eyes, navy wings with lightning streaks, golden lion body, 9.5 studs tall | 17,594 | 6 |
| Golem | Ancient crystal golem: carved slate blocks with moss, emerald crystal clusters, glowing eye slots and rune cracks, 9.9 studs tall | 7,314 | 6 |
| Wolf | Shadow alpha wolf: long wedge muzzle, tall ears, slate blue-grey coat with a charcoal saddle, big silver mane of sculpted locks, violet crystals glowing along the spine, calm violet eyes, 7 studs tall | 15,032 | 19 (10 since the remake) |
| Driller | Mining machine shaped like a mole: worn mining-yellow armour over gunmetal, chrome drill in a glowing ring, light-bar visor, furnace grille, oversized shovel claws, exhaust stacks, dug-up gems on its back, 5.1 studs tall and 7.9 long | 11,844 | 12 |

Each has its colours and soft shading baked into one texture, so it arrives as two parts.

## The pickaxes

Five tiers, each modelled standing up with the pick pointing forward and the bottom of the shaft at
the origin, so `SetupTools.lua` can set the grip from the size alone. Review sheet: `preview/pickaxes.png`.
Textures are 512 px: next to 1024 px bakes at close-up size the difference could not be seen.

| Tier | Look | Triangles | Length (studs) |
|---|---|---|---|
| Wooden | Worn branch handle, knapped flint head, rope lashing | 1,484 | 4.5 |
| Iron | Dark hammered forged head with bright worn edges, leather grip, riveted straps | 1,136 | 4.7 |
| Gold | Engraved crescent head with a ruby, black lacquer shaft, red silk grip | 1,712 | 5.0 |
| Emerald | Winged faceted emerald blades with glowing veins and core, slate socket | 1,318 | 5.1 |
| Ember | Black obsidian head with glowing cracks held by a dragon claw, horn crown, scaled shaft, ember pommel | 2,094 | 5.2 |

Weak points: the metal, gold and gem shine is painted into the texture, so the highlights do not move
as the tool turns; the shafts of the top three are long and plain, so the heads do all the work; the
flint on the wooden one is the flattest material; the ember head is busy up close. None of it has been
held in Studio yet.

## The eggs

Six hatching eggs, one for each pet family, about 4.5 studs tall and 3.2–3.5 wide. Import and set up
an egg like a pet: `SetupPets.lua` sends anything named `...Egg` to **ReplicatedStorage > Eggs**.
Review sheet: `preview/eggs.png`.

| Egg | Look | Triangles |
|---|---|---|
| Meadow | Cream shell with pastel speckles and a hairline crack (the starter egg, no glow) | 2,838 |
| Ember | Overlapping obsidian scales with ember-red edges, glowing where the points meet, horn nubs on top | 3,192 |
| Phoenix | Crimson-to-gold flame feathers swirling up to glowing tips | 3,600 |
| Storm | White veined porcelain wrapped in navy wing blades with silver rims and glowing lightning cracks | 3,354 |
| Crystal | Hewn slate slabs like the golem's, broken open front and back on crystals lit from inside | 3,109 |
| Shadow | Wrapped in tiers of slate fur locks with silver points like the wolf's mane; violet crystals lit from inside burst through the top, cradled by a silver crescent moon | 3,786 |

Weak points: the Shadow egg's fur locks are flat-faceted and up close can read as artichoke leaves,
and its upper shell has a plain dark band from the sides. Phoenix's feather tips spike out of the outline so it can read
like a pinecone, and its painted feather lines blur. Meadow's smooth shell can still look a little
like plastic up close, and Ember's obsidian reads charcoal more than black glass. Ember's glow part
is a whole inner shell seen through the gaps between the scales; how its Neon looks in Studio is
untested.

## The ore rocks

Seven rocks to mine, one per pickaxe tier plus a special one, each 4–5 studs wide and 2.8–4.4 tall.
Import and set up a rock like a pet: `SetupPets.lua` sends anything named `...Ore` to
**ReplicatedStorage > Ores** and, unlike pets and eggs, keeps it solid (hull collisions, clickable)
so players bump into it and your mining code can raycast or click it. Glow parts stay non-solid.
Review sheet: `preview/ores.png`.

| Rock | Look | Triangles |
|---|---|---|
| Stone | Weathered grey rock with lichen and quartz flecks (the starter) | 1,132 |
| Coal | Dark rock with black jagged coal seams breaking out | 1,720 |
| Iron | Brown-grey rock with clusters of rusty ore lumps and metal nuggets | 2,484 |
| Gold | Warm sandy slabs with thick gold veins and nuggets | 2,316 |
| Emerald | Dark slate split by a cluster of emerald crystals lit from inside | 1,218 |
| Ember | Black obsidian with a molten crack and orange ember crystals | 2,348 |
| Egg Geode | Cracked open on a speckled egg in a violet hollow ringed with crystals: the "you found an egg" rock | 2,570 |

Weak points: the gold veins read as gold bars bent over the rock rather than set into it, and the
gold slabs look a little like buns. Up close the geode's rim crystals are still a spiky crown. The
ember crack glows as a broad flat band, and the iron lumps look stuck on rather than grown. The
gloss on coal, gold and obsidian is painted into the texture, so it will not move in game.

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

- Dragon: even re-packed, the texture fills 38% of the image, and the small body scales still blur at
  mid range. The body barrel and thighs are smooth masses, the horns read grey-brown rather than black
  with bone tips, and at game distance the small head loses its face detail apart from the eyes.
- Bunny: the stitches are painted, not raised, and the pom-pom tail is not fluffy enough.
- Cat: leg and tail stripes are evenly spaced bands, and the outline is smooth.
- Fox: about 11,600 triangles, heavy for a pet if many are on screen.
- Unicorn: under strong light the coat reads nearly flat white and the gold dapple is faint. Head-on
  the almond eyes are seen edge-on and look a little sleepy. The legs are slim and it is narrow from
  the front, so it is small at game distance.
- Penguin: up close some belly facets look crumpled rather than a few clean knife strokes, and the
  grain hardly shows through the navy paint. The bead eyes look slightly owlish, and the red hat with
  a cream cuff hints at a Santa hat.
- Turtle: at game distance the shell detail collapses into a brown dome, and from the front the rim
  reads as a separate frilly band. The skin reads as smooth olive at mid range; scales and wrinkles
  only show up close. A soft rim shows round each eye socket close up, and the nostrils are smudges.
- Phoenix: the hundreds of curved feathers fill 41% of the image even re-packed, so the drawn
  feather shafts blur away. Up close the head is a rounded, slightly boxy shape, the
  backs of the wings are plain with the wing arm reading as a dark rod, and the rows of chest
  feathers are an even spiky pattern.
- Griffin: the white breast is a regular pattern of scale-like feathers that reads as armour more
  than soft plumage, and goes nearly flat white in strong light. The beak is a little large and
  bright, the lion body and thighs are smooth, the tail is thin and the eagle shanks are long.
- Golem: the legs and feet read as stacked boxes, a little robotic, and many limb blocks are similar
  slabs. The cracks, worn edges and carvings vanish at game distance, where the stone is plain dark
  grey. Each crystal's glowing core reads as one brighter crystal rather than light from inside.
- Wolf: from the front it is still a fairly narrow column with a jagged mane, weaker at game distance
  than the winged creatures. The big silver mane locks are smooth and alike, so up close the ruff
  reads a little like layered petals, and the body and legs are smooth shapes where painted strokes
  do most of the work.
- Driller: the outline is still a low loaf with stacks, and from the side the armour bands look a
  bit like a row of drums. The yellow is a little uniform at mid distance and the paint chips are
  small. In the renders the glow ring lights the yellow snout orange, which Roblox Neon will not do.

## How the practice rounds work

Build, render, look at the render, score it honestly, fix a few of the weakest things, save as a
new version, repeat. A round's score is only what can be seen in the picture.
