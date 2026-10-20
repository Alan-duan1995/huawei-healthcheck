"""
华为数通设备健康巡检系统 — FastAPI 应用入口
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import config, init_db
from app.routers import devices, tasks, reports


# ---------------------------------------------------------------------------
# 应用生命周期事件
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用启动 / 关闭时执行的操作"""
    # ---- 启动 ----
    # 初始化数据库（创建表）
    await init_db()

    # 确保报告输出目录存在
    report_dir = Path(config.get("report", {}).get("output_dir", "./reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    yield

    # ---- 关闭 ----
    # 如有需要，可在此释放资源


# ---------------------------------------------------------------------------
# 创建 FastAPI 应用
# ---------------------------------------------------------------------------

app = FastAPI(
    title="华为数通设备健康巡检系统",
    description="自动化采集华为交换机、路由器、防火墙的运行状态并生成健康巡检报告",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS 中间件
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------

app.include_router(devices.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# ---------------------------------------------------------------------------
# 静态文件（前端构建产物）
# ---------------------------------------------------------------------------

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


# ---------------------------------------------------------------------------
# 根路由
# ---------------------------------------------------------------------------

@app.get("/api")
async def root() -> dict[str, str]:
    """API 根路径，用于健康检查"""
    return {"message": "华为数通设备健康巡检系统 API"}
