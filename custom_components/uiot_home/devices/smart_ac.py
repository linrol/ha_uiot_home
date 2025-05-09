import json
import logging

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from typing import Any
_LOGGER = logging.getLogger(__name__)

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
    pk = climate_data.get("properties_key")
    self.power_switch_key = pk.get("powerSwitch")
    self.target_temperature_key = pk.get("targetTemperature")
    self.wind_speed_key = pk.get("thermostatMode")
    self.thermostat_mode_key = pk.get("windSpeed")
    self.hass = hass
    self._uiot_dev = uiot_dev
    self._attr_min_temp = 16
    self._attr_max_temp = 32
    self._attr_target_temperature_step = 1
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
      self._attr_is_on = properties_data.get(self.power_switch_key, "") != "off"
      self._attr_target_temperature = properties_data.get(self.target_temperature_key, 22)
      self._attr_hvac_mode = get_device_hvac_model(properties_data.get(self.thermostat_mode_key, ""), self._attr_is_on)
      self._attr_fan_mode = get_device_fan_model(properties_data.get(self.wind_speed_key, ""))

    if climate_data.get("deviceOnlineState", "") == 0:
      self._attr_available = False
    else:
      self._attr_available = True
    _LOGGER.debug("_attr_available=%d", self._attr_available)

    self._attr_device_info = {
      "identifiers": {("UIOT", f"ac_{self.mac}_{self._attr_unique_id}")},
      "name": f"{climate_data.get('deviceName', "")}",
      "manufacturer": "uiot_home",
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

    if payload_str.get(self.power_switch_key, ""):
      power_switch = payload_str.get(self.power_switch_key, "")
      power_switch_status = power_switch == "on"
      if self._attr_is_on == power_switch_status:
        _LOGGER.debug("powerSwitch 不需要更新 !")
      else:
        self._attr_is_on = power_switch_status
        _LOGGER.debug("_attr_is_on:%s", self._attr_is_on)

    if payload_str.get(self.target_temperature_key, ""):
      if self._attr_current_temperature == payload_str.get(self.target_temperature_key, 25):
        _LOGGER.debug("targetTemperature 不需要更新 !")
      else:
        self._attr_current_temperature = payload_str.get(self.target_temperature_key, 25)
        _LOGGER.debug("_attr_current_temperature:%s", self._attr_current_temperature)

    if payload_str.get(self.wind_speed_key, ""):
      if self._attr_fan_mode == get_device_fan_model(payload_str.get(self.wind_speed_key, "")):
        _LOGGER.debug("windSpeed 不需要更新 !")
      else:
        self._attr_fan_mode = get_device_fan_model(payload_str.get(self.wind_speed_key, ""))
        _LOGGER.debug("_attr_fan_mode:%s", self._attr_fan_mode)

    if payload_str.get(self.thermostat_mode_key, ""):
      if self._attr_hvac_mode == get_device_hvac_model(payload_str.get(self.thermostat_mode_key, ""), self._attr_is_on):
        _LOGGER.debug("thermostatMode 不需要更新 !")
      else:
        self._attr_hvac_mode = get_device_hvac_model(payload_str.get(self.thermostat_mode_key, ""), self._attr_is_on)
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
    temperature = self._attr_target_temperature
    fan_mode = self._attr_fan_mode
    self._attr_is_on = True
    msg_data = {self.power_switch_key: "on"}
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    if temperature:
      msg_data = {self.target_temperature_key: int(temperature)}
      _LOGGER.debug("msg_data:%s", msg_data)
      await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    if fan_mode:
      msg_data = {self.wind_speed_key: "mid" if fan_mode == "medium" else fan_mode}
      _LOGGER.debug("msg_data:%s", msg_data)
      await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_turn_off(self, **kwargs: Any) -> None:
    """Turn the switch off."""
    msg_data = {self.power_switch_key: "off"}
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
    if not self._attr_is_on:
      return
    msg_data = {}
    if fan_mode == "medium":
      msg_data[self.wind_speed_key] = "mid"
    else:
      msg_data[self.wind_speed_key] = fan_mode
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_set_temperature(self, **kwargs: Any) -> None:
    temperature = kwargs[ATTR_TEMPERATURE]
    self._attr_target_temperature = temperature
    if not self._attr_is_on:
      return
    # 单一温度
    msg_data = {self.target_temperature_key: int(self._attr_target_temperature)}
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
      msg_data[self.thermostat_mode_key] = "cool"
    elif hvac_mode == HVACMode.HEAT:
      msg_data[self.thermostat_mode_key] = "heat"
    elif hvac_mode == HVACMode.FAN_ONLY:
      msg_data[self.thermostat_mode_key] = "fan"
    elif hvac_mode == HVACMode.DRY:
      msg_data[self.thermostat_mode_key] = "dehumidification"
    else:
      msg_data[self.thermostat_mode_key] = "off"
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()