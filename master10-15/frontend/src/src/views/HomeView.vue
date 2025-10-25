<template>
    <div class="home-container">
      <h1>欢迎来到婚恋系统</h1>
      <p>在这里，注册/登录后即可完善资料、获取匹配推荐并发起牵线。</p>
  
      <div class="actions">
        <el-button type="primary" size="large" @click="goRegister">注册用户</el-button>
        <el-button size="large" style="margin-left: 12px;" @click="goLogin">登录</el-button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { useRouter } from 'vue-router'
  const router = useRouter()
  const goRegister = () => router.push('/register')
  const goLogin    = () => router.push('/login')
  </script>
  
  <style scoped>
  .home-container { max-width: 800px; margin: 80px auto; text-align: center; }
  h1 { font-size: 32px; margin-bottom: 16px; }
  p  { color: #555; margin-bottom: 40px; }
  .actions { margin-top: 20px; }
  </style>
  