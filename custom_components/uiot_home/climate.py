"""Switch platform for UIOT integration."""

import json
import logging

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .uiot_api.const import COMPANY, DOMAIN
from .uiot_api.uiot_device import UIOTDevice, is_entity_exist
from typing import Any

_LOGGER = logging.getLogger(__name__)


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
    uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
    entities.append(SmartAC(climate_data, uiot_dev, hass))

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
        uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
        if not is_entity_exist(hass, deviceId):
          new_entities.append(SmartAC(climate_data, uiot_dev, hass))

      if new_entities:
        async_add_entities(new_entities)

    except Exception as e:
      _LOGGER.error("Error processing config update: %s", e)
      raise

  signal = "mqtt_message_network_report"
  async_dispatcher_connect(hass, signal, handle_config_update)


def get_device_hvac_model(mode, power):
  if not power:
    return HVACMode.OFF
  elif mode == "cool":
    return HVACMode.COOL
  elif mode == "heat":
    return HVACMode.HEAT
  elif mode == "fan":
    return HVACMode.FAN_ONLY
  elif mode == "dehumidification":
    return HVACMode.DRY
  else:
    return HVACMode.OFF

def get_device_fan_model(mode):
  if mode == "low":
    return "low"
  elif mode == "mid":
    return "medium"
  elif mode == "high":
    return "high"
  else:
    return "low"


class SmartAC(ClimateEntity):
  """Representation of a UIOT home Switch."""

  def __init__(self, climate_data, uiot_dev, hass: HomeAssistant) -> None:
    """Initialize the switch."""
    self.hass = hass
    self._uiot_dev: UIOTDevice = uiot_dev
    self._attr_min_temp = 16
    self._attr_max_temp = 32
    self._attr_temperature_unit = UnitOfTemperature.CELSIUS
    self._attr_supported_features = (ClimateEntityFeature.FAN_MODE |
                                     ClimateEntityFeature.TARGET_TEMPERATURE)
    self._attr_hvac_modes = [HVACMode.COOL, HVACMode.HEAT,  HVACMode.FAN_ONLY, HVACMode.DRY, HVACMode.OFF]
    self._attr_fan_modes = ["low", "medium", "high"]
    self._attr_name = climate_data.get("deviceName", "")
    self._attr_unique_id = str(climate_data.get("deviceId", ""))
    self.mac = climate_data.get("deviceMac", "")
    properties_data = climate_data.get("properties", "")
    if properties_data:
      self._attr_is_on = properties_data.get("powerSwitch", "") != "off"
      self._attr_target_temperature = properties_data.get("targetTemperature", 25)
      self._attr_hvac_mode = get_device_hvac_model(properties_data.get("thermostatMode", ""), self._attr_is_on)
      self._attr_fan_mode = get_device_fan_model(properties_data.get("windSpeed", ""))

    if climate_data.get("deviceOnlineState", "") == 0:
      self._attr_available = False
    else:
      self._attr_available = True
    _LOGGER.debug("_attr_available=%d", self._attr_available)

    self._attr_device_info = {
      "identifiers": {(f"{DOMAIN}", f"{self.mac}")},
      "name": f"{climate_data.get('deviceName', "")}",
      "manufacturer": f"{COMPANY}",
      "suggested_area": f"{climate_data.get('roomName', "")}",
      "model": f"{climate_data.get('model', "")}",
      "sw_version": f"{climate_data.get('softwareVersion', "")}",
      "hw_version": f"{climate_data.get('hardwareVersion', "")}",
    }
    _LOGGER.debug("初始化设备: %s", self._attr_name)
    _LOGGER.debug("deviceId=%s", self._attr_unique_id)
    _LOGGER.debug("mac=%s", self.mac)

    # 订阅状态主题以监听本地控制的变化
    signal = "mqtt_message_received_state_report"
    async_dispatcher_connect(hass, signal, self._handle_mqtt_message)

  @callback
  def _handle_mqtt_message(self, msg):
    """Handle incoming MQTT messages for state updates."""
    # _LOGGER.debug(f"mqtt_message的数据:{msg.payload}")
    if self.hass is None:
      return
    msg_data = json.loads(msg.payload)

    if "online_report" in msg.topic:
      data = msg_data.get("data")
      devices_data = data.get("deviceList")
      for d in devices_data:
        deviceId = d.get("deviceId", "")
        netState = d.get("netState", "")
        if str(deviceId) == self._attr_unique_id:
          _LOGGER.debug(
              "设备在线状态变化 deviceId: %d,netState:%d", deviceId, netState
          )
          if netState == 0:
            self._attr_available = False
          else:
            self._attr_available = True
          self.async_write_ha_state()
      return

    try:
      data = msg_data.get("data", "")
      if self._attr_unique_id == str(data.get("deviceId", "")):
        payload_str = data.get("properties", "")
      else:
        return
    except UnicodeDecodeError as e:
      _LOGGER.error("Failed to decode message payload: %s", e)
      return

    if not payload_str:
      _LOGGER.warning("Received empty payload")
      return

    _LOGGER.debug("收到设备状态更新: %s", payload_str)

    if payload_str.get("powerSwitch", ""):
      power_switch = payload_str.get("powerSwitch", "")
      if power_switch == "on":
        powerSwitch_status = True
      elif power_switch == "off":
        powerSwitch_status = False
      else:
        powerSwitch_status = False
      if self._attr_is_on == powerSwitch_status:
        _LOGGER.debug("powerSwitch 不需要更新 !")
      else:
        self._attr_is_on = powerSwitch_status
        _LOGGER.debug("_attr_is_on:%s", self._attr_is_on)

    if payload_str.get("targetTemperature", ""):
      if self._attr_target_temperature == payload_str.get("targetTemperature", 25):
        _LOGGER.debug("targetTemperature 不需要更新 !")
      else:
        self._attr_target_temperature = payload_str.get("targetTemperature", 25)
        _LOGGER.debug("_attr_target_temperature:%s", self._attr_target_temperature)

    if payload_str.get("windSpeed", ""):
      if self._attr_fan_mode == get_device_fan_model(payload_str.get("windSpeed", "")):
        _LOGGER.debug("windSpeed 不需要更新 !")
      else:
        self._attr_fan_mode = get_device_fan_model(payload_str.get("windSpeed", ""))
        _LOGGER.debug("_attr_fan_mode:%s", self._attr_fan_mode)

    if payload_str.get("thermostatMode", ""):
      if self._attr_hvac_mode == get_device_hvac_model(payload_str.get("thermostatMode", ""), self._attr_is_on):
        _LOGGER.debug("thermostatMode 不需要更新 !")
      else:
        self._attr_hvac_mode = get_device_hvac_model(payload_str.get("thermostatMode", ""), self._attr_is_on)
        _LOGGER.debug("_attr_hvac_mode:%s", self._attr_hvac_mode)

    deviceOnlineState = data.get("deviceOnlineState", "")
    if deviceOnlineState == 0:
      self._attr_available = False
    else:
      self._attr_available = True

    self.async_write_ha_state()

  @property
  def is_on(self) -> bool:
    """Return true if switch is on."""
    return self._attr_is_on

  @property
  def fan_mode(self) -> str | None:
    return self._attr_fan_mode  # 你自己维护的当前风速值

  async def async_turn_on(
      self,
      percentage: int | None = None,
      preset_mode: str | None = None,
      **kwargs: Any,
  ) -> None:
    """Turn the switch on."""
    msg_data = {}
    msg_data["powerSwitch"] = "on"
    self._attr_is_on = True
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_turn_off(self, **kwargs: Any) -> None:
    """Turn the switch off."""
    msg_data = {}
    msg_data["powerSwitch"] = "off"
    self._attr_is_on = False
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_update(self) -> None:
    """Fetch new state data for this switch."""
    # _LOGGER.info("Updating switch state.")

  async def async_set_fan_mode(self, fan_mode: str) -> None:
    # 控制风速的逻辑
    self._attr_fan_mode = fan_mode
    msg_data = {}
    if fan_mode == "medium":
      msg_data["windSpeed"] = "mid"
    else:
      msg_data["windSpeed"] = fan_mode
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_set_temperature(self, **kwargs: Any) -> None:
    temperature = kwargs[ATTR_TEMPERATURE]
    self._attr_target_temperature = temperature
    # 单一温度
    msg_data = {"targetTemperature": self._attr_target_temperature}
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    """Set new target HVAC mode."""
    self._attr_hvac_mode = hvac_mode

    # 发送命令到设备（这里按你的 JSON 格式组装）
    if hvac_mode == HVACMode.OFF:
      await self.async_turn_off()
      return
    if not self._attr_is_on:
      await self.async_turn_on()
    msg_data = {}
    if hvac_mode == HVACMode.COOL:
      msg_data["thermostatMode"] = "cool"
    elif hvac_mode == HVACMode.HEAT:
      msg_data["thermostatMode"] = "heat"
    elif hvac_mode == HVACMode.FAN_ONLY:
      msg_data["thermostatMode"] = "fan"
    elif hvac_mode == HVACMode.DRY:
      msg_data["thermostatMode"] = "dehumidification"
    else:
      msg_data["thermostatMode"] = "off"
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()