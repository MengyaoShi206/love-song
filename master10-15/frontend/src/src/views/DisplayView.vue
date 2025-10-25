<template>
    <div class="layout">
      <!-- 左侧菜单（与 Main/Match 保持一致） -->
      <aside class="sidebar">
        <el-card class="sidebar-card" shadow="never">
          <div class="brand-meta">
            <div class="brand-title">资料详情</div>
            <div class="brand-sub">查看对方公开资料</div>
          </div>
  
          <el-menu :default-active="'display'" class="pretty-menu" @select="onSelect" :router="false">
            <el-menu-item index="display"><el-icon><User /></el-icon><span>资料展示</span></el-menu-item>
          </el-menu>
        </el-card>
      </aside>
  
      <!-- 右侧内容 -->
      <main class="content">
        <!-- 顶部栏：头像 + 名称 + 右上角返回 -->
        <div class="topbar">
          <div class="topbar-left">
            <el-avatar :size="56" :src="ua.avatar_url || ''" />
            <div class="meta">
              <div class="name">{{ ua.nickname || ua.username || '—' }}</div>
              <div class="sub">{{ [ua.city, ua.gender].filter(Boolean).join(' · ') }}</div>
            </div>
          </div>
          <div class="topbar-actions">
            <el-button type="primary" @click="goBackLikes">返回“您的喜欢”</el-button>
          </div>
        </div>
  
        <!-- 1. 基础信息（不展示手机号/邮箱） -->
        <el-card shadow="never" class="section">
          <template #header>基础信息</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">{{ ua.username || '—' }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ ua.nickname || '—' }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ ua.gender || '—' }}</el-descriptions-item>
            <el-descriptions-item label="城市">{{ ua.city || '—' }}</el-descriptions-item>
            <el-descriptions-item label="头像链接">
              <a v-if="ua.avatar_url" :href="ua.avatar_url" target="_blank" rel="noopener">{{ ua.avatar_url }}</a>
              <span v-else>—</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
  
        <!-- 2. 公开资料 -->
        <el-card shadow="never" class="section">
          <template #header>公开资料</template>
          <div class="mb-2"><b>个性签名：</b>{{ up.tagline || '—' }}</div>
          <div class="mb-1"><b>自我介绍：</b></div>
          <div class="bio">{{ up.bio || '—' }}</div>
        </el-card>
  
        <!-- 3. 择偶意向 -->
        <el-card shadow="never" class="section">
          <template #header>择偶意向</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="感情目标">{{ ui.relationship_goal || '—' }}</el-descriptions-item>
            <el-descriptions-item label="年龄">
              <span>{{ numOrDash(ui.preferred_age_min) }} - {{ numOrDash(ui.preferred_age_max) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="身高">
              <span>{{ numOrDash(ui.preferred_height_min) }} - {{ numOrDash(ui.preferred_height_max) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="偏好城市">
              {{ displayCities(ui.preferred_cities) }}
            </el-descriptions-item>
            <el-descriptions-item label="接受异地">{{ yn(ui.accept_long_distance) }}</el-descriptions-item>
            <el-descriptions-item label="接受离异">{{ yn(ui.accept_divorce) }}</el-descriptions-item>
            <el-descriptions-item label="接受子女">{{ yn(ui.accept_children) }}</el-descriptions-item>
            <el-descriptions-item label="结婚期望">{{ ui.marriage_timeline || '—' }}</el-descriptions-item>
            <el-descriptions-item label="生育计划">{{ ui.child_plan || '—' }}</el-descriptions-item>
            <el-descriptions-item label="宗教信仰">{{ ui.religion || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
  
        <!-- 4. 生活方式 -->
        <el-card shadow="never" class="section">
          <template #header>生活方式</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="作息">{{ ul.schedule || '—' }}</el-descriptions-item>
            <el-descriptions-item label="饮酒">{{ ul.drinking || '—' }}</el-descriptions-item>
            <el-descriptions-item label="吸烟">{{ ul.smoking || '—' }}</el-descriptions-item>
            <el-descriptions-item label="锻炼">{{ ul.workout_freq || '—' }}</el-descriptions-item>
            <el-descriptions-item label="饮食">{{ ul.diet || '—' }}</el-descriptions-item>
            <el-descriptions-item label="宠物">{{ ul.pet_view || '—' }}</el-descriptions-item>
            <el-descriptions-item label="性格">{{ ul.personality || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
  
        <!-- 5. 问答展示 -->
        <el-card shadow="never" class="section">
          <template #header>问答展示</template>
          <div v-if="qna.length">
            <div v-for="(qa, i) in qna" :key="i" class="qna-item">
              <b>Q{{ i + 1 }}：{{ qa.question }}</b>
              <p>A：{{ qa.answer || '—' }}</p>
            </div>
          </div>
          <el-empty v-else description="暂无公开问答" />
        </el-card>
      </main>
    </div>
  </template>
  
  <script setup>
  import { reactive, computed, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { User, Setting } from '@element-plus/icons-vue'
  import { getDisplay } from '@/api'
  
  const route = useRoute()
  const router = useRouter()
  const viewedUid = Number(route.params.uid)
  
  const display = reactive({
    user_account: {},
    user_profile_public: {},
    user_intention: {},
    user_lifestyle: {},
    user_qna: []
  })
  
  const ua = computed(() => display.user_account || {})
  const up = computed(() => display.user_profile_public || {})
  const ui = computed(() => display.user_intention || {})
  const ul = computed(() => display.user_lifestyle || {})
  const qna = computed(() => display.user_qna || [])
  
  function yn(v) {
    if (v === true || v === 1 || v === '1' || v === 'true') return '是'
    if (v === false || v === 0 || v === '0' || v === 'false') return '否'
    return '—'
  }
  function numOrDash(v) {
    return (v === 0 || v) ? v : '—'
  }
  function displayCities(v) {
    if (!v) return '—'
    try {
      const arr = typeof v === 'string' ? JSON.parse(v) : v
      if (Array.isArray(arr)) return arr.join('、')
    } catch (e) {}
    return String(v)
  }
  
  function onSelect(key) {
    if (key === 'display') router.push('/main')
    if (key === 'match') router.push('/match')
  }
  
  function goBackLikes() {
    router.push({ path: '/match', query: { tab: 'likes' } })
  }
  
  async function load() {
    const { data } = await getDisplay(viewedUid)
    Object.assign(display, data || {})
  }
  onMounted(load)
  </script>
  
  <style scoped>
  .layout { display:flex; height:100vh; background:#f8fafc; }
  .sidebar { width:264px; padding:14px; background:linear-gradient(180deg,#f8fafc,#ffffff); border-right:1px solid #eef2f7; }
  .content { flex:1; padding:24px; overflow:auto; }
  .sidebar-card { border-radius:18px; padding:14px; background:rgba(255,255,255,.8); backdrop-filter:saturate(160%) blur(8px); box-shadow:0 12px 30px rgba(15,23,42,.06); }
  .brand-title { font-weight:600; color:#1f2937; }
  .brand-sub { color:#6b7280; font-size:12px; }
  .pretty-menu { border-right:0 !important; background:transparent !important; --menu-item-radius:12px; }
  :deep(.el-menu-item){ height:44px; line-height:44px; margin:6px 0; border-radius:var(--menu-item-radius); font-weight:500; color:#4b5563; transition:all .2s; }
  :deep(.el-menu-item:hover){ background:#f1f5f9; }
  :deep(.el-menu-item.is-active){ background:#eef2ff; color:#111827; }
  .topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
  .topbar-left { display:flex; align-items:center; gap:12px; }
  .meta .name { font-weight:700; }
  .meta .sub { color:#6b7280; font-size:12px; }
  .section { margin-bottom:16px; }
  .bio { margin-top:6px; background:#f9fafb; padding:10px; border-radius:8px; }
  .qna-item { background:#f9fafb; padding:8px 10px; border-radius:8px; margin-bottom:10px; }
  </style>
  