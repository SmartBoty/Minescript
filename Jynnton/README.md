# Jynnton - Pyjinn from Python
Jynnton (`ˈdʒɪn.θən`, aka Jinn-ton) is a library made for Minescript, that allows you to create and run Pyjinn functions from Python.

Requirements:
- Minescript 5.0+
- Mappings (`\install_mappings`) for versions below 26.x
- `pyjinn_json`: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py
- Only tested on version 5.0b11, but may work on other versions aswell
- Python 3.12 +

What this library allows you to do:
- Execute Pyjinn code, straight from Python
- Easy calback between Python and Pyjinn
- Run functions on Pyjinn events
- And ofc, access java internals in just miliseconds

## How to use the library
Very simple actually. Just use the given decorator
```py
from Jynnton import as_pyjinn

@as_pyjinn()
def foo(): pass
```
Upon calling `foo()`, the function will now be called in Pyjinn

Example usage:

This will render a cube at the block you are looking at
```py
from Jynnton import Pyjinn, JavaClass, add_event_listener
from time import sleep

pyj = Pyjinn()

with pyj:
    BlockHitResult = JavaClass("net.minecraft.world.phys.BlockHitResult")
    Gizmos = JavaClass("net.minecraft.gizmos.Gizmos")
    ARGB = JavaClass("net.minecraft.util.ARGB")
    BlockPos = JavaClass("net.minecraft.core.BlockPos")
    GizmoStyle = JavaClass("net.minecraft.gizmos.GizmoStyle")
    mc = JavaClass("net.minecraft.client.Minecraft").getInstance()

    def render(event):
        hit = mc.hitResult
        if hit:
            if hit.getType() == BlockHitResult.Type.BLOCK:
                Gizmos.cuboid(BlockPos(hit.getBlockPos()),GizmoStyle.stroke(ARGB.color(255,200,100,200))).setAlwaysOnTop()
    
    add_event_listener("render",render)

    def foo():
        print("Bar")

while True: sleep(1)
```
