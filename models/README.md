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
| `props/hatchery.py` | The Hatchery, where eggs are hatched |
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
part (`Fox_Eye`, `Puppy_Gloss`, `Unicorn_GLOW_Horn`, `Dragon_GLOW`, `Bunny_Eyes`, `Cat_Gloss`, `Cat_GLOW`, `Penguin_Eyes`, `Turtle_Eyes`, `Phoenix_GLOW`, `Griffin_GLOW`, `Golem_GLOW`, `Wolf_GLOW`, `Driller_GLOW`, `Salamander_GLOW`).

## Put a pickaxe into Roblox Studio

1. Import `export/<name>_pickaxe.fbx` the same way, but leave **Anchored** off.
2. Select it, then paste all of `SetupTools.lua` into the Command Bar and press Enter. The textured
   part becomes the tool's `Handle`, any `GLOW` part turns Neon and is welded on, and the grip is set
   so the hand holds the shaft near the bottom with the head up and the pick forward. The tool goes to
   **ReplicatedStorage > Tools**; put a copy in **StarterPack** and press Play to try it.
3. If it sits wrong in the hand, change the tool's **Grip** settings in Properties
   (`GripPos` moves it, `GripForward`/`GripUp` turn it). Like the pet script, this has only been
   checked as valid Luau, not yet run in Studio.

## Animations

The pets have no bones: each is one rigid model. `PetAnimator.lua` animates them the way Roblox pet
games usually do, by moving and turning the whole model a little around its pivot every frame, on top
of where your pet-follow code puts it. Each pet has an idle (breathing, looking round, shifting its
weight, hovering) and a walk (trot, hop, stomp, glide...) that blend smoothly by speed, and each copy
starts at a random point in its motion so a group of pets does not move in step.

Put `PetAnimator.lua` in **ReplicatedStorage** as a ModuleScript called `PetAnimator`, then drive it
from the LocalScript that moves the pets (client only; it makes no connections of its own):

```lua
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local PetAnimator = require(ReplicatedStorage.PetAnimator)

local pet = ReplicatedStorage.Pets.Fox:Clone()
pet.Parent = workspace
local animator = PetAnimator.new(pet, "Fox")   -- the name picks the style; it defaults to pet.Name
local lastPosition = pet:GetPivot().Position

RunService.RenderStepped:Connect(function(dt)
	local target = followCFrame()              -- your follow code: where the pet's feet should be
	local speed = (target.Position - lastPosition).Magnitude / math.max(dt, 1e-3)
	lastPosition = target.Position
	animator:Step(dt, target, speed)           -- calls pet:PivotTo(target * offset)
end)

-- when the pet is unequipped: animator:Destroy() and pet:Destroy()
```

Pass the CFrame your code would otherwise have given `PivotTo` (pivot under the feet, facing where
the pet goes), and its speed in studs per second. Below about 0.6 studs/s the pet idles; by 4 studs/s
it is fully walking. The walk is tuned for 16 studs/s, a player's walking speed. Flyers and floaters
add their own hover height, so keep the target on the ground for them too.

**Changing a pet's style.** At the bottom of `PetAnimator.lua`, `PetAnimator.PETS` maps every pet
(name in lower case) to one of the styles in `PetAnimator.STYLES` (`walker`, `sitter`, `hopper`,
`heavy`, `flyer`, `floater`, `slither`, `blob`), plus any fields of its own, for example
`fox = { style = "hopper" }` or `griffin = { style = "flyer", hover = 0.3, amp = 1.2, speed = 0.9 }`.
`amp` scales all its movements, `speed` how fast they go, `hover` is its height above the ground
as a fraction of its height. Every field is explained where `Profile` is declared. A pet missing from
the table walks like a `walker`. Lengths are fractions of the pet's height, so the same style moves a
dragon more studs than a fox, and bigger pets also stride more slowly.

| Style | Pets |
|---|---|
| `sitter` (breathe, tilt and look round; perky hop-skip) | fox, puppy, cat, penguin (a side-to-side waddle instead of the skip), tophatcrow, hedgehog |
| `hopper` (arcs with a pause; the odd hop in place) | bunny, gargoyle (slower, lower stone hops: it is modelled crouched on its hands), drumdevil, mushroom, snowbunny, frog |
| `walker` (two-beat trot; slow look round, weight shift) | unicorn, wolf, horneddemon, lavacat, plumedlion, skeletondog, cerberus, piggy, dunecat, shadowpanther, frostwolf, nightunicorn |
| `heavy` (slow stomp and roll; rare look round) | turtle, dragon, golem, driller, spikecrab, highlandbull, magmacrown, grizzly, redrex, armordino, irongolem |
| `flyer` (hover, figure eight, bank; flies pitched down) | phoenix, griffin, infernobat, raven, firedemon, moth, duskbat, angelyeti |
| `floater` (slow drift, sway and turn) | ghost, cloudspirit, reaper, spiritblob, skyjelly, halosprite |
| `slither` (body swings side to side; raises its head) | salamander, snailrider, emberserpent, goldslug, sailback, croc |
| `blob` (hop, tilt and jelly wobble, no scaling) | kingslime, cauldron |

**Previews.** `models/anim/preview_anim.py` renders each pet's idle and walk with an exact Python port
of the same maths (it reads the tables out of `PetAnimator.lua`), into `preview/anim/<name>_idle.gif`,
`<name>_walk.gif` and `<name>_strip.png`, and checks that no part ever goes under the floor:

```bash
python models/anim/preview_anim.py fox golem      # or no names for every pet
```

PetAnimator parses as strict Luau but, like the setup scripts, has not been run in Studio yet.

## The pets so far

| Pet | Style | Triangles | Rounds |
|---|---|---|---|
| Fox | Sitting storybook animal with short fur and a simple, friendly face | 11,644 | 20 |
| Puppy | Plush toy with stitches, patches and a fleecy nap | 8,926 | 8 |
| Unicorn | Moonlight unicorn as a faceted low-poly sculpture: prancing horse, pearl-silver coat, sapphire-to-violet mane and tail, twisted glowing crystal horn, gold hooves | 5,864 | 15 (7 since the remake) |
| Dragon | Adult obsidian fire dragon: larger wedge head with a calm brow, cheek spikes and a black horn crown with bone tips, back plates, rib plates and armour scales, raised red wings, glowing ember eyes and seams, 10.2 studs tall | 19,401 | 16 (11 since the redesign) |
| Bunny | Crochet toy with rows of yarn stitches and a scarf | 8,290 | 4 |
| Cat | Needle-felted oatmeal tabby with roving-style stripes, a halo of stray wool fibres and a tiny felt miner's hat with a glowing lamp | 9,482 | 13 (8 since the remake) |
| Penguin | Whittled folk-art figure: knife-cut and gouged pale wood under thin worn milk paint, carved bobble hat, on a round oiled base | 7,437 | 12 (9 since the remake) |
| Turtle | Old forest tortoise in a naturalist storybook style: high domed shell with ridged growth rings, moss with mushrooms and a fern on top, olive scaly skin, calm amber eyes | 8,960 | 13 (11 since the remake) |
| Phoenix | Fire bird off a coat of arms: raptor head with a swept flame crest and glowing eyes, raised blade-feather wings with covert rows on the backs, flame-feather breast round an ember heart, flame train, 9.3 studs tall | 18,304 | 12 |
| Griffin | Storm griffin: white eagle head with glowing blue eyes and a gold cere, layered off-white breast, navy wings with lightning streaks, muscled golden lion body, tufted navy tail with a glowing core, 9.5 studs tall | 18,406 | 13 |
| Golem | Ancient crystal golem: chipped slate slabs with moss and roots, knee boulders and splayed toe stones, emerald crystals lit from inside, glowing eye slots, rune rings and seams, 9.9 studs tall | 11,246 | 11 |
| Wolf | Shadow alpha wolf: long wedge muzzle, tall ears, slate blue-grey coat with a charcoal saddle, big silver mane of sculpted locks, violet crystals glowing along the spine, calm violet eyes, 7 studs tall | 15,032 | 19 (10 since the remake) |
| Driller | Mining machine shaped like a mole: worn mining-yellow armour over gunmetal, chrome drill in a glowing ring, light-bar visor, furnace grille, oversized shovel claws, exhaust stacks, dug-up gems on its back, 5.1 studs tall and 7.9 long | 11,844 | 12 |
| Salamander | Lava salamander (a remake of the game's black lava lizard): near-black basalt skin with a cooled-lava crust, glowing seam and flank veins, obsidian spines, amber eyes, 3.3 studs tall and 6.8 long | 11,460 | 10 |

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

## The Hatchery

The machine where players hatch the eggs they mine (`props/hatchery.py`, sheet `preview/hatchery.png`),
9.5 × 10.2 studs and 8.7 tall, 11,883 triangles: a stepped stone base, four crystal pylons, a brass and
iron frame round a glass dome with an empty cushioned cradle, a control desk with gauges and a lever,
and an egg hopper on the right.

- Parts: `Hatchery_Body` (textured), `Hatchery_GLOW` (crystals, runes, conduits) and `Hatchery_Glass`
  (the dome: set its Material to Glass and Transparency to about 0.6 in Studio).
- Put an egg's bottom at 2 studs above the Hatchery's bottom centre (Blender empty `Hatchery_EggSpot`
  at (0, 0, 2.0); Import 3D may drop the empty). All six eggs fit inside the dome.
- Weak points: the empty dome looks plain until an egg is in it, the hopper reads only from the right,
  and painted detail is soft up close (about 30 px per stud).

## Remakes of the game's own pets

The pets already in the Mine an Egg place (screenshots in `reference/ingame_pets_*.png`) that looked
creepy or crude, rebuilt as the same creature with the same colours so they can replace the originals.
Each has `export/<name>.fbx` (+ `_colour.png`, `_rough.png`), `preview/<name>.png` and a side-by-side
`preview/<name>_before_after.png`. Set them up with `SetupPets.lua` like the other pets.

| Remake | Was | Now | Triangles |
|---|---|---|---|
| InfernoBat | Red bat with a devil-like human face | Fluffy crimson fire bat, amber eyes, flame wings with glowing edges | 11,192 |
| Gargoyle | Snarling grey stone gargoyle | Crouching stone guardian with a calm lion-dog face, moss and a glowing chest rune | 10,768 |
| Raven | Black crow with red eyes | Glossy black raven with a blue-violet sheen and warm amber eyes | 10,300 |
| Salamander | Black lava lizard | See the pets table | 11,460 |
| Ghost | White blob with huge bulging purple eyes | Small floating sheet ghost with calm eyes, a tiny smile, lavender glow in the folds | 7,460 |
| CloudSpirit | Cloud head with tentacle-like white wisps | Puffy cumulus with a friendly face, raining blue drops and a small spark | 7,154 |
| KingSlime | Yellow blob with staring eyes and a crown | Golden honey slime with a content smirk, trapped bubbles and a jewelled crown | 7,740 |
| Cauldron | Black horned cauldron with angry white eyes | Cheerful cast-iron cauldron with ember-tipped horns, bubbling green potion and a friendly face | 12,060 |
| DrumDevil | Red drum with a face, horns, a flame and a trident | Cheeky lacquered drum imp with brass studs, a flickering flame and a little trident | 10,248 |
| PlumedLion | Lion with a turkey-feather mane and red wings | Lion cub with a barred turkey-fan mane and red feather wings | 9,376 |
| Reaper | Hooded figure with a scythe | Little hooded spirit with soft violet eyes, a moon scythe and floating wisps | 8,096 |
| SkeletonDog | Skeleton dog | Happy black pup in a glowing bone-print costume with a bone tag | 9,570 |
| FireDemon | Hunched snarling red demon with bat wings and a gold crown | Upright molten imp-knight with glowing seams, bat wings, a crown of gold flame spikes and a calm face | 13,596 |
| HornedDemon | Red four-legged demon with ram horns, black wings and a crown | Red ram-beast with glossy curled black horns, armour plates, black-and-red wings and a gold circlet | 10,164 |
| LavaCat | Scowling red cat beast with a dragon tail | Red-to-flame-orange cat with relaxed amber eyes, a ':3' smile, ember stripes and a fluffy flame tail | 8,848 |
| Cerberus | Blocky navy three-headed dog | Loyal three-headed guardian pup in black and tan, floppy-folded ears, spiked collars, happy open smiles and a flame-tipped tail | 8,773 |
| SnailRider | Blocky snail on a red bike | Green snail with a coiled orange shell, stalk eyes and a smile, riding a small spoked red bicycle | 8,792 |
| Moth | Spiky dark moth with glaring yellow eyes | Fluffy brown moth with a white ruff, feathery antennae, big friendly eyes and painted orange swirl wings | 7,748 |
| SpiritBlob | Purple spiky ghost with a grin (original design, not a remake of its look) | Purple flame-wisp with one swept-back flame, calm aqua glowing eyes, blush and three floating sparks | 5,200 |
| Mushroom | Blocky red toadstool on legs | Toadstool with a glossy red cap with domed white spots, a sprout on top, a soft cream stem with a shy smile and moss at its feet | 7,860 |
| Piggy | Flat pink pig | Round pink piglet with stubby legs and hooves, fuzz, a curly tail and a happy open mouth | 6,740 |
| SnowBunny | Blocky white rabbit with two faces stacked | Natural white rabbit crouched on all fours, pink-lined ears, dark eyes and a pompom tail (unlike the crochet Bunny) | 7,520 |
| SpikeCrab | Pale crab with long spidery legs and white ice spikes | Low, chubby frost crab on short thick legs, with a domed frosty-blue shell, blue claws, five faceted ice crystals and a small smile | 8,280 |
| SkyJelly | White cloud covered in grey bumps that read as many eyes, with dangling strands | Pastel blue-to-pink cloud jellyfish with one friendly face, rim beads and flowing ribbon tentacles | 11,080 |
| EmberSerpent | Coiled red horned snake | Friendly coiled serpent-dragon in red-to-orange scales, small swept-back horns, round eyes and glowing ember belly plates | 9,672 |
| HighlandBull | Hunched minotaur-like bull-ape | Sturdy shaggy highland calf with a rust fringe, wide cream horns, a soft dark nose and hooves | 11,720 |
| DuskBat | Purple bat with a cat-like face | Fluffy dusk-purple fruit bat with big ears, a cream chest, lilac wing membranes and gentle eyes | 10,859 |
| MagmaCrown | Blocky lava lump with crystal spikes | Little basalt magma king with glowing cracks and face, an orange crystal crown and amethyst shoulder shards | 8,076 |
| Grizzly | Brown bear with back spikes and long claws | Calm grizzly with a shoulder hump, layered fur ridges, short claws and small mossy stones on its back | 11,840 |
| DuneCat | Hunched bony tan cat with a ridged spine | Slender sandy desert cat with calm kohl-lined almond eyes, shaped legs, darker ear and tail tips and a gold collar with a blue gem | 10,596 |
| ShadowPanther | Black panther with an open red snarl | Long, low charcoal panther with a blue-violet sheen, faint rosettes, calm gold-green eyes, a glowing violet collar gem and tail flame | 11,656 |
| GoldSlug | Lumpy gold blob with a moustache and sparkles | Dapper golden slug gentleman with a curled moustache, monocle, little top hat and floating sparkles | 9,988 |
| AngelYeti | Stiff white ape with a crown and feather wings | Fluffy white yeti cub with a pale blue face, layered feathered angel wings and a small gold halo-crown | 10,080 |
| Hedgehog | Blocky grey-spined hedgehog | Round hedgehog with clumped brown-cream spines, a pointy cream face, button nose and a mushroom on its back | 11,716 |
| SailBack | Stiff blocky sail-backed reptile | Rust-red sail-backed lizard with a ribbed sunset-striped sail, bold scales and a low, strong stance | 10,216 |
| RedRex | Chunky red horned dinosaur | Crimson horned dinosaur with darker bands, leaf-green back plates, cream horns and smiling cheeks | 10,472 |
| Frog | Lime frog with pink headphones | Chill DJ frog with spotted green skin, big amber eyes, relaxed half lids and pink over-ear headphones | 9,720 |
| TopHatCrow | Dark purple crow in a top hat with violet wing tips | Plump violet-black crow with layered breast scallops, folded three-layer wings with a violet sheen, a fan tail, a chunky beak and a top hat with a pink ribbon | 11,910 |
| Croc | Bright green flat-snouted lizard | Low-slung emerald crocodile on splayed legs, with a long tapering snout, a closed smile, two rows of broad scutes and a crested tail | 9,408 |
| HaloSprite | Winged eyeball inside gold rings | Pearl-white celestial sprite with a gold halo, big round-tipped feather wings, blush cheeks and one curled wispy tail | 9,856 |
| ArmorDino | Brown lumpy dinosaur with yellow spikes | Sturdy ankylosaur-type with keeled staggered back plates, amber side spikes, head scutes and a club tail | 11,416 |
| FrostWolf | Blue blocky wolf with a white spiky crest | Fluffy midnight-blue arctic wolf with a pale ruff, a ridge of ice crystals along its back and a round tail tip | 11,062 |
| IronGolem | Brown block golem with yellow lights | Friendly mining golem of dark stone under rusty riveted iron plates, big fists, a horned helmet and a glowing lantern heart | 11,702 |
| NightUnicorn | Black and white horse with a pale horn | Night-purple unicorn with a starry coat, a lilac mane and tail, silver hooves and a glowing spiral horn | 11,516 |

Weak points: PlumedLion's face reads more cub than noble lion; the Cauldron's and DrumDevil's surfaces
are fairly plain away from the face; the Reaper's hood is a plain smooth form. The Ghost and KingSlime are quite smooth (KingSlime's shine is painted on, and it is more
orange than the original's lemon); the CloudSpirit's wisps became rain streaks. InfernoBat's chest ruff looks a little like a shaggy beard up close; the Gargoyle's stone is
fairly smooth up close and it is crouched where the original stood; the Raven's body below the neck is
a plain dark column and its legs are thin.

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

- Dragon: the texture is still soft (about 38 px per stud; over 1,000 small pieces share one image),
  so the scales read because they are bold, not sharp. Under strong light the far horn's base can
  look pale, and from the front the chest is a plain mass behind the bronze belly plates.
- Bunny: the stitches are painted, not raised, and the pom-pom tail is not fluffy enough.
- Cat: the forms under the wool are fairly smooth, so the felt look comes mostly from the texture,
  a fabric sheen Roblox does not have and stray hairs that will be tiny in game. The outline is a
  simple round head on an egg body with tube front legs, and the M and leg bars look a little drawn on.
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
- Phoenix: from the front three-quarter the beak reads as a long gold cone and the brow is soft. The
  drawn feather shafts vanish at mid range (hundreds of small pieces share one 1024 texture), and the
  legs and feet are plain gold tubes.
- Griffin: up close the breast still reads slightly like rows of shingles rather than fluff, the
  flat skull planes and pointed neck hackles look a little like cardboard, and the lion hind legs
  below the thigh are tubes with painted muscle. Only about 100 triangles of budget are left.
- Golem: the chest, hump and shoulder boulders are still big smooth planes, plainer than the limbs.
  Up close the rune dashes can look like stitching, and the texture is a little soft (39 px per stud).
- Wolf: from the front it is still a fairly narrow column with a jagged mane, weaker at game distance
  than the winged creatures. The big silver mane locks are smooth and alike, so up close the ruff
  reads a little like layered petals, and the body and legs are smooth shapes where painted strokes
  do most of the work.
- Driller: the outline is still a low loaf with stacks, and from the side the armour bands look a
  bit like a row of drums. The yellow is a little uniform at mid distance and the paint chips are
  small. In the renders the glow ring lights the yellow snout orange, which Roblox Neon will not do.
- Salamander: straight on the snout still reads rounded, the throat plates look a little like belt
  bands, the legs are plain tubes, and at game distance it is a dark shape with orange accents.

## How the practice rounds work

Build, render, look at the render, score it honestly, fix a few of the weakest things, save as a
new version, repeat. A round's score is only what can be seen in the picture.
