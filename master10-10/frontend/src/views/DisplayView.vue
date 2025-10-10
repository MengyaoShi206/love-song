<template>
    <el-card class="box-card" style="max-width: 960px; margin: 24px auto;">
      <template #header>
        <div class="card-header">
          <span>资料展示（用户ID：{{ uid }}）</span>
          <router-link to="/main" class="home-btn">返回主页</router-link>
        </div>
      </template>
  
      <div v-if="data">
        <div style="display:flex; gap:20px; align-items:center;">
          <el-avatar :size="96" :src="data.user?.avatar_url" />
          <div>
            <h2>{{ data.user?.nickname || data.user?.username }}</h2>
            <p>{{ data.user?.city }} · {{ data.user?.email }}</p>
            <p>媒体通过：{{ data.media_count }} ｜ 问答：{{ data.qna_count }}</p>
          </div>
        </div>
        <el-divider />
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:18px;">
          <el-card><h3>公开资料</h3><pre>{{ data.profile }}</pre></el-card>
          <el-card><h3>生活方式</h3><pre>{{ data.lifestyle }}</pre></el-card>
          <el-card><h3>婚恋意向</h3><pre>{{ data.intention }}</pre></el-card>
        </div>
      </div>
      <el-empty v-else description="加载中或无数据" />
    </el-card>
  </template>
  
  <script setup>
  import { onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getDisplay } from '../api'
  
  const route = useRoute()
  const uid = Number(route.params.uid)
  const data = ref(null)
  
  onMounted(async ()=>{
    const { data: resp } = await getDisplay(uid)
    data.value = resp
  })
  </script>
  
  <style scoped>
  .card-header { display: flex; justify-content: space-between; align-items: center; }
  .home-btn { color: #409eff; text-decoration: none; }
  </style>
  