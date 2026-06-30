"""Lock platform for EZVIZ Smart Lock."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVICE_SERIAL,
    DOMAIN,
    EVENT_DOOR_OPENED,
    EVENT_PASSCODE_ADDED,
    EVENT_REMOTE_UNLOCK,
    EVENT_UNKNOWN,
    UNLOCK_RESET_SECONDS,
)
from .coordinator import EzvizCoordinator


EVENT_LABELS = {
    EVENT_DOOR_OPENED: "Door opened",
    EVENT_REMOTE_UNLOCK: "Remote unlock",
    EVENT_PASSCODE_ADDED: "Passcode added",
    EVENT_UNKNOWN: "Unknown",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZVIZ Smart Lock lock entity."""
    coordinator: EzvizCoordinator = hass.data[DOMAIN][entry.entry_id]

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
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: EzvizCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the EZVIZ Smart Lock entity."""
        self.coordinator = coordinator
        self.entry = entry

        serial = entry.data[CONF_DEVICE_SERIAL]

        self._attr_unique_id = f"{serial}_lock"
        self._attr_name = "Door"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name="EZVIZ Smart Lock",
            manufacturer="EZVIZ",
            model="DL05",
            serial_number=serial,
            configuration_url="https://www.ezviz.com/",
        )

        self._is_locked = True
        self._reset_task: asyncio.Task[None] | None = None

        self._last_user: str | None = None
        self._last_event: str | None = None
        self._last_event_label: str | None = None
        self._last_event_code: str | None = None
        self._last_alert: str | None = None
        self._last_event_time: str | None = None

        self._unsubscribe: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        self._unsubscribe = self.coordinator.register_callback(
            self._handle_ezviz_event,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callbacks when entity is removed."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

        if self._reset_task is not None:
            self._reset_task.cancel()

            with suppress(asyncio.CancelledError):
                await self._reset_task

            self._reset_task = None

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
            "remote_unlock_enabled": self.coordinator.remote_unlock_enabled,
        }

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock command is not supported."""
        raise HomeAssistantError("Remote lock is not supported by this device")

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock remotely, if enabled."""
        if not self.coordinator.remote_unlock_enabled:
            raise HomeAssistantError(
                "Remote unlock is disabled in integration settings",
            )

        await self.coordinator.async_remote_unlock()

        self._mark_unlocked(
            event_name=EVENT_REMOTE_UNLOCK,
            user=None,
            event_code=None,
            alert="Remote unlock requested from Home Assistant",
        )

    def _handle_ezviz_event(self, event_data: dict[str, Any]) -> None:
        """Handle EZVIZ event."""
        event_name = event_data.get("event_name") or EVENT_UNKNOWN

        self._last_user = event_data.get("user")
        self._last_event = event_name
        self._last_event_label = EVENT_LABELS.get(event_name, event_name)
        self._last_event_code = event_data.get("event_code")
        self._last_alert = event_data.get("alert")
        self._last_event_time = dt_util.utcnow().isoformat(timespec="seconds")

        if event_name in (EVENT_DOOR_OPENED, EVENT_REMOTE_UNLOCK):
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
        self._last_event_time = dt_util.utcnow().isoformat(timespec="seconds")

        self._is_locked = False

        if self._reset_task is not None:
            self._reset_task.cancel()

        self._reset_task = self.hass.async_create_task(
            self._reset_to_locked(),
        )

        self.schedule_update_ha_state()

    async def _reset_to_locked(self) -> None:
        """Reset lock state to locked after a short delay."""
        await asyncio.sleep(UNLOCK_RESET_SECONDS)

        self._is_locked = True
        self._reset_task = None
        self.schedule_update_ha_state()
