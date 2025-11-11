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
    <main class="content" ref="contentRef">
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

                        <!-- 喜欢按钮 / 状态 -->
                        <el-button
                          v-if="!u._liked && u.match_status !== 'matched'"
                          size="small"
                          type="danger"
                          plain
                          @click="onLike(u.id, 'recommend')"
                        >❤️ 喜欢</el-button>

                        <el-tag v-else-if="u.match_status !== 'matched'" type="warning">已喜欢</el-tag>
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
                      <div class="sig">
                        <span>生活</span>
                        <el-progress :percentage="toPct(u.signals?.lifestyle)" :show-text="false" />
                      </div>
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
                      @click="onLike(u.id, 'likedMe')"
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
                    <el-button size="small" type="primary" @click="onStartChat(u.id)">发起聊天</el-button>
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
      
      <ForcedAdDialog
        v-model="showGate"
        :ad="chatAd"
        :seconds="requiredSeconds"
        :vip-plus="vipPlus"
        @finished="handleGateFinished"
        @see="handleGateSeeAd"
      />

      <!-- 广告弹窗：让组件内部自己执行跳转，避免父子重复导航 -->
      <LikeAdDialog
        v-model="showAd"
        :ad="currentAd"
        :from="activeTab"
        @see="(ad) => goSeeAd(router, ad, activeTab)"
      />
      
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Setting } from '@element-plus/icons-vue'
import { getRecommendUsers, getMatchLikes, getMatchMutual, getLikedMe } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLikeWithAd } from '@/composables/useLikeWithAd.js'   // ⬅️ 只引入 hook，不再引入 goSeeAd
import LikeAdDialog from '@/components/LikeAdDialog.vue'

import ForcedAdDialog from '@/components/ForcedAdDialog.vue'
import { useAdGateForChat} from '@/composables/useAdGateForChat'

const router = useRouter()
const route = useRoute()
const defaultActive = ref('match')
const activeTab = ref('recommend')

const likes = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const mutual = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const likedMe = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })

const recommend = reactive({
  items: [],
  loading: false,
  params: { limit: 20, min_completion: 0 },
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

const contentRef = ref(null)
const uid = Number(localStorage.getItem('uid') || 1)

const onSelect = (key) => {
  if (key === 'display') router.push('/main')
  else if (key === 'match') router.push('/match')
}

function onTabClick(tab) {
  console.log('tab-click:', tab?.props?.name)
}

/** ============= 新版点赞 + 广告（强制来自后端，自动轮换） ============= */
const {
  showAd, currentAd, likeThenMaybeAd, closeAd, lastLikeResult, goSeeAd,
} = useLikeWithAd({
  enforceAd: true,   // 点赞必须返回广告；若后端没带，则前端调用 pick 接口
  autoRotate: true,  // 如果给到的 id 与“本会话已看”重复，会自动向后端再 pick
  limit: 1000
})

const likeLoading = ref(new Set())
const lastLikeFrom = ref('recommend') // 记录本次点赞来源 tab

async function onLike(targetId, from = '') {
  if (likeLoading.value.has(targetId)) return
  likeLoading.value.add(targetId)
  try {
    // 1) 点赞（后端 upsert Like + 自动 Match），hook 内部会拿/轮换广告
    const { adOpened, result } = await likeThenMaybeAd(uid, targetId)

    // 2) 精确刷新
    await refreshByKeys(result?.refresh || [])

    // 3) 回显状态
    markRecommendCard(targetId, result?.status)

    // 4) 打开弹窗（只在确实拿到广告时）
    lastLikeFrom.value = from || activeTab.value || 'recommend'
    if (adOpened && currentAd.value) {
      showAd.value = true
    } else {
      ElMessage.warning('暂时没有可展示的活动')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  } finally {
    likeLoading.value.delete(targetId)
  }
}
/** ========================================= */

async function loadLikes() {
  try {
    likes.loading = true
    const { data } = await getMatchLikes(uid, { page: likes.page, page_size: likes.page_size })
    Object.assign(likes, data, { loading: false })
  } catch (e) {
    likes.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function loadLikedMe() {
  try {
    likedMe.loading = true
    const { data } = await getLikedMe(uid, { page: likedMe.page, page_size: likedMe.page_size })
    Object.assign(likedMe, data, { loading: false })
  } catch (e) {
    likedMe.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function loadMutual() {
  try {
    mutual.loading = true
    const { data } = await getMatchMutual(uid, { page: mutual.page, page_size: mutual.page_size })
    Object.assign(mutual, data, { loading: false })
  } catch (e) {
    mutual.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function refreshByKeys(keys = []) {
  const todo = new Set(keys)
  const tasks = []
  if (todo.has('likes'))   tasks.push(loadLikes())
  if (todo.has('likedMe')) tasks.push(loadLikedMe())
  if (todo.has('mutual'))  tasks.push(loadMutual())
  if (!tasks.length) tasks.push(loadLikes())
  await Promise.all(tasks)
}

async function refreshLikesCache() {
  try {
    const { data } = await getMatchLikes(uid, { page: 1, page_size: 1000 })
    _clearObj(likedMap)
    const arr = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
    for (const it of arr) {
      const id = extractUserId(it)
      if (!Number.isNaN(id)) likedMap[id] = true
    }
  } catch(e) {}
}

async function refreshMutualCache() {
  try {
    const { data } = await getMatchMutual(uid, { page: 1, page_size: 1000 })
    _clearObj(matchedMap)
    const arr = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
    for (const it of arr) {
      const id = extractUserId(it)
      if (!Number.isNaN(id)) matchedMap[id] = true
    }
  } catch(e) {}
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

    // 按综合分降序
    items.sort((a, b) => (b?.score || 0) - (a?.score || 0))

    // 回填喜欢/匹配状态
    hydrateFlags(items)

    // total 兜底
    const total =
      Number.isFinite(Number(data?.total)) ? Number(data.total) :
      Number.isFinite(Number(data?.count)) ? Number(data.count) :
      Number.isFinite(Number(data?.total_count)) ? Number(data.total_count) :
      Number(items.length)

    recommend.items = items
    recommend.total = total
  } catch (e) {
    console.error('recommend api error:', e?.response?.status, e?.response?.data || e?.message)
    recommend.items = []
    recommend.total = 0
  } finally {
    recommend.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

function hydrateFlags(list) {
  for (const it of list) {
    if (matchedMap[it.id]) {
      it.match_status = 'matched'
      it._liked = true
    } else if (likedMap[it.id]) {
      it.match_status = it.match_status || 'pending'
      it._liked = true
    } else {
      it._liked = false
      if (!it.match_status) delete it.match_status
    }
  }
}

// 点赞后就地把推荐卡片标成“已喜欢/已匹配”
function markRecommendCard(targetId, status) {
  const it = recommend.items.find(x => x.id === targetId)
  if (!it) return
  it._liked = true
  if (status === 'matched' || status === 'already_matched') {
    it.match_status = 'matched'
    matchedMap[targetId] = true
  } else {
    it.match_status = it.match_status || 'pending'
    likedMap[targetId] = true
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
  await nextTick()
  scrollListToTop(false)
})

function goDisplay(id, newTab = false) {
  const resolved = router.resolve({ name: 'display', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}
function goDisplay_likedMe(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayLiked', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}
function goDisplay_recommend(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayRecommend', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}

function scrollListToTop(smooth = false) {
  const el = contentRef.value
  if (!el) return
  if ('scrollTo' in el) {
    el.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' })
  } else {
    el.scrollTop = 0
  }
}

// 通用提取 id
function extractUserId(it) {
  const cand = [it?.id, it?.uid, it?.user_id, it?.likee_id, it?.target_id, it?.user_b, it?.user?.id, it?.profile?.user_id]
  for (const v of cand) {
    const n = Number(v)
    if (!Number.isNaN(n)) return n
  }
  return NaN
}

// —— 发起聊天 · 15 秒强制广告闸门 ——
// 用别名避免与点赞广告的 showAd/currentAd 冲突
const {
  showGate,
  chatAd,
  requiredSeconds,
  vipPlus,
  openAdBeforeChat,
  handleGateFinished,
  handleGateSeeAd,
} = useAdGateForChat(router)

const pendingChatUserId = ref(null)

// 点击“发起聊天” => 先尝试打开广告闸门；如果没有广告则直接放行
async function onStartChat(userId) {
  pendingChatUserId.value = userId
  // print("meId",meId)
  const intercepted = openAdBeforeChat(userId, { meId: uid })

  // if (!intercepted) {
  //   // router.push({ path: '/chat', query: { with: userId } })
  //   router.push({ path: `/chat/${userId}` })
  // }
}

// 15 秒观看完成后触发
function onChatAdFinished() {
  const id = pendingChatUserId.value
  pendingChatUserId.value = null
  closeGate()
  if (id) router.push({ path: '/chat', query: { with: id } })
}

async function onChatSkip() {
  try {
    await ElMessageBox.confirm(
      '跳过广告需开通 VIP+，是否前往开通？',
      '需要会员',
      { type: 'warning', confirmButtonText: '去开通', cancelButtonText: '再想想' }
    )
    closeGate()
    await router.push('/vip-plus')
  } catch { /* 用户点取消 */ }
}

function onChatAdSee() {
  const d = chatAd.value
  if (!d) return

  closeGate() // 先关弹窗

  // 统一读取跳转字段，兜底 /ad/:id
  let dest = d.destination || d.route || d.url || d.link || (d.id ? `/ad/${d.id}` : '')
  if (!dest) return

  const isExternal = /^https?:\/\//i.test(dest)
  if (isExternal) {
    try {
      const u = new URL(dest)
      if (!u.searchParams.has('from')) u.searchParams.set('from', 'mutual')
      window.location.href = u.toString()
    } catch {
      // 非法 URL 字符串就直接整页跳
      window.location.href = dest
    }
  } else {
    if (!dest.startsWith('/')) dest = '/' + dest
    router.push({ path: dest, query: { from: 'mutual' } }).catch(() => {})
  }
}


// 你的原始跳转逻辑保持一致（你之前是跳到 /display/:id）
function goChat(otherId) {
  router.push(`/display/${otherId}`)
}

onMounted(async () => {
  const init = String(route.query.tab || '')
  if (['recommend','likedMe','likes','mutual','others'].includes(init)) {
    activeTab.value = init
  }
  await Promise.all([refreshLikesCache(), refreshMutualCache()])
  if (activeTab.value === 'recommend') {
    await loadRecommend()
  } else if (activeTab.value === 'likes') {
    await loadLikes()
  } else if (activeTab.value === 'likedMe') {
    await loadLikedMe()
  } else if (activeTab.value === 'mutual') {
    await loadMutual()
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
