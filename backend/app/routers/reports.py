"""
巡检报告路由模块

提供巡检报告查看、下载、健康矩阵数据和仪表盘汇总等API接口。
"""

import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    Device,
    InspectionTask,
    InspectionResult,
    TaskResponse,
    InspectionResultResponse,
    HealthMatrixItem,
)

router = APIRouter(prefix="/reports", tags=["巡检报告"])


@router.get("/dashboard", summary="获取仪表盘汇总数据")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    获取仪表盘首页汇总数据，包含：

    - 设备总数、任务总数
    - 最近一次巡检任务信息
    - 整体健康评分
    - 设备健康状态分布（健康/告警/严重）
    - 近期问题列表
    - 健康评分趋势
    """
    # 设备总数
    device_count_result = await db.execute(select(func.count(Device.id)))
    total_devices = device_count_result.scalar() or 0

    # 任务总数
    task_count_result = await db.execute(select(func.count(InspectionTask.id)))
    total_tasks = task_count_result.scalar() or 0

    # 最近一次已完成的巡检任务
    latest_task_result = await db.execute(
        select(InspectionTask)
        .where(InspectionTask.status == "completed")
        .order_by(InspectionTask.created_at.desc())
        .limit(1)
    )
    latest_task = latest_task_result.scalar_one_or_none()

    overall_health_score = 0
    device_health_distribution = {"healthy": 0, "warning": 0, "critical": 0}
    recent_issues = []
    latest_task_info = None

    if latest_task:
        latest_task_info = {
            "id": latest_task.id,
            "name": latest_task.name,
            "status": latest_task.status,
            "total_devices": latest_task.total_devices,
            "completed_devices": latest_task.completed_devices,
            "start_time": latest_task.start_time,
            "end_time": latest_task.end_time,
        }

        # 获取最近任务的所有巡检结果
        results_query = await db.execute(
            select(InspectionResult).where(
                InspectionResult.task_id == latest_task.id
            )
        )
        results = results_query.scalars().all()

        if results:
            # 计算整体健康评分（所有设备的平均分）
            scores = [
                r.health_score for r in results if r.health_score is not None
            ]
            if scores:
                overall_health_score = round(sum(scores) / len(scores), 1)

            # 设备健康状态分布
            for r in results:
                score = r.health_score or 0
                if score >= 80:
                    device_health_distribution["healthy"] += 1
                elif score >= 60:
                    device_health_distribution["warning"] += 1
                else:
                    device_health_distribution["critical"] += 1

            # 近期问题（从告警摘要和失败结果中提取）
            for r in results:
                if r.status == "failed":
                    recent_issues.append({
                        "device_name": r.device_name,
                        "device_host": r.device_host,
                        "issue": f"巡检失败: {r.error_message or '未知错误'}",
                        "severity": "critical",
                        "level": "critical",
                    })
                elif r.health_score is not None and r.health_score < 60:
                    issues_detail = []
                    if r.cpu_usage is not None and r.cpu_usage > 80:
                        issues_detail.append(f"CPU使用率过高: {r.cpu_usage}%")
                    if r.memory_usage is not None and r.memory_usage > 80:
                        issues_detail.append(f"内存使用率过高: {r.memory_usage}%")
                    if r.temperature is not None and r.temperature > 65:
                        issues_detail.append(f"温度过高: {r.temperature}°C")
                    if r.alarm_summary:
                        try:
                            alarms = json.loads(r.alarm_summary)
                            if isinstance(alarms, list):
                                for alarm in alarms[:3]:
                                    issues_detail.append(
                                        alarm.get("description", str(alarm))
                                    )
                            elif isinstance(alarms, dict):
                                alarm_count = alarms.get("total", 0)
                                if alarm_count > 0:
                                    issues_detail.append(
                                        f"存在 {alarm_count} 条告警"
                                    )
                        except (json.JSONDecodeError, TypeError):
                            pass

                    issue_text = "; ".join(issues_detail) if issues_detail else "健康评分低"
                    sev = "critical" if r.health_score < 40 else "warning"
                    recent_issues.append({
                        "device_name": r.device_name,
                        "device_host": r.device_host,
                        "issue": issue_text,
                        "severity": sev,
                        "level": sev,
                    })

            # 限制最多返回10条问题
            recent_issues = recent_issues[:10]

    # 健康评分趋势（最近10次已完成任务的评分）
    trend_result = await db.execute(
        select(InspectionTask)
        .where(InspectionTask.status == "completed")
        .order_by(InspectionTask.created_at.desc())
        .limit(10)
    )
    trend_tasks = trend_result.scalars().all()
    health_trend = []

    for t in reversed(trend_tasks):
        # 获取每个任务的平均健康评分
        scores_result = await db.execute(
            select(func.avg(InspectionResult.health_score)).where(
                InspectionResult.task_id == t.id,
                InspectionResult.health_score.isnot(None),
            )
        )
        avg_score = scores_result.scalar()
        health_trend.append({
            "task_name": t.name,
            "score": round(avg_score, 1) if avg_score else 0,
            "date": t.end_time.isoformat() if t.end_time else t.created_at.isoformat(),
        })

    return {
        "total_devices": total_devices,
        "total_tasks": total_tasks,
        "latest_task": latest_task_info,
        "overall_health_score": overall_health_score,
        "device_health_distribution": device_health_distribution,
        "recent_issues": recent_issues,
        "health_trend": health_trend,
    }


@router.get("", summary="获取巡检报告列表")
async def list_reports(db: AsyncSession = Depends(get_db)):
    """
    获取所有已完成且生成了报告的巡检任务列表。
    """
    query = (
        select(InspectionTask)
        .where(
            InspectionTask.status == "completed",
            InspectionTask.report_path.isnot(None),
        )
        .order_by(InspectionTask.created_at.desc())
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    reports = []
    for task in tasks:
        reports.append({
            "task_id": task.id,
            "task_name": task.name,
            "total_devices": task.total_devices,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "report_path": task.report_path,
            "created_at": task.created_at,
        })

    return reports


@router.get("/{task_id}", summary="获取巡检报告详情")
async def get_report(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定任务的完整巡检报告，包含任务信息、所有设备结果和健康矩阵数据。
    """
    result = await db.execute(
        select(InspectionTask).where(InspectionTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"巡检任务 ID={task_id} 不存在",
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"巡检任务尚未完成，当前状态: {task.status}",
        )

    # 获取巡检结果
    results_query = await db.execute(
        select(InspectionResult).where(InspectionResult.task_id == task_id)
    )
    inspection_results = results_query.scalars().all()

    # 构建健康矩阵数据
    matrix_items = _build_health_matrix(inspection_results)

    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "total_devices": task.total_devices,
            "completed_devices": task.completed_devices,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "report_path": task.report_path,
            "created_at": task.created_at,
        },
        "results": [
            {
                "id": r.id,
                "device_name": r.device_name,
                "device_host": r.device_host,
                "category": r.category,
                "status": r.status,
                "health_score": r.health_score,
                "cpu_usage": r.cpu_usage,
                "memory_usage": r.memory_usage,
                "temperature": r.temperature,
                "fan_status": r.fan_status,
                "power_status": r.power_status,
                "uptime": r.uptime,
                "ntp_status": r.ntp_status,
                "interface_summary": (
                    json.loads(r.interface_summary)
                    if r.interface_summary
                    else None
                ),
                "alarm_summary": (
                    json.loads(r.alarm_summary) if r.alarm_summary else None
                ),
                "error_message": r.error_message,
                "collected_at": r.collected_at,
            }
            for r in inspection_results
        ],
        "health_matrix": matrix_items,
    }


@router.get("/{task_id}/download", summary="下载巡检报告")
async def download_report(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    下载指定任务的HTML格式巡检报告文件。
    """
    result = await db.execute(
        select(InspectionTask).where(InspectionTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"巡检任务 ID={task_id} 不存在",
        )

    if not task.report_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该任务尚未生成报告文件",
        )

    if not os.path.exists(task.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告文件不存在，可能已被删除",
        )

    filename = f"巡检报告_{task.name}.html"
    return FileResponse(
        path=task.report_path,
        filename=filename,
        media_type="text/html",
    )


@router.get("/{task_id}/preview", summary="在线预览巡检报告")
async def preview_report(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    在线预览 HTML 格式巡检报告（通过 iframe 内联展示，不触发下载附件）。
    """
    result = await db.execute(
        select(InspectionTask).where(InspectionTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"巡检任务 ID={task_id} 不存在",
        )

    if not task.report_path or not os.path.exists(task.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告文件不存在",
        )

    with open(task.report_path, "r", encoding="utf-8") as f:
        html_str = f.read()

    return HTMLResponse(content=html_str)


@router.get("/{task_id}/matrix", summary="获取健康矩阵数据")
async def get_health_matrix(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定任务的健康矩阵数据，用于前端ECharts热力图等可视化展示。

    返回每台设备的各项指标评分（0-100），包括CPU、内存、温度、风扇、
    电源、接口、告警、NTP等维度。
    """
    result = await db.execute(
        select(InspectionTask).where(InspectionTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"巡检任务 ID={task_id} 不存在",
        )

    results_query = await db.execute(
        select(InspectionResult).where(InspectionResult.task_id == task_id)
    )
    inspection_results = results_query.scalars().all()

    return _build_health_matrix(inspection_results)


def _build_health_matrix(results: list) -> list[dict]:
    """
    根据巡检结果构建健康矩阵数据。

    将各设备的原始指标转换为0-100的评分值，用于前端可视化展示。
    """
    matrix_items = []

    for r in results:
        if r.status != "completed":
            continue

        metrics = {}

        # CPU评分：使用率越低评分越高
        if r.cpu_usage is not None:
            metrics["cpu"] = max(0, round(100 - r.cpu_usage))
        else:
            metrics["cpu"] = None

        # 内存评分：使用率越低评分越高
        if r.memory_usage is not None:
            metrics["memory"] = max(0, round(100 - r.memory_usage))
        else:
            metrics["memory"] = None

        # 温度评分：温度越低评分越高（以70°C为满分基准）
        if r.temperature is not None:
            temp_score = max(0, min(100, round((70 - r.temperature) / 70 * 100 + 30)))
            metrics["temperature"] = temp_score
        else:
            metrics["temperature"] = None

        # 风扇状态评分
        if r.fan_status:
            fan_lower = r.fan_status.lower()
            if fan_lower in ("normal", "ok", "正常"):
                metrics["fan"] = 100
            elif fan_lower in ("warning", "告警"):
                metrics["fan"] = 60
            else:
                metrics["fan"] = 20
        else:
            metrics["fan"] = None

        # 电源状态评分
        if r.power_status:
            power_lower = r.power_status.lower()
            if power_lower in ("normal", "ok", "正常"):
                metrics["power"] = 100
            elif power_lower in ("warning", "告警"):
                metrics["power"] = 60
            else:
                metrics["power"] = 20
        else:
            metrics["power"] = None

        # 接口评分：基于接口状态摘要
        if r.interface_summary:
            try:
                iface_data = json.loads(r.interface_summary)
                total_ifaces = iface_data.get("total", 0)
                up_ifaces = iface_data.get("up", 0)
                if total_ifaces > 0:
                    metrics["interface"] = round(up_ifaces / total_ifaces * 100)
                else:
                    metrics["interface"] = 100
            except (json.JSONDecodeError, TypeError):
                metrics["interface"] = None
        else:
            metrics["interface"] = None

        # 告警评分：无告警为满分，告警越多评分越低
        if r.alarm_summary:
            try:
                alarm_data = json.loads(r.alarm_summary)
                if isinstance(alarm_data, list):
                    alarm_count = len(alarm_data)
                elif isinstance(alarm_data, dict):
                    alarm_count = alarm_data.get("total", 0)
                else:
                    alarm_count = 0
                # 每条告警扣10分，最低0分
                metrics["alarm"] = max(0, 100 - alarm_count * 10)
            except (json.JSONDecodeError, TypeError):
                metrics["alarm"] = None
        else:
            metrics["alarm"] = 100  # 无告警则满分

        # NTP评分
        if r.ntp_status:
            ntp_lower = r.ntp_status.lower()
            if ntp_lower in ("synchronized", "synced", "ok", "正常", "已同步"):
                metrics["ntp"] = 100
            elif ntp_lower in ("unsynchronized", "unsynced", "未同步"):
                metrics["ntp"] = 30
            else:
                metrics["ntp"] = 50
        else:
            metrics["ntp"] = None

        matrix_items.append({
            "device_name": r.device_name,
            "category": r.category,
            "metrics": metrics,
            "health_score": r.health_score,
        })

    return matrix_items
