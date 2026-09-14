Works almost if not exactly like the builtin `java.py` (without the `eval_pyjinn_script`), but about 3× faster, and allows you to grab arbitrary objects from pyjinn, and use them in python

Requirements:
- Minescript 5.0 or higher
- `pyjinn_json`: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py

Please report any inconsistencies in the discord: https://discord.com/channels/930220988472389713/1543638360143437845

Supports:
- ~3× faster execution compared to `java.py` (builtin)
- `type()`* class grabbing (Equivalend of `Object.class` in java)
- `isinstance` checks
- `len` check
- Converting `java.py` (builtin) objects to `javapy` objects and back
- Automatic GC (garbage collection)

## Javapy specific functions
### `convert(obj:JavaObject) -> JavaObject`
Converts a Javapy object into a `java.py` (builtin) object

OR

Converts a `java.py` (builtin) object into a Javapy object

Note: Does not create a copy of the java side object

### `submit_object(obj:JavaObject) -> str`
Submits a Javapy object to a global space. Returns the uuid it was stored under. All processes see the same global space

Note: Does not create a copy of the java side object

### `request_object(uuid:str) -> JavaObject`
Requests a previously submitted (or manually submitted via pyjinn) object under a uuid. All processes see the same global space

Note: Does not create a copy of the java side object

### `type(obj)`
Import it to replace the already existing `type()` function. It behaves exactly how it does in pyjinn, returning the java side class of the object. Works exactly like the builtin for any other object

# Example usages:

Visual showcase of the difference in speed (compared to the builtin library):
```py
from system.lib.minescript import echo
from time import perf_counter, sleep

echo("Builtin library:")
sleep(2)
start = perf_counter()
from system.lib.java import JavaClass
random = JavaClass("java.util.Random")()
for _ in range(50):
    echo(random.nextInt())

echo(f"50 iterations took {perf_counter() - start} seconds. Now lets look at javapy:")
sleep(5)
start = perf_counter()
from javapy import JavaClass
random = JavaClass("java.util.Random")()

for _ in range(150):
    echo(random.nextInt())
echo(f"150 iterations took only {perf_counter() - start} seconds :D")
echo("(For both, it includes the time it takes to resolve the java.util.Random class, as well as the library loading)")
```
