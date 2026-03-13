"""Shared fixtures for all test modules."""
import sys
from pathlib import Path

import pytest

# Import router.py directly to avoid triggering the HA-dependent __init__.py.
# router.py has no homeassistant dependencies so this is safe.
COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "askey_rtf3505vw"
sys.path.insert(0, str(COMPONENT_DIR))

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
