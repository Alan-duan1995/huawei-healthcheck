<template>
  <div class="tasks-page" v-loading="loading">
    <!-- 顶部操作栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div>
          <h3>华为数通巡检任务管理</h3>
          <p class="sub-text">支持对全网交换机、核心路由器、出口防火墙执行自动化批量状态检查</p>
        </div>
        <div>
          <el-button type="primary" size="large" @click="openCreateDialog">
            <el-icon><VideoPlay /></el-icon>&nbsp;创建巡检任务
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 运行中的任务进度监控卡片 -->
    <el-card shadow="hover" class="running-card" v-if="activeRunningTask">
      <div class="running-header">
        <div class="running-info">
          <span class="pulse-dot"></span>
          <strong style="font-size: 16px;">正在执行巡检任务: {{ activeRunningTask.name }}</strong>
        </div>
        <el-tag type="warning" effect="dark">巡检采集处理中...</el-tag>
      </div>
      <div class="progress-wrap">
        <el-progress
          :percentage="calculateProgress(activeRunningTask)"
          :stroke-width="14"
          striped
          striped-flow
          :duration="15"
        />
        <div class="progress-meta">
          <span>
            已巡检完成: {{ activeRunningTask.completed_devices || 0 }} / {{ activeRunningTask.total_devices || 0 }} 台设备
          </span>
          <span>开始时间: {{ formatTime(activeRunningTask.start_time) }}</span>
        </div>
      </div>
    </el-card>

    <!-- 任务历史表格 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <span>巡检任务历史记录</span>
          <el-button link type="primary" @click="loadTasks">
            <el-icon><Refresh /></el-icon>&nbsp;刷新列表
          </el-button>
        </div>
      </template>

      <el-table :data="tasks" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="任务名称" min-width="200">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">
              {{ formatStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="完成进度" width="140">
          <template #default="{ row }">
            <span>{{ row.completed_devices || 0 }} / {{ row.total_devices || 0 }} 台</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewTaskDetail(row)">
              详情
            </el-button>
            <el-button
              link
              type="success"
              size="small"
              :disabled="row.status !== 'completed'"
              @click="goToReport(row)"
            >
              巡检报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建巡检任务弹窗 -->
    <el-dialog v-model="createDialogVisible" title="创建华为数通巡检任务" width="600px">
      <el-form label-width="110px">
        <el-form-item label="任务名称">
          <el-input
            v-model="newTaskName"
            placeholder="留空则自动生成（例: 华为核心设备日常巡检_20261020）"
          />
        </el-form-item>
        <el-form-item label="巡检设备范围">
          <div style="width: 100%;">
            <el-radio-group v-model="targetScope" style="margin-bottom: 12px;">
              <el-radio label="all">全网所有已启用设备 ({{ enabledDevices.length }} 台)</el-radio>
              <el-radio label="custom">指定特定设备</el-radio>
            </el-radio-group>

            <div v-if="targetScope === 'custom'" class="device-picker-box">
              <el-checkbox-group v-model="selectedDeviceIds">
                <div v-for="d in enabledDevices" :key="d.id" class="picker-item">
                  <el-checkbox :label="d.id">
                    <strong>{{ d.name }}</strong> ({{ d.host }} - {{ d.category }})
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateTask">
          立即执行巡检
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="巡检任务详细结果" size="650px">
      <div v-if="selectedTaskDetail" v-loading="drawerLoading">
        <div class="drawer-header-meta">
          <div>
            <h3>{{ selectedTaskDetail.name }}</h3>
            <p class="sub-text">
              状态:
              <el-tag size="small" :type="getStatusTag(selectedTaskDetail.status)">
                {{ formatStatus(selectedTaskDetail.status) }}
              </el-tag>
            </p>
          </div>
          <el-button
            type="primary"
            size="small"
            v-if="selectedTaskDetail.status === 'completed'"
            @click="goToReport(selectedTaskDetail)"
          >
            查看 HTML 报告
          </el-button>
        </div>

        <el-divider />

        <h4>各设备巡检结果明细 ({{ selectedTaskDetail.results?.length || 0 }} 台)</h4>
        <div class="result-list">
          <div
            v-for="res in selectedTaskDetail.results"
            :key="res.id"
            class="result-item"
            :class="'status-' + res.status"
          >
            <div class="res-row">
              <div>
                <strong>{{ res.device_name }}</strong>
                <span class="sub-text"> ({{ res.device_host }} · {{ res.category }})</span>
              </div>
              <div>
                <el-tag
                  :type="res.health_score >= 80 ? 'success' : res.health_score >= 60 ? 'warning' : 'danger'"
                  v-if="res.status === 'completed'"
                >
                  {{ res.health_score }} 分
                </el-tag>
                <el-tag type="danger" v-else>失败</el-tag>
              </div>
            </div>

            <div v-if="res.status === 'completed'" class="metrics-tags">
              <span>CPU: {{ res.cpu_usage !== null ? res.cpu_usage + '%' : 'N/A' }}</span>
              <span>内存: {{ res.memory_usage !== null ? res.memory_usage + '%' : 'N/A' }}</span>
              <span>温度: {{ res.temperature !== null ? res.temperature + '℃' : 'N/A' }}</span>
              <span>风扇: {{ res.fan_status || '正常' }}</span>
              <span>电源: {{ res.power_status || '正常' }}</span>
            </div>

            <div v-if="res.error_message" class="error-box">
              ⚠️ 错误: {{ res.error_message }}
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTasks, createTask, getTask, getDevices } from '../api'

const router = useRouter()
const loading = ref(false)
const tasks = ref([])
const devices = ref([])

const createDialogVisible = ref(false)
const creating = ref(false)
const newTaskName = ref('')
const targetScope = ref('all')
const selectedDeviceIds = ref([])

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const selectedTaskDetail = ref(null)

let pollTimer = null

const enabledDevices = computed(() => devices.value.filter((d) => d.enabled))

const activeRunningTask = computed(() => {
  return tasks.value.find((t) => t.status === 'running')
})

function formatTime(str) {
  if (!str) return '--'
  return new Date(str).toLocaleString('zh-CN')
}

function formatStatus(status) {
  const map = {
    pending: '排队中',
    running: '巡检中',
    completed: '已完成',
    failed: '异常中断',
  }
  return map[status] || status
}

function getStatusTag(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function calculateProgress(task) {
  if (!task || !task.total_devices) return 0
  const p = Math.round(((task.completed_devices || 0) / task.total_devices) * 100)
  return Math.min(100, Math.max(0, p))
}

async function loadTasks() {
  try {
    const res = await getTasks()
    tasks.value = res.data || []
  } catch (err) {
    ElMessage.error('获取任务列表失败: ' + err.message)
  }
}

async function loadDevices() {
  try {
    const res = await getDevices()
    devices.value = res.data || []
  } catch (err) {
    console.error(err)
  }
}

function openCreateDialog() {
  newTaskName.value = ''
  targetScope.value = 'all'
  selectedDeviceIds.value = []
  createDialogVisible.value = true
  loadDevices()
}

async function handleCreateTask() {
  creating.value = true
  try {
    const payload = {}
    if (newTaskName.value.trim()) {
      payload.name = newTaskName.value.trim()
    }
    if (targetScope.value === 'custom') {
      if (selectedDeviceIds.value.length === 0) {
        ElMessage.warning('请至少勾选一台要巡检的设备')
        creating.value = false
        return
      }
      payload.device_ids = selectedDeviceIds.value
    }
    await createTask(payload)
    ElMessage.success('已启动华为数通设备巡检')
    createDialogVisible.value = false
    loadTasks()
  } catch (err) {
    ElMessage.error('启动巡检任务失败: ' + err.message)
  } finally {
    creating.value = false
  }
}

async function viewTaskDetail(row) {
  drawerLoading.value = true
  drawerVisible.value = true
  try {
    const res = await getTask(row.id)
    selectedTaskDetail.value = res.data
  } catch (err) {
    ElMessage.error('获取任务详情失败: ' + err.message)
  } finally {
    drawerLoading.value = false
  }
}

function goToReport(row) {
  router.push('/reports')
}

function startPolling() {
  pollTimer = setInterval(() => {
    // 如果有正在运行的任务，自动刷新
    if (activeRunningTask.value) {
      loadTasks()
    }
  }, 2500)
}

onMounted(() => {
  loading.value = true
  Promise.all([loadTasks(), loadDevices()]).finally(() => {
    loading.value = false
  })
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.tasks-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sub-text {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.running-card {
  border-left: 4px solid #f59e0b;
  background-color: #fffbeb;
}
.running-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.running-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 10px #f59e0b;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.progress-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.device-picker-box {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 12px;
  background: #f8fafc;
}
.picker-item {
  padding: 4px 0;
}

.drawer-header-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}
.result-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}
.res-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.metrics-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #475569;
  background: #f1f5f9;
  padding: 6px 10px;
  border-radius: 6px;
}
.error-box {
  margin-top: 8px;
  font-size: 12px;
  color: #ef4444;
  background: #fef2f2;
  padding: 6px 10px;
  border-radius: 6px;
}
</style>
