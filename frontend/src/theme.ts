/** 全站视觉 token：对齐 copy-wms 紫色主色与状态语义。 */
import type { ThemeConfig } from 'antd'

export const PRIMARY_COLOR = '#7c3aed'

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: PRIMARY_COLOR,
    colorLink: PRIMARY_COLOR,
    colorInfo: PRIMARY_COLOR,
    borderRadius: 6,
    colorBgLayout: '#ffffff',
    fontFamily:
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    fontSize: 14,
  },
  components: {
    Menu: {
      fontSize: 14,
      itemHeight: 32,
      itemMarginBlock: 2,
      itemMarginInline: 0,
      itemPaddingInline: 8,
      itemBorderRadius: 6,
      iconSize: 18,
      collapsedIconSize: 18,
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      darkItemColor: '#e5e5e5',
      darkItemHoverColor: '#ffffff',
      darkItemHoverBg: 'rgba(38, 38, 38, 0.8)',
      darkItemSelectedBg: PRIMARY_COLOR,
      darkItemSelectedColor: '#ffffff',
      darkGroupTitleColor: '#a3a3a3',
    },
    Layout: {
      siderBg: '#171717',
      triggerBg: '#171717',
      headerHeight: 56,
      headerBg: '#ffffff',
      headerPadding: '0 24px',
    },
    Button: {
      borderRadius: 6,
    },
    Card: {
      borderRadiusLG: 8,
      boxShadowTertiary: 'none',
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#737373',
      borderColor: '#e5e5e5',
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
  待生成: 'default',
  待推送: 'default',
  pending: 'default',
  生成中: 'orange',
  推送中: 'orange',
  已推送: 'green',
  默认通过: 'green',
  部分成功: 'gold',
  partial_success: 'gold',
}

export function statusTagColor(status?: string | null): string {
  if (!status) return 'default'
  return STATUS_TAG_COLOR[status] ?? 'default'
}

/** 将后端保留状态映射为二期默认通过后的用户可见状态。 */
export function displayStatus(status: string | null | undefined, defaultStatus: string): string {
  return status === '待审核' ? defaultStatus : status || '—'
}

/** 状态筛选不展示后端预留状态，但保留其它筛选值与查询参数。 */
export function visibleStatusOptions<T extends { value: string }>(options: T[]): T[] {
  return options.filter((option) => option.value !== '待审核')
}

export const TABLE_PAGINATION = {
  position: ['bottomRight'] as ('bottomRight')[],
  showSizeChanger: false,
}
