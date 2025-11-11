<template>
  <div class="vip-plus-page">
    <el-card class="vip-card" shadow="always">
      <h2>开通 VIP+</h2>
      <p class="sub">免广告发起聊天 · 更高曝光 · 高级筛选 · 专属徽章</p>

      <ul class="benefits">
        <li>✅ 发起聊天免看广告</li>
        <li>✅ 推荐权重提升与优先曝光</li>
        <li>✅ 高级搜索与筛选（年龄、城市、教育等）</li>
        <li>✅ 聊天气泡与专属身份标识</li>
      </ul>

      <div class="actions">
        <el-button type="primary" size="large" @click="openNow">立即开通</el-button>
        <el-button text @click="goBack">返回</el-button>
      </div>

      <div class="note">* 开通即视为同意《会员服务协议》</div>

      <!-- <p class="debug">from={{ from }} | target={{ target }} | local.vip_plus={{ localVip }}</p> -->
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const from = computed(() => String(route.query.from || ''))
const target = computed(() => Number(route.query.target || 0))
const localVip = ref(localStorage.getItem('vip_plus') || '(null)')

onMounted(() => {
  console.log('[VipPlus] mounted, query:', route.query, 'local.vip_plus=', localVip.value)
})

function openNow() {
  // 这里接你真实的支付流程；演示：直接把本地 VIP 打开（验证后端就用后端返回）
  localStorage.setItem('vip_plus', 'vip_plus')
  console.log('[VipPlus] set localStorage.vip_plus = vip_plus')

  // 开通后：若带 target，直接进聊天；否则回来源或匹配页
  if (target.value > 0) router.push({ path: `/chat/${target.value}` }).catch(() => {})
  else if (from.value) router.push(from.value).catch(() => {})
  else router.push('/match').catch(() => {})
}

function skipOnce() {
  // ★ 关键：仅压制“下一次广告”
  sessionStorage.setItem('ad_gate_suppress_once', '1')
  console.log('[VipPlus] set ad_gate_suppress_once=1, go back. target=', target.value)

  // 回来源；没有的话就返回/回匹配页
  if (from.value) router.push(from.value).catch(() => {})
  else router.back()
}

function goBack() {
  if (from.value) router.push(from.value).catch(() => {})
  else router.back()
}
</script>

<style scoped>
.vip-plus-page { display:flex; justify-content:center; padding:24px; }
.vip-card { max-width: 720px; width:100%; border-radius:16px; }
.sub { color:#6b7280; margin-bottom: 16px; }
.benefits { margin: 12px 0 20px; line-height: 1.9; }
.actions { display:flex; gap:12px; margin-top: 8px; }
.note { color:#9ca3af; font-size:12px; margin-top: 12px; }
.debug { color:#9ca3af; font-size:12px; margin-top: 12px; }
</style>
