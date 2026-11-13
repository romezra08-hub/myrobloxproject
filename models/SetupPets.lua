--!strict
-- PET SETUP
-- 1. Import a pet with Import 3D (for example fox.fbx from models/export).
-- 2. In the Explorer, select what was imported (the model, or its parts). You can select several pets.
-- 3. Paste ALL of this into Roblox Studio's Command Bar (View tab > Command Bar) and press Enter.
--
-- For each pet it tidies the part names, makes the eyes glossy and any GLOW part Neon with a small
-- light, switches off collisions, welds the parts to the body, puts the pivot under the feet and
-- moves the pet into ReplicatedStorage > Pets. Running it again on the same pet is safe.
-- Ctrl+Z undoes it.

local ChangeHistoryService = game:GetService("ChangeHistoryService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Selection = game:GetService("Selection")

pcall(function()
	ChangeHistoryService:SetWaypoint("Before pet setup")
end)

local function log(message: string)
	print("Pet setup: " .. message)
end

-- Every MeshPart in the selection, including those inside selected models and folders.
local function selectedParts(): { MeshPart }
	local found: { MeshPart } = {}
	local seen: { [Instance]: boolean } = {}
	local function take(inst: Instance)
		if inst:IsA("MeshPart") and not seen[inst] then
			seen[inst] = true
			table.insert(found, inst)
		end
	end
	for _, inst in Selection:Get() do
		take(inst)
		for _, child in inst:GetDescendants() do
			take(child)
		end
	end
	return found
end

-- The folder the finished pets go into.
local function petsFolder(): Instance
	local existing = ReplicatedStorage:FindFirstChild("Pets")
	if existing then
		return existing
	end
	local created = Instance.new("Folder")
	created.Name = "Pets"
	created.Parent = ReplicatedStorage
	return created
end

-- Group the selected parts by pet: the name before the first underscore ("Fox_Body" -> "Fox").
local pets: { [string]: { MeshPart } } = {}
for _, part in selectedParts() do
	part.Name = (part.Name:gsub("%.%d+$", "")) -- "Fox_Body.001" -> "Fox_Body"
	local petName = part.Name:match("^([^_]+)_")
	if petName then
		local list = pets[petName]
		if not list then
			list = {}
			pets[petName] = list
		end
		table.insert(list, part)
	else
		log("skipped " .. part.Name .. " (its name does not look like Pet_Part)")
	end
end

local folder = petsFolder()
local finished: { Instance } = {}

for petName, parts in pets do
	-- The body is the part called Pet_Body, or failing that the biggest part.
	table.sort(parts, function(a: MeshPart, b: MeshPart): boolean
		return a.Size.Magnitude > b.Size.Magnitude
	end)
	local body: MeshPart = parts[1]
	for _, part in parts do
		if part.Name == petName .. "_Body" then
			body = part
		end
	end

	local oldParents: { [Instance]: boolean } = {}
	for _, part in parts do
		if part.Parent then
			oldParents[part.Parent] = true
		end
		for _, child in part:GetChildren() do
			if child:IsA("WeldConstraint") then
				child:Destroy() -- left over from an earlier run
			end
		end

		part.Anchored = true -- the stored pet stays put; your pet system moves its own copies
		part.CanCollide = false
		part.CanTouch = false
		part.CanQuery = false
		part.Massless = true
		pcall(function()
			part.CollisionFidelity = Enum.CollisionFidelity.Box
		end)
		pcall(function()
			part.RenderFidelity = Enum.RenderFidelity.Precise
		end)

		local lower = part.Name:lower()
		if lower:find("glow", 1, true) then
			part.Material = Enum.Material.Neon
			if not part:FindFirstChildOfClass("PointLight") then
				local light = Instance.new("PointLight")
				light.Color = part.Color
				light.Brightness = 0.6
				light.Range = 6
				light.Parent = part
			end
		elseif lower:find("_eye", 1, true) or lower:find("_gloss", 1, true) then
			part.Material = Enum.Material.SmoothPlastic
			part.Reflectance = 0.2
		end
	end

	-- Say so if the body arrived without its texture, or without the map that makes it matte.
	local appearance = body:FindFirstChildOfClass("SurfaceAppearance")
	if not appearance and body.TextureID == "" then
		log(body.Name .. " has no texture. Add a SurfaceAppearance to it and set ColorMap to " .. petName:lower() .. "_colour.png")
	elseif appearance then
		local ok, roughness = pcall(function(): string
			return appearance.RoughnessMap
		end)
		if ok and roughness == "" then
			log(body.Name .. " may look shiny. To make it matte, set its SurfaceAppearance's RoughnessMap to " .. petName:lower() .. "_rough.png")
		end
	end

	-- One model per pet, everything welded to the body.
	local model = Instance.new("Model")
	model.Name = petName
	for _, part in parts do
		part.Parent = model
		if part ~= body then
			local weld = Instance.new("WeldConstraint")
			weld.Part0 = body
			weld.Part1 = part
			weld.Parent = body
		end
	end

	-- The pivot goes under the feet, in the middle. Measure before choosing the PrimaryPart, while the
	-- bounding box is still lined up with the world.
	local boxCFrame, boxSize = model:GetBoundingBox()
	local feet = CFrame.new(boxCFrame.Position - Vector3.new(0, boxSize.Y / 2, 0))
	model.PrimaryPart = body
	body.PivotOffset = body.CFrame:ToObjectSpace(feet)

	-- Clear away the empty wrapper the parts came in, and any earlier copy of this pet.
	for oldParent in oldParents do
		if oldParent ~= model and (oldParent:IsA("Model") or oldParent:IsA("Folder")) and oldParent ~= folder then
			if #oldParent:GetChildren() == 0 then
				oldParent:Destroy()
			end
		end
	end
	local earlier = folder:FindFirstChild(petName)
	if earlier then
		earlier:Destroy()
	end
	model.Parent = folder

	table.insert(finished, model)
	log(petName .. " is ready in ReplicatedStorage > Pets (" .. #parts .. " parts, pivot under its feet)")
end

if #finished == 0 then
	log("nothing to do. Select the imported pet in the Explorer first, then run this again.")
else
	Selection:Set(finished)
end

pcall(function()
	ChangeHistoryService:SetWaypoint("Pet setup")
end)
