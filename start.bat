@echo off
chcp 65001 >nul 2>&1
title 华为数通设备健康巡检系统 (Huawei NetCheck) - 控制台

:menu
cls
echo ======================================================================
echo          华为数通设备健康巡检系统 (Huawei NetCheck) - Windows
echo ======================================================================
echo.
echo   [1] 运行 CLI 模拟仿真巡检 (秒级生成 HTML 报告并自动在浏览器中打开)
echo   [2] 运行真实网络巡检 (交互式指定 YAML 设备清单)
echo   [3] 一键启动全套 Web 平台 (新窗口独立启动后端 + 前端并自动打开浏览器)
echo   [4] 仅启动 Web 后端 API 服务 (FastAPI, 端口 8000)
echo   [5] 仅启动 Web 前端服务 (Vue 3, 端口 3000)
echo   [6] 安装 Python 后端依赖 (pip install -r backend/requirements.txt)
echo   [0] 退出
echo.
echo ======================================================================
set "choice="
set /p choice="请输入选项编号 [0-6, 默认 1]: "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo.
    echo [*] 正在启动 CLI 模拟巡检...
    python "%~dp0inspect_cli.py" --demo --view
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="2" (
    echo.
    set "cfg="
    set /p cfg="请输入设备清单路径 [默认 devices.example.yaml]: "
    if "%cfg%"=="" set cfg=%~dp0devices.example.yaml
    python "%~dp0inspect_cli.py" -c "%cfg%" --view
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo [*] 正在新窗口启动 FastAPI 后端服务...
    start "华为巡检-后端服务(8000)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    
    timeout /t 2 >nul 2>&1
    
    echo [*] 正在新窗口启动 Vue 前端开发服务...
    start "华为巡检-前端服务(3000)" cmd /k "cd /d %~dp0frontend && npm run dev"
    
    timeout /t 3 >nul 2>&1
    
    echo [*] 正在打开浏览器访问 http://localhost:3000 ...
    start http://localhost:3000
    
    echo.
    echo [✓] 后端与前端服务已分别在独立窗口启动！
    echo 按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo [*] 正在新窗口启动 FastAPI 后端服务 (http://localhost:8000)...
    start "华为巡检-后端服务(8000)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="5" (
    echo.
    echo [*] 正在新窗口启动 Vue 前端开发服务 (http://localhost:3000)...
    start "华为巡检-前端服务(3000)" cmd /k "cd /d %~dp0frontend && npm run dev"
    echo.
    echo 按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="6" (
    echo.
    echo [*] 正在安装 Python 依赖...
    cd /d "%~dp0backend"
    python -m pip install -r requirements.txt
    echo.
    echo [✓] 依赖安装完成。按任意键返回主菜单...
    pause >nul
    goto menu
)

if "%choice%"=="0" (
    exit /b 0
)

echo.
echo [!] 无效输入，请重新选择。
timeout /t 1 >nul 2>&1
goto menu
