"""Switch platform for UIOT integration."""

import json
import logging

from homeassistant.components.switch import SwitchEntity
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
        if device.get("type") == "switch":
            _LOGGER.debug("switch")
            device_data.append(device)

    entities = []
    deviceName = ""
    for switch_data in device_data:
        name = switch_data.get("deviceName", "")
        deviceId = switch_data.get("deviceId", "")
        channelNum = switch_data.get("channelNum", "")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        _LOGGER.debug("channelNum:%d", channelNum)
        if channelNum == 0:
            deviceName = name
        else:
            uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
            switch_data["mainDevieName"] = deviceName
            entities.append(Switch(switch_data, uiot_dev, hass))

    async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        if hass is None:
            return
        try:
            devices_data = msg
            device_data = []
            for device in devices_data:
                if device.get("type") == "switch":
                    _LOGGER.debug("switch")
                    _LOGGER.debug("devices_data %s", devices_data)
                    device_data.append(device)

            new_entities = []

            for switch_data in device_data:
                name = switch_data.get("deviceName", "")
                deviceId = switch_data.get("deviceId", "")
                channelNum = switch_data.get("channel", "")
                _LOGGER.debug("name:%s", name)
                _LOGGER.debug("deviceId:%d", deviceId)
                _LOGGER.debug("channelNum:%d", channelNum)
                if channelNum == 0:
                    deviceName = name
                    mainDeviceId = deviceId
                else:
                    uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
                    switch_data["mainDevieName"] = deviceName
                    switch_data["mainDeviceId"] = str(mainDeviceId)
                    if not is_entity_exist(hass, deviceId):
                        new_entities.append(Switch(switch_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)


class Switch(SwitchEntity):
    """Representation of a UIOT home Switch."""

    def __init__(self, switch_data, uiot_dev, hass: HomeAssistant) -> None:
        """Initialize the switch."""
        self.hass = hass
        self._attr_name = switch_data.get("deviceName", "")
        self._attr_unique_id = str(switch_data.get("deviceId", ""))
        self.mac = switch_data.get("deviceMac", "")
        if self.mac:
            pass
        else:
            self.mac = switch_data.get("mainDeviceId", "")
        self._uiot_dev: UIOTDevice = uiot_dev
        properties_data = switch_data.get("properties", "")
        if properties_data:
            powerSwitch = properties_data.get("powerSwitch", "")
            if powerSwitch == "off":
                self._attr_is_on = False
            else:
                self._attr_is_on = True

        deviceOnlineState = switch_data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True
        _LOGGER.debug("_attr_available=%d", self._attr_available)

        deviceName = switch_data.get("mainDevieName", "")
        if deviceName:
            _LOGGER.debug("deviceName=%s", deviceName)
        else:
            deviceName = self._attr_name
        self._attr_device_info = {
            "identifiers": {(f"{DOMAIN}", f"{self.mac}")},
            "name": f"{deviceName}",
            "manufacturer": f"{COMPANY}",
            "suggested_area": f"{switch_data.get('roomName', "")}",
            "model": f"{switch_data.get('model', "")}",
            "sw_version": f"{switch_data.get('softwareVersion', "")}",
            "hw_version": f"{switch_data.get('hardwareVersion', "")}",
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

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        msg_data = {}
        msg_data["powerSwitch"] = "on"
        self._attr_is_on = True
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
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
