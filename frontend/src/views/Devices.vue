<template>
  <div class="devices-page" v-loading="loading">
    <!-- 操作工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索设备名称、IP地址或位置..."
            prefix-icon="Search"
            clearable
            style="width: 280px"
          />
          <el-select v-model="filterCategory" placeholder="设备分类" clearable style="width: 140px">
            <el-option label="全部类别" value="" />
            <el-option label="交换机 (Switch)" value="switch" />
            <el-option label="路由器 (Router)" value="router" />
            <el-option label="防火墙 (Firewall)" value="firewall" />
          </el-select>
        </div>

        <div class="toolbar-right">
          <el-button type="default" @click="handleInitSamples">
            <el-icon><MagicStick /></el-icon>&nbsp;一键添加样例设备
          </el-button>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon>&nbsp;添加设备
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 设备列表表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="filteredDevices" stripe style="width: 100%">
        <el-table-column prop="name" label="设备名称" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="IP 地址" width="150">
          <template #default="{ row }">
            <code>{{ row.host }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="port" label="SSH 端口" width="95" align="center" />
        <el-table-column prop="category" label="分类" width="110">
          <template #default="{ row }">
            <el-tag :type="getCategoryTag(row.category)">
              {{ formatCategory(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_type" label="平台驱动" width="130" />
        <el-table-column prop="location" label="部署机房/位置" min-width="150" />
        <el-table-column prop="enabled" label="启用状态" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              :loading="testingId === row.id"
              @click="handleTestConnection(row)"
            >
              测试连接
            </el-button>
            <el-button link type="primary" size="small" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑设备对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '添加华为数通设备'"
      width="540px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="如: HW-Core-Switch-S6730" />
        </el-form-item>
        <el-form-item label="设备 IP 地址" prop="host">
          <el-input v-model="form.host" placeholder="如: 192.168.1.1" />
        </el-form-item>
        <el-form-item label="SSH 端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="设备类别" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="交换机 (Switch)" value="switch" />
            <el-option label="路由器 (Router)" value="router" />
            <el-option label="防火墙 (Firewall)" value="firewall" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备驱动类型" prop="device_type">
          <el-select v-model="form.device_type" style="width: 100%">
            <el-option label="huawei_vrp (默认 VRP)" value="huawei_vrp" />
            <el-option label="huawei_vrpv8 (VRPv8 平台)" value="huawei_vrpv8" />
            <el-option label="huawei (通用)" value="huawei" />
          </el-select>
        </el-form-item>
        <el-form-item label="登录用户名" prop="username">
          <el-input v-model="form.username" placeholder="如: admin" />
        </el-form-item>
        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="SSH 登录密码"
          />
        </el-form-item>
        <el-form-item label="物理位置/机房" prop="location">
          <el-input v-model="form.location" placeholder="如: 核心机房 A03 机柜" />
        </el-form-item>
        <el-form-item label="启用设备" prop="enabled">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDevices,
  createDevice,
  updateDevice,
  deleteDevice,
  testDevice,
  initSampleDevices,
} from '../api'

const loading = ref(false)
const devices = ref([])
const searchQuery = ref('')
const filterCategory = ref('')
const testingId = ref(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({
  id: null,
  name: '',
  host: '',
  port: 22,
  username: '',
  password: '',
  category: 'switch',
  device_type: 'huawei_vrp',
  location: '',
  enabled: true,
})

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入 IP 地址', trigger: 'blur' }],
  username: [{ required: true, message: '请输入登录用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }],
  category: [{ required: true, message: '请选择设备类别', trigger: 'change' }],
}

const filteredDevices = computed(() => {
  return devices.value.filter((d) => {
    const matchQuery =
      !searchQuery.value ||
      d.name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      d.host?.includes(searchQuery.value) ||
      d.location?.includes(searchQuery.value)
    const matchCat = !filterCategory.value || d.category === filterCategory.value
    return matchQuery && matchCat
  })
})

function formatCategory(cat) {
  const map = { switch: '交换机', router: '路由器', firewall: '防火墙' }
  return map[cat] || cat
}

function getCategoryTag(cat) {
  const map = { switch: 'success', router: 'warning', firewall: 'danger' }
  return map[cat] || 'info'
}

async function loadDevices() {
  loading.value = true
  try {
    const res = await getDevices()
    devices.value = res.data || []
  } catch (err) {
    ElMessage.error('加载设备列表失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  isEdit.value = false
  form.value = {
    id: null,
    name: '',
    host: '',
    port: 22,
    username: 'admin',
    password: '',
    category: 'switch',
    device_type: 'huawei_vrp',
    location: '',
    enabled: true,
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await updateDevice(form.value.id, form.value)
        ElMessage.success('设备更新成功')
      } else {
        await createDevice(form.value)
        ElMessage.success('设备创建成功')
      }
      dialogVisible.value = false
      loadDevices()
    } catch (err) {
      ElMessage.error((isEdit.value ? '更新' : '创建') + '失败: ' + err.message)
    } finally {
      submitting.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除设备 "${row.name}" (${row.host}) 吗？`, '提示', {
      type: 'warning',
    })
    await deleteDevice(row.id)
    ElMessage.success('设备已删除')
    loadDevices()
  } catch (e) {
    // 用户取消
  }
}

async function handleTestConnection(row) {
  testingId.value = row.id
  try {
    const res = await testDevice(row.id)
    if (res.data?.success) {
      ElMessage.success(res.data.message || '连接测试通过')
    } else {
      ElMessage.warning(res.data.message || '连接测试失败')
    }
  } catch (err) {
    ElMessage.error('测试异常: ' + err.message)
  } finally {
    testingId.value = null
  }
}

async function handleInitSamples() {
  try {
    const res = await initSampleDevices()
    ElMessage.success(res.data?.message || '演示设备注入成功')
    loadDevices()
  } catch (err) {
    ElMessage.error('注入样例设备失败: ' + err.message)
  }
}

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.devices-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-card {
  border-radius: 8px;
}
</style>
