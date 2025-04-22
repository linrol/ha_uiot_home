"""The Uiot Home integration."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .uiot_api.const import (
    APP_KEY,
    APP_SECRET,
    DOMAIN,
    GATEWAY,
    MQTT_BROKER,
    MQTT_PORT,
    PLATFORMS,
)
from .uiot_api.uiot_config import UIOTConfig
from .uiot_api.uiot_device import UIOTDevice, remove_device
from .uiot_api.uiot_host import UIOTHost
from .uiot_api.uiot_mqtt import UIOTMqttClient
from .uiot_api.util import phase_dev_list

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 60  # 最大重试次数
RETRY_DELAY = 5  # 每次重试之间的延迟时间（秒）


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform for current integration.

    Returns
    -------
    True if entry is configured.

    """
    _LOGGER.debug("Set up uiot home from a config entry")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    hass.data[DOMAIN]["entry"] = entry

    host_sn = entry.data.get(CONF_MAC)
    user_name = entry.data.get(CONF_USERNAME)
    passwd = entry.data.get(CONF_PASSWORD)
    _LOGGER.debug("host_sn=%s", host_sn)

    config = UIOTConfig(
        url=GATEWAY,
        access_token="",
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        third_name="test",
        third_sn="202005190099",
        host_sn=host_sn,
    )
    hass.data[DOMAIN]["config"] = config

    uiot_host = UIOTHost(config=config)

    (
        access_token,
        expires_in,
    ) = await uiot_host.update_access_token_async_passwd(user_name, passwd)
    _LOGGER.debug("access_token=%s,expires_in=%s}", access_token, expires_in)
    if expires_in:
        hass.data[DOMAIN]["expires_in"] = expires_in
    else:
        hass.data[DOMAIN]["expires_in"] = 3600

    # 定义要定时执行的任务
    async def scheduled_task(now):
        _LOGGER.debug("Executing scheduled task")
        # 定时刷新token
        (
            access_token,
            expires_in,
        ) = await uiot_host.update_access_token_async_passwd(user_name, passwd)
        _LOGGER.debug("token=%s,expires_in=%d}", access_token, expires_in)
        if expires_in:
            hass.data[DOMAIN]["expires_in"] = expires_in
        else:
            hass.data[DOMAIN]["expires_in"] = 3600

        _LOGGER.info("I expires_in:%d", hass.data[DOMAIN]["expires_in"])
        if hass.data[DOMAIN]["remove_timer"] is not None:
            hass.data[DOMAIN]["remove_timer"]()  # 取消当前定时器
            _LOGGER.info("取消当前定时器")

        times = hass.data[DOMAIN]["expires_in"]
        hass.data[DOMAIN]["remove_timer"] = async_track_time_interval(
            hass, scheduled_task, timedelta(seconds=times)
        )

    # 设置定时任务
    times = hass.data[DOMAIN]["expires_in"]
    hass.data[DOMAIN]["remove_timer"] = async_track_time_interval(
        hass, scheduled_task, timedelta(seconds=times)
    )

    retries = 0
    while retries < MAX_RETRIES:
        res = await uiot_host.uiot_get_host_devices_async()
        _LOGGER.info("Res:%s", res)
        if res:
            remove_device(hass)
            device_list = phase_dev_list(res)
            _LOGGER.debug("dev list:%s", device_list)
            hass.data[DOMAIN]["devices"] = device_list
            break
        retries += 1
        _LOGGER.error("Error! retries=%d", retries)
        if retries < MAX_RETRIES:
            _LOGGER.info("Retrying in %d seconds", RETRY_DELAY)
            await asyncio.sleep(RETRY_DELAY)  # 等待一段时间后重试

    mqtt_client = UIOTMqttClient(hass, MQTT_BROKER, MQTT_PORT, config=config)
    hass.data[DOMAIN]["mqtt_client"] = mqtt_client

    uiot_dev = UIOTDevice(config=config)
    hass.data[DOMAIN]["uiot_dev"] = uiot_dev

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 确保在卸载集成时清除定时器
    _LOGGER.debug("unload uiot home")
    if hass.data[DOMAIN]["remove_timer"] is not None:
        entry.async_on_unload(hass.data[DOMAIN]["remove_timer"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unload a config entry")
    remove_device(hass)
    if DOMAIN in hass.data and "devices" in hass.data[DOMAIN]:
        del hass.data[DOMAIN]["devices"]

    if DOMAIN in hass.data and "mqtt_client" in hass.data[DOMAIN]:
        client: UIOTMqttClient = hass.data[DOMAIN]["mqtt_client"]
        client.destrory_client()
        # 清理引用
        del hass.data[DOMAIN]["mqtt_client"]
        _LOGGER.debug("MQTT client destroyed successfully")
    else:
        _LOGGER.debug("MQTT client not found in hass.data")

    res = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if res:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.data[DOMAIN].pop("entry")
    return res
