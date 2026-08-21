Eventlib is a library aiming to add new events, while keeping minescripts `EventQueue`. It is a drag n' drop library, meaning you just import it, and you already have everything set up. The syntax is practically identical to what minescript uses.

Supports 1.21.8 to 26.2. Requires 5.0b11 or higher, and mappings (`\install_mappings`) for versions below 26.x

As of now, it contains: 
- `INCOMING_CHAT_INTERCEPT`
- `ENTITY_TOTEM_POPPED`
- `ENTITY_DIED`
- `SERVER_PARTICLE`
- `CLIENT_TICK`
- `HEALTH_CHANGE`
- `FOOD_CHANGE`
- `ACTIONBAR_CHANGE`
- `COMMAND_INTERCEPT`

And also updated:
- `ChatEvent` -> Optionally populate `.json`
- `KeyEvent` -> Optionally populate `.pretty_key`
- `OutgoingChatInterceptEvent` -> Optionally also capture messages sent by `chat()`, and automatically appends the message to the command history

And i would like to ask you (🫵) for events you would like to see

Docs: https://github.com/SmaertBoty/Minescript/blob/main/eventlib/DOCS.md

Feedback appreciated!: [Eventlib on Discord](https://discord.com/channels/930220988472389713/1511099314468950218)
Download redirect: [eventlib.py](https://smartboty.github.io/Minescript/?file=eventlib.py)

Example usage:
```py
from system.lib.minescript import EventType, EventQueue, echo, execute
from eventlib import * # Put it anywhere before instancing event queue ("EventQueue()")

events = EventQueue()
events.register_incoming_chat_interceptor(startswith="+")
events.register_totem_popped_listener()
events.register_entity_died_listener()
events.register_server_particle_listener()
events.register_client_tick_listener()
events.register_health_change_listener()
events.register_food_change_listener()
events.register_actionbar_change_listener()
events.register_command_interceptor()

events.register_chat_listener(eventlib=True) # Enables the .json value on the event
events.register_key_listener(eventlib=True) # Enables the .pretty_key value on the event
events.register_outgoing_chat_interceptor(eventlib=True) # Also captures messages sent via 'chat()'

while True:
    event = events.get()
    if event.type == EventType.INCOMING_CHAT_INTERCEPT:
        echo(f";Recieved: {event.message}")
        echo(f";Raw json: {event.json}")
    if event.type == EventType.ENTITY_TOTEM_POPPED:
        echo(";Totem popped for: " + event.entity.name)
    if event.type == EventType.ENTITY_DIED:
        echo(f";{event.entity.name} died!")
    if event.type == EventType.SERVER_PARTICLE:
        echo(f";Particle {event.particle} appeared at {event.x}, {event.y}, {event.z}")
    if event.type == EventType.CLIENT_TICK:
        echo(f";TICK! Current tick: {event.tick}")
    if event.type == EventType.HEALTH_CHANGE:
        echo(f";Health changed! Now at: {event.health}")
    if event.type == EventType.FOOD_CHANGE:
        echo(f";Food level changed! Hunger: {event.hunger}, Saturation: {event.saturation}")
    if event.type == EventType.ACTIONBAR_CHANGE:
        echo(f";Actionbar changed to: {event.message}")
    if event.type == EventType.CHAT:
        if not event.message.startswith(";"):
            echo(f";Message: {event.message}")
            echo(f";Raw json: {event.json}")
    if event.type == EventType.KEY:
        echo(f";Key code: {event.key} ({event.pretty_key})")
    if event.type == EventType.COMMAND_INTERCEPT:
        echo(f";Command: {event.command}")
        event.execute()
        with Ignore_Command_Intercept:
            execute("/say This was not intercepted!")
    if event.type == EventType.OUTGOING_CHAT_INTERCEPT:
        echo(f";Intercepted: {event.message}")
```
