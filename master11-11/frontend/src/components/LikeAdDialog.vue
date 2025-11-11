<!-- src/components/LikeAdDialog.vue -->
<template>
  <el-dialog
    v-model="visible_"
    width="420px"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    destroy-on-close
    align-center
    class="like-ad-dialog"
    @close="emitClose"
  >
    <!-- 头部：直接展示广告标题（例如：开通高级筛选） -->
    <template #header>
      <div class="ad-header">
        <span>{{ ad?.title }}</span>
        <el-icon class="ad-close" @click="emitClose"><Close /></el-icon>
      </div>
    </template>

    <!-- 点击主体也“去看看” -->
    <div class="ad-body" @click="emitSee">
      <img v-if="ad?.img" :src="ad.img" alt="ad" class="ad-img" />
      <div class="ad-text">
        <!-- 标题 / 副标题都来自后端 -->
        <h3>{{ ad?.title }}</h3>
        <p>{{ ad?.desc }}</p>
        <!-- 显示 id，方便你确认“轮换广告” -->
        <small v-if="ad?.id" class="ad-id">#{{ ad.id }}</small>
      </div>
    </div>

    <template #footer>
      <div class="ad-footer">
        <el-button @click="emitClose">稍后</el-button>
        <el-button type="primary" @click="emitSee">去看看</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'
import { goSeeAd } from '@/composables/useLikeWithAd.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 这里 ad 就是 useLikeWithAd.currentAd 传进来的，里面有 id / title / desc / img / destination
  ad: { type: Object, default: () => ({}) },
  // 来源 tab：recommend / likedMe / likes / mutual / others
  from: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'see', 'close'])

const router = useRouter()

// v-model
const visible_ = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function emitClose() {
  visible_.value = false
  emit('close')
}

function emitSee() {
  visible_.value = false
  emit('see', props.ad || null)   // 事件里把 ad 也抛出去（方便埋点）
  if (!props.ad) return
  // 直接根据后端给的 destination 跳转
  goSeeAd(router, props.ad, props.from || '')
}
</script>

<style scoped>
.like-ad-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding-right: 0;
}
.ad-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.ad-close {
  cursor: pointer;
  color: #94a3b8;
}
.ad-body {
  display: flex;
  gap: 12px;
  cursor: pointer;
}
.ad-img {
  width: 110px;
  height: 110px;
  border-radius: 12px;
  object-fit: cover;
  background: #f1f5f9;
}
.ad-text h3 {
  margin: 0;
  font-size: 15px;
}
.ad-text p {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}
.ad-id {
  display: inline-block;
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}
.ad-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
