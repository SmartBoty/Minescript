# Lib Inv
Easily and quickly manipulate the inventory.

Requirements:
- python 3.12+
- mappings (`\install_mappings`) for versions below 26.x
- Minescript 5.0b+
# Functions

### `inventory() -> list[dict]`
- returns the currently open inventory as a list of dicts (items)

### `pickup(slot,mouse=0)`
- Simulate a pickup action on a slot

### `quickmove(slot,mouse=0)`
- Simulate a quickmove action on a slot

### `swap(slot1,slot2)`
- Simulate a swap action on 2 slots

### `throw(slot:int,stack:bool=False)`
- Simulate a throw action on a slot
- if `stack` is true, drop a whole stack

### `quick_craft(slot:int, action:int=0)`
- Performs a quick craft action on a slot
- Its probably not what you think, it is mostly used to spread items evenly across many slots (see example below)

### `pickup_all(slot:int, direction:int=0)`
- Performs a pickup all action on a slot
- `direction` determines which order minecraft scans the inventory slots for matching items

### `get_slot_at(x:int, y:int) -> dict`
- Returns the item in a slot at `x` and `y` screen coordinates

### `get_cursor_item() -> dict`
- Returns the item in the cursor

### `open_inventory()`
- Opens up the players inventory

### `close_inventory()`
- Closes any open gui

### `get_item(slot) -> dict`
- Get an item from a slot

### `wait_for_screen_change(timeout=None)`
- Blocks untill the screen changes, with an optional timeout
- Returns `False` if it timed out, `True` if the screen changed in time
- A timeout of `None`, means forever

### `open_targeted_container(timeout=None)`
- Same as `wait_for_screen_change`, but also uses a 0 frame version of `player_press_use`, to open up the target container

### `get_all_buttons() -> list[str]`
- Returns all buttons names in a persistent order
- Get the index by enumerating it

### `press_button(idx:int, mouse:int=0, modifiers:int=0)`
- Press a button by index
- `mouse` is the mouse button (0 for LMB, 1 for RMB etc.)
- `modifiers` is modifiers such as shift or ctrl, 0 means no modifiers

### `get_trade_offers() -> list[dict]`
- Returns all trade offers, even the ones that are off screen

### `select_trade_offer(idx:int, mouse:int=0, modifiers:int=0)`
- Selects a trade offer, but doesnt buy it
- Offer must be on screen
- `idx` is not consistent with index returned from enumerating `get_trade_offers` (see example below to see how you can bypass this)

### `scroll_trade_offers(by:int)`
- Scrolls the trade offers

## Helper classes

### `QuickCraft`
- Helper class containing mapped QUICK_CRAFT actions
```
# LMB drag
BEGIN_EVEN
ADD_EVEN
END_EVEN

# RMB drag
BEGIN_SINGLE
ADD_SINGLE
END_SINGLE

# MMB drag (creative only)
BEGIN_CLONE
ADD_CLONE
END_CLONE
```

### `PickupAll`
- Helper class containing mapped PICKUP_ALL directions
```
# Default
FIRST_TO_LAST

# Reversed
LAST_TO_FIRST
```

### `Slots`
- Helper class containing notable slots
```
NULL
OUTSIDE # "Outside of inventory"
```

## Example usages
The following script will dump all diamonds from your inventory into the targeted chest
```py
import lib_inv as inv
from system.lib.minescript import player_press_use, player_get_targeted_block
import sys
from time import sleep

if "chest" not in player_get_targeted_block().type: sys.exit("Please look at a chest")
player_press_use(True)
player_press_use(False)

sleep(0.2)

for slot, item in enumerate(inv.inventory()):
    if item["id"] == "minecraft:diamond":
        inv.quickmove(slot)
```
This will choose a "Speed 1" effect on a beacon (assuming you are looking at it, and it is capable of choosing an effect)
```py
import lib_inv as inv
from time import sleep

inv.open_targeted_container()
sleep(0.2)
for slot, item in enumerate(inv.inventory()):
    if item["id"] == "minecraft:iron_ingot":
        inv.pickup(slot)
        break
inv.pickup(0,1)
inv.pickup(slot)
sleep(0.2)
inv.press_button(0) # Button for the "Speed 1" effect
for i, button in enumerate(inv.get_all_buttons()):
    if button == "Done": # The green checkmark
        inv.press_button(i)
```
This will cycle through all trades of a villager, selecting each one of them, and then closes the gui
```py
import lib_inv as inv
from time import sleep

inv.open_targeted_container()
sleep(0.2)
for i, offer in enumerate(inv.get_trade_offers()):
    if i > 6:
        inv.scroll_trade_offers(1)
        sleep(0.1)
    inv.select_trade_offer(min(i,6))
    sleep(0.2)
sleep(1)
inv.close_inventory()
```
This will open up your inventory, spread the item in slot `9` (top left slot) across your inventory evenly, then collect it back into the same slot
```py
from lib_inv import *
from time import sleep

open_inventory()
sleep(0.2)

pickup(9)
sleep(0.5)
quick_craft(Slots.NULL, QuickCraft.BEGIN_EVEN)
for slot in range(9, 18):
    quick_craft(slot, QuickCraft.ADD_EVEN)
quick_craft(Slots.NULL, QuickCraft.END_EVEN)
sleep(0.5)
pickup(9)

sleep(0.5)
pickup(9)
sleep(0.5)
pickup_all(9)
sleep(0.5)
pickup(9)
```
