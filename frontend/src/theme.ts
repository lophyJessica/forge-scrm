/** 全站视觉 token：对齐 copy-wms 紫色主色与状态语义。 */
import type { ThemeConfig } from 'antd'

export const PRIMARY_COLOR = '#7c3aed'

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: PRIMARY_COLOR,
    colorLink: PRIMARY_COLOR,
    colorInfo: PRIMARY_COLOR,
    borderRadius: 6,
    colorBgLayout: '#f5f5f7',
  },
  components: {
    Menu: {
      darkItemSelectedBg: PRIMARY_COLOR,
      darkItemSelectedColor: '#fff',
      darkItemHoverBg: 'rgba(124, 58, 237, 0.35)',
    },
    Layout: {
      siderBg: '#141414',
      triggerBg: '#141414',
    },
    Button: {
      borderRadius: 6,
    },
    Card: {
      borderRadiusLG: 8,
    },
  },
}

const STATUS_TAG_COLOR: Record<string, string> = {
  启用: 'green',
  已通过: 'green',
  已生效: 'green',
  已完成: 'green',
  已选定: 'green',
  已确认: 'green',
  已生成脚本: 'green',
  已使用: 'green',
  success: 'green',
  停用: 'red',
  已停用: 'red',
  已废弃: 'red',
  失败: 'red',
  已过期: 'red',
  failed: 'red',
  待审核: 'orange',
  待筛选: 'orange',
  进行中: 'orange',
  执行中: 'orange',
  检索中: 'orange',
  整理中: 'orange',
  searching: 'orange',
  organizing: 'orange',
  running: 'orange',
  草稿: 'default',
  待执行: 'default',
  pending: 'default',
  部分成功: 'gold',
  partial_success: 'gold',
}

export function statusTagColor(status?: string | null): string {
  if (!status) return 'default'
  return STATUS_TAG_COLOR[status] ?? 'default'
}

export const TABLE_PAGINATION = {
  position: ['bottomRight'] as ('bottomRight')[],
  showSizeChanger: false,
}
