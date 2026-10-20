# 华为数通设备自动化巡检工具 (Huawei Datacom Health Inspector)

专业的华为数通设备（交换机、路由器、防火墙）健康状态巡检与自动化诊断工具。通过 SSH (Netmiko / Paramiko) 协议批量并发采集设备运行数据，使用正则引擎智能解析状态指标，基于多维加权评分算法生成健康体检得分，并输出专业交互式 HTML 巡检报告。

---

## 🌟 核心功能与巡检维度

### 1. 基础硬件与运行状态
- **CPU & 内存利用率**：采集当前与5分钟平均利用率，支持多核/多板卡，超阈值告警。
- **温度与环境**：板卡/槽位传感器温度检测，Minor/Major/Fatal 阈值对比。
- **电源与风扇状态**：双电源冗余供电状态、电源在位检查、风扇模块转速与运转状态。
- **运行时间与系统补丁**：连续运行时间统计，版本号与已加载 Patch 状态。

### 2. 接口与链路健康度
- **接口 Up/Down 统计**：物理端口状态、协议状态、管理性 Down 过滤。
- **CRC 错包与丢包诊断**：InErrors / OutErrors 错包增量检测，光衰与链路质量异常预警。
- **带宽利用率统计**：进出方向利用率监测。

### 3. 路由与网络协议
- **OSPF 邻居状态**：Peer 状态检查（Full 状态验证、Init/2-Way/ExStart 异常捕获）。
- **BGP 邻居状态**：BGP Peer 状态（Established 验证、Down 状态与报文收发统计）。
- **NTP 时钟同步**：Clock Status 同步状态与层数检查。

### 4. 安全与防火墙专项
- **并发会话数与使用率**：当前连接数、最大连接数、会话占比诊断。
- **双机热备 (HRP)**：HRP 状态、Master/Backup 主备一致性检查。
- **IPSec VPN 隧道**：活动安全联盟 (Active SA) 状态。

### 5. 异常告警与日志分析
- **活动告警 (Active Alarm)**：提取 Critical / Major / Minor 级别未恢复告警。
- **日志缓冲区 (Logbuffer)**：高频异常 Link-Down / Flapping 日志检测。

---

## 📂 项目结构

```
huawei-healthcheck/
├── inspect_cli.py              # 🚀 便携式独立 CLI 巡检工具（支持现场无Web环境直接运行）
├── devices.example.yaml        # 📋 设备清单配置示例
├── start.sh                    # ⚡ 一键启动脚本
├── README.md                   # 📖 项目文档
│
├── backend/                    # 🐍 FastAPI 巡检服务后端
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── models.py           # 数据库模型 (设备表、任务表、结果表)
│   │   ├── schemas.py          # Pydantic 校验模型
│   │   ├── database.py         # 异步 SQLite / SQLAlchemy 配置
│   │   ├── routers/            # API 路由 (devices, tasks, reports)
│   │   ├── templates/
│   │   │   └── report.html     # 专业单文件 HTML 巡检报告模板
│   │   └── services/
│   │       ├── collector.py    # Netmiko SSH 并发采集引擎 (含真实连接与Mock仿真)
│   │       ├── parsers.py      # 华为 VRP 命令回显正则解析器 (700+行专业解析)
│   │       ├── analyzer.py     # 多维加权健康评分算法引擎
│   │       └── reporter.py     # HTML 报告生成器 (支持 Jinja2 与原生双引擎)
│   ├── config.yaml             # 系统配置与告警阈值配置
│   └── requirements.txt        # Python 依赖包清单
│
├── frontend/                   # 💻 Vue 3 + Element Plus + ECharts 运维控制台
│   ├── src/
│   │   ├── App.vue             # 控制台全局布局 (侧边栏导航、Header)
│   │   ├── views/
│   │   │   ├── Dashboard.vue   # 巡检监控大屏 (健康指数、状态饼图、走势图)
│   │   │   ├── Devices.vue     # 设备台账管理 (增删改查、连通性测试、一键导入)
│   │   │   ├── Tasks.vue       # 巡检任务中心 (一键发起巡检、实时进度轮询)
│   │   │   └── Reports.vue     # 报告中心 (在线预览、下载 HTML 报告、健康矩阵)
│   │   ├── api/index.js        # Axios API 交互封装
│   │   └── router/index.js     # 路由配置
│   ├── package.json
│   └── vite.config.js
└── reports/                    # 📊 生成的 HTML 巡检报告存放目录
```

---

## 🚀 使用方式

### 方式一：Windows 端极简运行（推荐 Windows 用户）

项目已针对 Windows 环境深度优化（自动适配控制台 ANSI 颜色与 UTF-8 编码、双击脚本自动调用系统默认浏览器展示 HTML 报告）：

1. **一键巡检体验**：
   - 直接双击运行根目录下的 `inspect.bat`，即可一键进行模拟仿真巡检，完成后自动弹出默认浏览器展示漂亮的巡检报告。
2. **Windows 交互式菜单**：
   - 双击运行 `start.bat`（或在 PowerShell 中执行 `.\start.ps1`），即可通过数字菜单启动：
     - `1`：运行 CLI 模拟仿真巡检并在浏览器查看报告
     - `2`：运行真实网络巡检
     - `3`：启动 FastAPI 后端服务 (端口 8000)
     - `4`：启动 Vue 3 前端服务 (端口 3000)
     - `5`：安装 Python 依赖

---

### 方式二：独立 CLI 命令行快速巡检（跨平台 Linux / macOS / Windows）

不需要部署复杂的前后端 Web 服务，直接在终端中运行即可批量巡检并生成漂亮的离线 HTML 报告：

```bash
# 1. 进入项目目录
cd /Users/alanduan/.gemini/antigravity/scratch/huawei-healthcheck

# 2. 仿真演练测试（无需物理机，模拟典型交换机/路由器/防火墙）
python3 inspect_cli.py --demo

# 3. 指定设备清单进行真实网络巡检
python3 inspect_cli.py -c devices.example.yaml -o ./reports -w 5
```

**命令行参数说明**：
- `-c, --config`：指定设备配置文件路径（默认为 `devices.example.yaml`）。
- `-o, --output`：指定生成的 HTML 报告输出目录（默认为 `./reports`）。
- `-w, --workers`：指定并发采集的线程数（默认为 `5`）。
- `--demo`：开启仿真演练模式，自动加载典型拓扑设备并生成样例报告。

执行完成后，工具会直接输出 HTML 报告文件路径，双击或在浏览器中打开即可查看：
```bash
open reports/report_*.html
```

---

### 方式三：全功能 Web 可视化管理平台模式

适合网络运维中心（NOC）、定期调度巡检以及多成员协同管理：

#### 1. 安装后端 Python 依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 2. 启动 FastAPI 后端服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
后端 API 文档（Swagger UI）：打开浏览器访问 `http://localhost:8000/docs`

#### 3. 启动 Vue 3 前端界面
```bash
cd ../frontend
npm install
npm run dev
```
前端界面：打开浏览器访问 `http://localhost:3000`

---

## 📋 设备清单配置示例 (`devices.yaml`)

```yaml
devices:
  # 核心交换机
  - name: "HW-Core-S6730"
    host: "192.168.10.1"
    port: 22
    username: "inspect_user"
    password: "YourPassword123"
    category: "switch"
    device_type: "huawei_vrp"
    location: "数据中心 A 机房 01 机柜"

  # 出口核心路由器
  - name: "HW-Edge-NE40E"
    host: "192.168.20.1"
    port: 22
    username: "inspect_user"
    password: "YourPassword123"
    category: "router"
    device_type: "huawei_vrp"
    location: "广域网出口机房 02 机柜"

  # 下一代防火墙
  - name: "HW-Sec-USG6650"
    host: "192.168.30.1"
    port: 22
    username: "inspect_user"
    password: "YourPassword123"
    category: "firewall"
    device_type: "huawei_vrp"
    location: "边界安全防护区 C01"
```

---

## 🔐 华为设备建议配置（只读巡检账号）

为保障生产网络安全，建议在华为设备上配置专用的低权限巡检账号（仅授予常用 display 命令执行权限）：

```text
<Huawei> system-view
[Huawei] aaa
[Huawei-aaa] local-user inspect_user password irreversible-cipher YourPassword123
[Huawei-aaa] local-user inspect_user service-type ssh
[Huawei-aaa] local-user inspect_user level 3
[Huawei-aaa] quit
[Huawei] ssh user inspect_user authentication-type password
[Huawei] ssh user inspect_user service-type stelnet
```
