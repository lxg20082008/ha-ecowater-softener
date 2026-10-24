# -*- coding: utf-8 -*-
"""怡口云 API 客户端

封装鉴权、设备状态、用水统计等接口调用。
使用微信 openid 自动获取/刷新 ewtoken（openid 固定，token 会过期）。
"""
import logging

import aiohttp

from .const import (
    API_BASE,
    API_DEVICE_STATUS,
    API_DAILY_USAGE,
    API_LOAD_CONFIG,
    API_GET_TOKEN,
    API_DEVICE_CONTROL,
    API_FAULT_LIST,
    API_FAULT_ADD,
    API_FAULT_REMOVE,
    API_FAULT_IS_NOTICE,
    API_FAULT_NO_NOTICE,
    API_IS_UPGRADE,
    API_RENAME,
    API_DEVICE_LIST,
    API_USAGE,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class EcowaterApiError(Exception):
    """怡口 API 异常"""


class EcowaterApi:
    """怡口云 API 客户端

    用 openid 自动获取/刷新 ewtoken，业务接口鉴权过期时自动重试。
    """

    def __init__(
        self,
        mac: str,
        openid: str,
        customer: str,
        device_password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """初始化客户端

        :param mac: 设备 MAC（无冒号大写，如 E8FDF8A55A80）
        :param openid: 微信 openid（固定标识，用于获取 token）
        :param customer: 手机号（改名/设备列表用）
        :param device_password: 设备 Web 界面密码
        :param session: aiohttp 会话（由调用方管理生命周期）
        """
        self._mac = mac
        self._openid = openid
        self._customer = customer
        self._device_password = device_password
        self._session = session
        self._token: str | None = None

    async def get_device_status(self) -> dict:
        """获取设备全量状态，返回 data[0] 对象"""
        await self._ensure_token()
        try:
            return await self._fetch_device_status()
        except EcowaterApiError as err:
            # token 过期(鉴权错误 30001)时刷新 token 并重试一次
            if "30001" in str(err) or "鉴权" in str(err):
                _LOGGER.warning("ewtoken 过期，自动刷新")
                await self._fetch_token()
                return await self._fetch_device_status()
            raise

    async def get_daily_usage(self, day=None) -> dict:
        """获取指定日期的用水统计"""
        await self._ensure_token()
        from datetime import date

        target = day or date.today()
        payload = await self._request(
            API_DAILY_USAGE,
            {"mac": self._mac, "currentDay": target.isoformat()},
        )
        return payload.get("data") or {}

    async def get_device_config(self) -> dict:
        """获取设备字段配置映射（dataXX 含义）"""
        await self._ensure_token()
        payload = await self._request(API_LOAD_CONFIG, {"mac": self._mac}, method="GET")
        return payload.get("data") or {}

    async def control_device(self, register: str, value) -> dict:
        """设备控制：写寄存器或触发操作

        :param register: 寄存器号（如 "1E" 总硬度、"03" 自检）
        :param value: 写入值（如 1 触发自检、20 设置硬度）
        """
        await self._ensure_token()
        return await self._request(
            API_DEVICE_CONTROL,
            {"mac": self._mac, register: value},
        )

    async def get_fault_list(self) -> dict:
        """获取警报通知列表（含各警报开关状态）"""
        await self._ensure_token()
        payload = await self._request(
            API_FAULT_LIST,
            {"deviceMac": self._mac, "modelCode": "000201"},
        )
        return payload.get("data") or {}

    async def set_fault(self, fault_code: str, enabled: bool) -> None:
        """开启/关闭单个警报通知

        :param fault_code: 故障代码（E101 低温/3D 长时间出水/16 低盐/30 软水用尽）
        :param enabled: True 开启, False 关闭
        """
        await self._ensure_token()
        if enabled:
            await self._request(
                API_FAULT_ADD,
                {
                    "devicemac": self._mac,
                    "modelCode": "000201",
                    "faultcode": fault_code,
                    "remindInterval": 30,
                },
            )
        else:
            await self._request(
                API_FAULT_REMOVE,
                {"deviceMac": self._mac, "faultCode": fault_code},
            )

    async def set_notice(self, enabled: bool) -> None:
        """开启/关闭警报通知总开关"""
        await self._ensure_token()
        path = API_FAULT_IS_NOTICE if enabled else API_FAULT_NO_NOTICE
        await self._request(path, {"mac": self._mac})

    async def set_ota(self, enabled: bool) -> None:
        """开启/关闭 OTA 自动升级"""
        await self._ensure_token()
        await self._request(
            API_IS_UPGRADE,
            {"mac": self._mac, "flag": 1 if enabled else 0},
        )

    async def get_device_list(self) -> list:
        """获取设备列表（含 deviceName、deviceId）"""
        await self._ensure_token()
        payload = await self._request(
            API_DEVICE_LIST,
            {"customer": self._customer, "modelCode": "00"},
        )
        return payload.get("data") or []

    async def rename_device(self, device_id: int, name: str) -> None:
        """修改设备名称"""
        await self._ensure_token()
        await self._request(
            API_RENAME,
            {
                "customer": self._customer,
                "deviceId": device_id,
                "deviceName": name,
            },
        )

    async def get_usage(self, period: str) -> dict:
        """获取用水统计总量与平均值

        :param period: daily/week/month/year
        :return: {"total": 总量, "average": 平均值}
        """
        await self._ensure_token()
        from datetime import date

        today = date.today()
        if period == "daily":
            data = {"mac": self._mac, "currentDay": today.isoformat()}
        elif period == "week":
            data = {"mac": self._mac, "endTime": today.isoformat()}
        elif period == "month":
            data = {"mac": self._mac, "whichyear": today.year, "monthInYear": today.month}
        elif period == "year":
            data = {"mac": self._mac, "whichyear": today.year}
        else:
            return {"total": 0.0, "average": 0.0}

        payload = await self._request(API_USAGE.format(period), data)
        usage = payload.get("data") or {}
        own_total = usage.get("ownTotal") or [0]
        own_average = usage.get("ownAverage") or [0]
        return {"total": float(own_total[0]), "average": float(own_average[0])}

    async def get_signal_strength(self, ip: str) -> int | None:
        """获取 WiFi 信号强度（%），从设备 Web 界面解析 cover_sta_rssi"""
        import re

        auth = aiohttp.BasicAuth("admin", self._device_password)
        try:
            async with self._session.get(
                f"http://{ip}/status_cn.html",
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except aiohttp.ClientError:
            return None

        match = re.search(r'cover_sta_rssi\s*=\s*"(\d+)%"', text)
        if match:
            return int(match.group(1))
        return None

    async def _fetch_device_status(self) -> dict:
        """拉取设备状态（带 ewtoken 鉴权）"""
        payload = await self._request(API_DEVICE_STATUS, {"deviceMac": self._mac})
        devices = payload.get("data") or []
        if not devices:
            raise EcowaterApiError("API 未返回设备数据")
        return devices[0]

    async def _ensure_token(self) -> None:
        """确保持有 token，没有则获取"""
        if self._token is None:
            await self._fetch_token()

    async def _fetch_token(self) -> None:
        """用 openid 调 getCustomer 获取新 ewtoken"""
        payload = await self._request(
            API_GET_TOKEN,
            {"openid": self._openid},
            use_auth=False,
        )
        token = payload.get("data")
        if not token:
            raise EcowaterApiError("获取 token 失败：响应无 data")
        self._token = f"customer{token}"
        _LOGGER.debug("已获取新 ewtoken: customer%s...", token[:8])

    async def _request(
        self,
        path: str,
        data: dict,
        method: str = "POST",
        use_auth: bool = True,
    ) -> dict:
        """发起请求并统一处理错误

        :param path: 接口路径（如 /api/applets/...）
        :param data: 表单参数
        :param method: GET 或 POST
        :param use_auth: 是否带 ewtoken 鉴权头（getCustomer 等接口为 False）
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if use_auth:
            headers["ewtoken"] = self._token or ""

        url = f"{API_BASE}{path}"
        try:
            if method == "GET":
                async with self._session.get(
                    url,
                    params=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    status = resp.status
                    payload = await resp.json(content_type=None)
            else:
                async with self._session.post(
                    url,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    status = resp.status
                    payload = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise EcowaterApiError(f"网络错误: {err}") from err
        except ValueError as err:
            raise EcowaterApiError(f"响应解析失败: {err}") from err

        if status != 200:
            raise EcowaterApiError(f"API 返回 HTTP {status}")

        # 怡口接口通用返回结构: {"resCode": "0", "resMsg": "ok", "data": ...}
        # 部分接口(统计/配置)用 {"code": 200, "msg": "..."}
        code = payload.get("resCode") or payload.get("code")
        if code not in (None, "0", 0, 200, "200"):
            msg = payload.get("resMsg") or payload.get("msg")
            raise EcowaterApiError(f"API 业务错误 {code}: {msg}")
        return payload
