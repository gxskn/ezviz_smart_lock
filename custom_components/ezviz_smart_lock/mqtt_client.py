"""MQTT client for EZVIZ Smart Lock."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from pyezvizapi import EzvizClient, MQTTClient

_LOGGER = logging.getLogger(__name__)

CONF_TOKEN = "token"
CONF_DEVICE_SERIAL = "device_serial"


def extract_type(metadata: str) -> str | None:
    """Extract event type from EZVIZ metadata."""
    for part in metadata.split("|"):
        if part.startswith("type="):
            return part.replace("type=", "")
    return None


def extract_user(ext: dict[str, Any]) -> str | None:
    """Extract user from EZVIZ extension payload."""
    value = ext.get("media_url_alt2")
    if not value:
        return None

    try:
        data = json.loads(base64.b64decode(value).decode("utf-8"))
        return data.get("user")
    except Exception:
        return None


def translate_event(event_code: str | None) -> str:
    """Translate EZVIZ event code to internal event name."""
    event_map = {
        "17011": "door_opened",
        "17026": "remote_unlock",
        "10231": "passcode_added",
    }
    return event_map.get(str(event_code), "unknown")


class EzvizMQTTClient:
    """EZVIZ MQTT client wrapper."""

    def __init__(self, hass, entry, coordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.config = dict(entry.data)
        self.coordinator = coordinator

        self.client: EzvizClient | None = None
        self.mqtt = None
        self.last_id = None

    def _get_current_token(self) -> dict:
        """Return current EZVIZ token."""
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

        event_code = None
        user = None
        metadata = ""

        if isinstance(ext_raw, str):
            parts = ext_raw.split(",")

            if len(parts) >= 15:
                user_b64 = parts[7]
                metadata = parts[14]

                try:
                    user_data = json.loads(base64.b64decode(user_b64).decode("utf-8"))
                    user = user_data.get("user")
                except Exception:
                    user = None

                event_code = extract_type(metadata)

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

    async def stop(self) -> None:
        """Stop EZVIZ MQTT client."""
        if self.mqtt:
            await self.hass.async_add_executor_job(self.mqtt.stop)