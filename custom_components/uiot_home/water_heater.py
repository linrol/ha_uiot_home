"""Water heater platform for UIOT integration."""

import json
import logging

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE
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
    _LOGGER.debug("async_setup_entry switch")

    devices_data = hass.data[DOMAIN].get("devices", [])

    device_data = []
    for device in devices_data:
        if device.get("type") == "water_heater":
            _LOGGER.debug("water_heater")
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
        entities.append(WaterHeater(c_data, uiot_dev, hass))

    async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        if hass is None:
            return
        try:
            devices_data = msg
            device_data = []
            for device in devices_data:
                if device.get("type") == "water_heater":
                    _LOGGER.debug("water_heater")
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
                    new_entities.append(WaterHeater(s_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)


class WaterHeater(WaterHeaterEntity):
    """Representation of a UIOT home WaterHeater."""

    def __init__(self, c_data, uiot_dev, hass: HomeAssistant) -> None:
        """Initialize the WaterHeater."""
        self.hass = hass
        self._attr_name = c_data.get("deviceName", "")
        self._attr_unique_id = str(c_data.get("deviceId", ""))
        self.mac = self._attr_unique_id
        self._uiot_dev: UIOTDevice = uiot_dev
        properties_data = c_data.get("properties", "")
        self._current_operation = properties_data.get("powerSwitch", "")
        self._value_switch_type = properties_data.get("value_switch_type", "")
        self._ValveSwitch = properties_data.get(self._value_switch_type, "")
        temperature_high = properties_data.get("temperature_max", 0)
        temperature_low = properties_data.get("temperature_min", 0)
        self._attr_target_temperature_high = temperature_high
        self._attr_target_temperature_low = temperature_low
        self._attr_target_temperature_step = 1
        self._attr_max_temp = temperature_high
        self._attr_min_temp = temperature_low
        self._attr_temperature_unit = "°C"
        self._attr_supported_features = (
            WaterHeaterEntityFeature.ON_OFF
            | WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_operation_list = ["on", "off"]
        self._cur_target_temperature = float(
            properties_data.get("targetTemperature", "20.0")
        )
        self._cur_current_temperature = 0
        if "currentTemperature" in properties_data:
            cTemperature = properties_data.get("currentTemperature", "")
            if cTemperature == "":
                self._cur_current_temperature = 0
            else:
                self._cur_current_temperature = float(cTemperature)

        deviceOnlineState = c_data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True
        _LOGGER.debug("_attr_available=%d", self._attr_available)

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
            if power_switch == "off":
                _LOGGER.debug("power_switch:%s", power_switch)
            else:
                if "currentTemperature" in payload_str:
                    cTemperature = payload_str.get("currentTemperature", "")
                    if cTemperature == "":
                        self._cur_current_temperature = 0
                    else:
                        self._cur_current_temperature = float(cTemperature)
                if "targetTemperature" in payload_str:
                    tTemperature = payload_str.get("targetTemperature", "")
                    self._cur_target_temperature = float(tTemperature)
        else:
            power_switch = "off"
        self._current_operation = power_switch
        if self._value_switch_type in payload_str:
            self._ValveSwitch = payload_str.get(self._value_switch_type, "")
        deviceOnlineState = data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True

        self.async_write_ha_state()

    @property
    def precision(self) -> float:
        """Water Heater precision."""
        return float(1)

    @property
    def target_temperature(self) -> float:
        """Climate target temperature."""
        return self._cur_target_temperature

    @property
    def current_temperature(self) -> float | None:
        """Climate current temperature."""
        if self._cur_current_temperature > 0:
            return self._cur_current_temperature
        return None

    @property
    def current_operation(self) -> str:
        """Return the current mode."""
        return self._current_operation

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on."""
        msg_data = {}
        msg_data["powerSwitch"] = "on"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_turn_on_value_switch(self, **kwargs) -> None:
        """Turn on."""
        msg_data = {}
        if self._value_switch_type == "":
            return
        msg_data[self._value_switch_type] = "on"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_turn_off_value_switch(self, **kwargs) -> None:
        """Turn on."""
        msg_data = {}
        if self._value_switch_type == "":
            return
        msg_data[self._value_switch_type] = "off"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off."""
        msg_data = {}
        msg_data["powerSwitch"] = "off"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Climate set temperature."""
        if self._ValveSwitch != "on":
            await self.async_turn_on_value_switch()
        if ATTR_TEMPERATURE not in kwargs:
            return
        temperature = int(((float(kwargs[ATTR_TEMPERATURE]) * 2) + 0.5) / 2)
        msg_data = {}
        msg_data["targetTemperature"] = str(temperature)
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set the operation mode of the water heater."""
        _LOGGER.debug("operation_mode:%s", operation_mode)
        if operation_mode == "on":
            await self.async_turn_on()
            if self._ValveSwitch != "on":
                await self.async_turn_on_value_switch()
        else:
            if self._ValveSwitch != "off":
                await self.async_turn_off_value_switch()
            await self.async_turn_off()
        self._current_operation = operation_mode
