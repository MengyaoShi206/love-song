// frontend/src/api/index.js
import axios from 'axios'
// const api = axios.create({ baseURL: 'http://127.0.0.1:8000/api/' })
const api = axios.create({ baseURL: 'http://172.20.60.50:8000/api/' })

export const loginUser    = (payload) => api.post('user/login', payload)
export const registerUser = (payload) => api.post('user/register', payload)
export const getDisplay = (uid) => api.get(`user/main/${uid}`)
export const updateProfile        = (uid, data) => api.put(`user/profile/${uid}`, data)
export const recomputeCompletion  = (uid)       => api.post(`user/completion/${uid}`)
export const getMatchLikes = (uid, params) => api.get(`user/match/likes/${uid}`, { params })
export const getMatchMutual = (uid, params) => api.get(`user/match/mutual/${uid}`, { params })