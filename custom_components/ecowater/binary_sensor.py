# -*- coding: utf-8 -*-
"""怡口软水机二进制传感器（在线状态）"""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EcowaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置二进制传感器平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    mac = entry.data["mac"]
    async_add_entities([EcowaterOnlineSensor(coordinator, mac)])


class EcowaterOnlineSensor(CoordinatorEntity[EcowaterCoordinator], BinarySensorEntity):
    """在线状态二进制传感器（开=在线，关=离线）"""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator: EcowaterCoordinator, mac: str) -> None:
        """初始化二进制传感器"""
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = "在线状态"
        self._attr_unique_id = f"ecowater_{mac}_online"

    @property
    def is_on(self) -> bool | None:
        """state 字段 = 1 表示在线"""
        data = self.coordinator.data
        if data is None:
            return None
        return data.get("state") == 1

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
