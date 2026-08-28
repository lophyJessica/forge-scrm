import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, Modal, Space, Tag, Typography, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import { statusTagColor } from '@/theme'
import type { TopicOut } from '@/types'

export default function TopicDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [topic, setTopic] = useState<TopicOut | null>(null)
  const [raw, setRaw] = useState<string | null>(null)
  const can = useAuthStore((s) => s.can)

  const load = useCallback(async () => {
    const { data } = await http.get<TopicOut>(`/topics/${id}`)
    setTopic(data)
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (!topic) return <Card loading />

  const screen = async (result: '选中' | '淘汰') => {
    await http.post(`/topics/${id}/screen`, { screening_result: result })
    message.success('已处理')
    void load()
  }

  const showRaw = async () => {
    const { data } = await http.get(`/topics/${id}/ai-raw`)
    setRaw(typeof data === 'string' ? data : JSON.stringify(data, null, 2))
  }

  return (
    <Card
      title={`选题 #${topic.id}`}
      extra={
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/topics')}>返回列表</Button>
          {topic.has_ai_raw_response && <Button onClick={showRaw}>查看 AI 原始响应</Button>}
          {can(PERM.选题修改) && (
            <Button onClick={() => navigate(`/topics/${topic.id}/edit`)}>修改</Button>
          )}
          {topic.status === '待筛选' && (
            <>
              <Button type="primary" onClick={() => screen('选中')}>
                选中
              </Button>
              <Button
                danger
                onClick={() => Modal.confirm({
                  title: '确认淘汰该选题？',
                  content: '淘汰后该选题将不再进入后续脚本生成流程。',
                  okText: '确认淘汰',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => screen('淘汰'),
                })}
              >
                淘汰
              </Button>
            </>
          )}
          {topic.status === '已选定' && (
            <Button type="primary" onClick={() => navigate(`/scripts/generate?topic_id=${topic.id}`)}>
              生成脚本
            </Button>
          )}
        </Space>
      }
    >
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="标题" span={2}>
          {topic.title}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusTagColor(topic.status)}>{topic.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="筛选结果">{topic.screening_result || '—'}</Descriptions.Item>
        <Descriptions.Item label="业务方向">{topic.direction}</Descriptions.Item>
        <Descriptions.Item label="专业方向">{topic.specialty}</Descriptions.Item>
        <Descriptions.Item label="客户场景">{topic.customer_scenario}</Descriptions.Item>
        <Descriptions.Item label="用户视角">{topic.user_perspective}</Descriptions.Item>
        <Descriptions.Item label="业务导向">{topic.business_direction}</Descriptions.Item>
        <Descriptions.Item label="选题原则">{topic.topic_principle}</Descriptions.Item>
        <Descriptions.Item label="选题角度">{topic.topic_angle}</Descriptions.Item>
        <Descriptions.Item label="批次号">{topic.batch_no || '独立创建'}</Descriptions.Item>
        <Descriptions.Item label="核心角度" span={2}>
          <Typography.Paragraph className="pre-wrap" style={{ marginBottom: 0 }}>
            {topic.core_angle}
          </Typography.Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label="关联资料" span={2}>
          {topic.material_ids.length ? topic.material_ids.map((m) => <Tag key={m}>#{m}</Tag>) : '—'}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间" span={2}>
          {topic.created_at}
        </Descriptions.Item>
      </Descriptions>

      <Modal open={raw !== null} onCancel={() => setRaw(null)} footer={null} width={720} title="AI 原始响应留档">
        <pre className="pre-wrap" style={{ maxHeight: 500, overflow: 'auto' }}>
          {raw}
        </pre>
      </Modal>
    </Card>
  )
}
