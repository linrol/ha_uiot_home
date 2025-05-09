"""Switch platform for UIOT integration."""

import logging

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .uiot_api.const import DOMAIN
from .uiot_api.uiot_device import UIOTDevice, is_entity_exist
from .devices.smart_ac import SmartAC
_LOGGER = logging.getLogger(__name__)

properties_ac_keys = {"powerSwitch": "airConditionPowerSwitch",
                      "targetTemperature": "airConditionTargetTemperature",
                      "thermostatMode": "airConditionThermostatMode",
                      "windSpeed": "airConditionWindSpeed"}

def climate_data_parse_list(climate_data, entities, hass) -> list:
  uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
  properties = climate_data.get("properties")
  if properties.get("powerSwitch"):
    climate_data["properties_key"] = properties_ac_keys
    entities.append(SmartAC(climate_data, uiot_dev, hass))
  return entities

async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
  """Set up the Switch platform from a config entry."""
  _LOGGER.debug("async_setup_entry climate")

  devices_data = hass.data[DOMAIN].get("devices", [])

  device_data = []
  for device in devices_data:
    if device.get("type") == "climate":
      _LOGGER.debug("climate")
      device_data.append(device)

  entities = []
  for climate_data in device_data:
    name = climate_data.get("deviceName", "")
    deviceId = climate_data.get("deviceId", "")
    _LOGGER.debug("name:%s", name)
    _LOGGER.debug("deviceId:%d", deviceId)
    entities = climate_data_parse_list(climate_data, entities, hass)
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
        if device.get("type") == "climate":
          _LOGGER.debug("climate")
          _LOGGER.debug("devices_data %s", devices_data)
          device_data.append(device)

      new_entities = []

      for climate_data in device_data:
        name = climate_data.get("deviceName", "")
        deviceId = climate_data.get("deviceId", "")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        if not is_entity_exist(hass, deviceId):
          new_entities = climate_data_parse_list(climate_data, new_entities, hass)

      if new_entities:
        async_add_entities(new_entities)

    except Exception as e:
      _LOGGER.error("Error processing config update: %s", e)
      raise

  signal = "mqtt_message_network_report"
  async_dispatcher_connect(hass, signal, handle_config_update)