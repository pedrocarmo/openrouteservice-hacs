"""Config flow for OpenRouteService integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult

from .api import CannotConnect, InvalidAuth, OpenRouteServiceAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenRouteServiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenRouteService."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Set unique ID based on API key prefix
                await self.async_set_unique_id(user_input[CONF_API_KEY][:12])
                self._abort_if_unique_id_configured()

                # Validate API key
                api = OpenRouteServiceAPI(self.hass, user_input[CONF_API_KEY])
                await api.validate_api_key()

                return self.async_create_entry(
                    title="OpenRouteService",
                    data=user_input,
                )

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "signup_url": "https://openrouteservice.org/sign-up"
            },
        )
