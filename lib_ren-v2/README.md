# Lib Ren - v2 aka *Rendering Library v2*
Easily render simple objects in world, or on the HUD

v1 by `JulianIsLost`: https://github.com/JulianIsLost5/minescript-scripts/tree/main/lib_ren

Requires:
- Python 3.12+
- Minescript 5.0+
- Minecraft 1.21.8+
- `pyjinn_json`: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py

## `Renderer`
Main class to render with this library

Ctor:
`Renderer(name=None, *, clear_on_push=True)`

If `clear_on_push` is `True`, the instruction list will be cleared after giving it to Pyjinn to render

Usage:
```py
renderer = Renderer()
with renderer as (GuiGraphics, Gizmos, Matrix): ...
```
- Block untill the next frame: `renderer.await_frame()`
- Push changes made: `renderer.push_stack()`
- Clear current state: `renderer.clear()`
Note: the `with` statement does the above automatically
- Get the `GUI` scale (updates every frame): `renderer.gui_scale()`

Other:
```py
renderer.iter_instructions()
renderer.supress_warnings()

renderer.GuiGraphics
renderer.Gizmos
renderer.Matrix
```
Note: No visual changes will be made untill `push_stack()` is called

## `GuiGraphics`
Provides a small subset of the `GuiGraphics` / `GuiGraphicsExtractor` api:
```py
GuiGraphics.fill(x1:int, y1:int, x2:int, y2:int, color:tuple[int,int,int,int])
GuiGraphics.text(text:str, x:int, y:int, color:tuple[int,int,int,int])
```

## `Gizmos`
Provides a small subset of the `Gizmos` api:
```py
Gizmos.text(text:str, pos:tuple[float,float,float], style:TextGizmoStyle)
Gizmos.cuboid(bounding_box:AABB, style:GizmoStyle)
Gizmos.line(start:tuple[float,float,float], end:tuple[float,float,float], color:tuple[int,int,int,int], width:float)
Gizmos.point(pos:tuple[float,float,float], color:tuple[int,int,int,int], size:float)
```

## `Matrix`
Provides a subset of `Matrix3x2fStack` matrix manipulation, specifically for `GuiGraphics`:
```py
Matrix.translate(x:float, y:float)
Matrix.scale(scale:float)
Matrix.scale(scale_x:float, scale_y:float)
Matrix.rotate(degrees:float) # In radians
Matrix.transform(x:float, y:float, scale_x:float, scale_y:float, degrees:float)
Matrix.clear()
```
Important:
- Rotating always uses `radians`, not `degrees`. Use `math.radians(degrees)` to convert
- `.clear()` only clears the current `Matrix` pose (transformations before this stay, but not after)
