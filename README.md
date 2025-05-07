# UIOT Home Integration for Home Assistant

[English](./README.md) | [简体中文](./README_zh.md)

The UIOT integration is an officially supported Home Assistant integration provided by UIOT. It allows you to use UIOT's smart home devices within Home Assistant.

## Installation

Please install it using the following method:

### Method 1:Install via HACS

> 1. make sure you have installed HACS to Home Assistant [HACS install guide](https://hacs.xyz/docs/use/download/download/)
> 2. open HACS, click [Custom repositories], Repository input: `https://github.com/uiotlink/ha_uiot_home`, Category select [Integration]
> 3. **Restart Home Assistant**.


### Method 2:Manual Install

>1. Download `uiot_home.zip` from [Latest Release](https://github.com/uiotlink/ha_uiot_home/releases/latest)
>2. Unzip and copy `uiot_home` to `/custom_components/`. in Home Assistant.
>3. **Restart Home Assistant**.

## Configuration

### Login

[Settings > Devices & Services > Add Integration] > Search for “Uiot Home” > Next > Click here to log in > Log in using your UIOT account credentials. Note: Your account must already have a functioning UIOT host added.

### Device synchronization

After logging in successfully, a list of all host families under the user's account will pop up. Select the family you need to bind, and after submission, all currently supported devices under that family will be automatically synchronized.

## Supported devices

| Name                                     | Function                                                                               |
|:-----------------------------------------|----------------------------------------------------------------------------------------|
| Zero-fire single switch                  | switch                                                                                 |
| Zero-fire double switch                  | switch                                                                                 |
| Zero-fire triple switch                  | switch                                                                                 |
| Zero-fire four switch                    | switch                                                                                 |
| Smart light strip controller             | switch、brightness、color temperature、color                                              |
| Smart color temperature light controller | switch、brightness、color temperature                                                    |
| Smart dimming controller                 | switch、brightness                                                                      |
| Dimmer switch                            | switch、brightness、color temperature                                                    |
| Smart spotlight                          | switch、brightness、color temperature                                                    |
| Smart door/window sensor                 | battery level、working mode、 opening and closing status                                 |
| Infrared curtain detector                | battery level、 light intensity、 alarm status                                           |
| AI super sensor                          | working mode、 lighting、 body movement characteristics、 whether there are people or not |
| Dual-detection sensor                    | working mode、 lighting、 body movement characteristics、 whether there are people or not |
| Temperature and humidity sensor          | battery power、 temperature and humidity status                                         |
| Four-in-one air box（PM2.5）               | light、 temperature、 humidity、pm2.5                                                     |
| Four-in-one air sensor（PM2.5）            | light、 temperature、 humidity、pm2.5                                                     |
| Four-in-one air sensor（formaldehyde）     | light、 temperature、 humidity、formaldehyde                                              |
| Four-in-one air sensor（CO2）              | light、 temperature、 humidity、co2                                                       |
| Five-in-one air sensor（CO2）              | light、 temperature、 humidity、co2、TVOC                                                  |
| Seven-in-one air box                     | light、 temperature、 humidity、co2、pm2.5、noise、formaldehyde                              |
| Seven-in-one air box（TVOC）               | light、 temperature、 humidity、co2、pm2.5、noise、TVOC                                      |
| Seven-in-one air sensor                  | light、 temperature、 humidity、co2、pm2.5、noise、formaldehyde                              |
| Seven-in-one air sensor（TVOC）            | light、 temperature、 humidity、co2、pm2.5、noise、TVOC                                      |
| Eight-in-one air box                     | light、 temperature、 humidity、co2、pm2.5、noise、formaldehyde、TVOC                         |
| Eight-in-one air sensor                  | light、 temperature、 humidity、co2、pm2.5、noise、formaldehyde、TVOC                         |
| Single-channel motor panel               | on、off、pause                                                                           |
| Dual-channel motor panel                 | on、off、pause                                                                           |
| Smart curtain motor                      | on、off、pause、opening and closing degree                                                |
| Smart roller blind motor                 | on、off、pause、opening and closing degree                                                |
| Lithium battery smart curtain motor      | on、off、pause、opening and closing degree                                                |
| Smart sliding window opener              | on、off、pause、opening and closing degree                                                |
| Smart push-pull window opener            | on、off、pause、opening and closing degree                                                |
| Dooya tubular motor control box          | on、off、pause、opening and closing degree                                                |
| Dream curtain motor                      | on、off、pause、opening and closing degree、rotation angle                                 |
| Six-in-one air sensor                    | light、 temperature、 humidity、co2、pm2.5、noise                                           |
| Fresh air                                | on、off、set speed                                                                       |

