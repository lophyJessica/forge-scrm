import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Descriptions, Divider, Form, Input, List, Modal, Select, Skeleton, Space, Tag, Typography, message } from 'antd'
import { http } from '@/api/client'
import { statusTagColor } from '@/theme'
import type { PageResult, ReportOut, ReportPushTaskOut } from '@/types'

function pretty(value: Record<string, unknown> | null | undefined) {
  return value ? JSON.stringify(value, null, 2) : '—'
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

type SourceItem = { type?: string; id?: number; [key: string]: unknown }

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [report, setReport] = useState<ReportOut | null>(null)
  const [pushTasks, setPushTasks] = useState<ReportPushTaskOut[]>([])
  const [loading, setLoading] = useState(true)
  const [pushOpen, setPushOpen] = useState(false)
  const [pushing, setPushing] = useState<number | null>(null)

  const load = async (reportId: string) => {
    const { data } = await http.get<ReportOut>(`/reports/${reportId}`)
    setReport(data)
    const push = await http.get<PageResult<ReportPushTaskOut>>(`/reports/${reportId}/push-tasks`, { params: { page_size: 50 } })
    setPushTasks(push.data.items)
  }

  useEffect(() => {
    let active = true
    if (!id) return undefined
    setLoading(true)
    load(id).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [id])

  const createPush = async () => {
    if (!id) return
    const values = await form.validateFields()
    await http.post(`/reports/${id}/push-tasks`, values)
    message.success('推送任务已创建（发送渠道待实测）')
    setPushOpen(false)
    await load(id)
  }

  const executePush = async (taskId: number) => {
    if (!id) return
    setPushing(taskId)
    try {
      await http.post(`/push-tasks/${taskId}/execute`)
    } catch {
      // 501 由全局拦截器提示；刷新列表看失败记录
    } finally {
      setPushing(null)
      await load(id)
    }
  }

  if (loading) return <Card><Skeleton active /></Card>
  if (!report) return <Alert type="error" message="报告不存在或加载失败" />

  const snapshot = report.source_snapshot || {}
  const sources = Array.isArray(snapshot.sources) ? snapshot.sources as SourceItem[] : []
  const gaps = Array.isArray(snapshot.gaps) ? snapshot.gaps as string[] : []

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card
        extra={(
          <Space>
            <Button onClick={() => navigate('/reports')}>返回列表</Button>
            {report.generation_status === '已完成' && (
              <Button type="primary" onClick={() => { form.resetFields(); setPushOpen(true) }}>创建推送</Button>
            )}
          </Space>
        )}
      >
        <Space align="center" wrap>
          <Typography.Title level={3} style={{ margin: 0 }}>{report.title}</Typography.Title>
          {report.is_ai_product && <Tag color="purple">AI 生成</Tag>}
          <Tag color={statusTagColor(report.generation_status)}>{report.generation_status}</Tag>
          <Tag color={statusTagColor(report.review_status)}>{report.review_status}</Tag>
        </Space>
        <Descriptions column={{ xs: 1, sm: 3 }} size="small" style={{ marginTop: 18 }}>
          <Descriptions.Item label="编号">{report.report_no}</Descriptions.Item>
          <Descriptions.Item label="类型">{report.report_type}</Descriptions.Item>
          <Descriptions.Item label="周期">{formatTime(report.period_start)} ~ {formatTime(report.period_end)}</Descriptions.Item>
          <Descriptions.Item label="生成时间">{formatTime(report.generated_at)}</Descriptions.Item>
          <Descriptions.Item label="重试次数">{report.retry_count}</Descriptions.Item>
          <Descriptions.Item label="审核状态">{report.review_status}</Descriptions.Item>
        </Descriptions>
        {report.error_message && (
          <Alert type="error" showIcon style={{ marginTop: 12 }} message={report.error_code || '生成失败'} description={report.error_message} />
        )}
        <Divider />
        <Typography.Title level={4}>摘要</Typography.Title>
        <Typography.Paragraph className="pre-wrap">{report.summary || '—'}</Typography.Paragraph>
      </Card>

      <Card title="报告正文">
        <Typography.Paragraph className="pre-wrap">{report.content || '—'}</Typography.Paragraph>
      </Card>

      <Card title="章节与结论">
        <Typography.Title level={5}>章节</Typography.Title>
        <pre className="pre-wrap">{pretty(report.sections)}</pre>
        <Typography.Title level={5}>结论</Typography.Title>
        <pre className="pre-wrap">{pretty(report.conclusions)}</pre>
      </Card>

      <Card title={`来源清单（${sources.length}）`}>
        {gaps.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="来源缺口" description={gaps.join('；')} />}
        <List
          dataSource={sources}
          locale={{ emptyText: '无来源快照。空源不会生成完整报告。' }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={`${item.type || 'source'}#${item.id ?? '—'}`}
                description={<Typography.Text type="secondary">{pretty(item)}</Typography.Text>}
              />
            </List.Item>
          )}
        />
      </Card>

      <Card title="推送任务">
        <List
          dataSource={pushTasks}
          locale={{ emptyText: '暂无推送任务。已完成报告可创建飞书/微信推送，发送能力待实测。' }}
          renderItem={(task) => (
            <List.Item
              actions={[
                task.status !== '已推送' ? (
                  <Button key="send" size="small" loading={pushing === task.id} onClick={() => executePush(task.id)}>发送</Button>
                ) : null,
              ]}
            >
              <List.Item.Meta
                title={`${task.task_no} · ${task.channel} / ${task.target_object}`}
                description={(
                  <Space wrap>
                    <Tag color={statusTagColor(task.status)}>{task.status}</Tag>
                    <Typography.Text type="secondary">重试 {task.retry_count}</Typography.Text>
                    {task.records?.[0]?.error_message && <Typography.Text type="danger">{task.records[0].error_message}</Typography.Text>}
                  </Space>
                )}
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal open={pushOpen} title="创建推送任务" width={520} onCancel={() => setPushOpen(false)} onOk={createPush} okText="创建" cancelText="取消">
        <Alert type="info" showIcon style={{ marginBottom: 12 }} message="渠道 API 待实测，创建后发送将返回暂不可用。" />
        <Form form={form} layout="vertical" initialValues={{ channel: '飞书', recipient_type: '指定人' }}>
          <Form.Item name="channel" label="渠道" rules={[{ required: true }]}>
            <Select options={[{ label: '飞书', value: '飞书' }, { label: '微信', value: '微信' }]} />
          </Form.Item>
          <Form.Item name="recipient_type" label="目标类型" rules={[{ required: true }]}>
            <Select options={[{ label: '指定人', value: '指定人' }, { label: '群', value: '群' }]} />
          </Form.Item>
          <Form.Item name="target_object" label="目标人或群" rules={[{ required: true, message: '请填写目标标识' }]}>
            <Input maxLength={255} placeholder="不保存凭据，仅记录用户指定的目标标识" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
