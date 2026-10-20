#!/usr/bin/env bash
# 华为数通巡检工具启动脚本

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================="
echo "    华为数通设备自动化巡检工具启动菜单"
echo "=================================================="
echo "1) 运行命令行快速模拟巡检 (CLI Demo)"
echo "2) 启动 Web 后端 API 服务 (FastAPI, 端口 8000)"
echo "3) 启动 Web 前端服务 (Vite, 端口 3000)"
echo "4) 退出"
echo "=================================================="
read -p "请选择运行模式 [1-4]: " choice

case $choice in
  1)
    echo "正在启动 CLI 模拟巡检..."
    python3 "$DIR/inspect_cli.py" --demo
    ;;
  2)
    echo "正在启动后端服务 (0.0.0.0:8000)..."
    cd "$DIR/backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ;;
  3)
    echo "正在启动前端服务 (localhost:3000)..."
    cd "$DIR/frontend"
    npm run dev
    ;;
  *)
    echo "退出。"
    exit 0
    ;;
esac
