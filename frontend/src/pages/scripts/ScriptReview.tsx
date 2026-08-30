import { Card, Typography } from 'antd'

/** 预留路由：当前脚本直接按默认可用口径处理。 */
export default function ScriptReview() {
  return (
    <Card title="脚本列表">
      <Typography.Text type="secondary">此入口暂未开放，请从脚本列表查看内容。</Typography.Text>
    </Card>
  )
}
