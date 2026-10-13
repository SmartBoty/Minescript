TYPE_CHECKING = True
TYPE_CHECKING = not TYPE_CHECKING
if not TYPE_CHECKING:
    import socket
    from system.lib.java import eval_pyjinn_script as eps
    import json
    from threading import Thread, get_ident, Lock
    from system.lib.minescript import version_info
    from uuid import uuid1
    from concurrent.futures import Future, TimeoutError

    version = int("".join([n for n in version_info().minecraft if n.isdigit()]))

    if not str(version).startswith("1"): version = int("99"+str(version))

    version_mappings = {
        "clicktype_const": {
            (0,12111) : ("handleInventoryMouseClick","""ClickType = JavaClass("net.minecraft.world.inventory.ClickType")"""),
            (99262,999999): ("handleContainerInput","""ClickType = JavaClass("net.minecraft.world.inventory.ContainerInput")""")
        },
        "screen_const": {
            (0,12111) : "",
            (99262,999999): ".gui"
        }
    }

    clicktype_mapping = [v for k,v in version_mappings["clicktype_const"].items() if k[0] <= version <= k[1]][0]
    screen_mapping = [v for k,v in version_mappings["screen_const"].items() if k[0] <= version <= k[1]][0]
    concurrent = {}
    writer_lock = Lock()

    bridge = socket.socket()
    bridge.bind(("127.0.0.1", 0))
    bridge.listen(1)
    port = bridge.getsockname()[1]

    eps(
r"""
mc = JavaClass("net.minecraft.client.Minecraft").getInstance()
ItemStack = JavaClass("net.minecraft.world.item.ItemStack")
GsonBuilder = JavaClass("com.google.gson.GsonBuilder")
JsonOps = JavaClass("com.mojang.serialization.JsonOps")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
Socket = JavaClass("java.net.Socket")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")
""" + clicktype_mapping[1] + r"""
RegistryOps = JavaClass("net.minecraft.resources.RegistryOps")
InventoryScreen = JavaClass("net.minecraft.client.gui.screens.inventory.InventoryScreen")
AbstractButton = JavaClass("net.minecraft.client.gui.components.AbstractButton")
MouseButtonEvent = JavaClass("net.minecraft.client.input.MouseButtonEvent")
MouseButtonInfo = JavaClass("net.minecraft.client.input.MouseButtonInfo")
MerchantScreen = JavaClass("net.minecraft.client.gui.screens.inventory.MerchantScreen")
MerchantOffer = JavaClass("net.minecraft.world.item.trading.MerchantOffer")
TradeOfferButton = JavaClass("net.minecraft.client.gui.screens.inventory.MerchantScreen$TradeOfferButton")
AbstractContainerScreen = JavaClass("net.minecraft.client.gui.screens.inventory.AbstractContainerScreen")
Array = JavaClass("java.lang.reflect.Array")
Object = JavaClass("java.lang.Object")

bridge = Socket("127.0.0.1", """ + str(port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))
gson = GsonBuilder().create()
screen_change_queue = []
guiScaleWidth = 1
guiScaleHeight = 1
getHoveredSlot = [m for m in type(AbstractContainerScreen).getDeclaredMethods() if m.getName() == "getHoveredSlot"][0]
getHoveredSlot.setAccessible(True)

def as_array(items,specific_type=Object):
    array = Array.newInstance(type(specific_type),len(items))
    for i,arg in enumerate(items):
        Array.set(array, i, arg)
    return array

def return_call(ufcid,data):
    if data is None: data = "null"
    elif data is True: data = "true"
    elif data is False: data = "false"
    writer.write(f"{ufcid}""" + '#' + r""":"+data + "\n")
    writer.flush()

def serialize_stack(itemstack):
    return gson.toJson(ItemStack.CODEC.encodeStart(RegistryOps.create(JsonOps.INSTANCE, mc.level.registryAccess()), itemstack).getOrThrow())

def serialize_offer(offer):
    return gson.toJson(MerchantOffer.CODEC.encodeStart(RegistryOps.create(JsonOps.INSTANCE, mc.level.registryAccess()), offer).getOrThrow())

def inventory(*_):
    out = []
    for slot in mc.player.containerMenu.slots:
        itemstack = slot.getItem()
        if str(itemstack) != "0 minecraft:air": out.append(serialize_stack(itemstack))
        else: out.append('{"id":"minecraft:air","count":0}')
    return "[" + ",".join(out) + "]"

def pickup(slot,mouse):
    slot = int(slot)
    mouse = int(mouse)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot, mouse, ClickType.PICKUP, mc.player)

def quickmove(slot,mouse):
    slot = int(slot)
    mouse = int(mouse)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot, mouse, ClickType.QUICK_MOVE, mc.player)

def throw(slot,all):
    slot = int(slot)
    all = int(all)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot, all, ClickType.THROW, mc.player)

def swap(slot1,slot2):
    slot1 = int(slot1)
    slot2 = int(slot2)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot1, slot2, ClickType.SWAP, mc.player)

def quick_craft(slot, action):
    slot = int(slot)
    action = int(action)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot, action, ClickType.QUICK_CRAFT, mc.player)

def pickup_all(slot, action):
    slot = int(slot)
    action = int(action)
    mc.gameMode.""" + clicktype_mapping[0] + r"""(mc.player.containerMenu.containerId, slot, action, ClickType.PICKUP_ALL, mc.player)

def open(*_):
    mc""" + screen_mapping + r""".setScreen(InventoryScreen(mc.player))

def close(*_):
    mc.player.closeContainer()

def get_item(slot):
    _slot = int(slot)
    i = -1
    for slot in mc.player.containerMenu.slots:
        i += 1
        if i == _slot: itemstack = slot.getItem()
    if str(itemstack) != "0 minecraft:air": return serialize_stack(itemstack)
    else: return '{"id":"minecraft:air","count":0}'

def wait_for_gui_change(id):
    screen_change_queue.append((id,mc""" + screen_mapping + r""".screen()))

def use(*_):
    player_press_use(True)
    player_press_use(False)

def get_buttons(*_):
    buttons = []
    for i, widget in enumerate(mc""" + screen_mapping + r""".screen().children()):
        if isinstance(widget, AbstractButton):
            buttons.append(widget.getMessage().getString())
    return str(buttons)

def press_button(id, button, modifiers):
    id = int(id)
    for i, widget in enumerate(mc""" + screen_mapping + r""".screen().children()):
        if isinstance(widget, AbstractButton):
            if i == id:
                widget.onPress(MouseButtonEvent(mc.mouseHandler.xpos()/guiScaleWidth, mc.mouseHandler.ypos()/guiScaleHeight, MouseButtonInfo(int(button), int(modifiers))))

def get_trades(*_):
    offers = []
    screen = mc""" + screen_mapping + r""".screen()
    if isinstance(screen, MerchantScreen):
        for offer in screen.getMenu().getOffers():
            offers.append(serialize_offer(offer))
    return str(offers)

def select_offer(id, button, modifiers):
    id = int(id)
    screen = mc""" + screen_mapping + r""".screen()
    if isinstance(screen, MerchantScreen):
        menu = screen.getMenu()
        i = -1
        for widget in screen.children():
            if isinstance(widget, TradeOfferButton):
                i += 1
                if i == id:
                    widget.onPress(MouseButtonEvent(mc.mouseHandler.xpos()/guiScaleWidth, mc.mouseHandler.ypos()/guiScaleHeight, MouseButtonInfo(int(button), int(modifiers))))
                    return

def scroll_offers(by):
    by = int(by)
    mc""" + screen_mapping + r""".screen().mouseScrolled(mc.mouseHandler.xpos()/guiScaleWidth, mc.mouseHandler.ypos()/guiScaleHeight, 0, by)

def get_slot_at(x,y):
    x = int(x) / guiScaleWidth
    y = int(y) / guiScaleHeight
    slot = getHoveredSlot.invoke(mc""" + screen_mapping + r""".screen(),as_array((x,y)))
    if slot is None: return '{"id":"minecraft:air","count":0}'
    itemstack = slot.getItem()
    if str(itemstack) != "0 minecraft:air": return serialize_stack(itemstack)
    else: return '{"id":"minecraft:air","count":0}'

def get_cursor(*_):
    itemstack = mc.player.containerMenu.getCarried()
    if str(itemstack) != "0 minecraft:air": return serialize_stack(itemstack)
    else: return '{"id":"minecraft:air","count":0}'

callables = {
"inventory":inventory,
"pickup":pickup,
"quickmove":quickmove,
"swap":swap,
"open":open,
"get_item":get_item,
"close":close,
"throw":throw,
"wait_for_gui_change":wait_for_gui_change,
"use":use,
"get_buttons":get_buttons,
"press_button":press_button,
"get_trades":get_trades,
"select_offer":select_offer,
"scroll_offers":scroll_offers,
"get_slot_at":get_slot_at,
"get_cursor":get_cursor,
"quick_craft":quick_craft,
"pickup_all":pickup_all
}

def frame(_):
    global guiScaleWidth, guiScaleHeight
    guiScaleWidth = mc.getWindow().getWidth() / mc.getWindow().getGuiScaledWidth()
    guiScaleHeight = mc.getWindow().getHeight() / mc.getWindow().getGuiScaledHeight()
    scrn = mc""" + screen_mapping + r""".screen()
    i = -1
    for id, screen in screen_change_queue.copy():
        i += 1
        if scrn != screen:
            return_call(id,True)
            screen_change_queue.pop(i)
    lines = []
    iters = 0
    if not reader.ready(): return
    while True:
        iters += 1
        if iters > 100: log("[Lib_inv] Overloaded! Exiting reader...") ; break
        try:
            if not reader.ready(): break
            line = reader.readLine()
            if line: lines.append(line)
            else: break
        except Exception as e:
            break
    for line in lines:
        cmd = line.split(":")
        if cmd[0][0] == "R":
            ufcid, func = cmd[0].split(""" + '"#"' + r""")
            return_call(ufcid[1:],callables[func](*cmd[1].split(",")))
        elif cmd[0][0] == "A":
            ufcid, func = cmd[0].split(""" + '"#"' + r""")
            callables[func](ufcid[1:])
        else: callables[cmd[0][1:]](*cmd[1].split(","))

add_event_listener("render",frame)
""")

    conn, _ = bridge.accept()
    writer = conn.makefile(mode="w",encoding="utf-8")
    reader = conn.makefile(mode="r",encoding="utf-8")

    def __reader__():
        while True:
            line = reader.readline()
            if not line: continue
            ufcid, *data = line.split(":")
            if ufcid in concurrent:
                concurrent.pop(ufcid).set_result(":".join(data))

    Thread(target=__reader__,daemon=True).start()

    def next_ufcid():
        return f"{get_ident()}@{uuid1()}#"

    def await_function_call(func_name,*args,awaited=False,timeout=None):
        ufcid = next_ufcid()
        future = Future()
        concurrent[ufcid] = future
        if not awaited: data = f"R{ufcid}{func_name}:{",".join(args) if args else ""}\n"
        else: data = f"A{ufcid}{func_name}:{",".join(args) if args else ""}\n"
        with writer_lock:
            writer.write(data)
            writer.flush()
        try: return future.result(timeout=timeout)[:-1]
        except TimeoutError: return None

    def noreturn_function_call(func_name,*args):
        data = f"N{func_name}:{",".join(args) if args else ""}\n"
        with writer_lock:
            writer.write(data)
            writer.flush()

del TYPE_CHECKING

def inventory() -> list[dict]:
    """
    Returns the entire player inventory, as a list of dicts
    """
    return json.loads(await_function_call("inventory"))

def pickup(slot:int,mouse:int=0):
    """
    Simulate a pickup action on a slot
    """
    noreturn_function_call("pickup",str(slot),str(mouse))

def quickmove(slot:int,mouse:int=0):
    """
    Simulate a quickmove action on a slot
    """
    noreturn_function_call("quickmove",str(slot),str(mouse))

def swap(slot1:int,slot2:int):
    """
    Simulate a swap action on 2 slots
    """
    noreturn_function_call("swap",str(slot1),str(slot2))

def throw(slot:int,stack:bool=False):
    """
    Simulate a throw action on a slot
    """
    noreturn_function_call("throw",str(slot),str(1 if stack else 0))

def quick_craft(slot:int, action:int=0):
    """
    Simulates a quick craft action on a slot
    """
    noreturn_function_call("quick_craft",str(slot),str(action))

def pickup_all(slot:int, direction:int=0):
    """
    Performs a pickup all action on a slot

    `direction` determines which order minecraft scans the inventory slots for matching items
    """
    noreturn_function_call("pickup_all",str(slot),str(direction))

def open_inventory():
    """
    Opens up the players inventory
    """
    noreturn_function_call("open")

def close_inventory():
    """
    Closes any open gui
    """
    noreturn_function_call("close")

def get_item(slot:int) -> dict:
    """
    Get the item from a slot
    """
    return json.loads(await_function_call("get_item",str(slot)))

def wait_for_screen_change(timeout=None):
    """
    Blocks untill the screen changes
    """
    return await_function_call("wait_for_gui_change",awaited=True,timeout=timeout) is True

def open_targeted_container(timeout=None):
    """
    Attempts to open the targeted container
    """
    noreturn_function_call("use")
    return wait_for_screen_change(timeout)

def get_all_buttons():
    """
    Returns all clickeable buttons in the current gui
    """
    return json.loads(await_function_call("get_buttons"))

def press_button(idx:int, mouse:int=0, modifiers:int=0):
    """
    Presses a button by index
    """
    noreturn_function_call("press_button",str(idx),str(mouse),str(modifiers))

def get_trade_offers():
    """
    Returns all trade offers, or None if there arent any in the currently open gui
    """
    return json.loads(await_function_call("get_trades"))

def select_trade_offer(idx:int, mouse:int=0, modifiers:int=0):
    """
    Selects a trade offer from index
    """
    noreturn_function_call("select_offer",str(idx),str(mouse),str(modifiers))

def scroll_trade_offers(by:int):
    """
    Scrolls the trade selection sidebar
    """
    noreturn_function_call("scroll_offers",str(-by))

def get_slot_at(x:int, y:int) -> dict:
    """
    Returns the item from a slot at a certain screen pixel coordinate
    """
    return json.loads(await_function_call("get_slot_at",str(x),str(y)))

def get_cursor_item() -> dict:
    """
    Returns the item at the cursor
    """
    return json.loads(await_function_call("get_cursor"))

class QuickCraft:
    """
    Helper class containing mapped QUICK_CRAFT actions
    """
    BEGIN_EVEN = 0
    ADD_EVEN = 1
    END_EVEN = 2

    BEGIN_SINGLE = 4
    ADD_SINGLE = 5
    END_SINGLE = 6

    BEGIN_CLONE = 8
    ADD_CLONE = 9
    END_CLONE = 10

class PickupAll:
    """
    Helper class containing mapped PICKUP_ALL directions
    """
    FIRST_TO_LAST = 0
    LAST_TO_FIRST = 1

class Slots:
    """
    Helper class containing notable slots
    """
    NULL = -999
    OUTSIDE = -999

__all__ = [
    "inventory",
    "pickup",
    "quickmove",
    "swap",
    "throw",
    "quick_craft",
    "pickup_all",
    "open_inventory",
    "close_inventory",
    "get_item",
    "wait_for_screen_change",
    "open_targeted_container",
    "get_all_buttons",
    "press_button",
    "get_trade_offers",
    "select_trade_offer",
    "scroll_trade_offers",
    "get_slot_at",
    "get_cursor_item",
    "QuickCraft",
    "PickupAll",
    "Slots"
]