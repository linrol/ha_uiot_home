"""Uiot mqtt api."""

# 标准库模块
import json
import logging

# 第三方库模块
import paho.mqtt.client as mqtt

# 本地模块
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN
from .uiot_config import UIOTConfig
from .util import compute_md5_str, decrypt1, get_timestamp_str, phase_dev_list

_LOGGER = logging.getLogger(__name__)


class UIOTMqttClient:
    """Uiot Mqtt Client Class."""

    _SYSTEMID: str = "HA_UIOT"
    _CLIENT_ID: str
    _USERNAME: str
    _PASSWD: str
    _client: mqtt.Client
    _config: UIOTConfig

    def __init__(self, hass: HomeAssistant, host, port, config) -> None:
        """Uiot Mqtt Client Class initialization."""
        _LOGGER.debug("Initialize the MQTT client")
        self.hass = hass
        timestamp: str = get_timestamp_str()
        self._config = config
        self._CLIENT_ID = "uiotop_sdk@" + self._SYSTEMID + "_" + timestamp
        _LOGGER.debug("_CLIENT_ID=%s", self._CLIENT_ID)
        # 动态适配不同版本的 paho-mqtt
        try:
            # 尝试使用 callback_api_version 参数（paho-mqtt 2.0+）
            self._client = mqtt.Client(
                client_id=self._CLIENT_ID,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            )
        except AttributeError:
            # 兼容旧版本（paho-mqtt < 2.0）
            self._client = mqtt.Client(self._CLIENT_ID)
        self._USERNAME = (
            self._config.app_key
            + "|"
            + self._SYSTEMID
            + "|thirdCloud|"
            + timestamp
            + "|"
        )
        self._mqtt_topic = ""
        passwd_data = self._USERNAME + self._config.app_secret
        self._PASSWD = compute_md5_str(passwd_data)
        self._client.username_pw_set(self._USERNAME, self._PASSWD)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=120)
        # 将 tls_set 调用移到后台线程
        self.hass.async_add_executor_job(self._setup_tls)

        try:
            _LOGGER.debug("Connect to MQTT broker %s:%d", host, port)
            rc = self._client.connect(host, port, 60)
            _LOGGER.debug("MQTT连接返回码:%d", rc)
            if rc != 0:
                _LOGGER.debug("MQTT连接失败，返回码：%d", rc)
        except Exception as e:
            _LOGGER.debug("MQTT连接过程中发生异常：%s", e)
            raise
        _LOGGER.debug("MQTT连接成功")
        self._client.loop_start()

    def _setup_tls(self):
        try:
            self._client.tls_set()  # 原来的阻塞调用
        except Exception as e:
            _LOGGER.error("Error setting up TLS: %s", e)
            raise

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        _LOGGER.debug("Connected to MQTT broker with result code: %s", rc)
        app_key = self._config.app_key
        host_sn = self._config.host_sn
        self._mqtt_topic = "uiotsdk" + "/" + app_key + "/+/" + host_sn + "/#"
        self._client.subscribe(self._mqtt_topic)

    @callback
    def _on_message(self, client, userdata, msg):
        # _LOGGER.debug("Received message on topic:%s", msg.topic)
        # 使用 call_soon_threadsafe 确保任务被安排到事件循环中执行
        self.hass.loop.call_soon_threadsafe(
            self.hass.async_create_task, self._handle_message(msg)
        )

    async def _handle_message(self, msg):
        """Handle the incoming message asynchronously within the event loop."""

        payload = json.loads(msg.payload.decode())
        data = payload["payload"]["data"]
        msg_data = decrypt1(data, self._config.app_secret)
        # _LOGGER.debug("解密后的数据：%s", msg_data)

        if (
            "state_report" in msg.topic
            or "online_report" in msg.topic
            or "env_report" in msg.topic
        ):
            msg.payload = msg_data
            signal = "mqtt_message_received_state_report"
            async_dispatcher_send(self.hass, signal, msg)
        elif "outwork_report" in msg.topic:
            # 遍历 移除不存在的设备
            msg_data = json.loads(msg_data)
            data = msg_data.get("data")
            devices_data = data.get("deviceList")
            # 移除实体
            registry_entry = er.async_get(self.hass)
            items = registry_entry.entities.items()
            for entity_id, entity_entry in list(items):
                # 检查实体是否属于当前配置项
                if entity_entry.platform == DOMAIN:
                    _LOGGER.debug(
                        "遍历实体:e:%s,u:%s", entity_id, entity_entry.unique_id
                    )
                    _LOGGER.debug("devices_data:%s", devices_data)
                    # 检查实体是否存在于设备列表中
                    for d in devices_data:
                        deviceId = d.get("deviceId", "")
                        if (
                            str(deviceId) == entity_entry.unique_id
                            or str(deviceId) in entity_entry.unique_id
                        ):
                            _LOGGER.debug(
                                "移除实体：%s   实体名称：%s",
                                entity_id,
                                entity_entry.name,
                            )
                            registry_entry.async_remove(entity_id)

            # 移除设备
            device_registry = dr.async_get(self.hass)
            # 遍历所有设备
            reg = registry_entry.entities
            for device_id, device in list(device_registry.devices.items()):
                # 检查设备是否属于当前配置项
                entry_id = self.hass.data[DOMAIN]["entry"].entry_id
                if entry_id in device.config_entries:
                    # 检查设备是否关联了实体
                    entities = reg.get_entries_for_device_id(device_id)
                    if entities:
                        _LOGGER.debug("设备已关联实体，不移除设备")
                    else:
                        _LOGGER.debug("移除设备名称：%s ", device.name)
                        device_registry.async_remove_device(device_id)
        elif "network_report" in msg.topic:
            _LOGGER.debug("新设备入网")
            msg_data = json.loads(msg_data)
            data = msg_data.get("data")
            _LOGGER.debug("data:%s", data)
            json_string = json.dumps(data)
            deviceList = phase_dev_list(json_string)
            _LOGGER.debug("deviceList:%s", deviceList)
            signal = "mqtt_message_network_report"
            async_dispatcher_send(self.hass, signal, deviceList)

    def publish(self, topic, payload):
        """Publish a message to a topic."""
        self._client.publish(topic, payload)

    def subscribe(self, topic):
        """Subscribe to a topic."""
        self._client.subscribe(topic)

    def destrory_client(self):
        """destrory_client."""
        _LOGGER.debug("destrory_client")
        try:
            self._client.unsubscribe(self._mqtt_topic)
            # 安全地断开连接
            if self._client.is_connected():
                self._client.disconnect()
            self._client.loop_stop()
        except Exception as e:
            _LOGGER.error("Error while destroying MQTT client: %s", e)
            raise
