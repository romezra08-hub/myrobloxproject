-- LocalScript: put in StarterPlayer > StarterPlayerScripts, name it "ShopClient"
-- Builds the whole shop UI in code: no ScreenGui needs to be made by hand.
-- Open with the SHOP button (bottom-left) or the key set in ShopConfig.ToggleKey.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local ShopConfig = require(ReplicatedStorage:WaitForChild("ShopConfig"))
local remotes = ReplicatedStorage:WaitForChild("ShopRemotes")
local purchaseRemote = remotes:WaitForChild("Purchase")
local getOwnedRemote = remotes:WaitForChild("GetOwned")

local player = Players.LocalPlayer
local Theme = ShopConfig.Theme

local ownedItems = {}
local cards = {} -- [itemId] = { frame, button, item, ... }
local currentCoins = 0

-- Helpers ---------------------------------------------------------------

local function create(className, props, children)
	local inst = Instance.new(className)
	local parent
	for key, value in pairs(props or {}) do
		if key == "Parent" then
			parent = value
		else
			inst[key] = value
		end
	end
	for _, child in ipairs(children or {}) do
		child.Parent = inst
	end
	if parent then
		inst.Parent = parent
	end
	return inst
end

local function corner(radius)
	return create("UICorner", { CornerRadius = UDim.new(0, radius) })
end

local function stroke(color, thickness, transparency)
	return create("UIStroke", {
		Color = color,
		Thickness = thickness or 1,
		Transparency = transparency or 0,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Border,
	})
end

local function gradient(top, bottom, rotation)
	return create("UIGradient", {
		Color = ColorSequence.new(top, bottom),
		Rotation = rotation or 90,
	})
end

local function padding(px)
	return create("UIPadding", {
		PaddingTop = UDim.new(0, px),
		PaddingBottom = UDim.new(0, px),
		PaddingLeft = UDim.new(0, px),
		PaddingRight = UDim.new(0, px),
	})
end

local function tween(inst, seconds, goal, style, direction)
	local t = TweenService:Create(
		inst,
		TweenInfo.new(seconds, style or Enum.EasingStyle.Quad, direction or Enum.EasingDirection.Out),
		goal
	)
	t:Play()
	return t
end

local function formatNumber(n)
	local s = tostring(math.floor(n))
	local formatted = s:reverse():gsub("(%d%d%d)", "%1,"):reverse()
	return (formatted:gsub("^,", ""))
end

-- Brightens a button on hover and squishes it on click.
local function addButtonFeel(button)
	local scale = create("UIScale", { Parent = button })
	button.MouseEnter:Connect(function()
		tween(scale, 0.12, { Scale = 1.05 })
	end)
	button.MouseLeave:Connect(function()
		tween(scale, 0.12, { Scale = 1 })
	end)
	button.MouseButton1Down:Connect(function()
		tween(scale, 0.08, { Scale = 0.94 })
	end)
	button.MouseButton1Up:Connect(function()
		tween(scale, 0.12, { Scale = 1.05 })
	end)
end

-- Root GUI ----------------------------------------------------------------

local screenGui = create("ScreenGui", {
	Name = "ShopGui",
	ResetOnSpawn = false,
	IgnoreGuiInset = true,
	ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
	Parent = player:WaitForChild("PlayerGui"),
})

-- Open button (bottom-left)
local openButton = create("TextButton", {
	Name = "OpenShop",
	AnchorPoint = Vector2.new(0, 1),
	Position = UDim2.new(0, 20, 1, -20),
	Size = UDim2.fromOffset(84, 84),
	BackgroundColor3 = Theme.Accent,
	AutoButtonColor = false,
	Text = "",
	Parent = screenGui,
}, {
	corner(20),
	stroke(Color3.fromRGB(255, 255, 255), 3, 0.2),
	gradient(Color3.fromRGB(255, 255, 255), Color3.fromRGB(200, 140, 30)),
	create("TextLabel", {
		BackgroundTransparency = 1,
		Position = UDim2.fromScale(0, 0.08),
		Size = UDim2.fromScale(1, 0.55),
		Text = "🛒",
		TextScaled = true,
		Font = Enum.Font.GothamBold,
	}),
	create("TextLabel", {
		BackgroundTransparency = 1,
		Position = UDim2.fromScale(0, 0.64),
		Size = UDim2.fromScale(1, 0.26),
		Text = "SHOP",
		TextScaled = true,
		Font = Enum.Font.GothamBlack,
		TextColor3 = Color3.fromRGB(255, 255, 255),
		TextStrokeColor3 = Color3.fromRGB(120, 70, 0),
		TextStrokeTransparency = 0,
	}),
})
addButtonFeel(openButton)

-- Dim background behind the shop
local backdrop = create("TextButton", {
	Name = "Backdrop",
	Size = UDim2.fromScale(1, 1),
	BackgroundColor3 = Color3.new(0, 0, 0),
	BackgroundTransparency = 1,
	AutoButtonColor = false,
	Text = "",
	Visible = false,
	ZIndex = 5,
	Parent = screenGui,
})

-- Main window
local window = create("Frame", {
	Name = "Window",
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.fromScale(0.5, 0.5),
	Size = UDim2.fromScale(0.7, 0.75),
	BackgroundColor3 = Theme.Background,
	Visible = false,
	ZIndex = 10,
	Parent = screenGui,
}, {
	corner(18),
	stroke(Theme.Stroke, 2),
	gradient(Theme.BackgroundTop, Theme.Background),
	create("UISizeConstraint", {
		MinSize = Vector2.new(340, 380),
		MaxSize = Vector2.new(920, 620),
	}),
})
local windowScale = create("UIScale", { Parent = window })

-- Header ------------------------------------------------------------------

local header = create("Frame", {
	Name = "Header",
	Size = UDim2.new(1, 0, 0, 68),
	BackgroundTransparency = 1,
	ZIndex = 11,
	Parent = window,
}, {
	create("UIPadding", {
		PaddingLeft = UDim.new(0, 22),
		PaddingRight = UDim.new(0, 16),
	}),
})

create("TextLabel", {
	Name = "Title",
	BackgroundTransparency = 1,
	Size = UDim2.new(0.5, 0, 1, 0),
	Text = "✨ ITEM SHOP",
	TextXAlignment = Enum.TextXAlignment.Left,
	Font = Enum.Font.GothamBlack,
	TextSize = 30,
	TextColor3 = Theme.Text,
	ZIndex = 11,
	Parent = header,
}, {
	gradient(Color3.fromRGB(255, 236, 160), Theme.Accent),
})

local closeButton = create("TextButton", {
	Name = "Close",
	AnchorPoint = Vector2.new(1, 0.5),
	Position = UDim2.new(1, 0, 0.5, 0),
	Size = UDim2.fromOffset(40, 40),
	BackgroundColor3 = Theme.Danger,
	AutoButtonColor = false,
	Text = "✕",
	Font = Enum.Font.GothamBlack,
	TextSize = 20,
	TextColor3 = Color3.new(1, 1, 1),
	ZIndex = 11,
	Parent = header,
}, {
	corner(12),
	gradient(Color3.new(1, 1, 1), Color3.fromRGB(180, 180, 180)),
})
addButtonFeel(closeButton)

local coinPill = create("Frame", {
	Name = "Coins",
	AnchorPoint = Vector2.new(1, 0.5),
	Position = UDim2.new(1, -54, 0.5, 0),
	Size = UDim2.fromOffset(150, 40),
	BackgroundColor3 = Theme.Panel,
	ZIndex = 11,
	Parent = header,
}, {
	corner(20),
	stroke(Theme.Accent, 2, 0.3),
})
local coinLabel = create("TextLabel", {
	BackgroundTransparency = 1,
	Size = UDim2.fromScale(1, 1),
	Text = ShopConfig.CurrencyIcon .. " 0",
	Font = Enum.Font.GothamBold,
	TextSize = 20,
	TextColor3 = Theme.Accent,
	ZIndex = 12,
	Parent = coinPill,
})

-- Divider under header
create("Frame", {
	Position = UDim2.new(0, 22, 0, 68),
	Size = UDim2.new(1, -44, 0, 2),
	BackgroundColor3 = Theme.Stroke,
	BackgroundTransparency = 0.5,
	BorderSizePixel = 0,
	ZIndex = 11,
	Parent = window,
})

-- Category tabs -----------------------------------------------------------

local tabBar = create("Frame", {
	Name = "Tabs",
	Position = UDim2.new(0, 22, 0, 82),
	Size = UDim2.new(1, -44, 0, 38),
	BackgroundTransparency = 1,
	ZIndex = 11,
	Parent = window,
}, {
	create("UIListLayout", {
		FillDirection = Enum.FillDirection.Horizontal,
		Padding = UDim.new(0, 8),
		SortOrder = Enum.SortOrder.LayoutOrder,
	}),
})

-- Item grid ---------------------------------------------------------------

local grid = create("ScrollingFrame", {
	Name = "Items",
	Position = UDim2.new(0, 16, 0, 132),
	Size = UDim2.new(1, -32, 1, -148),
	BackgroundTransparency = 1,
	BorderSizePixel = 0,
	CanvasSize = UDim2.new(),
	AutomaticCanvasSize = Enum.AutomaticSize.Y,
	ScrollingDirection = Enum.ScrollingDirection.Y,
	ScrollBarThickness = 6,
	ScrollBarImageColor3 = Theme.Stroke,
	ZIndex = 11,
	Parent = window,
}, {
	padding(6),
	create("UIGridLayout", {
		CellSize = UDim2.fromOffset(172, 236),
		CellPadding = UDim2.fromOffset(14, 14),
		SortOrder = Enum.SortOrder.LayoutOrder,
		HorizontalAlignment = Enum.HorizontalAlignment.Center,
	}),
})

-- Toast notification ------------------------------------------------------

local toast = create("TextLabel", {
	Name = "Toast",
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0, -80),
	Size = UDim2.fromOffset(320, 48),
	BackgroundColor3 = Theme.Buy,
	Text = "",
	Font = Enum.Font.GothamBold,
	TextSize = 18,
	TextColor3 = Color3.new(1, 1, 1),
	ZIndex = 50,
	Parent = screenGui,
}, {
	corner(14),
	stroke(Color3.new(1, 1, 1), 2, 0.5),
})
local toastId = 0

local function showToast(message, success)
	toastId += 1
	local myId = toastId
	toast.Text = message
	toast.BackgroundColor3 = success and Theme.Buy or Theme.Danger
	tween(toast, 0.35, { Position = UDim2.new(0.5, 0, 0, 24) }, Enum.EasingStyle.Back)
	task.delay(2, function()
		if toastId == myId then
			tween(toast, 0.25, { Position = UDim2.new(0.5, 0, 0, -80) }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		end
	end)
end

-- Cards -------------------------------------------------------------------

local function refreshCard(card)
	local item = card.item
	local button = card.button
	if ownedItems[item.Id] then
		button.Text = "✔ OWNED"
		button.BackgroundColor3 = Theme.Owned
		button.TextColor3 = Theme.SubText
		card.buttonGradient.Enabled = false
	else
		local canAfford = currentCoins >= item.Price
		button.Text = ShopConfig.CurrencyIcon .. " " .. formatNumber(item.Price)
		button.BackgroundColor3 = canAfford and Theme.Buy or Theme.Owned
		button.TextColor3 = canAfford and Color3.new(1, 1, 1) or Color3.fromRGB(255, 140, 140)
		card.buttonGradient.Enabled = true
	end
end

local function refreshAllCards()
	for _, card in pairs(cards) do
		refreshCard(card)
	end
end

local function shake(frame)
	for _, angle in ipairs({ -4, 4, -3, 3, 0 }) do
		tween(frame, 0.05, { Rotation = angle }).Completed:Wait()
	end
end

local function buy(card)
	local item = card.item
	if ownedItems[item.Id] or card.busy then
		return
	end
	card.busy = true
	card.button.Text = "..."

	local ok, success, message = pcall(function()
		return purchaseRemote:InvokeServer(item.Id)
	end)
	card.busy = false

	if ok and success then
		ownedItems[item.Id] = true
		showToast(message, true)
		tween(card.scale, 0.12, { Scale = 1.12 }).Completed:Wait()
		tween(card.scale, 0.25, { Scale = 1 }, Enum.EasingStyle.Back)
	else
		showToast(ok and message or "Something went wrong", false)
		task.spawn(shake, card.frame)
	end
	refreshCard(card)
end

local function createCard(item, order)
	local rarityColor = ShopConfig.Rarities[item.Rarity] or ShopConfig.Rarities.Common

	local frame = create("Frame", {
		Name = item.Id,
		LayoutOrder = order,
		BackgroundColor3 = Theme.Card,
		ZIndex = 12,
		Parent = grid,
	}, {
		corner(14),
		gradient(Color3.new(1, 1, 1), Color3.fromRGB(190, 190, 205)),
	})
	local cardStroke = stroke(rarityColor, 2, 0.45)
	cardStroke.Parent = frame
	local scale = create("UIScale", { Parent = frame })

	-- Icon area tinted with the rarity color
	local iconArea = create("Frame", {
		Position = UDim2.fromOffset(8, 8),
		Size = UDim2.new(1, -16, 0, 112),
		BackgroundColor3 = rarityColor,
		BackgroundTransparency = 0.2,
		ZIndex = 13,
		Parent = frame,
	}, {
		corner(10),
		gradient(Color3.new(1, 1, 1), Color3.fromRGB(70, 70, 90)),
	})

	local iconProps = {
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.55),
		Size = UDim2.fromScale(0.62, 0.62),
		BackgroundTransparency = 1,
		ZIndex = 14,
		Parent = iconArea,
	}
	local icon
	if item.Image and item.Image ~= "" then
		iconProps.Image = item.Image
		iconProps.ScaleType = Enum.ScaleType.Fit
		icon = create("ImageLabel", iconProps)
	else
		iconProps.Text = item.Emoji or "?"
		iconProps.TextScaled = true
		iconProps.Font = Enum.Font.GothamBold
		icon = create("TextLabel", iconProps)
	end
	create("UIAspectRatioConstraint", { Parent = icon })

	-- Rarity badge
	create("TextLabel", {
		Position = UDim2.fromOffset(6, 6),
		Size = UDim2.fromOffset(0, 18),
		AutomaticSize = Enum.AutomaticSize.X,
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 0.45,
		Text = string.upper(item.Rarity),
		Font = Enum.Font.GothamBlack,
		TextSize = 11,
		TextColor3 = rarityColor,
		ZIndex = 15,
		Parent = iconArea,
	}, {
		corner(9),
		create("UIPadding", { PaddingLeft = UDim.new(0, 8), PaddingRight = UDim.new(0, 8) }),
	})

	create("TextLabel", {
		Position = UDim2.fromOffset(12, 126),
		Size = UDim2.new(1, -24, 0, 22),
		BackgroundTransparency = 1,
		Text = item.Name,
		TextXAlignment = Enum.TextXAlignment.Left,
		TextTruncate = Enum.TextTruncate.AtEnd,
		Font = Enum.Font.GothamBold,
		TextSize = 17,
		TextColor3 = Theme.Text,
		ZIndex = 13,
		Parent = frame,
	})

	create("TextLabel", {
		Position = UDim2.fromOffset(12, 149),
		Size = UDim2.new(1, -24, 0, 32),
		BackgroundTransparency = 1,
		Text = item.Description or "",
		TextXAlignment = Enum.TextXAlignment.Left,
		TextYAlignment = Enum.TextYAlignment.Top,
		TextWrapped = true,
		Font = Enum.Font.Gotham,
		TextSize = 12,
		TextColor3 = Theme.SubText,
		ZIndex = 13,
		Parent = frame,
	})

	local buttonGradient = gradient(Color3.new(1, 1, 1), Color3.fromRGB(185, 185, 185))
	local button = create("TextButton", {
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 1, -10),
		Size = UDim2.new(1, -20, 0, 38),
		BackgroundColor3 = Theme.Buy,
		AutoButtonColor = false,
		Font = Enum.Font.GothamBlack,
		TextSize = 17,
		TextColor3 = Color3.new(1, 1, 1),
		ZIndex = 14,
		Parent = frame,
	}, {
		corner(10),
		buttonGradient,
	})
	addButtonFeel(button)

	-- Card hover: lift and light up the rarity border
	frame.MouseEnter:Connect(function()
		tween(scale, 0.15, { Scale = 1.04 })
		tween(cardStroke, 0.15, { Transparency = 0, Thickness = 3 })
	end)
	frame.MouseLeave:Connect(function()
		tween(scale, 0.15, { Scale = 1 })
		tween(cardStroke, 0.15, { Transparency = 0.45, Thickness = 2 })
	end)

	local card = {
		item = item,
		frame = frame,
		button = button,
		buttonGradient = buttonGradient,
		scale = scale,
	}
	button.Activated:Connect(function()
		buy(card)
	end)

	cards[item.Id] = card
	refreshCard(card)
end

for index, item in ipairs(ShopConfig.Items) do
	createCard(item, index)
end

-- Tabs logic --------------------------------------------------------------

local tabButtons = {}

local function selectTab(category)
	for name, tab in pairs(tabButtons) do
		local selected = name == category
		tween(tab, 0.15, {
			BackgroundColor3 = selected and Theme.Accent or Theme.Panel,
			TextColor3 = selected and Theme.Background or Theme.SubText,
		})
	end
	for _, card in pairs(cards) do
		card.frame.Visible = category == "All" or card.item.Category == category
	end
	grid.CanvasPosition = Vector2.zero
end

for index, category in ipairs(ShopConfig.Categories) do
	local tab = create("TextButton", {
		Name = category,
		LayoutOrder = index,
		Size = UDim2.fromOffset(0, 38),
		AutomaticSize = Enum.AutomaticSize.X,
		BackgroundColor3 = Theme.Panel,
		AutoButtonColor = false,
		Text = category,
		Font = Enum.Font.GothamBold,
		TextSize = 16,
		TextColor3 = Theme.SubText,
		ZIndex = 12,
		Parent = tabBar,
	}, {
		corner(19),
		create("UIPadding", { PaddingLeft = UDim.new(0, 18), PaddingRight = UDim.new(0, 18) }),
	})
	addButtonFeel(tab)
	tab.Activated:Connect(function()
		selectTab(category)
	end)
	tabButtons[category] = tab
end
selectTab("All")

-- Open / close ------------------------------------------------------------

local isOpen = false

local function setOpen(open)
	if open == isOpen then
		return
	end
	isOpen = open

	if open then
		backdrop.Visible = true
		window.Visible = true
		windowScale.Scale = 0.8
		tween(windowScale, 0.35, { Scale = 1 }, Enum.EasingStyle.Back)
		tween(backdrop, 0.25, { BackgroundTransparency = 0.45 })
	else
		tween(backdrop, 0.2, { BackgroundTransparency = 1 })
		local t = tween(windowScale, 0.2, { Scale = 0.8 }, Enum.EasingStyle.Back, Enum.EasingDirection.In)
		t.Completed:Connect(function()
			if not isOpen then
				window.Visible = false
				backdrop.Visible = false
			end
		end)
	end
end

openButton.Activated:Connect(function()
	setOpen(not isOpen)
end)
closeButton.Activated:Connect(function()
	setOpen(false)
end)
backdrop.Activated:Connect(function()
	setOpen(false)
end)

UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed then
		return
	end
	if input.KeyCode == ShopConfig.ToggleKey then
		setOpen(not isOpen)
	end
end)

-- Coins -------------------------------------------------------------------

local coinCounter = Instance.new("NumberValue")
coinCounter.Changed:Connect(function(value)
	coinLabel.Text = ShopConfig.CurrencyIcon .. " " .. formatNumber(value)
end)

task.spawn(function()
	local leaderstats = player:WaitForChild("leaderstats")
	local coins = leaderstats:WaitForChild(ShopConfig.CurrencyName)

	local function onCoinsChanged()
		currentCoins = coins.Value
		-- Count up/down smoothly instead of jumping
		tween(coinCounter, 0.5, { Value = currentCoins })
		refreshAllCards()
	end
	coins.Changed:Connect(onCoinsChanged)
	onCoinsChanged()
end)

task.spawn(function()
	local ok, list = pcall(function()
		return getOwnedRemote:InvokeServer()
	end)
	if ok and type(list) == "table" then
		for _, itemId in ipairs(list) do
			ownedItems[itemId] = true
		end
		refreshAllCards()
	end
end)
