# -*- coding: utf-8 -*-
"""怡口软水机按钮实体（操作类）"""
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EcowaterApi
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    REG_REGEN_TYPE,
    REG_SELF_CHECK,
)
from .coordinator import EcowaterCoordinator


@dataclass(frozen=True, kw_only=True)
class EcowaterButtonEntityDescription(ButtonEntityDescription):
    """怡口按钮实体描述，扩展 register(寄存器) 与 value(写入值)"""

    register: str
    value: int = 1


BUTTON_TYPES: tuple[EcowaterButtonEntityDescription, ...] = (
    EcowaterButtonEntityDescription(
        key="regen_now",
        name="立即再生",
        icon="mdi:refresh",
        register=REG_REGEN_TYPE,
        value=1,
    ),
    EcowaterButtonEntityDescription(
        key="self_check",
        name="设备自检",
        icon="mdi:clipboard-check",
        register=REG_SELF_CHECK,
        value=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置按钮平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: EcowaterApi = hass.data[DOMAIN][entry.entry_id]["api"]
    mac = entry.data["mac"]
    async_add_entities(
        EcowaterButton(coordinator, api, mac, description)
        for description in BUTTON_TYPES
    )


class EcowaterButton(CoordinatorEntity[EcowaterCoordinator], ButtonEntity):
    """怡口软水机按钮实体"""

    _attr_has_entity_name = True
    entity_description: EcowaterButtonEntityDescription

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        api: EcowaterApi,
        mac: str,
        description: EcowaterButtonEntityDescription,
    ) -> None:
        """初始化按钮"""
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"ecowater_{mac}_{description.key}"

    async def async_press(self) -> None:
        """按下按钮：调用 device/control 触发操作"""
        await self._api.control_device(
            self.entity_description.register,
            self.entity_description.value,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
