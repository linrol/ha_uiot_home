"""Scene platform for UIOT integration."""

import json
import logging

from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .uiot_api.const import DOMAIN
from .uiot_api.uiot_device import UIOTDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Scene platform from a config entry."""
    _LOGGER.debug("async_setup_entry fan")

    devices_data = hass.data[DOMAIN].get("devices", [])

    device_data = []
    for device in devices_data:
        if device.get("type") == "scene":
            _LOGGER.debug("scene")
            device_data.append(device)

    entities = []
    for c_data in device_data:
        smartName = c_data.get("smartName", "")
        smartId = c_data.get("smartId", 0)
        _LOGGER.debug("smartName:%s", smartName)
        _LOGGER.debug("smartId:%d", smartId)

        uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
        entities.append(UiotScene(c_data, uiot_dev, hass))

    async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        if hass is None:
            return
        try:
            devices_data = msg
            device_data = []
            for device in devices_data:
                if device.get("type") == "scene":
                    _LOGGER.debug("scene")
                    _LOGGER.debug("devices_data %s", devices_data)
                    device_data.append(device)

            new_entities = []

            for s_data in device_data:
                smartName = s_data.get("smartName", "")
                smartId = s_data.get("smartId", 0)
                _LOGGER.debug("smartName:%s", smartName)
                _LOGGER.debug("smartId:%d", smartId)
                uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
                new_entities.append(UiotScene(s_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)


class UiotScene(SceneEntity):
    """Representation of a UIOT home Scene."""

    def __init__(self, c_data, uiot_dev, hass: HomeAssistant) -> None:
        """Initialize the Scene."""
        self.hass = hass
        self._attr_name = c_data.get("smartName", "")
        self._smartId = str(c_data.get("smartId", ""))
        self._attr_unique_id = "smartId" + "_" + self._smartId
        self._uiot_dev: UIOTDevice = uiot_dev
        # room_id = "scene" + "_" + str(c_data.get("roomId", ""))
        # self._attr_device_info = {
        #     "identifiers": {(f"{DOMAIN}", f"{room_id}")},
        #     "name": f"{c_data.get('roomName', "")}",
        #     "suggested_area": f"{c_data.get('roomName', "")}",
        #     "manufacturer": f"{COMPANY}",
        #     "model": f"{"Room"}",
        # }
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

    @property
    def is_active(self) -> bool:
        """Return if this smart scene is currently active."""
        return True

    @property
    def name(self) -> str:
        """Return name of the scene."""
        return self._attr_name

    async def async_activate(self, **kwargs) -> None:
        """Activate scene. Try to get entities into requested state."""
        _LOGGER.debug("_smartId:%s", self._smartId)
        smartId = int(self._smartId)
        await self._uiot_dev.scene_control_real(smartId)
