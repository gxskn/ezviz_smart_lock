"""Config flow for EZVIZ Smart Lock."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
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


class EzvizSmartLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EZVIZ Smart Lock."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: EzvizClient | None = None
        self._user_input: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input = user_input

            self._client = EzvizClient(
                account=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                url="apiisa.ezvizlife.com",
            )

            try:
                await self.hass.async_add_executor_job(self._client.login)

                token = self._client._token

                await self.async_set_unique_id(user_input[CONF_DEVICE_SERIAL])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"EZVIZ Smart Lock {user_input[CONF_DEVICE_SERIAL]}",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_DEVICE_SERIAL: user_input[CONF_DEVICE_SERIAL],
                        CONF_TOKEN: token,
                        CONF_ENABLE_REMOTE_UNLOCK: user_input.get(
                            CONF_ENABLE_REMOTE_UNLOCK,
                            False,
                        ),
                    },
                )

            except EzvizAuthVerificationCode:
                return await self.async_step_mfa()

            except Exception:
                _LOGGER.debug("Unable to authenticate with EZVIZ", exc_info=True)
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_DEVICE_SERIAL, default="XX1234567"): str,
                vol.Optional(CONF_ENABLE_REMOTE_UNLOCK, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_mfa(self, user_input: dict[str, Any] | None = None):
        """Handle MFA verification."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                if self._client is None or self._user_input is None:
                    errors["base"] = "cannot_connect"
                else:
                    code = user_input[CONF_MFA_CODE]

                    await self.hass.async_add_executor_job(
                        self._client.login,
                        code,
                    )

                    token = self._client._token

                    await self.async_set_unique_id(
                        self._user_input[CONF_DEVICE_SERIAL]
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"EZVIZ Smart Lock {self._user_input[CONF_DEVICE_SERIAL]}",
                        data={
                            CONF_EMAIL: self._user_input[CONF_EMAIL],
                            CONF_DEVICE_SERIAL: self._user_input[CONF_DEVICE_SERIAL],
                            CONF_TOKEN: token,
                            CONF_ENABLE_REMOTE_UNLOCK: self._user_input.get(
                                CONF_ENABLE_REMOTE_UNLOCK,
                                False,
                            ),
                        },
                    )

            except Exception:
                _LOGGER.debug("Unable to validate EZVIZ MFA code", exc_info=True)
                errors["base"] = "invalid_auth"

        schema = vol.Schema(
            {
                vol.Required(CONF_MFA_CODE): str,
            }
        )

        return self.async_show_form(
            step_id="mfa",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )