<!-- src/views/AdDetailView.vue -->
<template>
  <div class="ad-detail-page">
    <!-- 顶部条 -->
    <div class="ad-topbar">
      <div class="left">
        <!-- 标题优先用后端给的 title；没有就显示“广告详情” -->
        <h2>{{ ad.title || '广告详情' }}</h2>
        <p class="sub" v-if="ad.time">发布时间：{{ fmtTs(ad.time) }}</p>
      </div>
      <div class="right">
        <el-button @click="goBack">返回</el-button>
        <el-button type="primary" @click="goOriginTab">回到来源列表</el-button>
      </div>
    </div>

    <!-- 内容区 -->
    <el-card shadow="never">
      <el-skeleton :loading="loading" animated :rows="4">
        <template #default>
          <div class="ad-body">
            <img v-if="ad.img" :src="ad.img" class="ad-cover" alt="ad" />
            <div class="ad-content">
              <!-- 这里完全展示后端字段，不再用默认文案 -->
              <h3>{{ ad.title }}</h3>
              <p v-if="ad.desc">{{ ad.desc }}</p>
              <p v-else class="muted">暂无描述</p>

              <!-- 如果 destination 存在，则可以“去看看” -->
              <el-button
                v-if="ad.destination"
                type="success"
                style="margin-top: 12px"
                @click="jumpDest"
              >
                去看看
              </el-button>

              <!-- 显示一下 id，方便你确认是不是你要的 Ad 5 那种 -->
              <p v-if="ad.id" class="muted" style="margin-top:8px">
                广告 ID：{{ ad.id }}
              </p>
            </div>
          </div>
        </template>
      </el-skeleton>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        style="margin-top: 16px"
      />
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAdDetail } from '@/api'

const route = useRoute()
const router = useRouter()

/**
 * ✅ 更健壮的广告 ID 提取逻辑
 * 支持 param / query / path 三种来源
 */
// 替换你文件里原来的 adId 计算属性
const adId = computed(() => {
  const p = route.params || {}
  const q = route.query || {}

  const candidates = [
    p.id,
    p.adId,
    p.ad_id,
    q.id,
    q.adId,
    q.ad_id,
  ]

  // 1) 先从 params / query 里取
  for (const v of candidates) {
    if (v === undefined || v === null || v === '') continue
    const n = Number(v)
    if (Number.isFinite(n) && n > 0) return n
  }

  // 2) 再从当前 URL 路径兜底一次 /ad/:id
  if (typeof window !== 'undefined') {
    const m = window.location.pathname.match(/\/ad\/(\d+)/)
    if (m) {
      const n = Number(m[1])
      if (Number.isFinite(n) && n > 0) return n
    }
  }

  // 都没拿到就返回 null
  return null
})



// 来源页签（recommend / likedMe / likes / mutual / others）
const fromTab = computed(() => (route.query.from ? String(route.query.from) : ''))

const ad = ref({
  id: null,
  title: '',
  desc: '',
  img: '',
  destination: '',
  time: ''
})
const loading = ref(false)
const error = ref('')

/**
 * ✅ 统一把后端广告数据“规范化”
 * 只做字段兼容，不做强制 fallback（比如不会强行 destination = `/ad/${id}`）
 */
function normalizeAdDetail(raw, fallbackId) {
  const src = raw || {}

  const id =
    src.id ??
    src.ad_id ??
    src.adId ??
    fallbackId ??
    null

  const title =
    src.title ??
    src.name ??
    src.headline ??
    ''

  const desc =
    src.desc ??
    src.description ??
    src.sub_title ??
    src.subtitle ??
    ''

  const img =
    src.img ??
    src.image ??
    src.image_url ??
    src.cover ??
    src.cover_url ??
    ''

  const destination =
    src.destination ??
    src.url ??
    src.link ??
    src.route ??
    '' // 👈 不再自己造 /ad/1，完全由后端决定跳哪

  const time =
    src.time ??
    src.publish_time ??
    src.created_at ??
    src.updated_at ??
    ''

  return { id, title, desc, img, destination, time }
}

/**
 * ✅ 拉取广告详情
 * id 无效就回推荐页
 */
 async function fetchAd() {
  const id = adId.value
  const n = Number(id)

  // 这里只做打印，不再强制跳回 /match
  if (!Number.isFinite(n) || n <= 0) {
    console.warn('[AdDetail] invalid id, stay on page', id, route)
    return
  }

  loading.value = true
  error.value = ''
  try {
    const res = await getAdDetail(n)   // ✅ 用合法的数字 id 调后端
    const data = res?.data ?? res
    ad.value = normalizeAdDetail(data, n)
  } catch (e) {
    console.error('[AdDetail] fetch error', e)
    error.value = '广告加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}


// ✅ 即时监听 adId，解决“同页面切换不同 id 不刷新”的问题
watch(adId, fetchAd, { immediate: true })

/**
 * ✅ 回到来源列表页（/match?tab=xxx）
 */
function goOriginTab() {
  const from = fromTab.value
  const validTabs = new Set(['recommend', 'likedMe', 'likes', 'mutual', 'others'])
  router.push({
    path: '/match',
    query: { tab: validTabs.has(from) ? from : 'recommend' }
  })
}

/**
 * ✅ 返回上一页（优先用来源，否则 history.back）
 */
function goBack() {
  const from = fromTab.value
  const validTabs = new Set(['recommend', 'likedMe', 'likes', 'mutual', 'others'])
  if (validTabs.has(from)) {
    router.push({ path: '/match', query: { tab: from } })
  } else {
    router.back()
  }
}

/**
 * ✅ 去看看（使用后端给的 destination，自动携带 from）
 *   - destination 是外链：整页跳转 + from
 *   - destination 是站内路由：router.push + from
 *   - destination 为空：直接回 /match?tab=recommend（不再强制 /ad/1）
 */
function jumpDest() {
  const from = fromTab.value || 'recommend'

  // 读取 destination；如果没有，就回匹配页，不再自己造 /ad/:id
  let dest = String(ad.value.destination || '').trim()
  if (!dest) {
    try {
      router.push({ path: '/match', query: { tab: 'recommend' } })
    } catch {
      window.location.href = '/match?tab=recommend'
    }
    return
  }

  // ===== A) 站外链接：整页跳，并补上 from =====
  if (/^https?:\/\//i.test(dest)) {
    try {
      const u = new URL(dest)
      if (from && !u.searchParams.has('from')) u.searchParams.set('from', from)
      window.location.href = u.toString()
    } catch {
      const url =
        dest +
        (from ? (dest.includes('?') ? '&' : '?') + `from=${encodeURIComponent(from)}` : '')
      window.location.href = url
    }
    return
  }

  // ===== B) 站内链接 =====
  if (dest[0] !== '/') dest = '/' + dest

  // B1) 如果目标仍然是 /ad/:id，则附加 from；同页同 id 时加 t 强制刷新
  const m = dest.match(/^\/ad\/(\d+)(?:\?|$)/)
  if (m) {
    const innerId = Number(m[1])
    const sameId = Number(adId.value) === innerId
    const sameFrom = String(route.query.from || '') === String(from)
    const query = sameId && sameFrom ? { from, t: Date.now() } : { from }

    router.push({ path: `/ad/${innerId}`, query }).catch(() => {
      const qs = `from=${encodeURIComponent(from)}${query.t ? `&t=${query.t}` : ''}`
      const url = `/ad/${innerId}?${qs}`
      window.location.href = url
    })
    return
  }

  // B2) 其它站内路由：带上 from，push 失败则整页跳
  const urlWithFrom =
    dest + (from ? (dest.includes('?') ? '&' : '?') + `from=${encodeURIComponent(from)}` : '')
  router.push({ path: dest, query: from ? { from } : {} }).catch(() => {
    window.location.href = urlWithFrom
  })
}

/**
 * ✅ 格式化时间戳
 */
function fmtTs(s) {
  if (!s) return '—'
  const t = String(s)
  return t.length > 19 ? t.slice(0, 19).replace('T', ' ') : t.replace('T', ' ')
}
</script>

<style scoped>
.ad-detail-page {
  padding: 16px;
}
.ad-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.ad-topbar .sub {
  opacity: 0.7;
  margin-top: 6px;
}
.ad-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.ad-cover {
  width: 360px;
  max-width: 42vw;
  border-radius: 10px;
  object-fit: cover;
}
.ad-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.muted {
  color: #9ca3af;
  font-size: 13px;
}
</style>
