# -*- coding: utf-8 -*-
"""怡口软水机传感器实体（信息类：只读显示）

标准声明式写法：SensorEntityDescription 定义实体 + CoordinatorEntity 自动数据更新。
实体按相关性排列：核心状态 → 实时用水 → 设备状态 → 用水统计 → 设备信息。
"""
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EcowaterCoordinator


def _fault_transform(value):
    """故障判断: null/空 = 正常, 有值 = 有故障"""
    if value in (None, "", "null", [], {}):
        return "正常"
    return "有故障"


@dataclass(frozen=True, kw_only=True)
class EcowaterSensorEntityDescription(SensorEntityDescription):
    """怡口传感器实体描述，扩展 data_key(数据字段) 与 transform(换算)"""

    data_key: str | None = None
    transform: Callable | None = None


SENSOR_TYPES: tuple[EcowaterSensorEntityDescription, ...] = (
    # --- 核心状态 ---
    EcowaterSensorEntityDescription(
        key="remaining_salt",
        name="剩余盐量",
        icon="mdi:calendar-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="天",
        suggested_display_precision=0,
        data_key="data13",
    ),
    EcowaterSensorEntityDescription(
        key="available_water",
        name="距下次再生可用水量",
        icon="mdi:water",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=0,
        data_key="data23",
    ),
    # --- 实时用水 ---
    EcowaterSensorEntityDescription(
        key="today_water",
        name="本日用水总量",
        icon="mdi:water",
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="data1D",
    ),
    EcowaterSensorEntityDescription(
        key="current_flow",
        name="即时流量",
        icon="mdi:waves",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/min",
        suggested_display_precision=1,
        data_key="data1C",
    ),
    # --- 设备状态 ---
    EcowaterSensorEntityDescription(
        key="regen_count",
        name="再生次数",
        icon="mdi:refresh",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="次",
        suggested_display_precision=0,
        data_key="data15",
    ),
    EcowaterSensorEntityDescription(
        key="fault_status",
        name="故障状态",
        icon="mdi:alert-circle",
        data_key="fault",
        transform=_fault_transform,
    ),
    EcowaterSensorEntityDescription(
        key="signal_strength",
        name="信号强度",
        icon="mdi:signal",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        data_key="_signal_strength",
    ),
    # --- 用水统计 ---
    EcowaterSensorEntityDescription(
        key="usage_daily_avg",
        name="本日每小时平均用水",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_daily_avg",
    ),
    EcowaterSensorEntityDescription(
        key="usage_week",
        name="近7日用水总量",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_week",
    ),
    EcowaterSensorEntityDescription(
        key="usage_week_avg",
        name="近7日每天平均用水",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_week_avg",
    ),
    EcowaterSensorEntityDescription(
        key="usage_month",
        name="本月用水总量",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_month",
    ),
    EcowaterSensorEntityDescription(
        key="usage_month_avg",
        name="本月每天平均用水",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_month_avg",
    ),
    EcowaterSensorEntityDescription(
        key="usage_year",
        name="本年用水总量",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_year",
    ),
    EcowaterSensorEntityDescription(
        key="usage_year_avg",
        name="本年每月平均用水",
        icon="mdi:chart-line",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="_usage_year_avg",
    ),
    # --- 设备信息 ---
    EcowaterSensorEntityDescription(
        key="model_name",
        name="设备型号",
        icon="mdi:tag-outline",
        data_key="modelName",
    ),
    EcowaterSensorEntityDescription(
        key="serial_number",
        name="产品序列号",
        icon="mdi:barcode",
        data_key="serialNumber",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器平台"""
    coordinator: EcowaterCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    mac = entry.data["mac"]
    async_add_entities(
        EcowaterSensor(coordinator, description, mac)
        for description in SENSOR_TYPES
    )


class EcowaterSensor(CoordinatorEntity[EcowaterCoordinator], SensorEntity):
    """怡口软水机传感器实体"""

    _attr_has_entity_name = True
    entity_description: EcowaterSensorEntityDescription

    def __init__(
        self,
        coordinator: EcowaterCoordinator,
        description: EcowaterSensorEntityDescription,
        mac: str,
    ) -> None:
        """初始化传感器"""
        super().__init__(coordinator)
        self.entity_description = description
        self._mac = mac
        self._attr_unique_id = f"ecowater_{mac}_{description.key}"

    @property
    def native_value(self):
        """从协调器数据读取字段值并换算"""
        data = self.coordinator.data
        if data is None:
            return None
        key = self.entity_description.data_key or self.entity_description.key
        value = data.get(key)
        if self.entity_description.transform:
            return self.entity_description.transform(value)
        return value

    @property
    def device_info(self) -> DeviceInfo:
        """关联到「怡口软水机」设备卡片"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name="怡口软水机",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
