# -*- coding: utf-8 -*-
"""怡口软水机集成常量定义"""

DOMAIN = "ecowater"

# 云 API 服务器与接口路径
API_BASE = "https://iot2.chinaecowater.com"
API_DEVICE_STATUS = "/api/applets/cusDev/devByDeviceMac"
API_DAILY_USAGE = "/api/app/statiscal/daily"
API_LOAD_CONFIG = "/api/applets/model/cusLoadConifgsByMac"
API_GET_TOKEN = "/api/applets/customer/getCustomer"
API_DEVICE_CONTROL = "/api/applets/device/control"
API_FAULT_LIST = "/api/applets/cusDevFault/list"
API_FAULT_ADD = "/api/applets/cusDevFault/add"
API_FAULT_REMOVE = "/api/applets/cusDevFault/remove"
API_FAULT_IS_NOTICE = "/api/applets/cusDevFault/isNotice"
API_FAULT_NO_NOTICE = "/api/applets/cusDevFault/noNotice"
API_IS_UPGRADE = "/api/applets/device/isUpgrade"
API_RENAME = "/api/applets/cusDev/rename"
API_DEVICE_LIST = "/api/applets/cusDev/cusDevListByMC3New"
API_USAGE = "/api/app/statiscal/{}"  # {} = daily/week/month/year

# 轮询间隔(秒)
SCAN_INTERVAL = 60
# 请求超时(秒)
REQUEST_TIMEOUT = 20

# 设备信息
MANUFACTURER = "Ecowater"
MODEL = "609ECM"
SW_VERSION = "v1.4.2"

# 设备 Web 界面（HF-LPC300 模块）默认登录凭据
DEFAULT_DEVICE_PASSWORD = "A-life-mate"

# 设备实体属性
ATTR_FAULT_DETAIL = "fault_detail"

# 设备控制寄存器号（device/control 写入用，mac=xxx&寄存器=值）
REG_REGEN_TYPE = "02"       # 再生类型（02=1 触发立即再生）
REG_SELF_CHECK = "03"       # 设备自检（03=1 触发自检）
REG_TIME_FORMAT = "0B"      # 时间制式（0=12h, 1=24h）
REG_VOLUME_UNIT = "0C"      # 容积单位（0=加仑, 1=升）
REG_HARDNESS_UNIT = "0D"    # 硬度单位（0=格令, 1=PPM）
REG_REGEN_INTERVAL = "0F"   # 再生最大间隔（0=自动, 1-15=天）
REG_HARDNESS = "1E"         # 总硬度（ppm/10 存储，格令=值÷1.71）
REG_REGEN_TIME = "25"       # 再生时间（时×256+分）
REG_SALT_LEVEL = "2A"       # 盐位档位
REG_SALT_LACK_ALARM = "31"  # 低盐警报（0=关闭, 1-99=天）
REG_AUTO_OFF_TIME = "3E"    # 长时间出水提示（0=关闭, 30/60/90/120=分钟）

# 警报故障代码（cusDevFault 接口用）
FAULT_LOW_TEMP = "E101"       # 低温警报
FAULT_LONG_WATER = "3D"       # 长时间出水警报
FAULT_LOW_SALT = "16"         # 低盐警报
FAULT_WATER_EXHAUSTED = "30"  # 软水用尽警报
