<!-- src/components/ForcedAdDialog.vue -->
<template>
  <el-dialog
    v-model="visible_"
    width="480px"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    destroy-on-close
    align-center
    class="forced-ad-dialog"
  >
    <template #header>
      <div class="ad-header">
        <div class="title">
          <el-icon><Timer /></el-icon>
          <span>正在播放赞助广告</span>
        </div>
        <div class="count">
          <span v-if="!vipPlus">
            {{ remain }} 秒后自动发起聊天
          </span>
          <span v-else>
            VIP+ 可随时直接发起聊天
          </span>
        </div>
      </div>
    </template>

    <div class="ad-body" @click="onSee">
      <img class="ad-img" :src="ad.img || defaultImg" alt="广告" />
      <div class="ad-text">
        <h3>{{ ad.title || '为你解锁更多聊天机会' }}</h3>
        <p>{{ ad.desc || '赞助商为你买单，完整观看广告后自动进入聊天页面～' }}</p>
      </div>
    </div>

    <template #footer>
      <div class="ad-footer">
        <!-- 非 VIP+：只能选择观看 / 去开通 VIP+ -->
        <template v-if="!vipPlus">
          <el-button @click="onSkipNonVip">
            跳过广告
          </el-button>
          <el-button type="primary" @click="onSee">
            了解活动
          </el-button>
        </template>

        <!-- VIP+：可以直接发起聊天 -->
        <template v-else>
          <el-button @click="onSee">
            看看广告
          </el-button>
          <el-button type="primary" @click="fastFinish">
            直接发起聊天
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  ad: {
    type: Object,
    default: () => ({}),
  },
  seconds: {
    type: Number,
    default: 15,
  },
  // 是否 VIP+：VIP+ 可以直接跳过广告
  vipPlus: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'finished', 'see'])

const router = useRouter()
const visible_ = ref(false)
const remain = ref(props.seconds || 15)
const timer = ref(null)

const defaultImg = 'https://placehold.co/400x200?text=Sponsor+AD'

function clearTimer() {
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

function startTimer() {
  clearTimer()
  remain.value = props.seconds || 15

  // VIP+ 也照样走倒计时，只是可以提前点击“直接发起聊天”
  timer.value = setInterval(() => {
    if (remain.value <= 1) {
      clearTimer()
      // 时间到了视为完成观看
      emit('finished')
      return
    }
    remain.value -= 1
  }, 1000)
}

watch(
  () => props.modelValue,
  (val) => {
    visible_.value = val
    if (val) {
      startTimer()
    } else {
      clearTimer()
    }
  },
  { immediate: true }
)

watch(visible_, (val) => {
  emit('update:modelValue', val)
  if (!val) clearTimer()
})

onBeforeUnmount(() => {
  clearTimer()
})

function toNum(x) {
  const n = Number(x)
  return Number.isFinite(n) && n > 0 ? n : null
}

/** 点击广告本体 / 了解活动 */
function onSee() {
  // 先通知父组件（父组件会用上面的 handleGateSeeAd 处理）
  emit('see')

  // 50ms 后如果父组件没处理（弹窗还开着），本地兜底
  setTimeout(() => {
    if (!visible_.value) return
    const d = props.ad || {}
    const toNum = (x) => {
      const n = Number(x); return Number.isFinite(n) && n > 0 ? n : null
    }
    const id = toNum(d.id ?? d.ad_id ?? d.adId ?? d.adID)
    const rawDest = d.destination || d.route || d.url || d.link || ''

    let dest = ''
    const isHttp = (u) => /^https?:\/\//i.test(String(u || ''))

    if (id) {
      // ✅ 有 id：强制站内
      dest = `/ad/${id}`
    } else if (isHttp(rawDest)) {
      try {
        const u = new URL(rawDest)
        const m = u.pathname.match(/^\/?ad\/(\d+)/i)
        if (m) {
          // 绝对 URL 其实也是 /ad/{id}，转站内
          dest = `/ad/${m[1]}`
        } else {
          // 真外链
          window.open(rawDest, '_blank')
          return
        }
      } catch {
        // 解析失败就继续往下走兜底
      }
    }

    if (!dest) {
      if (!rawDest) return
      dest = rawDest.startsWith('/') ? rawDest : `/${rawDest}`
    }

    // 用原生或路由都行，这里用原生保证万无一失，但同域同端口
    window.location.href = dest
  }, 50)
}


/** 非 VIP+ 点击“跳过广告”：弹出提示，引导去开通会员 */
async function onSkipNonVip() {
  try {
    await ElMessageBox.confirm(
      '开通 VIP+ 即可跳过广告、直接发起聊天，并享受更多特权，是否前往开通？',
      '开通 VIP+',
      {
        confirmButtonText: '去开通',
        cancelButtonText: '再想想',
        type: 'warning',
      }
    )
    // 用户确认，跳转到 VIP+ 页面
    router.push('/vip-plus').catch(() => {})
  } catch (e) {
    // 取消则什么都不做，继续看广告
  }
}

/** VIP+ 点击“直接发起聊天”：立即视作完成观看 */
function fastFinish() {
  clearTimer()
  emit('finished')
}
</script>

<style scoped>
.forced-ad-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  border-bottom: 1px solid #e5e7eb;
}
.ad-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.count {
  color: #0ea5e9;
}
.ad-body {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 8px;
  border-radius: 12px;
  background: #f8fafc;
}
.ad-img {
  width: 140px;
  height: 100px;
  border-radius: 10px;
  object-fit: cover;
  background: #e5e7eb;
}
.ad-text h3 {
  margin: 0;
  font-size: 16px;
}
.ad-text p {
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
}
.ad-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
