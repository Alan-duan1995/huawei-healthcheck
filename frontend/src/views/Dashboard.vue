<template>
  <div class="dashboard-container" v-loading="loading">
    <!-- 顶部核心数据指标卡 -->
    <div class="metrics-grid">
      <el-card shadow="hover" class="metric-card">
        <div class="metric-content">
          <div class="metric-info">
            <span class="label">设备资产总数</span>
            <span class="number">{{ stats.total_devices || 0 }} <small>台</small></span>
          </div>
          <div class="metric-icon bg-blue">
            <el-icon><Connection /></el-icon>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="metric-card">
        <div class="metric-content">
          <div class="metric-info">
            <span class="label">全网健康指数</span>
            <span :class="['number', getScoreClass(stats.overall_health_score)]">
              {{ stats.overall_health_score || '--' }} <small>分</small>
            </span>
          </div>
          <div class="metric-icon" :class="getScoreBgClass(stats.overall_health_score)">
            <el-icon><Odometer /></el-icon>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="metric-card">
        <div class="metric-content">
          <div class="metric-info">
            <span class="label">异常/关注设备</span>
            <span class="number text-warning">
              {{ (stats.device_health_distribution?.warning || 0) + (stats.device_health_distribution?.critical || 0) }} <small>台</small>
            </span>
          </div>
          <div class="metric-icon bg-amber">
            <el-icon><Warning /></el-icon>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover" class="metric-card">
        <div class="metric-content">
          <div class="metric-info">
            <span class="label">累计巡检任务</span>
            <span class="number">{{ stats.total_tasks || 0 }} <small>次</small></span>
          </div>
          <div class="metric-icon bg-indigo">
            <el-icon><Checked /></el-icon>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 最近一次巡检状态横幅 -->
    <el-card shadow="never" class="recent-task-card" v-if="stats.latest_task">
      <div class="task-banner">
        <div class="task-banner-left">
          <div class="banner-badge">最近一次巡检</div>
          <div class="banner-title">{{ stats.latest_task.name }}</div>
          <div class="banner-meta">
            <span>设备范围: {{ stats.latest_task.total_devices }} 台</span>
            <span class="dot-sep">•</span>
            <span>状态: <el-tag size="small" type="success">{{ stats.latest_task.status }}</el-tag></span>
            <span class="dot-sep">•</span>
            <span>完成时间: {{ formatTime(stats.latest_task.end_time) }}</span>
          </div>
        </div>
        <div class="task-banner-right">
          <el-button type="primary" plain @click="viewReport(stats.latest_task.id)">
            <el-icon><Document /></el-icon>&nbsp;查看完整报告
          </el-button>
          <el-button type="primary" @click="handleRunInspection">
            <el-icon><VideoPlay /></el-icon>&nbsp;重新巡检
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 图表展示区 -->
    <div class="charts-grid">
      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="card-header">
            <span>设备健康等级分布</span>
          </div>
        </template>
        <div ref="pieChartRef" class="chart-dom"></div>
      </el-card>

      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="card-header">
            <span>巡检健康评分历史走势</span>
          </div>
        </template>
        <div ref="lineChartRef" class="chart-dom"></div>
      </el-card>
    </div>

    <!-- 异常风险与待处理事项 -->
    <el-card shadow="hover" class="issues-card">
      <template #header>
        <div class="card-header">
          <span>待关注的设备异常隐患</span>
          <el-tag type="danger" size="small" v-if="stats.recent_issues?.length">
            {{ stats.recent_issues.length }} 项异常
          </el-tag>
        </div>
      </template>

      <div v-if="!stats.recent_issues || stats.recent_issues.length === 0" class="empty-issues">
        <el-icon class="ok-icon"><CircleCheckFilled /></el-icon>
        <p>全网设备状态良好，未发现明显隐患或高风险告警。</p>
      </div>

      <el-table :data="stats.recent_issues" v-else stripe style="width: 100%">
        <el-table-column prop="device_name" label="设备名称" width="220" />
        <el-table-column prop="device_host" label="IP 地址" width="160" />
        <el-table-column prop="issue" label="异常描述" />
        <el-table-column prop="level" label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'critical' ? 'danger' : 'warning'" size="small">
              {{ row.level === 'critical' ? '严重' : '告警' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getDashboard, createTask } from '../api'

const router = useRouter()
const loading = ref(false)
const stats = ref({})

const pieChartRef = ref(null)
const lineChartRef = ref(null)
let pieChart = null
let lineChart = null

function formatTime(str) {
  if (!str) return 'N/A'
  return new Date(str).toLocaleString('zh-CN')
}

function getScoreClass(score) {
  if (!score) return ''
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

function getScoreBgClass(score) {
  if (!score) return 'bg-gray'
  if (score >= 80) return 'bg-emerald'
  if (score >= 60) return 'bg-amber'
  return 'bg-rose'
}

async function loadData() {
  loading.value = true
  try {
    const res = await getDashboard()
    stats.value = res.data || {}
    await nextTick()
    initCharts()
  } catch (err) {
    ElMessage.error('获取仪表盘数据失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function initCharts() {
  const dist = stats.value.device_health_distribution || { healthy: 0, warning: 0, critical: 0 }

  // 1. 饼图
  if (pieChartRef.value) {
    if (!pieChart) pieChart = echarts.init(pieChartRef.value)
    const pieOption = {
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      color: ['#10b981', '#f59e0b', '#ef4444'],
      series: [
        {
          name: '健康分布',
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: { show: false },
          data: [
            { value: dist.healthy || 0, name: '健康 (>=80分)' },
            { value: dist.warning || 0, name: '关注 (60~79分)' },
            { value: dist.critical || 0, name: '隐患 (<60分)' },
          ],
        },
      ],
    }
    pieChart.setOption(pieOption)
  }

  // 2. 趋势折线图
  if (lineChartRef.value) {
    if (!lineChart) lineChart = echarts.init(lineChartRef.value)
    const trend = stats.value.health_trend || []
    const dates = trend.map((t) => t.task_name || t.date?.substring(5, 16))
    const scores = trend.map((t) => t.score)

    const lineOption = {
      tooltip: { trigger: 'axis' },
      grid: { top: '15%', left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates.length ? dates : ['无历史记录'],
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
      },
      series: [
        {
          name: '健康评分',
          type: 'line',
          smooth: true,
          data: scores.length ? scores : [100],
          itemStyle: { color: '#0284c7' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(2, 132, 199, 0.4)' },
              { offset: 1, color: 'rgba(2, 132, 199, 0.02)' },
            ]),
          },
        },
      ],
    }
    lineChart.setOption(lineOption)
  }
}

function handleResize() {
  pieChart?.resize()
  lineChart?.resize()
}

function viewReport(taskId) {
  router.push(`/reports`)
}

async function handleRunInspection() {
  try {
    const res = await createTask({ name: `全网例行巡检_${new Date().toLocaleTimeString()}` })
    ElMessage.success('已成功发起巡检任务')
    router.push('/tasks')
  } catch (err) {
    ElMessage.error('发起任务失败: ' + err.message)
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  lineChart?.dispose()
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.metric-card :deep(.el-card__body) {
  padding: 18px;
}
.metric-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.metric-info .label {
  font-size: 13px;
  color: #64748b;
  display: block;
}
.metric-info .number {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 4px;
  display: block;
}
.metric-info .number small {
  font-size: 13px;
  font-weight: normal;
  color: #94a3b8;
}
.metric-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: #ffffff;
}

.bg-blue { background: #3b82f6; }
.bg-emerald { background: #10b981; }
.bg-amber { background: #f59e0b; }
.bg-indigo { background: #6366f1; }
.bg-rose { background: #ef4444; }
.bg-gray { background: #94a3b8; }

.text-success { color: #10b981 !important; }
.text-warning { color: #f59e0b !important; }
.text-danger { color: #ef4444 !important; }

.recent-task-card {
  border-left: 4px solid #0284c7;
}
.task-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.banner-badge {
  font-size: 12px;
  font-weight: 600;
  color: #0284c7;
  text-transform: uppercase;
}
.banner-title {
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
  margin: 2px 0 6px 0;
}
.banner-meta {
  font-size: 13px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dot-sep {
  color: #cbd5e1;
}
.task-banner-right {
  display: flex;
  gap: 12px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
}
.chart-card {
  min-height: 320px;
}
.card-header {
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chart-dom {
  width: 100%;
  height: 250px;
}

.issues-card {
  margin-top: 4px;
}
.empty-issues {
  padding: 32px;
  text-align: center;
  color: #10b981;
}
.ok-icon {
  font-size: 40px;
  margin-bottom: 8px;
}
</style>
