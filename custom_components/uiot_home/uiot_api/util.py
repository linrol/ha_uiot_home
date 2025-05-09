"""Uiot util api."""

import base64
import binascii
from datetime import datetime
import hashlib
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def parse_byte2hex_str(buf: bytes) -> str:
    """parse_byte2hex_str."""
    # 使用列表推导式优化性能
    # format(byte, '02x') 直接生成补零的小写十六进制
    return "".join(f"{byte:02x}" for byte in buf)


def compute_md5(params: dict, secret: str) -> str:
    """compute_md5."""
    temp_sorted = {key: params[key] for key in sorted(params)}
    # print(temp_sorted)
    md5_raw_str: str = ""
    for key, val in temp_sorted.items():
        if key == "sign" or val == "" or key == "Content-Type":
            continue
        if md5_raw_str != "":
            md5_raw_str += "&"
        md5_raw_str = md5_raw_str + key + "=" + val
    md5_raw_str += secret
    md5_hash = hashlib.md5()
    md5_hash.update(md5_raw_str.encode("utf-8"))
    return md5_hash.hexdigest()


def compute_md5_str(params: str) -> str:
    """compute_md5_str."""
    md5_hash = hashlib.md5()
    md5_hash.update(params.encode("utf-8"))
    return md5_hash.hexdigest()


def encrypt1(plaintext: str, key: str) -> str:
    """encrypt1."""
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"\0")

    # 创建AES加密器（ECB模式，PKCS7填充）
    cipher = AES.new(key_bytes, AES.MODE_ECB)

    # 明文处理：转为字节 + PKCS7填充
    plaintext_bytes = plaintext.encode("utf-8")
    padded_bytes = pad(plaintext_bytes, AES.block_size)

    # 执行加密
    encrypted_bytes = cipher.encrypt(padded_bytes)

    # 结果处理：字节 → 十六进制字符串 → Base64编码
    # hex_str = binascii.hexlify(encrypted_bytes).decode('utf-8')
    hex_str = binascii.hexlify(encrypted_bytes).decode("utf-8")
    return base64.b64encode(hex_str.encode("utf-8")).decode("utf-8")


def decrypt1(ciphertext: str, key: str) -> str:
    """decrypt1."""
    # 密钥处理（保持与加密逻辑一致）
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"\0")

    # 创建解密器
    cipher = AES.new(key_bytes, AES.MODE_ECB)

    # Base64解码 → hex解码 → 原始加密字节
    hex_str = base64.b64decode(ciphertext).decode("utf-8")
    encrypted_bytes = binascii.unhexlify(hex_str)

    # 执行解密
    decrypted_bytes = cipher.decrypt(encrypted_bytes)

    # 去除填充并解码
    plaintext_bytes = unpad(decrypted_bytes, AES.block_size)
    return plaintext_bytes.decode("utf-8")


def get_timestamp_str() -> str:
    """get_timestamp_str."""
    return str(int(datetime.now().timestamp() * 1000))


def phase_dev_list(list_data: str) -> list:
    """Filter and classify devices based on their model."""
    # 定义模型与类型的映射关系
    MODEL_TYPE_MAP = {
        "l_dimmer_switch": "light",
        "l_smart_strip_controller": "light",
        "l_smart_color_temperature_spotlight": "light",
        "l_smart_dimming_controller": "light",
        "l_smart_tube_spotlight": "light",
        "l_zf_single_switch": "switch",
        "l_zf_double_switch": "switch",
        "l_zf_three_switch": "switch",
        "l_zf_four_switch": "switch",
        "ss_smart_door_sensor": "senser",
        "ss_ir_curtain_sensor": "senser",
        "ss_exist_human_detector": "senser",
        "ss_ir_radar_human_detector": "senser",
        "env_temp_hum_sensor": "senser",
        "env_4_1_air_genius_formaldehyde": "senser",
        "env_4_1_air_genius_co2": "senser",
        "env_4_1_air_genius_pm25": "senser",
        "env_4_1_air_box_pm25": "senser",
        "env_5_1_air_genius_co2": "senser",
        "env_6_1_air_genius": "senser",
        "env_7_1_air_genius_tvoc": "senser",
        "env_7_1_air_box_tvoc": "senser",
        "env_7_1_air_genius": "senser",
        "env_7_1_air_box": "senser",
        "env_8_1_air_genius": "senser",
        "env_8_1_air_box": "senser",
        "wc_smart_roller_motor": "cover",
        "wc_smart_curtain_motor": "cover",
        "wc_sliding_window_opener": "cover",
        "wc_panning_window_opener": "cover",
        "wc_single_motor_control_panel": "cover",
        "wc_double_motor_control_panel": "cover",
        "wc_dream_curtain_motor": "cover",
        "wc_smart_curtain_motor_box": "cover",
        "hs_smoke_detector": "senser",
        "hs_water_leak_detector": "senser",
        "hs_flammable_gas_detector": "senser",
        "hs_gas_leak_detector": "senser",
        "hs_sos_button": "senser",
        "hvac_thermostat_3h1_e3_child_ac": "climate",
        "hvac_thermostat_3h1_e3_child_fair_power": "fan",
        "hvac_thermostat_3h1_e3_child_wfh": "water_heater",
        "hvac_smart_gateway_engineering_ac": "climate",
        "hvac_smart_gateway_general_ac": "climate",
        "hvac_fresh_air_3h1_th": "fan",
        "hvac_ac_e3": "climate",
    }

    MODEL_ABILITY_MAP = {
        "wc_smart_roller_motor": 2,
        "wc_smart_curtain_motor": 2,
        "wc_sliding_window_opener": 2,
        "wc_panning_window_opener": 2,
        "wc_single_motor_control_panel": 1,
        "wc_double_motor_control_panel": 1,
        "wc_dream_curtain_motor": 3,
        "wc_smart_curtain_motor_box": 2,
    }

    # 定义默认属性
    DEFAULT_PROPERTIES = {
        "ss_smart_door_sensor": {
            "contactState": "close",
            "batteryPercentage": "100",
            "batteryState": "normal",
            "sensorWorkMode": "sensor",
        },
        "ss_ir_curtain_sensor": {
            "curtainAlarmState": "normal",
            "batteryPercentage": "100",
            "batteryState": "normal",
            "sensorWorkMode": "sensor",
            "illumination": "500",
        },
        "ss_exist_human_detector": {
            "illumination": "500",
            "humanDetectedState": "havePerson",
            "humanDistanceState": "0.1",
            "humanDirectionState": "noMovement",
            "humanActiveState": "inactivity",
            "sensorWorkMode": "sensor",
        },
        "ss_ir_radar_human_detector": {
            "humanDetectedState": "havePerson",
            "humanActiveState": "inactivity",
            "batteryPercentage": "100",
            "sensorWorkMode": "sensor",
        },
        "env_temp_hum_sensor": {
            "batteryPercentage": "100",
            "temperature": "20.0",
            "humidity": "30.0",
        },
        "env_4_1_air_genius_formaldehyde": {
            "illumination": "500",
            "formaldehyde": "0.01",
            "humidity": "30.0",
            "temperature": "25.0",
        },
        "env_4_1_air_genius_co2": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
        },
        "env_4_1_air_genius_pm25": {
            "illumination": "500",
            "pm25": "10",
            "humidity": "30.0",
            "temperature": "25.0",
        },
        "env_4_1_air_box_pm25": {
            "illumination": "500",
            "pm25": "10",
            "humidity": "30.0",
            "temperature": "25.0",
        },
        "env_5_1_air_genius_co2": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "tvoc": "30",
        },
        "env_6_1_air_genius": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
        },
        "env_7_1_air_genius_tvoc": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "tvoc": "30",
        },
        "env_7_1_air_box_tvoc": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "tvoc": "30",
        },
        "env_7_1_air_genius": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "formaldehyde": "0.01",
        },
        "env_7_1_air_box": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "formaldehyde": "0.01",
        },
        "env_8_1_air_genius": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "formaldehyde": "0.01",
            "tvoc": "30",
        },
        "env_8_1_air_box": {
            "illumination": "500",
            "co2": "100",
            "humidity": "30.0",
            "temperature": "25.0",
            "pm25": "10",
            "noise": "30",
            "formaldehyde": "0.01",
            "tvoc": "30",
        },
        "wc_smart_roller_motor": {
            "curtainPosition": 0,
            "motorSwitch": "off",
        },
        "wc_smart_curtain_motor": {
            "curtainPosition": 0,
            "motorSwitch": "off",
        },
        "wc_sliding_window_opener": {
            "curtainPosition": 0,
            "motorSwitch": "off",
        },
        "wc_panning_window_opener": {
            "curtainPosition": 0,
            "motorSwitch": "off",
        },
        "wc_single_motor_control_panel": {
            "motorSwitch": "off",
        },
        "wc_double_motor_control_panel": {
            "motorSwitch": "off",
        },
        "wc_dream_curtain_motor": {
            "curtainPosition": 0,
            "motorSwitch": "off",
            "blindAngle": "shading135",
        },
        "wc_smart_curtain_motor_box": {
            "curtainPosition": 0,
            "motorSwitch": "off",
        },
        "hs_smoke_detector": {
            "batteryPercentage": "100",
            "alarmState": "normal",
        },
        "hs_water_leak_detector": {
            "batteryPercentage": "100",
            "alarmState": "normal",
        },
        "hs_flammable_gas_detector": {
            "alarmState": "normal",
        },
        "hs_gas_leak_detector": {
            "alarmState": "normal",
        },
        "hs_sos_button": {
            "batteryPercentage": "100",
            "alarmState": "normal",
        },
        "hvac_thermostat_3h1_e3_child_ac": {
            "currentTemperature": "25",
            "targetTemperature": "26",
            "thermostatMode": "cool",
            "powerSwitch": "off",
            "windSpeed": "low",
            "temperature_max": 32,
            "temperature_min": 16,
            "hvac_modes": ["off", "cool", "heat", "dry", "fan_only"],
            "fan_modes": ["low", "medium", "high", "auto"],
        },
        "hvac_thermostat_3h1_e3_child_fair_power": {
            "powerSwitch": "off",
            "windSpeed": "low",
            "fan_modes": ["low", "mid", "high"],
        },
        "hvac_thermostat_3h1_e3_child_wfh": {
            "currentTemperature": "25",
            "targetTemperature": "26",
            "thermostatMode": "cool",
            "powerSwitch": "off",
            "temperature_max": 32,
            "temperature_min": 16,
            "value_switch_type": "waterValveSwitch",
        },
        "hvac_smart_gateway_engineering_ac": {
            "currentTemperature": "25",
            "targetTemperature": "26",
            "thermostatMode": "cool",
            "powerSwitch": "off",
            "windSpeed": "low",
            "temperature_max": 32,
            "temperature_min": 16,
            "hvac_modes": ["off", "cool", "heat", "dry", "fan_only"],
            "fan_modes": ["low", "medium", "high", "auto"],
        },
        "hvac_smart_gateway_general_ac": {
            "currentTemperature": "25",
            "targetTemperature": "26",
            "thermostatMode": "cool",
            "powerSwitch": "off",
            "windSpeed": "low",
            "temperature_max": 32,
            "temperature_min": 16,
            "hvac_modes": ["off", "cool", "heat", "dry", "fan_only"],
            "fan_modes": ["low", "medium", "high", "auto"],
        },
        "hvac_fresh_air_3h1_th": {
            "powerSwitch": "off",
            "windSpeed": "low",
            "fan_modes": ["low", "mid", "high"],
        },
        "hvac_ac_e3": {
            "currentTemperature": "25",
            "targetTemperature": "26",
            "thermostatMode": "cool",
            "powerSwitch": "off",
            "windSpeed": "low",
            "temperature_max": 32,
            "temperature_min": 16,
            "hvac_modes": ["off", "cool", "heat", "dry", "fan_only"],
            "fan_modes": ["low", "medium", "high", "auto"],
        },
    }

    # 辅助函数：初始化 properties
    def initialize_properties(device, default_properties):
        has_properties = "properties" in device
        is_valid_dict = isinstance(device.get("properties"), dict)
        if not (has_properties and is_valid_dict):
            device["properties"] = {}
        for key, value in default_properties.items():
            if key not in device["properties"]:
                device["properties"][key] = value
        if (
            "humanActiveState" in device["properties"]
            and "humanDetectedState" in device["properties"]
        ):
            if device["properties"]["humanDetectedState"] == "noPerson":
                device["properties"]["humanActiveState"] = "noFeatures"

    # 主逻辑
    filtered_devices = []
    data = json.loads(list_data)
    for device in data.get("deviceList", []):
        model = device.get("model", "")
        if model not in MODEL_TYPE_MAP:
            continue

        # 设置设备类型
        device["type"] = MODEL_TYPE_MAP[model]

        if model in MODEL_ABILITY_MAP:
            if ("channel" in device and device.get("channel", 0) == 0) or (
                "channelNum" in device and device.get("channelNum", 0) == 0
            ):
                continue

            device["ability_type"] = MODEL_ABILITY_MAP[model]

        # 初始化 properties（如果需要）
        if model in DEFAULT_PROPERTIES:
            initialize_properties(device, DEFAULT_PROPERTIES[model])

        # 添加到结果列表
        filtered_devices.append(device)
    # print(filtered_devices)
    return filtered_devices
