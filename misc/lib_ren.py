from __future__ import annotations
from system.lib.minescript import version_info, log as _log, echo
import sys

debug = False
verinf = version_info()

_mc_major_version,*_mc_minor_version = verinf.minecraft.split(".")
_minescript_version_index = verinf.minescript.split(".")
_is_fabric = "fabric" in verinf.mod_loader.lower()

def log(msg):
    if debug: echo(f"[Lib Ren-v2] {msg}")
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

_original_json_default_method = json.JSONEncoder.default
def _new_json_default_method(self, obj):
    method = getattr(obj, "__json__", None)
    if callable(method): return method()
    return _original_json_default_method(self, obj)
json.JSONEncoder.default = _new_json_default_method

renderers:list[Renderer] = []

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

class GuiGraphics:
    def __init__(self, parent:Renderer):
        self.renderer = parent

    def fill(self, x1:int, y1:int, x2:int, y2:int, color:tuple[int]):
        self.renderer._handle_instruction({"type":Shapes.RECTANGLE,"x1":round(x1),"y1":round(y1),"x2":round(x2),"y2":round(y2),"color":color})

    def text(self, text:str, x:int, y:int, color:tuple[int]):
        self.renderer._handle_instruction({"type":Shapes.TEXT,"text":text,"x":round(x),"y":round(y),"color":color})

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

    def setAlwaysOnTop(self):
        self.alwaysontop = True

class Gizmos:
    def __init__(self, parent:Renderer):
        self.renderer = parent

    def cuboid(self, bounding_box:AABB, style:GizmoStlye) -> Gizmo:
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

class Renderer:
    def __init__(self) -> Renderer:
        self._instructions = []
        self._promise = Promise()
        self.guigraphics = GuiGraphics(self)
        self.gizmos = Gizmos(self)
        self.id = str(len(renderers))
        self._guiscale = 4
        renderers.append(self)

    def __enter__(self) -> tuple[GuiGraphics,Gizmos]:
        self.await_frame()
        return (self.guigraphics,self.gizmos)

    def __exit__(self, exc_type, exc, tb):
        self.push_stack()

    def _handle_instruction(self, instruction:dict):
        self._instructions.append(instruction)

    def push_stack(self):
        instructions = self._instructions.copy()
        self._instructions.clear()
        _write(json.dumps({"id":self.id, "instructions":instructions}))

    def await_frame(self):
        self._promise.get()

    def gui_scale(self):
        return self._guiscale

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
            try: instructions.append(json.loads(reader.readLine()))
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
            render_instructions[instruction["id"]] = instruction["instructions"]
        for id in render_instructions:
            for inst in render_instructions[id]:
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
                else:
                    return notify_python({"type":1,"reason":f"No such renderable: {inst["type"]}"})
        return notify_python({"type":0,"gui_scale":mc.getWindow().getGuiScale()})
    except Exception as e:
        raise e
        return notify_python({"type":1,"reason":str(e)})
""" + _render_register + r"""
""")

_conn, _ = _bridge.accept()
_reader = _conn.makefile(mode="r")
_writer = _conn.makefile(mode="w")

responded = False

def __reader__():
    global responded
    while True:
        data = json.loads(_read())
        responded = True
        if data["type"] == 0:
            for renderer in renderers:
                renderer._promise.fulfill()
                renderer._guiscale = data["gui_scale"]
        elif data["type"] == 1:
            sys.stderr.write(data["reason"])
            os._exit(-1)

Thread(target=__reader__,daemon=True).start()

__all__ = [
    "Renderer",
    "ARGB",
    "AABB",
    "GizmoStyle",
    "Vec3D",
    "TextGizmoStyle"
]