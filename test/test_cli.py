from yacrs.config import configurable


@configurable('test_func').cli
@configurable('test_func').register
def test_func(a, b='hello', c=False):
    assert a == 1
    assert b == 'test'
    assert c is True

test_func()