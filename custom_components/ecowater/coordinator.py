# -*- coding: utf-8 -*-
"""怡口软水机数据协调器

统一拉取设备状态，所有传感器共享同一份数据，避免重复请求。
"""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcowaterApi, EcowaterApiError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EcowaterCoordinator(DataUpdateCoordinator):
    """数据协调器：每 60 秒拉取设备全量状态"""

    def __init__(self, hass: HomeAssistant, api: EcowaterApi, ip: str) -> None:
        """初始化协调器"""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self._api = api
        self._ip = ip
        self.fault_list: dict = {}  # 警报通知列表（含各开关状态）

    async def _async_update_data(self) -> dict:
        """拉取设备状态与警报列表，返回 data[0] 对象（含 _fault_list、deviceName）"""
        try:
            device = await self._api.get_device_status()
            fault = await self._api.get_fault_list()
            # 把警报列表合并进 data，这样开关状态变化会触发实体更新
            device["_fault_list"] = fault
            # 拉设备列表获取 deviceName（devByDeviceMac 无此字段）
            try:
                device_list = await self._api.get_device_list()
                if device_list:
                    device["deviceName"] = device_list[0].get("deviceName", "")
            except EcowaterApiError:
                pass
            # 拉取日/周/月/年用水统计（总量 + 平均）
            try:
                for period in ("daily", "week", "month", "year"):
                    usage = await self._api.get_usage(period)
                    device[f"_usage_{period}"] = usage["total"]
                    device[f"_usage_{period}_avg"] = usage["average"]
            except EcowaterApiError:
                pass
            # 拉取 WiFi 信号强度（设备 Web 界面）
            try:
                device["_signal_strength"] = await self._api.get_signal_strength(self._ip)
            except EcowaterApiError:
                pass
            return device
        except EcowaterApiError as err:
            # 转换为 UpdateFailed，HA 会把实体标记为不可用并记录日志
            raise UpdateFailed(f"拉取设备状态失败: {err}") from err
