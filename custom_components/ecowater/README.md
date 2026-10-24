# 怡口软水机 (Ecowater China) Home Assistant 集成

将国内版怡口软水机（609ECM 等型号）接入 Home Assistant，以「怡口软水机」设备卡片形式展示实时数据。

## 功能特性

- **设备卡片**：所有实体关联到统一的「怡口软水机」设备
- **16 个实体**：可用水量、剩余盐量、再生次数、今日用水量、即时流量、总硬度、再生时间、工作天数、盐位档位、低盐警报、距下次再生、剩余容量、累计流量、累计值、故障状态、在线状态
- **在线状态**：二进制传感器（开=在线，关=离线）
- **故障状态**：基于设备自检结果，设备异常时自动变「有故障」
- **60 秒自动刷新**：云端轮询

## 安装

### 方式一：HACS（推荐）

1. HACS → 自定义存储库 → 添加本仓库（类别：集成）
2. 安装「怡口软水机 (Ecowater China)」
3. 重启 Home Assistant

### 方式二：手动安装

1. 将 `custom_components/ecowater/` 目录复制到 HA 配置目录的 `custom_components/` 下
2. 重启 Home Assistant

## 配置

1. 设置 → 设备与服务 → 添加集成 → 搜索「怡口」
2. 输入设备 **MAC**、**openid** 和**手机号**
3. 提交（会自动验证连接）

## 如何获取 MAC 和 openid

| 参数 | 说明 | 示例 |
|---|---|---|
| MAC | 设备 MAC 地址（无冒号大写） | 抓包获取 |
| openid | 微信 openid（固定标识，用于自动获取 token） | 抓包获取 |
| customer | 手机号（绑定设备的账号） | 注册手机号 |

获取方式：抓包微信小程序与 `iot2.chinaecowater.com` 的通信，在 `customer/getCustomer` 接口的请求体（`openid=` 参数）或 `customer/openid` 接口的响应中获取。详见项目文档。

## 数据源说明

| 服务器 | 用途 |
|---|---|
| `iot2.chinaecowater.com` | 云 API（盐量/水量/再生状态等业务数据） |
| `192.168.31.36`（设备本体） | WiFi 模块本地后台（配网/重启，本集成不直接使用） |

## 字段映射（dataXX → 界面）

| dataXX | 含义 |
|---|---|
| data23 | 可用水量 / 距下次再生（L） |
| data13 | 剩余盐量（天） |
| data15 | 再生次数 |
| data1D | 今日用水量（L） |
| data1C | 即时流量（L/min） |
| data1E | 总硬度（÷1.71 = 格令） |
| data25 | 再生时间（时×256+分） |
| data14 | 工作天数 |
| data2A | 盐位档位 |
| data31 | 低盐警报（天） |
| fault | 故障（null=正常） |

## 注意事项

- **token 自动刷新**：用 openid 自动获取/刷新 token，永不过期
- 本集成适配**国内版**怡口（`iot2.chinaecowater.com`），不适用国外版（Ayla IoT / iQua）

## 许可证

MIT
