#!/usr/bin/env bash
# 华为数通巡检工具启动脚本 (macOS / Linux)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

while true; do
  clear
  echo "=================================================="
  echo "    华为数通设备自动化巡检工具启动菜单"
  echo "=================================================="
  echo "  1) 运行命令行快速模拟巡检 (CLI Demo)"
  echo "  2) 运行真实网络巡检 (使用 devices.example.yaml)"
  echo "  3) 启动 Web 后端 API 服务 (FastAPI, 端口 8000)"
  echo "  4) 启动 Web 前端服务 (Vue 3, 端口 3000)"
  echo "  0) 退出"
  echo "=================================================="
  read -p "请选择运行模式 [0-4, 默认 1]: " choice
  [ -z "$choice" ] && choice="1"

  case $choice in
    1)
      echo -e "\n[*] 正在启动 CLI 模拟巡检..."
      python3 "$DIR/inspect_cli.py" --demo --view
      echo ""
      read -n 1 -s -r -p "按任意键返回主菜单..."
      ;;
    2)
      echo ""
      read -p "请输入设备清单路径 [默认 $DIR/devices.example.yaml]: " cfg
      [ -z "$cfg" ] && cfg="$DIR/devices.example.yaml"
      python3 "$DIR/inspect_cli.py" -c "$cfg" --view
      echo ""
      read -n 1 -s -r -p "按任意键返回主菜单..."
      ;;
    3)
      echo -e "\n[*] 正在启动后端服务 (0.0.0.0:8000)..."
      cd "$DIR/backend"
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      break
      ;;
    4)
      echo -e "\n[*] 正在启动前端服务 (localhost:3000)..."
      cd "$DIR/frontend"
      npm run dev
      break
      ;;
    0)
      echo "退出。"
      exit 0
      ;;
    *)
      echo "无效选项，请重新选择。"
      sleep 1
      ;;
  esac
done
