"""Cover platform for UIOT integration."""

import json
import logging

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .uiot_api.const import COMPANY, DOMAIN
from .uiot_api.uiot_device import UIOTDevice, is_entity_exist

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Cover platform from a config entry."""
    devices_data = hass.data[DOMAIN].get("devices", [])
    device_data = []
    for device in devices_data:
        if device.get("type") == "cover":
            _LOGGER.debug("cover")
            device_data.append(device)
    entities = []
    for dev_data in device_data:
        name = dev_data.get("deviceName")
        deviceId = dev_data.get("deviceId")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
        entities.append(Cover(dev_data, uiot_dev, hass))
    async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        try:
            devices_data = msg
            device_data = []
            for device in devices_data:
                if device.get("type") == "cover":
                    _LOGGER.debug("cover")
                    _LOGGER.debug("devices_data %s", devices_data)
                    device_data.append(device)

            new_entities = []

            for dev_data in device_data:
                name = dev_data.get("deviceName", "")
                deviceId = dev_data.get("deviceId", "")
                _LOGGER.debug("name:%s", name)
                _LOGGER.debug("deviceId:%d", deviceId)
                uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
                if not is_entity_exist(hass, deviceId):
                    new_entities.append(Cover(dev_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    dispatcher_signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, dispatcher_signal, handle_config_update)


class Cover(CoverEntity, RestoreEntity):
    """Cover class for UIOT integration."""

    def __init__(self, dev_data, uiot_dev, hass: HomeAssistant) -> None:
        """Cover class initialization."""
        self._current_position = 0
        self._current_tilt_position = 0
        self._blindAngle_diff = 0
        self.hass = hass
        self._attr_name = dev_data.get("deviceName", "")
        self._attr_unique_id = str(dev_data.get("deviceId", ""))
        self._uiot_dev: UIOTDevice = uiot_dev
        if "curtainPosition" in dev_data["properties"]:
            self._current_position = int(
                dev_data["properties"].get("curtainPosition", "0")
            )
        self._current_position = max(0, min(self._current_position, 100))

        if "blindAngle" in dev_data["properties"]:
            blindAngle = dev_data["properties"].get("blindAngle", "")
            if blindAngle == "shading180":
                self._current_tilt_position = 100
            elif blindAngle == "shading135":
                self._current_tilt_position = 67
            elif blindAngle == "shading90":
                self._current_tilt_position = 45
            elif blindAngle == "shading45":
                self._current_tilt_position = 23
            else:
                self._current_tilt_position = 0
            _LOGGER.debug("tilt_position:%d", self._current_tilt_position)
            self._blindAngle = blindAngle

        self._is_opening = False
        self._is_closing = False
        self._attr_supported_features = CoverEntityFeature(0)
        ability_type = dev_data.get("ability_type")

        if ability_type == 1:
            self._attr_supported_features |= CoverEntityFeature.OPEN
            self._attr_supported_features |= CoverEntityFeature.CLOSE
            self._attr_supported_features |= CoverEntityFeature.STOP
        elif ability_type == 2:
            self._attr_supported_features |= CoverEntityFeature.OPEN
            self._attr_supported_features |= CoverEntityFeature.CLOSE
            self._attr_supported_features |= CoverEntityFeature.STOP
            self._attr_supported_features |= CoverEntityFeature.SET_POSITION
        elif ability_type == 3:
            self._attr_supported_features |= CoverEntityFeature.OPEN
            self._attr_supported_features |= CoverEntityFeature.CLOSE
            self._attr_supported_features |= CoverEntityFeature.STOP
            self._attr_supported_features |= CoverEntityFeature.SET_POSITION
            TILT_POSITION = CoverEntityFeature.SET_TILT_POSITION
            self._attr_supported_features |= TILT_POSITION
        deviceOnlineState = dev_data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True
        _LOGGER.debug("_attr_available=%d", self._attr_available)

        self._attr_device_info = {
            "identifiers": {(f"{DOMAIN}", f"{self._attr_unique_id}")},
            "name": f"{dev_data.get('deviceName', "")}",
            "manufacturer": f"{COMPANY}",
            "model": f"{dev_data.get('model', "")}",
            "suggested_area": f"{dev_data.get('roomName', "")}",
            "sw_version": f"{dev_data.get('softwareVersion', "")}",
            "hw_version": f"{dev_data.get('hardwareVersion', "")}",
        }
        _LOGGER.debug("初始化设备: %s", self._attr_name)

        # 订阅状态主题以监听本地控制的变化
        signal = "mqtt_message_received_state_report"
        async_dispatcher_connect(hass, signal, self._handle_mqtt_message)

    @callback
    def _handle_mqtt_message(self, msg):
        """Handle incoming MQTT messages for state updates."""
        # _LOGGER.debug("mqtt_message的数据:%s",msg.payload)
        if self.hass is None:
            return
        msg_data = json.loads(msg.payload)

        if "online_report" in msg.topic:
            # _LOGGER.info("online_reporte的数据:%s",msg.payload)
            data = msg_data.get("data")
            devices_data = data.get("deviceList")
            for d in devices_data:
                deviceId = d.get("deviceId", "")
                netState = d.get("netState", "")
                if str(deviceId) == self._attr_unique_id:
                    _LOGGER.info(
                        "设备在线状态变化 deviceId: %d,netState:%d",
                        deviceId,
                        netState,
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

        _LOGGER.info("收到设备状态更新: %s", payload_str)

        curtainPosition = payload_str.get("curtainPosition", 0)
        self._current_position = int(curtainPosition)
        _LOGGER.debug("_current_position:%d", self._current_position)
        self._current_position = max(0, min(self._current_position, 100))

        if "blindAngle" in payload_str:
            blindAngle = payload_str.get("blindAngle", "")
            if blindAngle == "shading180":
                self._current_tilt_position = 100
            elif blindAngle == "shading135":
                self._current_tilt_position = 67
            elif blindAngle == "shading90":
                self._current_tilt_position = 45
            elif blindAngle == "shading45":
                self._current_tilt_position = 23
            else:
                self._current_tilt_position = 0
            _LOGGER.info("Tilt_position:%d", self._current_tilt_position)
            self._blindAngle = blindAngle
            self._blindAngle_diff = 0

        if payload_str.get("motorSwitch", ""):
            motorSwitch = payload_str.get("motorSwitch", "")
            _LOGGER.debug("motorSwitch:%s", motorSwitch)
            if motorSwitch == "on":
                self._is_opening = True
                self._is_closing = False
                if "curtainPosition" not in payload_str:
                    self._current_position = 100
            elif motorSwitch == "pause":
                self._is_opening = False
                self._is_closing = False
                if "curtainPosition" not in payload_str:
                    self._current_position = 50
            else:
                self._is_opening = False
                self._is_closing = True

        deviceOnlineState = data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True

        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._attr_name

    @property
    def unique_id(self):
        """Return the unique_id of the device."""
        return self._attr_unique_id

    @property
    def supported_features(self):
        """Return the supported_features of the device."""
        return self._attr_supported_features

    @property
    def current_cover_position(self):
        """Return the current_cover_position of the device."""
        return self._current_position

    @property
    def current_cover_tilt_position(self):
        """Return the current_cover_tilt_position of the device."""
        return self._current_tilt_position

    @property
    def is_opening(self):
        """Cover is opening."""
        return self._is_opening

    @property
    def is_closing(self):
        """Cover is closing."""
        return self._is_closing

    @property
    def is_closed(self):
        """Cover is closed."""
        return self._current_position == 0

    async def async_open_cover(self, **kwargs):
        """Open Cover async."""
        _LOGGER.debug("打开窗帘")
        self._is_opening = True
        self._is_closing = False

        msg_data = {}
        msg_data["motorSwitch"] = "on"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

        # await self._update_position(100)
        self._current_position = 100
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close Cover async."""
        _LOGGER.debug("关闭窗帘")
        self._is_closing = True
        self._is_opening = False

        msg_data = {}
        msg_data["motorSwitch"] = "off"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

        self._current_position = 0
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop Cover async."""
        _LOGGER.debug("暂停窗帘运动")
        self._is_opening = False
        self._is_closing = False

        msg_data = {}
        msg_data["motorSwitch"] = "pause"
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

    async def async_set_cover_position(self, **kwargs):
        """Set Cover position."""
        target_position = kwargs.get("position", 0)
        _LOGGER.debug("target_position:%d", target_position)
        if target_position > self._current_position:
            self._is_opening = True
            self._is_closing = False
        elif target_position < self._current_position:
            self._is_closing = True
            self._is_opening = False

        msg_data = {}
        msg_data["curtainPosition"] = str(target_position)
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

        self._current_position = target_position
        self.async_write_ha_state()

    async def async_set_cover_tilt_position(self, **kwargs):
        """Set the tilt position of the curtain."""
        target_position = kwargs.get("tilt_position", 0)
        _LOGGER.info("Target_position:%d", target_position)

        msg_data = {}
        if target_position > self._current_tilt_position:
            if 0 < target_position <= 23:
                blindAngle = "shading45"
            elif 23 < target_position <= 45:
                blindAngle = "shading90"
            elif 45 < target_position <= 67:
                blindAngle = "shading135"
            else:
                blindAngle = "shading180"
        elif target_position <= self._current_tilt_position:
            if 0 < target_position <= 23:
                blindAngle = "shading0"
            elif 23 < target_position <= 45:
                blindAngle = "shading45"
            elif 45 < target_position <= 67:
                blindAngle = "shading90"
            else:
                blindAngle = "shading135"

        if self._current_position > 10:
            if blindAngle in ("shading0", "shading180"):
                if self._blindAngle_diff and self._current_tilt_position > 0:
                    self._current_tilt_position -= 1
                    self._blindAngle_diff = 0
                else:
                    self._current_tilt_position += 1
                    self._blindAngle_diff = 1
                self.async_write_ha_state()
                return

        self._current_tilt_position = target_position
        msg_data["blindAngle"] = blindAngle
        _LOGGER.info("Msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)

        self.async_write_ha_state()
