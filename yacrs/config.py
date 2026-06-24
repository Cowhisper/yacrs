import copy
import inspect
import json
import sys
from argparse import ArgumentParser
from functools import wraps

import toml
import yaml


class Node(dict):
    def __init__(self, init_dict=None, freeze=False):
        init_dict = {} if init_dict is None else init_dict
        super().__init__(init_dict)
        self.__dict__["__immutable__"] = freeze

    def is_frozen(self):
        return self.__dict__["__immutable__"]

    def freeze(self, freeze=True):
        self.__dict__["__immutable__"] = freeze
        for v in self.values():
            if isinstance(v, Node):
                v.freeze(freeze)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self.set(key, value)

    def get(self, key):
        node = self
        segments = key.split(".")
        for seg in segments[:-1]:
            if seg not in node or not isinstance(node[seg], Node):
                raise AttributeError(
                    "No such attribute '{}' in config node".format(key)
                )
            node = node[seg]
        last = segments[-1]
        if last not in node:
            raise AttributeError("No such attribute '{}' in config node".format(key))
        return node[last]

    def set(self, key, value, do_register=True):
        if self.is_frozen():
            raise AttributeError("Attempted to modify on a frozen config node")
        segments = key.split(".")
        if len(segments) == 1:
            self[segments[0]] = value
            return
        node = self
        for seg in segments[:-1]:
            if seg not in node:
                if do_register:
                    node[seg] = Node()
                else:
                    raise AttributeError(f"{seg} does not exist")
            elif not isinstance(node[seg], Node):
                raise AttributeError(f"{seg} is not a Node")
            node = node[seg]
        node[segments[-1]] = value

    def has(self, key):
        node = self
        segments = key.split(".")
        for seg in segments[:-1]:
            if seg not in node or not isinstance(node[seg], Node):
                return False
            node = node[seg]
        return segments[-1] in node

    def register(self, key):
        if self.is_frozen():
            raise AttributeError("Attempted to modify on a frozen config node")
        node = self
        for seg in key.split("."):
            if seg not in node:
                node[seg] = Node()
            elif not isinstance(node[seg], Node):
                raise AttributeError(f"{seg} is not a Node")
            node = node[seg]

    def update(self, *args, **kwargs):
        def _convert(value):
            if isinstance(value, dict) and not isinstance(value, Node):
                node = Node()
                for kk, vv in value.items():
                    node[kk] = _convert(vv)
                return node
            return value

        if self.is_frozen():
            raise AttributeError("Attempted to modify on a frozen config node")
        if args:
            other = args[0]
            if hasattr(other, "keys"):
                for k, v in other.items():
                    self[k] = _convert(v)
            else:
                for k, v in other:
                    self[k] = _convert(v)
        for k, v in kwargs.items():
            self[k] = _convert(v)

    def clone(self):
        return copy.deepcopy(self)

    def pprint(self, skip_prefix="_"):
        # print in yaml format
        lines = []

        def _recursive(cfg, indent=0):
            for k, v in cfg.items():
                if k.startswith(skip_prefix):
                    continue
                if isinstance(v, Node):
                    lines.append(" " * indent + k + ":")
                    _recursive(v, indent + 2)
                else:
                    lines.append(" " * indent + k + ": " + str(v))

        _recursive(self)
        return "\n".join(lines) + "\n" if lines else ""

    def delete(self, key):
        node = self
        segments = key.split(".")
        for seg in segments[:-1]:
            if seg not in node:
                raise AttributeError(f"{seg} does not exist")
            if not isinstance(node[seg], Node):
                raise AttributeError(f"{seg} is not a Node")
            node = node[seg]
        last = segments[-1]
        if last not in node:
            raise AttributeError(f"{last} does not exist")
        del node[last]


_C = Node()
_C._configurables = Node()
_C._registry = Node()


class configurable:
    UNDBIND = "_"

    def __init__(self, scope=None):
        self.scope = scope

    def do_register(self, func):
        scope = self.scope
        signature = inspect.signature(func)
        cls_name = func.__qualname__.split(".")[0]

        kwargs = {}
        defaultv = {}
        args = []
        for name, param in signature.parameters.items():
            if isinstance(param.annotation, str):
                if param.annotation.startswith("."):
                    annotation = param.annotation[1:]
                else:
                    annotation = param.annotation
            else:
                annotation = name
            if scope is not None:
                annotation = scope + "." + annotation
            kwargs[name] = annotation
            defaultv[name] = param.default
            args.append(name)

        _C._configurables[cls_name] = Node(
            {"kwargs": kwargs, "defaultv": defaultv, "args": args}, freeze=True
        )
        _C._registry[cls_name] = func

    def register(self, func):
        cls_name = func.__qualname__.split(".")[0]
        if self.scope is None:
            self.scope = cls_name
        self.do_register(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_info = _C._configurables[cls_name].clone()
            default_kwargs = func_info["kwargs"]
            default_values = func_info["defaultv"]
            args_names = func_info["args"]

            for k, v in zip(args_names, args):
                kwargs[k] = v

            dkwargs = {}
            for k, v in default_kwargs.items():
                vs = v.split(".")
                if vs[0] == configurable.UNDBIND:
                    vs[0] = self.scope
                v = ".".join(vs)
                if _C.has(v):
                    dkwargs[k] = _C.get(v)
                elif default_values[k] != inspect._empty:
                    dkwargs[k] = default_values[k]
                else:
                    # do nothing, let func call raise Error
                    pass
            dkwargs.update(kwargs)
            return func(**dkwargs)

        return wrapper

    def __call__(self, func):
        if isinstance(func, str):
            if func not in _C._registry:
                raise KeyError(f"Unregist module name: {func}.")
            func = _C._registry[func]
        if "__wrapped__" in func.__dict__:
            func = func.__wrapped__
        cls_name = func.__qualname__.split(".")[0]
        if self.scope is None:
            self.scope = cls_name

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_info = _C._configurables[cls_name].clone()
            default_kwargs = func_info["kwargs"]
            default_values = func_info["defaultv"]
            args_names = func_info["args"]

            for k, v in zip(args_names, args):
                kwargs[k] = v

            dkwargs = {}
            for k, v in default_kwargs.items():
                vs = v.split(".")
                if vs[0] == configurable.UNDBIND:
                    vs[0] = self.scope
                v = ".".join(vs)
                if _C.has(v):
                    dkwargs[k] = _C.get(v)
                elif default_values[k] != inspect._empty:
                    dkwargs[k] = default_values[k]
                else:
                    # do nothing, let func call raise Error
                    pass
            dkwargs.update(kwargs)
            return func(**dkwargs)

        return wrapper

    def cli(self, func):
        parser = ArgumentParser()
        parser.add_argument("--config", "-c", type=str, default=None)
        parser.add_argument("--verbose", "-v", action="store_true")
        parser.add_argument("options", nargs="*")
        args = parser.parse_args()
        if args.config:
            if args.config.endswith(".json"):
                d = json.load(open(args.config))
            elif args.config.endswith(".yaml") or args.config.endswith(".yml"):
                d = yaml.load(open(args.config), Loader=yaml.FullLoader)
            elif args.config.endswith(".toml"):
                d = toml.load(open(args.config))
            else:
                raise ValueError(f"Unsupported config file type: {args.config}")
            _C.update(d)

        for opt in args.options:
            if "=" not in opt:
                continue
            k, v = opt.split("=")
            if ":" in k:
                k, dtype = k.split(":", 1)
                try:
                    v = eval(dtype)(v)
                except Exception:
                    raise TypeError(f"Cannot convert {v} to {dtype}")
            _C.set(k, v)
        return self(func)


def merge_from_sys_argv():
    for opt in sys.argv[1:]:
        if "=" not in opt:
            continue
        k, v = opt.split("=", 1)
        if ":" in k:
            k, dtype = k.split(":", 1)
            try:
                v = eval(dtype)(v)
            except Exception:
                raise TypeError(f"Cannot convert {v} to {dtype}")
        else:
            try:
                v = eval(v)
            except Exception:
                pass
        _C.set(k, v)


def register(scope=None):
    """Python 3.8-compatible shorthand for ``@configurable(scope).register``."""

    def wrapper(func):
        return configurable(scope=scope).register(func=func)

    return wrapper


def cli(scope=None):
    """Python 3.8-compatible shorthand for ``@configurable(scope).cli``."""

    def wrapper(func):
        return configurable(scope=scope).cli(func=func)

    return wrapper
