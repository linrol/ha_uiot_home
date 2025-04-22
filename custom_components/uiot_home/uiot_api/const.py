"""Uiot const."""

from homeassistant.const import Platform

DOMAIN = "uiot_home"
COMPANY = "UIOT"
AUTHURL = "https://dev-oauth.unisiot.com:8165/oauth"
API_OPT_AUTH = "/oauth/token"
GATEWAY = "https://dev-openapi.unisiot.com/gateway"
APP_KEY = "3t4hjc4yvfvh34rhxjc1qbiu6csh635g"
APP_SECRET = "fMJ08baFhxLB21RdA0xtqCALBVRhUfEB"
MQTT_BROKER = "dev-bmqt.unisiot.com"
MQTT_PORT = 51322
PLATFORMS = [Platform.COVER, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]
