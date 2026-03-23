"""Tests for AskeyCoordinator — the central polling logic."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coordinator import AskeyCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
from router import RouterDevice, RouterInfo, SessionExpiredError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_ENTRY_ID = "test_entry_id"


def _make_coordinator(
    client: AsyncMock,
    scan_interval: int = 300,
    consider_home: int = 180,
):
    """Build an AskeyCoordinator with a mocked HA and client."""

    hass = MagicMock()
    hass.loop = None  # DataUpdateCoordinator checks this

    coordinator = AskeyCoordinator(
        hass,
        client=client,
        scan_interval=scan_interval,
        consider_home=consider_home,
    )
    # Stub the config_entry attribute that entities read.
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = _FAKE_ENTRY_ID
    return coordinator


def _make_client(**overrides) -> AsyncMock:
    """Return a mock AskeyRouterClient with sensible defaults."""
    client = AsyncMock()
    client.async_login = AsyncMock(return_value=True)
    client.async_get_devices = AsyncMock(return_value={
        "AA:BB:CC:DD:EE:01": RouterDevice(mac="AA:BB:CC:DD:EE:01", hostname="phone"),
        "AA:BB:CC:DD:EE:02": RouterDevice(mac="AA:BB:CC:DD:EE:02", hostname="laptop"),
    })
    client.async_get_info = AsyncMock(return_value=RouterInfo(
        uptime_raw="0D 1H 0M 0S",
        uptime_seconds=3600,
        software_version="1.0.0",
    ))
    for key, val in overrides.items():
        setattr(client, key, val)
    return client


# ---------------------------------------------------------------------------
# _async_setup
# ---------------------------------------------------------------------------


class TestAsyncSetup:
    @pytest.mark.asyncio
    async def test_login_success(self):
        client = _make_client()
        coordinator = _make_coordinator(client)

        # Should not raise
        await coordinator._async_setup()
        client.async_login.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_connection_error_raises_not_ready(self):
        client = _make_client(
            async_login=AsyncMock(side_effect=OSError("Connection refused")),
        )
        coordinator = _make_coordinator(client)

        with pytest.raises(ConfigEntryNotReady):
            await coordinator._async_setup()

    @pytest.mark.asyncio
    async def test_login_returns_false_raises_auth_failed(self):
        client = _make_client(
            async_login=AsyncMock(return_value=False),
        )
        coordinator = _make_coordinator(client)

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_setup()


# ---------------------------------------------------------------------------
# _fetch_data (happy path)
# ---------------------------------------------------------------------------


class TestFetchData:
    @pytest.mark.asyncio
    async def test_returns_devices(self):
        client = _make_client()
        coordinator = _make_coordinator(client)

        devices = await coordinator._fetch_data()
        assert len(devices) == 2
        assert "AA:BB:CC:DD:EE:01" in devices

    @pytest.mark.asyncio
    async def test_updates_info(self):
        client = _make_client()
        coordinator = _make_coordinator(client)

        await coordinator._fetch_data()
        assert coordinator.info.software_version == "1.0.0"
        assert coordinator.info.uptime_seconds == 3600

    @pytest.mark.asyncio
    async def test_updates_last_seen(self):
        client = _make_client()
        coordinator = _make_coordinator(client)

        await coordinator._fetch_data()
        assert "AA:BB:CC:DD:EE:01" in coordinator.last_seen
        assert "AA:BB:CC:DD:EE:02" in coordinator.last_seen

    @pytest.mark.asyncio
    async def test_resets_consecutive_failures(self):
        client = _make_client()
        coordinator = _make_coordinator(client)
        coordinator._consecutive_failures = 5

        await coordinator._fetch_data()
        assert coordinator._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_preserves_info_when_get_info_returns_none(self):
        """If async_get_info fails (returns None), keep previous good info."""
        client = _make_client(
            async_get_info=AsyncMock(return_value=None),
        )
        coordinator = _make_coordinator(client)
        coordinator.info = RouterInfo(
            uptime_raw="1D 0H 0M 0S",
            uptime_seconds=86400,
            software_version="old",
        )

        await coordinator._fetch_data()
        assert coordinator.info.software_version == "old"
        assert coordinator.info.uptime_seconds == 86400


# ---------------------------------------------------------------------------
# _async_update_data — error handling and re-login
# ---------------------------------------------------------------------------


class TestUpdateDataRelogin:
    @pytest.mark.asyncio
    async def test_session_expired_triggers_relogin(self):
        """SessionExpiredError should trigger re-login and retry."""
        client = _make_client()
        # First call raises SessionExpiredError, subsequent calls succeed
        client.async_get_devices = AsyncMock(
            side_effect=[SessionExpiredError("expired"), {
                "AA:BB:CC:DD:EE:01": RouterDevice(mac="AA:BB:CC:DD:EE:01"),
            }]
        )
        coordinator = _make_coordinator(client)

        devices = await coordinator._async_update_data()
        assert len(devices) == 1
        assert client.async_login.await_count == 1

    @pytest.mark.asyncio
    async def test_generic_error_triggers_relogin(self):
        """Any exception should trigger re-login and retry."""
        client = _make_client()
        client.async_get_devices = AsyncMock(
            side_effect=[RuntimeError("network glitch"), {
                "AA:BB:CC:DD:EE:01": RouterDevice(mac="AA:BB:CC:DD:EE:01"),
            }]
        )
        coordinator = _make_coordinator(client)

        devices = await coordinator._async_update_data()
        assert len(devices) == 1


# ---------------------------------------------------------------------------
# _handle_failure — graceful degradation
# ---------------------------------------------------------------------------


class TestHandleFailure:
    @pytest.mark.asyncio
    async def test_first_failure_returns_cached_data(self):
        """First failure should return cached data, not raise."""
        client = _make_client(
            async_get_devices=AsyncMock(side_effect=RuntimeError("fail")),
            async_login=AsyncMock(side_effect=OSError("unreachable")),
        )
        coordinator = _make_coordinator(client)
        coordinator.data = {
            "AA:BB:CC:DD:EE:01": RouterDevice(mac="AA:BB:CC:DD:EE:01"),
        }

        result = await coordinator._async_update_data()
        assert len(result) == 1
        assert coordinator._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_second_failure_raises_update_failed(self):
        """Second consecutive failure should raise UpdateFailed."""
        client = _make_client(
            async_get_devices=AsyncMock(side_effect=RuntimeError("fail")),
            async_login=AsyncMock(side_effect=OSError("unreachable")),
        )
        coordinator = _make_coordinator(client)
        coordinator._consecutive_failures = 1  # Already had one failure

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_first_failure_returns_empty_dict_when_no_cache(self):
        """First failure with no cached data returns empty dict."""
        client = _make_client(
            async_get_devices=AsyncMock(side_effect=RuntimeError("fail")),
            async_login=AsyncMock(side_effect=OSError("unreachable")),
        )
        coordinator = _make_coordinator(client)
        coordinator.data = None

        result = await coordinator._async_update_data()
        assert result == {}

    @pytest.mark.asyncio
    async def test_relogin_rejected_raises_config_entry_auth_failed(self):
        """When re-login returns False (bad credentials), raise ConfigEntryAuthFailed."""
        from homeassistant.exceptions import ConfigEntryAuthFailed

        client = _make_client(
            async_get_devices=AsyncMock(side_effect=RuntimeError("fail")),
            async_login=AsyncMock(return_value=False),
        )
        coordinator = _make_coordinator(client)

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_success_after_failure_resets_counter(self):
        """A successful fetch after a failure should reset the counter."""
        client = _make_client()
        coordinator = _make_coordinator(client)
        coordinator._consecutive_failures = 1

        await coordinator._fetch_data()
        assert coordinator._consecutive_failures == 0


# ---------------------------------------------------------------------------
# consider_home clamping
# ---------------------------------------------------------------------------


class TestConsiderHome:
    def test_clamped_to_scan_interval(self):
        """consider_home should be at least scan_interval."""
        client = _make_client()
        coordinator = _make_coordinator(client, scan_interval=1800, consider_home=180)
        assert coordinator.consider_home == 1800

    def test_larger_consider_home_is_kept(self):
        """If consider_home > scan_interval, it should be kept as-is."""
        client = _make_client()
        coordinator = _make_coordinator(client, scan_interval=300, consider_home=600)
        assert coordinator.consider_home == 600

    def test_equal_values_are_kept(self):
        client = _make_client()
        coordinator = _make_coordinator(client, scan_interval=300, consider_home=300)
        assert coordinator.consider_home == 300
