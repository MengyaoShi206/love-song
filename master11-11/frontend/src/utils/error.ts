// src/utils/error.ts
export function parseAxiosError(e: any) {
    const status = e?.response?.status
    const data   = e?.response?.data
    const url    = e?.config?.url
    const method = e?.config?.method
    const reqId  = e?.response?.headers?.['x-request-id'] || e?.response?.headers?.['x-correlation-id']
  
    // detail 常见位置：{detail} / {message} / {error}
    const detail = data?.detail ?? data?.message ?? data?.error
    const msg    = detail || e?.message || String(e)
  
    // 还有人把 detail 做成数组（FastAPI/Pydantic 校验）
    const detailList = Array.isArray(data?.detail) ? data.detail : undefined
  
    return { status, url, method, msg, data, detailList, reqId }
  }
  