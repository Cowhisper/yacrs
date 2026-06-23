import pytest

from yacrs.config import _C


@pytest.fixture(scope="session")
def initial_config_state():
    """Capture the global config state after all test modules are imported."""
    return _C._configurables.clone(), _C._registry.clone()


@pytest.fixture(autouse=True)
def reset_global_config(initial_config_state):
    """Reset the global _C config before each test while preserving registrations."""
    initial_configurables, initial_registry = initial_config_state
    _C._configurables = initial_configurables.clone()
    _C._registry = initial_registry.clone()
    for key in list(_C.keys()):
        if key not in ("_configurables", "_registry"):
            del _C[key]
    yield
