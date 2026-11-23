Works almost if not exactly like the builtin `java.py` (without the `eval_pyjinn_script`), but about 3× faster, and allows you to grab arbitrary objects from pyjinn, and use them in python

Requirements:
- Minescript 5.0b or higher
- `pyjinn_json`: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py

Please report any inconsistencies in the discord: https://discord.com/channels/930220988472389713/1543638360143437845

Features:
- ~3-6× faster execution compared to `java.py` (builtin)
- `type()`* class grabbing (Equivalend of `Object.class` in java)
- `isinstance`, `len` checks
- Converting `java.py` (builtin) objects to `javapy` objects and back
- Automatic GC (garbage collection)
- Evaluating src or syntax to pyjinn code

## Javapy specific functions / objects
### `convert(obj:JavaObject) -> JavaObject`
Converts a Javapy object into a `java.py` (builtin) object

OR

Converts a `java.py` (builtin) object into a Javapy object

Note: Does not create a copy of the java side object

### `submit(obj:JavaObject) -> str`
Submits a Javapy object to a global space. Returns the uuid it was stored under. All processes see the same global space

Note: Does not create a copy of the java side object

### `request(uuid:str) -> JavaObject`
Requests a previously submitted (or manually submitted via pyjinn) object under a uuid. All processes see the same global space

Note: Does not create a copy of the java side object

### `type(obj)`
Import it to replace the already existing `type()` class. It behaves exactly how it does in pyjinn, returning the java side class of the object. Works exactly like the builtin for any other object

### `__script__`
This is the handle to a completely empty pyjinn script instance

## Manual optimizations
Constructing a java class is faster if done on the same line that it was evaluated on
```py
JavaClass("some.class.path")() # Faster

# Slower
clss = JavaClass("some.class.path")
clss()
```

## Quirks
Javapy can differentiate between `foo.bar` and `foo.bar()`, and they will work differently
- `foo.bar` is resolved as a field access
- `foo.bar()` is resolved as a method call
This means, that if `foo` has a method called `bar`, the only way to access it (outside of reflection) is by doing `foo.bar()` wich will immediately call said method, making it impossible to get a refference to the method.

# Example usages:

Visual showcase of the difference in speed (compared to the builtin library):
```py
from system.lib.minescript import echo
from time import perf_counter, sleep

echo("Builtin library:")
sleep(2)
echo("Begin")
start = perf_counter()
from system.lib.java import JavaClass
echo(f"Library loaded in {perf_counter() - start} seconds!")
start = perf_counter()
random = JavaClass("java.util.Random")
echo(f"'java.util.Random' class resolved in {perf_counter() - start} seconds!")
start = perf_counter()
random = random()
echo(f"'java.util.Random' class instantiated in {perf_counter() - start} seconds!")
start = perf_counter()
for _ in range(50):
    echo(random.nextInt())

echo(f"50 iterations took {perf_counter() - start} seconds. Now lets look at javapy:")
sleep(5)
echo("Begin")
start = perf_counter()
from javapy import JavaClass
echo(f"Library loaded in {perf_counter() - start} seconds!")
start = perf_counter()
random = JavaClass("java.util.Random")
echo(f"'java.util.Random' class resolved in {perf_counter() - start} seconds!")
start = perf_counter()
random = random()
echo(f"'java.util.Random' class instantiated in {perf_counter() - start} seconds!")
start = perf_counter()
for _ in range(300):
    echo(random.nextInt())
echo(f"300 iterations took only {perf_counter() - start} seconds :D")
```
