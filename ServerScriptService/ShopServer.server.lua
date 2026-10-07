-- Script: put in ServerScriptService, name it "ShopServer"
-- Gives players coins and handles purchases. Prices are checked here so
-- exploiters can't buy things for free from the client.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local ShopConfig = require(ReplicatedStorage:WaitForChild("ShopConfig"))

local remotes = Instance.new("Folder")
remotes.Name = "ShopRemotes"
remotes.Parent = ReplicatedStorage

local purchaseRemote = Instance.new("RemoteFunction")
purchaseRemote.Name = "Purchase"
purchaseRemote.Parent = remotes

local getOwnedRemote = Instance.new("RemoteFunction")
getOwnedRemote.Name = "GetOwned"
getOwnedRemote.Parent = remotes

-- Owned items for this server session only (not saved between games).
local owned = {}

local function setupPlayer(player)
	owned[player] = {}

	local leaderstats = player:FindFirstChild("leaderstats")
	if not leaderstats then
		leaderstats = Instance.new("Folder")
		leaderstats.Name = "leaderstats"
		leaderstats.Parent = player
	end

	if not leaderstats:FindFirstChild(ShopConfig.CurrencyName) then
		local coins = Instance.new("IntValue")
		coins.Name = ShopConfig.CurrencyName
		coins.Value = ShopConfig.StartingCoins
		coins.Parent = leaderstats
	end
end

Players.PlayerAdded:Connect(setupPlayer)
for _, player in ipairs(Players:GetPlayers()) do
	setupPlayer(player)
end

Players.PlayerRemoving:Connect(function(player)
	owned[player] = nil
end)

getOwnedRemote.OnServerInvoke = function(player)
	local list = {}
	for itemId in pairs(owned[player] or {}) do
		table.insert(list, itemId)
	end
	return list
end

purchaseRemote.OnServerInvoke = function(player, itemId)
	if typeof(itemId) ~= "string" then
		return false, "Invalid item"
	end

	local item = ShopConfig.ItemsById[itemId]
	if not item then
		return false, "Unknown item"
	end

	local inventory = owned[player]
	local leaderstats = player:FindFirstChild("leaderstats")
	local coins = leaderstats and leaderstats:FindFirstChild(ShopConfig.CurrencyName)
	if not inventory or not coins then
		return false, "Please try again"
	end

	if inventory[itemId] then
		return false, "You already own this"
	end

	if coins.Value < item.Price then
		return false, "Not enough " .. ShopConfig.CurrencyName
	end

	coins.Value -= item.Price
	inventory[itemId] = true
	return true, "Purchased " .. item.Name .. "!"
end
