"""Switch platform for UIOT integration."""

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .uiot_api.const import DOMAIN
from .uiot_api.uiot_device import UIOTDevice, is_entity_exist
from .devices.fresh_air import FreshAir

_LOGGER = logging.getLogger(__name__)

properties_keys = {"powerSwitch": "powerSwitch", "windSpeed": "windSpeed"}
properties_3h1_keys = {"powerSwitch": "freshAirPowerSwitch", "windSpeed": "freshAirWindSpeed"}

def fan_data_parse_list(fan_data, entities, hass) -> list:
    uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
    properties = fan_data.get("properties")
    if properties.get("powerSwitch"):
        fan_data["properties_key"] = properties_keys
        entities.append(FreshAir(fan_data, uiot_dev, hass))
    if properties.get("freshAirPowerSwitch"):
        fan_data["properties_key"] = properties_3h1_keys
        entities.append(FreshAir(fan_data, uiot_dev, hass))
    return entities

async def async_setup_entry(hass: HomeAssistant, entry,
    async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Switch platform from a config entry."""
    _LOGGER.debug("async_setup_entry fan")

    devices_data = hass.data[DOMAIN].get("devices", [])

    device_data = []
    for device in devices_data:
        if device.get("type") == "fan":
            _LOGGER.debug("fan")
            device_data.append(device)

    entities = []
    for fan_data in device_data:
        name = fan_data.get("deviceName", "")
        deviceId = fan_data.get("deviceId", "")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        entities = fan_data_parse_list(fan_data, entities, hass)
    if entities:
        async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        if hass is None:
            return
        try:
            devices_data = msg
            device_data = []
            for device in devices_data:
                if device.get("type") == "fan":
                    _LOGGER.debug("fan")
                    _LOGGER.debug("devices_data %s", devices_data)
                    device_data.append(device)

            new_entities = []
            for fan_data in device_data:
                name = fan_data.get("deviceName", "")
                deviceId = fan_data.get("deviceId", "")
                _LOGGER.debug("name:%s", name)
                _LOGGER.debug("deviceId:%d", deviceId)
                if not is_entity_exist(hass, deviceId):
                    new_entities = fan_data_parse_list(fan_data, new_entities, hass)
            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)