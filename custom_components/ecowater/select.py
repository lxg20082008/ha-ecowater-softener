# -*- coding: utf-8 -*-
"""怡口软水机选择实体（设置类：枚举选项）"""
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
    REG_AUTO_OFF_TIME,
    REG_HARDNESS_UNIT,
    REG_REGEN_INTERVAL,
    REG_REGEN_TIME,
    REG_REGEN_TYPE,
    REG_SALT_LACK_ALARM,
    REG_TIME_FORMAT,
    REG_VOLUME_UNIT,
)
from .coordinator import EcowaterCoordinator


def _regen_time_read(value):
    """再生时间读换算: data25 ÷ 256 = 时"""
    try:
        return int(value) // 256
    except (TypeError, ValueError):
        return None


def _regen_time_write(value):
    """再生时间写换算: 时 × 256 = data25"""
    return int(value) * 256


@dataclass(frozen=True, kw_only=True)
class EcowaterSelectEntityDescription(SelectEntityDescription):
    """怡口选择实体描述，扩展寄存器与值映射"""

    register: str
    data_key: str
    value_map: dict  # {寄存器值: 选项标签}
    read_transform: Callable | None = None
    write_transform: Callable | None = None


SELECT_TYPES: tuple[EcowaterSelectEntityDescription, ...] = (
    EcowaterSelectEntityDescription(
        key="regen_mode",
        name="再生模式",
        icon="mdi:refresh",
        options=["自动再生", "立即再生", "预约再生"],
        register=REG_REGEN_TYPE,
        data_key="data02",
        value_map={0: "自动再生", 1: "立即再生", 2: "预约再生"},
    ),
    EcowaterSelectEntityDescription(
        key="regen_time",
        name="再生时间",
        icon="mdi:clock-outline",
        options=[f"{i}时" for i in range(24)],
        register=REG_REGEN_TIME,
        data_key="data25",
        value_map={i: f"{i}时" for i in range(24)},
        read_transform=_regen_time_read,
        write_transform=_regen_time_write,
    ),
    EcowaterSelectEntityDescription(
        key="regen_interval",
        name="再生最大间隔",
        icon="mdi:calendar",
        options=["自动"] + [f"{i}天" for i in range(1, 16)],
        register=REG_REGEN_INTERVAL,
        data_key="data0F",
        value_map={0: "自动", **{i: f"{i}天" for i in range(1, 16)}},
    ),
    EcowaterSelectEntityDescription(
        key="salt_lack_alarm",
        name="低盐警报",
        icon="mdi:alert-outline",
        options=["关闭"] + [f"{i}天" for i in range(1, 100)],
        register=REG_SALT_LACK_ALARM,
        data_key="data31",
        value_map={0: "关闭", **{i: f"{i}天" for i in range(1, 100)}},
    ),
    EcowaterSelectEntityDescription(
        key="time_format",
        name="时间制式",
        icon="mdi:clock-outline",
        options=["12小时制", "24小时制"],
        register=REG_TIME_FORMAT,
        data_key="data0B",
        value_map={0: "12小时制", 1: "24小时制"},
    ),
    EcowaterSelectEntityDescription(
        key="volume_unit",
        name="容积单位",
        icon="mdi:water",
        options=["加仑", "升"],
        register=REG_VOLUME_UNIT,
        data_key="data0C",
        value_map={0: "加仑", 1: "升"},
    ),
    EcowaterSelectEntityDescription(
        key="hardness_unit",
        name="硬度单位",
        icon="mdi:gauge",
        options=["格令", "PPM"],
        register=REG_HARDNESS_UNIT,
        data_key="data0D",
        value_map={0: "格令", 1: "PPM"},
    ),
    EcowaterSelectEntityDescription(
        key="long_water_alarm",
        name="长时间出水提示",
        icon="mdi:timer-outline",
        options=["关闭", "30分钟", "60分钟", "90分钟", "120分钟"],
        register=REG_AUTO_OFF_TIME,
        data_key="data3E",
        value_map={0: "关闭", 30: "30分钟", 60: "60分钟", 90: "90分钟", 120: "120分钟"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置选择实体平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: EcowaterApi = hass.data[DOMAIN][entry.entry_id]["api"]
    mac = entry.data["mac"]
    async_add_entities(
        EcowaterSelect(coordinator, api, mac, description)
        for description in SELECT_TYPES
    )


class EcowaterSelect(CoordinatorEntity[EcowaterCoordinator], SelectEntity):
    """怡口软水机选择实体"""

    _attr_has_entity_name = True
    entity_description: EcowaterSelectEntityDescription

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        api: EcowaterApi,
        mac: str,
        description: EcowaterSelectEntityDescription,
    ) -> None:
        """初始化选择实体"""
        super().__init__(coordinator)
        self._api = api
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"ecowater_{mac}_{description.key}"

    @property
    def current_option(self) -> str | None:
        """读当前选项（含换算）"""
        data = self.coordinator.data
        if data is None:
            return None
        value = data.get(self.entity_description.data_key)
        if self.entity_description.read_transform:
            value = self.entity_description.read_transform(value)
        return self.entity_description.value_map.get(value)

    async def async_select_option(self, option: str) -> None:
        """写新选项（反向映射标签到值，含换算）"""
        reverse = {v: k for k, v in self.entity_description.value_map.items()}
        value = reverse.get(option)
        if value is None:
            return
        if self.entity_description.write_transform:
            value = self.entity_description.write_transform(value)
        await self._api.control_device(self.entity_description.register, value)

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
