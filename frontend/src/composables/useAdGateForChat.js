// src/composables/useAdGateForChat.js
import { ref } from 'vue'
import { getAdList, getDisplay } from '@/api'
import { goSeeAd } from '@/composables/useLikeWithAd.js'

function readBool(x) {
  const s = String(x ?? '').toLowerCase().trim()
  return s === 'true' || s === '1' || s === 'yes' || s === 'y'
      || s === 'vip_plus' || s === 'vip+' || s === 'vip' || s === 'plus'
}

function isVipPlusLocal() {
  try {
    const raw = localStorage.getItem('vip_plus')
    return readBool(raw)
  } catch {
    return false
  }
}

async function syncVipPlusFromServer(uid) {
  console.log('[ChatAdGate] localStorage.vip_plus =', localStorage.getItem('vip_plus'))
  try {
    if (!uid) {
      console.warn('[ChatAdGate] meId not provided -> use localStorage only')
      return isVipPlusLocal()
    }
    const { data } = await getDisplay(uid) // /api/user/main/{uid}
    const lvl = String(data?.plan_code || '').toLowerCase()
    const isVip = ['vip_plus', 'vip', 'plus'].includes(lvl) || !!data?.vip_plus
    console.log('[ChatAdGate] server plan_code =', lvl, 'vip_plus =', !!data?.vip_plus, '=> final =', isVip)
    if (isVip) localStorage.setItem('vip_plus', 'vip_plus')
    else localStorage.removeItem('vip_plus')
    return isVip
  } catch (e) {
    console.warn('[ChatAdGate] getDisplay failed, fallback local:', e)
    return isVipPlusLocal()
  }
}

async function fetchServerAds(limit = 50) {
  try {
    const { data } = await getAdList({ limit })
    return Array.isArray(data?.items) ? data.items : []
  } catch (e) {
    console.warn('[ChatAdGate] getAdList error:', e)
    return []
  }
}

export function useAdGateForChat(router) {
  const showGate = ref(false)
  const chatAd = ref(null)
  const requiredSeconds = ref(15)
  const pendingTargetId = ref(null)
  const vipPlus = ref(isVipPlusLocal())

  function goChatNow() {
    const n = Number(pendingTargetId.value)
    if (!Number.isFinite(n) || n <= 0) {
      console.warn('[ChatAdGate] goChatNow invalid id:', pendingTargetId.value)
      return
    }
    showGate.value = false
    router.push({ path: `/chat/${n}` }).catch(err => {
      // 避免重复导航的未捕获异常影响交互
      console.warn('[ChatAdGate] router.push error:', err?.message || err)
    })
  }

  /**
   * 入口：发起聊天前闸门
   * targetUser: id 或包含 id/user_id/userId 的对象
   * options: { meId?: number, seconds?: number }
   * 返回：boolean -> true 表示已拦截并弹窗；false 表示未拦截
   */
  async function openAdBeforeChat(targetUser, options = {}) {
    // ★ 如果刚从 VIP+ 返回并设置了“压制一次广告”，本次直接放行
    if (sessionStorage.getItem('ad_gate_suppress_once') === '1') {
      sessionStorage.removeItem('ad_gate_suppress_once')
      const n0 = Number(targetUser?.id ?? targetUser?.user_id ?? targetUser?.userId ?? targetUser)
      if (Number.isFinite(n0) && n0 > 0) {
        console.log('[ChatAdGate] suppress once -> go chat directly', n0)
        pendingTargetId.value = n0
        goChatNow()
        return false
      }
    }

    // 解析聊天对象 id
    const rawId = targetUser?.id ?? targetUser?.user_id ?? targetUser?.userId ?? targetUser
    const n = Number(rawId)
    if (!Number.isFinite(n) || n <= 0) {
      console.warn('[ChatAdGate] openAdBeforeChat invalid targetUser:', targetUser)
      return false
    }
    pendingTargetId.value = n

    // 同步 VIP
    vipPlus.value = await syncVipPlusFromServer(options?.meId)

    // 倒计时：VIP+ 直接 0；非 VIP 用外部传入或默认 15s
    requiredSeconds.value = vipPlus.value
      ? 0
      : (Number.isFinite(options.seconds) ? Number(options.seconds) : 15)

    // 拉广告（后端为空则兜底）
    let pool = await fetchServerAds(50)
    if (!Array.isArray(pool) || pool.length === 0) {
      pool = [{
        id: 1001,
        title: '开通 VIP+ 跳过广告',
        desc: '发起聊天免广告、更多曝光与加速匹配',
        destination: '/vip-plus',
        img: 'https://placehold.co/400x200?text=VIP%2B',
      }]
    }
    chatAd.value = pool[Math.floor(Math.random() * pool.length)]
    console.log('[ChatAdGate] show ad gate with ad:', chatAd.value, 'vipPlus=', vipPlus.value, 'sec=', requiredSeconds.value)

    // ★ 关键：无论是否 VIP 都“显示弹窗”，区别只在按钮是否可立即跳过
    showGate.value = true
    return true
  }

  // 用户点击“去看看”（广告落地页或 /vip-plus）
  function handleGateSeeAd(from = 'mutual') {
    const ad = chatAd.value
    if (!ad) return
    showGate.value = false

    let dest = ad.destination || ad.route || (ad.id ? `/ad/${ad.id}` : '')
    if (dest && !/^https?:\/\//i.test(dest) && !dest.startsWith('/')) dest = '/' + dest
    if (!dest) return

    const back = router.currentRoute.value.fullPath
    const target = String(pendingTargetId.value || '')

    if (/^https?:\/\//i.test(dest)) {
      window.location.href = dest
      return
    }

    const isVipPlusPage = dest === '/vip-plus' || dest.startsWith('/vip-plus')
    if (isVipPlusPage) {
      // 去开通/跳过页：告诉它“回来后压制一次广告”
      sessionStorage.setItem('ad_gate_suppress_once', '1')
      router.push({ path: dest, query: { from: back, target } }).catch(() => {})
    } else {
      goSeeAd(router, ad, from)
    }
  }

  // 倒计时结束 / 或 VIP+ 点击“跳过（VIP+）”
  function handleGateFinished() {
    console.log('[ChatAdGate] FINISHED or VIP SKIP -> chat with', pendingTargetId.value)
    goChatNow()
  }

  return {
    showGate,
    chatAd,
    requiredSeconds,
    vipPlus,
    openAdBeforeChat,
    handleGateFinished,
    handleGateSeeAd,
  }
}
