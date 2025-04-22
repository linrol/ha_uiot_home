"""Uiot http api."""

import json
import logging

import aiohttp
import requests

from .const import AUTHURL
from .util import compute_md5, encrypt1

_LOGGER = logging.getLogger(__name__)


class UIOThttpClient:
    """Uiot http Client."""

    http_header: dict = {
        "method": "uiotsoft.openapi.host.bindthird",
        "appkey": "",
        "timestamp": "",
        "version": "1.0",
        "isEncrypt": "true",
        "accessToken": "",
        "Content-Type": "application/json; charset=utf-8",
    }

    body: dict = {}

    def __init__(self) -> None:
        """Uiot http Client initialization."""

    def update_access_token(self, app_key, app_secret) -> str:
        """Update access token."""

        openapi_authurl = AUTHURL
        api_opt_auth = "/oauth/token"
        payload_auth = {
            "client_id": app_key,
            "client_secret": app_secret,
            "grant_type": "client_credentials",
        }
        cur_url = openapi_authurl + api_opt_auth
        response = requests.post(cur_url, params=payload_auth, timeout=10)
        if response.status_code != 200:
            return -1
        _LOGGER.debug("response.text:%s", response.text)
        res_json_obj = json.loads(response.text)
        _LOGGER.debug("token: %s", res_json_obj["access_token"])
        return res_json_obj["access_token"]

    async def update_access_token_async_password_mode(
        self, app_key, app_secret, username, password
    ) -> str:
        """Update access token by password."""

        try:
            openapi_authurl = AUTHURL
            api_opt_auth = "/oauth/token"
            payload_auth = {
                "client_id": app_key,
                "client_secret": app_secret,
                "username": username,
                "password": password,
                "grant_type": "password",
                "scope": "read write",
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url=openapi_authurl + api_opt_auth, params=payload_auth
                ) as response,
            ):
                status = response.status
                # _LOGGER.error("status=%d", status)
                if status == 200:
                    text: str = await response.text()
                    res_obj = json.loads(text)
                    return res_obj["access_token"], res_obj["expires_in"]
                return None, None
        except KeyError as e:
            _LOGGER.error("Response: %s, Response: %s", e, res_obj)
            return None, None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None, None

    async def update_access_token_async(self, app_key, app_secret) -> str:
        """Update access token."""
        try:
            openapi_authurl = AUTHURL
            api_opt_auth = "/oauth/token"
            payload_auth = {
                "client_id": app_key,
                "client_secret": app_secret,
                "grant_type": "client_credentials",
            }

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url=openapi_authurl + api_opt_auth, params=payload_auth
                ) as response,
            ):
                status = response.status
                if status == 200:
                    text: str = await response.text()
                    res_obj = json.loads(text)
                    return res_obj["access_token"], res_obj["expires_in"]
                return None, None
        except KeyError as e:
            _LOGGER.error("KeyError: %s, response: %s", e, res_obj)
            return None, None
        except Exception:
            _LOGGER.exception("Unexpected error")
            return None, None

    def update_header(self, header: dict) -> None:
        """Update header."""
        self.http_header.update(header)

    def request(self, url, secret) -> requests.Response:
        """Request."""
        self.http_header["data"] = encrypt1(
            json.dumps(self.body, separators=(",", ":")), secret
        )
        sign = compute_md5(self.http_header, secret)
        self.http_header["sign"] = str(sign)
        _data = self.http_header["data"]
        _headers = self.http_header
        return requests.post(url, headers=_headers, data=_data, timeout=10)

    async def request_async(self, url, secret) -> dict:
        """Request async."""
        self.http_header["data"] = encrypt1(
            json.dumps(self.body, separators=(",", ":")), secret
        )
        sign = compute_md5(self.http_header, secret)
        self.http_header["sign"] = str(sign)
        header = self.http_header
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url=url, headers=header, data=self.http_header["data"]
            ) as response,
        ):
            status = response.status
            _LOGGER.debug("status:%d", status)
            if status == 200:
                text: str = await response.text()
                _LOGGER.debug("text:%s", text)
                res_obj = json.loads(text)
                if res_obj["code"] != 0:
                    code = res_obj["code"]
                    desc = res_obj["desc"]
                    return {"status": code, "text": desc}
                return {"status": res_obj["code"], "text": text}
            return {"status": status, "text": ""}

    def request_get(self, url, payload) -> requests.Response:
        """Request get."""
        return requests.get(url, params=payload, timeout=10)
