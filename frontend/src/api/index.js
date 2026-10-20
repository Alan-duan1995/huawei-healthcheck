import axios from 'axios'

// 创建 Axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)

// ==================== 设备管理 API ====================

/** 获取设备列表 */
export function getDevices(params) {
  return api.get('/devices', { params })
}

/** 创建设备 */
export function createDevice(data) {
  return api.post('/devices', data)
}

/** 获取设备详情 */
export function getDevice(id) {
  return api.get(`/devices/${id}`)
}

/** 更新设备 */
export function updateDevice(id, data) {
  return api.put(`/devices/${id}`, data)
}

/** 删除设备 */
export function deleteDevice(id) {
  return api.delete(`/devices/${id}`)
}

/** 测试设备连接 */
export function testDevice(id) {
  return api.post(`/devices/${id}/test`)
}

/** 一键初始化演示设备 */
export function initSampleDevices() {
  return api.post('/devices/init-samples')
}

/** 获取设备统计 */
export function getDeviceStats() {
  return api.get('/devices/stats')
}

// ==================== 巡检任务 API ====================

/** 获取任务列表 */
export function getTasks(params) {
  return api.get('/tasks', { params })
}

/** 创建巡检任务 */
export function createTask(data) {
  return api.post('/tasks', data)
}

/** 获取任务详情 */
export function getTask(id) {
  return api.get(`/tasks/${id}`)
}

/** 获取任务进度 */
export function getTaskProgress(id) {
  return api.get(`/tasks/${id}/progress`)
}

// ==================== 巡检报告 API ====================

/** 获取报告列表 */
export function getReports(params) {
  return api.get('/reports', { params })
}

/** 获取报告健康矩阵数据 */
export function getReportMatrix(id) {
  return api.get(`/reports/${id}/matrix`)
}

/** 下载报告 */
export function downloadReport(id) {
  return api.get(`/reports/${id}/download`, { responseType: 'blob' })
}

/** 获取仪表盘汇总数据 */
export function getDashboard() {
  return api.get('/reports/dashboard')
}

export default api
