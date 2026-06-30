"""Coordinator for the EZVIZ Smart Lock integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from copy import deepcopy
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_DEVICE_SERIAL,
    CONF_ENABLE_REMOTE_UNLOCK,
    CONF_TOKEN,
    HA_EVENT_EZVIZ_SMART_LOCK,
)
from .mqtt_client import EzvizMQTTClient

_LOGGER = logging.getLogger(__name__)

EZVIZ_HASSIO_TERMINAL_NAME = "hassio"
EZVIZ_REMOTE_UNLOCK_TYPE = "unLinkIPC"


class EzvizCoordinator:
    """Coordinator for the EZVIZ Smart Lock integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the EZVIZ coordinator."""
        self.hass = hass
        self.entry = entry
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self.mqtt = EzvizMQTTClient(hass, entry, self)

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        _LOGGER.debug("Initializing EZVIZ Smart Lock coordinator")

    async def async_start(self) -> None:
        """Start MQTT client."""
        await self.mqtt.start()

    async def async_stop(self) -> None:
        """Stop MQTT client."""
        await self.mqtt.stop()
        self._callbacks.clear()

    @property
    def remote_unlock_enabled(self) -> bool:
        """Return if remote unlock is enabled."""
        return bool(self.entry.data.get(CONF_ENABLE_REMOTE_UNLOCK, False))

    def register_callback(
        self,
        callback: Callable[[dict[str, Any]], None],
    ) -> Callable[[], None]:
        """Register a callback for EZVIZ events."""
        self._callbacks.append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe

    def handle_event(self, event_data: dict[str, Any]) -> None:
        """Handle an event received from MQTT."""
        self.hass.loop.call_soon_threadsafe(
            self._handle_event_in_hass_loop,
            event_data,
        )

    def _handle_event_in_hass_loop(self, event_data: dict[str, Any]) -> None:
        """Handle an event inside the Home Assistant event loop."""
        self.fire_event(event_data)
        self.notify_callbacks(event_data)

    def fire_event(self, event_data: dict[str, Any]) -> None:
        """Fire an EZVIZ Smart Lock event on the Home Assistant bus."""
        self.hass.bus.fire(HA_EVENT_EZVIZ_SMART_LOCK, event_data)

    def notify_callbacks(self, event_data: dict[str, Any]) -> None:
        """Notify registered callbacks."""
        for callback in list(self._callbacks):
            try:
                callback(event_data)
            except Exception:
                _LOGGER.exception("Error in EZVIZ Smart Lock callback")

    async def async_update_token(self, token: dict[str, Any]) -> None:
        """Persist a refreshed EZVIZ token."""
        data = deepcopy(dict(self.entry.data))

        if data.get(CONF_TOKEN) == token:
            return

        data[CONF_TOKEN] = token

        self.hass.config_entries.async_update_entry(
            self.entry,
            data=data,
        )

        updated_entry = self.hass.config_entries.async_get_entry(self.entry.entry_id)

        if updated_entry is not None:
            self.entry = updated_entry

        _LOGGER.debug("EZVIZ token updated")

    def _select_terminal_bind_code(self) -> str:
        """Select the bind code required for DL05 remote unlock."""
        if self.mqtt.client is None:
            raise HomeAssistantError("EZVIZ client is not connected")

        current_feature_code = self.mqtt.client._token.get("feature_code")

        terminals_response = self.mqtt.client.get_terminals()
        terminals = terminals_response.get("terminals", [])

        valid_terminals: list[dict[str, str]] = []

        for terminal in terminals:
            sign = str(terminal.get("sign") or "").strip()
            user_id = str(terminal.get("userId") or "").strip()
            name = str(
                terminal.get("name") or terminal.get("terminalName") or user_id
            ).strip()
            last_modify = str(
                terminal.get("lastModifytime")
                or terminal.get("lastModifyTime")
                or ""
            )

            if not sign or not user_id:
                continue

            valid_terminals.append(
                {
                    "sign": sign,
                    "user_id": user_id,
                    "name": name,
                    "last_modify": last_modify,
                }
            )

        if not valid_terminals:
            raise HomeAssistantError("No valid EZVIZ terminal bind found")

        preferred = [
            terminal
            for terminal in valid_terminals
            if terminal["sign"] != current_feature_code
            and terminal["name"].casefold() != EZVIZ_HASSIO_TERMINAL_NAME
        ]

        selected = max(
            preferred or valid_terminals,
            key=lambda item: item["last_modify"],
        )

        _LOGGER.debug(
            "EZVIZ terminal selected for remote unlock: name=%s sign_prefix=%s",
            selected["name"],
            selected["sign"][:8],
        )

        return f"{selected['sign']}{selected['user_id']}"

    async def async_remote_unlock(self) -> dict[str, Any]:
        """Execute remote unlock."""
        if not self.remote_unlock_enabled:
            raise HomeAssistantError("Remote unlock is disabled")

        if self.mqtt.client is None:
            raise HomeAssistantError("EZVIZ client is not connected")

        serial = self.entry.data[CONF_DEVICE_SERIAL]

        bind_code = await self.hass.async_add_executor_job(
            self._select_terminal_bind_code,
        )

        random_response = await self.hass.async_add_executor_job(
            partial(
                self.mqtt.client._request_json,
                "PUT",
                (
                    f"/v3/iot-feature/action/{serial}/DoorLock/0/DoorLockMgr/"
                    "QueryRemoteUnlockRandomCode"
                ),
                json_body={"value": {}},
            )
        )

        random_code = random_response.get("data", {}).get("randomCode")

        if not random_code:
            raise HomeAssistantError("Could not get remote unlock random code")

        unlock_payload = {
            "value": {
                "unLockInfo": {
                    "bindCode": bind_code,
                    "randomCode": random_code,
                    "type": EZVIZ_REMOTE_UNLOCK_TYPE,
                    "userName": self.entry.data.get(CONF_EMAIL),
                }
            }
        }

        return await self.hass.async_add_executor_job(
            partial(
                self.mqtt.client._request_json,
                "PUT",
                (
                    f"/v3/iot-feature/action/{serial}/DoorLock/0/DoorLockMgr/"
                    "RemoteUnlockReq"
                ),
                json_body=unlock_payload,
            )
        )
