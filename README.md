# YACRS: Yet Anothor Configuration and Registration System

## Why YACRS?
There are hundreds of configuration system package for python. `YACS` (by @rbgirshick) is a great one especially for DeepLearnig projects.
Many famous projects' configuration system is based on `YACS`. Such as Detectron2, fvcore, etc. However, even if yasc is a handy and reliable
configuration system, it still has some inconvenience. `YASC` keep all information in `CfgNode` which leads to an unsolved issue, how to gracefully
map these information to an existing code (funciton or class). For instance

```python
import torch
from yacs.config import CfgNode


class Model(torch.nn.Module):
    def __init__(self, input_channels, output_channels):
        self.net = torch.nn.Linear(input_channels, output_channels)

    @staticmethod
    def from_config(cfg):
        return Model(
            input_channels=cfg.input_channels,
            output_channels=cfg.output_channels
        )

cfg = CfgNode({'input_channels': 3, 'output_channels': 32})

# Option 1, do arguments mapping in main loop
model = Model(
    input_channels=cfg.input_channels,
    output_channels=cfg.output_channels
)

# Option 2, do some extra coding in class defination. Define a staticmethod in class.
model = Model.from_config(cfg)
```

YACRS is offers a more convenient way
```python
# Option 3, use yacrs!
import torch
from yacrs import configurable, _C

# ----------------------------------------------------------------

_C.register('Model1')
_C.Model1.input_channels = 1
_C.Model1.output_channels = 2

# register module with specific scope

@configurable().register  # equal  @configurable(scope='Model1').register
class Model1(torch.nn.Module):
    def __init__(self, input_channels, output_channels):
        super().__init__()
        self.net = torch.nn.Linear(input_channels, output_channels)

model = Model1()

# ----------------------------------------------------------------

_C.register('l1')
_C.register('l2')
_C.l1.input_channels = 1
_C.l1.output_channels = 2
_C.l2.input_channels = 3
_C.l2.output_channels = 4

# register module with unbind scope

@configurable(configurable.UNBIND).register
class Model2(torch.nn.Module):
    def __init__(self, input_channels, output_channels=10):
        super().__init__()
        self.net = torch.nn.Linear(input_channels, output_channels)

# use configurable to bind scope 'l1' and 'l2' to Model2 class separately

model1 = configurable('l1')(Model2)()
model2 = configurable('l2')('Model2')() # both class and class name would work

# you can overwrite augments by passing args or kwargs
# augments priority args/kwargs > bind node > default value
model1 = configurable('l1')(Model2)(3, output_channels=1024)
```

## Example
write a `config.yaml` for training.
```yaml
train:
    epoch: 10
    lr: 0.01
    scheduler: 'ExponentialLR'
    optimizer: 'SGD'
    dataset: 'TrainDataset'
    model: 'torchvision.resnet50'

TrainDataset:
    data_files:
        - a.txt
        - b.txt
    mean: [0.5, 0.5, 0.5]
    std: [0.5, 0.5, 0.5]

torchvision:
    resnet50:
        num_classes:
        zero_init_residual: false


ExponentialLR:
    gamma: 0.9

SGD:
    momentum: 0.9

```

Training script
```python
import torch
from torchvision.models import resnet50
from yacrs import configurable, _C, Node

# register module
configurable('torchvision.resnet50').register(resnet50)
configurable('ExponentialLR').register(torch.optim.lr_scheduler.ExponentialLR)
configurable('SGD').register(torch.optim.SGD)

@configurable().register
class TrainDataset(torch.utils.data.Dataset):
    def __init__(self, data_files, mean, std):
        super().__init__()
        pass


@configurable().register
def train(
    epoch,
    lr,
    scheduler,
    optimizer,
    dataset,
    model,
):
    dataset = configurable()(dataset)()
    model = configurable()(model)(num_classes=dataset.num_classes)
    opt = configurable()(optimizer)(model.parameters(), lr=lr)
    sch = configurable()(scheduler)(optimizer)

    for i in range(epoch):
        ...


if __name__ == '__main__':
    import yaml

    with open("config.yaml") as stream:
        cfg_json = yaml.safe_load(stream)
        cfg = Node(cfg_json)
    _C.update(cfg)

    # print global config
    print(_C.pprint())

    train()
```

## Install
```bash
pip install yacrs
```
