"""MQTT client for EZVIZ Smart Lock."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pyezvizapi import EzvizClient, MQTTClient

from .const import (
    CONF_DEVICE_SERIAL,
    CONF_TOKEN,
    EVENT_DOOR_OPENED,
    EVENT_PASSCODE_ADDED,
    EVENT_REMOTE_UNLOCK,
    EVENT_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

EZVIZ_EVENT_DOOR_OPENED = "17011"
EZVIZ_EVENT_REMOTE_UNLOCK = "17026"
EZVIZ_EVENT_PASSCODE_ADDED = "10231"


def extract_type(metadata: str) -> str | None:
    """Extract event type from EZVIZ metadata."""
    for part in metadata.split("|"):
        if part.startswith("type="):
            return part.removeprefix("type=")

    return None


def extract_user(ext: dict[str, Any]) -> str | None:
    """Extract user from EZVIZ extension payload."""
    value = ext.get("media_url_alt2")

    if not value:
        return None

    try:
        data = json.loads(base64.b64decode(value).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    user = data.get("user")

    if isinstance(user, str):
        return user

    return None


def translate_event(event_code: str | None) -> str:
    """Translate EZVIZ event code to internal event name."""
    event_map = {
        EZVIZ_EVENT_DOOR_OPENED: EVENT_DOOR_OPENED,
        EZVIZ_EVENT_REMOTE_UNLOCK: EVENT_REMOTE_UNLOCK,
        EZVIZ_EVENT_PASSCODE_ADDED: EVENT_PASSCODE_ADDED,
    }

    return event_map.get(str(event_code), EVENT_UNKNOWN)


class EzvizMQTTClient:
    """EZVIZ MQTT client wrapper."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator,
    ) -> None:
        """Initialize the EZVIZ MQTT client wrapper."""
        self.hass = hass
        self.entry = entry
        self.config = dict(entry.data)
        self.coordinator = coordinator

        self.client: EzvizClient | None = None
        self.mqtt: MQTTClient | None = None
        self.last_id: str | None = None

    def _get_current_token(self) -> dict[str, Any]:
        """Return current EZVIZ token."""
        if self.client is None:
            return {}

        return self.client._token

    async def start(self) -> None:
        """Start EZVIZ MQTT client."""
        token = self.config[CONF_TOKEN]

        self.client = EzvizClient(token=token)

        await self.hass.async_add_executor_job(self.client.login)

        new_token = self._get_current_token()

        if new_token != token:
            self.config[CONF_TOKEN] = new_token
            await self.coordinator.async_update_token(new_token)

        self.mqtt = MQTTClient(
            new_token,
            self.client._session,
            on_message_callback=self._on_message,
        )

        await self.hass.async_add_executor_job(self.mqtt.connect)

    def _on_message(self, msg: dict[str, Any]) -> None:
        """Handle EZVIZ MQTT message."""
        msg_id = msg.get("id")

        if msg_id == self.last_id:
            return

        self.last_id = msg_id

        alert = msg.get("alert", "")
        ext_raw = msg.get("ext", "")

        event_code: str | None = None
        user: str | None = None
        metadata = ""

        if isinstance(ext_raw, str):
            event_code, user, metadata = self._parse_string_ext(ext_raw)

        elif isinstance(ext_raw, dict):
            metadata = ext_raw.get("metadata", "")
            event_code = extract_type(metadata)
            user = extract_user(ext_raw)

        event_name = translate_event(event_code)

        event_data = {
            "id": msg_id,
            "event_code": event_code,
            "event_name": event_name,
            "user": user,
            "alert": alert,
            "metadata": metadata,
            "device": self.config.get(CONF_DEVICE_SERIAL),
        }

        self.coordinator.handle_event(event_data)

    @staticmethod
    def _parse_string_ext(ext_raw: str) -> tuple[str | None, str | None, str]:
        """Parse EZVIZ string extension payload."""
        parts = ext_raw.split(",")

        if len(parts) < 15:
            return None, None, ""

        user_b64 = parts[7]
        metadata = parts[14]
        event_code = extract_type(metadata)
        user = None

        try:
            user_data = json.loads(base64.b64decode(user_b64).decode("utf-8"))
            parsed_user = user_data.get("user")

            if isinstance(parsed_user, str):
                user = parsed_user

        except (ValueError, TypeError, json.JSONDecodeError):
            user = None

        return event_code, user, metadata

    async def stop(self) -> None:
        """Stop EZVIZ MQTT client."""
        if self.mqtt is None:
            return

        await self.hass.async_add_executor_job(self.mqtt.stop)
        self.mqtt = None
