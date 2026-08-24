/** 登录态（zustand）：token + 当前用户 + 权限判定。 */
import { create } from 'zustand'
import { http, TOKEN_KEY } from '@/api/client'
import type { LoginResponse, UserOut } from '@/types'

const USER_KEY = 'forge_scrm_user'

function readUser(): UserOut | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as UserOut) : null
  } catch {
    return null
  }
}

interface AuthState {
  token: string | null
  user: UserOut | null
  mustChangePassword: boolean
  login: (username: string, password: string) => Promise<LoginResponse>
  logout: () => Promise<void>
  refreshMe: () => Promise<void>
  isAdmin: () => boolean
  can: (permission: string) => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY),
  user: readUser(),
  mustChangePassword: false,

  login: async (username, password) => {
    const { data } = await http.post<LoginResponse>('/auth/login', { username, password })
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    set({ token: data.access_token, user: data.user, mustChangePassword: data.must_change_password })
    return data
  },

  logout: async () => {
    try {
      await http.post('/auth/logout')
    } catch {
      // 一期 JWT 无服务端黑名单，登出失败也直接清本地
    }
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({ token: null, user: null, mustChangePassword: false })
  },

  refreshMe: async () => {
    const { data } = await http.get<UserOut>('/auth/me')
    localStorage.setItem(USER_KEY, JSON.stringify(data))
    set({ user: data })
  },

  isAdmin: () => get().user?.role === '管理员',

  // 管理员恒有全部权限；成员按 functional_permissions 显式授权（context/06 §2.2）
  can: (permission) => {
    const user = get().user
    if (!user) return false
    if (user.role === '管理员') return true
    return (user.functional_permissions || []).includes(permission)
  },
}))
