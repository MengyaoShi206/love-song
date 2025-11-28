<!-- /frontend/src/views/ChatListView.vue -->
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

          <el-menu-item index="chat">
            <el-icon><ChatLineSquare /></el-icon>
            <span class="menu-chat-label">
              聊天（已匹配）
              <span v-if="totalUnread > 0" class="menu-unread-pill">
                {{ totalUnreadDisplay }}
              </span>
            </span>
          </el-menu-item>

          <el-menu-item index="other" disabled>
            <el-icon><Setting /></el-icon>
            <span>其他（待扩展）</span>
          </el-menu-item>
        </el-menu>
      </el-card>
    </aside>

    <!-- 右侧聊天区域 -->
    <main class="content">
      <div class="chat-layout">
        <!-- 左：会话列表 -->
        <section class="chat-list-pane">
          <div class="chat-list-header">
            <div class="title">
              已双向匹配
              <span v-if="totalUnread > 0" class="unread-pill">
                {{ totalUnreadDisplay }}
              </span>
            </div>
            <div class="sub">
              点击头像发起聊天；每位 TA 首次聊天需观看 15 秒广告解锁
            </div>
          </div>

          <el-skeleton :loading="mutual.loading" animated :count="4">
            <template #template>
              <div class="chat-list-item skeleton">
                <el-skeleton-item
                  variant="circle"
                  style="width: 40px; height: 40px"
                />
                <div class="skeleton-text">
                  <el-skeleton-item variant="text" style="width: 80%" />
                  <el-skeleton-item variant="text" style="width: 60%" />
                </div>
              </div>
            </template>

            <template #default>
              <div v-if="mutual.items.length" class="chat-list">
                <div
                  v-for="u in mutual.items"
                  :key="u.id"
                  :class="['chat-list-item', { active: u.id === activeChatId }]"
                  @click="onClickUser(u)"
                >
                  <!-- 头像 + 红点 -->
                  <div class="avatar-badge-wrapper">
                    <el-avatar :size="40" :src="u.avatar_url || ''" />
                    <span
                      v-if="getUnread(u.id) > 0"
                      class="avatar-unread-pill"
                    >
                      {{ getUnread(u.id) > 99 ? '99+' : getUnread(u.id) }}
                    </span>
                  </div>

                  <!-- 右侧文字区域 -->
                  <div class="meta">
                    <div class="line-1">
                      <span class="name">
                        {{ u.nickname || u.username || 'ID' + u.id }}
                      </span>
                      <span class="age-city">
                        {{
                          [u.age && u.age + '岁', u.city]
                            .filter(Boolean)
                            .join(' · ')
                        }}
                      </span>
                    </div>
                    <div class="line-2">
                      <span class="last-msg">
                        {{
                          lastMessagePreview(u.id) ||
                          '还没有开始聊天，点一下试试～'
                        }}
                      </span>
                    </div>
                    <div class="lock-line">
                      <el-tag v-if="vipPlus" size="small" type="success">
                        VIP+ 免广告
                      </el-tag>
                      <el-tag v-else size="small" type="warning">
                        需广告解锁
                      </el-tag>
                    </div>
                    <div class="action-line">
                      <el-button
                        size="small"
                        plain
                        class="profile-btn"
                        @click.stop="goProfile(u.id)"
                      >
                        查看资料
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>

              <el-empty
                v-else
                description="暂无双向匹配；可以先在匹配中心多点点 ❤️"
              />
            </template>
          </el-skeleton>
        </section>

        <!-- 右：聊天窗口 -->
        <section class="chat-pane">
          <template v-if="activeUser">
            <header class="chat-header">
              <div class="left">
                <el-avatar :size="44" :src="activeUser.avatar_url || ''" />
                <div class="info">
                  <div class="name-row">
                    <span class="name">
                      {{
                        activeUser.nickname ||
                        activeUser.username ||
                        'ID' + activeUser.id
                      }}
                    </span>
                    <span class="tag" v-if="activeUser.age">
                      {{ activeUser.age }}岁
                    </span>
                    <span class="tag" v-if="activeUser.city">
                      {{ activeUser.city }}
                    </span>
                  </div>
                  <div class="sub">
                    {{
                      activeUser.tagline ||
                      activeUser.bio ||
                      '好好聊一聊，看看是否合适～'
                    }}
                  </div>
                </div>
              </div>
              <div class="right">
                <el-tag v-if="vipPlus" size="small" type="success">
                  VIP+ 已开启
                </el-tag>
                <el-tag
                  v-else-if="isUnlocked(activeChatId)"
                  size="small"
                  type="success"
                >
                  本轮已解锁
                </el-tag>
                <el-tag v-else size="small" type="warning">
                  需广告解锁
                </el-tag>
                <el-button
                  size="small"
                  plain
                  class="profile-btn"
                  @click="goProfile(activeUser.id)"
                >
                  查看资料
                </el-button>
              </div>
            </header>

            <div class="chat-body">
              <div class="chat-messages" ref="messagesRef">
                <div
                  v-for="m in currentMessages"
                  :key="m.id"
                  :class="['msg-row', m.from === 'me' ? 'me' : 'other']"
                >
                  <div class="bubble">
                    <div class="content">
                      <!-- 文字 -->
                      <template v-if="!m.msg_type || m.msg_type === 'text'">
                        <div class="text">{{ m.content }}</div>
                      </template>

                      <!-- 图片 -->
                      <template v-else-if="m.msg_type === 'image'">
                        <el-image
                          class="msg-image"
                          :src="fileUrl(m.content)"
                          :preview-src-list="[fileUrl(m.content)]"
                          fit="cover"
                        />
                      </template>

                      <!-- 文件 -->
                      <template v-else-if="m.msg_type === 'file'">
                        <a
                          class="msg-file"
                          :href="fileUrl(m.content)"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <el-icon class="file-icon"><Folder /></el-icon>
                          <span class="file-name">{{ m.file_name || '文件' }}</span>
                        </a>
                      </template>

                      <!-- 视频 -->
                      <template v-else-if="m.msg_type === 'video'">
                        <video
                          class="msg-video"
                          :src="fileUrl(m.content)"
                          controls
                        />
                      </template>

                      <!-- 位置 -->
                      <template v-else-if="m.msg_type === 'location'">
                        <a
                          class="msg-file"
                          :href="m.content"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <el-icon class="file-icon"><Position /></el-icon>
                          <span class="file-name">查看位置</span>
                        </a>
                      </template>

                      <!-- fallback -->
                      <template v-else>
                        <div class="text">{{ m.content }}</div>
                      </template>
                    </div>

                    <div class="time">{{ formatTime(m.ts) }}</div>
                  </div>
                </div>


                <div v-if="!currentMessages.length" class="chat-empty">
                  这是你们的第一条对话，真诚地介绍一下自己会更容易打开话题～
                </div>
              </div>

              <div class="chat-input">
                <el-input
                  v-model="inputText"
                  type="textarea"
                  :rows="3"
                  resize="none"
                  placeholder="给对方发一条消息…（回车发送，Shift+回车换行）"
                  @keyup.enter.stop.prevent="onPressEnter"
                />

                <!-- 新增：表情 + 添加附件 -->
                <div class="chat-input-actions">
                  <!-- 表情 -->
                  <el-popover
                    placement="top-start"
                    width="260"
                    trigger="click"
                  >
                    <template #reference>
                      <button class="icon-btn" type="button">
                        <span class="emoji-trigger">😊</span>
                      </button>
                    </template>
                    <div class="emoji-panel">
                      <span
                        v-for="e in emojiList"
                        :key="e"
                        class="emoji-item"
                        @click="appendEmoji(e)"
                      >
                        {{ e }}
                      </span>
                    </div>
                  </el-popover>

                  <!-- 加号：附件 -->
                  <el-popover
                    placement="top-start"
                    width="220"
                    trigger="click"
                  >
                    <template #reference>
                      <button class="icon-btn plus" type="button">
                        <el-icon><Plus /></el-icon>
                      </button>
                    </template>
                    <div class="attach-panel">
                      <div class="attach-item" @click="triggerSelectFile('image')">
                        <el-icon><Picture /></el-icon>
                        <span>照片</span>
                      </div>
                      <div class="attach-item" @click="triggerSelectFile('video')">
                        <el-icon><VideoCamera /></el-icon>
                        <span>视频</span>
                      </div>
                      <div class="attach-item" @click="triggerSelectFile('file')">
                        <el-icon><Folder /></el-icon>
                        <span>文件</span>
                      </div>
                      <div class="attach-item" @click="sendLocation">
                        <el-icon><Position /></el-icon>
                        <span>位置</span>
                      </div>
                    </div>
                  </el-popover>

                  <!-- 隐藏的文件选择 input -->
                  <input
                    ref="imageInputRef"
                    type="file"
                    accept="image/*"
                    class="hidden-file-input"
                    @change="onFileSelected('image', $event)"
                  />
                  <input
                    ref="videoInputRef"
                    type="file"
                    accept="video/*"
                    class="hidden-file-input"
                    @change="onFileSelected('video', $event)"
                  />
                  <input
                    ref="fileInputRef"
                    type="file"
                    class="hidden-file-input"
                    @change="onFileSelected('file', $event)"
                  />
                </div>

                <div class="chat-input-footer">
                  <span class="hint">
                    已接入后台实时聊天，消息会自动保存；如连接异常可刷新页面重试
                  </span>
                  <el-button
                    type="primary"
                    size="small"
                    :disabled="!inputText.trim() || !activeChatId"
                    @click="handleSend"
                  >
                    发送
                  </el-button>
                </div>
              </div>

            </div>
          </template>

          <template v-else>
            <div class="chat-placeholder">
              <h2>选择一位已匹配的 TA 开始聊天</h2>
              <p>
                左侧列表中点选某位 TA，我们会先为你播放一条 15 秒广告来解锁本次聊天。
              </p>
              <p>若已开通 VIP+，广告界面会自动允许你跳过广告直接进入聊天。</p>
            </div>
          </template>
        </section>
      </div>

      <!-- 15 秒强制广告弹窗（每位 TA 单独解锁） -->
      <ForcedAdDialog
        v-model="showGate"
        :ad="chatAd"
        :seconds="requiredSeconds"
        :vip-plus="vipPlus"
        @finished="onGateFinishedWrapper"
        @see="handleGateSeeAdFromChat"
      />
    </main>
  </div>
</template>

<script setup>
defineOptions({ name: 'ChatListView' })

import {
  ref,
  reactive,
  computed,
  onMounted,
  watch,
  nextTick,
  onBeforeUnmount,
} from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import {
  User,
  Setting,
  ChatLineSquare,
  Plus,
  Picture,
  Folder,
  VideoCamera,
  Position,
} from '@element-plus/icons-vue'

import api, {
  getMatchMutual,
  getChatHistory,
  sendChatMessage,
  uploadChatFile, 
} from '@/api'
import ForcedAdDialog from '@/components/ForcedAdDialog.vue'
import { useAdGateForChat } from '@/composables/useAdGateForChat'
import { useChatUnreadBadge } from '@/composables/useChatUnreadBadge'

// ====== 左侧菜单 ======
const router = useRouter()
const route = useRoute()
const defaultActive = ref('chat')

const onSelect = (key) => {
  if (key === 'display') {
    router.push('/main')
  } else if (key === 'match') {
    router.push('/match')
  } else if (key === 'chat') {
    // 已经在聊天中心
  }
}
// 把后端返回的相对路径 /static/... 转成完整 URL
function buildStaticUrl(path) {
  if (!path) return ''
  const s = String(path)

  // 已经是 http/https 就直接用
  if (/^https?:\/\//i.test(s)) return s

  // 从 axios baseURL 推导后端根地址，例如 http://172.20.60.50:8000
  let base = api?.defaults?.baseURL || ''
  if (!base) return s

  // 去掉末尾斜杠
  base = base.replace(/\/+$/, '')
  // 去掉 /api 前缀
  base = base.replace(/\/api$/i, '')

  const cleanPath = s.startsWith('/') ? s : '/' + s
  return base + cleanPath
}

// ====== 用户 & 会话列表 ======
const uid = Number(sessionStorage.getItem('uid') || 0)
const { totalUnread, totalUnreadDisplay, setTotalUnread } = useChatUnreadBadge()

// WebSocket 实例 & 状态
const ws = ref(null)
const isWsConnected = ref(false)

const mutual = reactive({
  items: [],
  loading: false,
})

async function loadMutual() {
  mutual.loading = true
  try {
    const { data } = await getMatchMutual(uid, { page: 1, page_size: 1000 })
    const items = Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data)
        ? data
        : []
    mutual.items = items
  } catch (e) {
    console.error('getMatchMutual error:', e)
    mutual.items = []
  } finally {
    mutual.loading = false
  }
}

// 当前正在聊天的对象 id
const activeChatId = ref(null)
const activeUser = computed(
  () => mutual.items.find((u) => u.id === activeChatId.value) || null,
)

// ====== 每个 TA 的广告解锁状态 ======
const UNLOCK_KEY = 'chat_unlocked_ids_v1'
const unlockedIds = ref(new Set())

let wsReconnectTimer = null
let wsHeartbeatTimer = null

function startHeartbeat() {
  stopHeartbeat()
  wsHeartbeatTimer = window.setInterval(() => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
    try {
      ws.value.send(JSON.stringify({ type: 'ping' }))
    } catch (e) {
      console.warn('[ChatList] heartbeat send fail:', e)
    }
  }, 20000)
}

function stopHeartbeat() {
  if (wsHeartbeatTimer) {
    clearInterval(wsHeartbeatTimer)
    wsHeartbeatTimer = null
  }
}

function scheduleReconnect() {
  if (wsReconnectTimer) return
  wsReconnectTimer = window.setTimeout(() => {
    wsReconnectTimer = null
    initWs()
  }, 5000)
}

function loadUnlockedFromStorage() {
  try {
    const raw = sessionStorage.getItem(UNLOCK_KEY)
    if (!raw) return
    const arr = JSON.parse(raw)
    if (!Array.isArray(arr)) return
    const s = new Set()
    for (const v of arr) {
      const n = Number(v)
      if (Number.isFinite(n) && n > 0) s.add(n)
    }
    unlockedIds.value = s
  } catch (e) {
    console.warn('[ChatList] loadUnlocked error:', e)
  }
}

function persistUnlocked() {
  try {
    const arr = Array.from(unlockedIds.value || [])
    sessionStorage.setItem(UNLOCK_KEY, JSON.stringify(arr))
  } catch (e) {
    console.warn('[ChatList] persistUnlocked error:', e)
  }
}

function markUnlocked(id) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return
  const s = unlockedIds.value
  if (!s.has(n)) {
    s.add(n)
    persistUnlocked()
  }
}

function isUnlocked(id) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return false
  return unlockedIds.value.has(n)
}

// ====== 聊天内容（按用户分组） ======
const messagesMap = reactive({}) // { [userId]: UiMessage[] }

// ====== 未读消息计数（前端本地） ======
const UNREAD_KEY = `chat_unread_map_v1_${uid}`
const unreadMap = reactive({}) // { [userId]: number }

// 本地 total，仅用于计算；真正展示用全局 useChatUnreadBadge
const totalUnreadLocal = computed(() => {
  return Object.values(unreadMap).reduce((sum, v) => {
    const n = Number(v)
    return sum + (Number.isFinite(n) && n > 0 ? n : 0)
  }, 0)
})

function getUnread(id) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return 0
  return unreadMap[n] || 0
}

function setUnread(id, count) {
  const n = Number(id)
  const c = Math.max(0, Number(count) || 0)
  if (!Number.isFinite(n) || n <= 0) return
  if (c === 0) {
    delete unreadMap[n]
  } else {
    unreadMap[n] = c
  }
  persistUnread()
}

function incUnread(id, delta = 1) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return
  const cur = unreadMap[n] || 0
  unreadMap[n] = cur + (Number(delta) || 1)
  persistUnread()
}

function clearUnread(id) {
  setUnread(id, 0)
}

function loadUnread() {
  try {
    const raw = sessionStorage.getItem(UNREAD_KEY)
    if (raw) {
      const obj = JSON.parse(raw)
      if (obj && typeof obj === 'object') {
        for (const [k, v] of Object.entries(obj)) {
          const uidNum = Number(k)
          const cnt = Number(v)
          if (Number.isFinite(uidNum) && uidNum > 0 && cnt > 0) {
            unreadMap[uidNum] = cnt
          }
        }
      }
    }
  } catch (e) {
    console.warn('[ChatList] loadUnread error:', e)
  }
  // 初始化时把总未读同步到全局 store
  setTotalUnread(totalUnreadLocal.value || 0)
}

function persistUnread() {
  try {
    const plain = {}
    for (const [k, v] of Object.entries(unreadMap)) {
      const cnt = Number(v)
      if (cnt > 0) plain[k] = cnt
    }
    sessionStorage.setItem(UNREAD_KEY, JSON.stringify(plain))

    const n = totalUnreadLocal.value || 0
    // 给其他页面用的总未读
    sessionStorage.setItem(
      `chat_unread_total_v1_${uid}`,
      String(n),
    )
    // 同时更新全局 store，让 MainLayout / MatchDisplay 立刻响应
    setTotalUnread(n)
  } catch (e) {
    console.warn('[ChatList] persistUnread error:', e)
  }
}


// ====== 输入区 & 当前会话 ======
const inputText = ref('')
const messagesRef = ref(null)
// 表情简单先弄一小排常用的
const emojiList = [
  '😀','😁','😂','🤣','😊','😍','😘','😜',
  '😎','😢','😭','😡','👍','👎','🙏','👏',
]

const imageInputRef = ref(null)
const videoInputRef = ref(null)
const fileInputRef = ref(null)

const currentMessages = computed(() => {
  if (!activeChatId.value) return []
  const arr = messagesMap[activeChatId.value]
  return Array.isArray(arr) ? arr : []
})

function fileUrl(path) {
  if (!path) return ''
  const s = String(path)

  // 已经是 http / https 的完整地址了，直接用
  if (/^https?:\/\//i.test(s)) {
    return s
  }

  // 标准化为以 / 开头的路径，比如 "/static/chat/20251119/xxx.png"
  const cleanPath = s.startsWith('/') ? s : '/' + s

  // 1）优先从 axios 的 baseURL 推出后端根地址
  // 例如 baseURL = "http://172.20.60.50:8000/api/"
  // 则 backendOrigin = "http://172.20.60.50:8000"
  let backendOrigin = ''
  if (api && api.defaults && api.defaults.baseURL) {
    backendOrigin = api.defaults.baseURL
      .replace(/\/+$/, '')      // 去掉结尾的 /
      .replace(/\/api$/i, '')   // 去掉尾部的 /api
  }

  // 2）兜底用当前前端域名（如果你将来前后端同域部署，也能用）
  if (!backendOrigin && typeof window !== 'undefined') {
    backendOrigin = window.location.origin
  }

  // 3）再兜底，实在推不出来就返回原始相对路径（至少不会报错）
  if (!backendOrigin) {
    return cleanPath
  }

  return backendOrigin + cleanPath
}

function ensureMsgArray(id) {
  if (!messagesMap[id]) messagesMap[id] = []
}

function formatTime(ts) {
  try {
    const d = ts instanceof Date ? ts : new Date(ts)
    if (Number.isNaN(d.getTime())) return ''
    const h = String(d.getHours()).padStart(2, '0')
    const m = String(d.getMinutes()).padStart(2, '0')
    return `${h}:${m}`
  } catch {
    return ''
  }
}

function lastMessagePreview(userId) {
  const arr = messagesMap[userId]
  if (!Array.isArray(arr) || !arr.length) return ''
  const last = arr[arr.length - 1]
  const text = String(last.content || '')
  if (text.length <= 18) return text
  return text.slice(0, 18) + '…'
}

function scrollToBottom() {
  const el = messagesRef.value
  if (!el) return
  try {
    el.scrollTop = el.scrollHeight || 0
  } catch {
    //
  }
}

watch(currentMessages, () => {
  nextTick(() => scrollToBottom())
})

function mapServerMsgToUi(raw) {
  if (!raw) return null

  const fromId = Number(raw.from_user_id ?? raw.fromId ?? raw.from)
  const from = fromId === uid ? 'me' : 'other'

  const msgType = raw.msg_type ?? raw.msgType ?? 'text'
  const created =
    raw.created_at ?? raw.createdAt ?? raw.ts ?? new Date().toISOString()

  let content = raw.content ?? ''
  let fileName = raw.file_name ?? raw.fileName ?? raw.filename ?? ''

  // 兼容：如果后端把 content 做成 JSON，可以在这里解析
  if (typeof content === 'string' && msgType !== 'text') {
    try {
      const obj = JSON.parse(content)
      if (obj && typeof obj === 'object') {
        content = obj.url || obj.content || content
        fileName = obj.name || fileName
      }
    } catch {
      // 忽略 JSON 解析失败，按原样用字符串
    }
  } else if (content && typeof content === 'object' && msgType !== 'text') {
    // 后端如果直接给了对象 { url, name }
    fileName = content.name || fileName
    content = content.url || content.content || ''
  }

  // ✅ 关键：把 /static/... 补成完整后端 URL
  if (msgType !== 'text') {
    content = buildStaticUrl(content)
  }

  const id =
    raw.id ??
    `${fromId || 'u'}-${created}-${Math.random().toString(36).slice(2)}`

  return {
    id,
    from,
    msg_type: msgType,
    content: String(content ?? ''),
    file_name: fileName || '',
    ts: created,
    _raw: raw,
  }
}



function goProfile(id) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return
  router.push({ name: 'displayChat', params: { uid: n } })
}

// 历史消息
async function loadHistoryForUser(otherId) {
  const n = Number(otherId)
  if (!Number.isFinite(n) || n <= 0) return
  try {
    const { data } = await getChatHistory(uid, n, { limit: 100 })
    let items = []
    if (Array.isArray(data?.items)) items = data.items
    else if (Array.isArray(data)) items = data
    else if (Array.isArray(data?.data)) items = data.data

    const mapped = items
      .map((it) => mapServerMsgToUi(it))
      .filter((x) => !!x)
    ensureMsgArray(n)
    messagesMap[n].splice(0, messagesMap[n].length, ...mapped)
  } catch (e) {
    console.error('getChatHistory error:', e)
    ensureMsgArray(n)
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  if (!activeChatId.value) {
    ElMessage.warning('请先在左侧选择一位聊天对象')
    return
  }
  const toId = activeChatId.value

  const wsPayload = {
    type: 'chat',
    to_user_id: toId,
    content: text,
    msg_type: 'text',
  }

  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    try {
      ws.value.send(JSON.stringify(wsPayload))
    } catch (e) {
      console.error('[ChatList] ws send error:', e)
      ElMessage.error('发送失败，请稍后重试')
      return
    }
  } else {
    try {
      await sendChatMessage({
        from_user_id: uid,
        to_user_id: toId,
        content: text,
        msg_type: 'text',
      })
      await loadHistoryForUser(toId)
    } catch (e) {
      console.error('[ChatList] sendChatMessage error:', e)
      ElMessage.error('发送失败，请稍后重试')
      return
    }
  }

  inputText.value = ''
  nextTick(() => scrollToBottom())
}

function appendEmoji(e) {
  inputText.value += e
}

function triggerSelectFile(kind) {
  if (!activeChatId.value) {
    ElMessage.warning('请先在左侧选择一位聊天对象')
    return
  }
  if (kind === 'image' && imageInputRef.value) {
    imageInputRef.value.click()
  } else if (kind === 'video' && videoInputRef.value) {
    videoInputRef.value.click()
  } else if (kind === 'file' && fileInputRef.value) {
    fileInputRef.value.click()
  }
}

async function onFileSelected(kind, evt) {
  const input = evt?.target
  const file = input?.files?.[0]
  // 立刻清空，否则同一个文件再次选择不会触发 change
  if (input) input.value = ''

  if (!file) return

  if (!activeChatId.value) {
    ElMessage.warning('请先在左侧选择一位聊天对象')
    return
  }

  try {
    const toId = activeChatId.value

    // 1）上传文件到后端（签名：文件 + 选项对象）
    const res = await uploadChatFile(file, {
      from_user_id: uid,   // 当前登录用户 id
      to_user_id: toId,    // 正在聊天的对方 id
      kind,                // 'image' | 'video' | 'file'
    })
    console.log('[ChatList] upload ok:', res)

    // 2）上传成功后，直接重新拉一遍当前会话的历史消息
    await loadHistoryForUser(toId)
    nextTick(() => scrollToBottom())
  } catch (e) {
    console.error('[ChatList] upload error:', e, e?.response?.data)
    const detail =
      e?.response?.data?.detail ||
      e?.response?.data?.error ||
      '上传失败，请稍后重试'
    ElMessage.error(detail)
  }
}


async function sendRichMessage(toId, url, kind) {
  const msgType =
    kind === 'image'
      ? 'image'
      : kind === 'video'
      ? 'video'
      : kind === 'file'
      ? 'file'
      : kind === 'location'
      ? 'location'
      : 'text'

  const wsOk = ws.value && ws.value.readyState === WebSocket.OPEN

  const localMsg = {
    id: `local-${Date.now()}`,
    from: 'me',
    msg_type: msgType,
    content: url,
    ts: new Date().toISOString(),
  }

  // 本地先插一条，提升体验
  ensureMsgArray(toId)
  messagesMap[toId].push(localMsg)
  nextTick(() => scrollToBottom())

  const payload = {
    type: 'chat',
    to_user_id: toId,
    content: url,
    msg_type: msgType,
  }

  try {
    if (wsOk) {
      ws.value.send(JSON.stringify(payload))
    } else {
      await sendChatMessage({
        from_user_id: uid,
        to_user_id: toId,
        content: url,
        msg_type: msgType,
      })
    }
  } catch (e) {
    console.error('[ChatList] send rich error:', e)
    ElMessage.error('发送失败，请稍后重试')
  }
}

function sendLocation() {
  if (!navigator.geolocation) {
    ElMessage.error('当前浏览器不支持定位')
    return
  }
  if (!activeChatId.value) {
    ElMessage.warning('请先在左侧选择一位聊天对象')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords
      // 简单用高德/百度/谷歌地图链接都可以，这里先用通用的
      const url = `https://www.google.com/maps?q=${latitude},${longitude}`
      sendRichMessage(activeChatId.value, url, 'location')
    },
    (err) => {
      console.error(err)
      ElMessage.error('获取位置失败，请检查浏览器定位权限')
    },
  )
}

function onPressEnter(e) {
  if (e.shiftKey) {
    inputText.value += '\n'
  } else {
    e.preventDefault()
    handleSend()
  }
}

// ====== WebSocket 接收消息 ======
function buildWsUrl() {
  let base = api?.defaults?.baseURL || ''
  try {
    if (base.endsWith('/')) base = base.slice(0, -1)
    const u = new URL(base)
    const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProto}//${u.host}/api/chat/ws/${uid}`
  } catch (e) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${proto}//${host}/api/chat/ws/${uid}`
  }
}

function handleIncomingWs(evt) {
  try {
    const raw = JSON.parse(evt.data)
    if (!raw || raw.type !== 'chat') return
    const fromId = Number(raw.from_user_id)
    const toId = Number(raw.to_user_id)
    if (!Number.isFinite(fromId) || !Number.isFinite(toId)) return
    if (fromId !== uid && toId !== uid) return

    const otherId = fromId === uid ? toId : fromId
    ensureMsgArray(otherId)
    const uiMsg = mapServerMsgToUi(raw)
    if (uiMsg) {
      messagesMap[otherId].push(uiMsg)

      // 收到对方发来的消息：未读 + 通知
      if (fromId !== uid) {
        const pageVisible = document.visibilityState === 'visible'
        const isCurrentChat = activeChatId.value === otherId

        // 不在当前会话 或 页面不在前台，才记未读
        if (!(isCurrentChat && pageVisible)) {
          incUnread(otherId)
        }

        // 非当前会话时弹通知
        if (activeChatId.value !== otherId) {
          const otherUser =
            mutual.items.find((u) => u.id === otherId) || {}
          const title =
            otherUser.nickname ||
            otherUser.username ||
            `来自 ID${otherId} 的新消息`
          const text = String(uiMsg.content || '')
          const preview =
            text.length <= 30 ? text : text.slice(0, 30) + '…'

          ElNotification({
            title,
            message: preview,
            position: 'bottom-right',
            duration: 4500,
            onClick: () => {
              router.push({ name: 'chat', params: { id: otherId } })
            },
          })
        }
      }

      if (activeChatId.value === otherId) {
        nextTick(() => scrollToBottom())
      }
    }
  } catch (e) {
    console.error('[ChatList] WS message parse error:', e)
  }
}

function initWs() {
  if (!uid) return
  if (ws.value && ws.value.readyState === WebSocket.OPEN) return

  const url = buildWsUrl()
  try {
    const socket = new WebSocket(url)
    ws.value = socket

    socket.onopen = () => {
      isWsConnected.value = true
      console.log('[ChatList] WebSocket connected:', url)
      stopHeartbeat()
      startHeartbeat()
    }

    socket.onmessage = (evt) => {
      handleIncomingWs(evt)
    }

    socket.onclose = () => {
      console.log('[ChatList] WebSocket closed')
      isWsConnected.value = false
      ws.value = null
      stopHeartbeat()
      scheduleReconnect()
    }

    socket.onerror = (err) => {
      console.error('[ChatList] WebSocket error', err)
      isWsConnected.value = false
      scheduleReconnect()
    }
  } catch (e) {
    console.error('[ChatList] WebSocket init error:', e)
    scheduleReconnect()
  }
}

onBeforeUnmount(() => {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  stopHeartbeat()
  if (ws.value) {
    try {
      ws.value.close()
    } catch {}
    ws.value = null
  }
})

// ====== 广告闸门逻辑 ======
const pendingChatUserId = ref(null)

const {
  showGate,
  chatAd,
  requiredSeconds,
  vipPlus,
  openAdBeforeChat,
  handleGateFinished,
  handleGateSeeAd,
} = useAdGateForChat(router)

const handleGateSeeAdFromChat = () => handleGateSeeAd('chat')

async function onClickUser(u) {
  const id = Number(u?.id)
  if (!Number.isFinite(id) || id <= 0) return

  if (isUnlocked(id)) {
    await setActiveChat(id)
    router.push({ path: `/chat/${id}` }).catch(() => {})
    return
  }

  pendingChatUserId.value = id
  const intercepted = await openAdBeforeChat(id, { meId: uid })

  if (!intercepted) {
    markUnlocked(id)
    await setActiveChat(id)
  }
}

async function onGateFinishedWrapper() {
  const id = Number(pendingChatUserId.value)
  if (Number.isFinite(id) && id > 0) {
    markUnlocked(id)
    await setActiveChat(id)
  }
  handleGateFinished()
}

// URL -> 当前会话 id （兼容 /chat/:id）
async function syncActiveFromRoute() {
  const raw = route.params.id || route.query.with
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return
  markUnlocked(n)
  await setActiveChat(n)
}

async function setActiveChat(id) {
  const n = Number(id)
  if (!Number.isFinite(n) || n <= 0) return
  activeChatId.value = n
  clearUnread(n) // ✅ 选中会话时清空未读
  await loadHistoryForUser(n)
  nextTick(() => scrollToBottom())
}

watch(
  () => route.params.id,
  () => {
    syncActiveFromRoute()
  },
)
watch(
  () => route.query.with,
  () => {
    syncActiveFromRoute()
  },
)

// ====== 生命周期：初始化 ======
onMounted(async () => {
  if (!uid) {
    ElMessage.error('未登录，无法使用聊天功能')
    router.push('/login')
    return
  }

  loadUnlockedFromStorage()
  loadUnread()
  await loadMutual()
  await syncActiveFromRoute()
  initWs()
})
</script>

<style scoped>
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
  overflow: hidden;
}

/* 左侧卡片样式 */
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

/* 主体两列布局 */
.chat-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  height: 100%;
}

/* 左：会话列表 */
.chat-list-pane {
  background: #ffffff;
  border-radius: 16px;
  padding: 12px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-list-header {
  padding: 4px 4px 10px;
  border-bottom: 1px solid #f3f4f6;
  margin-bottom: 8px;
}

.chat-list-header .title {
  font-weight: 600;
  color: #111827;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chat-list-header .sub {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

/* 通用红点样式 */
.unread-pill,
.menu-unread-pill,
.avatar-unread-pill {
  display: inline-flex;
  min-width: 18px;
  padding: 0 5px;
  height: 18px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  justify-content: center;
  align-items: center;
}

/* 菜单文案 + 红点 */
.menu-chat-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 头像右上角红点 */
.avatar-badge-wrapper {
  position: relative;
  display: inline-block;
}

.avatar-unread-pill {
  position: absolute;
  right: -2px;
  top: -2px;
  transform: translate(25%, -25%);
  font-size: 10px;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
}

.chat-list {
  overflow-y: auto;
  padding-right: 4px;
}

.chat-list-item {
  display: flex;
  gap: 10px;
  padding: 8px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.16s ease, transform 0.08s ease;
  align-items: center;
}

.chat-list-item:hover {
  background: #f9fafb;
}

.chat-list-item.active {
  background: #eef2ff;
}

.chat-list-item.skeleton {
  cursor: default;
}

.chat-list-item .meta {
  flex: 1;
  min-width: 0;
}

.chat-list-item .line-1 {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6px;
}

.chat-list-item .name {
  font-weight: 600;
  color: #111827;
  max-width: 120px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-list-item .age-city {
  font-size: 12px;
  color: #6b7280;
}

.chat-list-item .line-2 {
  font-size: 12px;
  color: #4b5563;
  margin-top: 2px;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-list-item .lock-line {
  margin-top: 4px;
}

.chat-list-item .action-line {
  margin-top: 2px;
  font-size: 12px;
}

/* 右：聊天窗口 */
.chat-pane {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-header .left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-header .info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-header .name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.chat-header .name {
  font-size: 16px;
  font-weight: 600;
}

.chat-header .tag {
  font-size: 12px;
  padding: 2px 6px;
  background: #f3f4ff;
  border-radius: 999px;
  color: #4f46e5;
}

.chat-header .sub {
  font-size: 12px;
  color: #6b7280;
}

.chat-header .right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-btn {
  padding: 0 10px;
  font-size: 12px;
}

/* 聊天主体 */
.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  padding: 12px 16px;
  overflow-y: auto;
  background: #f9fafb;
}

.msg-row {
  display: flex;
  margin-bottom: 8px;
}

.msg-row.me {
  justify-content: flex-end;
}

.msg-row.other {
  justify-content: flex-start;
}

.msg-row .bubble {
  max-width: 70%;
  padding: 8px 10px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.msg-row.me .bubble {
  background: #4f46e5;
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.msg-row.other .bubble {
  background: #ffffff;
  color: #111827;
  border-bottom-left-radius: 4px;
}

.msg-row .text {
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-row .time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}

.chat-empty {
  text-align: center;
  margin-top: 30px;
  font-size: 13px;
  color: #9ca3af;
}

/* 输入区 */
.chat-input {
  border-top: 1px solid #e5e7eb;
  padding: 10px 14px 12px;
  background: #ffffff;
}
.chat-input-actions {
  margin-top: 4px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icon-btn.plus {
  border: 1px solid #e5e7eb;
}

.icon-btn:hover {
  background: #f3f4f6;
}

.hidden-file-input {
  display: none;
}
.emoji-trigger {
  font-size: 18px;
  line-height: 1;
}

.emoji-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
}

.emoji-item {
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.emoji-item:hover {
  background: #f3f4f6;
}

.attach-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attach-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 6px;
}

.attach-item:hover {
  background: #f3f4f6;
}

.msg-image {
  max-width: 220px;
  border-radius: 8px;
  display: block;
}

.msg-video {
  max-width: 260px;
  border-radius: 8px;
  border-radius: 8px;
}

.msg-file {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f3f4f6;
  text-decoration: none;
  color: #111827;
  font-size: 13px;
}

.msg-file .file-icon {
  font-size: 16px;
}

.msg-file:hover {
  background: #e5e7eb;
}

.chat-input-footer {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-input-footer .hint {
  font-size: 12px;
  color: #9ca3af;
}

/* 占位态 */
.chat-placeholder {
  height: 100%;
  padding: 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: #4b5563;
  gap: 8px;
}

.chat-placeholder h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.chat-placeholder p {
  font-size: 13px;
}

/* 响应式 */
@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .chat-list-pane {
    max-height: 220px;
  }

  .content {
    padding: 8px;
  }
}
</style>
