/** axios 实例：统一 baseURL / Bearer token / 401 跳登录 / 后端 detail 错误提示。 */
import axios, { AxiosError } from 'axios'
import { message } from 'antd'

type ErrorDetail = string | { message?: string; [key: string]: unknown }

export const http = axios.create({
  baseURL: '/api',
  timeout: 300000, // 分析/生成任务一期为同步执行（D-T1），需要较长超时
})

export const TOKEN_KEY = 'forge_scrm_token'

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<{ detail?: ErrorDetail }>) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
      return Promise.reject(error)
    }
    const detailMessage = typeof detail === 'string' ? detail : detail?.message
    const handledByCollectionPage = status === 409 && typeof detail === 'object' && detail?.code === 'COLLECTION_TASK_DUPLICATE'
    if (!handledByCollectionPage) {
      message.error(detailMessage || error.message || '请求失败')
    }
    return Promise.reject(error)
  },
)

export function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
