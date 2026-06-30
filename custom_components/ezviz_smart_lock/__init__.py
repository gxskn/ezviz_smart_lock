"""The EZVIZ Smart Lock integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import EzvizCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: vol.Schema) -> bool:
    """Set up the EZVIZ Smart Lock integration."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up EZVIZ Smart Lock from a config entry."""
    coordinator = EzvizCoordinator(hass, entry)

    await coordinator.async_setup()
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload an EZVIZ Smart Lock config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if not unload_ok:
        return False

    coordinator: EzvizCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

    await coordinator.async_stop()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True
