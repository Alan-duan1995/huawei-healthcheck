<template>
  <div class="reports-page" v-loading="loading">
    <!-- 顶部概览 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div>
          <h3>华为数通巡检报告中心</h3>
          <p class="sub-text">查看全网历史巡检报告、下载离线 HTML 报表及分析设备健康矩阵</p>
        </div>
        <div>
          <el-button link type="primary" @click="loadReports">
            <el-icon><Refresh /></el-icon>&nbsp;刷新报告列表
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 报告列表表格 -->
    <el-card shadow="never" class="table-card">
      <div v-if="reports.length === 0" class="empty-state">
        <el-icon class="empty-icon"><DocumentDelete /></el-icon>
        <p>暂无生成的巡检报告，请先前往【巡检任务】发起一次巡检。</p>
      </div>

      <el-table :data="reports" stripe style="width: 100%" v-else>
        <el-table-column prop="task_id" label="任务ID" width="80" align="center" />
        <el-table-column prop="task_name" label="报告名称" min-width="220">
          <template #default="{ row }">
            <strong>{{ row.task_name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="total_devices" label="巡检设备数" width="120" align="center">
          <template #default="{ row }">
            <span>{{ row.total_devices }} 台</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="巡检开始时间" width="180">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column prop="end_time" label="巡检完成时间" width="180">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewOnline(row)">
              <el-icon><View /></el-icon>&nbsp;在线预览
            </el-button>
            <el-button link type="success" size="small" @click="viewMatrix(row)">
              <el-icon><Grid /></el-icon>&nbsp;健康矩阵
            </el-button>
            <el-button link type="warning" size="small" @click="handleDownload(row)">
              <el-icon><Download /></el-icon>&nbsp;下载 HTML
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 在线预览 HTML 报告对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="`报告在线预览 - ${currentReport?.task_name || ''}`"
      width="90%"
      top="4vh"
      destroy-on-close
    >
      <div class="iframe-container" v-loading="iframeLoading">
        <iframe
          v-if="previewUrl"
          :src="previewUrl"
          class="report-iframe"
          @load="iframeLoading = false"
        ></iframe>
      </div>
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleDownload(currentReport)">
          <el-icon><Download /></el-icon>&nbsp;下载该报告
        </el-button>
      </template>
    </el-dialog>

    <!-- 健康矩阵展示弹窗 -->
    <el-dialog
      v-model="matrixDialogVisible"
      :title="`设备健康矩阵 - ${currentReport?.task_name || ''}`"
      width="820px"
      destroy-on-close
    >
      <div v-loading="matrixLoading">
        <el-table :data="matrixData" border stripe style="width: 100%">
          <el-table-column prop="device_name" label="设备名称" min-width="160" />
          <el-table-column prop="category" label="分类" width="90" align="center" />
          <el-table-column prop="health_score" label="健康总分" width="95" align="center">
            <template #default="{ row }">
              <span :style="{ fontWeight: 'bold', color: getScoreColor(row.health_score) }">
                {{ row.health_score }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="cpu_score" label="CPU" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.cpu_score) }">{{ row.cpu_score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="memory_score" label="内存" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.memory_score) }">{{ row.memory_score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="temperature_score" label="温度" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.temperature_score) }">{{ row.temperature_score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="fan_score" label="风扇" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.fan_score) }">{{ row.fan_score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="power_score" label="电源" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.power_score) }">{{ row.power_score ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="ntp_score" label="NTP" width="80" align="center">
            <template #default="{ row }">
              <span :style="{ color: getScoreColor(row.ntp_score) }">{{ row.ntp_score ?? '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getReports, downloadReport, getReportMatrix } from '../api'

const loading = ref(false)
const reports = ref([])

const previewDialogVisible = ref(false)
const iframeLoading = ref(false)
const currentReport = ref(null)
const previewUrl = ref('')

const matrixDialogVisible = ref(false)
const matrixLoading = ref(false)
const matrixData = ref([])

function formatTime(str) {
  if (!str) return '--'
  return new Date(str).toLocaleString('zh-CN')
}

function getScoreColor(score) {
  if (score === null || score === undefined) return '#94a3b8'
  if (score >= 80) return '#10b981'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

async function loadReports() {
  loading.value = true
  try {
    const res = await getReports()
    reports.value = res.data || []
  } catch (err) {
    ElMessage.error('加载报告列表失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function viewOnline(row) {
  currentReport.value = row
  iframeLoading.value = true
  previewUrl.value = `/api/reports/${row.task_id}/preview`
  previewDialogVisible.value = true
}

async function viewMatrix(row) {
  currentReport.value = row
  matrixLoading.value = true
  matrixDialogVisible.value = true
  try {
    const res = await getReportMatrix(row.task_id)
    matrixData.value = res.data || []
  } catch (err) {
    ElMessage.error('获取健康矩阵失败: ' + err.message)
  } finally {
    matrixLoading.value = false
  }
}

async function handleDownload(row) {
  if (!row) return
  try {
    const res = await downloadReport(row.task_id)
    const blob = new Blob([res.data], { type: 'text/html' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `华为巡检报告_${row.task_name}.html`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('报告下载成功')
  } catch (err) {
    ElMessage.error('下载失败: ' + err.message)
  }
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.reports-page {
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

.empty-state {
  text-align: center;
  padding: 48px;
  color: #94a3b8;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.iframe-container {
  height: 72vh;
  width: 100%;
}
.report-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
}
</style>
