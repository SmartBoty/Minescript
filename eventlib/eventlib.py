import system.lib.minescript as m
import sys
if int("".join([n for n in m.version_info().minescript if n.isdigit()])) < 5011: sys.exit("[Eventlib] Please update to 5.0b11!")

version = int("".join([n for n in m.version_info().minecraft if n.isdigit()]))
if not str(version).startswith("1"): version = int("99"+str(version))

version_mappings = {
    "keyevent_const": {
        (0,12108) : ("event.key,event.scan_code",""),
        (12109,999999): ("KeyEvent(event.key,event.scan_code,event.modifiers)","""KeyEvent = JavaClass("net.minecraft.client.input.KeyEvent")""")
    },
    "hud_const": {
        (0,99261) : "mc.gui",
        (99262,999999): "mc.gui.hud"
    }
}

keyevent_mapping = [v for k,v in version_mappings["keyevent_const"].items() if k[0] <= version <= k[1]][0]
hud_mapping = [v for k,v in version_mappings["hud_const"].items() if k[0] <= version <= k[1]][0]

#from system.lib.minescript import *
from threading import Thread
from system.lib.java import eval_pyjinn_script as eps
import socket
import json
import uuid
from queue import Queue as qQ
from typing import TYPE_CHECKING
from dataclasses import dataclass
from time import time

try: identifier = str(uuid.uuid8())
except: identifier = str(uuid.uuid1())

bridge = socket.socket()
bridge.bind(("127.0.0.1", 0))
bridge.listen(1)
port = bridge.getsockname()[1]

def __serve_listener__():
    while True:
        line = file.readline()
        if not line: continue
        try:
            event = json.loads(line)
            if event["event"] == "intercept_incoming_chat":
                queues = registered_incoming_intercept.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.INCOMING_CHAT_INTERCEPT,
                        "message": event["text"],
                        "json": event["json"]
                    })
            elif event["event"] == "entity_totem_popped":
                queues = registered_totem_popped.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.ENTITY_TOTEM_POPPED,
                        "entity": [e for e in m.entities() if e.uuid == event["uuid"]][0]
                    })
            elif event["event"] == "entity_died":
                queues = registered_entity_died.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.ENTITY_DIED,
                        "entity": [e for e in m.entities() if e.uuid == event["uuid"]][0]
                    })
            elif event["event"] == "server_particle":
                queues = registered_particle.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.SERVER_PARTICLE,
                        "particle": event["particle"],
                        "position": (float(event["x"]),float(event["y"]),float(event["z"]))
                    })
            elif event["event"] == "client_tick":
                queues = registered_client_tick.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.CLIENT_TICK,
                        "tick": int(event["tick"])
                    })
            elif event["event"] == "health_change":
                queues = registered_client_tick.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.HEALTH_CHANGE,
                        "health": float(event["health"])
                    })
            elif event["event"] == "food_change":
                queues = registered_food_change.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.FOOD_CHANGE,
                        "hunger": float(event["food"]),
                        "saturation": float(event["saturation"])
                    })
            elif event["event"] == "actionbar_change":
                queues = registered_actionbar_change.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.ACTIONBAR_CHANGE,
                        "message": event["message"]
                    })
            elif event["event"] == "chat_event":
                queues = registered_chat.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.CHAT,
                        "message": event["text"],
                        "json": event["json"],
                        "time": time()
                    })
            elif event["event"] == "key_event":
                queues = registered_key.copy()
                for queue in queues:
                    queue.put({
                        "type":m.EventType.KEY,
                        "time": time(),
                        "key": int(event["key"]),
                        "pretty_key": event["pretty_key"],
                        "scan_code": int(event["scan_code"]),
                        "action": int(event["action"]),
                        "modifiers": int(event["modifiers"]),
                        "screen": event["screen"]
                    })
            elif event["event"] == "command_intercept":
                queues = registered_command_intercept.copy()
                for queue in queues:
                    queue.put({
                        "type": m.EventType.COMMAND_INTERCEPT,
                        "command": event["command"],
                        "execute": lambda: m.execute(fr"""\eval '__script__.vars["game"]["eventlib"]["{identifier}"]["command_intercept"]["block"] = False' 'execute("{event["command"]}")'""")
                    })
            elif event["event"] == "outgoing_chat":
                queues = registered_outgoing_intercept.copy()
                for queue in queues:
                    queue.put({
                        "type" :m.EventType.OUTGOING_CHAT_INTERCEPT,
                        "time": time(),
                        "message": event["text"]
                    })
            else:
                m.log(f"[EventLib] Event unnaccounted for: {event["event"]} ({event})")
            queues = []
        except: m.log(f"[EventLib] Malformed json event: '{line[:-1]}'")

script = eps(
r"""
mc = JavaClass("net.minecraft.client.Minecraft").getInstance()
ClientboundPlayerChatPacket = JavaClass("net.minecraft.network.protocol.game.ClientboundPlayerChatPacket")
ClientboundSystemChatPacket = JavaClass("net.minecraft.network.protocol.game.ClientboundSystemChatPacket")
ClientboundEntityEventPacket = JavaClass("net.minecraft.network.protocol.game.ClientboundEntityEventPacket")
ClientboundLevelParticlesPacket = JavaClass("net.minecraft.network.protocol.game.ClientboundLevelParticlesPacket")
BuiltInRegistries = JavaClass("net.minecraft.core.registries.BuiltInRegistries")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
Socket = JavaClass("java.net.Socket")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
mappings = JavaClass("net.minescript.common.Minescript").mappingsLoader.get()
ComponentSerialization = JavaClass("net.minecraft.network.chat.ComponentSerialization")
GsonBuilder = JavaClass("com.google.gson.GsonBuilder")
JsonOps = JavaClass("com.mojang.serialization.JsonOps")
RegistryOps = JavaClass("net.minecraft.resources.RegistryOps")
InputConstants = JavaClass("com.mojang.blaze3d.platform.InputConstants")
""" + keyevent_mapping[1] + r"""
ServerboundChatCommandPacket = JavaClass("net.minecraft.network.protocol.game.ServerboundChatCommandPacket")
ServerboundChatCommandSignedPacket = JavaClass("net.minecraft.network.protocol.game.ServerboundChatCommandSignedPacket")
Pattern = JavaClass("java.util.regex.Pattern")
ServerboundChatPacket = JavaClass("net.minecraft.network.protocol.game.ServerboundChatPacket")

def reflect_field(_class, field_name, raw=False):
    clss = _class.getClass()
    f = mappings.getRuntimeFieldName(clss, field_name)
    field = clss.getDeclaredField(f)
    field.setAccessible(True)
    if not raw: return field.get(_class)
    else: return field

def reverse(lst):
    out = [None for _ in range(len(lst))]
    i = len(lst)-1
    if i > 0:
        for item in lst:
            out[i] = item
            i -= 1
    else: return lst
    return out

def sanitize_string(s):
    return s.replace('"','\\"')

identifier = '""" + identifier + r"""'
if "eventlib" not in __script__.vars["game"]:
    __script__.vars["game"]["eventlib"] = {}
__script__.vars["game"]["eventlib"][identifier] = {"intercept_incoming_chat":{"state":False,"startswith":""},"entity_totem_popped":False,"entity_died":False,"server_particle":False,"client_tick":False,"health_change":False,"food_change":False,"actionbar_change":False,"chat_listener":False,"key_listener":False,"command_intercept":{"block":True,"state":False},"outgoing_chat":{"state":False,"filter":0,"startswith":"","pattern":""}}
bridge = Socket("127.0.0.1", """ + str(port) + r""")
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
hp = player_health()
food = [mc.player.getFoodData().getFoodLevel(),mc.player.getFoodData().getSaturationLevel()]
ab_timestamp_predicted = reflect_field(""" + hud_mapping + r""","overlayMessageTime")
chatlength = len(list(reflect_field(""" + hud_mapping + r""".getChat(), "allMessages")))

def add_event(event):
    writer.write(event.replace("\n",r"\n") + "\n")
    writer.flush()

def s2c(event):
    if __script__.vars["game"]["eventlib"][identifier]["intercept_incoming_chat"]["state"]:# or __script__.vars["game"]["eventlib"][identifier]["chat_listener"]:
        if isinstance(event.packet, ClientboundSystemChatPacket):
            if event.packet.overlay(): return
            comp = event.packet.content()
            dat = event.packet.content().getString()
            json_string = GsonBuilder().create().toJson(ComponentSerialization.CODEC.encodeStart(RegistryOps.create(JsonOps.INSTANCE, mc.level.registryAccess()),comp).getOrThrow())
        elif isinstance(event.packet, ClientboundPlayerChatPacket):
            dat = event.packet.body().content()
            comp = event.packet.body()
            json_string = '{"text":"' + sanitize_string(dat) + '"}'
        else: return
        if dat.startswith(__script__.vars["game"]["eventlib"][identifier]["intercept_incoming_chat"]["startswith"]):
            add_event('{"event":"intercept_incoming_chat","text":"' + sanitize_string(dat) + '","json":' + json_string + '}')
            event.cancel()
            field = reflect_field(mc.player.connection,"nextChatIndex",True)
            field.setInt(mc.player.connection, field.get(mc.player.connection)+1)
        #elif __script__.vars["game"]["eventlib"][identifier]["chat_listener"]:
        #    add_event('{"event":"chat_event","text":"' + dat + '","json":' + json_string + '}')

    if isinstance(event.packet, ClientboundEntityEventPacket):
        if __script__.vars["game"]["eventlib"][identifier]["entity_totem_popped"]:
            if int(event.packet.getEventId()) == 35:
                add_event('{"event":"entity_totem_popped","uuid":"' + event.packet.getEntity(mc.level).getStringUUID() + '"}')
        if __script__.vars["game"]["eventlib"][identifier]["entity_died"]:
            if int(event.packet.getEventId()) == 3:
                add_event('{"event":"entity_died","uuid":"' + event.packet.getEntity(mc.level).getStringUUID() + '"}')
    
    if __script__.vars["game"]["eventlib"][identifier]["server_particle"]:
        if isinstance(event.packet, ClientboundLevelParticlesPacket): 
            add_event('{"event":"server_particle","particle":"' + BuiltInRegistries.PARTICLE_TYPE.getKey(event.packet.getParticle().getType()).toString() + '","x":str(event.packet.getX()),"y":str(event.packet.getY()),"z":str(event.packet.getZ())}')

def c2s(event):
    if __script__.vars["game"]["eventlib"][identifier]["command_intercept"]["state"]:
        if isinstance(event.packet, ServerboundChatCommandPacket) or isinstance(event.packet, ServerboundChatCommandSignedPacket):
            if __script__.vars["game"]["eventlib"][identifier]["command_intercept"]["block"]:
                add_event('{"event":"command_intercept","command":"' + sanitize_string(event.packet.command()) + '"}')
                event.cancel()
            else: __script__.vars["game"]["eventlib"][identifier]["command_intercept"]["block"] = True
    if __script__.vars["game"]["eventlib"][identifier]["outgoing_chat"]["state"]:
        if isinstance(event.packet, ServerboundChatPacket):
            if __script__.vars["game"]["eventlib"][identifier]["outgoing_chat"]["filter"] == 0:
                if event.packet.message().startswith(__script__.vars["game"]["eventlib"][identifier]["outgoing_chat"]["startswith"]):
                    event.cancel()
                    add_event('{"event":"outgoing_chat","text":"' + sanitize_string(event.packet.message()) + '","match":null}')
            elif __script__.vars["game"]["eventlib"][identifier]["outgoing_chat"]["filter"] == 1:
                matcher = Pattern.compile(__script__.vars["game"]["eventlib"][identifier]["outgoing_chat"]["pattern"]).matcher(event.packet.message())
                if matcher.lookingAt():
                    event.cancel()
                    match = [sanitize_string(matcher.group(i)) for i in range(matcher.groupCount())]
                    add_event('{"event":"outgoing_chat","text":"' + sanitize_string(event.packet.message()) + '","match":' + str(match) + '}')

def key_event(event):
    if __script__.vars["game"]["eventlib"][identifier]["key_listener"]:
        pretty_key = InputConstants.getKey(""" + keyevent_mapping[0] + r""").getDisplayName().getString()
        add_event('{"event":"key_event","key":' + str(event.key) + ',"pretty_key":"' + str(pretty_key) + '","scan_code":' + str(event.scan_code) + ',"action":' + str(event.action) + ',"modifiers":' + str(event.modifiers) + ',"screen":"' + str(event.screen) + '"}')

def tick(event):
    global hp, food, ab_timestamp_predicted
    if __script__.vars["game"]["eventlib"][identifier]["client_tick"]:
        add_event('{"event":"client_tick","tick":' + str(world_info().game_ticks) + '}')
    if __script__.vars["game"]["eventlib"][identifier]["health_change"]:
        if hp != player_health():
            add_event('{"event":"health_change","health":' + str(player_health()) + '}')
            hp = player_health()
    if __script__.vars["game"]["eventlib"][identifier]["food_change"]:
        new_food = [mc.player.getFoodData().getFoodLevel(),mc.player.getFoodData().getSaturationLevel()]
        if food != new_food:
            add_event('{"event":"food_change","food":' + str(new_food[0]) + ',"saturation":' + str(new_food[1]) + '}')
            food = new_food
    if __script__.vars["game"]["eventlib"][identifier]["actionbar_change"]:
        try: nab = reflect_field(""" + hud_mapping + r""","overlayMessageString").getString()
        except: nab = None
        time = reflect_field(""" + hud_mapping + r""","overlayMessageTime")
        if time != ab_timestamp_predicted-1 and time > 0:
            add_event('{"event":"actionbar_change","message":"' + sanitize_string(nab) + '"}')
        ab_timestamp_predicted = time

def frame(_):
    global chatlength
    msgs = list(reflect_field(""" + hud_mapping + r""".getChat(), "allMessages"))
    new = []
    if len(msgs) > chatlength:
        for i in range(len(msgs)- chatlength):
            new.append(msgs[i].content())
        chatlength = len(msgs)
        if __script__.vars["game"]["eventlib"][identifier]["chat_listener"]:
            for comp in reverse(new):
                dat = comp.getString()
                json_string = GsonBuilder().create().toJson(ComponentSerialization.CODEC.encodeStart(RegistryOps.create(JsonOps.INSTANCE, mc.level.registryAccess()),comp).getOrThrow())
                add_event('{"event":"chat_event","text":"' + sanitize_string(dat) + '","json":' + json_string + '}')
    elif len(msgs) < chatlength-1: chatlength = len(msgs)

add_event_listener("tick",tick)
add_event_listener("clientbound_packet",s2c)
add_event_listener("key",key_event)
add_event_listener("serverbound_packet",c2s)
add_event_listener("render",frame)
""")
conn, _ = bridge.accept()
file = conn.makefile(encoding="utf-8")

registered_incoming_intercept = []
registered_totem_popped = []
registered_entity_died = []
registered_particle = []
registered_client_tick = []
registered_health_change = []
registered_food_change = []
registered_actionbar_change = []
registered_chat = []
registered_key = []
registered_command_intercept = []
registered_outgoing_intercept = []

Thread(target=__serve_listener__,daemon=True).start()

@dataclass
class INCOMING_CHAT_INTERCEPT:
    type:str
    message:str
    json:dict

@dataclass
class ENTITY_TOTEM_POPPED:
    type:str
    entity:m.EntityData

@dataclass
class ENTITY_DIED:
    type:str
    entity:m.EntityData

@dataclass
class SERVER_PARTICLE:
    type:str
    particle:str
    position:tuple[float,float,float]

@dataclass
class CLIENT_TICK:
    type:str
    tick:int

@dataclass
class HEALTH_CHANGE:
    type:str
    health:float

@dataclass
class FOOD_CHANGE:
    type:str
    hunger:float
    saturation:float

@dataclass
class ACTIONBAR_CHANGE:
    type:str
    message:str

@dataclass
class EventlibChatEvent(m.ChatEvent):
    type:str
    time:float
    message:str
    json:dict=None

@dataclass
class EventlibKeyEvent(m.KeyEvent):
    type: str
    time: float
    key: int
    pretty_key: str = None
    scan_code: int
    action: int
    modifiers: int
    screen: str

@dataclass
class COMMAND_INTERCEPT:
    type:str
    command:str
    execute:m.Callable

def _execute(command: str):
    current_executor(command)

execute = _execute
m.execute = _execute

def __original_execute__(command: str):
    if not isinstance(command, str):
      raise TypeError("Argument must be a string.")
    return (command,)
__original_execute__ = m.NoReturnScriptFunction("execute", __original_execute__)

def eventlib_execute(command:str):
    if not isinstance(command, str): raise TypeError("Argument must be a string.")
    __original_execute__(fr"""\eval '__script__.vars["game"]["eventlib"]["{identifier}"]["command_intercept"]["block"] = False' 'execute("{command}")'""")

current_executor = __original_execute__

class ICI:
    def __enter__(*_):
        global current_executor
        current_executor = eventlib_execute
    
    def __exit__(*_):
        global current_executor
        current_executor = __original_execute__

Ignore_Command_Intercept = ICI()

@dataclass
class EventlibOutgoingChatIntercept:
    type:str
    time:float
    message:str

m.EventType.INCOMING_CHAT_INTERCEPT = "incoming_chat_intercept"
m._EVENT_CONSTRUCTORS["incoming_chat_intercept"] = INCOMING_CHAT_INTERCEPT

m.EventType.ENTITY_TOTEM_POPPED = "entity_totem_popped"
m._EVENT_CONSTRUCTORS["entity_totem_popped"] = ENTITY_TOTEM_POPPED

m.EventType.ENTITY_DIED = "entity_died"
m._EVENT_CONSTRUCTORS["entity_died"] = ENTITY_DIED

m.EventType.SERVER_PARTICLE = "server_particle"
m._EVENT_CONSTRUCTORS["server_particle"] = SERVER_PARTICLE

m.EventType.CLIENT_TICK = "client_tick"
m._EVENT_CONSTRUCTORS["client_tick"] = CLIENT_TICK

m.EventType.HEALTH_CHANGE = "health_change"
m._EVENT_CONSTRUCTORS["health_change"] = HEALTH_CHANGE

m.EventType.FOOD_CHANGE = "food_change"
m._EVENT_CONSTRUCTORS["food_change"] = FOOD_CHANGE

m.EventType.ACTIONBAR_CHANGE = "actionbar_change"
m._EVENT_CONSTRUCTORS["actionbar_change"] = ACTIONBAR_CHANGE

m.EventType.COMMAND_INTERCEPT = "command_intercept"
m._EVENT_CONSTRUCTORS["command_intercept"] = COMMAND_INTERCEPT

def register_incoming_chat_interceptor(self,*,startswith:str=""):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["intercept_incoming_chat"] = {"{"}"state":True,"startswith":"{startswith}"{"}"}'""")
    self.eventlib_listeners.append("intercept_incoming_chat")
    registered_incoming_intercept.append(self.queue)

def register_totem_popped_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["entity_totem_popped"] = True'""")
    self.eventlib_listeners.append("entity_totem_popped")
    registered_totem_popped.append(self.queue)

def register_entity_died_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["entity_died"] = True'""")
    self.eventlib_listeners.append("entity_died")
    registered_entity_died.append(self.queue)

def register_server_particle_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["server_particle"] = True'""")
    self.eventlib_listeners.append("server_particle")
    registered_particle.append(self.queue)

def register_client_tick_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["client_tick"] = True'""")
    self.eventlib_listeners.append("client_tick")
    registered_client_tick.append(self.queue)

def register_health_change_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["health_change"] = True'""")
    self.eventlib_listeners.append("health_change")
    registered_health_change.append(self.queue)

def register_food_change_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["food_change"] = True'""")
    self.eventlib_listeners.append("food_change")
    registered_food_change.append(self.queue)

def register_actionbar_change_listener(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["actionbar_change"] = True'""")
    self.eventlib_listeners.append("actionbar_change")
    registered_actionbar_change.append(self.queue)

def eventlib_register_chat_listener(self,*,eventlib=False):
    if eventlib:
        execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["chat_listener"] = True'""")
        self.eventlib_listeners.append("chat_listener")
        registered_chat.append(self.queue)
    else: self._register(m.EventType.CHAT, m._register_chat_message_listener)

def eventlib_register_key_listener(self,*,eventlib=False):
    if eventlib:
        execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["key_listener"] = True'""")
        self.eventlib_listeners.append("key_listener")
        registered_key.append(self.queue)
    else: self._register(m.EventType.KEY, m._register_key_listener)

def register_command_interceptor(self):
    execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["command_intercept"]["state"] = True'""")
    self.eventlib_listeners.append("command_intercept")
    registered_command_intercept.append(self.queue)

def eventlib_register_outgoing_chat_interceptor(self, *, prefix: str = None, pattern: str = None, eventlib=False):
    if eventlib:
        if prefix: execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["outgoing_chat"] = {"{"}"state":True,"startswith":"{prefix}","pattern":"","filter":0{"}"}'""")
        elif pattern: execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["outgoing_chat"] = {"{"}"state":True,"startswith":"","pattern":"{pattern}","filter":1{"}"}'""")
        else: execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["outgoing_chat"] = {"{"}"state":True,"startswith":"","pattern":"","filter":0{"}"}'""")
        self.eventlib_listeners.append("outgoing_chat")
        registered_outgoing_intercept.append(self.queue)
    else:
        self._register(
            EventType.OUTGOING_CHAT_INTERCEPT,
            lambda handler, exception_handler: \
                m._register_chat_message_interceptor(
                    handler, exception_handler, prefix=prefix, pattern=pattern))

def unregister_all(self):
    for event in self.eventlib_listeners:
        if event == "intercept_incoming_chat": execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["intercept_incoming_chat"]["state"] = False'""")
        elif event == "command_intercept": execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["command_intercept"]["state"] = False'""")
        elif event == "outgoing_chat": execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["outgoing_chat"]["state"] = False'""")
        else: execute(fr"""\eval '0' '__script__.vars["game"]["eventlib"]["{identifier}"]["{event}"] = False'""")
    self.eventlib_listeners = []
    listener_ids = self.event_listener_ids
    self.event_listener_ids = []
    for listener_id in listener_ids:
      m._unregister_event_handler(listener_id)

m.EventQueue.register_incoming_chat_interceptor = register_incoming_chat_interceptor
m.EventQueue.register_totem_popped_listener = register_totem_popped_listener
m.EventQueue.register_entity_died_listener = register_entity_died_listener
m.EventQueue.register_server_particle_listener = register_server_particle_listener
m.EventQueue.register_client_tick_listener = register_client_tick_listener
m.EventQueue.register_health_change_listener = register_health_change_listener
m.EventQueue.register_food_change_listener = register_food_change_listener
m.EventQueue.register_actionbar_change_listener = register_actionbar_change_listener
m.EventQueue.register_chat_listener = eventlib_register_chat_listener
m.EventQueue.register_key_listener = eventlib_register_key_listener
m.EventQueue.register_command_interceptor = register_command_interceptor
m.EventQueue.register_outgoing_chat_interceptor = eventlib_register_outgoing_chat_interceptor
m._EVENT_CONSTRUCTORS["chat"] = EventlibChatEvent
m._EVENT_CONSTRUCTORS["key"] = EventlibKeyEvent
m._EVENT_CONSTRUCTORS["outgoing_chat_intercept"] = EventlibOutgoingChatIntercept

m.EventQueue.unregister_all = unregister_all
m.EventQueue.eventlib_listeners = []

if TYPE_CHECKING:
    class EventQueue(m.EventQueue(),m.EventQueue):
        """Queue for managing events.

          Implements context management so that it can be used with a `with` expression
          to automatically unregister event listeners at the end of the block, e.g.
        
          ```
          with EventQueue() as event_queue:
            event_queue.register_chat_listener()
            while True:
              event = event_queue.get()
              if event.type == EventType.CHAT and "knock knock" in event.message.lower():
                echo("Who's there?")
          ```
        
          Compatibility: Python only. (See `add_event_listener` and `EventLoop` for Pyjinn event handling.)
        
          Since: v4.0

          Extended by Eventlib to include extra events
          """
        eventlib_listeners = []
        def register_incoming_chat_interceptor(self,*,startswith:str=""): ...
        def register_totem_popped_listener(self): ...
        def register_entity_died_listener(self): ...
        def register_server_particle_listener(self): ...
        def register_client_tick_listener(self): ...
        def register_health_change_listener(self): ...
        def register_food_change_listener(self): ...
        def register_actionbar_change_listener(self): ...
        def get(self, block: bool = True, timeout: float = None) -> Event|None:
            """Gets the next event in the queue.

            Args:
              block: if `True`, block until an event fires
              timeout: timeout in seconds to wait for an event if `block` is `True`
        
            Returns:
              subclass-dependent event
        
            Raises:
              `queue.Empty` if `block` is `True` and `timeout` expires, or `block` is `False` and
              queue is empty.
            """
        def register_chat_listener(self,*,eventlib:bool=False):
            """Registers listener for `EventType.CHAT` events as `ChatEvent`.
        
            Example:
            ```
              with EventQueue() as event_queue:
                event_queue.register_chat_listener()
                while True:
                  event = event_queue.get()
                  if event.type == EventType.CHAT:
                    if not event.message.startswith("> "):
                      echo(f"> Got chat message: {event.message}")
            ```
            If `eventlib` is `True`, extra data will be attached
            """
        def register_key_listener(self,*,eventlib:bool=False):
            """Registers listener for `EventType.KEY` events as `KeyEvent`.
            Example:
            ```
              with EventQueue() as event_queue:
                event_queue.register_key_listener()
                while True:
                  event = event_queue.get()
                  if event.type == EventType.KEY:
                    if event.action == 0:
                      action = 'up'
                    elif event.action == 1:
                      action = 'down'
                    else:
                      action = 'repeat'
                    echo(f"Got key {action} with code {event.key}")
            ```
            If `eventlib` is `True`, extra data will be attached
            """
        def register_command_interceptor(self): ...
        def register_outgoing_chat_interceptor(self, *, prefix: str = None, pattern: str = None,eventlib:bool=False):
          """Registers listener for `EventType.OUTGOING_CHAT_INTERCEPT` events as `ChatEvent`.
          Intercepts outgoing chat messages from the local player. Interception can be restricted to
          messages matching `prefix` or `pattern`. Intercepted messages can be chatted with `chat()`.
          `prefix` or `pattern` can be specified, but not both. If neither `prefix` nor
          `pattern` is specified, all outgoing chat messages are intercepted.
          Args:
            prefix: if specified, intercept only the messages starting with this literal prefix
            pattern: if specified, intercept only the messages matching this regular expression
          Example:
          ```
            with EventQueue() as event_queue:
              event_queue.register_outgoing_chat_interceptor(pattern=".*%p.*")
              while True:
                event = event_queue.get()
                if event.type == EventType.OUTGOING_CHAT_INTERCEPT:
                  # Replace "%p" in outgoing chats with your current position.
                  chat(event.message.replace("%p", str(player().position)))
          ```
          If `eventlib` is `True`, also intercepts messages sent via `chat()`
          """
        def unregister_all(): ...
    def execute(command: str):
          """Executes the given command.
        
          If `command` is prefixed by a backslash, it's treated as Minescript command,
          otherwise it's treated as a Minecraft command (the slash prefix is optional).
        
          *Note: This was named `exec` in Minescript 2.0. The old name is no longer
          available in v3.0.*
        
          Since: v2.1
          
          Extended by Eventlib to allow usage with `Ignore_Command_Intercept` context manager
          """
    class EventType(m._EventType):
        INCOMING_CHAT_INTERCEPT:str = "incoming_chat_intercept"
        ENTITY_TOTEM_POPPED:str = "entity_totem_popped"
        ENTITY_DIED:str = "entity_died"
        SERVER_PARTICLE:str = "server_particle"
        CLIENT_TICK:str = "client_tick"
        HEALTH_CHANGE:str = "health_change"
        FOOD_CHANGE:str = "food_change"
        ACTIONBAR_CHANGE:str = "actionbar_change"
        COMMAND_INTERCEPT:str = "command_intercept"
    class Event:
        type:str
        time:float
        message:str
        entity:m.EntityData
        position:m.BlockPos|m.Vector3f
        old_state:str
        new_state:str
        player_uuid:str
        item:m.ItemStack
        amount:int
        entity_uuid:str
        cause_uuid:str
        source:str
        blockpack_base64:str
        loaded:bool
        x_min:int
        z_min:int
        x_max:int
        z_max:int
        connected:bool
        json:dict
        key:int
        pretty_key:str
        execute:m.Callable
        """
        Executes the command, without intercepting it
        """
        command:str
    __all__ = [
        "EventQueue",
        "EventType",
        "Event",
        "Ignore_Command_Intercept",
        "execute",
        "identifier"
    ]
else:
    __all__ = [
        "Ignore_Command_Intercept",
        "execute",
        "identifier"
    ]