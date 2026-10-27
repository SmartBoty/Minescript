## Table of contents
### Events
- [Modifications to builtin events](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#modifications-to-builtin-events)
- [Incoming chat interceptor](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#incoming-chat-interceptor)
- [Entity totem popped](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#entity-totem-popped)
- [Entity died](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#entity-died)
- [Server particle](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#server-particle)
- [Health change](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#health-change)
- [Food change](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#food-change)
- [Actionbar change](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#actionbar-change)
- [Command interceptor](https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md#command-interceptor)
- [Title change](https://github.com/SmartBoty/Minescript/blob/main/eventlib/DOCS.md#title-change)
### Data Types
- EntityData -> https://minescript.net/docs#entitydata

## Syntax
Use `from eventlib import *` for syntax checking

## Listeners
### Incoming chat interceptor
Intercepts all incoming messages, before they reach other parts of the client. Can be filtered to only intercept messages that start with a specific character
```
listener: register_incoming_chat_interceptor(*,startswith="")
type: EventType.INCOMING_CHAT_INTERCEPT
message: str
json: dict
```

### Entity totem popped
Triggers when a totem of an entity is "popped"
```
listener: register_totem_popped_listener()
type: EventType.ENTITY_TOTEM_POPPED
entity: EntityData
```

### Entity died
Triggers when an entity dies
```
listener: register_entity_died_listener()
type: EventType.ENTITY_DIED
entity: EntityData
```

### Server particle
Triggers when a particle from the server appears
```
listener: register_server_particle_listener()
type: EventType.SERVER_PARTICLE
particle: str
x: float
y: float
z: float
```

### Health change
Triggers when the health of the local player changes
```
listener: register_health_change_listener()
type: EventType.HEALTH_CHANGE
health: float
```

### Food change
Triggers when the hunger or saturation of the local player changes
```
listener: register_food_change_listener()
type: EventType.FOOD_CHANGE
hunger: float
saturation: float
```

### Actionbar change
Triggers when the actionbar changes
```
listener: register_actionbar_change_listener()
type: EventType.ACTIONBAR_CHANGE
message: str
```

### Title change
Triggers when the big title changes
```
listener: register_title_change_listener()
type: EventType.TITLE_CHANGE
title: str
title_json: dict
subtitle: str
subtitle_json: dict
```

### Command interceptor
Intercepts all outgoing commands:
- `/` commands executed manually, or via `execute()`
- any and all commands from `click_event` (in a json formatted chat message)

To execute commands without triggering the interceptor, use `.execute()` on the event, or `execute()` in a `Ignore_Command_Intercept` context manager
```py
listener: register_command_interceptor()
type: EventType.COMMAND_INTERCEPT
command: str
execute: Callable
```

# Modifications to builtin events
### Chat event
- Populate a `json` field with the chat messages raw json, if eventlib is enabled in the registering function, otherwise it uses the builtin protocol
- `register_chat_listener(eventlib=True)`
- Optional, `False` by default

### Key event
- Populate a `pretty_key` field with the pretty name of the GLFW key in CamelCase (ie.: `A`, `B`, `Left Control` etc...), if eventlib is enabled in the registering function, otherwise it uses the builtin protocol
- `register_key_listener(eventlib=True)`
- Optional, `False` by default

### Outgoing chat intercept event
- Allows capturing of messages sent via `chat()`, and automatically appends manually sent messages to the command history, if eventlib is enabled in the registering function, otherwise it uses the builtin protocol
- `register_outgoing_chat_interceptor(eventlib=True)`
- Optional, `False` by default
