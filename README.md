# YACRS: Yet Another Configuration and Registration System

YACRS is a lightweight Python configuration system that maps configuration values directly to class or function arguments. It is inspired by [YACS](https://github.com/rbgirshick/yacs) but adds a decorator-based registration and binding mechanism so you can wire configs to existing code without writing boilerplate mapping logic.

## Philosophy
Get rid of the configuration value mapping in code blocks.

## Features

- **Hierarchical config nodes** — `Node` extends `dict` and supports dotted-key access (e.g. `cfg.model.lr`).
- **Auto-vivification** — Nested paths are created on demand.
- **Immutable snapshots** — Freeze a config tree to prevent accidental changes.
- **Decorator-based binding** — `@configurable` maps config values to function/class `__init__` arguments.
- **Scope binding** — Bind the same class/function to different config scopes.
- **CLI support** — Load JSON/YAML/TOML configs and override values from the command line.

## Installation

```bash
pip install yacrs
```

Or install from source:

```bash
git clone https://github.com/Cowhisper/yacrs.git
cd yacrs
pip install -e .
```

## Quick Start

```python
from yacrs import configurable, _C

# 1. Register a class with a config scope
@configurable('model').register
class Model:
    def __init__(self, input_channels, output_channels):
        self.input_channels = input_channels
        self.output_channels = output_channels

# 2. Create config entries
_C.register('model')
_C.model.input_channels = 3
_C.model.output_channels = 32

# 3. Instantiate from config
model = Model()
print(model.input_channels)  # 3
print(model.output_channels)  # 32
```

See [`tutorial.md`](tutorial.md) for a complete walkthrough.

## Core Concepts

### `Node`

A `Node` is a dictionary that supports attribute-style and dotted-key access:

```python
from yacrs import Node

cfg = Node()
cfg.model = Node()
cfg.model.lr = 0.01
cfg.set('model.optimizer', 'Adam')

print(cfg.get('model.lr'))  # 0.01
print(cfg.model.optimizer)  # Adam
```

### `_C` — Global Config

`_C` is the package-wide root `Node`. It is where `@configurable` looks up values by default.

### `@configurable`

The `configurable` decorator registers a class or function and binds its parameters to config values at call time.

```python
from yacrs import configurable, _C

@configurable('train').register
def train(epoch, lr, model):
    print(f'Training {model} for {epoch} epochs at lr={lr}')

_C.register('train')
_C.train.epoch = 10
_C.train.lr = 0.001
_C.train.model = 'resnet50'

train()  # Training resnet50 for 10 epochs at lr=0.001
```

### CLI

Use `configurable(...).cli` to load config files and override values from the command line:

```bash
python train.py -c config.yaml train.epoch=20 train.lr=0.01
```

See [`tutorial.md`](tutorial.md) for details on CLI usage and config file formats.

## License

MIT
