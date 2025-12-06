import sys
import copy
import inspect
import json
import yaml
import toml
from functools import wraps
from argparse import ArgumentParser


class Node(dict):
    def __init__(self, init_dict=None, freeze=False):
        init_dict = {} if init_dict is None else init_dict
        super(Node, self).__init__(init_dict)
        self.__dict__['__immutable__'] = freeze

    def is_frozen(self):
        return self.__dict__['__immutable__']

    def freeze(self, freeze=True):
        self.__dict__['__immutable__'] = freeze
        for v in self.__dict__.values():
            if isinstance(v, Node):
                v.freeze(freeze)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self.set(key, value)

    def get(self, key):
        if not self.has(key):
            raise AttributeError(
                "No such attribute '{}' in config node".format(key)
            )
        ksegments = key.split('.')
        if len(ksegments) == 1:
            return self[ksegments[0]]
        else:
            k_suffix = '.'.join(ksegments[1:])
            return self[ksegments[0]].get(k_suffix)

    def set(self, key, value, do_register=True):
        if self.is_frozen():
            raise AttributeError(
                "Attempted to modify on a frozen config node"
            )
        ksegments = key.split('.')
        if len(ksegments) == 1:
            self[ksegments[0]] = value
            return
        else:
            key_prefix = '.'.join(ksegments[:-1])
            if not self.has(key_prefix) and do_register:
                self.register(key_prefix)
            node = self.get(key_prefix)
            if isinstance(node, Node):
                node[ksegments[-1]] = value
            else:
                raise AttributeError(f"{key_prefix} is not a Node")
            return

    def has(self, key):
        ksegments = key.split('.')
        if len(ksegments) == 1:
            return ksegments[0] in self
        else:
            if ksegments[0] not in self:
                return False
            if isinstance(self[ksegments[0]], Node):
                k_suffix = '.'.join(ksegments[1:])
                return self[ksegments[0]].has(k_suffix)
            else:
                return False

    def register(self, key):
        if self.is_frozen():
            raise AttributeError(
                "Attempted to modify on a frozen config node"
            )
        ksegments = key.split('.')
        if len(ksegments) > 1:
            if ksegments[0] not in self:
                self[ksegments[0]] = Node()
            if isinstance(self[ksegments[0]], Node):
                self[ksegments[0]].register('.'.join(ksegments[1:]))
            else:
                raise AttributeError(f'{ksegments[0]} is not a Node')
        else:
            self[key] = Node()

    def clone(self):
        return copy.deepcopy(self)

    def pprint(self, skip_prefix='_'):
        # print in yaml format
        def _recursive(cfg, indent=0):
            s = ''
            for k, v in cfg.items():
                if k.startswith(skip_prefix):
                    continue
                if isinstance(v, Node):
                    s += ' ' * indent + k + ':\n'
                    s += _recursive(v, indent + 2)
                else:
                    s += ' ' * indent + k + ': ' + str(v) + '\n'
            return s
        return _recursive(self)

    def delete(self, key):
        ksegments = key.split('.')
        if ksegments[0] not in self:
            raise AttributeError(f'{ksegments[0]} does not exist')
        if len(ksegments) == 1:
            del self[ksegments[0]]
        else:
            if isinstance(self[ksegments[0]], Node):
                self[ksegments[0]].delete('.'.join(ksegments[1:]))
            else:
                raise AttributeError(f'{ksegments[0]} is not a Node')


_C = Node()
_C._configurables = Node()
_C._registry = Node()


class configurable:
    UNDBIND = '_'
    def __init__(self, scope=None):
        self.scope = scope
        
    def do_register(self, func):
        scope = self.scope
        signature = inspect.signature(func)
        cls_name = func.__qualname__.split('.')[0]
        
        kwargs = {}
        defaultv = {}
        args = []
        for name, param in signature.parameters.items():
            if isinstance(param.annotation, str):
                if param.annotation.startswith('.'):
                    annotation = param.annotation[1:]
                else:
                    annotation = param.annotation
            else:
                annotation = name
            if scope is not None:
                annotation = scope + '.' + annotation
            kwargs[name] = annotation
            defaultv[name] = param.default
            args.append(name)

        _C._configurables[cls_name] = Node(
            {
                'kwargs': kwargs,
                'defaultv': defaultv,
                'args': args
            }
            , freeze=True)
        _C._registry[cls_name] = func

    def register(self, func):
        cls_name = func.__qualname__.split('.')[0]
        if self.scope is None:
            self.scope = cls_name
        self.do_register(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_info = _C._configurables[cls_name].clone()
            default_kwargs = func_info['kwargs']
            default_values = func_info['defaultv']
            args_names = func_info['args']

            for k, v in zip(args_names, args):
                kwargs[k] = v

            dkwargs = {}
            for k, v in default_kwargs.items():
                vs = v.split('.')
                if vs[0] == configurable.UNDBIND:
                    vs[0] = self.scope
                v = '.'.join(vs)
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
                raise KeyError(f'Unregist module name: {func}.')
            func = _C._registry[func]
        if '__wrapped__' in func.__dict__:
            func = func.__wrapped__
        cls_name = func.__qualname__.split('.')[0]
        if self.scope is None:
            self.scope = cls_name
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_info = _C._configurables[cls_name].clone()
            default_kwargs = func_info['kwargs']
            default_values = func_info['defaultv']
            args_names = func_info['args']

            for k, v in zip(args_names, args):
                kwargs[k] = v

            dkwargs = {}
            for k, v in default_kwargs.items():
                vs = v.split('.')
                if vs[0] == configurable.UNDBIND:
                    vs[0] = self.scope
                v = '.'.join(vs)
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
        parser.add_argument('--config', '-c', type=str, default=None)
        parser.add_argument('--verbose', '-v', action='store_true')
        parser.add_argument('options', nargs="*")
        args = parser.parse_args()
        if args.config:
            if args.config.endswith('.json'):
                d = json.load(open(args.config))
            elif args.config.endswith('.yaml') or args.config.endswith('.yml'):
                d = yaml.load(open(args.config), Loader=yaml.FullLoader)
            elif args.config.endswith('.toml'):
                d = toml.load(open(args.config))
            else:
                raise ValueError(f'Unsupported config file type: {args.config}')
            _C.update(d)

        for opt in args.options:
            if '=' not in opt:
                continue
            k, v = opt.split('=')
            if ":" in k:
                k, dtype = k.split(":", 1)
                try:
                    v = eval(dtype)(v)
                except:
                    raise TypeError(f"Cannot convert {v} to {dtype}")
            _C.set(k, v)
        return self(func)


def cregister(scope=None):
    def wrapper(func):
        return configurable(scope=scope).register(func=func)
    return wrapper