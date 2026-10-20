"""
Pydantic 数据模式（请求 / 响应）
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# Device 相关
# ===========================================================================

class DeviceCreate(BaseModel):
    """创建设备请求体"""
    name: str = Field(..., min_length=1, max_length=128, description="设备名称")
    host: str = Field(..., min_length=1, max_length=64, description="IP地址")
    port: int = Field(default=22, ge=1, le=65535, description="SSH端口")
    username: str = Field(..., min_length=1, max_length=64, description="登录用户名")
    password: str = Field(..., min_length=1, max_length=256, description="登录密码")
    device_type: str = Field(default="huawei_vrp", description="设备类型")
    category: str = Field(..., description="设备分类: switch, router, firewall")
    location: Optional[str] = Field(default=None, max_length=256, description="设备位置")
    enabled: bool = Field(default=True, description="是否启用")


class DeviceUpdate(BaseModel):
    """更新设备请求体（所有字段可选）"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128, description="设备名称")
    host: Optional[str] = Field(default=None, min_length=1, max_length=64, description="IP地址")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="SSH端口")
    username: Optional[str] = Field(default=None, min_length=1, max_length=64, description="登录用户名")
    password: Optional[str] = Field(default=None, min_length=1, max_length=256, description="登录密码")
    device_type: Optional[str] = Field(default=None, description="设备类型")
    category: Optional[str] = Field(default=None, description="设备分类")
    location: Optional[str] = Field(default=None, max_length=256, description="设备位置")
    enabled: Optional[bool] = Field(default=None, description="是否启用")


class DeviceResponse(BaseModel):
    """设备响应体"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    port: int
    username: str
    device_type: str
    category: str
    location: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# InspectionTask 相关
# ===========================================================================

class TaskResponse(BaseModel):
    """巡检任务响应体（列表用）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    total_devices: int
    completed_devices: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    report_path: Optional[str] = None
    created_at: datetime


class TaskDetailResponse(TaskResponse):
    """巡检任务详情响应体（含结果列表）"""
    results: list["InspectionResultResponse"] = []


# ===========================================================================
# InspectionResult 相关
# ===========================================================================

class InspectionResultResponse(BaseModel):
    """巡检结果响应体"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    device_id: int
    device_name: str
    device_host: str
    category: str
    status: str
    health_score: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    temperature: Optional[float] = None
    fan_status: Optional[str] = None
    power_status: Optional[str] = None
    uptime: Optional[str] = None
    interface_summary: Optional[str] = None
    alarm_summary: Optional[str] = None
    ntp_status: Optional[str] = None
    routing_info: Optional[str] = None
    firewall_info: Optional[str] = None
    error_message: Optional[str] = None
    collected_at: datetime


# ===========================================================================
# 健康矩阵（聚合视图用）
# ===========================================================================

class HealthMatrixResponse(BaseModel):
    """健康矩阵响应 —— 用于设备概览"""
    device_name: str = Field(..., description="设备名称")
    category: str = Field(..., description="设备分类")
    metrics: dict[str, Any] = Field(default_factory=dict, description="指标键值对")


# 解决 TaskDetailResponse 中前向引用
TaskDetailResponse.model_rebuild()
