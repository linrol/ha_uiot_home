import json
import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from typing import Any

_LOGGER = logging.getLogger(__name__)

class FreshAir(FanEntity):
  """Representation of a UIOT home Switch."""

  def __init__(self, fan_data, uiot_dev, hass: HomeAssistant) -> None:
    """Initialize the switch."""
    pk = fan_data.get("properties_key")
    self.power_switch_key = pk.get("powerSwitch")
    self.wind_speed_key = pk.get("windSpeed")
    self.hass = hass
    self._attr_name = fan_data.get("deviceName", "")
    self._attr_unique_id = str(fan_data.get("deviceId", ""))
    self.mac = fan_data.get("deviceMac", "")
    self._uiot_dev = uiot_dev
    self._attr_supported_features = (
        FanEntityFeature.TURN_ON |
        FanEntityFeature.TURN_OFF |
        FanEntityFeature.SET_SPEED
    )
    properties_data = fan_data.get("properties", "")
    if properties_data:
      powerSwitch = properties_data.get(self.power_switch_key, "")
      if powerSwitch == "off":
        self._attr_is_on = False
      else:
        self._attr_is_on = True
      windSpeed = properties_data.get(self.wind_speed_key, "")
      if windSpeed == "low":
        self._attr_percentage = 33
      elif windSpeed == "mid":
        self._attr_percentage = 66
      elif windSpeed == "high":
        self._attr_percentage = 100
      else:
        self._attr_percentage = 0

    deviceOnlineState = fan_data.get("deviceOnlineState", "")
    if deviceOnlineState == 0:
      self._attr_available = False
    else:
      self._attr_available = True
    _LOGGER.debug("_attr_available=%d", self._attr_available)

    self._attr_device_info = {
      "identifiers": {("UIOT", f"air_{self.mac}_{self._attr_unique_id}")},
      "name": f"{fan_data.get('deviceName', "")}",
      "manufacturer": "uiot_home",
      "suggested_area": f"{fan_data.get('roomName', "")}",
      "model": f"{fan_data.get('model', "")}",
      "sw_version": f"{fan_data.get('softwareVersion', "")}",
      "hw_version": f"{fan_data.get('hardwareVersion', "")}",
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

    if payload_str.get(self.wind_speed_key, ""):
      wind_speed = payload_str.get(self.wind_speed_key, "")
      if wind_speed == "low":
        windSpeed_value = 33
      elif wind_speed == "mid":
        windSpeed_value = 66
      elif wind_speed == "high":
        windSpeed_value = 100
      else:
        windSpeed_value = 0
      if self._attr_percentage == windSpeed_value:
        _LOGGER.debug("windSpeed 不需要更新 !")
      else:
        self._attr_percentage = windSpeed_value
        _LOGGER.debug("_attr_percentage:%s", self._attr_percentage)

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

  async def async_turn_on(
      self,
      percentage: int | None = None,
      preset_mode: str | None = None,
      **kwargs: Any,
  ) -> None:
    """Turn the switch on."""
    msg_data = {}
    msg_data[self.power_switch_key] = "on"
    self._attr_is_on = True
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_turn_off(self, **kwargs: Any) -> None:
    """Turn the switch off."""
    msg_data = {}
    msg_data[self.power_switch_key] = "off"
    self._attr_is_on = False
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()

  async def async_update(self) -> None:
    """Fetch new state data for this switch."""
    # _LOGGER.info("Updating switch state.")

  async def async_set_percentage(self, percentage: int) -> None:
    """Set the speed of the fan, as a percentage."""
    if percentage == 0:
      await self.async_turn_off()
    msg_data = {}
    if percentage <= 33:
      msg_data[self.wind_speed_key] = "low"
    elif percentage <= 66:
      msg_data[self.wind_speed_key] = "mid"
    elif percentage <= 100:
      msg_data[self.wind_speed_key] = "high"
    _LOGGER.debug("msg_data:%s", msg_data)
    await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
    self.async_write_ha_state()