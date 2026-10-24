# -*- coding: utf-8 -*-
"""怡口软水机集成 UI 配置流

- 用户配置：输入设备 MAC、微信 openid、手机号（用于改名/设备列表）
- 选项流（齿轮）：重新配网（改 WiFi SSID/密码，走设备 Web 界面）
"""
import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .api import EcowaterApi, EcowaterApiError
from .const import DOMAIN, DEFAULT_DEVICE_PASSWORD


class EcowaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理配置流：输入设备 MAC、openid 与手机号"""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """配置第一步：输入 MAC、openid、手机号"""
        errors = {}
        if user_input is not None:
            mac = (user_input.get("mac") or "").strip().upper()
            openid = (user_input.get("openid") or "").strip()
            customer = (user_input.get("customer") or "").strip()
            ip = (user_input.get("ip") or "").strip()
            device_password = user_input.get("device_password") or ""
            if not mac or not openid or not customer:
                errors["base"] = "invalid_input"
            else:
                try:
                    await self._test_connection(mac, openid, customer)
                except EcowaterApiError:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"怡口软水机 ({mac[-4:]})",
                        data={
                            "mac": mac,
                            "openid": openid,
                            "customer": customer,
                            "ip": ip,
                            "device_password": device_password or DEFAULT_DEVICE_PASSWORD,
                        },
                    )

        data_schema = vol.Schema(
            {
                vol.Required("mac"): str,
                vol.Required("openid"): str,
                vol.Required("customer"): str,
                vol.Optional("ip", default="192.168.31.36"): str,
                vol.Optional("device_password", default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_connection(self, mac: str, openid: str, customer: str) -> None:
        """测试连接是否有效，失败抛 EcowaterApiError"""
        async with aiohttp.ClientSession() as session:
            api = EcowaterApi(mac, openid, customer, DEFAULT_DEVICE_PASSWORD, session)
            await api.get_device_status()

    @staticmethod
    def async_get_options_flow(config_entry):
        """返回选项流（集成卡片齿轮按钮）"""
        return EcowaterOptionsFlow()


class EcowaterOptionsFlow(config_entries.OptionsFlow):
    """选项流：重新配网（改 WiFi）"""

    async def async_step_init(self, user_input=None):
        """配网表单：WiFi SSID 与密码"""
        errors = {}
        if user_input is not None:
            ssid = (user_input.get("ssid") or "").strip()
            password = user_input.get("password") or ""
            ip = self.config_entry.data.get("ip") or "192.168.31.36"
            device_password = self.config_entry.data.get("device_password") or DEFAULT_DEVICE_PASSWORD
            if not ssid:
                errors["base"] = "invalid_ssid"
            else:
                try:
                    await self._reconfigure_wifi(ip, ssid, password, device_password)
                except Exception as err:  # noqa: BLE001
                    errors["base"] = "reconfig_fail"
                else:
                    return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required("ssid"): str,
                vol.Required("password"): str,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )

    async def _reconfigure_wifi(
        self, ip: str, ssid: str, password: str, device_password: str
    ) -> None:
        """调用设备 Web 界面 do_cmd_cn.html 改 WiFi"""
        auth = aiohttp.BasicAuth("admin", device_password)
        form = {
            "sta_setting_ssid": ssid,
            "sta_setting_auth": "WPA2PSK",
            "sta_setting_encry": "AES",
            "sta_setting_wpakey": password,
            "wan_setting_dhcp": "DHCP",
        }
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(
                f"http://{ip}/do_cmd_cn.html",
                data=form,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"配网接口返回 HTTP {resp.status}")
