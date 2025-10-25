<template>
  <el-card class="box-card" style="max-width: 520px; margin: 24px auto;">
    <h2>登录</h2>
    <el-form :model="form" label-width="120px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" placeholder="请输入用户名" />
      </el-form-item>

      <el-form-item label="密码哈希">
        <el-input
          v-model="form.password_hash"
          placeholder="示例：'hash'（演示）或实际哈希"
        />
      </el-form-item>

      <el-button type="primary" @click="submit" :loading="loading">登录</el-button>
      <el-button @click="goRegister" style="margin-left:8px;">没有账号？去注册</el-button>
      
      <el-divider />
      <el-alert v-if="error" :title="error" type="error" show-icon />
    </el-form>
  </el-card>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const form = reactive({
  username: '',
  password_hash: 'hash' // 演示用，实际项目改为真实密码或哈希
})

async function submit() {
  error.value = ''
  try {
    loading.value = true
    const { data } = await loginUser(form)

    // ✅ 保存用户 id，方便 /main 页面读取
    localStorage.setItem('uid', String(data.id))

    // ✅ 跳转到 /main?uid={id}
    router.push({ path: '/main', query: { uid: String(data.id) } })

    ElMessage.success(`欢迎回来，${data.username}`)
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

function goRegister() { 
  router.push('/register') 
}
</script>
