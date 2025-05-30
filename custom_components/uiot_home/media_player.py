"""Media player platform for UIOT integration."""

import json
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .uiot_api.const import COMPANY, DOMAIN
from .uiot_api.uiot_host import UIOTHost

_LOGGER = logging.getLogger(__name__)


def handle_result(task, arg1, hass: HomeAssistant):
    """Handle result."""
    mqtt_client = hass.data[DOMAIN].get("mqtt_client")
    try:
        result = task.result()
        _LOGGER.debug("arg1=%s,最终返回数据: %s", arg1, result)
        response = result.get("response", {})
        speech = response.get("speech", {})
        plain = speech.get("plain", {})
        speech2 = plain.get("speech", "")
        _LOGGER.debug("speech2: %s", speech2)
        mqtt_client.voice_control_result(arg1, speech2)
    except Exception as e:
        _LOGGER.error("服务调用失败: %s", repr(e))
        raise


async def async_ha_voice(hass: HomeAssistant, text) -> str:
    """Voice control."""
    service_data = {}
    service_data["text"] = text
    service_data["language"] = "zh-CN"  # 需匹配系统语言设置
    try:
        # 异步调用服务
        result = await hass.services.async_call(
            "conversation",
            "process",
            service_data,
            blocking=True,
            return_response=True,
        )
    except Exception as e:
        _LOGGER.error("Conversation 调用失败: %s", repr(e))
        raise
    finally:
        pass
    return result


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
):
    """Set up the Media player platform from a config entry."""
    devices_data = hass.data[DOMAIN].get("devices", [])

    device_data = []
    for device in devices_data:
        if device.get("type") == "media_player":
            _LOGGER.debug("media_player")
            device_data.append(device)

    entities = []
    for c_data in device_data:
        name = c_data.get("deviceName", "")
        deviceId = c_data.get("deviceId", "")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)

        uiot_host: UIOTHost = hass.data[DOMAIN].get("uiot_host")
        res = await uiot_host.uiot_query_voice_switch_async()
        c_data["voice_switch"] = res
        entities.append(MediaPlayer(c_data, uiot_host, hass))

    async_add_entities(entities)


class MediaPlayer(MediaPlayerEntity):
    """Media Player."""

    def __init__(self, data, uiot_host, hass: HomeAssistant) -> None:
        """Initialize the media player."""
        self.hass = hass
        self._attr_name = data.get("deviceName", "")
        self._attr_unique_id = str(data.get("deviceId", ""))
        self.mac = self._attr_unique_id
        self._uiot_host: UIOTHost = uiot_host
        voice_switch = data.get("voice_switch", 0)
        _LOGGER.debug("voice_switch=%d", voice_switch)
        if voice_switch:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF

        self._attr_device_info = {
            "identifiers": {(f"{DOMAIN}", f"{self.mac}")},
            "name": f"{self._attr_name}",
            "manufacturer": f"{COMPANY}",
            "suggested_area": f"{data.get('roomName', "")}",
            "model": f"{data.get('model', "")}",
            "sw_version": f"{data.get('softwareVersion', "")}",
            "hw_version": f"{data.get('hardwareVersion', "")}",
        }
        _LOGGER.debug("初始化设备: %s", self._attr_name)
        _LOGGER.debug("deviceId=%s", self._attr_unique_id)
        _LOGGER.debug("mac=%s", self.mac)

        # 订阅状态主题以监听本地控制的变化
        signal = "mqtt_message_received_state_report"
        async_dispatcher_connect(hass, signal, self._handle_mqtt_message)

        signal = "mqtt_message_voice_control"
        async_dispatcher_connect(hass, signal, self._handle_msg_voice_control)

    @callback
    def _handle_msg_voice_control(self, msg):
        """Handle incoming MQTT messages for voice control."""
        text = msg["data"]
        sId = msg["sessionId"]
        _LOGGER.debug("text:%s", text)
        _LOGGER.debug("sessionId:%s", sId)
        task = self.hass.loop.create_task(async_ha_voice(self.hass, text))
        task.add_done_callback(lambda t: handle_result(t, sId, self.hass))

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
        deviceOnlineState = data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True

        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name."""
        return self._attr_name

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def supported_features(self):
        """Return supported features."""
        TURN_ON = MediaPlayerEntityFeature.TURN_ON
        TURN_OFF = MediaPlayerEntityFeature.TURN_OFF
        return TURN_ON | TURN_OFF

    async def async_turn_on(self):
        """Turn on."""
        self._state = STATE_ON
        res = await self._uiot_host.uiot_config_voice_switch_async(1)
        if res:
            self._state = STATE_ON
        _LOGGER.debug("Turning on")
        self.schedule_update_ha_state()

    async def async_turn_off(self):
        """Turn off."""
        res = await self._uiot_host.uiot_config_voice_switch_async(0)
        if res:
            self._state = STATE_OFF
        _LOGGER.debug("Turning off")
        self.schedule_update_ha_state()
