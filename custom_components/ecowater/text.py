# -*- coding: utf-8 -*-
"""怡口软水机文本实体（设备命名）"""
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EcowaterApi
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EcowaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置文本实体平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: EcowaterApi = hass.data[DOMAIN][entry.entry_id]["api"]
    mac = entry.data["mac"]
    async_add_entities([EcowaterName(coordinator, api, mac)])


class EcowaterName(CoordinatorEntity[EcowaterCoordinator], TextEntity):
    """设备命名文本实体"""

    _attr_has_entity_name = True
    _attr_name = "设备命名"
    _attr_icon = "mdi:rename-box"

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        api: EcowaterApi,
        mac: str,
    ) -> None:
        """初始化文本实体"""
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self._attr_unique_id = f"ecowater_{mac}_device_name"

    @property
    def native_value(self) -> str | None:
        """读当前设备名"""
        data = self.coordinator.data
        if data is None:
            return None
        return data.get("deviceName") or data.get("deviceName")

    async def async_set_value(self, value: str) -> None:
        """写新设备名"""
        data = self.coordinator.data
        device_id = data.get("deviceId") if data else None
        if device_id is not None:
            await self._api.rename_device(device_id, value)
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
