@echo off
chcp 65001 >nul
title 华为数通设备健康巡检系统 - Windows 控制台

echo ======================================================================
echo          华为数通设备健康巡检系统 (Huawei NetCheck) - Windows
echo ======================================================================
echo  1. 一键运行 CLI 模拟仿真巡检并在浏览器查看报告
echo  2. 运行真实网络巡检 (使用 devices.example.yaml 或自定义配置)
echo  3. 启动 Web 后端服务 (FastAPI, 端口 8000)
echo  4. 启动 Web 前端服务 (Vue 3, 端口 3000)
echo  5. 安装 Python 后端依赖 (pip install -r backend/requirements.txt)
echo  6. 退出
echo ======================================================================
set /p choice="请输入数字选项 [1-6]: "

if "%choice%"=="1" (
    echo.
    echo [*] 正在启动 CLI 模拟巡检并生成报告...
    python "%~dp0inspect_cli.py" --demo --view
    pause
    goto end
)

if "%choice%"=="2" (
    echo.
    set /p cfg="请输入设备清单路径 [默认: devices.example.yaml]: "
    if "%cfg%"=="" set cfg=devices.example.yaml
    python "%~dp0inspect_cli.py" -c "%cfg%" --view
    pause
    goto end
)

if "%choice%"=="3" (
    echo.
    echo [*] 正在启动 FastAPI 后端服务 (http://localhost:8000)...
    cd /d "%~dp0backend"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    goto end
)

if "%choice%"=="4" (
    echo.
    echo [*] 正在启动 Vue 前端开发服务 (http://localhost:3000)...
    cd /d "%~dp0frontend"
    npm run dev
    goto end
)

if "%choice%"=="5" (
    echo.
    echo [*] 正在安装 Python 依赖...
    cd /d "%~dp0backend"
    python -m pip install -r requirements.txt
    pause
    goto end
)

:end
