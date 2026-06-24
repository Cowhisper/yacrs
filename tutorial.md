# YACRS Tutorial

This tutorial covers the core features of YACRS: hierarchical config nodes, the `configurable` decorator, scope binding, and CLI usage.

## Table of Contents

1. [Working with `Node`](#working-with-node)
2. [The Global Config `_C`](#the-global-config-_c)
3. [Binding Code to Config with `@configurable`](#binding-code-to-config-with-configurable)
4. [Scopes and Unbound Registrations](#scopes-and-unbound-registrations)
5. [Command Line Interface](#command-line-interface)
6. [Complete Example](#complete-example)

---

## Working with `Node`

`Node` is the basic building block of YACRS. It behaves like a Python `dict` but also supports attribute-style access and dotted keys.

### Creating a Node

```python
from yacrs import Node

# Empty node
cfg = Node()

# From a dictionary
cfg = Node({'model': {'lr': 0.01}, 'train': {'epoch': 10}})
```

### Accessing Values

You can use dictionary syntax, attribute syntax, or dotted keys:

```python
cfg = Node()
cfg['model'] = Node()
cfg['model']['lr'] = 0.01

# Attribute access
print(cfg.model.lr)  # 0.01

# Dotted-key access
print(cfg.get('model.lr'))  # 0.01
cfg.set('model.optimizer', 'Adam')
print(cfg.has('model.optimizer'))  # True
```

### Nested Auto-Registration

When you `set` a dotted key, intermediate `Node`s are created automatically:

```python
cfg = Node()
cfg.set('a.b.c.d', 'deep')
print(cfg.a.b.c.d)  # deep
```

If you want to create nested nodes without assigning a value, use `register`:

```python
cfg = Node()
cfg.register('data.train')
cfg.data.train.batch_size = 32
```

### Freezing

Freeze a node (and all nested nodes) to make it read-only:

```python
cfg = Node()
cfg.model = Node()
cfg.model.lr = 0.01
cfg.freeze(True)

# This raises AttributeError
cfg.model.lr = 0.02
```

Unfreeze with `cfg.freeze(False)`.

### Cloning and Pretty Printing

```python
cfg = Node({'model': {'lr': 0.01}})
copy = cfg.clone()  # deep copy

print(cfg.pprint())
# model:
#   lr: 0.01
```

Keys starting with `_` are skipped by `pprint` by default.

---

## The Global Config `_C`

`_C` is the package-wide root `Node`. The `configurable` decorator looks up values there by default.

```python
from yacrs import _C

_C.register('model')
_C.model.lr = 0.01

print(_C.get('model.lr'))  # 0.01
```

You can also merge command-line options into `_C`:

```python
from yacrs import merge_from_sys_argv

merge_from_sys_argv()
print(_C.model.lr)
```

`merge_from_sys_argv` reads `sys.argv[1:]`, parses `key=value` pairs, and sets them on `_C`. It automatically evaluates literal values (`1`, `True`, `[1, 2]`) and supports explicit type hints (`key:int=42`).

---

## Binding Code to Config with `@configurable`

The `configurable` decorator connects a class or function to a config scope.

### Basic Registration

```python
from yacrs import configurable, _C

@configurable('model').register
class Model:
    def __init__(self, input_channels, output_channels):
        self.input_channels = input_channels
        self.output_channels = output_channels

_C.register('model')
_C.model.input_channels = 3
_C.model.output_channels = 32

model = Model()
print(model.input_channels)   # 3
print(model.output_channels)  # 32
```

When you call `Model()`, the wrapper looks up `model.input_channels` and `model.output_channels` in `_C`. If a value is missing, the parameter's default is used; if there is no default, a `TypeError` is raised.

### Registration Without Explicit Scope

If you omit the scope, it is inferred from the class or function name:

```python
@configurable().register
class Optimizer:
    def __init__(self, lr):
        self.lr = lr

_C.register('Optimizer')
_C.Optimizer.lr = 0.001

opt = Optimizer()
```

### Convenience Decorator `cregister`

`cregister` is a shorthand for `configurable(...).register`:

```python
from yacrs import cregister, _C

@cregister('model')
class Model:
    def __init__(self, input_channels):
        self.input_channels = input_channels

_C.register('model')
_C.model.input_channels = 3

model = Model()
```

---

## Scopes and Unbound Registrations

### Reusing a Class with Different Scopes

Sometimes the same class should be instantiated with different config scopes. Use the unbind constant `configurable.UNDBIND` (or `cregister()` without a scope) to register without binding, then bind later:

```python
from yacrs import configurable, _C

@configurable(configurable.UNDBIND).register
class Model:
    def __init__(self, input_channels, output_channels=10):
        self.input_channels = input_channels
        self.output_channels = output_channels

_C.register('l1')
_C.l1.input_channels = 1
_C.l1.output_channels = 2

_C.register('l2')
_C.l2.input_channels = 3
_C.l2.output_channels = 4

model1 = configurable('l1')(Model)()
model2 = configurable('l2')(Model)()

print(model1.input_channels)  # 1
print(model2.input_channels)  # 3
```

You can also bind by registered name:

```python
model2 = configurable('l2')('Model')()
```

### String Annotations

Parameter annotations can be strings. A leading `.` means the rest of the name is relative to the scope; otherwise it is used as-is:

```python
@configurable('model').register
class Model:
    def __init__(self, lr: '.optimizer.lr'):
        self.lr = lr

_C.register('model')
_C.model.optimizer = Node()
_C.model.optimizer.lr = 0.01

model = Model()
print(model.lr)  # 0.01
```

If the annotation is not a string, the parameter name is used as the config key.

---

## Command Line Interface

`configurable(...).cli` turns a function into a CLI entry point. It supports loading JSON, YAML, and TOML config files and overriding values from the command line.

### Example Function

```python
from yacrs import configurable

@configurable('train').cli
@configurable('train').register
def train(epoch, lr, model='resnet18'):
    print(f'Training {model} for {epoch} epochs at lr={lr}')

if __name__ == '__main__':
    train()
```

### Usage

```bash
# Options only
python train.py train.epoch=10 train.lr=0.001 train.model=resnet50

# Load a config file and override values
python train.py -c config.yaml train.epoch=20
```

### Type Hints on the Command Line

Use `:` to specify a type for command-line values:

```bash
python train.py train.epoch:int=10 train.lr:float=0.001
```

### Config File Formats

A YAML config file might look like this:

```yaml
train:
  epoch: 10
  lr: 0.001
  model: resnet50
```

Load it with:

```bash
python train.py -c config.yaml
```

---

## Complete Example

The following example shows how to wire a training script together with config files and decorators.

### `config.yaml`

```yaml
train:
  epoch: 10
  lr: 0.01
  dataset: TrainDataset
  model: torchvision.resnet50

TrainDataset:
  data_files:
    - a.txt
    - b.txt
  mean: [0.5, 0.5, 0.5]
  std: [0.5, 0.5, 0.5]

torchvision:
  resnet50:
    num_classes: 10
    zero_init_residual: false
```

### `train.py`

```python
from torchvision.models import resnet50
from yacrs import configurable, _C, Node
import yaml


@configurable('torchvision.resnet50').register
def build_resnet50(num_classes, zero_init_residual=False):
    model = resnet50(num_classes=num_classes)
    # configure zero_init_residual if needed
    return model


@configurable().register
class TrainDataset:
    def __init__(self, data_files, mean, std):
        self.data_files = data_files
        self.mean = mean
        self.std = std


@configurable('train').cli
@configurable('train').register
def train(epoch, lr, dataset, model):
    dataset = configurable()(dataset)()
    model = configurable()(model)(num_classes=10)
    print(f'Train {epoch} epochs, lr={lr}')
    print(f'Dataset files: {dataset.data_files}')
    print(f'Model: {model}')


if __name__ == '__main__':
    train()
```

### Run It

```bash
python train.py -c config.yaml
```

This loads the YAML file into `_C`, resolves `train.dataset` and `train.model`, and instantiates the dataset and model from their respective config scopes.

---

## Summary

- Use `Node` for hierarchical, dotted-key configs.
- Use `_C` as the global config root.
- Use `@configurable(scope).register` to bind classes/functions to config scopes.
- Use `configurable.UNDBIND` to register reusable building blocks.
- Use `configurable(...).cli` for config-file and command-line driven scripts.

For API details, see the source code in `yacrs/config.py`.
