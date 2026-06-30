"""Constants for the EZVIZ Smart Lock integration."""

from homeassistant.const import Platform

DOMAIN = "ezviz_smart_lock"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DEVICE_SERIAL = "device_serial"
CONF_ENABLE_REMOTE_UNLOCK = "enable_remote_unlock"

PLATFORMS: list[Platform] = [
    Platform.LOCK,
]

UNLOCK_RESET_SECONDS = 5