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
            <el-tab-pane label="喜欢你的人" name="likedMe"></el-tab-pane>
            <el-tab-pane label="您的喜欢" name="likes"></el-tab-pane>
            <el-tab-pane label="已双向匹配" name="mutual"></el-tab-pane>
            <el-tab-pane label="其他" name="others"></el-tab-pane>
          </el-tabs>
        </div>
  
        <!-- 为您推荐 -->
        <div v-if="activeTab === 'recommend'">
          <div class="toolbar">
            <el-select
              v-model="recommend.params.limit"
              size="small"
              style="width:100px"
              @change="() => { recommend.page = 1; loadRecommend() }"
            >
              <el-option :value="20" label="20条/页" />
              <el-option :value="40" label="40条/页" />
              <el-option :value="100" label="100条/页" />
            </el-select>
            <el-button size="small" @click="loadRecommend" :loading="recommend.loading">刷新推荐</el-button>
            <div class="hint">完善资料、上传清晰照片、通过认证可显著提升推荐质量</div>
          </div>


          <el-skeleton :loading="recommend.loading" animated :count="3">
            <template #template>
              <el-skeleton-item variant="image" style="width:100%;height:180px;border-radius:12px" />
              <div style="padding:10px 0">
                <el-skeleton-item variant="p" />
                <el-skeleton-item variant="text" />
              </div>
            </template>

            <template #default>
              <el-row :gutter="16">
                <el-col :span="6" v-for="u in recommend.items" :key="u.id">
                  <el-card shadow="hover" class="rec-card">
                    <div class="rec-cover">
                      <img :src="u.avatar_url || placeholder" alt="profile cover" loading="lazy" />
                      <div class="rec-score">综合 {{ toPct(u?.score ?? 0) }}%</div>
                    </div>

                    <div class="rec-body">
                      <div class="rec-head">
                        <div class="left">
                          <div class="name">{{ u.nickname || ('ID'+u.id) }}</div>
                          <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                        </div>
                        <div class="right">
                          <el-button size="small" @click="goDisplay_recommend(u.id)">查看资料</el-button>

                          <!-- 未喜欢且未匹配时，展示喜欢按钮 -->
                          <el-button
                            v-if="!u._liked && u.match_status !== 'matched'"
                            size="small"
                            type="danger"
                            plain
                            @click="onLike(u.id)"
                          >❤️ 喜欢</el-button>

                          <!-- 已喜欢但未匹配 -->
                          <el-tag v-else-if="u.match_status !== 'matched'" type="warning">已喜欢</el-tag>

                          <!-- 已匹配 -->
                          <el-tag v-else type="success">已匹配</el-tag>
                        </div>
                      </div>

                      <div class="tagline" v-if="u.tagline || u.bio">{{ u.tagline || u.bio }}</div>

                      <div class="signals">
                        <div class="sig">
                          <span>相似</span>
                          <el-progress :percentage="toPct(u.signals?.similarity)" :show-text="false" />
                        </div>
                        <div class="sig">
                          <span>互补</span>
                          <el-progress :percentage="toPct(u.signals?.complementarity)" :show-text="false" />
                        </div>
                        <div class="sig">
                          <span>意向</span>
                          <el-progress :percentage="toPct(u.signals?.intention_fit)" :show-text="false" />
                        </div>
                        <!-- 新增：生活 -->
                        <div class="sig">
                          <span>生活</span>
                          <el-progress :percentage="toPct(u.signals?.lifestyle)" :show-text="false" />
                        </div>
                        <!-- 新增：可信 -->
                        <div class="sig">
                          <span>可信</span>
                          <el-progress :percentage="toPct(u.signals?.trust_safety)" :show-text="false" />
                        </div>
                      </div>


                      <div class="reasons" v-if="u.reasons?.length">
                        <el-tag v-for="(r, idx) in u.reasons" :key="idx" size="small" effect="plain" class="mr8">
                          {{ r }}
                        </el-tag>
                      </div>
                      <div class="reason-summary" v-else>
                        {{ u.reason_summary || '多维度匹配度较高' }}
                      </div>
                    </div>
                  </el-card>
                </el-col>
              </el-row>

              <div v-if="!recommend.items.length" class="empty-line">
                <el-empty description="暂无推荐；建议补充资料、增加媒体并开启认证" />
              </div>

              <div class="pager" v-if="recommend.items.length">
                <el-pagination
                  background
                  layout="prev, pager, next"
                  :total="recommend.total"
                  :page-size="recommend.params.limit"
                  :current-page="recommend.page"
                  @current-change="(p)=>{ recommend.page = p; loadRecommend() }"
                />
              </div>
            </template>
          </el-skeleton>
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
                <el-col :span="6" v-for="u in likes.items" :key="u.id">
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
                      <el-tag v-if="u.match_status==='matched'" type="success">已匹配</el-tag>
                      <el-tag v-else type="warning">等待回应</el-tag>
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

        <!-- 喜欢您的人 -->
        <div v-else-if="activeTab === 'likedMe'">
            <el-skeleton :loading="likedMe.loading" animated :count="3">
            <template #template>
                <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
                <div style="padding:8px 0">
                <el-skeleton-item variant="p" />
                <el-skeleton-item variant="text" />
                </div>
            </template>
            <template #default>
                <el-row :gutter="16">
                <el-col :span="6" v-for="u in likedMe.items" :key="u.id">
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
                      <el-button size="small" @click="goDisplay_likedMe(u.id)">查看资料</el-button>
                      <el-button 
                        v-if="u.match_status==='waiting'" 
                        size="small" 
                        type="danger" 
                        plain 
                        @click="onLike(u.id)"
                      >❤️ 喜欢回去</el-button>
                      <el-tag v-else-if="u.match_status==='pending'" type="warning">已喜欢</el-tag>
                      <el-tag v-else-if="u.match_status==='matched'" type="success">已匹配</el-tag>
                    </div>
                    </el-card>
                </el-col>
                </el-row>
                <div v-if="!likedMe.items.length" class="empty-line">
                <el-empty description="暂无喜欢你的人" />
                </div>
                <div class="pager">
                <el-pagination
                    background
                    layout="prev, pager, next"
                    :total="likedMe.total"
                    :page-size="likedMe.page_size"
                    :current-page="likedMe.page"
                    @current-change="(p)=>{ likedMe.page=p; loadLikedMe() }"
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
                <el-col :span="6" v-for="u in mutual.items" :key="u.id">
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
import { getRecommendUsers, getMatchLikes, getMatchMutual, getLikedMe, likeUser } from '@/api'
import { ElMessage } from 'element-plus'


const router = useRouter()
const route = useRoute()
const defaultActive = ref('match') // 当前页高亮“匹配资料展示”
const activeTab = ref('recommend')

const likes = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const mutual = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const likedMe = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })

const recommend = reactive({
  items: [],
  loading: false,
  params: { limit: 20, min_completion: 0 }, // 默认 20
  page: 1,
  total: 0,
})

const placeholder = 'https://placehold.co/600x400?text=Profile'
const toPct = (x) => {
  const v = Number(x || 0)
  if (Number.isNaN(v)) return 0
  const p = Math.round(v * 100)
  return Math.max(0, Math.min(100, p))
}

const likedMap = reactive({})   
const matchedMap = reactive({}) 
function _clearObj(obj){ for (const k of Object.keys(obj)) delete obj[k] }



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

async function loadLikedMe() {
  try {
    likedMe.loading = true
    const { data } = await getLikedMe(uid, { page: likedMe.page, page_size: likedMe.page_size })
    Object.assign(likedMe, data, { loading: false })
  } catch (e) {
    likedMe.loading = false
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


async function refreshLikesCache() {
  try {
    const { data } = await getMatchLikes(uid, { page: 1, page_size: 1000 })
    _clearObj(likedMap)
    for (const it of (data?.items || [])) likedMap[it.id] = true
  } catch(e) { /* 忽略 */ }
}

async function refreshMutualCache() {
  try {
    const { data } = await getMatchMutual(uid, { page: 1, page_size: 1000 })
    _clearObj(matchedMap)
    for (const it of (data?.items || [])) matchedMap[it.id] = true
  } catch(e) { /* 忽略 */ }
}


async function loadRecommend() {
  recommend.loading = true
  try {
    const { data } = await getRecommendUsers(uid, {
      limit: recommend.params.limit,
      page: recommend.page,
      min_completion: recommend.params.min_completion
    })

    const items = Array.isArray(data?.items) ? data.items : []
    
    for (const it of items) {
      if (matchedMap[it.id]) {
        it.match_status = 'matched'
        it._liked = true
      } else if (likedMap[it.id]) {
        it.match_status = it.match_status || 'pending'
        it._liked = true
      } else {
        // 没有记录时，确保按钮出现
        it._liked = false
        if (!it.match_status) delete it.match_status
      }
    }

    // ✅ 兜底 total（后端若没给，就用其它字段或 items.length）
    const total =
      Number.isFinite(Number(data?.total)) ? Number(data.total) :
      Number.isFinite(Number(data?.count)) ? Number(data.count) :
      Number.isFinite(Number(data?.total_count)) ? Number(data.total_count) :
      Number(items.length) // 最差兜底：当前页条数

    recommend.items = items
    recommend.total = total

    console.log('recommend resp:', { total: data?.total, len: items.length, page: recommend.page, size: recommend.params.limit })
  } catch (e) {
    console.error('recommend api error:', e?.response?.status, e?.response?.data || e?.message)
    recommend.items = []
    recommend.total = 0
  } finally {
    recommend.loading = false
  }
}


async function onLike(targetId) {
  try {
    const { data } = await likeUser(uid, targetId)
    // 本地缓存先标记
    likedMap[targetId] = true
    if (data?.status === 'matched') matchedMap[targetId] = true

    // 更新当前推荐卡片的本地状态
    const it = recommend.items.find(x => x.id === targetId)
    if (it) {
      it._liked = true
      if (data?.status === 'matched') {
        it.match_status = 'matched'
      } else {
        // 后端返回 pending 时，前端用 'pending' 统一标记“已喜欢”
        it.match_status = it.match_status || 'pending'
      }
    }

    // 根据返回结果刷新其他列表（后端之前给过 refresh 提示也可用）
    if (data?.status === 'matched') {
      ElMessage.success('🎉 已互相喜欢，已加入双向匹配')
      loadMutual()
    } else {
      ElMessage.success('已发送喜欢')
    }
    loadLikes()
    loadLikedMe()

    // 如果你希望“为您推荐”整个列表也重新拉取（非必须）：
    // await loadRecommend()

  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  }
}

watch(activeTab, async (t) => {
  if (t === 'recommend') {
    await Promise.all([refreshLikesCache(), refreshMutualCache()])
    await loadRecommend()
  }
  if (t === 'likes') loadLikes()
  if (t === 'mutual') loadMutual()
  if (t === 'likedMe') loadLikedMe()
})

function goDisplay(id, newTab = false) {
  const resolved = router.resolve({ name: 'display', params: { uid: id } })
  if (newTab) {
    window.open(resolved.href, '_blank')
  } else {
    router.push(resolved)
  }
}

function goDisplay_likedMe(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayLiked', params: { uid: id } })
  if (newTab) window.open(resolved.href, '_blank')
  else router.push(resolved)
}

function goDisplay_recommend(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayRecommend', params: { uid: id } })
  if (newTab) window.open(resolved.href, '_blank')
  else router.push(resolved)
}


onMounted(async () => {
  const init = String(route.query.tab || '')
  if (['recommend','likedMe','likes','mutual','others'].includes(init)) {
    activeTab.value = init 
  }
  // 先建缓存，再拉推荐，保证回显
  await Promise.all([refreshLikesCache(), refreshMutualCache()])

  if (activeTab.value === 'recommend') {
    await loadRecommend()
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
.toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
}
.toolbar .hint {
  font-size: 12px; color: #6b7280;
}
.rec-card { border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.rec-cover { position: relative; width: 100%; height: 180px; overflow: hidden; border-radius: 10px; }
.rec-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rec-badges { position: absolute; left: 8px; top: 8px; display: flex; gap: 6px; }
.rec-score { position: absolute; right: 8px; bottom: 8px; font-size: 12px; background: rgba(17,24,39,0.72); color: #fff; padding: 4px 8px; border-radius: 10px; }
.rec-body { padding: 10px 2px 2px; }
.rec-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.rec-head .name { font-weight: 600; }
.rec-head .sub { color: #6b7280; font-size: 12px; margin-top: 2px; }
.signals { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; margin-top: 8px; }
.sig { display: grid; grid-template-columns: 40px 1fr; align-items: center; gap: 8px; font-size: 12px; color: #6b7280; }
.reasons { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.mr8 { margin-right: 8px; }
.reason-summary { margin-top: 8px; color: #374151; font-size: 13px; }


  </style>
  