"""Uiot device api."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .http_api import UIOThttpClient
from .uiot_config import UIOTConfig
from .util import get_timestamp_str

_LOGGER = logging.getLogger(__name__)


class UIOTDevice:
    """Uiot device class."""

    _config: UIOTConfig
    _http_client: UIOThttpClient

    def __init__(self, config: UIOTConfig) -> None:
        """Uiot device initialization."""
        self._config = config
        self._http_client = UIOThttpClient()

    async def dev_control_real(self, deviceId, property: dict) -> int:
        """Uiot device control."""
        self._http_client.body = {
            "thirdSn": self._config.third_sn,
            "appKey": self._config.app_key,
            "sn": self._config.host_sn,
            "deviceId": deviceId,
            "properties": property,
        }
        header = {
            "timestamp": get_timestamp_str(),
            "appkey": self._config.app_key,
            "accessToken": self._config.access_token,
            "method": "uiotsoft.openapi.device.control",
        }
        _LOGGER.debug("body:%s", self._http_client.body)
        self._http_client.update_header(header)
        res = await self._http_client.request_async(
            self._config.request_url, secret=self._config.app_secret
        )
        return res["status"]

    async def dev_control_async(
        self, deviceId, dev_properties, properties: dict
    ) -> int:
        """Uiot device control."""
        state: int = -1
        for k, v in properties.items():
            if k in dev_properties:
                property_val = {k: v}
                state = await self.dev_control_real(deviceId, property_val)
                if state != 0:
                    return state
        return state


def remove_device(hass: HomeAssistant, config_entry_id: str):
    """Uiot device remove."""
    # 移除实体
    registry_entry = er.async_get(hass)
    for entity_id, entity_entry in list(registry_entry.entities.items()):
        # 检查实体是否属于当前配置项
        if (
            entity_entry.platform == DOMAIN
            and entity_entry.config_entry_id == config_entry_id
        ):
            _LOGGER.debug(
                "遍历实体注册表:e_id:%s,u_id:%s", entity_id, entity_entry.unique_id
            )
            registry_entry.async_remove(entity_id)

    # 移除设备
    device_registry = dr.async_get(hass)
    # 遍历所有设备
    reg = registry_entry.entities
    for device_id, device in list(device_registry.devices.items()):
        # 检查设备是否属于当前配置项
        if config_entry_id in device.config_entries:
            # 检查设备是否关联了实体
            entities = reg.get_entries_for_device_id(device_id)
            if entities:
                _LOGGER.debug("设备已关联实体，不移除设备")
            else:
                _LOGGER.debug("移除设备名称：%s ", device.name)
                device_registry.async_remove_device(device_id)


def is_entity_exist(hass: HomeAssistant, deviceID) -> bool:
    """Uiot device remove."""
    registry_entry = er.async_get(hass)
    for entity_id, entity_entry in list(registry_entry.entities.items()):
        # 检查实体是否属于当前配置项
        if entity_entry.platform == DOMAIN:
            if (
                str(deviceID) == entity_entry.unique_id
                or str(deviceID) in entity_entry.unique_id
            ):
                _LOGGER.debug("找到实体,entity_id=%s", entity_id)
                return True
    return False
