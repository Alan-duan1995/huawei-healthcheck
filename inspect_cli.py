#!/usr/bin/env python3
"""
华为数通设备自动化巡检 CLI 工具
开箱即用，支持交换机、核心路由器、下一代防火墙批量并发巡检。
支持现场直接运行并导出自包含 HTML 交互式巡检报告。
"""

import argparse
import asyncio
import os
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Windows 终端 ANSI 颜色与 UTF-8 编码兼容设置
if sys.platform.startswith("win"):
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 启用虚拟终端代码处理 (ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# 将 backend 路径加入 sys.path 以便复用核心解析与报告模块
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

try:
    import yaml
except ImportError:
    yaml = None

from app.services.collector import DeviceCollector
from app.services.analyzer import HealthAnalyzer
from app.services.reporter import ReportGenerator


def print_banner():
    banner = r"""
  _    _                               _   _      _    _____ _               _    
 | |  | |                             (_) | \ | | |  / ____| |             | |   
 | |__| |_   _  __ ___      _____ _    _  |  \| | ___| |    | |__   ___  ___| | __
 |  __  | | | |/ _` \ \ /\ / / _ \ |  | | | . ` |/ _ \ |    | '_ \ / _ \/ __| |/ /
 | |  | | |_| | (_| |\ V  V /  __/ |  | | | |\  |  __/ |____| | | |  __/ (__|   < 
 |_|  |_|\__,_|\__,_| \_/\_/ \___|_|  |_| |_| \_|\___|\_____|_| |_|\___|\___|_|\_\
    == 华为数通设备自动化巡检工具 (Huawei Datacom Health Inspector) ==
    """
    print("\033[36m" + banner + "\033[0m")


def load_devices_from_file(filepath: str) -> list:
    path = Path(filepath)
    if not path.exists():
        print(f"\033[31m[错误] 配置文件不存在: {filepath}\033[0m")
        sys.exit(1)

    if not yaml:
        print("\033[31m[错误] 缺少 PyYAML 库，请先安装: pip install pyyaml\033[0m")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict):
        return data.get("devices", [])
    elif isinstance(data, list):
        return data
    return []


def get_mock_devices() -> list:
    return [
        {
            "name": "HW-Core-S6730",
            "host": "192.168.10.1",
            "port": 22,
            "username": "admin",
            "password": "Password@123",
            "category": "switch",
            "device_type": "huawei_vrp",
            "location": "数据中心机房 01 机柜",
        },
        {
            "name": "HW-Edge-NE40E",
            "host": "192.168.20.1",
            "port": 22,
            "username": "admin",
            "password": "Password@123",
            "category": "router",
            "device_type": "huawei_vrp",
            "location": "广域网出口机房 02 机柜",
        },
        {
            "name": "HW-Sec-USG6650",
            "host": "192.168.30.1",
            "port": 22,
            "username": "admin",
            "password": "Password@123",
            "category": "firewall",
            "device_type": "huawei_vrp",
            "location": "安全防护隔离区 03 机柜",
        },
    ]


def inspect_single_device(dev: dict, analyzer: HealthAnalyzer) -> dict:
    name = dev.get("name", dev.get("host", "未知"))
    host = dev.get("host", "")
    cat = dev.get("category", "switch")

    print(f"\033[34m[*] 正在巡检设备: {name} ({host}) [{cat}]...\033[0m")

    collector = DeviceCollector(dev)
    collect_res = collector._collect_sync()

    if not collect_res.get("success"):
        err = collect_res.get("error", "采集未知错误")
        print(f"\033[31m[-] 设备 {name} 采集失败: {err}\033[0m")
        return {
            "device_name": name,
            "device_host": host,
            "category": cat,
            "status": "failed",
            "health_score": 0,
            "health_level": "critical",
            "error_message": err,
            "issues": [f"采集失败: {err}"],
        }

    outputs = collect_res.get("outputs", {})
    analysis = analyzer.analyze(outputs, cat)

    score = analysis.get("health_score", 0)
    score_color = "\033[32m" if score >= 80 else ("\033[33m" if score >= 60 else "\033[31m")
    print(f"{score_color}[+] 设备 {name} 巡检完成，健康评分: {score} 分\033[0m")

    item = {
        "device_name": name,
        "device_host": host,
        "category": cat,
        "status": "completed",
        "health_score": score,
        "cpu_usage": analysis.get("cpu_usage"),
        "memory_usage": analysis.get("memory_usage"),
        "temperature": analysis.get("temperature"),
        "fan_status": analysis.get("fan_status"),
        "power_status": analysis.get("power_status"),
        "uptime": analysis.get("uptime"),
        "ntp_status": analysis.get("ntp_status"),
        "health_level": analysis.get("health_level"),
        "issues": analysis.get("issues", []),
        "metric_scores": analysis.get("metric_scores", {}),
    }
    return item


def run_inspection(devices: list, output_dir: str, workers: int = 5) -> str:
    start_time = datetime.now()
    analyzer = HealthAnalyzer()

    print(f"\033[32m[+] 开始并发巡检，目标设备数: {len(devices)} 台，并发线程数: {workers}\033[0m")
    print("-" * 75)

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(inspect_single_device, d, analyzer) for d in devices]
        for f in futures:
            results.append(f.result())

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("-" * 75)
    print(f"\033[32m[+] 全部设备巡检结束，耗时: {duration:.2f} 秒\033[0m")

    # 生成 HTML 报告
    template_dir = str(BASE_DIR / "backend" / "app" / "templates")
    reporter = ReportGenerator(template_dir=template_dir, output_dir=output_dir)

    task_info = {
        "name": f"华为数通设备巡检_{start_time.strftime('%Y%m%d_%H%M%S')}",
        "start_time": start_time,
        "end_time": end_time,
        "total_devices": len(devices),
        "completed_devices": len(results),
    }

    report_path = reporter.generate(task_info, results)
    print(f"\033[32m[✓] 巡检报告已成功生成: {report_path}\033[0m")

    # 打印简要控制台汇总表格
    print("\n" + "=" * 75)
    print(f"{'设备名称':<20} {'IP地址':<16} {'分类':<10} {'健康分':<8} {'状态'}")
    print("-" * 75)
    for r in results:
        status_txt = "正常" if r.get("health_score", 0) >= 80 else ("需关注" if r.get("health_score", 0) >= 60 else "严重/失败")
        print(f"{r.get('device_name'):<20} {r.get('device_host'):<16} {r.get('category'):<10} {r.get('health_score', 0):<8} {status_txt}")
    print("=" * 75)

    return report_path


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="华为数通设备自动化巡检工具 (CLI)")
    default_output = str(BASE_DIR / "reports")
    parser.add_argument("-c", "--config", type=str, default=str(BASE_DIR / "devices.example.yaml"), help="设备清单 YAML 配置文件路径")
    parser.add_argument("-o", "--output", type=str, default=default_output, help="HTML 报告输出目录")
    parser.add_argument("-w", "--workers", type=int, default=5, help="并发巡检并发数 (默认 5)")
    parser.add_argument("--demo", action="store_true", help="演示模拟模式（内置交换机、路由器、防火墙仿真数据，无需连物理机）")
    parser.add_argument("-i", "--interactive", action="store_true", help="开启交互式向导模式")
    parser.add_argument("--view", action="store_true", help="巡检完成后自动在默认浏览器中打开 HTML 报告")

    args = parser.parse_args()

    # 当未传入参数或显式指定 -i 时，启动友好的终端交互式向导
    interactive_mode = args.interactive or (len(sys.argv) == 1)
    if interactive_mode and not args.demo and "-c" not in sys.argv and "--config" not in sys.argv:
        print("\033[36m" + "=" * 55)
        print(" 请选择华为数通设备巡检模式：")
        print("   1) 模拟仿真演练 (Demo，无需真实硬件，秒级出报告)")
        print("   2) 真实设备巡检 (从 YAML 清单读取 IP 执行 SSH 采集)")
        print("   3) 退出")
        print("=" * 55 + "\033[0m")
        try:
            choice = input("请输入选项编号 [1-3, 默认 1]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消。")
            sys.exit(0)

        if choice == "2":
            cfg_input = input(f"请输入设备配置文件路径 [默认 {args.config}]: ").strip()
            if cfg_input:
                args.config = cfg_input
            devices = load_devices_from_file(args.config)
        elif choice == "3":
            print("退出。")
            sys.exit(0)
        else:
            print("\033[33m[*] 启动华为典型网络拓扑仿真巡检...\033[0m")
            os.environ["MOCK_INSPECTION"] = "1"
            devices = get_mock_devices()

        try:
            auto_open = input("是否在巡检完成后自动在浏览器中打开报告？[Y/n, 默认 Y]: ").strip().lower()
            if auto_open in ("", "y", "yes"):
                args.view = True
        except (KeyboardInterrupt, EOFError):
            pass
    elif args.demo:
        print("\033[33m[*] 已开启【演示模拟仿真模式】，将对预设的典型华为数通网络拓扑进行全流程巡检\033[0m")
        os.environ["MOCK_INSPECTION"] = "1"
        devices = get_mock_devices()
    else:
        if not os.path.exists(args.config):
            print(f"\033[33m[*] 未找到配置文件 {args.config}，自动启用内置华为演示设备...\033[0m")
            os.environ["MOCK_INSPECTION"] = "1"
            devices = get_mock_devices()
        else:
            print(f"[*] 正在从 {args.config} 读取设备清单...")
            devices = load_devices_from_file(args.config)

    if not devices:
        print("\033[31m[错误] 设备列表为空，退出。\033[0m")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    report_file = run_inspection(devices, args.output, args.workers)

    print(f"\n\033[36m提示: 可在浏览器中直接打开该报告查看交互式图表与设备详情:\033[0m")
    if sys.platform.startswith("win"):
        print(f'\033[36mstart "" "{report_file}"\033[0m\n')
    elif sys.platform == "darwin":
        print(f'\033[36mopen "{report_file}"\033[0m\n')
    else:
        print(f'\033[36mxdg-open "{report_file}"\033[0m\n')

    if args.view:
        try:
            webbrowser.open(Path(report_file).as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    main()
