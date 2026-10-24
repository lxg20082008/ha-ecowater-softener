# -*- coding: utf-8 -*-
"""怡口软水机数字实体（设置类：可写数值）"""
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EcowaterApi
from .const import DOMAIN, MANUFACTURER, MODEL, REG_HARDNESS, REG_SALT_LEVEL
from .coordinator import EcowaterCoordinator


def _hardness_read(value):
    """总硬度读换算: data1E ÷ 1.71 = 格令"""
    try:
        return round(float(value) / 1.71)
    except (TypeError, ValueError):
        return None


def _hardness_write(value):
    """总硬度写换算: 格令 × 1.71 = data1E"""
    return round(float(value) * 1.71)


@dataclass(frozen=True, kw_only=True)
class EcowaterNumberEntityDescription(NumberEntityDescription):
    """怡口数字实体描述，扩展寄存器与读写换算"""

    register: str
    data_key: str
    read_transform: Callable | None = None
    write_transform: Callable | None = None


NUMBER_TYPES: tuple[EcowaterNumberEntityDescription, ...] = (
    EcowaterNumberEntityDescription(
        key="hardness",
        name="总硬度",
        icon="mdi:gauge",
        native_min_value=1,
        native_max_value=160,
        native_step=1,
        register=REG_HARDNESS,
        data_key="data1E",
        read_transform=_hardness_read,
        write_transform=_hardness_write,
    ),
    EcowaterNumberEntityDescription(
        key="salt_level",
        name="盐位",
        icon="mdi:gauge",
        native_min_value=0,
        native_max_value=8,
        native_step=1,
        register=REG_SALT_LEVEL,
        data_key="data2A",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置数字实体平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: EcowaterApi = hass.data[DOMAIN][entry.entry_id]["api"]
    mac = entry.data["mac"]
    async_add_entities(
        EcowaterNumber(coordinator, api, mac, description)
        for description in NUMBER_TYPES
    )


class EcowaterNumber(CoordinatorEntity[EcowaterCoordinator], NumberEntity):
    """怡口软水机数字实体"""

    _attr_has_entity_name = True
    entity_description: EcowaterNumberEntityDescription

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        api: EcowaterApi,
        mac: str,
        description: EcowaterNumberEntityDescription,
    ) -> None:
        """初始化数字实体"""
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"ecowater_{mac}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """读当前值（含换算）"""
        data = self.coordinator.data
        if data is None:
            return None
        value = data.get(self.entity_description.data_key)
        if self.entity_description.read_transform:
            return self.entity_description.read_transform(value)
        return value

    async def async_set_native_value(self, value: float) -> None:
        """写新值（含换算）到设备"""
        if self.entity_description.write_transform:
            value = self.entity_description.write_transform(value)
        await self._api.control_device(self.entity_description.register, int(value))

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
