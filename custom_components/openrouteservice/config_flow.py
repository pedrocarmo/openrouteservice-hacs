"""Config flow for OpenRouteService integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import CannotConnect, InvalidAuth, OpenRouteServiceAPI
from .const import (
    CONF_GEOCODING_CACHE_DAYS,
    CONF_LANGUAGE,
    CONF_ROUTE_CACHE_DAYS,
    CONF_UNITS,
    DEFAULT_GEOCODING_CACHE_DAYS,
    DEFAULT_LANGUAGE,
    DEFAULT_ROUTE_CACHE_DAYS,
    DEFAULT_UNITS,
    DOMAIN,
    LANGUAGES,
    UNITS,
)

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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for OpenRouteService."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._base_input: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Handle custom language
            language = user_input[CONF_LANGUAGE]
            if language == "custom":
                # Store the base input for custom language step
                self._base_input = user_input
                return await self.async_step_custom_language()

            return self.async_create_entry(title="", data=user_input)

        # Get current options or use defaults
        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GEOCODING_CACHE_DAYS,
                        default=options.get(
                            CONF_GEOCODING_CACHE_DAYS, DEFAULT_GEOCODING_CACHE_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=365)),
                    vol.Required(
                        CONF_ROUTE_CACHE_DAYS,
                        default=options.get(
                            CONF_ROUTE_CACHE_DAYS, DEFAULT_ROUTE_CACHE_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=365)),
                    vol.Required(
                        CONF_UNITS,
                        default=options.get(CONF_UNITS, DEFAULT_UNITS),
                    ): vol.In(UNITS),
                    vol.Required(
                        CONF_LANGUAGE,
                        default=options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                    ): vol.In(LANGUAGES),
                }
            ),
        )

    async def async_step_custom_language(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle custom language input."""
        if user_input is not None:
            # Combine base input with custom language
            final_input = self._base_input.copy()
            final_input[CONF_LANGUAGE] = user_input["custom_language_code"]
            return self.async_create_entry(title="", data=final_input)

        return self.async_show_form(
            step_id="custom_language",
            data_schema=vol.Schema(
                {
                    vol.Required("custom_language_code"): str,
                }
            ),
        )
