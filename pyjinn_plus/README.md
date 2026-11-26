# Pyjinn Plus
An experimental pyjinn library containing many utilities

Concept heavily inspired by [MSP]()
# What is Pyjinn plus?
p+ / pp is a collection of utilities for pyjinn. Many of its additions are recreations of python libraries, separated into neat classes you can import
# Table of contents
- [reflect]() - Relfection helper
- [JavaArray]() - Array creation helper
- [json]()
- [inspect]()
- [Path]()
- [math]()
- [random]()
- [threading]()
- [Thread]()
- [Lock]()
- [time]()
- [asyncio]()
- [socket]() - Very experimental, usage not advised
- [Queue]()
- [Builtins]()
- [os]()
- [pyjinn]() - Interpreter utilities
- [java]() - Java utilities
- [shutil]()
- [ClassBuilder]() - Custom java class creation

# API
## `reflect`
### `field(obj, field:str, *, raw_field=False) -> JavaObject`:
- Grabs a field of an object, regardless of visibility flags
- Doesnt search superclasses
- if `raw_field` is `True`, it returns the field handle, rather than its value
### `method(obj, method:str, args:list=[], *, raw_method=False) -> JavaObject`:
- Invokes a method of an object, regardless of visibility flags
- Doesnt search superclasses
- if `raw_method` is `True`, it returns the method handle, rather than the result of it
### `cast(obj, to_type)`:
- Casts an object to a given runtime type
### `as_class(obj)`:
- Returns the objects class
- Handles `org.pyjinn.interpreter.JavaClass` and `java.lang.Class` objects
### `matches_types(firsthand_types:list, secondhand_types:list) -> bool`:
- Returns wether the types of 2 iterables can be interchanged according to pyjinns rules
## `JavaArray`:
### `JavaArray(*items, specific_type=Object)`:
- Returns an array with the items passed down, casted to a specific runtime type
### `of(items:list, specific_type=Object)`:
- Returns an array of the items passed down, casted to a specific runtime type
### `to_classes(*items)`:
- Returns an array of the classes of the items passed down, casted to the runtime type of java.lang.Class
### `classes_of(items)`:
- Returns an array of the classes of the items passed down, casted to the runtime type of java.lang.Class
## `json`
A copy of [pyjinn_json]()
### `dumps(obj)`:
- Returns the json string equivalent of the object passed down
### `loads(json_string:str)`:
- Returns the object equivalent of the json string passed down
## `inspect`
### `getsource(obj)`:
- Returns a non faithful recreation of the src of pyjinn FUNCTIONS
- Methods dont work yet
### `callstack()`:
- Returns the callstack of the context this was called from
### `stack()`:
- Returns the stack
## `Path`
Most (like 90%) of the methods of `pathlib.Path` exists here, and is the same
Due to this, ill only be documenting the more notable ones:
- `.path` field returns the java path object
- supports `/` concatentation with `str`, `Path` or `java.nio.file.Path`
- Has the most used `touch()`, `unlink()`, `mkdir()` and `write_text(data:str)` methods among others
- Due to pyjinns lack of properties, all properties of `pathlib.Path` (such as `.parent` field) have been replaced with methods (so like `.parent()`)
## `math`
Most of the functions of the `math` library
## `random()`
A few functions of the `random` library:
- `random()`
- `randint(a, b)`
- `randrange(a, b)` (Note: `steps` is not supported)
- `uniform(a, b)`
- `choice(iterable)`
- `shuffle(iterable)`
- `gauss(mu, sigma)`
- `seed(x)`
## `threading`
Does not contain the `Thread`/`Lock` library as a nested class, as pyjinn doesnt support that atm
- `current_thread()`
- `main_thread()`
- `active_count()`
- `enumerate()`
- `get_ident()`
- `get_native_id()`
## `Thread`
May not work exactly as you please, as threads generally work weirdly with pyjinn, due to the scripts not owning a process themselves
### `Thread(*, target=None, name=None, args=[], kwargs={}, daemon=None)`:
- `start(self)`
- `run(self)`
- `join(self)`
- `is_alive(self)`
- `set_name(self, name)`
- `set_daemon(self, state)`
- `get_ident(self)`
- `get_native_id(self)`
## `Lock`
In practice, it is equal to `threading.Lock` (minus the context manager protocol)
## `time`
- `sleep(time)`
- `time()`
- `perf_counter()`
- `perf_counter_ns()`
## `asyncio`
Sidenote: `while True` loops in `async` contexts must `await asyncio.sleep` for a minimum of `0` seconds at the end of every, otherwise the game freezes forever
- `run(coro)` Note: Does not block
- `sleep(time)` Must be `await`-ed
## `socket`
Dont use this
## `Queue`
- `Queue()`
- `put(self, item, block=True, timeout:int|float=0)`
- `put_nowait(self, item)`
- `get(self, block=True, timeout:int|float=0) -> Any`
- `get_nowait(self) -> Any`
- `empty(self) -> bool`
- `qsize(self) -> int`
## `builtins`
- `map(func, iterable)` Note: instantly evaluated into a list
- `any(iterable)`
- `setattr(obj, name, value)`
- `iter(obj)`
- `next(gen)`
## `os`
- `getcwd()`
## `pyjinn`
### `eval_pyjinn_script(src)`
The pyjinn equivalent of the python `system.lib.java.eval_pyjinn_script`
### `jobless_script(self, src, argv=[], stdout=__script__.stdout, stderr=__script__.stdout)`
Equal to `eval_pyjinn_script`, except the created script does not have a job:
- Never exits on its own (only exits when `.exit()` is called on it, or an exception happens on the module level)
- Due to it never exiting, `zombie callback` mecomes a non issue
- Does not appear in `\jobs` and cannot be killed by `\killjob -1`
- Cannot have things that require a `job`, ie even listeners
## `java`
### `JavaClass(clss)`
Same as the builtin `JavaClass`, but accepts variables as its argument
## `shutil`
- `rmtree(path:Path)`
## `ClassBuilder`
Experimental class to creating java classes
### `new_class(path, src)`
- Creates a runtime class under `path` with the java sourcecode of `src`, and returns the `java.lang.Class` handle
- If the class exists under `path`, it returns that class instead
- `path` must be the same as `package` + the class name combined
### `load_class(clss)`
Loads in a class creates by `ClassBuilder` if it exists

