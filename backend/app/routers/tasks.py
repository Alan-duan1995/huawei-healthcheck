"""
巡检任务路由模块

提供巡检任务的创建、执行、进度查询和管理等API接口。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.models import (
    Device,
    InspectionTask,
    InspectionResult,
    TaskResponse,
    InspectionResultResponse,
)
from app.services.collector import DeviceCollector
from app.services.analyzer import HealthAnalyzer
from app.services.reporter import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["巡检任务"])


class TaskCreate(BaseModel):
    """创建巡检任务的请求体"""

    name: Optional[str] = Field(None, description="任务名称，不填则自动生成")
    device_ids: Optional[list[int]] = Field(
        None, description="指定巡检的设备ID列表，不填则巡检所有已启用设备"
    )


async def _run_inspection(task_id: int, device_ids: list[int]):
    """
    后台执行巡检任务。

    遍历所有目标设备，依次执行数据采集、健康分析，并更新巡检结果。
    所有设备完成后生成巡检报告。
    """
    async with async_session_factory() as db:
        try:
            # 获取任务记录
            result = await db.execute(
                select(InspectionTask).where(InspectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"巡检任务 ID={task_id} 不存在")
                return

            task.status = "running"
            task.start_time = datetime.now()
            await db.commit()

            # 获取所有目标设备
            devices_result = await db.execute(
                select(Device).where(Device.id.in_(device_ids))
            )
            devices = devices_result.scalars().all()

            analyzer = HealthAnalyzer()
            inspection_results = []

            for device in devices:
                # 为每台设备创建巡检结果记录
                insp_result = InspectionResult(
                    task_id=task_id,
                    device_id=device.id,
                    device_name=device.name,
                    device_host=device.host,
                    category=device.category,
                    status="running",
                    collected_at=datetime.now(),
                )
                db.add(insp_result)
                await db.commit()
                await db.refresh(insp_result)

                try:
                    # 数据采集
                    collector = DeviceCollector(
                        host=device.host,
                        port=device.port,
                        username=device.username,
                        password=device.password,
                        device_type=device.device_type,
                        category=device.category,
                        name=device.name,
                    )
                    collect_res = await collector.collect()
                    if not collect_res.get("success"):
                        insp_result.status = "failed"
                        insp_result.error_message = collect_res.get("error") or "采集失败"
                        logger.warning(
                            f"设备 {device.name}({device.host}) 采集未成功: {insp_result.error_message}"
                        )
                    else:
                        outputs = collect_res.get("outputs", {})
                        # 健康分析
                        analysis = analyzer.analyze(outputs, device.category)
                        insp_result._analysis = analysis

                        # 更新巡检结果
                        insp_result.status = "completed"
                        insp_result.health_score = analysis.get("health_score", 0)
                        insp_result.cpu_usage = analysis.get("cpu_usage")
                        insp_result.memory_usage = analysis.get("memory_usage")
                        insp_result.temperature = analysis.get("temperature")
                        insp_result.fan_status = analysis.get("fan_status")
                        insp_result.power_status = analysis.get("power_status")
                        insp_result.uptime = analysis.get("uptime")
                        insp_result.ntp_status = analysis.get("ntp_status")
                        insp_result.interface_summary = (
                            json.dumps(analysis.get("interface_summary"), ensure_ascii=False)
                            if analysis.get("interface_summary")
                            else None
                        )
                        insp_result.alarm_summary = (
                            json.dumps(analysis.get("alarm_summary"), ensure_ascii=False)
                            if analysis.get("alarm_summary")
                            else None
                        )
                        insp_result.routing_info = (
                            json.dumps(analysis.get("routing_info"), ensure_ascii=False)
                            if analysis.get("routing_info")
                            else None
                        )
                        insp_result.firewall_info = (
                            json.dumps(analysis.get("firewall_info"), ensure_ascii=False)
                            if analysis.get("firewall_info")
                            else None
                        )
                        insp_result.raw_output = (
                            json.dumps(outputs, ensure_ascii=False)
                            if outputs
                            else None
                        )

                        logger.info(
                            f"设备 {device.name}({device.host}) 巡检完成，"
                            f"健康评分: {insp_result.health_score}"
                        )

                except Exception as e:
                    # 单台设备采集失败，不影响其他设备
                    insp_result.status = "failed"
                    insp_result.error_message = str(e)
                    logger.error(
                        f"设备 {device.name}({device.host}) 巡检失败: {e}"
                    )

                inspection_results.append(insp_result)

                # 更新任务进度
                task.completed_devices = (task.completed_devices or 0) + 1
                await db.commit()

            # 所有设备完成，生成报告
            try:
                reporter = ReportGenerator()
                report_path = await asyncio.to_thread(
                    reporter.generate, task, inspection_results
                )
                task.report_path = report_path
            except Exception as e:
                logger.error(f"巡检报告生成失败: {e}")

            task.status = "completed"
            task.end_time = datetime.now()
            await db.commit()

            logger.info(f"巡检任务 ID={task_id} 已完成")

        except Exception as e:
            logger.error(f"巡检任务 ID={task_id} 执行异常: {e}")
            try:
                result = await db.execute(
                    select(InspectionTask).where(InspectionTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.end_time = datetime.now()
                    await db.commit()
            except Exception:
                logger.error(f"更新任务 ID={task_id} 失败状态时出错")


@router.get("", response_model=list[TaskResponse], summary="获取巡检任务列表")
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取巡检任务列表，按创建时间倒序排列。

    - **skip**: 跳过记录数（分页偏移），默认0
    - **limit**: 返回记录数上限，默认20
    """
    query = (
        select(InspectionTask)
        .order_by(InspectionTask.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建并启动巡检任务",
)
async def create_task(
    task_in: TaskCreate = TaskCreate(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    创建一个新的巡检任务并在后台启动执行。

    - 可指定任务名称，不填则自动生成（格式：巡检任务-时间戳）
    - 可指定设备ID列表，不填则对所有已启用设备执行巡检
    - 接口立即返回任务信息，巡检在后台异步执行
    """
    # 确定任务名称
    task_name = task_in.name or f"巡检任务-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 确定目标设备
    if task_in.device_ids:
        # 校验指定的设备ID是否存在
        devices_result = await db.execute(
            select(Device).where(Device.id.in_(task_in.device_ids))
        )
        devices = devices_result.scalars().all()
        if not devices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定的设备不存在",
            )
        device_ids = [d.id for d in devices]
    else:
        # 获取所有已启用设备
        devices_result = await db.execute(
            select(Device).where(Device.enabled == True)  # noqa: E712
        )
        devices = devices_result.scalars().all()
        if not devices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有可用的已启用设备",
            )
        device_ids = [d.id for d in devices]

    # 创建任务记录
    task = InspectionTask(
        name=task_name,
        status="pending",
        total_devices=len(device_ids),
        completed_devices=0,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 在后台启动巡检
    background_tasks.add_task(_run_inspection, task.id, device_ids)

    return task


@router.get("/{task_id}", response_model=TaskResponse, summary="获取巡检任务详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定巡检任务的详细信息，包含所有设备的巡检结果。
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

    # 获取关联的巡检结果
    results_query = await db.execute(
        select(InspectionResult).where(InspectionResult.task_id == task_id)
    )
    inspection_results = results_query.scalars().all()

    # 构造响应，将结果附加到任务中
    task_dict = {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "total_devices": task.total_devices,
        "completed_devices": task.completed_devices,
        "start_time": task.start_time,
        "end_time": task.end_time,
        "report_path": task.report_path,
        "created_at": task.created_at,
        "results": inspection_results,
    }

    return task_dict


@router.get("/{task_id}/progress", summary="获取巡检任务进度")
async def get_task_progress(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定巡检任务的执行进度，用于前端轮询。

    返回任务状态、总设备数、已完成数和完成百分比。
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

    total = task.total_devices or 0
    completed = task.completed_devices or 0
    percentage = round((completed / total * 100), 1) if total > 0 else 0

    return {
        "task_id": task.id,
        "name": task.name,
        "status": task.status,
        "total_devices": total,
        "completed_devices": completed,
        "percentage": percentage,
        "start_time": task.start_time,
        "end_time": task.end_time,
    }


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除巡检任务",
)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除指定巡检任务及其所有关联的巡检结果。

    正在运行中的任务不可删除。
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

    if task.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="正在运行中的任务不可删除",
        )

    # 删除关联的巡检结果
    results_query = await db.execute(
        select(InspectionResult).where(InspectionResult.task_id == task_id)
    )
    results = results_query.scalars().all()
    for r in results:
        await db.delete(r)

    await db.delete(task)
    await db.commit()
