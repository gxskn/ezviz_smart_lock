"""Config flow for EZVIZ Smart Lock."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from pyezvizapi import EzvizAuthVerificationCode, EzvizClient

from .const import (
    CONF_DEVICE_SERIAL,
    CONF_EMAIL,
    CONF_ENABLE_REMOTE_UNLOCK,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_TOKEN = "token"
CONF_MFA_CODE = "mfa_code"

EZVIZ_API_URL = "apiisa.ezvizlife.com"


class EzvizSmartLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EZVIZ Smart Lock."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client: EzvizClient | None = None
        self._user_input: dict[str, Any] | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_DEVICE_SERIAL] = user_input[CONF_DEVICE_SERIAL].strip().upper()
            self._user_input = user_input

            self._client = EzvizClient(
                account=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                url=EZVIZ_API_URL,
            )

            try:
                await self.hass.async_add_executor_job(self._client.login)

                return await self._async_create_ezviz_entry(
                    user_input=user_input,
                    token=self._client._token,
                )

            except EzvizAuthVerificationCode:
                return await self.async_step_mfa()

            except Exception:
                _LOGGER.debug("Unable to authenticate with EZVIZ", exc_info=True)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(),
            errors=errors,
            description_placeholders={},
        )

    async def async_step_mfa(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle MFA verification."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if self._client is None or self._user_input is None:
                errors["base"] = "cannot_connect"
            else:
                try:
                    await self.hass.async_add_executor_job(
                        self._client.login,
                        user_input[CONF_MFA_CODE],
                    )

                    return await self._async_create_ezviz_entry(
                        user_input=self._user_input,
                        token=self._client._token,
                    )

                except Exception:
                    _LOGGER.debug("Unable to validate EZVIZ MFA code", exc_info=True)
                    errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="mfa",
            data_schema=self._mfa_schema(),
            errors=errors,
            description_placeholders={},
        )

    async def _async_create_ezviz_entry(
        self,
        *,
        user_input: dict[str, Any],
        token: dict[str, Any],
    ) -> ConfigFlowResult:
        """Create the EZVIZ config entry."""
        serial = user_input[CONF_DEVICE_SERIAL]

        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"EZVIZ Smart Lock {serial}",
            data={
                CONF_EMAIL: user_input[CONF_EMAIL],
                CONF_DEVICE_SERIAL: serial,
                CONF_TOKEN: token,
                CONF_ENABLE_REMOTE_UNLOCK: user_input.get(
                    CONF_ENABLE_REMOTE_UNLOCK,
                    False,
                ),
            },
        )

    @staticmethod
    def _user_schema() -> vol.Schema:
        """Return the user step schema."""
        return vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_DEVICE_SERIAL, default="XX1234567"): str,
                vol.Optional(CONF_ENABLE_REMOTE_UNLOCK, default=False): bool,
            }
        )

    @staticmethod
    def _mfa_schema() -> vol.Schema:
        """Return the MFA step schema."""
        return vol.Schema(
            {
                vol.Required(CONF_MFA_CODE): str,
            }
        )
