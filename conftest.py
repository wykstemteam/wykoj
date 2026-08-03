"""
Root conftest. `wykoj/tortoise_config.py` reads config.json at *import time*
(module-level `open("config.json")`), and importing any submodule under the
`wykoj` package runs `wykoj/__init__.py`, which imports tortoise_config. This
means merely importing e.g. `wykoj.models` fails with FileNotFoundError
unless config.json already exists before pytest collects test modules -
fixtures run too late for this, so it has to happen in pytest_configure.
"""
import json
import os

_CONFIG_PATH = "config.json"  # relative, matching tortoise_config.py's own open("config.json")
_created_config = False


def pytest_configure(config) -> None:
    global _created_config
    if not os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, "w") as f:
            json.dump({"DB_URI": "sqlite://:memory:"}, f)
        _created_config = True


def pytest_unconfigure(config) -> None:
    if _created_config and os.path.exists(_CONFIG_PATH):
        os.remove(_CONFIG_PATH)
