// frontend/src/composables/useChatUnreadBadge.js
import { ref, computed } from 'vue'

const totalUnread = ref(0)

function setTotalUnread(n) {
  const v = Number(n)
  totalUnread.value = Number.isFinite(v) && v > 0 ? v : 0
}

function syncFromStorage(uid) {
  if (!uid) return
  try {
    const raw = sessionStorage.getItem(`chat_unread_total_v1_${uid}`) || '0'
    setTotalUnread(Number(raw))
  } catch (e) {
    console.warn('[chat-unread-badge] syncFromStorage error:', e)
  }
}

const totalUnreadDisplay = computed(() => {
  const n = totalUnread.value
  if (!n) return ''
  return n > 99 ? '99+' : String(n)
})

export function useChatUnreadBadge() {
  return {
    totalUnread,
    totalUnreadDisplay,
    setTotalUnread,
    syncFromStorage,
  }
}
