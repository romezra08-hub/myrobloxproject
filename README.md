# Shop UI for Roblox Studio

A shop styled in code: dark rounded window, gold title, a coin counter that counts up and down, category tabs, item cards with rarity colors and hover effects, pop-up messages and open/close animations.

## Quickest way: one paste

1. Open `InstallShop.lua` on GitHub and click **Copy raw file**.
2. In Studio, open **View → Command Bar**, paste it in, and press **Enter**.
3. Press **Play**.

The installer creates all 3 scripts for you. Ctrl+Z undoes it.

## Put it in Roblox Studio by hand

Make 3 scripts in the **Explorer** (hover a service → click **+**), then copy in the code from each file:

| In Studio, create…  | Inside…                                | Name it      | Copy code from                                   |
|---------------------|----------------------------------------|--------------|--------------------------------------------------|
| **ModuleScript**    | `ReplicatedStorage`                    | `ShopConfig` | `ReplicatedStorage/ShopConfig.lua`               |
| **Script**          | `ServerScriptService`                  | `ShopServer` | `ServerScriptService/ShopServer.server.lua`      |
| **LocalScript**     | `StarterPlayer > StarterPlayerScripts` | `ShopClient` | `StarterPlayerScripts/ShopClient.client.lua`     |

The names matter: the other scripts look for `ShopConfig` by name.

Press **Play**. Click the gold **SHOP** button (bottom-left) or press **B**.

If you already have an old shop GUI, delete it or disable it so you don't have two shops.

## Customize

Everything is in `ShopConfig`:
- **Items**: name, price, category, rarity, emoji, description. To use a picture, set `Image = "rbxassetid://YOUR_ID"`.
- **Theme**: all the colors.
- **Rarities**: border/badge color for each rarity.
- **StartingCoins**, **ToggleKey**, **CurrencyName**.

## Notes
- The server checks every purchase, so players can't buy things for free.
- What players own is **not saved** when they leave. Saving it needs a DataStore.
- Buying an item takes the coins and marks it owned. It doesn't hand out a tool or pet yet. Add that at the `-- Owned items` / purchase section in `ShopServer`.
