import pytest
import sys
sys.path.append('.')
print(sys.path)
from yacrs.config import Node, configurable, merge_from_sys_argv, cregister
from yacrs.config import _C as CFG


# write pytest test case of XCfgNode

def test_xcfgnode():
    node = Node({'a': 1})
    assert node.get('a') == 1
    
    node.set('b', 2)
    assert node.get('b') == 2
    
    node.freeze(True)
    assert node.is_frozen()

    with pytest.raises(AttributeError):
        node.set('c', 3)

    node.freeze(False)
    with pytest.raises(AttributeError):
        node.set('a.b.c', 3, True)

    with pytest.raises(AttributeError):
        node.set('x.y', 3, False)

    node.delete('a')
    assert node.has('a') is False

    node.register('a.b.c')
    assert isinstance(node.get('a.b.c'), Node)

    node.set('q.p.r', 2, True)
    assert node.q.p.r == 2

    node_new = node.clone()
    assert node_new == node

    text = node.pprint()
    result = """
b: 2
a:
  b:
    c:
q:
  p:
    r: 2
""".strip()
    assert text.strip() == result


@configurable(configurable.UNDBIND).register
class ExampleClass1(object):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    @property
    def c(self):
        return self.a + self.b
    
    @staticmethod
    def d():
        return 1
    
    def __call__(self, c):
        return self.a + self.b + c
    

@configurable('model_2').register
class ExampleClass2(object):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    @property
    def c(self):
        return self.a + self.b
    
    @staticmethod
    def d():
        return 1
    
    def __call__(self, c):
        return self.a + self.b + c
    

@configurable().register
class ExampleClass3(object):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    @property
    def c(self):
        return self.a + self.b
    
    @staticmethod
    def d():
        return 1
    
    def __call__(self, c):
        return self.a + self.b + c


@cregister()
class ExampleClass4(object):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    @property
    def c(self):
        return self.a + self.b
    
    @staticmethod
    def d():
        return 1
    
    def __call__(self, c):
        return self.a + self.b + c


def test_configurable_unbind():
    CFG.register('model_1')
    CFG.model_1.a = 1
    CFG.model_1.b = 2
    ec = configurable('model_1')(ExampleClass1)()
    assert ec.__class__.__name__ == 'ExampleClass1'
    assert ec.a == 1
    assert ec.b == 2
    assert ec.c == 3
    assert ec.d() == 1
    assert ExampleClass1.d() == 1
    assert ec(3) == 6


def test_configurable():
    CFG.register('model_2')
    CFG.model_2.a = 1
    CFG.model_2.b = 2
    ec = ExampleClass2()
    assert ec.__class__.__name__ == 'ExampleClass2'
    assert ec.a == 1
    assert ec.b == 2
    assert ec.c == 3
    assert ec.d() == 1
    assert ExampleClass2.d() == 1
    assert ec(3) == 6


def test_cregister():
    CFG.register('ExampleClass4')
    CFG.ExampleClass4.a = 1
    CFG.ExampleClass4.b = 2
    ec = configurable()("ExampleClass4")()
    assert ec.__class__.__name__ == 'ExampleClass4'
    assert ec.a == 1
    assert ec.b == 2
    assert ec.c == 3
    assert ec.d() == 1


def test_merge_from_sys_argv():
    sys.argv.append('a=1')
    sys.argv.append('b=test')
    sys.argv.append('c=True')
    merge_from_sys_argv()
    assert CFG.a == 1
    assert CFG.b == 'test'
    assert CFG.c is True


def test_build():
    CFG.register('model_2')
    CFG.model_2.a = 1
    CFG.model_2.b = 2
    ec = configurable()(ExampleClass2)()
    ec = configurable()('ExampleClass2')()
    CFG.register('ExampleClass3')
    CFG.ExampleClass3.a = 1
    CFG.ExampleClass3.b = 2
    ec = ExampleClass3()
    ec = ExampleClass3(3, b=4)


def test_cli():
    sys.argv = [sys.argv[0]]
    sys.argv.append('test_func.a=1')
    sys.argv.append('test_func.b=test')
    sys.argv.append('test_func.c=True')
    merge_from_sys_argv()

    @configurable('test_func').cli
    @configurable('test_func').register
    def test_func(a, b='hello', c=False):
        assert a == 1
        assert b == 'test'
        assert c is True

    test_func()
