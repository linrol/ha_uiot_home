"""Config flow."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .uiot_api.const import APP_KEY, APP_SECRET, AUTHURL, DOMAIN, GATEWAY
from .uiot_api.uiot_config import UIOTConfig
from .uiot_api.uiot_host import UIOTHost

_LOGGER = logging.getLogger(__name__)


CONF_HOME_NAME = "home_name"


class UIOTHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UIOTHomeConfigFlow."""

    VERSION = 1

    def __init__(self) -> None:
        """UIOTHomeConfigFlow class."""
        config = UIOTConfig(
            url=GATEWAY,
            access_token="",
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            third_name="Home Assistant",
            third_sn="202005190099",
            host_sn="",
        )
        self._account = ""
        self._password = ""
        self._hostSn_list = []
        self._sn = ""
        self._access_token = ""
        self._uiot_oauth = UIOTHost(config=config)
        self.config = config

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("async_step_user")
        errors = {}
        if user_input is not None:
            # Here you would validate the input and create an entry.
            # For now, we just return the form filled with user_input.
            try:
                # 验证账号密码并获取设备列表
                hostSn_list = await self.hass.async_add_executor_job(
                    self._oauth_login,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )

                if hostSn_list:
                    # 保存账号密码，进入设备选择步骤
                    self._account = user_input[CONF_USERNAME]
                    self._password = user_input[CONF_PASSWORD]
                    self._hostSn_list = hostSn_list
                    return await self.async_step_select_device()

                errors["base"] = "no_devices"
            except Exception as ex:
                _LOGGER.error("Failed to connect: %s", ex)
                errors["base"] = "cannot_connect"
                raise

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    def _oauth_login(self, account: str, passwd: str) -> list:
        """Oauth login."""
        try:
            snList = self._uiot_oauth.get_host_list(account, passwd, AUTHURL)
        except Exception as ex:
            _LOGGER.error("Error getting device list: %s", ex)
            raise
        else:
            _LOGGER.info("Host_list:%s", snList)
            return snList

    async def async_step_select_device(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle device selection."""
        errors = {}

        if user_input is not None:
            title = user_input[CONF_HOME_NAME]
            _LOGGER.info("Title:%s", title)

            # 获取 remark 为 title 的设备的 sn
            self._sn = next(
                (
                    device["sn"]
                    for device in self._hostSn_list
                    if device.get("remark") == title
                ),
                None,
            )
            _LOGGER.info("Sn:%s", self._sn)

            self.config.third_sn = self._sn

            self.config.host_sn = self._sn

            self._uiot_oauth.update_host_config(self.config)

            (
                self._access_token,
                _,
            ) = await self._uiot_oauth.update_access_token_async_passwd(
                self._account, self._password
            )

            if self._access_token:
                _LOGGER.info("Access_token:%s", self._access_token)
                result = await self._uiot_oauth.uiot_bind_host_async(self._sn)
                if result is True:
                    return self.async_create_entry(
                        title=user_input[CONF_HOME_NAME],
                        data={
                            CONF_USERNAME: self._account,
                            CONF_PASSWORD: self._password,
                            CONF_MAC: self._sn,
                        },
                    )
                errors["base"] = "bind_host_error"
            else:
                errors["base"] = "get_token_error"

        home_names = [device["remark"] for device in self._hostSn_list]
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOME_NAME): vol.In(home_names),
                }
            ),
            errors=errors,
        )
