import json
import sys

import pytest
import toml
import yaml

from yacrs.config import _C as CFG, configurable, merge_from_sys_argv


class TestMergeFromSysArgv:
    def test_merge_basic(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "a=1", "b=test", "c=True"]
            merge_from_sys_argv()
            assert CFG.a == 1
            assert CFG.b == "test"
            assert CFG.c is True
        finally:
            sys.argv = original

    def test_merge_with_type_hints(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "a:int=42", "b:float=3.14"]
            merge_from_sys_argv()
            assert CFG.a == 42
            assert CFG.b == 3.14
        finally:
            sys.argv = original

    def test_merge_bool_type_hint_true(self):
        # bool('True') returns True, so this path works for true values.
        original = sys.argv
        try:
            sys.argv = ["prog", "c:bool=True"]
            merge_from_sys_argv()
            assert CFG.c is True
        finally:
            sys.argv = original

    def test_merge_string_fallback(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "name=hello"]
            merge_from_sys_argv()
            assert CFG.name == "hello"
        finally:
            sys.argv = original

    def test_merge_ignores_non_kv_args(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "--flag", "a=1", "positional"]
            merge_from_sys_argv()
            assert CFG.a == 1
            assert not CFG.has("--flag")
            assert not CFG.has("positional")
        finally:
            sys.argv = original

    def test_merge_invalid_type(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "a:int=notanint"]
            with pytest.raises(TypeError, match="Cannot convert"):
                merge_from_sys_argv()
        finally:
            sys.argv = original

    def test_merge_dotted_keys(self):
        original = sys.argv
        try:
            sys.argv = ["prog", "model.a:int=1", "model.b=test"]
            merge_from_sys_argv()
            assert CFG.model.a == 1
            assert CFG.model.b == "test"
        finally:
            sys.argv = original


class TestConfigurableCLI:
    def test_cli_options(self):
        original = sys.argv
        try:
            sys.argv = [
                "prog",
                "test_func.a:int=1",
                "test_func.b=test",
                "test_func.c:bool=True",
            ]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a, b="hello", c=False):
                assert a == 1
                assert b == "test"
                assert c is True

            test_func()
        finally:
            sys.argv = original

    def test_cli_options_string_default(self):
        # Without type hints the CLI keeps values as strings.
        original = sys.argv
        try:
            sys.argv = ["prog", "test_func.a=1"]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a):
                assert a == "1"

            test_func()
        finally:
            sys.argv = original

    def test_cli_json_config(self, tmp_path):
        config = {"test_func": {"a": 1, "b": "test", "c": True}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        original = sys.argv
        try:
            sys.argv = ["prog", "-c", str(config_file)]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a, b="hello", c=False):
                assert a == 1
                assert b == "test"
                assert c is True

            test_func()
        finally:
            sys.argv = original

    def test_cli_yaml_config(self, tmp_path):
        config = {"test_func": {"a": 2, "b": "yaml", "c": False}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))

        original = sys.argv
        try:
            sys.argv = ["prog", "--config", str(config_file)]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a, b="hello", c=False):
                assert a == 2
                assert b == "yaml"
                assert c is False

            test_func()
        finally:
            sys.argv = original

    def test_cli_toml_config(self, tmp_path):
        config = {"test_func": {"a": 3, "b": "toml", "c": True}}
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml.dumps(config))

        original = sys.argv
        try:
            sys.argv = ["prog", "-c", str(config_file)]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a, b="hello", c=False):
                assert a == 3
                assert b == "toml"
                assert c is True

            test_func()
        finally:
            sys.argv = original

    def test_cli_options_override_config(self, tmp_path):
        config = {"test_func": {"a": 1, "b": "config", "c": False}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        original = sys.argv
        try:
            sys.argv = ["prog", "-c", str(config_file), "test_func.b=override"]

            @configurable("test_func").cli
            @configurable("test_func").register
            def test_func(a, b="hello", c=False):
                assert a == 1
                assert b == "override"
                assert c is False

            test_func()
        finally:
            sys.argv = original

    def test_cli_unsupported_config_type(self, tmp_path):
        config_file = tmp_path / "config.txt"
        config_file.write_text("a=1")

        @configurable("test_func").register
        def test_func(a=1):
            pass

        original = sys.argv
        try:
            sys.argv = ["prog", "-c", str(config_file)]
            with pytest.raises(ValueError, match="Unsupported config file type"):
                configurable("test_func").cli(test_func)
        finally:
            sys.argv = original
