import { Button, Dropdown, Space } from 'antd'

/** 表格操作列：1–2 个文字按钮并排；超过 2 个时其余收入「更多」。 */
export function TableActions({ items }: { items: React.ReactNode[] }) {
  const nodes = items.filter(Boolean)
  if (nodes.length === 0) return null
  if (nodes.length <= 2) {
    return <Space size={8}>{nodes}</Space>
  }
  return (
    <Space size={8}>
      {nodes[0]}
      {nodes[1]}
      <Dropdown
        menu={{
          items: nodes.slice(2).map((node, index) => ({
            key: String(index),
            label: node,
          })),
        }}
      >
        <Button size="small">更多</Button>
      </Dropdown>
    </Space>
  )
}
