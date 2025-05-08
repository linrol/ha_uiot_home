"""Uiot host."""

import json
import logging

import requests

from .http_api import UIOThttpClient
from .uiot_config import UIOTConfig
from .util import decrypt1, get_timestamp_str

_LOGGER = logging.getLogger(__name__)


class UIOTHost:
    """UIOT Host class."""

    _http_client: UIOThttpClient
    _config: UIOTConfig

    def __init__(self, config: UIOTConfig) -> None:
        """UIOT Host class init."""
        self._http_client = UIOThttpClient()
        self._config = config
        self.body = ""

    async def update_access_token_async_passwd(self, username, password):
        """Update access token by passwd."""
        (
            self._config.access_token,
            expires_in,
        ) = await self._http_client.update_access_token_async_password_mode(
            self._config.app_key, self._config.app_secret, username, password
        )
        return self._config.access_token, expires_in

    async def update_access_token_async(self):
        """Update access token."""
        (
            self._config.access_token,
            expires_in,
        ) = await self._http_client.update_access_token_async(
            self._config.app_key, self._config.app_secret
        )
        return self._config.access_token, expires_in

    def get_response_data(self, res: str) -> str:
        """Get response data."""
        res_json = json.loads(res)
        if res_json["code"] != 0:
            return res_json["desc"]
        return decrypt1(res_json["data"], self._config.app_secret)

    def uiot_bind_host(self, host_sn: str) -> int:
        """Uiot bind host."""
        header = {
            "timestamp": get_timestamp_str(),
            "appkey": self._config.app_key,
            "accessToken": self._config.access_token,
            "method": "uiotsoft.openapi.host.bindthird",
        }
        self._http_client.update_header(header)
        self._http_client.body = {
            "thirdSn": self._config.third_sn,
            "appVer": "3.8.001",
            "sysVer": "1.2.110",
            "thirdName": self._config.third_name,
            "sdkVer": "uiot-open-java-sdk-2.0.6.20210603",
            "appKey": self._config.app_key,
            "sn": host_sn,
            "thirdType": "DEV",
        }
        self._config.host_sn = host_sn
        res = self._http_client.request(
            self._config.request_url, secret=self._config.app_secret
        )
        if res.status_code != 200:
            return -1
        return 0

    async def uiot_bind_host_async(self, host_sn: str) -> int:
        """Uiot bind host async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.host.bindthird",
            }
            self._http_client.update_header(header)
            self._http_client.body = {
                "thirdSn": self._config.third_sn,
                "appVer": "3.8.001",
                "sysVer": "1.2.110",
                "thirdName": self._config.third_name,
                "sdkVer": "uiot-open-java-sdk-2.0.6.20210603",
                "appKey": self._config.app_key,
                "sn": host_sn,
                "thirdType": "DEV",
            }
            _LOGGER.info("Header:%s", header)
            _LOGGER.info("Body:%s", self._http_client.body)
            self._config.host_sn = host_sn
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return False
        except Exception:
            _LOGGER.exception("Unexpected error")
            return False
        else:
            _LOGGER.debug("Res:%s", res)
            if res["status"] != 0:
                return False
            return True

    def uiot_get_host_info(self) -> dict:
        """Uiot get host info."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.host.getInfo",
            }
            self._http_client.update_header(header)
            thirdSn = self._config.third_sn
            sn = self._config.host_sn
            self.body = {"thirdSn": thirdSn, "sn": sn}
            res = self._http_client.request(
                self._config.request_url, secret=self._config.app_secret
            )
            if res.status_code != 200:
                return {}
            return {"data": self.get_response_data(res.text)}
        except KeyError as e:
            _LOGGER.error("Key error:%s", e)
            return None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None

    async def uiot_get_host_info_async(self) -> dict:
        """Uiot get host info async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.host.getInfo",
            }
            self._http_client.update_header(header)
            thirdSn = self._config.third_sn
            sn = self._config.host_sn
            self.body = {"thirdSn": thirdSn, "sn": sn}
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
            if res["status"] != 0:
                return {}

            return {"data": self.get_response_data(res["text"])}
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None

    def uiot_get_host_devices(self) -> dict:
        """Uiot get host devices."""
        header = {
            "timestamp": get_timestamp_str(),
            "appkey": self._config.app_key,
            "accessToken": self._config.access_token,
            "method": "uiotsoft.openapi.device.list",
        }
        self._http_client.update_header(header)
        self._http_client.body = {
            "thirdSn": self._config.third_sn,
            "appKey": self._config.app_key,
            "sn": self._config.host_sn,
        }
        res = self._http_client.request(
            self._config.request_url, secret=self._config.app_secret
        )
        if res.status_code != 200:
            return {}
        return {"data": self.get_response_data(res.text)}

    async def uiot_get_host_devices_async(self) -> dict:
        """Uiot get host devices async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.device.list",
            }
            self._http_client.update_header(header)
            self._http_client.body = {
                "thirdSn": self._config.third_sn,
                "appKey": self._config.app_key,
                "sn": self._config.host_sn,
            }
            _LOGGER.debug("_request_url: %s", self._config.request_url)
            _LOGGER.debug("body: %s", self._http_client.body)
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
            _LOGGER.debug("Res: %s", res)
            if res["status"] != 0:
                return {}
            return self.get_response_data(res["text"])
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return {}
        except Exception:
            _LOGGER.exception("Unexpected error")
            return {}

    async def uiot_get_host_device_async(self, device_id) -> dict:
        """Uiot get host devices async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.device.get",
            }
            self._http_client.update_header(header)
            self._http_client.body = {
                "thirdSn": self._config.third_sn,
                "appKey": self._config.app_key,
                "sn": self._config.host_sn,
                "deviceId": device_id
            }
            _LOGGER.debug("_request_url: %s", self._config.request_url)
            _LOGGER.debug("body: %s", self._http_client.body)
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
            _LOGGER.debug("Res: %s", res)
            if res["status"] != 0:
                return {}
            return self.get_response_data(res["text"])
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return {}
        except Exception:
            _LOGGER.exception("Unexpected error")
            return {}

    def uiot_get_host_smart(self) -> dict:
        """Uiot get host smart."""
        header = {
            "timestamp": get_timestamp_str(),
            "appkey": self._config.app_key,
            "accessToken": self._config.access_token,
            "method": "uiotsoft.openapi.smart.exe.list",
        }
        self._http_client.update_header(header)
        self.body = {
            "thirdSn": self._config.third_sn,
            "appKey": self._config.app_key,
            "sn": self._config.host_sn,
        }
        res = self._http_client.request(
            self._config.request_url, secret=self._config.app_secret
        )
        if res.status_code != 200:
            return {}
        return {"data": self.get_response_data(res.text)}

    async def uiot_get_host_smart_async(self) -> dict:
        """Uiot get host smart async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.smart.exe.list",
            }
            self._http_client.update_header(header)
            self.body = {
                "thirdSn": self._config.third_sn,
                "appKey": self._config.app_key,
                "sn": self._config.host_sn,
            }
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
            if res["status"] != 0:
                return {}
            return {"data": self.get_response_data(res["text"])}
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None

    async def uiot_get_host_smart_detail_async(self, smart_id) -> dict:
        """Uiot get host smart detail async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.smart.manual.get",
            }
            self._http_client.update_header(header)
            self._http_client.body = {
                "thirdSn": self._config.third_sn,
                "appKey": self._config.app_key,
                "sn": self._config.host_sn,
                "smartId": smart_id
            }
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
            if res["status"] != 0:
                return {}
            return {"data": self.get_response_data(res["text"])}
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None

    def get_host_list(self, account, password, openapi_auth_url) -> dict:
        """Get host list."""
        payload = {
            "username": account,
            "password": password,
        }

        response: requests.Response = self._http_client.request_get(
            openapi_auth_url + "/oauth/getUserSnNew", payload
        )

        _LOGGER.debug("status:%d", response.status_code)
        if response.status_code == 200:
            res_obj = json.loads(response.text)
            snList = res_obj["result"]["snList"]
        return snList

    def update_host_config(self, config) -> None:
        """Update host config."""
        self._config = config

    async def uiot_unbind_host_async(self, host_sn: str) -> int:
        """Uiot unbind host async."""
        try:
            header = {
                "timestamp": get_timestamp_str(),
                "appkey": self._config.app_key,
                "accessToken": self._config.access_token,
                "method": "uiotsoft.openapi.host.unbindthird",
            }
            self._http_client.update_header(header)
            self._http_client.body = {
                "thirdSn": self._config.third_sn,
                "appKey": self._config.app_key,
                "sn": host_sn,
            }
            _LOGGER.info("Header:%s", header)
            _LOGGER.info("Body:%s", self._http_client.body)
            self._config.host_sn = host_sn
            res = await self._http_client.request_async(
                self._config.request_url, secret=self._config.app_secret
            )
        except KeyError as e:
            _LOGGER.error("Key error: %s", e)
            return False
        except Exception:
            _LOGGER.exception("Unexpected error")
            return False
        else:
            _LOGGER.debug("Res:%s", res)
            if res["status"] != 0:
                return False
            return True
