import { Card, Typography } from 'antd'

/** 预留路由：当前资料直接按默认可用口径处理。 */
export default function MaterialReview() {
  return (
    <Card title="资料列表">
      <Typography.Text type="secondary">此入口暂未开放，请从资料列表查看内容。</Typography.Text>
    </Card>
  )
}
