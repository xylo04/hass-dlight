"""Platform for light integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from .const import CONF_IP, CONF_DEVICE_ID, DOMAIN
from .dlight import get_device_info, get_device_states, turn_on, turn_off, CannotConnect, WrongId

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import LightEntity, ColorMode, COLOR_MODE_COLOR_TEMP

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP): str,
        vol.Required(CONF_DEVICE_ID): str,
    }
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    data = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.info(data)
    ip = data[CONF_IP]
    device_id = data[CONF_DEVICE_ID]

    try:
        response = await get_device_info(ip, device_id)
        async_add_entities([Dlight(ip, device_id, response.get("swVersion"), response.get("hwVersion"), response.get("deviceModel"))])
    except (CannotConnect, WrongId) as e:
        _LOGGER.error("Failed to connect to light", exc_info=True)
        return

def brightness_to_device(brightness):
    if brightness is None:
        return None
    return round(100*brightness/255)

def brightness_to_hass(brightness):
    if brightness is None:
        return None
    return round(255*brightness/100)

class Dlight(LightEntity):
    _attr_has_entity_name: bool = True
    _attr_icon: str = "mdi:lamp"
    # Light supports 2600 - 6000K
    _attr_min_mireds: int = round(1000000 / 6000)
    _attr_max_mireds: int = round(1000000 / 2600)

    ip: str
    device_id: str

    swVersion: str
    hwVersion: str
    model: str

    def __init__(self, ip:str, device_id:str, swVersion:str, hwVersion:str, model:str) -> None:
        self.ip = ip
        self.device_id = device_id
        self._attr_unique_id = device_id
        self._attr_name = device_id
        self._attr_assumed_state = False
        self._attr_color_mode = COLOR_MODE_COLOR_TEMP
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
        self._attr_should_poll = True
        self.swVersion = swVersion
        self.hwVersion = hwVersion
        self.model = model

    @property
    def device_info(self):
        return {
            "manufacturer": "Google",
            "model": self.model,
            "name": "dLight",
            "sw_version": self.swVersion,
            "hw_version": self.hwVersion,
            "identifiers": {
                (DOMAIN, self.device_id),
            },
        }

    async def async_update(self):
        try:
            state = await get_device_states(self.ip, self.device_id)
        except:
            _LOGGER.error("Failed to update state", exc_info=True)
            self._attr_available = False
            return

        if state.get("status") != "SUCCESS":
            self._attr_available = False
            _LOGGER.warn(f"Unknown status in data {state}")
            return

        self._attr_available = True
        states = state.get("states")
        _LOGGER.debug(states)
        if states is None:
            self._attr_is_on = None
            self._attr_brightness = None
            self._attr_color_temp = None
        else:
            self._attr_is_on = states.get("on", None)
            self._attr_brightness = brightness_to_hass(states.get("brightness", None))
            color_temp = states.get("color", {}).get("temperature", None)
            if color_temp is not None:
                self._attr_color_temp = round(1000000 / color_temp)
            else:
                self._attr_color_temp = None

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug(f"Turn on {kwargs} b: {self._attr_brightness} t: {self._attr_color_temp}")
        brightness = None
        if kwargs.get("brightness") is not None:
            brightness = brightness_to_device(kwargs.get("brightness"))

        temperature = None
        if kwargs.get("color_temp") is not None:
            temperature = round(1000000 / kwargs.get("color_temp"), -2)

        status = await turn_on(self.ip, self.device_id, brightness, temperature)
        if status.get("on") is not None:
            self._attr_is_on = status.get("on")
        if status.get("brightness") is not None:
            self._attr_brightness = brightness_to_hass(status.get("brightness"))
        _LOGGER.info(status)

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug(f"Turn off {kwargs} b: {self._attr_brightness} t: {self._attr_color_temp}")
        status = await turn_off(self.ip, self.device_id)
        if status.get("on") is not None:
            self._attr_is_on = status.get("on")
        _LOGGER.debug(status)
