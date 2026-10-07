-- ModuleScript: put in ReplicatedStorage, name it "ShopConfig"
-- Edit items, prices, colors here. Both the server and the UI read this.

local ShopConfig = {}

ShopConfig.CurrencyName = "Coins" -- name of the leaderstats value
ShopConfig.CurrencyIcon = "🪙"
ShopConfig.StartingCoins = 1000
ShopConfig.ToggleKey = Enum.KeyCode.B

ShopConfig.Categories = { "All", "Weapons", "Pets", "Boosts" }

ShopConfig.Rarities = {
	Common = Color3.fromRGB(170, 178, 189),
	Rare = Color3.fromRGB(64, 156, 255),
	Epic = Color3.fromRGB(176, 92, 255),
	Legendary = Color3.fromRGB(255, 184, 28),
}

ShopConfig.Theme = {
	Background = Color3.fromRGB(22, 24, 35),
	BackgroundTop = Color3.fromRGB(40, 44, 66),
	Panel = Color3.fromRGB(31, 34, 50),
	Card = Color3.fromRGB(40, 44, 64),
	Stroke = Color3.fromRGB(78, 86, 124),
	Text = Color3.fromRGB(245, 246, 255),
	SubText = Color3.fromRGB(160, 166, 195),
	Accent = Color3.fromRGB(255, 196, 48),
	Buy = Color3.fromRGB(46, 204, 113),
	Danger = Color3.fromRGB(235, 77, 75),
	Owned = Color3.fromRGB(90, 96, 120),
}

-- Image = "rbxassetid://123..." shows a picture; leave it "" to show the Emoji instead.
ShopConfig.Items = {
	{ Id = "wooden_sword", Name = "Wooden Sword", Category = "Weapons", Rarity = "Common", Price = 100, Emoji = "🗡️", Image = "", Description = "A trusty starter blade." },
	{ Id = "ice_blade", Name = "Ice Blade", Category = "Weapons", Rarity = "Rare", Price = 450, Emoji = "❄️", Image = "", Description = "Freezes foes on hit." },
	{ Id = "dragon_axe", Name = "Dragon Axe", Category = "Weapons", Rarity = "Legendary", Price = 2500, Emoji = "🪓", Image = "", Description = "Forged in dragon fire." },
	{ Id = "puppy", Name = "Puppy", Category = "Pets", Rarity = "Common", Price = 150, Emoji = "🐶", Image = "", Description = "Follows you everywhere." },
	{ Id = "fox", Name = "Fox", Category = "Pets", Rarity = "Epic", Price = 900, Emoji = "🦊", Image = "", Description = "Finds extra coins." },
	{ Id = "unicorn", Name = "Unicorn", Category = "Pets", Rarity = "Legendary", Price = 3000, Emoji = "🦄", Image = "", Description = "Pure magic." },
	{ Id = "speed_boost", Name = "Speed Boost", Category = "Boosts", Rarity = "Rare", Price = 300, Emoji = "⚡", Image = "", Description = "Run faster for 5 min." },
	{ Id = "jump_boost", Name = "Jump Boost", Category = "Boosts", Rarity = "Common", Price = 200, Emoji = "🦘", Image = "", Description = "Jump higher for 5 min." },
	{ Id = "coin_x2", Name = "2x Coins", Category = "Boosts", Rarity = "Epic", Price = 1200, Emoji = "💰", Image = "", Description = "Double coins for 10 min." },
}

ShopConfig.ItemsById = {}
for _, item in ipairs(ShopConfig.Items) do
	ShopConfig.ItemsById[item.Id] = item
end

return ShopConfig
