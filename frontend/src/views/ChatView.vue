<!-- haozong/hunlian/master/frontend/src/views/ChatView.vue -->
<template>
  <div class="chat-layout">
    <main class="chat-main">
      <el-card shadow="never" class="chat-card">
        <template #header>
          <div class="chat-header">
            <div class="title">聊天</div>
            <div class="subtitle">
              正在和 <strong>{{ displayName }}</strong> 聊天
            </div>
          </div>
        </template>

        <div class="chat-body">
          <div v-if="!targetId" class="empty">
            未获取到聊天对象 ID，请从“聊天列表”或“已双向匹配”重新发起聊天。
          </div>

          <div v-else class="mock-messages">
            <div class="sys-msg">
              （占位）这里未来接入真实即时聊天功能。
            </div>
            <div class="msg-row me">
              <div class="bubble">
                你好呀，很高兴认识你～
              </div>
            </div>
            <div class="msg-row other">
              <div class="bubble">
                嗨，我也是，咱们可以先简单聊聊兴趣爱好。
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="draft"
            type="textarea"
            :rows="2"
            placeholder="这里先做 UI 占位，暂未接入后端发送～"
          />
          <el-button type="primary" :disabled="!draft" @click="onSend">
            发送
          </el-button>
        </div>
      </el-card>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

// 从路由参数拿聊天对象 ID：/chat/:id
const targetId = computed(() => {
  const raw = route.params.id
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
})

const displayName = computed(() => {
  if (!targetId.value) return '未知用户'
  return `ID${targetId.value}`
})

const draft = ref('')

function onSend() {
  if (!draft.value) return
  ElMessage.success('当前为占位 UI，暂未真正发送')
  draft.value = ''
}
</script>

<style scoped>
.chat-layout {
  padding: 24px;
  background: #f8fafc;
  min-height: 100vh;
  box-sizing: border-box;
}

.chat-main {
  max-width: 960px;
  margin: 0 auto;
}

.chat-card {
  border-radius: 18px;
}

.chat-header .title {
  font-size: 18px;
  font-weight: 600;
}

.chat-header .subtitle {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}

.chat-body {
  min-height: 260px;
  padding: 8px 0 16px;
  border-bottom: 1px solid #e5e7eb;
}

.empty {
  color: #9ca3af;
  text-align: center;
  padding: 40px 0;
}

.mock-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.msg-row {
  display: flex;
}

.msg-row.me {
  justify-content: flex-end;
}

.msg-row.other {
  justify-content: flex-start;
}

.bubble {
  max-width: 60%;
  padding: 8px 12px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.msg-row.me .bubble {
  background: #4f46e5;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-row.other .bubble {
  background: #e5e7eb;
  color: #111827;
  border-bottom-left-radius: 4px;
}

.chat-input {
  margin-top: 12px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
