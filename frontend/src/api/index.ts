// src/api/index.ts
import axios from 'axios'
import { parseAxiosError } from '@/utils/error'
import request from './request'


export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(cfg => {
  // 方便看请求体
  console.log('➡️[REQ]', cfg.method?.toUpperCase(), cfg.url, cfg.data ?? cfg.params)
  return cfg
})

api.interceptors.response.use(
  (res) => {
    console.log('✅[RES]', res.status, res.config.url, res.data)
    return res
  },
  (e) => {
    const info = parseAxiosError(e)
    console.error('❌[ERR]', info.status, info.method?.toUpperCase(), info.url, info.msg, info)
    // 继续把错误抛出，交给你的 catch 处理
    return Promise.reject(e)
  }
)

// 你原有的封装
export function updateProfile(uid: number, payload: any) {
  return api.put(`/user/profile/${uid}`, payload)
}

export function getDisplay(uid: number, meId?: number) {
  return request.get(`/api/user/display/${uid}`, {
    params: meId ? { me_id: meId } : {}
  })
}