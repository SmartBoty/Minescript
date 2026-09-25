from __future__ import annotations
from system.lib.minescript import version_info, log as _log, echo
import sys

debug = False
verinf = version_info()

_mc_major_version,*_mc_minor_version = verinf.minecraft.split(".")
_minescript_version_index = verinf.minescript.split(".")
_is_fabric = "fabric" in verinf.mod_loader.lower()

def log(msg):
    if debug: print(f"[Lib Ren-v2] {msg}",file=sys.stderr)
    else: _log(f"[Lib Ren-v2] {msg}")

if not _is_fabric: sys.exit(f"Expected modloader to be 'Fabric', but got: {verinf.mod_loader}")
if int(_mc_major_version) >= 26:
    log("26.x detected!")
    _render_imports = (
r"""
HudElementRegistry = JavaClass("net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry")
Identifier = JavaClass("net.minecraft.resources.Identifier")
UUID = JavaClass("java.util.UUID")
render_id = Identifier.fromNamespaceAndPath(UUID.randomUUID().toString(),UUID.randomUUID().toString())
""")
    _render_register = (
r"""
HudElementRegistry.addLast(render_id, ManagedCallback(manage_render))
""")
    _render_drawstring = "text"
elif int(_mc_minor_version[-1]) >= 8 and int(_mc_minor_version[0]) >= 21:
    log("1.21.x detected!")
    _render_imports = (
r"""
HudRenderCallback = JavaClass("net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback")
""")
    _render_register = (
r"""
HudRenderCallback.EVENT.register(HudRenderCallback(ManagedCallback(manage_render)))
""")
    _render_drawstring = "drawString"
else: sys.exit(f"Expected version to be 1.21.8 or higher, but got: {".".join([_mc_major_version,*_mc_minor_version])}")

from threading import Thread, Lock
import socket
import json
from system.lib.java import eval_pyjinn_script as eps
from concurrent.futures import Future
import os

def convert_to_json(obj):
    method = getattr(obj, "__json__", None)
    if callable(method): return method()
    else: return obj

_bridge = socket.socket()
_bridge.bind(("127.0.0.1", 0))
_bridge.listen(1)
_port = _bridge.getsockname()[1]
_write_lock = Lock()

def _read():
    return _reader.readline()

def _write(data):
    with _write_lock:
        _writer.write(data+"\n")
        _writer.flush()

class AppendOnlyList:
    def __init__(self, items=[]):
        self._list = list(items)

    def append(self, *items):
        self._list += list(items)

    def __iter__(self):
        return iter(self._list)

    def __list__(self):
        return self._list

    def __len__(self):
        return len(self._list)

    def copy(self):
        return self._list.copy()

    def index(self, index):
        return self._list.index(index)

    def __getitem__(self, index):
        return self._list[index]

class Promise:
    def __init__(self):
        self.future = Future()
        self.avaliable = True
        self.lock = Lock()

    def fulfill(self, data=None):
        if self.avaliable:
            self.avaliable = False
            self.future.set_result(data)

    def get(self):
        self.avaliable = True
        result = self.future.result()
        self.future = Future()
        return result

    def throw(self, exc):
        if self.avaliable:
            self.future.set_exception(exc)

class Vec3D:
    def __new__(cls, x:float, y:float, z:float) -> tuple[float,float,float]:
        return (x,y,z)

class ARGB:
    @staticmethod
    def color(alpha, red, green, blue) -> tuple[int,int,int,int]:
        return (round(alpha),round(red),round(green),round(blue))

class Shapes:
    RECTANGLE = 0
    TEXT = 1
    CUBOID = 3
    LINE3D = 4
    POINT3D = 5
    TEXT3D = 6

class GuiGraphic:
    def __json__(self):
        if self.type == Shapes.RECTANGLE:
            return {"type":Shapes.RECTANGLE,"x1":self.x1,"y1":self.y1,"x2":self.x2,"y2":self.y2,"color":self.color}
        elif self.type == Shapes.TEXT:
            return {"type":Shapes.TEXT,"text":self.text,"x":self.x,"y":self.y,"color":self.color}
        else:
            return {"type":self.type}

    @property
    def attributes(self):
        return [k for k in self.__dict__ if not k.startswith("__") and not k == "attributes"]

class GuiGraphics:
    def __init__(self, parent:Renderer):
        self.renderer = parent

    def __enter__(self) -> GuiGraphics:
        self.renderer.await_frame()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.renderer.push_stack()

    def fill(self, x1:int, y1:int, x2:int, y2:int, color:tuple[int]):
        this = GuiGraphic()
        this.type = Shapes.RECTANGLE
        this.x1 = round(x1)
        this.x2 = round(x2)
        this.y1 = round(y1)
        this.y2 = round(y2)
        this.color = color
        self.renderer._handle_instruction(this)

    def text(self, text:str, x:int, y:int, color:tuple[int]):
        this = GuiGraphic()
        this.type = Shapes.TEXT
        this.text = text
        this.x = round(x)
        this.y = round(y)
        this.color = color
        self.renderer._handle_instruction(this)

class AABB:
    def __new__(cls, x1:float, y1:float, z1:float, x2:float, y2:float, z2:float) -> tuple[float,float,float,float,float,float]:
        return (float(x1), float(y1), float(z1), float(x2), float(y2), float(z2))

class GizmoStyle:
    @staticmethod
    def stroke(color:tuple[int,int,int,int], width:float=1) -> dict[str,tuple[int,int,int,int],float]:
        return {"type":"stroke","color":color,"width":width}

    @staticmethod
    def fill(color:tuple[int,int,int,int]) -> dict[str,tuple[int,int,int,int]]:
        return {"type":"fill","color":color}

    @staticmethod
    def strokeAndFill(stroke_color:tuple[int,int,int,int], stroke_width:float, fill_color:tuple[int,int,int,int]) -> dict[str,tuple[int,int,int,int],float,int]:
        return {"type":"strokeAndFill","color":stroke_color,"width":stroke_width,"fill":fill_color}

class TextGizmoStyle:
    def __new__(cls, color:tuple[int,int,int,int], scale:float, offset_left:float) -> dict[tuple[int,int,int,int],float,float]:
        return {"color":color,"scale":float(scale),"offset_left":float(offset_left)}

class Gizmo:
    def __init__(self):
        self.alwaysontop = False

    def __json__(self):
        if self.type == Shapes.CUBOID:
            return {"type":self.type, "alwaysontop":self.alwaysontop, "aabb":self.aabb, "style":self.style}
        elif self.type == Shapes.LINE3D:
            return {"type":self.type, "alwaysontop":self.alwaysontop, "start":self.start, "end":self.end, "color":self.color, "width":self.width}
        elif self.type == Shapes.POINT3D:
            return {"type":self.type, "alwaysontop":self.alwaysontop, "pos":self.pos, "color":self.color, "size":self.size}
        elif self.type == Shapes.TEXT3D:
            return {"type":self.type, "alwaysontop":self.alwaysontop, "text":self.text, "pos":self.pos, "style":self.style}
        else:
            return {"type":self.type}

    def setAlwaysOnTop(self):
        self.alwaysontop = True

    @property
    def attributes(self):
        return [k for k in self.__dict__ if not k.startswith("__") and not k in ("attributes","setAlwaysOnTop")]

class Gizmos:
    def __init__(self, parent:Renderer):
        self.renderer = parent

    def __enter__(self) -> Gizmos:
        self.renderer.await_frame()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.renderer.push_stack()

    def cuboid(self, bounding_box:AABB, style:GizmoStyle) -> Gizmo:
        this = Gizmo()
        this.type = Shapes.CUBOID
        this.aabb = bounding_box
        this.style = style
        self.renderer._handle_instruction(this)
        return this

    def line(self, start:tuple[float,float,float], end:tuple[float,float,float], color:tuple[int,int,int,int], width:float) -> Gizmo:
        this = Gizmo()
        this.type = Shapes.LINE3D
        this.start = start
        this.end = end
        this.color = color
        this.width = width
        self.renderer._handle_instruction(this)
        return this

    def point(self, pos:tuple[float,float,float], color:tuple[int,int,int,int], size:float) -> Gizmo:
        this = Gizmo()
        this.type = Shapes.POINT3D
        this.pos = pos
        this.color = color
        this.size = size
        self.renderer._handle_instruction(this)
        return this

    def text(self, text:str, pos:tuple[float,float,float], style:TextGizmoStyle) -> Gizmo:
        this = Gizmo()
        this.type = Shapes.TEXT3D
        this.text = text
        this.pos = pos
        this.style = style
        self.renderer._handle_instruction(this)
        return this

class Matrix:
    def __json__(self):
        if self.type == "matrix_translate":
            return {"type":self.type, "x": self.x, "y": self.y}
        elif self.type == "matrix_scale":
            return {"type":self.type, "scale_x":self.scale_x, "scale_y": self.scale_y}
        elif self.type == "matrix_rotate":
            return {"type":self.type, "degrees":self.degrees}
        elif self.type == "matrix_transform":
            return {"type":self.type, "x": self.x, "y": self.y, "scale_x":self.scale_x, "scale_y": self.scale_y, "degrees":self.degrees}
        else:
            return {"type":self.type}

class Matricies:
    def __init__(self, parent:Renderer):
        self.renderer = parent

    def translate(self, x:float, y:float):
        this = Matrix()
        this.type = "matrix_translate"
        this.x = x
        this.y = y
        self.renderer._handle_instruction(this)

    def scale(self, scale:float, scale_y:float=None):
        this = Matrix()
        this.type = "matrix_scale"
        this.scale_x = scale
        this.scale_y = scale_y if scale_y is not None else scale
        self.renderer._handle_instruction(this)

    def rotate(self, degrees:float):
        this = Matrix()
        this.type = "matrix_rotate"
        this.degrees = degrees
        self.renderer._handle_instruction(this)

    def clear(self):
        this = Matrix()
        this.type = "matrix_new"
        self.renderer._handle_instruction(this)

    def transform(self, x_pos:float, y_pos:float, scale_x:float, scale_y:float, degrees:float):
        this = Matrix()
        this.type = "matrix_transform"
        this.x = x_pos
        this.y = y_pos
        this.scale_x = scale_x
        this.scale_y = scale_y
        this.degrees = degrees
        self.renderer._handle_instruction(this)

renderers:AppendOnlyList[Renderer] = AppendOnlyList() # type:ignore

class Renderer:
    def __init__(self, name = None, *, clear_on_push=True) -> Renderer:
        self._instructions = []
        self._promise = Promise()
        self.GuiGraphics = GuiGraphics(self)
        self.Gizmos = Gizmos(self)
        self.Matrix = Matricies(self)
        self.id = len(renderers)
        self.name = name if name is not None else "<Unidentified>"
        self._guiscale = 4
        self.clear_on_push = clear_on_push
        self._supress_warnings = False
        renderers.append(self)

    def __enter__(self) -> tuple[GuiGraphics,Gizmos,Matricies]:
        self.await_frame()
        return (self.GuiGraphics,self.Gizmos,self.Matrix)

    def __exit__(self, exc_type, exc, tb):
        self.push_stack()

    def _handle_instruction(self, instruction:dict):
        self._instructions.append(instruction)

    def push_stack(self):
        instructions = self._instructions.copy()
        if self.clear_on_push: self.clear()
        _write(json.dumps({"id":self.id, "name":self.name, "instructions":instructions},default=convert_to_json))

    def await_frame(self):
        self._promise.get()

    def gui_scale(self):
        if not _script_loaded:
            self.await_frame()
        return self._guiscale

    def clear(self):
        self._instructions.clear()

    def iter_instructions(self):
        return iter(self._instructions)

    def supress_warnings(self, state=True):
        self._supress_warnings = state

def __begin__():
    try:
        eps(r"""
import pyjinn_json as json
Socket = JavaClass("java.net.Socket")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")
ARGB = JavaClass("net.minecraft.util.ARGB")
mc = JavaClass("net.minecraft.client.Minecraft").getInstance()
Component = JavaClass("net.minecraft.network.chat.Component")
ChatFormatting = JavaClass("net.minecraft.ChatFormatting")
""" + _render_imports + r"""
SocketException = JavaClass("java.net.SocketException")
Gizmos = JavaClass("net.minecraft.gizmos.Gizmos")
GizmoStyle = JavaClass("net.minecraft.gizmos.GizmoStyle")
AABB = JavaClass("net.minecraft.world.phys.AABB")
Vec3 = JavaClass("net.minecraft.world.phys.Vec3")
TextGizmoStyle = JavaClass("net.minecraft.gizmos.TextGizmo$Style")
OptionalDouble = JavaClass("java.util.OptionalDouble")
Double = JavaClass("java.lang.Double")

class Shapes:
""" + "\n".join(f"    {k} = {v}" for k,v in Shapes.__dict__.items() if not k.startswith("__")) + r"""

bridge = Socket("127.0.0.1", """ + str(_port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))

render_instructions = {}

def read_instructions():
    instructions = []
    for _ in range(50):
        if not reader.ready(): return instructions
        else:
            try:
                instructions.append(json.loads(reader.readLine()))
            except SocketException as e:
                if not e.getMessage().startswith("Connection reset"):
                    raise e
    return instructions

def notify_python(data):
    try:
        writer.write(json.dumps(data)+"\n")
        writer.flush()
    except SocketException as e:
        if not e.getMessage().startswith("Connection reset"):
            raise e

def manage_render(GuiGraphics, delta):
    global render_instructions
    try:
        instruction_set = read_instructions()
        for instruction in instruction_set:
            render_instructions[instruction["id"]] = {"name":instruction["name"], "instructions":instruction["instructions"]}
        matrix = False
        for id in render_instructions:
            for i, inst in enumerate(render_instructions[id]["instructions"]):
                if not inst:
                    notify_python({"type":2,"reason":f"Malformed instruction: instruction {i+1} ({i}) on '{render_instructions[id]["name"]}' ({id})","on":id})
                    break
                if inst["type"] == Shapes.RECTANGLE:
                    GuiGraphics.fill(inst["x1"], inst["y1"], inst["x2"], inst["y2"], ARGB.color(*inst["color"]))
                elif inst["type"] == Shapes.TEXT:
                    GuiGraphics.text(mc.font, inst["text"], inst["x"], inst["y"], ARGB.color(*inst["color"]))
                elif inst["type"] == Shapes.CUBOID:
                    if inst["style"]["type"] == "stroke":
                        style = GizmoStyle.stroke(ARGB.color(*inst["style"]["color"]), inst["style"]["width"])
                    elif inst["style"]["type"] == "fill":
                        style = GizmoStyle.fill(ARGB.color(*inst["style"]["color"]))
                    elif inst["style"]["type"] == "strokeAndFill":
                        style = GizmoStyle.strokeAndFill(ARGB.color(*inst["style"]["color"]), inst["style"]["width"], ARGB.color(*inst["style"]["fill"]))
                    else: return notify_python({"type":1,"reason":f"No such gizmo style: {inst["style"]["type"]}"})
                    gizmo = Gizmos.cuboid(AABB(*inst["aabb"]),style)
                    if inst["alwaysontop"]:
                        gizmo.setAlwaysOnTop()
                elif inst["type"] == Shapes.LINE3D:
                    gizmo = Gizmos.line(Vec3(*inst["start"]),Vec3(*inst["end"]),ARGB.color(*inst["color"]),inst["width"])
                    if inst["alwaysontop"]:
                        gizmo.setAlwaysOnTop()
                elif inst["type"] == Shapes.POINT3D:
                    gizmo = Gizmos.point(Vec3(*inst["pos"]),ARGB.color(*inst["color"]),inst["size"])
                    if inst["alwaysontop"]:
                        gizmo.setAlwaysOnTop()
                elif inst["type"] == Shapes.TEXT3D:
                    gizmo = Gizmos.billboardText(inst["text"], Vec3(*inst["pos"]), TextGizmoStyle(ARGB.color(*inst["style"]["color"]), inst["style"]["scale"].floatValue(), OptionalDouble.of(inst["style"]["offset_left"])))
                    if inst["alwaysontop"]:
                        gizmo.setAlwaysOnTop()
                elif inst["type"].startswith("matrix_"):
                    if not matrix:
                        matrix = GuiGraphics.pose()
                        matrix.pushMatrix()
                    if inst["type"] == "matrix_translate": matrix.translate(inst["x"], inst["y"])
                    elif inst["type"] == "matrix_scale": matrix.scale(inst["scale_x"], inst["scale_y"])
                    elif inst["type"] == "matrix_rotate": matrix.rotate(inst["degrees"])
                    elif inst["type"] == "matrix_new":
                        matrix.popMatrix()
                        matrix.pushMatrix()
                    elif inst["type"] == "matrix_transform":
                        matrix.translate(inst["x"], inst["y"])
                        matrix.scale(inst["scale_x"], inst["scale_y"])
                        matrix.rotate(inst["degrees"])
                else:
                    notify_python({"type":2,"reason":f"No such renderable: {inst["type"]}","on":id})
                    break
            if matrix:
                matrix.popMatrix()
                matrix = False
        return notify_python({"type":0,"gui_scale":mc.getWindow().getGuiScale()})
    except Exception as e:
        return notify_python({"type":1,"reason":e.getMessage()})
""" + _render_register + r"""
""")
    except Exception as e: log(e)

Thread(target=__begin__).start()

_conn, _ = _bridge.accept()
_reader = _conn.makefile(mode="r")
_writer = _conn.makefile(mode="w")
_script_loaded = False

def __reader__():
    global _script_loaded
    last_warning = ""
    while True:
        data = json.loads(_read())
        _script_loaded = True
        if data["type"] == 0:
            for renderer in renderers.copy():
                renderer._guiscale = data["gui_scale"]
                renderer._promise.fulfill()
        elif data["type"] == 1:
            sys.stderr.write(data["reason"])
            sys.stderr.flush()
            os._exit(-1)
        elif data["type"] == 2:
            if not data["reason"] == last_warning:
                if not renderers[data["on"]]._supress_warnings:
                    last_warning = data["reason"]
                    print("[Lib Ren-v2] Warning: " + data["reason"],file=sys.stderr)

Thread(target=__reader__,daemon=True).start()

__all__ = [
    "Renderer",
    "ARGB",
    "AABB",
    "GizmoStyle",
    "Vec3D",
    "TextGizmoStyle"
]
