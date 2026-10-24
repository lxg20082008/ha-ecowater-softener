# -*- coding: utf-8 -*-
"""怡口软水机 (Ecowater) 集成

通过 UI 配置流添加（设置 -> 设备与服务 -> 添加集成 -> 怡口软水机）。
输入设备 MAC 与微信 openid，自动创建「怡口软水机」设备卡片及全部传感器实体。
支持多设备（按 entry_id 隔离）。
"""
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api import EcowaterApi
from .const import DOMAIN, MANUFACTURER, MODEL, SW_VERSION, DEFAULT_DEVICE_PASSWORD
from .coordinator import EcowaterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置 config entry：创建设备 + 数据协调器 + 加载平台"""
    mac = entry.data["mac"]
    openid = entry.data["openid"]
    customer = entry.data.get("customer") or ""
    device_password = entry.data.get("device_password") or DEFAULT_DEVICE_PASSWORD
    ip = entry.data.get("ip") or "192.168.31.36"

    # 数据协调器（含 API 客户端，用 openid 自动获取/刷新 token）
    session = aiohttp.ClientSession()
    api = EcowaterApi(mac, openid, customer, device_password, session)
    coordinator = EcowaterCoordinator(hass, api, ip)
    await coordinator.async_refresh()

    # 在设备注册表中创建设备（关联到当前 config entry）
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac)},
        name="怡口软水机",
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=SW_VERSION,
    )

    # 按 entry_id 存储（支持多设备）
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "mac": mac,
        "api": api,
        "session": session,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载 config entry"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})
        session = data.get("session")
        if session:
            await session.close()
    return unload_ok
