<template>
  <div class="layout">
    <header class="header">
      <strong>婚恋系统</strong>
    </header>

    <div class="body">
      <aside class="sider">
        <el-menu :default-active="'display'">
          <el-menu-item index="display" @click="goDisplay">资料展示</el-menu-item>
          <el-menu-item index="other" disabled>其他（待扩展）</el-menu-item>
        </el-menu>
      </aside>

      <main class="content">
        <el-empty description="右侧区域暂时留白（你可在此放子路由或内容）" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const uid = Number(route.query.uid || 1)

function goDisplay(){
  router.push({ path: `/display/${uid}` })
}
</script>

<style scoped>
.layout { height: 100vh; display: flex; flex-direction: column; }
.header { height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid #eee; }
.home-btn { color: #409eff; text-decoration: none; }
.body { flex: 1; display: flex; }
.sider { width: 200px; border-right: 1px solid #eee; padding-top: 8px; }
.content { flex: 1; padding: 16px; }
</style>
