<template>
  <div class="app-layout">
    <!-- 侧边导航栏 -->
    <aside class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><Platform /></el-icon>
        <span class="logo-text">Huawei NetCheck</span>
      </div>

      <el-menu
        :default-active="activeRoute"
        class="nav-menu"
        router
        background-color="#0f172a"
        text-color="#94a3b8"
        active-text-color="#38bdf8"
      >
        <el-menu-item index="/">
          <el-icon><DataLine /></el-icon>
          <span>巡检大屏</span>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><Connection /></el-icon>
          <span>设备台账</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Odometer /></el-icon>
          <span>巡检任务</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <span>巡检报告</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <div class="badge-card">
          <span class="dot"></span>
          <span class="status-txt">VRP 巡检引擎就绪</span>
        </div>
      </div>
    </aside>

    <!-- 主体区域 -->
    <div class="main-container">
      <!-- 顶部 Header -->
      <header class="header">
        <div class="header-left">
          <h2 class="page-title">{{ currentTitle }}</h2>
        </div>
        <div class="header-right">
          <el-tag type="info" effect="plain" class="time-tag">
            {{ currentTime }}
          </el-tag>
          <el-button type="primary" size="default" @click="goToCreateTask">
            <el-icon><VideoPlay /></el-icon>&nbsp;发起巡检
          </el-button>
        </div>
      </header>

      <!-- 页面内容视图 -->
      <main class="content-body">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const activeRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '巡检控制台')

const currentTime = ref('')
let timer = null

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function goToCreateTask() {
  router.push('/tasks')
}

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style>
/* 全局基础重置 */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background-color: #f8fafc;
  color: #1e293b;
  overflow: hidden;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
}

.sidebar {
  width: 230px;
  background-color: #0f172a;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-right: 1px solid #1e293b;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid #1e293b;
}
.logo-icon {
  font-size: 26px;
  color: #38bdf8;
}
.logo-text {
  color: #f8fafc;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.5px;
}

.nav-menu {
  border-right: none;
  flex: 1;
  padding-top: 12px;
}
.nav-menu :deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  margin: 4px 12px;
  border-radius: 8px;
}
.nav-menu :deep(.el-menu-item.is-active) {
  background-color: #1e293b !important;
  font-weight: 600;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #1e293b;
}
.badge-card {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(56, 189, 248, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #38bdf8;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.header {
  height: 64px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.time-tag {
  font-family: monospace;
  font-size: 13px;
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background-color: #f8fafc;
}
</style>
