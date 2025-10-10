<template>
    <el-card class="box-card" style="max-width: 520px; margin: 24px auto;">
      <h2>登录</h2>
      <el-form :model="form" label-width="120px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码哈希">
          <el-input v-model="form.password_hash" placeholder="示例：$2b$12$... 或 'hash'（演示）" />
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
  import { loginUser } from '../api'
  
  const router = useRouter()
  const loading = ref(false)
  const error = ref('')
  const form = reactive({
    username: '',
    password_hash: 'hash' // 演示：和注册页保持一致（真实场景请改为密码并服务端校验哈希）
  })
  
  async function submit() {
    error.value = ''
    try {
      loading.value = true
      const { data } = await loginUser(form)
      // 登录成功 → 跳到资料页
      router.push({ path: '/main', query: { user_id: data.id } })
    } catch (e) {
      error.value = e?.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }
  
  function goRegister() {
    router.push('/register')
  }
  </script>
  