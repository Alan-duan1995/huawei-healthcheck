"""
巡检报告生成器
优先使用 Jinja2 模板引擎生成专业的 HTML 格式巡检报告；
在未安装 Jinja2 的纯标准库环境下，自动降级为内置原生渲染器，确保开箱即用零崩溃。
"""

import html
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")
DEFAULT_OUTPUT_DIR = str(Path("./reports").resolve())


class ReportGenerator:
    """
    巡检报告生成器
    """

    def __init__(
        self,
        template_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR

        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.env = None
        if HAS_JINJA2:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self.env.filters["status_color"] = self._get_status_color
            self.env.filters["score_level"] = self._get_score_level
            self.env.filters["format_percent"] = self._format_percent
            self.env.filters["format_value"] = self._format_value

    def _normalize_task(self, task: Union[dict, Any]) -> dict:
        if isinstance(task, dict):
            return task
        return {
            "id": getattr(task, "id", None),
            "name": getattr(task, "name", "Huawei-Inspection"),
            "status": getattr(task, "status", "completed"),
            "total_devices": getattr(task, "total_devices", 0),
            "completed_devices": getattr(task, "completed_devices", 0),
            "start_time": getattr(task, "start_time", None),
            "end_time": getattr(task, "end_time", None),
        }

    def _normalize_result(self, r: Union[dict, Any]) -> dict:
        if isinstance(r, dict):
            item = dict(r)
        else:
            item = {
                "id": getattr(r, "id", None),
                "device_name": getattr(r, "device_name", "未知设备"),
                "device_host": getattr(r, "device_host", ""),
                "category": getattr(r, "category", "switch"),
                "status": getattr(r, "status", "completed"),
                "health_score": getattr(r, "health_score", 0),
                "cpu_usage": getattr(r, "cpu_usage", None),
                "memory_usage": getattr(r, "memory_usage", None),
                "temperature": getattr(r, "temperature", None),
                "fan_status": getattr(r, "fan_status", None),
                "power_status": getattr(r, "power_status", None),
                "uptime": getattr(r, "uptime", None),
                "ntp_status": getattr(r, "ntp_status", None),
                "error_message": getattr(r, "error_message", None),
            }
            if hasattr(r, "_analysis") and isinstance(r._analysis, dict):
                item.update(r._analysis)
            else:
                raw_interface = getattr(r, "interface_summary", None)
                if isinstance(raw_interface, str) and raw_interface:
                    try:
                        item["interface_summary"] = json.loads(raw_interface)
                    except Exception:
                        pass
                raw_alarm = getattr(r, "alarm_summary", None)
                if isinstance(raw_alarm, str) and raw_alarm:
                    try:
                        item["alarm_summary"] = json.loads(raw_alarm)
                    except Exception:
                        pass

        score = item.get("health_score") or 0
        if "health_level" not in item:
            if score >= 80:
                item["health_level"] = "healthy"
            elif score >= 60:
                item["health_level"] = "warning"
            else:
                item["health_level"] = "critical"

        if "issues" not in item:
            item["issues"] = []
            if item.get("status") == "failed":
                item["issues"].append(item.get("error_message") or "采集失败")
            if (item.get("cpu_usage") or 0) >= 80:
                item["issues"].append(f"CPU使用率高达 {item['cpu_usage']}%")
            if (item.get("memory_usage") or 0) >= 85:
                item["issues"].append(f"内存使用率高达 {item['memory_usage']}%")
            if item.get("fan_status") and "abnormal" in str(item["fan_status"]).lower():
                item["issues"].append(f"风扇状态异常: {item['fan_status']}")
            if item.get("power_status") and "abnormal" in str(item["power_status"]).lower():
                item["issues"].append(f"电源状态异常: {item['power_status']}")

        return item

    def generate(self, task: Union[dict, Any], results: list[Union[dict, Any]]) -> str:
        """生成 HTML 巡检报告"""
        try:
            task_dict = self._normalize_task(task)
            normalized_results = [self._normalize_result(r) for r in results]

            overall_score = self._calculate_overall_score(normalized_results)
            health_matrix = self._generate_health_matrix(normalized_results)

            healthy_count = sum(1 for r in normalized_results if r.get("health_level") == "healthy" and r.get("status") != "failed")
            warning_count = sum(1 for r in normalized_results if r.get("health_level") == "warning" and r.get("status") != "failed")
            critical_count = sum(1 for r in normalized_results if r.get("health_level") == "critical" and r.get("status") != "failed")
            failed_count = sum(1 for r in normalized_results if r.get("status") == "failed")

            all_issues = []
            for r in normalized_results:
                device_label = f"{r.get('device_name', '未知')} ({r.get('device_host', '')})"
                for issue in r.get("issues", []):
                    all_issues.append({
                        "device": device_label,
                        "issue": issue,
                        "health_level": r.get("health_level", "warning"),
                    })

            if overall_score >= 80:
                overall_level = "healthy"
            elif overall_score >= 60:
                overall_level = "warning"
            else:
                overall_level = "critical"

            st = task_dict.get("start_time")
            et = task_dict.get("end_time")
            start_str = st.strftime("%Y-%m-%d %H:%M:%S") if isinstance(st, datetime) else (str(st) if st else "N/A")
            end_str = et.strftime("%Y-%m-%d %H:%M:%S") if isinstance(et, datetime) else (str(et) if et else "N/A")

            # 优先使用 Jinja2 渲染
            template_path = os.path.join(self.template_dir, "report.html")
            if self.env and os.path.exists(template_path):
                template = self.env.get_template("report.html")
                html_content = template.render(
                    task=task_dict,
                    start_time_str=start_str,
                    end_time_str=end_str,
                    results=normalized_results,
                    overall_score=overall_score,
                    overall_level=overall_level,
                    health_matrix=health_matrix,
                    total_devices=len(normalized_results),
                    healthy_count=healthy_count,
                    warning_count=warning_count,
                    critical_count=critical_count,
                    failed_count=failed_count,
                    all_issues=all_issues,
                    generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            else:
                # 降级：原生字符串渲染，保证无 Jinja2 依赖依然正常产出漂亮 HTML
                html_content = self._render_fallback_html(
                    task_dict, start_str, end_str, normalized_results,
                    overall_score, overall_level, health_matrix,
                    healthy_count, warning_count, critical_count, failed_count, all_issues
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_name = str(task_dict.get("name") or "inspection").replace(" ", "_")
            filename = f"report_{task_name}_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"巡检报告已生成: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"生成巡检报告时出错: {e}")
            raise

    def _render_fallback_html(
        self, task, start_str, end_str, results,
        overall_score, overall_level, matrix,
        healthy_count, warning_count, critical_count, failed_count, all_issues
    ) -> str:
        """无 Jinja2 时的标准原生 HTML 模版生成"""
        score_level_txt = self._get_score_level(overall_score)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 异常列表
        issues_html = ""
        if all_issues:
            items = []
            for i in all_issues:
                items.append(
                    f"<div style='background:#fef2f2;border-left:4px solid #ef4444;padding:10px 14px;margin-bottom:8px;border-radius:6px;display:flex;justify-content:space-between;'>"
                    f"<div><strong>{html.escape(str(i['device']))}</strong>: {html.escape(str(i['issue']))}</div>"
                    f"<span style='color:#ef4444;font-weight:600;'>{i['health_level'].upper()}</span>"
                    f"</div>"
                )
            issues_html = f"<div style='background:white;padding:20px;border-radius:12px;margin-bottom:20px;border:1px solid #e2e8f0;'><h3>⚠️ 重点关注异常 ({len(all_issues)})</h3><div style='margin-top:12px;'>{''.join(items)}</div></div>"

        # 矩阵行
        matrix_rows = []
        for m in matrix:
            sc = m['health_score']
            color = self._get_status_color(sc)
            cpu = f"{m.get('cpu_usage'):.1f}%" if m.get('cpu_usage') is not None else "N/A"
            mem = f"{m.get('memory_usage'):.1f}%" if m.get('memory_usage') is not None else "N/A"
            temp = f"{m.get('temperature')} ℃" if m.get('temperature') is not None else "N/A"
            fan = "正常" if m.get('fan_score', 0) >= 80 else "异常"
            pwr = "正常" if m.get('power_score', 0) >= 80 else "异常"
            ntp = "已同步" if m.get('ntp_score', 0) >= 80 else "未同步"
            matrix_rows.append(
                f"<tr>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'><strong>{html.escape(m['device_name'])}</strong></td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'><code>{html.escape(m['device_host'])}</code></td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'><span style='background:#e0e7ff;color:#3730a3;padding:2px 8px;border-radius:4px;font-size:12px;'>{m['category']}</span></td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;font-weight:bold;color:{color};'>{sc} 分</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{cpu}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{mem}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{temp}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{fan}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{pwr}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #e2e8f0;'>{ntp}</td>"
                f"</tr>"
            )

        # 设备详情卡片
        dev_cards = []
        for r in results:
            sc = r.get('health_score') or 0
            color = self._get_status_color(sc)
            issues_str = "; ".join(r.get('issues', []))
            issue_badge = f"<div style='margin-top:8px;font-size:12px;color:#ef4444;background:#fef2f2;padding:6px;border-radius:4px;'>⚠️ {html.escape(issues_str)}</div>" if issues_str else ""
            dev_cards.append(
                f"<div style='border:1px solid #e2e8f0;border-radius:10px;padding:16px;background:white;'>"
                f"<div style='display:flex;justify-content:space-between;border-bottom:1px solid #f1f5f9;padding-bottom:8px;margin-bottom:8px;'>"
                f"<div><strong>{html.escape(r.get('device_name', ''))}</strong><div style='font-size:12px;color:#64748b;'>{html.escape(r.get('device_host', ''))} · {r.get('category', '').upper()}</div></div>"
                f"<div style='font-size:16px;font-weight:bold;color:{color};'>{sc} 分</div>"
                f"</div>"
                f"<div style='font-size:13px;line-height:1.8;'>"
                f"<div>CPU / 内存: <b>{self._format_percent(r.get('cpu_usage'))}</b> / <b>{self._format_percent(r.get('memory_usage'))}</b></div>"
                f"<div>温度: <b>{self._format_value(r.get('temperature'))} ℃</b></div>"
                f"<div>风扇 / 电源: <b>{r.get('fan_status') or '正常'}</b> / <b>{r.get('power_status') or '正常'}</b></div>"
                f"<div>运行时间: <span style='font-size:11px;color:#64748b;'>{r.get('uptime') or 'N/A'}</span></div>"
                f"</div>"
                f"{issue_badge}"
                f"</div>"
            )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>华为数通设备健康巡检报告 - {html.escape(str(task.get('name')))}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 28px; border-radius: 14px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
.stat-box {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.stat-item {{ background: white; padding: 18px; border-radius: 10px; border: 1px solid #e2e8f0; }}
.stat-val {{ font-size: 26px; font-weight: bold; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ background: #f1f5f9; text-align: left; padding: 10px; }}
.cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h2 style="margin:0 0 8px 0;">华为数通设备健康巡检报告</h2>
      <div style="font-size:13px;color:#94a3b8;">任务: {html.escape(str(task.get('name')))} | 巡检周期: {start_str} ~ {end_str}</div>
    </div>
    <div style="text-align:right;background:rgba(255,255,255,0.1);padding:12px 20px;border-radius:10px;">
      <div style="font-size:12px;color:#cbd5e1;">全网健康总评分</div>
      <div style="font-size:36px;font-weight:bold;color:{self._get_status_color(overall_score)};">{overall_score} <span style="font-size:16px;">分</span></div>
    </div>
  </div>

  <div class="stat-box">
    <div class="stat-item"><div>设备总数</div><div class="stat-val">{len(results)} 台</div></div>
    <div class="stat-item"><div>状态正常</div><div class="stat-val" style="color:#10b981;">{healthy_count} 台</div></div>
    <div class="stat-item"><div>轻微关注</div><div class="stat-val" style="color:#f59e0b;">{warning_count} 台</div></div>
    <div class="stat-item"><div>严重风险</div><div class="stat-val" style="color:#ef4444;">{critical_count + failed_count} 台</div></div>
  </div>

  {issues_html}

  <div style="background:white;padding:24px;border-radius:12px;margin-bottom:20px;border:1px solid #e2e8f0;">
    <h3 style="margin-bottom:16px;">📊 全网设备健康矩阵</h3>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>设备名称</th><th>IP地址</th><th>分类</th><th>评分</th><th>CPU</th><th>内存</th><th>温度</th><th>风扇</th><th>电源</th><th>NTP</th>
          </tr>
        </thead>
        <tbody>
          {''.join(matrix_rows)}
        </tbody>
      </table>
    </div>
  </div>

  <div style="background:white;padding:24px;border-radius:12px;border:1px solid #e2e8f0;">
    <h3 style="margin-bottom:16px;">🔍 设备巡检明细卡片</h3>
    <div class="cards-grid">
      {''.join(dev_cards)}
    </div>
  </div>

  <div style="text-align:center;margin-top:24px;color:#94a3b8;font-size:12px;">
    由 华为数通巡检系统 自动生成 · {now_str}
  </div>
</div>
</body>
</html>
"""

    def _generate_health_matrix(self, results: list[dict]) -> list[dict]:
        matrix = []
        for r in results:
            metric_scores = r.get("metric_scores") or {}
            entry = {
                "device_name": r.get("device_name", "未知"),
                "device_host": r.get("device_host", ""),
                "category": r.get("category", ""),
                "health_score": r.get("health_score", 0),
                "health_level": r.get("health_level", "critical"),
                "cpu_score": metric_scores.get("cpu", min(100, max(0, 100 - int(r.get("cpu_usage") or 0)))),
                "memory_score": metric_scores.get("memory", min(100, max(0, 100 - int(r.get("memory_usage") or 0)))),
                "temperature_score": metric_scores.get("temperature", 90 if (r.get("temperature") or 40) < 60 else 50),
                "fan_score": metric_scores.get("fan", 100 if "abnormal" not in str(r.get("fan_status", "")).lower() else 30),
                "power_score": metric_scores.get("power", 100 if "abnormal" not in str(r.get("power_status", "")).lower() else 30),
                "interface_score": metric_scores.get("interfaces", 95),
                "alarm_score": metric_scores.get("alarms", 100 if not r.get("alarm_summary") else 80),
                "ntp_score": metric_scores.get("ntp", 100 if "sync" in str(r.get("ntp_status", "")).lower() else 50),
                "cpu_usage": r.get("cpu_usage"),
                "memory_usage": r.get("memory_usage"),
                "temperature": r.get("temperature"),
            }
            matrix.append(entry)

        matrix.sort(key=lambda x: x.get("health_score", 0))
        return matrix

    @staticmethod
    def _get_status_color(score: float) -> str:
        if score is None:
            return "#9e9e9e"
        if score >= 80:
            return "#10b981"
        elif score >= 60:
            return "#f59e0b"
        else:
            return "#ef4444"

    @staticmethod
    def _get_score_level(score: float) -> str:
        if score is None:
            return "未知"
        if score >= 80:
            return "健康"
        elif score >= 60:
            return "告警"
        else:
            return "严重"

    @staticmethod
    def _format_percent(value: Optional[float]) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f}%"

    @staticmethod
    def _format_value(value, default: str = "N/A") -> str:
        if value is None:
            return default
        return str(value)

    def _calculate_overall_score(self, results: list[dict]) -> float:
        valid_scores = [
            r.get("health_score", 0)
            for r in results
            if r.get("status") != "failed" and r.get("health_score") is not None
        ]
        if not valid_scores:
            return 0.0
        return round(sum(valid_scores) / len(valid_scores), 1)
