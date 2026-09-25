"""Config flow for Spotify Soloist."""

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN, WS_TIMEOUT


class SoloistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Spotify Soloist config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.ws_connect(
                        f"ws://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}",
                        timeout=WS_TIMEOUT,
                    ) as websocket,
                ):
                    await websocket.receive(timeout=WS_TIMEOUT)
            except aiohttp.ClientError, TimeoutError, OSError:
                errors["base"] = "cannot_connect"
            else:
                unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )
