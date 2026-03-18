"""Shared fixtures for all test modules."""
import importlib
import sys
import types
from pathlib import Path

import pytest

# Register HA stubs BEFORE importing the component so modules that depend
# on homeassistant (coordinator, const, etc.) resolve against our stubs.
HA_STUBS_DIR = Path(__file__).parent / "ha_stubs"
sys.path.insert(0, str(HA_STUBS_DIR))

# Import component modules directly to avoid triggering the HA-dependent __init__.py.
COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "askey_rtf3505vw"
sys.path.insert(0, str(COMPONENT_DIR))

# Register the component directory as a package so relative imports
# (from .const, from .router) work inside coordinator.py, etc.
_PKG_NAME = "askey_rtf3505vw"
_pkg = types.ModuleType(_PKG_NAME)
_pkg.__path__ = [str(COMPONENT_DIR)]
_pkg.__package__ = _PKG_NAME
sys.modules[_PKG_NAME] = _pkg

# Pre-load submodules that use relative imports.
for _mod_name in ("const", "router", "coordinator"):
    _full = f"{_PKG_NAME}.{_mod_name}"
    if _full not in sys.modules:
        _spec = importlib.util.spec_from_file_location(
            _full, COMPONENT_DIR / f"{_mod_name}.py",
            submodule_search_locations=[],
        )
        _mod = importlib.util.module_from_spec(_spec)
        _mod.__package__ = _PKG_NAME
        sys.modules[_full] = _mod
        _spec.loader.exec_module(_mod)
        # Also register as top-level so `from coordinator import ...` works.
        sys.modules[_mod_name] = _mod

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def dhcp_html() -> str:
    return _load("dhcpinfo.html")


@pytest.fixture
def arp_html() -> str:
    return _load("arpview.html")


@pytest.fixture
def wifi_24_html() -> str:
    return _load("wlstationlist_24.html")


@pytest.fixture
def wifi_5_html() -> str:
    return _load("wlstationlist_5.html")


@pytest.fixture
def info_html() -> str:
    return _load("info.html")


@pytest.fixture
def login_html() -> str:
    return _load("login.html")


@pytest.fixture
def resetrouter_html() -> str:
    return _load("resetrouter.html")
