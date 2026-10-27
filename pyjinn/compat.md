## **ACLoPLFSBP**
- *A Comprehensive List of Python Language Features Supported By Pyjinn* (in no particular order)

Target pyjinn version: `Pyjinn 0.14` (`\eval version_info().pyjinn`)

- [Compatibilities](https://github.com/SmartBoty/Minescript/new/main/pyjinn#compatibilities)
- [Incompatibilities](https://github.com/SmartBoty/Minescript/new/main/pyjinn#incompatibilities)

## Compatibilities
- [Supported builtin libraries](https://github.com/SmartBoty/Minescript/new/main/pyjinn#supported-builtin-libraries)
- [Supported language features](https://github.com/SmartBoty/Minescript/new/main/pyjinn#supported-language-features)
- [Supported global variables](https://github.com/SmartBoty/Minescript/new/main/pyjinn#supported-global-variables)
- [Known Supported dunders](https://github.com/SmartBoty/Minescript/new/main/pyjinn#known-supported-dunders)
### **Supported** builtin libraries:
```py
import sys

sys.argv
sys.version
sys.stdout
sys.stderr
sys.exit(status) # Note: only accepts integers
```
```py
import pathlib

path = pathlib.Path("some/path")
path.mkdir(exist_ok=True)
path.joinpath(*elements)
path.exists()
```
```py
import math

math.pi
math.e
math.tau

math.sqrt(x)
math.fmod(x)
```
```py
import json

json.loads("json_string")
```
```py
import atexit

atexit.register(func, *args, **kwargs) # Returns `func`
atexit.unregister(func)
```
### **Supported** language features:
```py
a, b, c = iterable
x, y = 1, 2
iterable[spli:cing]
del obj
yield x
async
await
def func(a, *b, c=None): ...
def func(a, /, b, *, c): ... # Posonly and Kwonly args
foo(*args, **kwargs)
foo(x=1) # Kwargs
return
pass
if
elif
else
try
except
finally
for
while
lambda
@staticmethod
@classmethod
[i for i in j]
f"F-{"str"}ings"
import xyz
import xyz as a
from xyz imort a
def foo(a:int) -> str: ...
x:int = foo()
```
### **Supported** global variables
```py
__name__
```
### Known **supported** dunders:
```py
__eq__
__ne__
__lt__
__le__
__gt__
__ge__
__add__
__sub__
__mul__
__truediv__
__floordiv__
__mod__
__pow__
__lshift__
__rshift__
__and__
__rand__
__or__
__ror__
__xor__
__rxor__
__getitem__
__setitem__
__contains__
__call__
__next__
```

## Incompatibilities
- [Unsupported builtin libraries](https://github.com/SmartBoty/Minescript/new/main/pyjinn#unsupported-builtin-libraries)
- [Unsupported language features](https://github.com/SmartBoty/Minescript/new/main/pyjinn#unsupported-language-features)
- [Unsupported global variables](https://github.com/SmartBoty/Minescript/new/main/pyjinn#unsupported-global-variables)
- [Known unsupported dunders](https://github.com/SmartBoty/Minescript/new/main/pyjinn#known-unsupported-dunders)
### **Unsupported** builtin libraries
- No python module is supported, other than a few, wich is only partially supported (community made libraries can be used instead)
### **Unsupported** language features:
```py
... # Elipsis
with obj: ...
with obj as x: ...
_, *rest = iterable # Specifically the `*rest` part
class SomeClass(OtherClass): ... # Specifically, subclassing
@decorator # Specifically custom decorators / descriptors only
for x in y: ...
else: ... # Specifically the `else` after a `for`
while x: ...
else: ... # Specifically the `else` after a `while`
try: ...
finally: ...
else: ... # Specifically the `else` after a `finally`
(i for i in j)
b"foo" # Python style bytes
@=
//=
%=
**=
<<=
>>=
&=
|=
^=
```
### **Unsupported** global variables
- All variables starting and ending with `__` except `__name__`
### Known, **unsupported** dunders:
```py
__repr__ # Cause: missing `repr` function
__str__ # Never gets called
__bytes__ # Cause: pyjinn only supports javas `byte`-s, and missing `byte` function
__format__ # Cause: missing `format` function
__hash__ # Cause: missing `hash` function
__bool__ # Never gets called
__dir__ # Cause: missing `dir` function
__radd__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__iadd__ # Cause: unidentified
__rsub__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__isub__ # Cause: unidentified
__rmul__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__imul__ # Cause: unidentified
__rtruediv__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__itruediv__ # Cause: unidentified
__rfloordiv__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__ifloordiv__ # Cause: unidentified
__rmod__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__imod__ # Cause: unidentified
__rpow__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__rlshift__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__rrshift__ # Cause: Interpreter throws exception on the left object, never reaching this dunder
__neg__ # Cause: unidentified
__abs__ # Never gets called
__int__ # Never gets called
__float__ # Never gets called
__complex__ # Cause: Missing `complex` function
__index__ # Never gets called
__round__ # Never gets called
__delitem__ # Cause: Explicitly not supported
__iter__ # Never gets called
__reversed__ # Cause: missing `reversed` function
__missing__ # Never gets called
```
