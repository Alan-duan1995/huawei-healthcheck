# 华为数通设备健康巡检系统 - PowerShell 启动脚本
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Show-Menu {
    Clear-Host
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "         华为数通设备健康巡检系统 (Huawei NetCheck) - PowerShell" -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "  [1] 运行 CLI 模拟仿真巡检 (秒级生成 HTML 报告并在浏览器打开)"
    Write-Host "  [2] 运行真实网络设备巡检 (交互式指定 YAML 设备清单)"
    Write-Host "  [3] 一键启动全套 Web 平台 (独立新窗口启动后端 + 前端，并打开浏览器)"
    Write-Host "  [4] 仅启动 Web 后端服务 (FastAPI, 端口 8000)"
    Write-Host "  [5] 仅启动 Web 前端服务 (Vue 3, 端口 3000)"
    Write-Host "  [6] 安装 Python 依赖"
    Write-Host "  [0] 退出"
    Write-Host "======================================================================" -ForegroundColor Cyan
}

while ($true) {
    Show-Menu
    $choice = Read-Host "请输入选项编号 [0-6, 默认 1]"
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

    switch ($choice) {
        "1" {
            Write-Host "`n[*] 正在启动 CLI 模拟巡检..." -ForegroundColor Green
            python "$CurrentDir\inspect_cli.py" --demo --view
            Write-Host "`n按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "2" {
            $cfg = Read-Host "`n请输入设备清单路径 [默认 $CurrentDir\devices.example.yaml]"
            if ([string]::IsNullOrWhiteSpace($cfg)) { $cfg = "$CurrentDir\devices.example.yaml" }
            python "$CurrentDir\inspect_cli.py" -c "$cfg" --view
            Write-Host "`n按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "3" {
            Write-Host "`n[*] 正在新窗口启动后端与前端服务..." -ForegroundColor Green
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$CurrentDir\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
            Start-Sleep -Seconds 2
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$CurrentDir\frontend'; npm run dev"
            Start-Sleep -Seconds 3
            Start-Process "http://localhost:3000"
            Write-Host "[✓] 服务已在新窗口启动，已打开浏览器！" -ForegroundColor Green
            Write-Host "`n按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "4" {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$CurrentDir\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
            Write-Host "`n按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "5" {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$CurrentDir\frontend'; npm run dev"
            Write-Host "`n按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "6" {
            Set-Location "$CurrentDir\backend"
            python -m pip install -r requirements.txt
            Write-Host "`n依赖安装完成。按回车键返回主菜单..."
            [void][System.Console]::ReadLine()
        }
        "0" {
            Write-Host "退出。"
            exit 0
        }
        default {
            Write-Host "无效选项，请重新选择。" -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
