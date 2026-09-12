Works almost if not exactly like the builtin `java.py` (without the `eval_pyjinn_script`), but about 3× faster, and allows you to grab arbitrary objects from pyjinn, and use them in python

Requirements:
- Minescript 5.0 or higher
- `pyjinn_json`: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py

Please report any inconsistencies in the discord: https://discord.com/channels/930220988472389713/1543638360143437845

## Javapy specific functions
### `convert(obj:JavaObject) -> JavaObject`
Converts a Javapy object into a `java.py` (builtin) object

OR

Converts a `java.py` (builtin) object into a Javapy object

Note: Does not create a copy

### `submit_object(obj:JavaObject) -> str`
Submits a Javapy object to a global space. Returns the uuid it was stored under. All processes see the same global space

Note: Does not create a copy

### `request_object(uuid:str) -> JavaObject`
Requests a previously submitted (or manually submitted via pyjinn) object under a uuid. All processes see the same global space

Note: Does not create a copy
