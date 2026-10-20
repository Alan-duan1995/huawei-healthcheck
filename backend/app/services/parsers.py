"""
华为 VRP 命令输出解析器
使用正则表达式从各种 display 命令的输出中提取关键指标。
每个解析器都有健壮的错误处理，解析失败时返回合理的默认值。
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_cpu_usage(output: str) -> Optional[float]:
    """
    解析 display cpu-usage 命令输出，提取 CPU 使用率

    支持的输出格式:
        CPU Usage : 15%
        CPU usage  : 15%
        CPU Usage    :15%
        cpu-usage : 15%

    Args:
        output: 命令原始输出

    Returns:
        float: CPU 使用率百分比，解析失败返回 None
    """
    if not output or output.startswith("ERROR:"):
        return None
    try:
        # 匹配常见的 CPU 使用率格式
        patterns = [
            r'CPU\s*[Uu]sage\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'cpu-usage\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'CPU\s*[Uu]sing\s*[Pp]ercentage\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            # 匹配表格格式中五分钟平均 CPU 使用率
            r'five\s+(?:minutes|min)\s*:?\s*(\d+(?:\.\d+)?)\s*%',
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                logger.debug(f"解析 CPU 使用率: {value}%")
                return value

        # 尝试匹配纯数字行（某些简化输出格式）
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', output)
        if match:
            return float(match.group(1))

        logger.warning("无法从输出中解析 CPU 使用率")
        return None
    except Exception as e:
        logger.error(f"解析 CPU 使用率时出错: {e}")
        return None


def parse_memory_usage(output: str) -> Optional[float]:
    """
    解析 display memory-usage 命令输出，提取内存使用率

    支持的输出格式:
        Memory Using Percentage : 45%
        Memory Using Percentage Is: 45%
        memory usage: 45%

    Args:
        output: 命令原始输出

    Returns:
        float: 内存使用率百分比，解析失败返回 None
    """
    if not output or output.startswith("ERROR:"):
        return None
    try:
        patterns = [
            r'[Mm]emory\s+[Uu]sing\s+[Pp]ercentage\s*(?:[Ii]s)?\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'[Mm]emory\s+[Uu]sage\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'[Mm]emory\s+[Uu]tilization\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'[Uu]sed\s*:\s*\d+.*[Tt]otal\s*:\s*\d+.*[Uu]sage\s*:?\s*(\d+(?:\.\d+)?)\s*%',
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                logger.debug(f"解析内存使用率: {value}%")
                return value

        # 尝试从 Used/Total 计算内存使用率
        used_match = re.search(r'[Uu]sed\s*:\s*(\d+)', output)
        total_match = re.search(r'[Tt]otal\s*:\s*(\d+)', output)
        if used_match and total_match:
            used = int(used_match.group(1))
            total = int(total_match.group(1))
            if total > 0:
                return round(used / total * 100, 2)

        logger.warning("无法从输出中解析内存使用率")
        return None
    except Exception as e:
        logger.error(f"解析内存使用率时出错: {e}")
        return None


def parse_temperature(output: str) -> Optional[float]:
    """
    解析 display temperature all 命令输出，提取最高温度值

    Args:
        output: 命令原始输出

    Returns:
        float: 最高温度（摄氏度），解析失败返回 None
    """
    if not output or output.startswith("ERROR:"):
        return None
    try:
        # 匹配所有温度值（整数或小数）
        temp_values = []

        # 匹配 "当前温度" 格式
        patterns = [
            r'[Cc]urrent\s*(?:[Tt]emperature)?\s*:?\s*(\d+(?:\.\d+)?)',
            r'[Tt]emperature\s*:?\s*(\d+(?:\.\d+)?)\s*(?:C|℃|°)',
            r'(\d+(?:\.\d+)?)\s*(?:C|℃|°)\s',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output)
            for m in matches:
                try:
                    val = float(m)
                    # 合理温度范围过滤（排除明显不合理的值）
                    if 0 <= val <= 150:
                        temp_values.append(val)
                except ValueError:
                    continue

        if temp_values:
            max_temp = max(temp_values)
            logger.debug(f"解析最高温度: {max_temp}°C")
            return max_temp

        logger.warning("无法从输出中解析温度信息")
        return None
    except Exception as e:
        logger.error(f"解析温度时出错: {e}")
        return None


def parse_fan_status(output: str) -> str:
    """
    解析 display fan 命令输出，判断风扇状态

    Args:
        output: 命令原始输出

    Returns:
        str: 'Normal' 或 'Abnormal'，解析失败返回 'Unknown'
    """
    if not output or output.startswith("ERROR:"):
        return "Unknown"
    try:
        output_lower = output.lower()

        # 检查是否存在异常关键字
        abnormal_keywords = ["abnormal", "absent", "failed", "fault", "error", "not present"]
        for keyword in abnormal_keywords:
            if keyword in output_lower:
                logger.debug("检测到风扇异常状态")
                return "Abnormal"

        # 检查是否存在正常关键字
        normal_keywords = ["normal", "ok", "present", "active"]
        for keyword in normal_keywords:
            if keyword in output_lower:
                logger.debug("风扇状态正常")
                return "Normal"

        logger.warning("无法判断风扇状态")
        return "Unknown"
    except Exception as e:
        logger.error(f"解析风扇状态时出错: {e}")
        return "Unknown"


def parse_power_status(output: str) -> str:
    """
    解析 display power 命令输出，判断电源状态

    Args:
        output: 命令原始输出

    Returns:
        str: 'Normal' 或 'Abnormal'，解析失败返回 'Unknown'
    """
    if not output or output.startswith("ERROR:"):
        return "Unknown"
    try:
        output_lower = output.lower()

        # 检查是否存在异常关键字
        abnormal_keywords = ["abnormal", "absent", "failed", "fault", "error", "not supply"]
        for keyword in abnormal_keywords:
            if keyword in output_lower:
                logger.debug("检测到电源异常状态")
                return "Abnormal"

        # 检查是否存在正常关键字
        normal_keywords = ["normal", "supply", "present", "ok", "active"]
        for keyword in normal_keywords:
            if keyword in output_lower:
                logger.debug("电源状态正常")
                return "Normal"

        logger.warning("无法判断电源状态")
        return "Unknown"
    except Exception as e:
        logger.error(f"解析电源状态时出错: {e}")
        return "Unknown"


def parse_uptime(output: str) -> str:
    """
    解析 display version 命令输出，提取设备运行时间

    Args:
        output: 命令原始输出

    Returns:
        str: 运行时间字符串，解析失败返回 'Unknown'
    """
    if not output or output.startswith("ERROR:"):
        return "Unknown"
    try:
        # 匹配 uptime 格式: "uptime is 120 days, 5 hours, 30 minutes"
        patterns = [
            r'[Uu]ptime\s+is\s+(.*?)(?:\n|$)',
            r'[Uu]ptime\s*:\s*(.*?)(?:\n|$)',
            r'has\s+been\s+running\s+for\s+(.*?)(?:\n|$)',
            r'[Rr]un\s+[Tt]ime\s*:?\s*(.*?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                uptime_str = match.group(1).strip().rstrip(",")
                logger.debug(f"解析运行时间: {uptime_str}")
                return uptime_str

        logger.warning("无法从输出中解析运行时间")
        return "Unknown"
    except Exception as e:
        logger.error(f"解析运行时间时出错: {e}")
        return "Unknown"


def parse_interfaces(output: str) -> dict:
    """
    解析 display interface brief 命令输出，统计接口状态

    Args:
        output: 命令原始输出

    Returns:
        dict: {'total': N, 'up': N, 'down': N, 'admin_down': N}
    """
    result = {"total": 0, "up": 0, "down": 0, "admin_down": 0}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        lines = output.strip().split("\n")

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # 跳过表头行（通常包含 Interface、PHY、Protocol 等关键字）
            if re.match(r'^(Interface|InUti|---)', line_stripped, re.IGNORECASE):
                continue

            # 匹配接口行：接口名 + 状态
            # 常见格式：GE0/0/1  up  up  ...
            #           GE0/0/2  down  down  ...
            #           GE0/0/3  *down  down  ...  (* 表示管理性关闭)
            intf_match = re.match(
                r'^(\S+)\s+(\*?(?:up|down|(?:admin\s*down)))\s+',
                line_stripped,
                re.IGNORECASE
            )
            if intf_match:
                result["total"] += 1
                phy_status = intf_match.group(2).lower()
                if phy_status == "up":
                    result["up"] += 1
                elif phy_status.startswith("*") or "admin" in phy_status:
                    result["admin_down"] += 1
                else:
                    result["down"] += 1

        logger.debug(
            f"解析接口统计: 总计={result['total']}, "
            f"UP={result['up']}, DOWN={result['down']}, "
            f"管理性关闭={result['admin_down']}"
        )
        return result
    except Exception as e:
        logger.error(f"解析接口信息时出错: {e}")
        return result


def parse_alarms(output: str) -> dict:
    """
    解析 display alarm active 命令输出，统计告警信息

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'total': N,
            'critical': N,
            'major': N,
            'minor': N,
            'warning': N,
            'details': [告警描述字符串列表]
        }
    """
    result = {
        "total": 0,
        "critical": 0,
        "major": 0,
        "minor": 0,
        "warning": 0,
        "details": [],
    }
    if not output or output.startswith("ERROR:"):
        return result

    try:
        # 检查是否没有活动告警
        if re.search(r'[Nn]o\s+(?:active\s+)?alarm', output, re.IGNORECASE):
            logger.debug("没有活动告警")
            return result

        lines = output.strip().split("\n")

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # 跳过表头和分隔符
            if re.match(r'^(Sequence|---|\s*$)', line_stripped, re.IGNORECASE):
                continue

            line_lower = line_stripped.lower()

            # 判断告警级别
            if "critical" in line_lower:
                result["critical"] += 1
                result["total"] += 1
                result["details"].append(line_stripped)
            elif "major" in line_lower:
                result["major"] += 1
                result["total"] += 1
                result["details"].append(line_stripped)
            elif "minor" in line_lower:
                result["minor"] += 1
                result["total"] += 1
                result["details"].append(line_stripped)
            elif "warning" in line_lower:
                result["warning"] += 1
                result["total"] += 1
                result["details"].append(line_stripped)
            elif re.search(r'\d{4}-\d{2}-\d{2}', line_stripped):
                # 包含日期的行可能是告警行（没有明确级别标识）
                result["warning"] += 1
                result["total"] += 1
                result["details"].append(line_stripped)

        logger.debug(
            f"解析告警统计: 总计={result['total']}, "
            f"严重={result['critical']}, 主要={result['major']}, "
            f"次要={result['minor']}, 警告={result['warning']}"
        )
        return result
    except Exception as e:
        logger.error(f"解析告警信息时出错: {e}")
        return result


def parse_ntp_status(output: str) -> str:
    """
    解析 display ntp status 命令输出，判断 NTP 同步状态

    Args:
        output: 命令原始输出

    Returns:
        str: 'synchronized' 或 'unsynchronized'
    """
    if not output or output.startswith("ERROR:"):
        return "unsynchronized"
    try:
        output_lower = output.lower()

        # 检查同步状态
        if "synchronized" in output_lower and "unsynchronized" not in output_lower:
            logger.debug("NTP 已同步")
            return "synchronized"

        if "clock is synchronized" in output_lower:
            return "synchronized"

        if "stratum" in output_lower:
            # 有层级信息通常意味着已同步
            stratum_match = re.search(r'stratum\s*:?\s*(\d+)', output_lower)
            if stratum_match:
                stratum = int(stratum_match.group(1))
                if 1 <= stratum <= 15:
                    return "synchronized"

        logger.debug("NTP 未同步")
        return "unsynchronized"
    except Exception as e:
        logger.error(f"解析 NTP 状态时出错: {e}")
        return "unsynchronized"


def parse_ospf_peers(output: str) -> dict:
    """
    解析 display ospf peer brief 命令输出，提取 OSPF 邻居信息

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'total': N,
            'full': N,
            'peers': [{'neighbor': ip, 'state': state, 'interface': intf}]
        }
    """
    result = {"total": 0, "full": 0, "peers": []}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        lines = output.strip().split("\n")

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 匹配 OSPF 邻居行：通常包含 IP 地址和状态
            # 格式示例：10.1.1.2  GE0/0/1  Full  ...
            match = re.match(
                r'(\d+\.\d+\.\d+\.\d+)\s+\S+\s+(\S+)\s+(\S+)',
                line_stripped
            )
            if not match:
                # 尝试另一种格式
                match = re.match(
                    r'(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+.*?(Full|Init|2-Way|ExStart|Exchange|Loading|Down)',
                    line_stripped,
                    re.IGNORECASE
                )

            if match:
                groups = match.groups()
                neighbor = groups[0]
                # 根据匹配组数确定接口和状态
                if len(groups) >= 3:
                    interface = groups[1]
                    state = groups[2]
                else:
                    interface = ""
                    state = groups[1] if len(groups) >= 2 else "Unknown"

                peer_info = {
                    "neighbor": neighbor,
                    "state": state,
                    "interface": interface,
                }
                result["peers"].append(peer_info)
                result["total"] += 1
                if state.lower() == "full":
                    result["full"] += 1

        logger.debug(f"解析 OSPF 邻居: 总计={result['total']}, Full={result['full']}")
        return result
    except Exception as e:
        logger.error(f"解析 OSPF 邻居信息时出错: {e}")
        return result


def parse_bgp_peers(output: str) -> dict:
    """
    解析 display bgp peer 命令输出，提取 BGP 邻居信息

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'total': N,
            'established': N,
            'peers': [{'peer': ip, 'state': state, 'prefixes': N}]
        }
    """
    result = {"total": 0, "established": 0, "peers": []}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        lines = output.strip().split("\n")

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 匹配 BGP 邻居行
            # 格式示例：10.1.1.2  4  65001  ...  Established  120
            match = re.match(
                r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+)\s+.*?'
                r'(Established|Idle|Connect|Active|OpenSent|OpenConfirm)\s*(\d*)',
                line_stripped,
                re.IGNORECASE
            )
            if match:
                peer_ip = match.group(1)
                state = match.group(3)
                prefixes_str = match.group(4)
                prefixes = int(prefixes_str) if prefixes_str else 0

                peer_info = {
                    "peer": peer_ip,
                    "state": state,
                    "prefixes": prefixes,
                }
                result["peers"].append(peer_info)
                result["total"] += 1
                if state.lower() == "established":
                    result["established"] += 1
            else:
                # 尝试简化匹配
                simple_match = re.match(
                    r'(\d+\.\d+\.\d+\.\d+)\s+.*?(Established|Idle|Connect|Active|OpenSent|OpenConfirm)',
                    line_stripped,
                    re.IGNORECASE
                )
                if simple_match:
                    peer_ip = simple_match.group(1)
                    state = simple_match.group(2)
                    peer_info = {
                        "peer": peer_ip,
                        "state": state,
                        "prefixes": 0,
                    }
                    result["peers"].append(peer_info)
                    result["total"] += 1
                    if state.lower() == "established":
                        result["established"] += 1

        logger.debug(f"解析 BGP 邻居: 总计={result['total']}, Established={result['established']}")
        return result
    except Exception as e:
        logger.error(f"解析 BGP 邻居信息时出错: {e}")
        return result


def parse_routing_stats(output: str) -> dict:
    """
    解析 display ip routing-table statistics 命令输出，提取路由统计信息

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'total_routes': N,
            'active_routes': N,
            'protocols': {'Direct': N, 'Static': N, 'OSPF': N, 'BGP': N, ...}
        }
    """
    result = {"total_routes": 0, "active_routes": 0, "protocols": {}}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        # 匹配总路由数
        total_match = re.search(
            r'[Tt]otal\s*(?:[Nn]umber\s+of\s+)?[Rr]outes?\s*:?\s*(\d+)', output
        )
        if total_match:
            result["total_routes"] = int(total_match.group(1))

        # 匹配活跃路由数
        active_match = re.search(
            r'[Aa]ctive\s*(?:[Rr]outes?)?\s*:?\s*(\d+)', output
        )
        if active_match:
            result["active_routes"] = int(active_match.group(1))

        # 匹配各协议路由数
        protocol_patterns = [
            (r'[Dd]irect\s*:?\s*(\d+)', "Direct"),
            (r'[Ss]tatic\s*:?\s*(\d+)', "Static"),
            (r'OSPF\s*:?\s*(\d+)', "OSPF"),
            (r'BGP\s*:?\s*(\d+)', "BGP"),
            (r'IS-?IS\s*:?\s*(\d+)', "IS-IS"),
            (r'RIP\s*:?\s*(\d+)', "RIP"),
        ]
        for pattern, proto_name in protocol_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                result["protocols"][proto_name] = int(match.group(1))

        logger.debug(
            f"解析路由统计: 总计={result['total_routes']}, "
            f"活跃={result['active_routes']}"
        )
        return result
    except Exception as e:
        logger.error(f"解析路由统计信息时出错: {e}")
        return result


def parse_firewall_sessions(output: str) -> dict:
    """
    解析 display firewall session table summary 命令输出，提取会话统计

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'current': N,
            'max': N,
            'usage_percent': float
        }
    """
    result = {"current": 0, "max": 0, "usage_percent": 0.0}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        # 匹配当前会话数
        current_patterns = [
            r'[Cc]urrent\s+[Ss]ession(?:s)?\s*:?\s*(\d+)',
            r'[Tt]otal\s+[Ss]ession(?:s)?\s*:?\s*(\d+)',
            r'[Cc]urrent\s+[Tt]otal(?:Sessions)?\s*:?\s*(\d+)',
        ]
        for pattern in current_patterns:
            match = re.search(pattern, output)
            if match:
                result["current"] = int(match.group(1))
                break

        # 匹配最大会话数
        max_patterns = [
            r'[Mm]ax(?:imum)?\s+[Ss]ession(?:s)?\s*:?\s*(\d+)',
            r'[Ss]ession\s+[Ll]imit\s*:?\s*(\d+)',
            r'[Mm]ax\s*:?\s*(\d+)',
        ]
        for pattern in max_patterns:
            match = re.search(pattern, output)
            if match:
                result["max"] = int(match.group(1))
                break

        # 计算使用率
        if result["max"] > 0:
            result["usage_percent"] = round(
                result["current"] / result["max"] * 100, 2
            )

        logger.debug(
            f"解析防火墙会话: 当前={result['current']}, "
            f"最大={result['max']}, 使用率={result['usage_percent']}%"
        )
        return result
    except Exception as e:
        logger.error(f"解析防火墙会话信息时出错: {e}")
        return result


def parse_hrp_state(output: str) -> str:
    """
    解析 display hrp state 命令输出，提取双机热备状态

    Args:
        output: 命令原始输出

    Returns:
        str: HA 状态描述（如 'Active', 'Standby', 'Active Standalone'），
             解析失败返回 'Unknown'
    """
    if not output or output.startswith("ERROR:"):
        return "Unknown"
    try:
        # 匹配 HRP 状态
        patterns = [
            r'[Ss]tate\s*:?\s*(Active(?:\s+Standalone)?|Standby|Initial)',
            r'[Rr]ole\s*:?\s*(Active(?:\s+Standalone)?|Standby|Primary|Secondary)',
            r'HRP_[AM]\[(.+?)\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                state = match.group(1).strip()
                logger.debug(f"解析 HRP 状态: {state}")
                return state

        # 通过关键字判断
        output_lower = output.lower()
        if "active" in output_lower:
            return "Active"
        elif "standby" in output_lower:
            return "Standby"

        logger.warning("无法判断 HRP 状态")
        return "Unknown"
    except Exception as e:
        logger.error(f"解析 HRP 状态时出错: {e}")
        return "Unknown"


def parse_ipsec_sa(output: str) -> dict:
    """
    解析 display ipsec sa brief 命令输出，提取 IPSec SA 信息

    Args:
        output: 命令原始输出

    Returns:
        dict: {
            'total': N,
            'tunnels': [
                {'name': str, 'peer': str, 'status': str}
            ]
        }
    """
    result = {"total": 0, "tunnels": []}
    if not output or output.startswith("ERROR:"):
        return result
    try:
        # 检查是否没有 SA
        if re.search(r'[Nn]o\s+(?:IPSec\s+)?SA', output, re.IGNORECASE):
            return result

        lines = output.strip().split("\n")
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # 跳过表头
            if re.match(r'^(Number|---|\s*$|Interface)', line_stripped, re.IGNORECASE):
                continue

            # 匹配隧道行
            # 格式示例: policy1  10.1.1.2  ESP  ...
            match = re.match(
                r'(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\S+)',
                line_stripped
            )
            if match:
                tunnel_info = {
                    "name": match.group(1),
                    "peer": match.group(2),
                    "status": match.group(3),
                }
                result["tunnels"].append(tunnel_info)
                result["total"] += 1

        logger.debug(f"解析 IPSec SA: 总计={result['total']} 条隧道")
        return result
    except Exception as e:
        logger.error(f"解析 IPSec SA 信息时出错: {e}")
        return result
