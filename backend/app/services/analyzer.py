"""
健康分析引擎
基于采集到的设备数据，通过加权评分算法计算设备健康分数，
并生成健康等级和问题列表。
"""

import logging
from typing import Optional

from app.services import parsers

logger = logging.getLogger(__name__)

# 默认阈值配置（可通过 config.yaml 覆盖）
DEFAULT_THRESHOLDS = {
    "cpu": {"warning": 60, "critical": 80},
    "memory": {"warning": 70, "critical": 85},
    "temperature": {"warning": 55, "critical": 70},
    "error_packets": {"warning": 100, "critical": 1000},
    "session_usage_percent": {"warning": 60, "critical": 80},
}

# 基础指标权重（适用于所有设备类型）
BASE_WEIGHTS = {
    "cpu": 15,
    "memory": 15,
    "temperature": 10,
    "fan": 10,
    "power": 10,
    "interfaces": 15,
    "alarms": 15,
    "ntp": 10,
}

# 路由器额外指标权重
ROUTER_EXTRA_WEIGHTS = {
    "ospf": 10,
    "bgp": 10,
}

# 防火墙额外指标权重
FIREWALL_EXTRA_WEIGHTS = {
    "sessions": 10,
    "ha": 10,
}


class HealthAnalyzer:
    """
    健康分析器
    解析设备原始输出数据，计算健康分数并生成分析报告。
    """

    def __init__(self, thresholds: Optional[dict] = None):
        """
        初始化分析器

        Args:
            thresholds: 告警阈值配置字典，格式为:
                {
                    "cpu": {"warning": 60, "critical": 80},
                    "memory": {"warning": 70, "critical": 85},
                    ...
                }
                如果未提供，使用默认阈值。
        """
        self.thresholds = thresholds if thresholds else DEFAULT_THRESHOLDS

    def analyze(self, raw_outputs: dict, category: str) -> dict:
        """
        分析设备健康状况

        Args:
            raw_outputs: 命令名称 -> 原始输出的映射字典
            category: 设备类别（switch/router/firewall）

        Returns:
            dict: 包含以下字段:
                - cpu_usage (float): CPU 使用率
                - memory_usage (float): 内存使用率
                - temperature (float): 温度
                - fan_status (str): 风扇状态
                - power_status (str): 电源状态
                - uptime (str): 运行时间
                - interface_summary (dict): 接口统计
                - alarm_summary (dict): 告警统计
                - ntp_status (str): NTP 同步状态
                - routing_info (dict): 路由信息（路由器专有）
                - firewall_info (dict): 防火墙信息（防火墙专有）
                - health_score (float): 健康分数 (0-100)
                - health_level (str): 健康等级
                - issues (list): 问题列表
        """
        category = category.lower()
        issues = []

        # ===== 解析各项指标 =====
        cpu_usage = parsers.parse_cpu_usage(
            raw_outputs.get("display cpu-usage", "")
        )
        memory_usage = parsers.parse_memory_usage(
            raw_outputs.get("display memory-usage", "")
        )
        temperature = parsers.parse_temperature(
            raw_outputs.get("display temperature all", "")
        )
        fan_status = parsers.parse_fan_status(
            raw_outputs.get("display fan", "")
        )
        power_status = parsers.parse_power_status(
            raw_outputs.get("display power", "")
        )
        uptime = parsers.parse_uptime(
            raw_outputs.get("display version", "")
        )
        interface_summary = parsers.parse_interfaces(
            raw_outputs.get("display interface brief", "")
        )
        alarm_summary = parsers.parse_alarms(
            raw_outputs.get("display alarm active", "")
        )
        ntp_status = parsers.parse_ntp_status(
            raw_outputs.get("display ntp status", "")
        )

        # 路由器专有指标
        routing_info = {}
        if category == "router":
            ospf_peers = parsers.parse_ospf_peers(
                raw_outputs.get("display ospf peer brief", "")
            )
            bgp_peers = parsers.parse_bgp_peers(
                raw_outputs.get("display bgp peer", "")
            )
            routing_stats = parsers.parse_routing_stats(
                raw_outputs.get("display ip routing-table statistics", "")
            )
            routing_info = {
                "ospf_peers": ospf_peers,
                "bgp_peers": bgp_peers,
                "routing_stats": routing_stats,
            }

        # 防火墙专有指标
        firewall_info = {}
        if category == "firewall":
            fw_sessions = parsers.parse_firewall_sessions(
                raw_outputs.get("display firewall session table summary", "")
            )
            hrp_state = parsers.parse_hrp_state(
                raw_outputs.get("display hrp state", "")
            )
            ipsec_sa = parsers.parse_ipsec_sa(
                raw_outputs.get("display ipsec sa brief", "")
            )
            firewall_info = {
                "sessions": fw_sessions,
                "hrp_state": hrp_state,
                "ipsec_sa": ipsec_sa,
            }

        # ===== 计算各指标分数 =====
        scores = {}

        # CPU 分数
        if cpu_usage is not None:
            scores["cpu"] = self._score_metric(
                cpu_usage,
                self.thresholds.get("cpu", {}).get("warning", 60),
                self.thresholds.get("cpu", {}).get("critical", 80),
            )
            if scores["cpu"] <= 20:
                issues.append(f"⚠️ CPU 使用率过高: {cpu_usage}%（严重阈值: "
                              f"{self.thresholds.get('cpu', {}).get('critical', 80)}%）")
            elif scores["cpu"] <= 60:
                issues.append(f"⚡ CPU 使用率偏高: {cpu_usage}%（告警阈值: "
                              f"{self.thresholds.get('cpu', {}).get('warning', 60)}%）")
        else:
            scores["cpu"] = 50  # 无法获取时给中间分
            issues.append("❓ 无法获取 CPU 使用率信息")

        # 内存分数
        if memory_usage is not None:
            scores["memory"] = self._score_metric(
                memory_usage,
                self.thresholds.get("memory", {}).get("warning", 70),
                self.thresholds.get("memory", {}).get("critical", 85),
            )
            if scores["memory"] <= 20:
                issues.append(f"⚠️ 内存使用率过高: {memory_usage}%（严重阈值: "
                              f"{self.thresholds.get('memory', {}).get('critical', 85)}%）")
            elif scores["memory"] <= 60:
                issues.append(f"⚡ 内存使用率偏高: {memory_usage}%（告警阈值: "
                              f"{self.thresholds.get('memory', {}).get('warning', 70)}%）")
        else:
            scores["memory"] = 50
            issues.append("❓ 无法获取内存使用率信息")

        # 温度分数
        if temperature is not None:
            scores["temperature"] = self._score_metric(
                temperature,
                self.thresholds.get("temperature", {}).get("warning", 55),
                self.thresholds.get("temperature", {}).get("critical", 70),
            )
            if scores["temperature"] <= 20:
                issues.append(f"⚠️ 设备温度过高: {temperature}°C（严重阈值: "
                              f"{self.thresholds.get('temperature', {}).get('critical', 70)}°C）")
            elif scores["temperature"] <= 60:
                issues.append(f"⚡ 设备温度偏高: {temperature}°C（告警阈值: "
                              f"{self.thresholds.get('temperature', {}).get('warning', 55)}°C）")
        else:
            scores["temperature"] = 80  # 无温度传感器的设备给较高默认分

        # 风扇分数
        if fan_status == "Normal":
            scores["fan"] = 100
        elif fan_status == "Abnormal":
            scores["fan"] = 20
            issues.append("⚠️ 风扇状态异常，请检查散热系统")
        else:
            scores["fan"] = 60
            issues.append("❓ 无法确认风扇状态")

        # 电源分数
        if power_status == "Normal":
            scores["power"] = 100
        elif power_status == "Abnormal":
            scores["power"] = 20
            issues.append("⚠️ 电源状态异常，请检查供电系统")
        else:
            scores["power"] = 60
            issues.append("❓ 无法确认电源状态")

        # 接口分数（基于 down 接口占比）
        if interface_summary["total"] > 0:
            down_ratio = interface_summary["down"] / interface_summary["total"]
            if down_ratio == 0:
                scores["interfaces"] = 100
            elif down_ratio < 0.1:
                scores["interfaces"] = 80
            elif down_ratio < 0.3:
                scores["interfaces"] = 60
                issues.append(
                    f"⚡ 存在 {interface_summary['down']} 个接口 DOWN "
                    f"（共 {interface_summary['total']} 个接口）"
                )
            else:
                scores["interfaces"] = 30
                issues.append(
                    f"⚠️ 大量接口 DOWN: {interface_summary['down']}/"
                    f"{interface_summary['total']}"
                )
        else:
            scores["interfaces"] = 60
            issues.append("❓ 无法获取接口信息")

        # 告警分数
        if alarm_summary["total"] == 0:
            scores["alarms"] = 100
        elif alarm_summary["critical"] > 0:
            scores["alarms"] = 10
            issues.append(
                f"🚨 存在 {alarm_summary['critical']} 条严重告警！"
            )
        elif alarm_summary["major"] > 0:
            scores["alarms"] = 30
            issues.append(
                f"⚠️ 存在 {alarm_summary['major']} 条主要告警"
            )
        elif alarm_summary["minor"] > 0:
            scores["alarms"] = 60
            issues.append(
                f"⚡ 存在 {alarm_summary['minor']} 条次要告警"
            )
        else:
            scores["alarms"] = 80
            issues.append(
                f"💡 存在 {alarm_summary['warning']} 条警告信息"
            )

        # NTP 分数
        if ntp_status == "synchronized":
            scores["ntp"] = 100
        else:
            scores["ntp"] = 30
            issues.append("⚠️ NTP 时间未同步，可能影响日志和证书校验")

        # ===== 计算加权健康分数 =====
        weights = dict(BASE_WEIGHTS)

        # 路由器额外评分
        if category == "router":
            weights.update(ROUTER_EXTRA_WEIGHTS)

            ospf_peers_data = routing_info.get("ospf_peers", {})
            if ospf_peers_data.get("total", 0) > 0:
                if ospf_peers_data["full"] == ospf_peers_data["total"]:
                    scores["ospf"] = 100
                elif ospf_peers_data["full"] > 0:
                    scores["ospf"] = 60
                    not_full = ospf_peers_data["total"] - ospf_peers_data["full"]
                    issues.append(
                        f"⚡ {not_full} 个 OSPF 邻居未达到 Full 状态"
                    )
                else:
                    scores["ospf"] = 20
                    issues.append("⚠️ 所有 OSPF 邻居均不在 Full 状态")
            else:
                scores["ospf"] = 80  # 没有 OSPF 邻居可能是正常的

            bgp_peers_data = routing_info.get("bgp_peers", {})
            if bgp_peers_data.get("total", 0) > 0:
                if bgp_peers_data["established"] == bgp_peers_data["total"]:
                    scores["bgp"] = 100
                elif bgp_peers_data["established"] > 0:
                    scores["bgp"] = 60
                    not_established = bgp_peers_data["total"] - bgp_peers_data["established"]
                    issues.append(
                        f"⚡ {not_established} 个 BGP 邻居未建立"
                    )
                else:
                    scores["bgp"] = 20
                    issues.append("⚠️ 所有 BGP 邻居均未建立")
            else:
                scores["bgp"] = 80

        # 防火墙额外评分
        if category == "firewall":
            weights.update(FIREWALL_EXTRA_WEIGHTS)

            fw_sessions_data = firewall_info.get("sessions", {})
            session_usage = fw_sessions_data.get("usage_percent", 0)
            if session_usage > 0:
                scores["sessions"] = self._score_metric(
                    session_usage,
                    self.thresholds.get("session_usage_percent", {}).get("warning", 60),
                    self.thresholds.get("session_usage_percent", {}).get("critical", 80),
                )
                if scores["sessions"] <= 20:
                    issues.append(
                        f"⚠️ 防火墙会话使用率过高: {session_usage}%"
                    )
                elif scores["sessions"] <= 60:
                    issues.append(
                        f"⚡ 防火墙会话使用率偏高: {session_usage}%"
                    )
            else:
                scores["sessions"] = 80

            hrp_state = firewall_info.get("hrp_state", "Unknown")
            if hrp_state in ("Active", "Standby"):
                scores["ha"] = 100
            elif hrp_state == "Active Standalone":
                scores["ha"] = 60
                issues.append("⚡ 防火墙双机热备处于 Active Standalone 状态，备机可能异常")
            elif hrp_state == "Unknown":
                scores["ha"] = 60
                issues.append("❓ 无法确认防火墙双机热备状态")
            else:
                scores["ha"] = 40
                issues.append(f"⚠️ 防火墙双机热备状态异常: {hrp_state}")

        # 计算加权平均分
        total_weight = 0
        weighted_sum = 0
        for metric, weight in weights.items():
            if metric in scores:
                weighted_sum += scores[metric] * weight
                total_weight += weight

        health_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0

        # 确定健康等级
        if health_score >= 80:
            health_level = "healthy"
        elif health_score >= 60:
            health_level = "warning"
        else:
            health_level = "critical"

        logger.info(
            f"健康分析完成: 分数={health_score}, 等级={health_level}, "
            f"发现 {len(issues)} 个问题"
        )

        # ===== 组装返回结果 =====
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "temperature": temperature,
            "fan_status": fan_status,
            "power_status": power_status,
            "uptime": uptime,
            "interface_summary": interface_summary,
            "alarm_summary": alarm_summary,
            "ntp_status": ntp_status,
            "routing_info": routing_info if category == "router" else {},
            "firewall_info": firewall_info if category == "firewall" else {},
            "health_score": health_score,
            "health_level": health_level,
            "issues": issues,
            "metric_scores": scores,  # 各指标的独立分数，用于报告展示
        }

    def _score_metric(
        self, value: float, warning_threshold: float, critical_threshold: float
    ) -> int:
        """
        对单一指标进行评分

        Args:
            value: 指标实际值
            warning_threshold: 告警阈值
            critical_threshold: 严重阈值

        Returns:
            int: 分数值
                - 100: 正常（低于告警阈值）
                - 60:  告警（介于告警和严重阈值之间）
                - 20:  严重（超过严重阈值）
        """
        if value >= critical_threshold:
            return 20
        elif value >= warning_threshold:
            return 60
        else:
            return 100
