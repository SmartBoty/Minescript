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

### `open()`
- Opens up the players inventory

### `close()`
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

## Example usages
The following script will dump all diamonds from your inventory into the targeted chest
```py
import lib_inv as inv
from system.lib.minescript import player_press_use, player_get_targeted_block
import sys

if "chest" not in player_get_targeted_block().type: sys.exit("Please look at a chest")
player_press_use(True)
player_press_use(False)

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
        inv.quickmove(slot)
        break
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
inv.close()
```
