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
    except (CannotConnect, WrongId) as e:
        _LOGGER.error("Failed to connect to light", exc_info=True)
        return

    async_add_entities([Dlight(ip, device_id)])
    
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
    _attr_min_mireds: int = 1000000 / 2600
    _attr_max_mireds: int = 1000000 / 6000

    ip: str 
    device_id: str

    def __init__(self, ip:str, device_id:str) -> None:
        self.ip = ip
        self.device_id = device_id
        self._attr_name = f"dLight {device_id}"
        self._attr_unique_id = device_id
        self._attr_assumed_state = False
        self._attr_color_mode = COLOR_MODE_COLOR_TEMP
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
        self._attr_should_poll = True

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
        _LOGGER.info(states)
        if states is None:
            self._attr_is_on = None
            self._attr_brightness = None
            self._attr_color_temp = None
        else:
            self._attr_is_on = states.get("on", None)
            self._attr_brightness = brightness_to_hass(states.get("brightness", None))
            color_temp = states.get("color", {}).get("temperature", None)
            if color_temp is not None:
                self._attr_color_temp = 1000000 / color_temp
            else:
                self._attr_color_temp = None

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(f"Turn on {kwargs} b: {self._attr_brightness} t: {self._attr_color_temp}")
        brightness = None
        if kwargs.get("brightness") is not None:
            brightness = brightness_to_device(kwargs.get("brightness"))

        temperature = None
        if kwargs.get("color_temp") is not None:
            temperature = kwargs.get("color_temp") * 1000000

        status = await turn_on(self.ip, self.device_id, brightness, temperature)
        if status.get("on") is not None:
            self._attr_is_on = status.get("on")
        _LOGGER.info(status)

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(f"Turn off {kwargs} b: {self._attr_brightness} t: {self._attr_color_temp}")
        status = await turn_off(self.ip, self.device_id)
        if status.get("on") is not None:
            self._attr_is_on = status.get("on")
        _LOGGER.info(status)
    


    def scale_number(self, unscaled, to_min, to_max, from_min, from_max):
        if unscaled is None:
            return None
        return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min