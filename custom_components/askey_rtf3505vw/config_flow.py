"""Config flow for the Askey RTF3505VW integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .router import DEFAULT_HOST, AskeyRouterClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=3600)
        ),
    }
)

STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _test_credentials(host: str, password: str) -> bool:
    """Validate credentials against the router before saving the config entry."""
    async with aiohttp.ClientSession() as session:
        client = AskeyRouterClient(session, host=host, password=password)
        return await client.async_test_credentials()


class AskeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the UI setup flow for the Askey RTF3505VW integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            try:
                ok = await _test_credentials(host, password)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                if ok:
                    return self.async_create_entry(
                        title=f"Askey RTF3505VW ({host})",
                        data=user_input,
                    )
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]

            try:
                ok = await _test_credentials(host, password)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                if ok:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates=user_input,
                    )
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Triggered when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle re-authentication with a new password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            host = reauth_entry.data[CONF_HOST]
            password = user_input[CONF_PASSWORD]

            try:
                ok = await _test_credentials(host, password)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                if ok:
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data_updates={CONF_PASSWORD: password},
                    )
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": reauth_entry.data[CONF_HOST]},
        )
