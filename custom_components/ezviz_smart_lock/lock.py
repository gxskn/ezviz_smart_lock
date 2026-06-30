"""Lock platform for EZVIZ Smart Lock."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import CONF_DEVICE_SERIAL, DOMAIN, UNLOCK_RESET_SECONDS


EVENT_LABELS = {
    "door_opened": "Door opened",
    "remote_unlock": "Remote unlock",
    "passcode_added": "Passcode added",
    "unknown": "Unknown",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up EZVIZ Smart Lock lock entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EzvizSmartLockEntity(
                coordinator=coordinator,
                entry=entry,
            )
        ]
    )


class EzvizSmartLockEntity(LockEntity):
    """EZVIZ Smart Lock entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry

        serial = entry.data[CONF_DEVICE_SERIAL]

        self._attr_unique_id = f"{serial}_lock"
        self._attr_name = "Door"

        self._is_locked = True
        self._reset_task: asyncio.Task | None = None

        self._last_user = None
        self._last_event = None
        self._last_event_label = None
        self._last_event_code = None
        self._last_alert = None
        self._last_event_time = None

        self._unsubscribe = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        self._unsubscribe = self.coordinator.register_callback(
            self._handle_ezviz_event
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callbacks when entity is removed."""
        if self._unsubscribe:
            self._unsubscribe()

        if self._reset_task:
            self._reset_task.cancel()

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._is_locked

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity state attributes."""
        return {
            "last_user": self._last_user,
            "last_event": self._last_event,
            "last_event_label": self._last_event_label,
            "last_event_code": self._last_event_code,
            "last_alert": self._last_alert,
            "last_event_time": self._last_event_time,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        serial = self.entry.data[CONF_DEVICE_SERIAL]

        return DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name="EZVIZ Smart Lock",
            manufacturer="EZVIZ",
            model="DL05",
            serial_number=serial,
            configuration_url="https://www.ezviz.com/",
        )

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock command is not supported."""
        raise HomeAssistantError("Remote lock is not supported by this device")

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock remotely, if enabled."""
        if not self.coordinator.remote_unlock_enabled:
            raise HomeAssistantError(
                "Remote unlock is disabled in integration settings"
            )

        await self.coordinator.async_remote_unlock()

        self._mark_unlocked(
            event_name="remote_unlock",
            user=None,
            event_code=None,
            alert="Remote unlock requested from Home Assistant",
        )

    def _handle_ezviz_event(self, event_data: dict[str, Any]) -> None:
        """Handle EZVIZ event."""
        event_name = event_data.get("event_name") or "unknown"

        self._last_user = event_data.get("user")
        self._last_event = event_name
        self._last_event_label = EVENT_LABELS.get(event_name, event_name)
        self._last_event_code = event_data.get("event_code")
        self._last_alert = event_data.get("alert")
        self._last_event_time = datetime.now().isoformat(timespec="seconds")

        if event_name in ("door_opened", "remote_unlock"):
            self._mark_unlocked(
                event_name=event_name,
                user=self._last_user,
                event_code=self._last_event_code,
                alert=self._last_alert,
            )
            return

        self.schedule_update_ha_state()

    def _mark_unlocked(
        self,
        *,
        event_name: str,
        user: str | None,
        event_code: str | None,
        alert: str | None,
    ) -> None:
        """Temporarily mark the lock as unlocked."""
        self._last_user = user
        self._last_event = event_name
        self._last_event_label = EVENT_LABELS.get(event_name, event_name)
        self._last_event_code = event_code
        self._last_alert = alert
        self._last_event_time = datetime.now().isoformat(timespec="seconds")

        self._is_locked = False

        if self._reset_task:
            self._reset_task.cancel()

        self._reset_task = self.hass.async_create_task(self._reset_to_locked())

        self.schedule_update_ha_state()

    async def _reset_to_locked(self) -> None:
        """Reset lock state to locked after a short delay."""
        await asyncio.sleep(UNLOCK_RESET_SECONDS)

        self._is_locked = True
        self.schedule_update_ha_state()