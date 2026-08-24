import { Result } from 'antd'
import type { ReactNode } from 'react'
import { useAuthStore } from '@/store/auth'

/** 路由守卫：仅管理员可见（context/06 §2.2 一期口径）。 */
export default function RequireAdmin({ children }: { children: ReactNode }) {
  const isAdmin = useAuthStore((s) => s.isAdmin)()
  if (!isAdmin) {
    return <Result status="403" title="403" subTitle="该功能仅管理员可用" />
  }
  return <>{children}</>
}
