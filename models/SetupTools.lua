--!strict
-- PICKAXE SETUP
-- 1. Import a pickaxe with Import 3D (for example ember_pickaxe.fbx from models/export).
-- 2. In the Explorer, select what was imported (the model, or its parts). You can select several pickaxes.
-- 3. Paste ALL of this into Roblox Studio's Command Bar (View tab > Command Bar) and press Enter.
--
-- For each pickaxe it makes a Tool: the textured part becomes the Handle, any GLOW part turns Neon
-- with a small light and is welded on, collisions are switched off, and the grip is set so the hand
-- holds the shaft near the bottom with the head up and the pick pointing forward. The finished tools
-- go into ReplicatedStorage > Tools. To try one, put a copy in StarterPack and press Play.
-- Running it again on the same pickaxe is safe. Ctrl+Z undoes it.

local ChangeHistoryService = game:GetService("ChangeHistoryService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Selection = game:GetService("Selection")

local GRIP_HEIGHT = 0.7 -- studs from the bottom of the shaft to the middle of the hand

pcall(function()
	ChangeHistoryService:SetWaypoint("Before pickaxe setup")
end)

local function log(message: string)
	print("Pickaxe setup: " .. message)
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

local function toolsFolder(): Instance
	local existing = ReplicatedStorage:FindFirstChild("Tools")
	if existing then
		return existing
	end
	local created = Instance.new("Folder")
	created.Name = "Tools"
	created.Parent = ReplicatedStorage
	return created
end

-- "EmberPickaxe" -> "Ember Pickaxe"
local function spaced(name: string): string
	return (name:gsub("(%l)(%u)", "%1 %2"))
end

-- Group the selected parts by tool: the name before the first underscore ("EmberPickaxe_Handle" -> "EmberPickaxe").
-- A part already renamed to "Handle" by an earlier run is grouped under the tool it sits in.
local groups: { [string]: { MeshPart } } = {}
for _, part in selectedParts() do
	part.Name = (part.Name:gsub("%.%d+$", "")) -- "EmberPickaxe_Handle.001" -> "EmberPickaxe_Handle"
	local toolName = part.Name:match("^([^_]+)_")
	if not toolName then
		local parent = part.Parent
		if parent and parent:IsA("Tool") then
			local source = parent:GetAttribute("SourceName")
			toolName = if typeof(source) == "string" then source else (parent.Name:gsub(" ", ""))
		end
	end
	if toolName then
		local list = groups[toolName]
		if not list then
			list = {}
			groups[toolName] = list
		end
		table.insert(list, part)
	else
		log("skipped " .. part.Name .. " (its name does not look like Name_Part)")
	end
end

local folder = toolsFolder()
local finished: { Instance } = {}

for toolName, parts in groups do
	-- The handle is the part called Name_Handle (or Handle from an earlier run), or failing that the biggest part.
	table.sort(parts, function(a: MeshPart, b: MeshPart): boolean
		return a.Size.Magnitude > b.Size.Magnitude
	end)
	local handle: MeshPart = parts[1]
	for _, part in parts do
		if part.Name == toolName .. "_Handle" or part.Name == "Handle" then
			handle = part
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
		part.Anchored = false -- a held tool must be free to move with the hand
		part.CanCollide = false
		part.CanQuery = false
		part.Massless = true
		pcall(function()
			part.CollisionFidelity = Enum.CollisionFidelity.Box
		end)
		pcall(function()
			part.RenderFidelity = Enum.RenderFidelity.Precise
		end)
		if part.Name:lower():find("glow", 1, true) then
			part.Name = "Glow"
			part.Material = Enum.Material.Neon
			if not part:FindFirstChildOfClass("PointLight") then
				local light = Instance.new("PointLight")
				light.Color = part.Color
				light.Brightness = 0.5
				light.Range = 5
				light.Parent = part
			end
		end
	end
	handle.Name = "Handle"
	handle.CanTouch = true -- so your mining code can use Touched if it wants to

	local appearance = handle:FindFirstChildOfClass("SurfaceAppearance")
	if not appearance and handle.TextureID == "" then
		log(toolName .. " has no texture. Add a SurfaceAppearance to its Handle and set ColorMap to its _colour.png")
	end

	-- Reuse the tool from an earlier run if there is one, so settings you changed on it are kept.
	local displayName = spaced(toolName)
	local existing = folder:FindFirstChild(displayName)
	local tool: Tool
	if existing and existing:IsA("Tool") then
		tool = existing
	else
		tool = Instance.new("Tool")
		tool.Name = displayName
	end
	tool.RequiresHandle = true
	tool.CanBeDropped = false
	tool:SetAttribute("SourceName", toolName)

	for _, part in parts do
		part.Parent = tool
		if part ~= handle then
			local weld = Instance.new("WeldConstraint")
			weld.Part0 = handle
			weld.Part1 = part
			weld.Parent = handle
		end
	end

	-- The pickaxe was modelled standing up with its head on top and the pick pointing forward, centred
	-- on the shaft. The hand goes on the shaft a little above the bottom; the head then points up and
	-- the pick forward when the character holds the tool out.
	tool.Grip = CFrame.new(0, -handle.Size.Y / 2 + GRIP_HEIGHT, 0)

	for oldParent in oldParents do
		if oldParent ~= tool and (oldParent:IsA("Model") or oldParent:IsA("Folder")) and oldParent ~= folder then
			if #oldParent:GetChildren() == 0 then
				oldParent:Destroy()
			end
		end
	end
	tool.Parent = folder

	table.insert(finished, tool)
	log(displayName .. " is ready in ReplicatedStorage > Tools (" .. #parts .. " parts)")
end

if #finished == 0 then
	log("nothing to do. Select the imported pickaxe in the Explorer first, then run this again.")
else
	Selection:Set(finished)
	log("to try a pickaxe, put a copy of it in StarterPack and press Play")
end

pcall(function()
	ChangeHistoryService:SetWaypoint("Pickaxe setup")
end)
