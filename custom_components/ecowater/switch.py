# -*- coding: utf-8 -*-
"""怡口软水机开关实体（设置类：警报通知开关）"""
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
    FAULT_LOW_TEMP,
    FAULT_LONG_WATER,
    FAULT_LOW_SALT,
    FAULT_WATER_EXHAUSTED,
)
from .coordinator import EcowaterCoordinator


@dataclass(frozen=True, kw_only=True)
class EcowaterSwitchEntityDescription(SwitchEntityDescription):
    """怡口开关实体描述，扩展 fault_code（单个警报的故障代码）"""

    fault_code: str | None = None  # None 表示警报通知总开关


SWITCH_TYPES: tuple[EcowaterSwitchEntityDescription, ...] = (
    EcowaterSwitchEntityDescription(
        key="notice",
        name="警报通知",
        icon="mdi:bell",
        fault_code=None,
    ),
    EcowaterSwitchEntityDescription(
        key="low_temp",
        name="低温警报",
        icon="mdi:snowflake",
        fault_code=FAULT_LOW_TEMP,
    ),
    EcowaterSwitchEntityDescription(
        key="long_water",
        name="长时间出水警报",
        icon="mdi:water-alert",
        fault_code=FAULT_LONG_WATER,
    ),
    EcowaterSwitchEntityDescription(
        key="low_salt",
        name="低盐警报",
        icon="mdi:alert",
        fault_code=FAULT_LOW_SALT,
    ),
    EcowaterSwitchEntityDescription(
        key="water_exhausted",
        name="软水用尽警报",
        icon="mdi:water-off",
        fault_code=FAULT_WATER_EXHAUSTED,
    ),
    EcowaterSwitchEntityDescription(
        key="ota_upgrade",
        name="OTA自动升级",
        icon="mdi:cloud-upload",
        fault_code="OTA",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置开关实体平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: EcowaterApi = hass.data[DOMAIN][entry.entry_id]["api"]
    mac = entry.data["mac"]
    async_add_entities(
        EcowaterSwitch(coordinator, api, mac, description)
        for description in SWITCH_TYPES
    )


class EcowaterSwitch(CoordinatorEntity[EcowaterCoordinator], SwitchEntity):
    """怡口软水机开关实体"""

    _attr_has_entity_name = True
    entity_description: EcowaterSwitchEntityDescription

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        api: EcowaterApi,
        mac: str,
        description: EcowaterSwitchEntityDescription,
    ) -> None:
        """初始化开关实体"""
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"ecowater_{mac}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """读开关状态"""
        data = self.coordinator.data
        if data is None:
            return None
        # OTA 开关读 isUpgrade 字段
        if self.entity_description.fault_code == "OTA":
            return data.get("isUpgrade") == 1
        fault = data.get("_fault_list") or {}
        if self.entity_description.fault_code is None:
            # 警报通知总开关
            return fault.get("isNotice") == 1
        # 单个警报：查 listFaultCode 里的 selected
        for item in fault.get("listFaultCode", []):
            if item.get("faultCode") == self.entity_description.fault_code:
                return item.get("selected") == 1
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """开启"""
        code = self.entity_description.fault_code
        if code == "OTA":
            await self._api.set_ota(True)
        elif code is None:
            await self._api.set_notice(True)
        else:
            await self._api.set_fault(code, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """关闭"""
        code = self.entity_description.fault_code
        if code == "OTA":
            await self._api.set_ota(False)
        elif code is None:
            await self._api.set_notice(False)
        else:
            await self._api.set_fault(code, False)
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
