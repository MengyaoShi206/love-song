// src/composables/useLikeWithAd.js
import { ref } from 'vue'
import { likeUser, getAdDetail } from '@/api'

/**
 * 顶层工具：统一“从广告对象跳转到落地页”
 * 供其他组件直接 import { goSeeAd } 使用
 */
export function goSeeAd(router, ad, from = 'recommend') {
  const fromSafe = from || 'recommend'
  const raw = ad || {}

  // 1) 从后端对象里取 id（兼容 ad_id / adId）
  const id = Number(
    raw.id ?? raw.ad_id ?? raw.adId ?? raw.adID ?? raw.adID
  )

  // 2) 优先用后端给的 destination / url / route / link
  let dest =
    raw.destination ||
    raw.route ||
    raw.url ||
    raw.link ||
    '' 

  // 3) 如果是绝对外链，就保留外链；否则我们统一走 /ad/:id
  const isExternal = /^https?:\/\//i.test(dest)

  if (!isExternal && Number.isFinite(id) && id > 0) {
    // 👇 这里 **强制** 使用通用广告详情页，而不是 '/ad/boost' 之类自定义路径
    dest = `/ad/${id}`
  }

  // 4) 如果既没 destination 又没 id，就直接回匹配页
  if (!dest) {
    router.push({ path: '/match', query: { tab: fromSafe } })
    return
  }


  // 5) 根据是外链还是站内路由分别处理
  if (/^https?:\/\//i.test(dest)) {
    // 外链：在 URL 上附加 from 参数
    try {
      const url = new URL(dest)
      url.searchParams.set('from', fromSafe)
      window.location.href = url.toString()
    } catch (e) {
      // URL 解析失败就直接粗暴跳
      window.location.href = dest
    }
    return
  }

  // 站内：确保有前导斜杠
  if (!dest.startsWith('/')) dest = '/' + dest

  router.push({
    path: dest,
    query: { from: fromSafe }
  }).catch(() => {
    // 避免重复导航报错
  })
}

/**
 * Hook：统一“点赞 →（可选）弹广告”的逻辑
 */
export function useLikeWithAd (opts = {}) {
  const enforceAd  = opts.enforceAd  ?? false     // 是否“必弹广告”
  const autoRotate = opts.autoRotate ?? true      // 本地兜底轮换/随机
  const limit      = opts.limit      ?? 2000        // 本地兜底 id 范围 [1, limit]
  const maxTries   = opts.maxTries   ?? 50        // 本地兜底尝试次数
  const fallbackAd = opts.fallbackAd ?? null      // 兜底固定广告
  const serverPick = typeof opts.serverPick === 'function'
    ? opts.serverPick
    : null                                         // 可选：后端抽广告函数

  // UI 状态
  const showAd        = ref(false)
  const currentAd     = ref(null)
  const lastLikeResult = ref(null)

  // 去重轮换用
  const seenIds = new Set()
  let localCursor = 0

  /** 关弹窗 */
  function closeAd () {
    showAd.value = false
  }

  /** 点赞 → 可能打开广告弹窗 */
  async function likeThenMaybeAd (uid, targetId) {
    // 1) 点赞
    const res = await likeUser(uid, targetId)
    const result = res?.data ?? res
    lastLikeResult.value = result

    // 2) 优先从“点赞返回”里拿广告（后端决定广告）
    let ad =
      normalizeAd(result?.ad) ||
      null

    if (!ad && result?.ad_id != null) {
      ad = await fetchAdById(result.ad_id)
    } else if (!ad && result?.advert?.id != null) {
      ad = await fetchAdById(result.advert.id)
    }

    const ctx = { uid, targetId }

    // 3) 没有就依次用：
    //    serverPick → 本地轮换/随机 → fallbackAd
    if (!ad) ad = await serverPickNew(ctx)
    if (!ad) ad = await localRotate()
    if (!ad) ad = fallbackAd ? normalizeAd(fallbackAd) : null

    // 4) 是否弹窗
    const shouldOpen = !!ad && (enforceAd || !!(result?.ad || result?.ad_id))
    if (shouldOpen) {
      currentAd.value = ad
      showAd.value = true
      if (ad?.id != null) seenIds.add(Number(ad.id))
      return { adOpened: true, result }
    } else {
      currentAd.value = null
      showAd.value = false
      return { adOpened: false, result }
    }
  }

  /** === 内部：从后端“抽取新广告”（可选） === */
  async function serverPickNew (ctx) {
    if (!serverPick) return null  // 没传就直接跳过
    try {
      const exclude = [...seenIds]
      const res = await serverPick({
        uid: ctx.uid,
        target_id: ctx.targetId,
        limit,
        exclude
      })
      const id =
        res?.data?.id ??
        res?.data?.ad_id ??
        res?.ad_id ??
        null
      return id != null ? fetchAdById(id) : null
    } catch {
      return null
    }
  }

  /** === 内部：本地兜底轮换/随机拉广告 === */
  async function localRotate () {
    if (!autoRotate || !Number.isFinite(Number(limit)) || limit <= 0) return null

    for (let i = 0; i < maxTries; i++) {
      const guessId = pickLocalId(limit)
      if (seenIds.has(guessId)) continue
      const ad = await fetchAdById(guessId)
      if (ad) return ad
    }
    return null
  }

  function pickLocalId (limit) {
    // 简单“顺序+抖动”防止太假
    localCursor = (localCursor + 1) % limit
    const jitter = Math.floor(Math.random() * 3) // 0~2
    const id = 1 + ((localCursor + jitter) % limit)
    return id
  }

  /** === 内部：取广告详情 & 标准化结构 === */
  async function fetchAdById (id) {
    try {
      const { data } = await getAdDetail(id)
      return normalizeAd(data)
    } catch {
      return null
    }
  }

  function normalizeAd (raw) {
    if (!raw || typeof raw !== 'object') return null
    return {
      id:
        raw.id ??
        raw.ad_id ??
        raw.advert_id ??   // ✅ 新增
        raw.adv_id ??      // ✅ 新增
        null,
      title:       raw.title ?? raw.name ?? '',
      desc:        raw.desc ?? raw.description ?? '',
      img:         raw.img ?? raw.image_url ?? raw.cover ?? '',
      destination: raw.destination ?? raw.route ?? raw.url ?? '',
      time:        raw.time ?? raw.start_time ?? null,
    }
  }
  

  return {
    // 状态
    showAd,
    currentAd,
    lastLikeResult,
    // 行为
    likeThenMaybeAd,
    closeAd,
    // 把顶层 goSeeAd 也挂出来，想从 hook 里用也行
    goSeeAd,
  }
}
