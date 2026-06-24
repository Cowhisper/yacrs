import pytest

from yacrs.config import _C as CFG
from yacrs.config import configurable, register


# Module-level helper classes for tests that rely on inferred scope names.
# Nested classes inside test methods have qualified names that include the
# test class/method, which breaks the simple scope inference used by yacrs.
@register()
class InferredScopeModel:
    def __init__(self, a):
        self.a = a


@register()
class ModelForCallByName:
    def __init__(self, a):
        self.a = a


@register("annotated_model")
class AnnotationWithScopeModel:
    def __init__(self, a: "other.value"):
        self.a = a


class TestConfigurableRegister:
    def test_register_basic(self):
        @register("model")
        class Model:
            def __init__(self, a, b=10):
                self.a = a
                self.b = b

        CFG.register("model")
        CFG.model.a = 1
        m = Model()
        assert m.a == 1
        assert m.b == 10

    def test_register_default_override(self):
        @register("model")
        class Model:
            def __init__(self, a, b=10):
                self.a = a
                self.b = b

        CFG.register("model")
        CFG.model.a = 1
        CFG.model.b = 20
        m = Model()
        assert m.a == 1
        assert m.b == 20

    def test_register_scope_inferred(self):
        CFG.register("InferredScopeModel")
        CFG.InferredScopeModel.a = 5
        obj = InferredScopeModel()
        assert obj.a == 5

    def test_register_preserves_class_name(self):
        @register("model")
        class Model:
            def __init__(self, a):
                self.a = a

        CFG.register("model")
        CFG.model.a = 1
        m = Model()
        assert m.__class__.__name__ == "Model"


class TestConfigurableUnbind:
    def test_unbind_scope(self):
        @register(configurable.UNDBIND)
        class Model:
            def __init__(self, a, b):
                self.a = a
                self.b = b

        CFG.register("model_scope")
        CFG.model_scope.a = 1
        CFG.model_scope.b = 2
        m = configurable("model_scope")(Model)()
        assert m.a == 1
        assert m.b == 2

    def test_unbind_default(self):
        @register(configurable.UNDBIND)
        class Model:
            def __init__(self, a, b=99):
                self.a = a
                self.b = b

        CFG.register("Model")
        CFG.Model.a = 1
        m = configurable("Model")(Model)()
        assert m.a == 1
        assert m.b == 99


class TestConfigurableCall:
    def test_call_by_name(self):
        CFG.register("ModelForCallByName")
        CFG.ModelForCallByName.a = 3
        m = configurable()("ModelForCallByName")()
        assert m.a == 3

    def test_call_by_name_unregistered(self):
        with pytest.raises(KeyError, match="Unregist module name"):
            configurable()("NonExistent")()

    def test_call_direct(self):
        @register("model")
        class Model:
            def __init__(self, a, b):
                self.a = a
                self.b = b

        CFG.register("model")
        CFG.model.a = 1
        CFG.model.b = 2
        m = configurable("model")(Model)()
        assert m.a == 1
        assert m.b == 2

    def test_call_with_positional_args(self):
        @register("model")
        class Model:
            def __init__(self, a, b):
                self.a = a
                self.b = b

        CFG.register("model")
        CFG.model.a = 1
        CFG.model.b = 2
        m = Model(3, b=4)
        assert m.a == 3
        assert m.b == 4

    def test_call_function(self):
        @register("func")
        def my_func(a, b=10):
            return a + b

        CFG.register("func")
        CFG.func.a = 5
        assert my_func() == 15


class TestConfigurableErrors:
    def test_missing_required(self):
        @register("model")
        class Model:
            def __init__(self, a):
                self.a = a

        CFG.register("model")
        with pytest.raises(TypeError):
            Model()

    def test_call_unregistered_name(self):
        with pytest.raises(KeyError):
            configurable()("missing")()


class TestConfigurableAnnotations:
    def test_string_annotation_dot_prefix(self):
        @register("model")
        class Model:
            def __init__(self, a: ".custom"):
                self.a = a

        CFG.register("model")
        CFG.model.custom = "hello"
        m = Model()
        assert m.a == "hello"

    def test_string_annotation_plain(self):
        @register("model")
        class Model:
            def __init__(self, a: "plain"):
                self.a = a

        CFG.register("model")
        CFG.model.plain = "world"
        m = Model()
        assert m.a == "world"

    def test_string_annotation_with_scope(self):
        CFG.register("annotated_model")
        CFG.register("annotated_model.other")
        CFG.annotated_model.other.value = "scoped"
        obj = AnnotationWithScopeModel()
        assert obj.a == "scoped"

    def test_annotation_uses_param_name(self):
        @register("model")
        class Model:
            def __init__(self, alpha_value):
                self.a = alpha_value

        CFG.register("model")
        CFG.model.alpha_value = 42
        m = Model()
        assert m.a == 42
