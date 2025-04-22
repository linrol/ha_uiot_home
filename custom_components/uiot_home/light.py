"""Light platform for UIOT integration."""

import asyncio
import json
import logging

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .uiot_api.const import COMPANY, DOMAIN
from .uiot_api.uiot_device import UIOTDevice

_LOGGER = logging.getLogger(__name__)


def update_light_status(self, payload_str):
    """update_light_status."""
    # 配置能力
    self._attr_supported_color_modes = set()
    if "colorAndColorTemperatureAbility" in payload_str:
        colorAndColorTemperatureAbility = payload_str.get(
            "colorAndColorTemperatureAbility", ""
        )
        _LOGGER.debug("Ability=%s", colorAndColorTemperatureAbility)
        if colorAndColorTemperatureAbility == "all":
            _LOGGER.debug("支持亮度、色温、颜色")
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
        elif colorAndColorTemperatureAbility == "colorAdjust":
            _LOGGER.debug("支持亮度、颜色")
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
        elif colorAndColorTemperatureAbility == "colorTemperature":
            _LOGGER.debug("支持亮度、色温")
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
        else:
            _LOGGER.debug("支持亮度")
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS

    else:
        if "colorTemperature" in payload_str:
            Enable = payload_str.get("colorTemperatureEnable", "")
            if Enable in ("enable", ""):
                _LOGGER.debug("支持色温")
                self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
                self._attr_max_color_temp_kelvin = 6500
                self._attr_min_color_temp_kelvin = 2700
                self._attr_color_mode = ColorMode.COLOR_TEMP
            else:
                _LOGGER.debug("不支持色温")

        if "colorAdjust" in payload_str:
            _LOGGER.debug("支持颜色")
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB

        if "brightness" in payload_str:
            _LOGGER.debug("支持亮度")
            if self._attr_supported_color_modes:
                color_modes = self._attr_supported_color_modes
                _LOGGER.debug("color_modes:%s", color_modes)
            else:
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
                self._attr_color_mode = ColorMode.BRIGHTNESS

    # _LOGGER.debug("color_modes:%s", self._attr_supported_color_modes)

    if payload_str.get("colorTemperature") and (
        ColorMode.COLOR_TEMP in self._attr_supported_color_modes
    ):
        if self._attr_color_temp_kelvin is not None:
            kelvin_value = self._attr_color_temp_kelvin
            if int(payload_str.get("colorTemperature", "")) == (
                kelvin_value - kelvin_value % 50
            ):
                _LOGGER.debug("colorTemperature 不需要更新 !")
            else:
                self._attr_color_temp_kelvin = int(
                    payload_str.get("colorTemperature", "")
                )
                self._attr_color_mode = ColorMode.COLOR_TEMP
                _LOGGER.debug("kelvin:%s", self._attr_color_temp_kelvin)

    if payload_str.get("brightness"):
        brightness = int(payload_str.get("brightness", "")) * 255 / 100
        if self._attr_brightness == brightness:
            _LOGGER.debug("brightness 不需要更新 !")
        else:
            self._attr_brightness = brightness

    if payload_str.get("colorAdjust") and (
        ColorMode.RGB in self._attr_supported_color_modes
    ):
        # 将十六进制字符串转换为整数
        rgb_int = int(payload_str.get("colorAdjust", ""), 16)
        # 分别提取RGB值
        r = (rgb_int >> 16) & 0xFF
        g = (rgb_int >> 8) & 0xFF
        b = rgb_int & 0xFF
        if self._attr_rgb_color == (r, g, b):
            _LOGGER.debug("colorAdjust 不需要更新 !")
        else:
            self._attr_rgb_color = (r, g, b)
            self._attr_color_mode = ColorMode.RGB

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

    deviceOnlineState = payload_str.get("deviceOnlineState", "")
    if deviceOnlineState == 0:
        self._attr_available = False
    else:
        self._attr_available = True


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Switch platform from a config entry."""
    _LOGGER.debug("async_setup_entry light")

    devices_data = hass.data[DOMAIN].get("devices", [])
    device_data = []
    for device in devices_data:
        if device.get("type") == "light":
            _LOGGER.debug("light")
            device_data.append(device)

    entities = []
    for light_data in device_data:
        name = light_data.get("deviceName")
        deviceId = light_data.get("deviceId")
        _LOGGER.debug("name:%s", name)
        _LOGGER.debug("deviceId:%d", deviceId)
        uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
        entities.append(Light(light_data, uiot_dev, hass))
    async_add_entities(entities)

    @callback
    def handle_config_update(msg):
        try:
            devices_data = msg
            _LOGGER.debug("devices_data %s", devices_data)

            device_data = []
            for device in devices_data:
                if device.get("type") == "light":
                    _LOGGER.debug("light")
                    device_data.append(device)

            new_entities = []

            for light_data in device_data:
                name = light_data.get("deviceName")
                deviceId = light_data.get("deviceId")
                _LOGGER.debug("name:%s", name)
                _LOGGER.debug("deviceId:%d", deviceId)
                uiot_dev: UIOTDevice = hass.data[DOMAIN].get("uiot_dev")
                new_entities.append(Light(light_data, uiot_dev, hass))

            if new_entities:
                async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Error processing config update: %s", e)
            raise

    signal = "mqtt_message_network_report"
    async_dispatcher_connect(hass, signal, handle_config_update)


class Light(LightEntity):
    """Light entity for UIOT integration."""

    def __init__(self, light_data, uiot_dev, hass: HomeAssistant) -> None:
        """Initialize the Light."""
        self._turn_on_task = None
        self._turn_on_lock = asyncio.Lock()
        self._attr_name = light_data.get("deviceName", "")
        self._attr_unique_id = str(light_data.get("deviceId", ""))
        self.mac = light_data.get("deviceMac", "")
        if self.mac:
            pass
        else:
            self.mac = self._attr_unique_id
        deviceOnlineState = light_data.get("deviceOnlineState", "")
        if deviceOnlineState == 0:
            self._attr_available = False
        else:
            self._attr_available = True
        _LOGGER.debug("_attr_available=%d", self._attr_available)
        self._uiot_dev: UIOTDevice = uiot_dev
        properties_data = light_data.get("properties", "")
        if properties_data:
            powerSwitch = properties_data.get("powerSwitch", "")
            if powerSwitch == "off":
                self._attr_is_on = False
            else:
                self._attr_is_on = True

        self._attr_device_info = {
            "identifiers": {(f"{DOMAIN}", f"{self.mac}")},
            "name": f"{light_data.get('deviceName', "")}",
            "manufacturer": f"{COMPANY}",
            "model": f"{light_data.get('model', "")}",
            "suggested_area": f"{light_data.get('roomName', "")}",
            "sw_version": f"{light_data.get('softwareVersion', "")}",
            "hw_version": f"{light_data.get('hardwareVersion', "")}",
        }
        _LOGGER.debug("初始化设备: %s", self._attr_name)

        self._attr_supported_color_modes = set()
        properties_data = light_data.get("properties", "")
        if properties_data == "":
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_brightness = 1
            self._attr_color_mode = ColorMode.BRIGHTNESS

        if "colorTemperature" in properties_data:
            Enable = properties_data.get("colorTemperatureEnable", "")
            if Enable in ("enable", ""):
                _LOGGER.debug("支持色温")
                self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
                self._attr_max_color_temp_kelvin = 6500
                self._attr_min_color_temp_kelvin = 2700
                self._attr_color_temp_kelvin = properties_data.get(
                    "colorTemperature", ""
                )
                self._attr_color_mode = ColorMode.COLOR_TEMP
            else:
                _LOGGER.debug("不支持色温")

        if "colorAdjust" in properties_data:
            _LOGGER.debug("支持颜色")
            self._attr_supported_color_modes.add(ColorMode.RGB)
            rgb_int = int(properties_data.get("colorAdjust", ""), 16)
            # 分别提取RGB值
            r = (rgb_int >> 16) & 0xFF
            g = (rgb_int >> 8) & 0xFF
            b = rgb_int & 0xFF
            self._attr_rgb_color = (r, g, b)
            self._attr_color_mode = ColorMode.RGB

        if "brightness" in properties_data:
            _LOGGER.debug("支持亮度")
            if (
                ColorMode.COLOR_TEMP in self._attr_supported_color_modes
                or ColorMode.RGB in self._attr_supported_color_modes
            ):
                _LOGGER.debug("已默认支持亮度，不用重复设置亮度模式")
            else:
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
                self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_brightness = (
                int(properties_data.get("brightness", 1)) * 255 / 100
            )

        _LOGGER.debug("color_modes:%s", self._attr_supported_color_modes)
        # 订阅状态主题以监听本地控制的变化
        signal = "mqtt_message_received_state_report"
        async_dispatcher_connect(hass, signal, self._handle_mqtt_message)

    @callback
    def _handle_mqtt_message(self, msg):
        """Handle incoming MQTT messages for state updates."""
        # _LOGGER.debug(f"mqtt_message的数据:{ msg.payload}")
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

        update_light_status(self, payload_str)

        self.async_write_ha_state()

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Flag supported color modes."""
        return self._attr_supported_color_modes

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return the color mode of the light."""
        return self._attr_color_mode

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._attr_color_temp_kelvin

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return self._attr_brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color value."""
        return self._attr_rgb_color

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._attr_is_on

    @property
    def available(self) -> bool:
        """Return true if switch is available."""
        return self._attr_available

    @property
    def name(self) -> str:
        """Return name."""
        return self._attr_name

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on."""
        # 获取锁
        async with self._turn_on_lock:
            # 如果有正在等待的任务，取消它
            if self._turn_on_task is not None:
                self._turn_on_task.cancel()

            # 创建一个新的任务来处理实际的逻辑，并在5秒后执行
            task = asyncio.create_task(self._handle_turn_on(**kwargs))
            self._turn_on_task = task

    async def _handle_turn_on(self, **kwargs) -> None:
        # 确保在等待期间没有其他调用
        async with self._turn_on_lock:
            # 如果任务还是当前的，则执行逻辑
            task_status = self._turn_on_task.done()
            if self._turn_on_task is not None and not task_status:
                _LOGGER.debug("Actually turning on with kwargs:{kwargs}")
                # # 在这里执行实际的逻辑
                # self._turn_on_task = None  # 重置任务
            else:
                _LOGGER.debug("Turn on was called again, skipping this one")
                return

        msg_data = {}
        if kwargs.get("brightness"):
            self._attr_brightness = int(kwargs.get("brightness"))
            msg_data["brightness"] = str(
                round(int(kwargs.get("brightness")) * 100 / 255)
            )

        if kwargs.get("color_temp_kelvin"):
            self._attr_color_temp_kelvin = kwargs.get("color_temp_kelvin")
            self._attr_color_mode = ColorMode.COLOR_TEMP
            min_value = self._attr_min_color_temp_kelvin
            max_value = self._attr_max_color_temp_kelvin
            color_temp = 100 - int(
                (kwargs.get("color_temp_kelvin") - min_value)
                * 100
                / (max_value - min_value)
            )
            msg_data["colorTemperature"] = str(color_temp)

        if kwargs.get("rgb_color"):
            self._attr_rgb_color = kwargs.get("rgb_color")
            self._attr_color_mode = ColorMode.RGB
            # 将RGB值转换为十六进制字符串
            r = self._attr_rgb_color[0]
            g = self._attr_rgb_color[1]
            b = self._attr_rgb_color[2]
            color_adjust = (r << 16) + (g << 8) + b
            msg_data["colorAdjust"] = str(hex(color_adjust)[2:].zfill(6))

        if not kwargs:
            msg_data["powerSwitch"] = "on"
            self._attr_is_on = True
            # self._attr_color_mode = ColorMode.ONOFF
        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        # 在这里执行实际的逻辑
        self._turn_on_task = None  # 重置任务
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off."""
        msg_data = {}
        if not kwargs:
            msg_data["powerSwitch"] = "off"
            self._attr_is_on = False

        _LOGGER.debug("msg_data:%s", msg_data)
        await self._uiot_dev.dev_control_real(self._attr_unique_id, msg_data)
        self.async_write_ha_state()
