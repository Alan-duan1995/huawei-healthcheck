# 华为数通设备健康巡检系统 - PowerShell 启动脚本
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         华为数通设备健康巡检系统 (Huawei NetCheck) - PowerShell" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " 1. 一键运行 CLI 模拟仿真巡检并在浏览器查看报告"
Write-Host " 2. 运行真实网络巡检 (使用 devices.example.yaml)"
Write-Host " 3. 启动 Web 后端服务 (FastAPI, 端口 8000)"
Write-Host " 4. 启动 Web 前端服务 (Vue 3, 端口 3000)"
Write-Host " 5. 退出"
Write-Host "======================================================================" -ForegroundColor Cyan

$choice = Read-Host "请输入数字选项 [1-5]"

switch ($choice) {
    "1" {
        Write-Host "`n[*] 正在启动 CLI 模拟巡检..." -ForegroundColor Green
        python "$CurrentDir\inspect_cli.py" --demo --view
    }
    "2" {
        Write-Host "`n[*] 正在使用 devices.example.yaml 进行巡检..." -ForegroundColor Green
        python "$CurrentDir\inspect_cli.py" -c "$CurrentDir\devices.example.yaml" --view
    }
    "3" {
        Write-Host "`n[*] 正在启动后端服务 (http://localhost:8000)..." -ForegroundColor Green
        Set-Location "$CurrentDir\backend"
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "4" {
        Write-Host "`n[*] 正在启动前端开发服务 (http://localhost:3000)..." -ForegroundColor Green
        Set-Location "$CurrentDir\frontend"
        npm run dev
    }
    default {
        Write-Host "退出。"
    }
}
