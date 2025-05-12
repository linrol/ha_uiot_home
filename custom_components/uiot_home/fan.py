"""Fan platform for UIOT integration."""

import json
import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .uiot_api.const import COMPANY, DOMAIN
from .uiot_api.uiot_device import UIOTDevice, is_entity_exist

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Switch platform from a config entry."""
    _LOGGER.debug("async_setup_entry fan")

    devices_data = hass.data[DOMAIN].get("devices", [])

    device_data = []
    for device in devices_data:
        if device.get("type") == "fan":
            _LOGGER.debug("fan")
            device_data.append(device)

    entities = []
    for c_data in device_data:
        name = c_data.get("deviceName", "")
        deviceId = c_data.get("deviceId", "")
        channelNum = c_data.get("channelNum", "")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        _LOGGER.debug("channelNum:%d", channelNum)

        uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
        entities.append(Fan(c_data, uiot_dev, hass))

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

            for s_data in device_data:
                name = s_data.get("deviceName", "")
                deviceId = s_data.get("deviceId", "")
                channelNum = s_data.get("channel", "")
                _LOGGER.debug("name:%s", name)
                _LOGGER.debug("deviceId:%d", deviceId)
                _LOGGER.debug("channelNum:%d", channelNum)
                uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
                if not is_entity_exist(hass, deviceId):
                    new_entities.append(Fan(s_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)


class Fan(FanEntity):
    """Representation of a UIOT home Fan."""

    def __init__(self, c_data, uiot_dev, hass: HomeAssistant) -> None:
        """Initialize the Fan."""
        self.hass = hass
        self._attr_name = c_data.get("deviceName", "")
        self._attr_unique_id = str(c_data.get("deviceId", ""))
        self.mac = self._attr_unique_id
        self._uiot_dev: UIOTDevice = uiot_dev
        properties_data = c_data.get("properties", "")
        power_switch = properties_data.get("powerSwitch", "off")
        if power_switch == "off":
            self._attr_is_on = False
        else:
            self._attr_is_on = True
        deviceOnlineState = c_data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True
        _LOGGER.debug("_attr_available=%d", self._attr_available)
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.TURN_ON
        )
        self._attr_speed_count = 100
        deviceName = self._attr_name
        self._attr_device_info = {
            "identifiers": {(f"{DOMAIN}", f"{self.mac}")},
            "name": f"{deviceName}",
            "manufacturer": f"{COMPANY}",
            "suggested_area": f"{c_data.get('roomName', "")}",
            "model": f"{c_data.get('model', "")}",
            "sw_version": f"{c_data.get('softwareVersion', "")}",
            "hw_version": f"{c_data.get('hardwareVersion', "")}",
        }
        _LOGGER.debug("初始化设备: %s", self._attr_name)
        _LOGGER.debug("deviceId=%s", self._attr_unique_id)
        _LOGGER.debug("mac=%s", self.mac)

        if "fan_modes" in properties_data:
            self._fan_modes = properties_data.get("fan_modes", "")
        else:
            self._fan_modes = ["low", "mid", "high"]
        self._percentage_step = 100 / len(self._fan_modes)
        _LOGGER.debug("self._percentage_step=%d", self._percentage_step)
        _LOGGER.debug("fan_mode=%s", self._fan_modes[2])
        self._fan_speed = 0
        windSpeed = properties_data.get("windSpeed", "low")
        if windSpeed in self._fan_modes:
            self._fan_speed = (
                self._fan_modes.index(windSpeed) + 1
            ) * self._percentage_step

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

        if "powerSwitch" in payload_str:
            power_switch = payload_str.get("powerSwitch", "")
            if power_switch == "off":
                self._attr_is_on = False
            else:
                self._attr_is_on = True
        if "windSpeed" in payload_str:
            windSpeed = payload_str.get("windSpeed", "")
            if windSpeed in self._fan_modes:
                self._fan_speed = (
                    self._fan_modes.index(windSpeed) + 1
                ) * self._percentage_step
        _LOGGER.debug("_fan_speed: %d", self._fan_speed)
        deviceOnlineState = data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True

        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Fan is on."""
        return self._attr_is_on

    @property
    def percentage(self) -> int:
        """Fan fan speed."""
        return self._fan_speed

    async def async_turn_on(self, percentage, preset_mode, **kwargs) -> None:
        """Turn the fan on."""
        msg_data = {}
        msg_data["powerSwitch"] = "on"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        msg_data = {}
        msg_data["powerSwitch"] = "off"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Fan async set percentage."""
        _LOGGER.debug("percentage:%d", percentage)
        self._fan_speed = percentage
        if percentage == 0:
            await self.async_turn_off()
        else:
            msg_data = {}
            _index = int(percentage / self._percentage_step)
            if _index >= len(self._fan_modes):
                _index = len(self._fan_modes) - 1
            msg_data["windSpeed"] = self._fan_modes[_index]
            _LOGGER.debug("msg_data:%s", msg_data)
            uid = self._attr_unique_id
            await self._uiot_dev.dev_control_real(uid, msg_data)
            self.async_write_ha_state()
