"""Constants for the EZVIZ Smart Lock integration."""

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform

DOMAIN = "ezviz_smart_lock"

CONF_TOKEN = "token"
CONF_DEVICE_SERIAL = "device_serial"
CONF_ENABLE_REMOTE_UNLOCK = "enable_remote_unlock"

PLATFORMS: list[Platform] = [
    Platform.LOCK,
]

UNLOCK_RESET_SECONDS = 5

EVENT_DOOR_OPENED = "door_opened"
EVENT_REMOTE_UNLOCK = "remote_unlock"
EVENT_PASSCODE_ADDED = "passcode_added"
EVENT_UNKNOWN = "unknown"

HA_EVENT_EZVIZ_SMART_LOCK = "ezviz_smart_lock_event"
