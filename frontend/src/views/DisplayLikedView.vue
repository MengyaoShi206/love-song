<template>
  <div class="layout">
    <!-- 左侧菜单 -->
    <aside class="sidebar">
      <el-card class="sidebar-card" shadow="never">
        <div class="brand-meta">
          <div class="brand-title">资料详情</div>
          <div class="brand-sub">来自“喜欢你的人”</div>
        </div>

        <el-menu :default-active="'displayLiked'" class="pretty-menu" @select="onSelect" :router="false">
          <el-menu-item index="displayLiked">
            <el-icon><User /></el-icon><span>资料展示</span>
          </el-menu-item>
        </el-menu>
      </el-card>
    </aside>

    <!-- 右侧 -->
    <main class="content" ref="contentRef">
      <!-- 顶部栏 -->
      <div class="topbar">
        <div class="topbar-left">
          <el-skeleton :loading="loading" :rows="1" animated style="--el-skeleton-circle-size:56px">
            <template #template>
              <el-skeleton-item variant="circle" style="width:56px;height:56px" />
              <div style="margin-left:12px">
                <el-skeleton-item variant="h3" style="width:180px" />
                <el-skeleton-item variant="text" style="width:120px;margin-top:8px" />
              </div>
            </template>
            <template #default>
              <el-avatar :size="56" :src="ua.avatar_url || ''" />
              <div class="meta">
                <div class="name">{{ ua.nickname || ua.username || '—' }}</div>
                <div class="sub">{{ [ua.city, ua.gender].filter(Boolean).join(' · ') }}</div>
              </div>
            </template>
          </el-skeleton>
        </div>

        <div class="topbar-actions">
          <el-button type="primary" @click="goBackLikedMe">返回“喜欢你的人”</el-button>

          <template v-if="!loading">
            <!-- 一定用当前看的这个人 viewedUid -->
            <el-button
              v-if="!likedFlag && matchStatus !== 'matched'"
              type="danger"
              plain
              @click="onLikeBtnClick"
              style="margin-left:8px"
            >❤️ 喜欢</el-button>

            <el-tag v-else-if="matchStatus !== 'matched'" type="warning" style="margin-left:8px">已喜欢</el-tag>
            <el-tag v-else type="success" style="margin-left:8px">已匹配</el-tag>
          </template>
        </div>
      </div>

      <!-- ====== 下面都是展示块 ====== -->

      <!-- 1. 基础信息 -->
      <el-card shadow="never" class="section">
        <template #header>基础信息</template>
        <el-skeleton :loading="loading" animated :rows="4">
          <template #default>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户名">{{ ua.username || '—' }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ ua.nickname || '—' }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ ua.gender || '—' }}</el-descriptions-item>
              <el-descriptions-item label="城市">{{ ua.city || '—' }}</el-descriptions-item>
              <el-descriptions-item label="生日">{{ ua.birth_date || '—' }}</el-descriptions-item>
              <el-descriptions-item label="身高">{{ ua.height_cm || '—' }}</el-descriptions-item>
              <el-descriptions-item label="体重">{{ ua.weight_kg || '—' }}</el-descriptions-item>
              <el-descriptions-item label="家乡">{{ ua.hometown || '—' }}</el-descriptions-item>
              <el-descriptions-item label="感情状态">{{ ua.marital_status || '—' }}</el-descriptions-item>
              <el-descriptions-item label="是否有子女">{{ ua.has_children || '—' }}</el-descriptions-item>
              <el-descriptions-item label="头像链接">
                <a v-if="ua.avatar_url" :href="ua.avatar_url" target="_blank" rel="noopener">{{ ua.avatar_url }}</a>
                <span v-else>—</span>
              </el-descriptions-item>
            </el-descriptions>
          </template>
        </el-skeleton>
      </el-card>

      <!-- 2. 公开资料 -->
      <el-card shadow="never" class="section">
        <template #header>公开资料</template>
        <el-skeleton :loading="loading" animated :rows="3">
          <template #default>
            <div class="mb-2"><b>个性签名：</b>{{ up.tagline || '—' }}</div>
            <div class="mb-1"><b>自我介绍：</b></div>
            <div class="bio">{{ up.bio || '—' }}</div>
          </template>
        </el-skeleton>
      </el-card>

      <!-- 3. 择偶意向 -->
      <el-card shadow="never" class="section">
        <template #header>择偶意向</template>
        <el-skeleton :loading="loading" animated :rows="4">
          <template #default>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="感情目标">{{ ui.relationship_goal || '—' }}</el-descriptions-item>
              <el-descriptions-item label="年龄">
                <span>{{ numOrDash(ui.preferred_age_min) }} - {{ numOrDash(ui.preferred_age_max) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="身高">
                <span>{{ numOrDash(ui.preferred_height_min) }} - {{ numOrDash(ui.preferred_height_max) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="偏好城市">{{ displayCities(ui.preferred_cities) }}</el-descriptions-item>
              <el-descriptions-item label="接受异地">{{ yn(ui.accept_long_distance) }}</el-descriptions-item>
              <el-descriptions-item label="接受离异">{{ yn(ui.accept_divorce) }}</el-descriptions-item>
              <el-descriptions-item label="接受子女">{{ yn(ui.accept_children) }}</el-descriptions-item>
              <el-descriptions-item label="结婚期望">{{ ui.marriage_timeline || '—' }}</el-descriptions-item>
              <el-descriptions-item label="生育计划">{{ ui.child_plan || '—' }}</el-descriptions-item>
              <el-descriptions-item label="宗教信仰">{{ ui.religion || '—' }}</el-descriptions-item>
              <el-descriptions-item label="家庭观">{{ ui.family_view || '—' }}</el-descriptions-item>
            </el-descriptions>
          </template>
        </el-skeleton>
      </el-card>

      <!-- 4. 生活方式 -->
      <el-card shadow="never" class="section">
        <template #header>生活方式</template>
        <el-skeleton :loading="loading" animated :rows="3">
          <template #default>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="作息">{{ ul.schedule || '—' }}</el-descriptions-item>
              <el-descriptions-item label="饮酒">{{ ul.drinking || '—' }}</el-descriptions-item>
              <el-descriptions-item label="吸烟">{{ ul.smoking || '—' }}</el-descriptions-item>
              <el-descriptions-item label="锻炼">{{ ul.workout_freq || '—' }}</el-descriptions-item>
              <el-descriptions-item label="饮食">{{ ul.diet || '—' }}</el-descriptions-item>
              <el-descriptions-item label="宠物">{{ ul.pet_view || '—' }}</el-descriptions-item>
              <el-descriptions-item label="消费观">{{ ul.spending_view || '—' }}</el-descriptions-item>
              <el-descriptions-item label="储蓄观">{{ ul.saving_view || '—' }}</el-descriptions-item>
              <el-descriptions-item label="旅行偏好">{{ ul.travel_pref || '—' }}</el-descriptions-item>
              <el-descriptions-item label="兴趣标签">{{ ul.interests || '—' }}</el-descriptions-item>
              <el-descriptions-item label="性格">{{ ul.personality || '—' }}</el-descriptions-item>
            </el-descriptions>
          </template>
        </el-skeleton>
      </el-card>

      <!-- 5. 问答展示 -->
      <el-card shadow="never" class="section">
        <template #header>问答展示</template>
        <el-skeleton :loading="loading" animated :rows="4">
          <template #default>
            <div v-if="qna.length">
              <div v-for="(qa, i) in qna" :key="i" class="qna-item">
                <b>Q{{ i + 1 }}：{{ qa.question }}</b>
                <p>A：{{ qa.answer || '—' }}</p>
              </div>
            </div>
            <el-empty v-else description="暂无公开问答" />
          </template>
        </el-skeleton>
      </el-card>

      <!-- 6. 相册 -->
      <el-card shadow="never" class="section">
        <template #header>相册</template>
        <template v-if="Array.isArray(medias) && medias.length">
          <div class="media-grid">
            <el-image
              v-for="(m, i) in medias"
              :key="m.id || i"
              :src="m.thumb_url || m.url"
              :preview-src-list="mediaUrls"
              :initial-index="i"
              fit="cover"
              class="media-item"
              :preview-teleported="true"
            >
              <template #error>
                <div class="image-slot">加载失败</div>
              </template>
            </el-image>
          </div>
        </template>
        <el-empty v-else description="暂无相册" />
      </el-card>

      <!-- 7. 认证与安全 -->
      <el-card shadow="never" class="section">
        <template #header>认证与安全</template>
        <template v-if="hasVerifyOrRisk">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="认证状态">
              {{ verifyStatusText(verification.status) }}
            </el-descriptions-item>
            <el-descriptions-item label="认证备注">{{ verification.reason || '—' }}</el-descriptions-item>
            <el-descriptions-item label="风控得分">{{ risk.score ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="风控动作">{{ riskActionText(risk.action) }}</el-descriptions-item>
            <el-descriptions-item label="风控到期">{{ fmtTs(risk.expire_at) }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <el-empty v-else description="暂无认证/风控信息" />
      </el-card>

      <!-- 错误提示 -->
      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        class="section"
        :closable="false"
      />

      <!-- ✅ 广告弹窗：必弹 + 带来源 -->
      <LikeAdDialog
        v-model="showAd"
        :ad="currentAd"
        from="likedMe"
        @close="onAdClose"
        @see="onAdSee"
      />
    </main>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User } from '@element-plus/icons-vue'
import { getDisplay, getMatchLikes, getMatchMutual, getLikedMe } from '@/api'
import LikeAdDialog from '@/components/LikeAdDialog.vue'
import { useLikeWithAd } from '@/composables/useLikeWithAd.js'
import { goSeeAd } from '@/composables/useLikeWithAd.js' // ⚠️ 单独导入

const route = useRoute()
const router = useRouter()

const viewedUid = ref(Number(route.params.uid))
const uid = Number(sessionStorage.getItem('uid') || 0)


const display = reactive({
  user_account: {},
  user_profile_public: {},
  user_intention: {},
  user_lifestyle: {},
  user_qna: [],
  user_medias: [],
  verification: {},
  risk: {}
})

const ua  = computed(() => display.user_account || {})
const up  = computed(() => display.user_profile_public || {})
const ui  = computed(() => display.user_intention || {})
const ul  = computed(() => display.user_lifestyle || {})
const qna = computed(() => display.user_qna || [])

const medias = computed(() => Array.isArray(display.user_medias) ? display.user_medias : [])
const mediaUrls = computed(() => medias.value.map(m => m?.url).filter(Boolean))
const verification = computed(() => display.verification || {})
const risk = computed(() => display.risk || {})

const loading   = ref(false)
const errorMsg  = ref('')
const contentRef = ref(null)

const likedFlag   = ref(false)
const matchStatus = ref('')   // '' | 'pending' | 'matched'
const likedMeList = ref([])

// === ✅ 新版“广告+喜欢”组合式（强制弹窗 + 兜底） ===
const {
  showAd,           // 控制弹窗
  currentAd,        // 当前广告
  likeThenMaybeAd,  // 先 like 再可选弹广告
  closeAd,          // 关窗
  lastLikeResult,   // 最近一次 like 的返回
} = useLikeWithAd({
  limit: 50,
  enforceAd: true, // **强制**每次点赞都弹广告
  fallbackAd: { id: 1, destination: '/ad/1', title: '精选推荐' }
})

function extractUserId(it) {
  const cand = [
    it?.id, it?.uid, it?.user_id, it?.likee_id, it?.target_id, it?.user_b,
    it?.user?.id, it?.profile?.user_id
  ]
  for (const v of cand) {
    const n = Number(v)
    if (!Number.isNaN(n)) return n
  }
  return NaN
}

function yn(v) {
  if (v === true || v === 1 || v === '1' || String(v).toLowerCase() === 'true') return '是'
  if (v === false || v === 0 || v === '0' || String(v).toLowerCase() === 'false') return '否'
  return '—'
}
function numOrDash(v) { return (v === 0 || v) ? v : '—' }
function displayCities(v) {
  if (!v) return '—'
  try {
    const arr = typeof v === 'string' ? JSON.parse(v) : v
    if (Array.isArray(arr)) return arr.join('、')
  } catch (e) {}
  return String(v)
}
function fmtTs(s) {
  if (!s) return '—'
  try {
    const t = String(s)
    return t.length > 19 ? t.slice(0, 19).replace('T', ' ') : t.replace('T', ' ')
  } catch { return String(s) }
}
function verifyStatusText(s) {
  const mapNum = { 0: '待审', 1: '通过', 2: '拒绝', 3: '复审中' }
  if (s === null || s === undefined || s === '') return '—'
  const n = Number(s)
  if (!Number.isNaN(n) && n in mapNum) return mapNum[n]
  const str = String(s).toLowerCase()
  const mapStr = { pending: '待审', approved: '通过', rejected: '拒绝', review: '复审中' }
  return mapStr[str] || String(s)
}
function riskActionText(a) {
  const map = { 0: '无', 1: '限流', 2: '限聊', 3: '封禁' }
  if (a === null || a === undefined || a === '') return '—'
  const n = Number(a)
  if (!Number.isNaN(n) && n in map) return map[n]
  const str = String(a).toLowerCase()
  const mapStr = { none: '无', throttle: '限流', limit_chat: '限聊', ban: '封禁' }
  return mapStr[str] || String(a)
}

function normalizeDisplayPayload(raw) {
  const data = raw || {}
  const medias = data.user_medias || data.user_media || data.medias || []
  const safeMedias = Array.isArray(medias)
    ? medias.map((m, i) => ({
        id: m?.id ?? i,
        media_type: m?.media_type ?? 'photo',
        url: m?.url ?? '',
        thumb_url: m?.thumb_url ?? '',
        audit_status: m?.audit_status ?? m?.status ?? 'approved',
        sort_order: m?.sort_order ?? i,
        created_at: m?.created_at ?? null,
        updated_at: m?.updated_at ?? null
      }))
    : []
  const v = data.verification || {}
  const verification = {
    status: v.status ?? v.state ?? '',
    reason: v.reason ?? v.note ?? '',
    created_at: v.created_at ?? null,
    updated_at: v.updated_at ?? null
  }
  const r = data.risk || {}
  const risk = {
    score: r.score ?? r.level ?? undefined,
    action: r.action ?? r.policy ?? undefined,
    expire_at: r.expire_at ?? null,
    created_at: r.created_at ?? null
  }
  return { ...data, user_medias: safeMedias, verification, risk }
}

const hasVerifyOrRisk = computed(() => {
  const v = verification.value
  const r = risk.value
  const hasV = v && (v.status != null && v.status !== '')
  const hasR = r && (r.score != null || r.action != null || r.level != null)
  return !!(hasV || hasR)
})

function onSelect(key) {
  if (key === 'displayLiked') router.push({ path: '/match', query: { tab: 'likedMe' } })
}
function goBackLikedMe() {
  router.push({ path: '/match', query: { tab: 'likedMe' } })
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await getDisplay(viewedUid.value)
    const norm = normalizeDisplayPayload(data || {})
    Object.assign(display, {
      ...norm,
      user_medias: norm.user_medias || [],
      verification: norm.verification || {},
      risk: norm.risk || {}
    })
  } catch (e) {
    errorMsg.value = '加载资料失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

async function refreshLikeStates() {
  try {
    const [likesRes, mutualRes] = await Promise.all([
      getMatchLikes(uid, { page: 1, page_size: 1000 }),
      getMatchMutual(uid, { page: 1, page_size: 1000 })
    ])
    const likesRaw  = Array.isArray(likesRes?.data?.items) ? likesRes.data.items
                   : Array.isArray(likesRes?.data)       ? likesRes.data : []
    const mutualRaw = Array.isArray(mutualRes?.data?.items) ? mutualRes.data.items
                    : Array.isArray(mutualRes?.data)       ? mutualRes.data : []

    const likedSet  = new Set(likesRaw.map(extractUserId).filter(n => !Number.isNaN(n)))
    const mutualSet = new Set(mutualRaw.map(extractUserId).filter(n => !Number.isNaN(n)))

    if (mutualSet.has(viewedUid.value)) {
      likedFlag.value = true
      matchStatus.value = 'matched'
    } else if (likedSet.has(viewedUid.value)) {
      likedFlag.value = true
      matchStatus.value = 'pending'
    } else {
      likedFlag.value = false
      matchStatus.value = ''
    }
  } catch (e) {
    // 静默
  }
}

async function fetchLikedMe () {
  try {
    const { data } = await getLikedMe(uid, { page: 1, page_size: 100 })
    likedMeList.value = Array.isArray(data?.items) ? data.items
                    : Array.isArray(data)       ? data : []
  } catch (e) {
    // 静默
  }
}

onMounted(async () => {
  await Promise.all([load(), refreshLikeStates()])
  contentRef.value?.scrollTo?.({ top: 0, behavior: 'smooth' })
  fetchLikedMe()
})

watch(() => route.params.uid, async (n) => {
  viewedUid.value = Number(n)
  await Promise.all([load(), refreshLikeStates()])
  contentRef.value?.scrollTo?.({ top: 0, behavior: 'smooth' })
})

/** ✅ 点“喜欢”：必弹广告（即使 like 失败也弹兜底） */
async function onLikeBtnClick () {
  try {
    const { adOpened, result } = await likeThenMaybeAd(uid, viewedUid.value)

    // 乐观更新：立即给到“已喜欢/已匹配”的视觉反馈
    likedFlag.value = true
    if (result?.status === 'matched') {
      matchStatus.value = 'matched'
    } else if (matchStatus.value !== 'matched') {
      matchStatus.value = 'pending'
    }

    // 精确刷新
    await reloadByKeys(result?.refresh || [])
  } catch (e) {
    // ❗ like 失败也强制弹窗（满足“每次点击都要弹”）
    if (!currentAd.value) {
      currentAd.value = { id: 1, destination: '/ad/1', title: '精选推荐' }
    }
    showAd.value = true
  }
}

/** 精确刷新：本页只需 likedMe / likes / mutual */
async function reloadByKeys(keys = []) {
  const set = new Set(keys)
  const jobs = []
  if (set.has('likedMe')) jobs.push(fetchLikedMe())
  if (set.has('likes') || set.has('mutual')) jobs.push(refreshLikeStates())
  if (jobs.length) await Promise.all(jobs)
}

/** ✅ 弹窗“稍后再说” */
function onAdClose () {
  closeAd() // 只是收起弹窗；like 已经完成或已兜底弹窗
}

/** ✅ 弹窗“去看看”：先关窗再跳，带上 from=likedMe */
function onAdSee () {
  closeAd()
  goSeeAd(router, currentAd.value, 'likedMe')
}
</script>

<style scoped>
/* 保留你的样式基础 */
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
.meta { display:flex; flex-direction:column; }
.meta .name { font-weight:700; }
.meta .sub { color:#6b7280; font-size:12px; }
.section { margin-bottom:16px; }
.mb-2 { margin-bottom: 8px; }
.mb-1 { margin-bottom: 4px; }
.bio { margin-top:6px; background:#f9fafb; padding:10px; border-radius:8px; }
.qna-item { background:#f9fafb; padding:8px 10px; border-radius:8px; margin-bottom:10px; }
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.media-item {
  width: 100%;
  height: 120px;
  border-radius: 10px;
  overflow: hidden;
  background: #f3f4f6;
}
.image-slot {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  color: #9ca3af; font-size: 12px;
}
</style>
