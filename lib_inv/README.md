# Lib Inv
Easily and quickly manipulate the inventory.

Requirements:
- python 3.12+
- mappings (`\install_mappings`) for versions below 26.x
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
- Closes any openn gui

### `get_item(slot) -> dict`
- Get an item from a slot

## Example usage
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
