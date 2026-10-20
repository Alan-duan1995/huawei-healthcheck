"""
数据库配置模块
使用 SQLAlchemy 异步引擎 + aiosqlite 驱动
"""

import os
from pathlib import Path
from typing import AsyncGenerator

import yaml
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# 加载配置文件
# ---------------------------------------------------------------------------

_config_path = Path(__file__).resolve().parent.parent / "config.yaml"

with open(_config_path, "r", encoding="utf-8") as _f:
    config: dict = yaml.safe_load(_f)

# ---------------------------------------------------------------------------
# 数据库 URL（从 config.yaml 读取）
# ---------------------------------------------------------------------------

SQLALCHEMY_DATABASE_URL: str = config["database"]["url"]

# 确保 data 目录存在（SQLite 文件所在目录）
_db_file = SQLALCHEMY_DATABASE_URL.split("///")[-1]
if _db_file:
    Path(_db_file).parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 异步引擎 & Session 工厂
# ---------------------------------------------------------------------------

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# 声明式基类
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """所有模型的声明式基类"""
    pass


# ---------------------------------------------------------------------------
# FastAPI 依赖注入 —— 获取数据库会话
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖项：提供异步数据库会话，请求结束后自动关闭。
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# 初始化数据库（创建所有表）
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """
    创建所有已注册的 ORM 表。应在应用启动时调用。
    """
    async with engine.begin() as conn:
        # 导入模型，确保 Base.metadata 包含所有表定义
        from app import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
