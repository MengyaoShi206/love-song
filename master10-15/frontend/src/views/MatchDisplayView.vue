<template>
    <div class="layout">
      <!-- 左侧菜单 -->
      <aside class="sidebar">
        <el-card class="sidebar-card" shadow="never">
          <div class="brand">
            <div class="brand-meta">
              <div class="brand-title">匹配中心</div>
              <div class="brand-sub">发现更合适的 TA</div>
            </div>
          </div>
  
          <el-menu
            :default-active="defaultActive"
            class="pretty-menu"
            @select="onSelect"
            :router="false"
          >
            <el-menu-item index="display">
              <el-icon><User /></el-icon>
              <span>资料展示</span>
            </el-menu-item>
  
            <el-menu-item index="match">
              <el-icon><User /></el-icon>
              <span>匹配资料展示</span>
            </el-menu-item>
  
            <el-menu-item index="other" disabled>
              <el-icon><Setting /></el-icon>
              <span>其他（待扩展）</span>
            </el-menu-item>
          </el-menu>
        </el-card>
      </aside>
  
      <!-- 右侧内容 -->
      <main class="content">
        <!-- 顶部：筛选 Tabs -->
        <div class="topbar">
          <el-tabs v-model="activeTab" @tab-click="onTabClick" class="tabs">
            <el-tab-pane label="为您推荐" name="recommend"></el-tab-pane>
            <el-tab-pane label="您的喜欢" name="likes"></el-tab-pane>
            <el-tab-pane label="已双向匹配" name="mutual"></el-tab-pane>
            <el-tab-pane label="其他" name="others"></el-tab-pane>
          </el-tabs>
        </div>
  
        <!-- 为您推荐：占位 -->
      <div v-if="activeTab === 'recommend'">
        <el-empty description="系统为您推荐的匹配对象（待接入推荐接口）" />
      </div>

        <!-- 您的喜欢 -->
        <div v-else-if="activeTab === 'likes'">
            <el-skeleton :loading="likes.loading" animated :count="3">
            <template #template>
                <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
                <div style="padding:8px 0">
                <el-skeleton-item variant="p" />
                <el-skeleton-item variant="text" />
                </div>
            </template>
            <template #default>
                <el-row :gutter="16">
                <el-col :span="8" v-for="u in likes.items" :key="u.id">
                    <el-card shadow="hover" class="user-card">
                    <div class="user-card-head">
                        <el-avatar :size="56" :src="u.avatar_url || ''" />
                        <div class="meta">
                        <div class="name">{{ u.nickname || u.username }}</div>
                        <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                        </div>
                    </div>
                    <div class="tagline">{{ u.tagline || '—' }}</div>
                    <div class="actions">
                      <el-button size="small" @click="goDisplay(u.id)">查看资料</el-button>
                    </div>
                    </el-card>
                </el-col>
                </el-row>
                <div v-if="!likes.items.length" class="empty-line">
                <el-empty description="暂无喜欢的人" />
                </div>
                <div class="pager">
                <el-pagination
                    background
                    layout="prev, pager, next"
                    :total="likes.total"
                    :page-size="likes.page_size"
                    :current-page="likes.page"
                    @current-change="(p)=>{ likes.page=p; loadLikes() }"
                />
                </div>
            </template>
            </el-skeleton>
        </div>

        <!-- 已双向匹配 -->
        <div v-else-if="activeTab === 'mutual'">
            <el-skeleton :loading="mutual.loading" animated :count="3">
            <template #template>
                <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
                <div style="padding:8px 0">
                <el-skeleton-item variant="p" />
                <el-skeleton-item variant="text" />
                </div>
            </template>
            <template #default>
                <el-row :gutter="16">
                <el-col :span="8" v-for="u in mutual.items" :key="u.id">
                    <el-card shadow="hover" class="user-card">
                    <div class="user-card-head">
                        <el-avatar :size="56" :src="u.avatar_url || ''" />
                        <div class="meta">
                        <div class="name">{{ u.nickname || u.username }}</div>
                        <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                        </div>
                    </div>
                    <div class="tagline">{{ u.tagline || '—' }}</div>
                    <div class="actions">
                        <el-button size="small" type="primary" @click="router.push(`/display/${u.id}`)">发起聊天</el-button>
                    </div>
                    </el-card>
                </el-col>
                </el-row>
                <div v-if="!mutual.items.length" class="empty-line">
                <el-empty description="暂无双向匹配" />
                </div>
                <div class="pager">
                <el-pagination
                    background
                    layout="prev, pager, next"
                    :total="mutual.total"
                    :page-size="mutual.page_size"
                    :current-page="mutual.page"
                    @current-change="(p)=>{ mutual.page=p; loadMutual() }"
                />
                </div>
            </template>
            </el-skeleton>
        </div>

        <!-- 其他 -->
        <div v-else>
            <el-empty description="更多匹配类别（待扩展）" />
        </div>
        </main>
    </div>
    </template>
  
  <script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Setting } from '@element-plus/icons-vue'
import { getMatchLikes, getMatchMutual } from '@/api'

const router = useRouter()
const route = useRoute()
const defaultActive = ref('match') // 当前页高亮“匹配资料展示”
const activeTab = ref('recommend')

const likes = reactive({ items: [], page: 1, page_size: 12, total: 0, loading: false })
const mutual = reactive({ items: [], page: 1, page_size: 12, total: 0, loading: false })

const uid = Number(localStorage.getItem('uid') || 1)

const onSelect = (key) => {
  if (key === 'display') router.push('/main')
  else if (key === 'match') router.push('/match')
}

async function loadLikes() {
  try {
    likes.loading = true
    const { data } = await getMatchLikes(uid, { page: likes.page, page_size: likes.page_size })
    Object.assign(likes, data, { loading: false })
  } catch (e) {
    likes.loading = false
  }
}

async function loadMutual() {
  try {
    mutual.loading = true
    const { data } = await getMatchMutual(uid, { page: mutual.page, page_size: mutual.page_size })
    Object.assign(mutual, data, { loading: false })
  } catch (e) {
    mutual.loading = false
  }
}

function onTabClick(tab) {
  // 这里能打印出被点击的 pane name，便于确认点击事件触发
  console.log('tab-click:', tab?.props?.name)
}

watch(activeTab, (t) => {
  if (t === 'likes') loadLikes()
  if (t === 'mutual') loadMutual()
})

function goDisplay(id, newTab = false) {
  const resolved = router.resolve({ name: 'display', params: { uid: id } })
  if (newTab) {
    window.open(resolved.href, '_blank')
  } else {
    router.push(resolved)
  }
}


onMounted(() => {
  const init = String(route.query.tab || '')
  if (['recommend','likes','mutual','others'].includes(init)) {
    activeTab.value = init 
  }
})

  </script>
  
  <style scoped>
  /* —— 与 MainLayout.vue 保持一致的布局与样式 —— */
  .layout {
    display: flex;
    height: 100vh;
    background: #f8fafc;
  }
  .sidebar {
    width: 264px;
    padding: 14px;
    background: linear-gradient(180deg, #f8fafc, #ffffff);
    border-right: 1px solid #eef2f7;
  }
  .content {
    flex: 1;
    padding: 24px;
    overflow: auto;
  }
  .sidebar-card {
    border-radius: 18px;
    padding: 14px;
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: saturate(160%) blur(8px);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }
  .brand-title {
    font-weight: 600;
    color: #1f2937;
  }
  .brand-sub {
    color: #6b7280;
    font-size: 12px;
  }
  .pretty-menu {
    border-right: 0 !important;
    background: transparent !important;
    --menu-item-radius: 12px;
  }
  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    margin: 6px 0;
    border-radius: var(--menu-item-radius);
    font-weight: 500;
    color: #4b5563;
    transition: all 0.2s ease;
  }
  :deep(.el-menu-item:hover) {
    background: #f1f5f9;
  }
  :deep(.el-menu-item.is-active) {
    background: #eef2ff;
    color: #111827;
  }
  .topbar {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    margin-bottom: 16px;
  }
  .tabs {
    --el-tabs-header-height: 46px;
  }
.user-card { 
    margin-bottom: 16px; 
    border-radius: 12px; 
}
.user-card-head { 
    display: flex; 
    align-items: center; 
    gap: 12px; 
}
.meta .name { 
    font-weight: 600; 
}
.meta .sub { 
    font-size: 12px; 
    color: #6b7280; 
}
.tagline { 
    margin: 10px 0; 
    color: #374151; 
    min-height: 20px; 
}
.actions { 
    display: flex; 
    gap: 8px; 
}
.pager { 
    display: flex; 
    justify-content: center; 
    padding: 12px 0; 
}
.empty-line { 
    padding: 24px 0; 
}
.topbar { 
  position: relative; 
  z-index: 5; 
  background: #f8fafc; 
}
.content { 
  position: relative; 
  z-index: 1; 
}

  </style>
  