"""
设备管理路由模块

提供设备的增删改查、连通性测试和统计信息等API接口。
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
)
from app.services.collector import DeviceCollector

router = APIRouter(prefix="/devices", tags=["设备管理"])


@router.get("", response_model=list[DeviceResponse], summary="获取设备列表")
async def list_devices(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有设备列表。

    - **category**: 可选，按设备类别过滤（switch/router/firewall）
    """
    query = select(Device)
    if category:
        query = query.where(Device.category == category)
    query = query.order_by(Device.created_at.desc())
    result = await db.execute(query)
    devices = result.scalars().all()
    return devices


@router.get("/stats", summary="获取设备统计信息")
async def get_device_stats(db: AsyncSession = Depends(get_db)):
    """
    获取设备统计数据，包括总数、各类别数量、已启用数量。
    """
    # 总数
    total_result = await db.execute(select(func.count(Device.id)))
    total = total_result.scalar() or 0

    # 已启用数量
    enabled_result = await db.execute(
        select(func.count(Device.id)).where(Device.enabled == True)  # noqa: E712
    )
    enabled = enabled_result.scalar() or 0

    # 按类别统计
    category_result = await db.execute(
        select(Device.category, func.count(Device.id)).group_by(Device.category)
    )
    by_category = {row[0]: row[1] for row in category_result.all()}

    return {
        "total": total,
        "enabled": enabled,
        "by_category": {
            "switch": by_category.get("switch", 0),
            "router": by_category.get("router", 0),
            "firewall": by_category.get("firewall", 0),
        },
    }


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加设备",
)
async def create_device(
    device_in: DeviceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    新增一台网络设备。

    必填字段：name, host, username, password, category
    """
    # 检查主机地址是否已存在
    existing = await db.execute(
        select(Device).where(Device.host == device_in.host)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"设备主机地址 {device_in.host} 已存在",
        )

    device = Device(**device_in.model_dump())
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceResponse, summary="获取设备详情")
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    根据设备ID获取设备详细信息。
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 ID={device_id} 不存在",
        )
    return device


@router.put("/{device_id}", response_model=DeviceResponse, summary="更新设备")
async def update_device(
    device_id: int,
    device_in: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新指定设备的信息，仅更新提供的字段。
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 ID={device_id} 不存在",
        )

    update_data = device_in.model_dump(exclude_unset=True)
    # 如果更新了主机地址，检查是否与其他设备冲突
    if "host" in update_data and update_data["host"] != device.host:
        existing = await db.execute(
            select(Device).where(
                Device.host == update_data["host"],
                Device.id != device_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"设备主机地址 {update_data['host']} 已被其他设备使用",
            )

    for field, value in update_data.items():
        setattr(device, field, value)

    await db.commit()
    await db.refresh(device)
    return device


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除设备",
)
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除指定设备。删除后不可恢复。
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 ID={device_id} 不存在",
        )

    await db.delete(device)
    await db.commit()


@router.post("/{device_id}/test", summary="测试设备连通性")
async def test_device_connection(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    测试与指定设备的SSH连通性。

    尝试通过SSH连接设备，返回连接成功或失败的结果。
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备 ID={device_id} 不存在",
        )

    collector = DeviceCollector(
        host=device.host,
        port=device.port,
        username=device.username,
        password=device.password,
        device_type=device.device_type,
    )

    try:
        # 在线程池中运行阻塞的SSH连接测试
        success = await asyncio.to_thread(collector.test_connection)
        if success:
            return {
                "success": True,
                "message": f"设备 {device.name}({device.host}) 连接成功",
            }
        else:
            return {
                "success": False,
                "message": f"设备 {device.name}({device.host}) 连接失败",
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"设备 {device.name}({device.host}) 连接异常: {str(e)}",
        }


@router.post("/init-samples", summary="一键初始化演示环境华为数通设备")
async def init_sample_devices(db: AsyncSession = Depends(get_db)):
    """
    一键注入 3 台典型华为数通仿真设备（交换机、路由器、防火墙），
    便于在没有真实设备的演示测试环境下直接体验全流程巡检。
    """
    samples = [
        {
            "name": "HW-Core-Switch-S6730",
            "host": "192.168.10.1",
            "port": 22,
            "username": "admin",
            "password": "Huawei@123",
            "device_type": "huawei_vrp",
            "category": "switch",
            "location": "数据中心 A 机房 01 机柜",
            "enabled": True,
        },
        {
            "name": "HW-Edge-Router-NE40E",
            "host": "192.168.20.1",
            "port": 22,
            "username": "admin",
            "password": "Huawei@123",
            "device_type": "huawei_vrp",
            "category": "router",
            "location": "广域网出口机房 02 机柜",
            "enabled": True,
        },
        {
            "name": "HW-Sec-Firewall-USG6650",
            "host": "192.168.30.1",
            "port": 22,
            "username": "admin",
            "password": "Huawei@123",
            "device_type": "huawei_vrp",
            "category": "firewall",
            "location": "DMZ 边界安全机柜",
            "enabled": True,
        },
    ]

    added = 0
    for s in samples:
        exist = await db.execute(select(Device).where(Device.host == s["host"]))
        if not exist.scalar_one_or_none():
            device = Device(**s)
            db.add(device)
            added += 1

    await db.commit()
    return {"message": f"成功添加 {added} 台华为演示数通设备", "added_count": added}

