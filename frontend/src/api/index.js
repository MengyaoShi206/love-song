// frontend/src/api/index.js
import axios from 'axios'

// 本机或内网服务地址，保持末尾带 /，下面所有 path 都不要以 / 开头
const api = axios.create({
  baseURL: 'http://172.20.60.50:8000/api/',
  timeout: 15000,
})
// import api from './request'

// ========== 账户 ==========
export const loginUser    = (payload)        => api.post('user/login', payload)
export const registerUser = (payload)        => api.post('user/register', payload)

// ========== 展示 / 资料 ==========
export const getDisplay             = (uid)       => api.get(`user/main/${uid}`)
export const updateProfile          = (uid, data) => api.put(`user/profile/${uid}`, data)
export const recomputeCompletion    = (uid)       => api.post(`user/completion/${uid}`)

// ========== 匹配 / 推荐 ==========
export const getMatchLikes     = (uid, params) => api.get(`user/match/likes/${uid}`, { params })
export const getMatchMutual    = (uid, params) => api.get(`user/match/mutual/${uid}`, { params })
export const getRecommendUsers = (uid, params) => api.get(`user/recommend/${uid}`, { params })
export const getLikedMe        = (uid, params) => api.get(`user/match/liked_me/${uid}`, { params })

// ========== 点赞（后端 /api/user/like，JSON 体传 liker_id/likee_id）==========
export const likeUser = (liker_id, likee_id) =>
  api.post('user/like', { liker_id, likee_id })

// ========== 广告（注意：都走 /api/user/ads 前缀，不要以 / 开头）==========
export const getAdList   = (params)   => api.get('user/ads', { params })
export const getAdDetail = (id)       => api.get(`user/ads/${id}`)

// ========== 自定义匹配 ==========
export const getManualMatch = (uid, params) => api.get(`user/match/custom/${uid}`, { params })
export const getProfileDetail = (uid, me_id) => api.get(`user/display/${uid}`, { params: { me_id } })

// ========== 聊天 ==========
export const getChatHistory = (meId, otherId, params = {}) =>
  api.get('chat/history', { params: { me_id: meId, other_id: otherId, ...params,},
  })

export const sendChatMessage = (payload) => api.post('chat/send', payload)

export function uploadChatFile(file, { from_user_id, to_user_id, kind }) {
  const form = new FormData()
  form.append('file', file)
  form.append('from_user_id', from_user_id)
  form.append('to_user_id', to_user_id)
  form.append('kind', kind || 'file')
  return api.post('/chat/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  // return api.post('/chat/upload', fd)
}

// 如项目里需要，也可以导出 axios 实例
export default api
