#!python
#from system.pyj.minescript import JavaClass
import atexit
_ToNumberPolicy = JavaClass("com.google.gson.ToNumberPolicy")
_Gson = JavaClass("com.google.gson.GsonBuilder")().serializeNulls().setObjectToNumberStrategy(_ToNumberPolicy.LONG_OR_DOUBLE).create()
_Map = JavaClass("java.util.Map")
_HashMap = JavaClass("java.util.HashMap")
_List = JavaClass("java.util.List")
_ArrayList = JavaClass("java.util.ArrayList")
_String = JavaClass("java.lang.String")
_Long = JavaClass("java.lang.Long")
_Path = JavaClass("java.nio.file.Path")
_Paths = JavaClass("java.nio.file.Paths")
_Files = JavaClass("java.nio.file.Files")
_FileAlreadyExistsException = JavaClass("java.nio.file.FileAlreadyExistsException")
_NoSuchFileException = JavaClass("java.nio.file.NoSuchFileException")
_FileAttribute = JavaClass("java.nio.file.attribute.FileAttribute")
_OpenOption = JavaClass("java.nio.file.OpenOption")
_JavaClass = JavaClass("org.pyjinn.interpreter.JavaClass")
_Class = JavaClass("java.lang.Class")
_TypeChecker = JavaClass("org.pyjinn.interpreter.Script$TypeChecker")
_String = JavaClass("java.lang.String")
_StatementBlock = JavaClass("org.pyjinn.interpreter.Script$StatementBlock")
_ConstantExpression = JavaClass("org.pyjinn.interpreter.Script$ConstantExpression")
_Object = JavaClass("java.lang.Object")
_Array = JavaClass("java.lang.reflect.Array")
_Math = JavaClass("java.lang.Math")
_BigInteger = JavaClass("java.math.BigInteger")
_Double = JavaClass("java.lang.Double")
_Random = JavaClass("java.util.Random")
_Collections = JavaClass("java.util.Collections")
_Thread = JavaClass("java.lang.Thread")
_Runnable = JavaClass("java.lang.Runnable")
_Semaphore = JavaClass("java.util.concurrent.Semaphore")
_System = JavaClass("java.lang.System")
_Socket = JavaClass("java.net.Socket")
_BufferedWriter = JavaClass("java.io.BufferedWriter")
_OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
_StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
_BufferedReader = JavaClass("java.io.BufferedReader")
_InputStreamReader = JavaClass("java.io.InputStreamReader")
_InetSocketAddress = JavaClass("java.net.InetSocketAddress")
_LinkedBlockingQueue = JavaClass("java.util.LinkedBlockingQueue")
_TimeUnit = JavaClass("java.util.concurrent.TimeUnit")

TYPE_CHECKING = False

class reflect:
    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'reflect'")

    _cached = {
        "class":{},
        "field":{},
        "method":{}
    }

    def as_class(self,obj):
        if isinstance(obj, _JavaClass): return type(obj)
        elif isinstance(obj, _Class): return obj
        else: return obj.getClass()

    def field(self,obj, field, *, raw_field=False):
        clss = reflect.as_class(obj)
        id = clss.getName()
        if id in reflect._cached["field"]:
            if field in reflect._cached["field"][id]:
                if raw_field: return reflect._cached["field"][id][field]
                else: return reflect._cached["field"][id][field].get(obj)
        else: reflect._cached["field"][id] = {}
        f = clss.getDeclaredField(field)
        f.setAccessible(True)
        reflect._cached["field"][id][field] = f
        if raw_field: return f
        else: return f.get(obj)

    def cast(self, obj, to_type): return reflect.as_class(to_type).cast(type(_Object).cast(obj))
reflect = reflect()

class JavaArray:
    def of(self, items, specific_type=_Object):
        if specific_type is _Object: return reflect.field(list(items), "list").toArray()
        else:
            array = _Array.newInstance(type(specific_type),len(items))
            for i,arg in enumerate(items):
                _Array.set(array, i, arg)
            return array
    def __call__(self, *items):
        return reflect.field(list(items), "list").toArray()
    def to_classes(self, *items):
        return _TypeChecker.getTypes(JavaArray.of(items))
    def classes_of(self, items):
        return _TypeChecker.getTypes(JavaArray.of(items))
JavaArray = JavaArray()

class json:
    # Original source: https://github.com/SmartBoty/Minescript/blob/main/pyjinn/pyjinn_json.py
    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'json'")

    def _listify_pyjinnlist(self,items):
        lst = _ArrayList()
        for item in items:
            lst.add(item)
        return lst

    def _isdigit(self,item):
        if item.startswith("-"): item = item[1:]
        try: float(item) ; return True
        except: pass
        return False

    def _mapify_pyjinndict(self,pyjinndict):
        out = _HashMap()
        for key,value in pyjinndict.items():
            out.put(key,json._handle_tojson(value))
        return out

    def _dictify_javamap(self,javamap):
        out = {}
        for key in javamap.keySet():
            out[key] = json._handle_fromjson(javamap.get(key))
        return out

    def _handle_fromjson(self,obj):
        if isinstance(obj, _Map): return json._dictify_javamap(obj)
        elif isinstance(obj, _List): return [json._handle_fromjson(javaobj) for javaobj in obj]
        elif isinstance(obj, _Long): return int(obj)
        else: return obj

    def _handle_tojson(self,obj):
        if isinstance(obj, dict): return json._mapify_pyjinndict(obj)
        elif isinstance(obj, (list, tuple)): return json._listify_pyjinnlist([json._handle_tojson(javaobj) for javaobj in obj])
        else: return obj

    def loads(self,json_string:str):
        try:
            json_string = json_string.strip()
            if json_string.startswith("["): return json._handle_fromjson(_Gson.fromJson(json_string, type(_List)))
            elif json_string.startswith("{"): return json._handle_fromjson(_Gson.fromJson(json_string, type(_Map)))
            elif json_string == "null": return None
            elif json_string == "true": return True
            elif json_string == "false": return False
            elif json._isdigit(json_string):
                if "." in json_string or "e" in json_string.lower(): return float(json_string)
                else: return int(json_string)
            elif json_string.startswith('"'):
                if json_string.endswith('"'): return _Gson.fromJson(json_string, type(_String))
                else: raise Exception(f"Unterminated string: {json_string}<<<")
            else: raise Exception(f"Invalid literal: '{json_string}'")
        except Exception as e: raise Exception(f"§eJSONDecodeException: {e.getMessage().replace("path $.","")}")

    def dumps(self,obj) -> str:
        try: return _Gson.toJson(json._handle_tojson(obj))
        except Exception as e: raise Exception(f"§eJSONEncodeException: {e.getMessage()}")
json = json()

class inspect:
    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'inspect'")

    def callstack(self): return reflect.field(__script__,"callStack").get().toArray()[1:]

    def getsource(self,obj):
        definition = obj.functionDef()
        name = definition.identifier().name()
        is_async = definition.isAsync()
        decorators = definition.decorators()
        args = definition.args()
        vararg = definition.vararg()
        kwarg = definition.kwarg()
        kwonly = definition.keywordOnlyArgs()
        body = definition.body()
        if vararg.isEmpty(): vararg = []
        else: vararg = [f"*{vararg.get().identifier().name()}"]
        if kwarg.isEmpty(): kwarg = []
        else: kwarg = [f"**{kwarg.get().identifier().name()}"]
        src = None
        if isinstance(body, _StatementBlock):
            statements = body.statements()
            docstring = ""
            indent = 4
            if isinstance(statements[0], _ConstantExpression) and isinstance(statements[0].value(), str):
                docstring = statements[0].toString().translateEscapes()
                if "\n" in docstring:
                    lines = [i.strip() for i in docstring.split("\n")]
                    docstring = "\n  ".join(lines)
                    q = docstring[0]
                    docstring = q*2 + docstring + q*2
                docstring = "  " + docstring
                statements = statements[1:]
            indent = min(indent,2)
            src = docstring + ("\n" + " "*indent) + ("\n" + " "*indent).join(list("\n".join([str(i) for i in statements]).split("\n")))
        else:
            src = body.toString()
            if not src.startswith(" "):
                src = "  " + src
        all_args = [arg.identifier().name() for arg in args]
        all_args += vararg
        all_args += [arg.identifier().name() for arg in kwonly]
        all_args += kwarg
        header = "".join([f"@{dec.name()}\n" for dec in decorators]) + ("async " if is_async else "") + "def " + name + f"({", ".join(all_args)}):\n"
        return header + src
inspect = inspect()

class Path:
    def _unwrap_str(self, other=None):
        if other is not None:
            if isinstance(other, str): return other
            elif isinstance(other, Path): return other.path.toString()
            elif isinstance(other, _Path): return other.toString()
        else: return self.path.toString()

    def _unwrap_path(self, path=None):
        if path is not None:
            if isinstance(path, str): return Path(path).path
            elif isinstance(path, Path): return path.path
            elif isinstance(path, _Path): return path
        else: return self.path

    def __init__(self, path, *path_pieces):
        self.path = _Path.of(self._unwrap_str(path), JavaArray.of(path_pieces,type("")))

    def name(self) -> str: return self.path.getFileName()

    def parent(self): return Path(self.path.getParent())

    def resolve(self): return Path(self.absolute().path.normalize())

    def absolute(self): return Path(self.path.toAbsolutePath())

    def samefile(self, other): return self.path.equals(Path(other).path)

    def iterdir(self):
        for c in self.path:
            yield c

    def as_uri(self) -> str: return self.path.toUri().toString()

    def touch(self, exist_ok=True):
        try: _Files.createFile(self.path, JavaArray.of([],_FileAttribute))
        except _FileAlreadyExistsException as e:
            if not exist_ok: raise e

    def unlink(self, missing_ok=False):
        try: _Files.delete(self.path)
        except _NoSuchFileException as e:
            if not missing_ok: raise e

    def mkdir(self, parents=False):
        if parents: _Files.createdirectories(self.path)
        else: _Files.createDirectory(self.path)

    def write_text(self, data): _Files.writeString(self.path, data, JavaArray.of([],_OpenOption))

    def read_text(self) -> str: return _Files.readString(self.path)

    def write_bytes(self, data): _Files.write(self.path, data, JavaArray.of([],_OpenOption))

    def read_bytes(self, data): return _Files.readAllBytes(self.path)

    def exists(self): return _Files.exists(self.path)

    def is_dir(self): return _Files.isDirectory(self.path)

    def is_file(self): return _Files.isRegularFile(self.path)

    def relative_path_to(self, path): return Path(self.path.relativize(path))

    def len(self): return self.__len__()

    def join(self, path): return self.__truediv__(path)

    def __len__(self): return self.path.getNameCount()

    def __truediv__(self, path): return Path(self.path.resolve(self._unwrap_str(path))).resolve()

class math:
    def __init__(self):
        self.pi = _Math.PI
        self.e = _Math.E
        self.tau = 2 * _Math.PI
        self.inf = _Double.POSITIVE_INFINITY
        self.nan = _Double.NaN
        
    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'math'")
    
    def ceil(self, x): return int(_Math.ceil(x))

    def floor(self, x): return int(_Math.floor(x))

    def fabs(self, x): return _Math.fabs(x)

    def gcd(self, a, b): return int(_BigInteger.valueOf(a).gcd(_BigInteger.valueOf(b)))

    def lcm(self, a, b): return math.abs(a / math.gcd(a,b) * b)

    def isqrt(self, x): return int(_BigInteger.valueOf(x).sqrt())

    def fmod(self, a, b): return a % b

    def remainder(self, a, b): return _Math.IEEEremainder(a, b)

    def copysign(self, a, b): return _Math.copysign(a, b)

    def isfinite(self, x): return _Double.isFinite(x)

    def isnan(self, x): return _Double.isNaN(x)

    def sqrt(self, x): return _Math.sqrt(x)

    def cbrt(self, x): return _Math.cbrt(x)

    def pow(self, a, b): return _Math.pow(a, b)

    def exp(self, x): return _Math.exp(x)

    def exp2(self, x): return _Math.pow(2, x)

    def expm1(self, x): return _Math.expm1(x)

    def log(self, x, base=None):
        if base is None: return _Math.log(x)
        else: return _Math.log(x) / _Math.log(base)

    def log2(self, x): return _Math.log(x) / _Math.log(2)

    def log10(self, x): return _Math.log10(x)

    def log1p(self, x): return _Math.log1p(x)

    def sin(self, x): return _Math.sin(x)

    def cos(self, x): return _Math.cos(x)

    def tan(self, x): return _Math.tan(x)

    def asin(self, x): return _Math.asin(x)

    def acos(self, x): return _Math.acos(x)

    def atan(self, x): return _Math.atan(x)

    def atan2(self, a, b): return _Math.atan2(a, b)

    def hypot(self, a, b): return _Math.hypot(a, b)

    def degrees(self, x): return _Math.toDegrees(x)

    def radians(self, x): return _Math.toRadians(x)

    def sinh(self, x): return _Math.sinh(x)

    def cosh(self, x): return _Math.cosh(x)

    def tanh(self, x): return _Math.tanh(x)

    def ldexp(self, a, b): return _Math.scalb(a, b)

    def nextafter(self, a, b): return _Math.nextAfter(a,b)

    def ulp(self, x): return _Math.ulp(x)

    def fma(self, a, b, c): return _Math.fma(a,b,c)
math = math()

class random:
    def __init__(self):
        self.rng = _Random()

    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'random'")

    def random(self): return self.nextDouble()

    def randint(self, a, b): return self.rng.nextInt(a, b + 1)

    def randrange(self, a, b=None):
        if b is None: return self.rng.nextInt(a)
        else: return self.rng.nextInt(a, b)

    def uniform(self, a, b): return a + (b - a) * self.rng.nextDouble()

    def choice(self, iterable): iterable[random.randint(len(iterable))]

    def shuffle(self, iterable):
        seq = JavaList(iterable)
        _Collections.shuffle(seq, self.rng)
        return seq

    def gauss(self, mu, sigma): return mu + sigma * self.rng.nextGaussian()

    def seed(self, x=None):
        if x is None: self.rng = _Random()
        else: self.rng.setSeed(x)
random = random()

class threading:
    def __init__(self):
        self._main_thread = _Thread.currentThread()
        self._threads = {}
        def exit_worker():
            for thread in self._threads:
                thread.stop()
        atexit.register(exit_worker)

    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'threading'")

    def current_thread(self): return _Thread.currentThread()

    def main_thread(self): return self._main_thread

    def active_count(self): return _Thread.activeCount()

    def enumerate(self): return _Thread.getAllStackTraces().keySet()

    def get_ident(self): _Thread.currentThread().getId()

    def get_native_id(self): _Thread.currentThread().threadId()
threading = threading()

class Thread:
    def __init__(self, *, target=None, name=None, args=[], kwargs={}, daemon=None):
        threading._threads[self] = None
        self.target = target
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.daemon = daemon
        def _thread_worker(self, args, kwargs):
            try: self.target(*args,**kwargs)
            except: pass
            if self.daemon: remove_event_listener(self._listener_id)
            self._thread.stop()
        self._thread = _Thread(_Runnable(lambda: _thread_worker(self, args, kwargs)),name) if name is not None else _Thread(_Runnable(lambda: _thread_worker(self, args, kwargs)))
        if daemon: self._listener_id = add_event_listener("world",lambda _: None)
        else: self._listener_id = None

    def start(self): self._thread.start()

    def stop(self):
        if self.daemon: remove_event_listener(self._listener_id)
        self._thread.stop()
        del threading._threads[self]

    def run(self): self._thread.run()

    def join(self, timeout=None):
        if timeout is not None: self._thread.join(timeout)
        else: self._thread.join()
    
    def is_alive(self): return self._thread.isAlive()

    def set_name(self, name):
        self._thread.setName(name)
        self.name = name

    def set_daemon(self, state):
        self._thread.setDaemon(state)
        self.daemon = state

    def get_ident(self): return self._thread.getId()

    def get_native_id(self): return self._thread.threadId()

class Lock:
    def __init__(self):
        self.lock = _Semaphore(1)

    def acquire(self):
        self.lock.acquire()

    def release(self):
        if self.lock.availablePermits() > 0: self.lock.release()

class time:
    def sleep(self, time): _Thread.sleep(int(time*1000))
    def perf_counter(self): return _System.nanoTime() / 1e9
    def perf_counter_ns(self): return _System.nanoTime()
    def time(self): return _System.currentTimeMillis() / 1000

class asyncio:
    def __init__(self):
        self._event_loop = EventLoop()

    def __call__(self,*args,**kwargs): raise Exception("Cannot instantiate 'asyncio'")

    def run(self, coro): self._event_loop.run(lambda _: coro())

    def sleep(self, time): self._event_loop.sleep(time)
asyncio = asyncio()

class socket:
    def __init__(self):
        self._socket = _Socket()
        self._socket.setSoTimeout(1)
        self._writer = _BufferedWriter(_OutputStreamWriter(self.socket.getOutputStream(), _StandardCharsets.UTF_8))
        self._reader = _BufferedReader(_InputStreamReader(self.socket.getInputStream(), _StandardCharsets.UTF_8))

    def write(self, data): self._writer.write(str(data))

    def flush(self): self._writer.flush()

    def read_line(self):
        if self._reader.ready():
            try: return self._reader.readLine()
            except Exception as e:
                if not e.getMessage().startswith("Connection reset"): raise e
            return None
        else: return None

    def ready(self): return self._reader.ready()

    def bind(self, host, port): self._socket.bind(_InetSocketAddress(host, port))

class Queue:
    def __init__(self):
        self.q = _LinkedBlockingQueue()

    def put(self, item, block=True, timeout=0):
        if block: return self.q.put(item)
        elif timeout > 0: return self.q.offer(item, timeout, _TimeUnit.SECONDS)
        else: return self.q.add(item)

    def put_nowait(self, item): self.put(item,False)

    def get(self, block=True, timeout=0):
        if block: return self.q.take()
        elif timeout > 0: return self.q.poll(timeout, _TimeUnit.SECONDS)
        else: return self.q.remove()

    def get_nowait(self): return self.get(False)

    def empty(self): return self.q.remainingCapacity() == 0

    def qsize(self): return self.q.size()

if not TYPE_CHECKING:
    def map(callable, iterable):
        return [callable(i) for i in iterable]

if TYPE_CHECKING:
    class reflect:
        """
        Helper functions with reflection
        """
        @staticmethod
        def as_class(obj) -> any:
            """
            Returns the underlying runtime type of the object
            """
        @staticmethod
        def field(obj, field:str, *, raw_field=False) -> any:
            """
            Grabs a field of an object, regardless of visibility flags
    
            Searches top level only
            """
        @staticmethod
        def cast(obj, to_type) -> any:
            """
            Cast an object to a specific runtime type
            """
    class JavaArray:
        """
        Helper methods to creating java arrays
        """
        @staticmethod
        def of(items:list|tuple, specific_type=_Object) -> any:
            """
            Returns an array with the items from an iterable, casted to a specific runtime type

            Default `specific_type` is `java.lang.Object`
            """
        @staticmethod
        def __new__(cls, *items) -> any:
            """
            Returns an array made from the items passed down, casted to a specific runtime type

            Default `specific_type` is `java.lang.Object`
            """
        @staticmethod
        def classes_of(items:list|tuple) -> any:
            """
            Returns an array of the runtime types of the objects in the iterable, casted to the runtime type of `java.lang.Class`
            """
        @staticmethod
        def to_classes(*items) -> any:
            """
            Returns an array of the runtime types of the objects passed down, casted to the runtime type of `java.lang.Class`
            """
    class json:
        """
        Provides a subset of the functionality of the `json` library

        Note: output is not guaranteed to be exact with the `json` library
        """
        @staticmethod
        def loads(json_string:str) -> any:
            """
            `json.loads(...)` equivalent
            """
        @staticmethod
        def dumps(obj) -> str:
            """
            `json.dumps(...)` equivalent
            """
    class inspect:
        """
        Provides a small subset of the functionality of the `inspect` library

        Note: output is not guaranteed to be exact with the `inspect` library
        """
        @staticmethod
        def callstack() -> any:
            """
            Returns the callstack of the context this was called from
            """
        @staticmethod
        def getsource(func) -> str:
            """
            Returns a non faithful recreation of the src of most pyjinn functions
    
            Note: does not work on methods, as those do not conserve their source
            """
    class Path:
        """
        Provides a small subset of the functionality of the `pathlib.Path` class

        Note: output is not guaranteed to be exact with the `pathlib` library
        
        Note2: no methods mutate any `Path` object, all of them return new ones

        Note3: Supports `/` concatentating with `str`, `Path` and `java.nio.file.Path`
        """
        def __init__(self, path, *pieces) -> Path:
            """
            Path object that points to a file or directory

            Get the underlying java `Path` object with `Path.path`
            """
        def name(self) -> str:
            """
            Returns the name of the file or directory this path points to

            `pathlib.Path.name` equivalent
            """
        def parent(self) -> Path:
            """
            Returns the parent directory, or `None` if this is the root, of the directory or file this path points to

            `pathlib.Path.parent` equivalent
            """
        def resolve(self) -> Path:
            """
            `pathlib.Path.resolve()` equivalent
            """
        def absolute(self) -> Path:
            """
            `pathlib.Path.absolute()` equivalent
            """
        def samefile(self, other) -> bool:
            """
            `pathlib.Path.samefile(...)` equivalent
            """
        def iterdir(self) -> any:
            """
            `pathlib.Path.iterdir()` equivalent
            """
        def as_uri(self) -> str:
            """
            `pathlib.Path.as_uri()` equivalent
            """
        def touch(self, exist_ok=True):
            """
            `pathlib.Path.touch()` equivalent
            """
        def unlink(self, missing_ok=False):
            """
            `pathlib.Path.unlink()` equivalent
            """
        def mkdir(self, parents=False):
            """
            `pathlib.Path.mkdir()` equivalent
            """
        def write_text(self, data:str):
            """
            `pathlib.Path.write_text(...)` equivalent
            """
        def read_text(self) -> str:
            """
            `pathlib.Path.read_text()` equivalent
            """
        def write_bytes(self, data):
            """
            `pathlib.Path.write_bytes(...)` equivalent

            Only works with java `byte`-s
            """
        def read_bytes(self) -> any:
            """
            `pathlib.Path.read_bytes()` equivalent

            Returns java `byte`-s
            """
        def exists(self) -> bool:
            """
            `pathlib.Path.exists()` equivalent
            """
        def is_dir(self) -> bool:
            """
            `pathlib.Path.is_dir()` equivalent
            """
        def is_file(self) -> bool:
            """
            `pathlib.Path.is_file()` equivalent
            """
        def relative_path_to(self, path) -> Path:
            """
            Returns the path from this path, to a relative path
            """
        def len(self) -> int:
            """
            Returns the number of components in the path
            """
        def join(self, path) -> Path:
            """
            `pathlib.Path / obj` equivalent
            """
    class math:
        """
        Provides a subset of the functionality of the `math` library
        """
        @staticmethod
        def ceil(x:int|float):
            """
            `math.ceil(...)` equivalent
            """
        @staticmethod
        def floor(x:int|float):
            """
            `math.floor(...)` equivalent
            """
        @staticmethod
        def fabs(x:int|float):
            """
            `math.fabs(...)` equivalent
            """
        @staticmethod
        def gcd(a:int|float, b:int|float):
            """
            `math.gcd(...)` equivalent
            """
        @staticmethod
        def lcm(a:int|float, b:int|float):
            """
            `math.lcm(...)` equivalent
            """
        @staticmethod
        def isqrt(x:int|float):
            """
            `math.isqrt(...)` equivalent
            """
        @staticmethod
        def fmod(a:int|float, b:int|float):
            """
            `math.fmod(...)` equivalent
            """
        @staticmethod
        def remainder(a:int|float, b:int|float):
            """
            `math.remainder(...)` equivalent
            """
        @staticmethod
        def copysign(a:int|float, b:int|float):
            """
            `math.copysign(...)` equivalent
            """
        @staticmethod
        def isfinite(x:int|float):
            """
            `math.isfinite(...)` equivalent
            """
        @staticmethod
        def isnan(x:int|float):
            """
            `math.isnan(...)` equivalent
            """
        @staticmethod
        def sqrt(x:int|float):
            """
            `math.sqrt(...)` equivalent
            """
        @staticmethod
        def cbrt(x:int|float):
            """
            `math.cbrt(...)` equivalent
            """
        @staticmethod
        def pow(a:int|float, b:int|float):
            """
            `math.pow(...)` equivalent
            """
        @staticmethod
        def exp(x:int|float):
            """
            `math.exp(...)` equivalent
            """
        @staticmethod
        def exp2(x:int|float):
            """
            `math.exp2(...)` equivalent
            """
        @staticmethod
        def expm1(x:int|float):
            """
            `math.expm1(...)` equivalent
            """
        @staticmethod
        def log(x:int|float, base:int|float=None):
            """
            `math.log(...)` equivalent
            """
        @staticmethod
        def log2(x:int|float):
            """
            `math.log2(...)` equivalent
            """
        @staticmethod
        def log10(x:int|float):
            """
            `math.log10(...)` equivalent
            """
        @staticmethod
        def log1p(x:int|float):
            """
            `math.log1p(...)` equivalent
            """
        @staticmethod
        def sin(x:int|float):
            """
            `math.sin(...)` equivalent
            """
        @staticmethod
        def cos(x:int|float):
            """
            `math.cos(...)` equivalent
            """
        @staticmethod
        def tan(x:int|float):
            """
            `math.tan(...)` equivalent
            """
        @staticmethod
        def asin(x:int|float):
            """
            `math.asin(...)` equivalent
            """
        @staticmethod
        def acos(x:int|float):
            """
            `math.acos(...)` equivalent
            """
        @staticmethod
        def atan(x:int|float):
            """
            `math.atan(...)` equivalent
            """
        @staticmethod
        def atan2(a:int|float, b:int|float):
            """
            `math.atan2(...)` equivalent
            """
        @staticmethod
        def hypot(a:int|float, b:int|float):
            """
            `math.hypot(...)` equivalent
            """
        @staticmethod
        def degrees(x:int|float):
            """
            `math.degrees(...)` equivalent
            """
        @staticmethod
        def radians(x:int|float):
            """
            `math.radians(...)` equivalent
            """
        @staticmethod
        def sinh(x:int|float):
            """
            `math.sinh(...)` equivalent
            """
        @staticmethod
        def cosh(x:int|float):
            """
            `math.cosh(...)` equivalent
            """
        @staticmethod
        def tanh(x:int|float):
            """
            `math.tanh(...)` equivalent
            """
        @staticmethod
        def ldexp(a:int|float, b:int|float):
            """
            `math.ldexp(...)` equivalent
            """
        @staticmethod
        def nextafter(a:int|float, b:int|float):
            """
            `math.nextafter(...)` equivalent
            """
        @staticmethod
        def ulp(x:int|float):
            """
            `math.ulp(...)` equivalent
            """
        @staticmethod
        def fma(a:int|float, b:int|float, c:int|float):
            """
            `math.fma(...)` equivalent
            """
    class map:
        @staticmethod
        def __new__(cls, callable, iterable) -> list:
            """
            Similar to pythons `map`, but returns a list instead of an iterator
            """
    class random:
        """
        Provides a small subset of the functionality of the `random` library

        Note: output is not guaranteed to be exact with the `random` library
        """
        @staticmethod
        def random() -> float:
            """
            `random.random()` equivalent
            """
        @staticmethod
        def randint(a:int, b:int) -> int:
            """
            `random.randint(...)` equivalent
            """
        @staticmethod
        def randrange(a:int, b:int=None) -> int:
            """
            `random.randrange(..., steps=1)` equivalent
            """
        @staticmethod
        def uniform(a:int|float, b:int|float) -> float:
            """
            `random.uniform(...)` equivalent
            """
        @staticmethod
        def choice(iterable:list|tuple) -> any:
            """
            `random.choice(...)` equivalent
            """
        @staticmethod
        def shuffle(iterable:list|tuple) -> list:
            """
            `random.shuffle(...)` equivalent
            """
        @staticmethod
        def gauss(mu, sigma):
            """
            `random.gauss(...)` equivalent
            """
        @staticmethod
        def seed(x:int=None):
            """
            `random.seed(...)` equivalent
            """
    class threading:
        """
        Provides a small subset of the functionality of the `threading` library

        Note: output is not guaranteed to be exact with the `threading` library

        Note2: the `Thread` class is not part of this, but rather is another class you need to import
        """
        @staticmethod
        def current_thread():
            """
            `threading.current_thread()` equivalent
            """
        @staticmethod
        def main_thread():
            """
            `threading.main_thread()` equivalent

            Note: Always points to the thread the module was loaded from, rather than the actual main thread
            """
        @staticmethod
        def active_count():
            """
            `threading.active_count()` equivalent
            """
        @staticmethod
        def enumerate():
            """
            `threading.enumerate()` equivalent
            """
        @staticmethod
        def get_ident():
            """
            `threading.get_ident()` equivalent
            """
        @staticmethod
        def get_native_id():
            """
            `threading.get_native_id()` equivalent
            """
    class Thread:
        """
        Provides a subset of the functionality of the `threading.Thread` class

        Note: output is not guaranteed to be exact with the `threading` library

        Note2: the thread will keep running even after the script is killed
        """
        def __init__(self, *, target=None, name=None, args=[], kwargs={}, daemon=None):
            """
            `threading.Thread(...)` equivalent
            """
        def start(self):
            """
            `threading.Thread.start()` equivalent
            """
        def run(self):
            """
            `threading.Thread.run()` equivalent
            """
        def join(self):
            """
            `threading.Thread.join()` equivalent
            """
        def is_alive(self):
            """
            `threading.Thread.is_alive()` equivalent
            """
        def set_name(self, name):
            """
            `threading.Thread.name = ...` equivalent
            """
        def set_daemon(self, state):
            """
            `threading.Thread.daemon = ...` equivalent
            """
        def get_ident(self):
            """
            `threading.Thread.ident` equivalent
            """
        def get_native_id(self):
            """
            `threading.Thread.native_id` equivalent
            """
    class Lock:
        """
        Provides a subset of the functionality of the `threading.Lock` class

        Note: output is not guaranteed to be exact with the `threading` library
        """
        def __init__(self):
            """
            `threading.Lock()` equivalent
            """
        def acquire(self):
            """
            `threading.Lock.acquire()` equivalent
            """
        def release(self):
            """
            `threading.Lock.release()` equivalent
            """
    class time:
        """
        Provides a small subset of the functionality of the `time` library

        Note: output is not guaranteed to be exact with the `time` library
        """
        @staticmethod
        def sleep(time:int|float):
            """
            `time.sleep(...)` equivalent

            Smallest possible sleep time is `0.001` (or `1ms`)
            """
        @staticmethod
        def perf_counter():
            """
            `time.perf_counter()` equivalent
            """
        @staticmethod
        def perf_counter_ns():
            """
            `time.perf_counter_ns()` equivalent
            """
        @staticmethod
        def time():
            """
            `time.time()` equivalent
            """
    class asyncio:
        """
        Provides a small subset of the functionality of the `asyncio` library

        Note: output is not guaranteed to be exact with the `asyncio` library
        """
        def run(coro):
            """
            `asyncio.run(...)` equivalent

            Does not block
            """
        def sleep(time):
            """
            `asyncio.sleep(...)` equivalent
            """
    class socket:
        """
        Not a recreation of the `socket.socket` class, but rather a custom helper class to help with sockets
        """
        def __init__(self): pass
        def bind(host,port):
            """
            Binds this socket to a host and a port
            """
        def ready(self) -> bool:
            """
            Returns wether this socket has something to read
            """
        def read_line(self) -> str|None:
            """
            Reads 1 line, delimeted by `\n`

            Returns `None` if there wasnt a full line of data
            """
        def write(self, data:str):
            """
            Writes data to the socket, that can be read externally
            """
        def flush(self):
            """
            Flushes the write buffer
            """
    class Queue:
        """
        Provides a small subset of the functionality of the `queue.Queue` class

        Note: output is not guaranteed to be exact with the `queue` library
        """
        def __init__(self):
            """
            `queue.Queue()` equivalent
            """
        def put(self, item, block=True, timeout:int|float=0):
            """
            `queue.Queue.put(...)` equivalent
            """
        def put_nowait(self, item):
            """
            `queue.Queue.put_nowait(...)` equivalent
            """
        def get(self, block=True, timeout:int|float=0) -> any:
            """
            `queue.Queue.get(...)` equivalent
            """
        def get_nowait(self) -> any:
            """
            `queue.Queue.get_nowait()` equivalent
            """
        def empty(self) -> bool:
            """
            `queue.Queue.empty()` equivalent
            """
        def qsize(self) -> int:
            """
            `queue.Queue.qsize()` equivalent
            """

