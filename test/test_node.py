import pytest

from yacrs.config import Node


class TestNodeInit:
    def test_init_empty(self):
        node = Node()
        assert len(node) == 0
        assert not node.is_frozen()

    def test_init_from_dict(self):
        node = Node({"a": 1, "b": 2})
        assert node["a"] == 1
        assert node.get("b") == 2

    def test_init_frozen(self):
        node = Node({"a": 1}, freeze=True)
        assert node.is_frozen()
        with pytest.raises(AttributeError, match="frozen"):
            node.set("b", 2)

    def test_init_from_node(self):
        source = Node({"a": 1})
        node = Node(source)
        assert node["a"] == 1


class TestNodeGet:
    def test_get_basic(self):
        node = Node({"a": 1})
        assert node.get("a") == 1

    def test_get_attribute_access(self):
        node = Node({"a": 1})
        assert node.a == 1

    def test_get_missing(self):
        node = Node()
        with pytest.raises(AttributeError, match="No such attribute 'x'"):
            node.get("x")

    def test_get_missing_attribute(self):
        node = Node()
        with pytest.raises(AttributeError):
            _ = node.x

    def test_get_nested(self):
        node = Node()
        node.register("a.b.c")
        node.set("a.b.c", 42)
        assert node.get("a.b.c") == 42
        assert node.a.b.c == 42

    def test_get_nested_invalid_path(self):
        node = Node({"a": 1})
        with pytest.raises(AttributeError, match="No such attribute 'a.b'"):
            node.get("a.b")

    def test_get_deeply_nested(self):
        node = Node()
        node.set("a.b.c.d.e", "deep")
        assert node.get("a.b.c.d.e") == "deep"


class TestNodeSet:
    def test_set_basic(self):
        node = Node()
        node.set("a", 1)
        assert node["a"] == 1

    def test_set_overwrite(self):
        node = Node({"a": 1})
        node.set("a", 2)
        assert node["a"] == 2

    def test_set_nested_auto_register(self):
        node = Node()
        node.set("a.b.c", 1)
        assert isinstance(node.get("a"), Node)
        assert isinstance(node.get("a.b"), Node)
        assert node.get("a.b.c") == 1

    def test_set_nested_no_register(self):
        node = Node()
        with pytest.raises(AttributeError):
            node.set("a.b", 1, do_register=False)

    def test_set_nested_no_register_existing_prefix(self):
        node = Node()
        node.register("a")
        with pytest.raises(AttributeError):
            node.set("a.b.c", 1, do_register=False)

    def test_set_overwrite_node_with_value(self):
        node = Node()
        node.register("a.b")
        node.set("a", 1)
        assert node.get("a") == 1
        with pytest.raises(AttributeError):
            node.get("a.b")

    def test_set_frozen(self):
        node = Node({"a": 1}, freeze=True)
        with pytest.raises(AttributeError, match="frozen"):
            node.set("a", 2)
        with pytest.raises(AttributeError, match="frozen"):
            node.set("b", 2)

    def test_set_non_node_intermediate(self):
        node = Node({"a": 1})
        with pytest.raises(AttributeError, match="is not a Node"):
            node.set("a.b", 2)

    def test_setattr(self):
        node = Node()
        node.foo = "bar"
        assert node["foo"] == "bar"
        assert node.foo == "bar"

    def test_setattr_nested(self):
        node = Node()
        node.a = Node()
        node.a.b = 1
        assert node.get("a.b") == 1

    def test_set_value_types(self):
        node = Node()
        node.set("int", 1)
        node.set("float", 1.5)
        node.set("str", "hello")
        node.set("list", [1, 2, 3])
        node.set("dict", {"x": 1})
        node.set("none", None)
        assert node.get("int") == 1
        assert node.get("float") == 1.5
        assert node.get("str") == "hello"
        assert node.get("list") == [1, 2, 3]
        assert node.get("dict") == {"x": 1}
        assert node.get("none") is None


class TestNodeHas:
    def test_has_basic(self):
        node = Node({"a": 1})
        assert node.has("a")
        assert not node.has("b")

    def test_has_nested(self):
        node = Node()
        node.register("a.b.c")
        assert node.has("a")
        assert node.has("a.b")
        assert node.has("a.b.c")
        assert not node.has("a.b.d")
        assert not node.has("a.x.c")

    def test_has_non_node_intermediate(self):
        node = Node({"a": 1})
        assert not node.has("a.b")

    def test_has_empty_node(self):
        node = Node()
        assert not node.has("a")


class TestNodeRegister:
    def test_register_basic(self):
        node = Node()
        node.register("a")
        assert isinstance(node.get("a"), Node)

    def test_register_nested(self):
        node = Node()
        node.register("a.b.c")
        assert isinstance(node.get("a"), Node)
        assert isinstance(node.get("a.b"), Node)
        assert isinstance(node.get("a.b.c"), Node)

    def test_register_idempotent(self):
        node = Node()
        node.register("a.b")
        node.register("a.b")
        assert isinstance(node.get("a.b"), Node)

    def test_register_non_node_intermediate(self):
        node = Node({"a": 1})
        with pytest.raises(AttributeError, match="is not a Node"):
            node.register("a.b")

    def test_register_frozen(self):
        node = Node(freeze=True)
        with pytest.raises(AttributeError, match="frozen"):
            node.register("a")


class TestNodeDelete:
    def test_delete_basic(self):
        node = Node({"a": 1})
        node.delete("a")
        assert not node.has("a")

    def test_delete_nested(self):
        node = Node()
        node.register("a.b.c")
        node.delete("a.b.c")
        assert node.has("a.b")
        assert not node.has("a.b.c")

    def test_delete_missing(self):
        node = Node()
        with pytest.raises(AttributeError, match="does not exist"):
            node.delete("a")

    def test_delete_non_node_intermediate(self):
        node = Node({"a": 1})
        with pytest.raises(AttributeError, match="is not a Node"):
            node.delete("a.b")


class TestNodeFreeze:
    def test_freeze(self):
        node = Node()
        node.freeze(True)
        assert node.is_frozen()
        node.freeze(False)
        assert not node.is_frozen()

    def test_freeze_recursive(self):
        node = Node()
        node.register("a.b.c")
        node.freeze(True)
        assert node.is_frozen()
        assert node.get("a").is_frozen()
        assert node.get("a.b").is_frozen()
        assert node.get("a.b.c").is_frozen()
        with pytest.raises(AttributeError, match="frozen"):
            node.get("a").set("x", 1)

    def test_unfreeze_recursive(self):
        node = Node()
        node.register("a.b")
        node.freeze(True)
        node.freeze(False)
        assert not node.get("a").is_frozen()
        node.get("a").set("x", 1)
        assert node.get("a.x") == 1

    def test_register_frozen(self):
        node = Node()
        node.register("a")
        node.freeze(True)
        with pytest.raises(AttributeError, match="frozen"):
            node.register("a.b")


class TestNodeClone:
    def test_clone(self):
        node = Node({"a": 1})
        node.register("b.c")
        node.set("b.c", 2)
        cloned = node.clone()
        assert cloned == node
        assert cloned is not node
        cloned.set("a", 999)
        assert node.get("a") == 1

    def test_clone_deep(self):
        node = Node()
        node.set("a.b", [1, 2, 3])
        cloned = node.clone()
        cloned.get("a.b").append(4)
        assert node.get("a.b") == [1, 2, 3]


class TestNodePprint:
    def test_pprint(self):
        node = Node()
        node.set("b", 2)
        node.register("a.b.c")
        node.set("q.p.r", 2)
        text = node.pprint()
        expected = """
b: 2
a:
  b:
    c:
q:
  p:
    r: 2
""".strip()
        assert text.strip() == expected

    def test_pprint_empty(self):
        node = Node()
        assert node.pprint() == ""

    def test_pprint_skip_prefix(self):
        node = Node()
        node.set("_private", 1)
        node.set("public", 2)
        text = node.pprint()
        assert "_private" not in text
        assert "public" in text

    def test_pprint_nested_values(self):
        node = Node()
        node.set("a.b", 1)
        node.set("a.c", 2)
        text = node.pprint()
        assert text.strip() == "a:\n  b: 1\n  c: 2"


class TestNodeUpdate:
    def test_update_basic(self):
        node = Node()
        node.update({"a": 1, "b": 2})
        assert node.get("a") == 1
        assert node.get("b") == 2

    def test_update_converts_nested_dicts(self):
        node = Node()
        node.update({"a": {"b": {"c": 1}}})
        assert isinstance(node.get("a"), Node)
        assert isinstance(node.get("a.b"), Node)
        assert node.get("a.b.c") == 1

    def test_update_kwargs(self):
        node = Node()
        node.update(a=1, b=2)
        assert node.get("a") == 1
        assert node.get("b") == 2

    def test_update_sequence(self):
        node = Node()
        node.update([("a", 1), ("b", 2)])
        assert node.get("a") == 1
        assert node.get("b") == 2

    def test_update_frozen(self):
        node = Node(freeze=True)
        with pytest.raises(AttributeError, match="frozen"):
            node.update({"a": 1})


class TestNodeEdgeCases:
    def test_dict_methods_still_work(self):
        node = Node({"a": 1})
        assert list(node.keys()) == ["a"]
        assert list(node.values()) == [1]
        assert list(node.items()) == [("a", 1)]
        assert len(node) == 1

    def test_node_is_dict_subclass(self):
        node = Node({"a": 1})
        assert isinstance(node, dict)

    def test_attribute_access_does_not_conflict_with_dict_methods(self):
        node = Node()
        node.set("items", "value")
        # dict method takes precedence over attribute access
        assert callable(node.items)
        assert node["items"] == "value"
