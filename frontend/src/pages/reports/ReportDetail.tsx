import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Badge, Button, Card, Descriptions, Divider, Drawer, Form, Input, List, Modal, Skeleton, Space, Tag, Tooltip, Typography, message } from 'antd'
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
type PushConfig = { channel: 'feishu'; receivers_count: number; configured: boolean }

const PUSH_CONFIG_ERROR = '未配置飞书推送，请联系管理员设置 FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_PUSH_OPEN_IDS'

function latestPushError(task: ReportPushTaskOut) {
  return [...(task.records || [])].reverse().find((record) => record.status === '失败')?.error_message
}

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [report, setReport] = useState<ReportOut | null>(null)
  const [pushTasks, setPushTasks] = useState<ReportPushTaskOut[]>([])
  const [pushConfig, setPushConfig] = useState<PushConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [pushDrawerOpen, setPushDrawerOpen] = useState(false)
  const [createPushOpen, setCreatePushOpen] = useState(false)
  const [pushing, setPushing] = useState<number | null>(null)
  const [cancelling, setCancelling] = useState<number | null>(null)

  const load = async (reportId: string) => {
    const [reportResponse, pushResponse, configResponse] = await Promise.all([
      http.get<ReportOut>(`/reports/${reportId}`),
      http.get<PageResult<ReportPushTaskOut>>(`/reports/${reportId}/push-tasks`, { params: { page_size: 50 } }),
      http.get<PushConfig>('/reports/push-config'),
    ])
    setReport(reportResponse.data)
    setPushTasks(pushResponse.data.items)
    setPushConfig(configResponse.data)
  }

  const loadPushTasks = async (reportId: string) => {
    const { data } = await http.get<PageResult<ReportPushTaskOut>>(`/reports/${reportId}/push-tasks`, {
      params: { page_size: 50 },
    })
    setPushTasks(data.items)
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

  const openCreatePush = () => {
    form.setFieldsValue({
      channel: '飞书',
      recipient_type: '指定人',
      target_object: pushConfig?.configured
        ? `系统接收人 ×${pushConfig.receivers_count}（飞书）`
        : '未配置，请联系管理员',
    })
    setCreatePushOpen(true)
  }

  const createPush = async () => {
    if (!id) return
    const values = await form.validateFields()
    await http.post(`/reports/${id}/push-tasks`, values)
    message.success('推送任务已创建，可点发送推给接收人')
    setCreatePushOpen(false)
    setPushDrawerOpen(true)
    await loadPushTasks(id)
  }

  const executePush = async (taskId: number) => {
    if (!id) return
    setPushing(taskId)
    try {
      const { data } = await http.post<ReportPushTaskOut>(`/push-tasks/${taskId}/execute`)
      if (data.status === '已推送') {
        message.success('推送成功，接收人已在飞书收到卡片')
      } else {
        message.error(latestPushError(data) || '推送失败，请稍后重试')
      }
    } catch {
      // 全局请求拦截器展示后端错误。
    } finally {
      setPushing(null)
      await loadPushTasks(id)
    }
  }

  const cancelPush = async (taskId: number) => {
    if (!id) return
    setCancelling(taskId)
    try {
      await http.post(`/reports/push-tasks/${taskId}/cancel`)
      message.success('推送任务已取消')
    } catch {
      // 全局请求拦截器展示后端错误。
    } finally {
      setCancelling(null)
      await loadPushTasks(id)
    }
  }

  const deletePush = (taskId: number) => {
    if (!id) return
    Modal.confirm({
      title: '确认删除该推送任务？',
      content: '删除后不可恢复（已推送的飞书消息不会撤回）',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await http.delete(`/reports/push-tasks/${taskId}`)
          message.success('推送任务已删除')
        } catch {
          // 全局请求拦截器展示后端错误。
        } finally {
          await loadPushTasks(id)
        }
      },
    })
  }

  const deleteReport = () => {
    if (!id) return
    Modal.confirm({
      title: '确认删除该报告？删除后不可恢复',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await http.delete(`/reports/${id}`)
        message.success('报告已删除')
        navigate('/reports')
      },
    })
  }

  if (loading) return <Card><Skeleton active /></Card>
  if (!report) return <Alert type="error" message="报告不存在或加载失败" />

  const snapshot = report.source_snapshot || {}
  const sources = Array.isArray(snapshot.sources) ? snapshot.sources as SourceItem[] : []
  const gaps = Array.isArray(snapshot.gaps) ? snapshot.gaps as string[] : []
  const pendingPushCount = pushTasks.filter((task) => task.status === '待推送' || task.status === '失败').length

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card
        extra={(
          <Space>
            <Button onClick={() => navigate('/reports')}>返回列表</Button>
            <Badge count={pendingPushCount} size="small">
              <Button onClick={() => setPushDrawerOpen(true)}>推送任务（{pushTasks.length}）</Button>
            </Badge>
            {report.generation_status === '已完成' && (
              <Tooltip title={pushConfig?.configured ? undefined : PUSH_CONFIG_ERROR}>
                <Button type="primary" onClick={openCreatePush}>创建推送</Button>
              </Tooltip>
            )}
            {report.generation_status !== '生成中' && (
              <Button type="link" danger onClick={deleteReport}>删除</Button>
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

      <Drawer
        open={pushDrawerOpen}
        width={480}
        title="推送任务"
        onClose={() => setPushDrawerOpen(false)}
        extra={report.generation_status === '已完成' ? (
          <Tooltip title={pushConfig?.configured ? undefined : PUSH_CONFIG_ERROR}>
            <Button type="primary" size="small" onClick={openCreatePush}>创建推送</Button>
          </Tooltip>
        ) : null}
      >
        <List
          dataSource={pushTasks}
          locale={{ emptyText: '暂无推送任务。已完成报告可创建飞书推送，创建后点发送即推送给接收人。' }}
          renderItem={(task) => {
            const error = latestPushError(task)
            const canSend = task.status === '待推送' || task.status === '失败'
            const canDelete = canSend || task.status === '已取消'
            return (
              <List.Item
                actions={[
                  canSend ? (
                    <Button
                      key="send"
                      size="small"
                      disabled={cancelling === task.id}
                      loading={pushing === task.id}
                      onClick={() => executePush(task.id)}
                    >
                      发送
                    </Button>
                  ) : null,
                  canSend ? (
                    <Button
                      key="cancel"
                      size="small"
                      disabled={pushing === task.id}
                      loading={cancelling === task.id}
                      onClick={() => cancelPush(task.id)}
                    >
                      取消
                    </Button>
                  ) : null,
                  canDelete ? (
                    <Button key="delete" size="small" danger onClick={() => deletePush(task.id)}>
                      删除
                    </Button>
                  ) : null,
                ]}
              >
                <List.Item.Meta
                  title={`${task.task_no} · ${task.channel} / ${task.target_object}`}
                  description={(
                    <Space wrap>
                      <Tag color={task.status === '已取消' ? 'default' : statusTagColor(task.status)}>{task.status}</Tag>
                      <Typography.Text type="secondary">重试 {task.retry_count}</Typography.Text>
                      {error && <Typography.Text type="danger">{error}</Typography.Text>}
                    </Space>
                  )}
                />
              </List.Item>
            )
          }}
        />
      </Drawer>

      <Modal
        open={createPushOpen}
        title="创建推送任务"
        width={520}
        zIndex={1100}
        onCancel={() => setCreatePushOpen(false)}
        onOk={createPush}
        okButtonProps={{ disabled: !pushConfig?.configured }}
        okText="创建"
        cancelText="取消"
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }} message="推送将通过飞书应用发送给系统配置的接收人。" />
        <Form form={form} layout="vertical" initialValues={{ channel: '飞书', recipient_type: '指定人' }}>
          <Form.Item name="channel" label="渠道" rules={[{ required: true }]}>
            <Input readOnly />
          </Form.Item>
          <Form.Item name="recipient_type" label="目标类型" rules={[{ required: true }]}>
            <Input readOnly />
          </Form.Item>
          <Form.Item name="target_object" label="目标人或群" rules={[{ required: true }]}>
            <Input readOnly />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
