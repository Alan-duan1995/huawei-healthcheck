"""
数据库 ORM 模型定义
包含：Device / InspectionTask / InspectionResult
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ===========================================================================
# Device — 设备信息表
# ===========================================================================

class Device(Base):
    """网络设备信息"""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="设备名称")
    host: Mapped[str] = mapped_column(String(64), nullable=False, comment="IP地址")
    port: Mapped[int] = mapped_column(Integer, default=22, comment="SSH端口")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="登录用户名")
    password: Mapped[str] = mapped_column(String(256), nullable=False, comment="登录密码（实际项目应加密存储）")
    device_type: Mapped[str] = mapped_column(
        String(32), default="huawei_vrp",
        comment="设备类型: huawei_vrp, huawei_vrpv8, huawei",
    )
    category: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="设备分类: switch, router, firewall",
    )
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="设备位置")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间",
    )

    # 关系
    inspection_results: Mapped[list["InspectionResult"]] = relationship(
        back_populates="device", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name='{self.name}', host='{self.host}')>"


# ===========================================================================
# InspectionTask — 巡检任务表
# ===========================================================================

class InspectionTask(Base):
    """巡检任务"""
    __tablename__ = "inspection_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="任务名称")
    status: Mapped[str] = mapped_column(
        String(32), default="pending",
        comment="任务状态: pending, running, completed, failed",
    )
    total_devices: Mapped[int] = mapped_column(Integer, default=0, comment="总设备数")
    completed_devices: Mapped[int] = mapped_column(Integer, default=0, comment="已完成设备数")
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="结束时间")
    report_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="报告文件路径",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间",
    )

    # 关系
    results: Mapped[list["InspectionResult"]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<InspectionTask(id={self.id}, name='{self.name}', status='{self.status}')>"


# ===========================================================================
# InspectionResult — 巡检结果表
# ===========================================================================

class InspectionResult(Base):
    """单台设备的巡检结果"""
    __tablename__ = "inspection_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspection_tasks.id"), nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=False,
    )
    device_name: Mapped[str] = mapped_column(String(128), comment="设备名称（冗余快照）")
    device_host: Mapped[str] = mapped_column(String(64), comment="IP地址（冗余快照）")
    category: Mapped[str] = mapped_column(String(32), comment="设备分类")
    status: Mapped[str] = mapped_column(
        String(32), default="pending",
        comment="采集状态: pending, success, failed, unreachable",
    )
    health_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="健康评分 0-100",
    )

    # ---- 健康指标字段 ----
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="CPU使用率")
    memory_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="内存使用率")
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="温度(℃)")
    fan_status: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="风扇状态")
    power_status: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="电源状态")
    uptime: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="运行时长")
    interface_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="接口摘要 JSON")
    alarm_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="告警摘要 JSON")
    ntp_status: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="NTP同步状态")
    routing_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="路由信息 JSON（路由器）")
    firewall_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="防火墙信息 JSON（防火墙）")
    raw_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="原始命令输出 JSON")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    collected_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="采集时间",
    )

    # 关系
    task: Mapped["InspectionTask"] = relationship(back_populates="results")
    device: Mapped["Device"] = relationship(back_populates="inspection_results")

    def __repr__(self) -> str:
        return (
            f"<InspectionResult(id={self.id}, device='{self.device_name}', "
            f"status='{self.status}', score={self.health_score})>"
        )
