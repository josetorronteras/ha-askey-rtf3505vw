"""Tests for the RouterDevice dataclass."""
import pytest

from router import RouterDevice


class TestMacNormalisation:
    def test_lowercase_converted_to_uppercase(self):
        d = RouterDevice(mac="aa:bb:cc:dd:ee:ff")
        assert d.mac == "AA:BB:CC:DD:EE:FF"

    def test_hyphens_replaced_with_colons(self):
        d = RouterDevice(mac="AA-BB-CC-DD-EE-FF")
        assert d.mac == "AA:BB:CC:DD:EE:FF"

    def test_mixed_case_hyphens(self):
        d = RouterDevice(mac="aa-BB-cc-DD-ee-FF")
        assert d.mac == "AA:BB:CC:DD:EE:FF"


class TestHostnameFallback:
    def test_empty_hostname_defaults_to_mac(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF")
        assert d.hostname == "AA:BB:CC:DD:EE:FF"

    def test_explicit_hostname_is_kept(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", hostname="my-phone")
        assert d.hostname == "my-phone"


class TestConnectionType:
    def test_wired_when_no_band(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF")
        assert d.is_wired is True
        assert d.is_wifi is False

    def test_wifi_when_band_is_24ghz(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", band="2.4GHz")
        assert d.is_wifi is True
        assert d.is_wired is False

    def test_wifi_when_band_is_5ghz(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", band="5GHz")
        assert d.is_wifi is True
        assert d.is_wired is False


class TestGuestNetwork:
    def test_guest_when_interface_has_dot(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", interface="wl0.1")
        assert d.is_guest is True

    def test_not_guest_for_main_24ghz_interface(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", interface="wl0")
        assert d.is_guest is False

    def test_not_guest_for_5ghz_interface(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF", interface="wl1")
        assert d.is_guest is False

    def test_not_guest_when_no_interface(self):
        d = RouterDevice(mac="AA:BB:CC:DD:EE:FF")
        assert d.is_guest is False
