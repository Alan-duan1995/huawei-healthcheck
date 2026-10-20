"""
华为设备数据采集器
通过 SSH (Netmiko) 连接华为 VRP 设备，执行巡检命令并收集原始输出。
支持真实网络采集与模拟仿真模式（Mock）。
"""

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Union

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
except ImportError:
    ConnectHandler = None
    NetmikoTimeoutException = Exception
    NetmikoAuthenticationException = Exception

logger = logging.getLogger(__name__)

# 线程池，用于将同步的 Netmiko 调用包装为异步操作
_executor = ThreadPoolExecutor(max_workers=10)

# 所有设备通用命令
COMMON_COMMANDS = [
    "display version",
    "display cpu-usage",
    "display memory-usage",
    "display temperature all",
    "display fan",
    "display power",
    "display interface brief",
    "display alarm active",
    "display ntp status",
    "display logbuffer size 50",
]

# 路由器额外命令
ROUTER_COMMANDS = [
    "display ospf peer brief",
    "display bgp peer",
    "display ip routing-table statistics",
]

# 防火墙额外命令
FIREWALL_COMMANDS = [
    "display firewall session table summary",
    "display hrp state",
    "display ipsec sa brief",
]


class DeviceCollector:
    """
    设备数据采集器
    负责通过 SSH 连接到华为 VRP 设备，执行一系列巡检命令并返回原始输出。
    """

    def __init__(
        self,
        device_info: Optional[Union[dict, Any]] = None,
        *,
        host: str = "",
        port: int = 22,
        username: str = "",
        password: str = "",
        device_type: str = "huawei_vrp",
        category: str = "switch",
        name: str = "",
        **kwargs,
    ):
        """
        初始化采集器，兼容字典入参和关键字参数入参
        """
        if isinstance(device_info, dict):
            self.host = device_info.get("host", host)
            self.port = int(device_info.get("port", port) or 22)
            self.username = device_info.get("username", username)
            self.password = device_info.get("password", password)
            self.device_type = device_info.get("device_type", device_type)
            self.category = (device_info.get("category", category) or "switch").lower()
            self.device_name = device_info.get("name", name or self.host)
        else:
            self.host = host
            self.port = int(port or 22)
            self.username = username
            self.password = password
            self.device_type = device_type
            self.category = (category or "switch").lower()
            self.device_name = name or self.host

        # 是否开启 Mock 模拟模式
        self.is_mock = (
            os.getenv("MOCK_INSPECTION", "0") == "1"
            or "mock" in self.host.lower()
            or self.host in ("127.0.0.1", "localhost", "0.0.0.0")
            or "demo" in self.device_name.lower()
            or "mock" in self.device_name.lower()
        )

        # Netmiko 连接参数
        self._connect_params = {
            "device_type": self.device_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "timeout": 20,
            "read_timeout_override": 45,
            "fast_cli": False,
        }

    def test_connection(self) -> bool:
        """测试设备 SSH 连通性（同步执行）"""
        if self.is_mock:
            time.sleep(0.5)
            return True

        if ConnectHandler is None:
            raise RuntimeError("Netmiko 未安装，请先执行 pip install netmiko")

        conn = None
        try:
            conn = ConnectHandler(**self._connect_params)
            return True
        except Exception as e:
            logger.warning(f"设备 {self.device_name}({self.host}) 连通性测试失败: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    async def collect(self) -> dict:
        """
        异步采集设备数据
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(_executor, self._collect_sync)
            return result
        except Exception as e:
            logger.error(f"采集设备 {self.device_name} ({self.host}) 数据时发生未知异常: {e}")
            return {
                "success": False,
                "outputs": {},
                "error": f"未知异常: {str(e)}",
            }

    def _collect_sync(self) -> dict:
        """
        同步采集设备数据（在线程池中执行）
        """
        if self.is_mock:
            time.sleep(1.0)  # 模拟网络交互时延
            return {
                "success": True,
                "outputs": self._generate_mock_outputs(),
                "error": None,
            }

        if ConnectHandler is None:
            return {
                "success": False,
                "outputs": {},
                "error": "Netmiko 未安装，无法建立 SSH 连接",
            }

        outputs = {}
        connection = None

        try:
            logger.info(f"正在连接设备 {self.device_name} ({self.host}:{self.port})...")
            connection = ConnectHandler(**self._connect_params)
            logger.info(f"成功连接到设备 {self.device_name} ({self.host})")

            # 根据设备类别确定要执行的命令列表
            commands = list(COMMON_COMMANDS)
            if self.category == "router":
                commands.extend(ROUTER_COMMANDS)
            elif self.category == "firewall":
                commands.extend(FIREWALL_COMMANDS)

            # 逐条执行命令并收集输出
            for cmd in commands:
                try:
                    logger.debug(f"[{self.device_name}] 执行命令: {cmd}")
                    output = connection.send_command(cmd, read_timeout=45)
                    outputs[cmd] = output
                except Exception as cmd_err:
                    logger.warning(f"[{self.device_name}] 执行命令 '{cmd}' 失败: {cmd_err}")
                    outputs[cmd] = f"ERROR: {str(cmd_err)}"

            logger.info(
                f"设备 {self.device_name} ({self.host}) 数据采集完成，"
                f"成功执行 {sum(1 for v in outputs.values() if not v.startswith('ERROR:'))}/{len(commands)} 条命令"
            )
            return {
                "success": True,
                "outputs": outputs,
                "error": None,
            }

        except NetmikoTimeoutException as e:
            error_msg = f"连接超时: {str(e)}"
            logger.error(f"[{self.device_name}] {error_msg}")
            return {"success": False, "outputs": outputs, "error": error_msg}

        except NetmikoAuthenticationException as e:
            error_msg = f"认证失败: {str(e)}"
            logger.error(f"[{self.device_name}] {error_msg}")
            return {"success": False, "outputs": outputs, "error": error_msg}

        except Exception as e:
            error_msg = f"连接异常: {str(e)}"
            logger.error(f"[{self.device_name}] {error_msg}")
            return {"success": False, "outputs": outputs, "error": error_msg}

        finally:
            if connection:
                try:
                    connection.disconnect()
                except Exception:
                    pass

    def _generate_mock_outputs(self) -> dict:
        """为演示和离线测试生成逼真的华为 VRP 回显数据"""
        cat = self.category
        if cat == "router":
            return {
                "display version": (
                    "Huawei Versatile Routing Platform Software\n"
                    "VRP (R) software, Version 8.180 (NE40E V800R012C10SPC300)\n"
                    "Copyright (C) 2012-2024 HUAWEI TECH CO., LTD.\n"
                    "HUAWEI NE40E-M2K uptime is 185 days, 14 hours, 22 minutes\n"
                    "Patch Version: V800R012SPH020"
                ),
                "display cpu-usage": (
                    "CPU Usage : 24%\n"
                    "CPU using percentage: 24%\n"
                    "CPU utilization for five minutes: 23%"
                ),
                "display memory-usage": (
                    "Memory Using Percentage : 48%\n"
                    "Total Memory: 16384 Mbytes, Used Memory: 7864 Mbytes"
                ),
                "display temperature all": (
                    "SlotID  CardID  SensorID  Status  Temp(C)  Minor(C)  Major(C)  Fatal(C)\n"
                    "1       0       1         Normal  42       65        75        85\n"
                    "2       0       1         Normal  44       65        75        85"
                ),
                "display fan": (
                    "SlotID  FanID   Present  Register  Status  Speed(rpm)\n"
                    "1       FAN1    YES      YES       Normal  3400\n"
                    "1       FAN2    YES      YES       Normal  3450"
                ),
                "display power": (
                    "SlotID  PowerID  Present  Mode  State   Volt(V)  Power(W)\n"
                    "1       PWR1     YES      AC    Normal  220.0    450.0\n"
                    "1       PWR2     YES      AC    Normal  220.0    450.0"
                ),
                "display interface brief": (
                    "Interface                   PHY      Protocol InUti OutUti inErrors outErrors\n"
                    "GigabitEthernet0/0/0        up       up       15%    12%          0         0\n"
                    "GigabitEthernet0/0/1        up       up       22%    18%          2         0\n"
                    "10GE1/0/1                   up       up       45%    50%          0         0\n"
                    "10GE1/0/2                   up       up       40%    42%          0         0\n"
                    "LoopBack0                   up       up(s)     0%     0%          0         0"
                ),
                "display alarm active": "No active alarm.",
                "display ntp status": "clock status: synchronized\nclock stratum: 2\nreference clock: 10.10.1.1",
                "display ospf peer brief": (
                    "Area 0.0.0.0 interface 10GE1/0/1\n"
                    "Router ID       Address         State         Mode\n"
                    "10.255.0.2      10.1.1.2        Full          Nbr is Master"
                ),
                "display bgp peer": (
                    "BGP local router ID : 10.255.0.1\n"
                    "Peer            AS    MsgRcvd    MsgSent    OutQ   Up/Down       State\n"
                    "10.255.0.2     65001   12450      12448       0    180d12h  Established"
                ),
                "display ip routing-table statistics": "Total routes: 4520, Active: 4520",
                "display logbuffer size 50": "%%01INFO/4/LINK_STATE: GigabitEthernet0/0/1 changed status to UP.",
            }
        elif cat == "firewall":
            return {
                "display version": (
                    "Huawei Versatile Routing Platform Software\n"
                    "VRP (R) software, Version 5.170 (USG6600E V500R005C20SPC500)\n"
                    "HUAWEI USG6650E uptime is 98 days, 3 hours, 10 minutes"
                ),
                "display cpu-usage": (
                    "CPU Usage : 38%\n"
                    "CPU utilization for five minutes: 36%"
                ),
                "display memory-usage": "Memory Using Percentage : 62%",
                "display temperature all": "Slot 0 Temperature: 48 C, Normal",
                "display fan": "FAN 1 Status: Normal, Speed: 4200 RPM\nFAN 2 Status: Normal, Speed: 4200 RPM",
                "display power": "Power 1 Status: Normal, State: Supply\nPower 2 Status: Normal, State: Supply",
                "display interface brief": (
                    "Interface                   PHY      Protocol InUti OutUti inErrors outErrors\n"
                    "GigabitEthernet1/0/0        up       up       30%    25%          0         0\n"
                    "GigabitEthernet1/0/1        up       up       28%    32%          0         0\n"
                    "XGigabitEthernet0/0/0       up       up       55%    60%         15         0"
                ),
                "display alarm active": "Minor: 2026-10-18 14:02:11 Session count exceeded 60% threshold",
                "display ntp status": "clock status: synchronized",
                "display firewall session table summary": (
                    "Current Total Sessions : 185420\n"
                    "Max Sessions : 2000000\n"
                    "Session usage : 9.2%"
                ),
                "display hrp state": "The HRP role is Master.",
                "display ipsec sa brief": "Total IPSec SA: 4, Active SA: 4",
                "display logbuffer size 50": "%%01SEC/4/POLICY_PERMIT: Traffic permitted by rule Trust_to_Untrust.",
            }
        else:
            # 默认 Switch
            return {
                "display version": (
                    "Huawei Versatile Routing Platform Software\n"
                    "VRP (R) software, Version 5.170 (CloudEngine S6730-H V200R021C00SPC100)\n"
                    "HUAWEI S6730-H48X6Q uptime is 240 days, 6 hours, 45 minutes"
                ),
                "display cpu-usage": (
                    "CPU Usage : 16%\n"
                    "CPU using percentage: 16%"
                ),
                "display memory-usage": "Memory Using Percentage : 35%",
                "display temperature all": "Slot 1 Sensor 1 Temp: 38 C (Minor 65, Major 75)",
                "display fan": "Fan 1: Status Normal\nFan 2: Status Normal",
                "display power": "Power 1: State Normal\nPower 2: State Normal",
                "display interface brief": (
                    "Interface                   PHY      Protocol InUti OutUti inErrors outErrors\n"
                    "10GE1/0/1                   up       up       12%    10%          0         0\n"
                    "10GE1/0/2                   up       up       15%    14%          0         0\n"
                    "10GE1/0/3                   down     down      0%     0%          0         0\n"
                    "40GE1/0/1                   up       up       25%    30%          0         0\n"
                    "Vlanif10                    up       up        -      -           0         0"
                ),
                "display alarm active": "No active alarm.",
                "display ntp status": "clock status: synchronized",
                "display logbuffer size 50": "%%01IFNET/4/LINK_STATE: 10GE1/0/2 changed status to UP.",
            }
