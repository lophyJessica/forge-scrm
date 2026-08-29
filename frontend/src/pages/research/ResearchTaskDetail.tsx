import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Descriptions, Divider, Skeleton, Space, Tag, Typography, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { http } from '@/api/client'
import { statusTagColor } from '@/theme'
import type { ResearchTaskOut } from '@/types'

const STATUS_LABEL: Record<string, string> = {
  pending: '待执行',
  searching: '检索中',
  organizing: '整理中',
  success: '已完成',
  failed: '失败',
}

const STAGE_LABEL: Record<string, string> = {
  searching: '检索中',
  organizing: '整理中',
  completed: '已完成',
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function formatJson(value: unknown) {
  if (value == null) return '—'
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function sourceCount(task: ResearchTaskOut) {
  const value = task.checkpoint_data?.source_count
  return typeof value === 'number' ? value : '—'
}

export default function ResearchTaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [task, setTask] = useState<ResearchTaskOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const { data } = await http.get<ResearchTaskOut>(`/research-tasks/${id}`)
      setTask(data)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const run = async () => {
    if (!task) return
    setRunning(true)
    try {
      const action = task.status === 'failed' ? 'retry' : 'execute'
      const { data } = await http.post<ResearchTaskOut>(`/research-tasks/${task.id}/${action}`)
      setTask(data)
      message.success(action === 'retry' ? '研究任务已重试' : '研究任务执行完成')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <Card><Skeleton active /></Card>
  if (!task) return <Alert type="error" message="研究任务不存在或加载失败" />

  const statusLabel = STATUS_LABEL[task.status] || task.status
  const stageLabel = task.current_stage ? (STAGE_LABEL[task.current_stage] || task.current_stage) : '—'
  const canRun = task.status === 'pending' || task.status === 'failed'

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card
        title={`研究任务 ${task.task_no}`}
        extra={(
          <Space size={8}>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/research/tasks')}>返回列表</Button>
            {canRun && (
              <Button type="primary" loading={running} onClick={() => void run()}>
                {task.status === 'failed' ? '重试' : '开始执行'}
              </Button>
            )}
          </Space>
        )}
      >
        <Descriptions column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="任务编号">{task.task_no}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusTagColor(statusLabel)}>{statusLabel}</Tag></Descriptions.Item>
          <Descriptions.Item label="当前阶段">{stageLabel}</Descriptions.Item>
          <Descriptions.Item label="进度">{task.progress_percent == null ? '—' : `${task.progress_percent}%`}</Descriptions.Item>
          <Descriptions.Item label="阶段说明">{task.progress_message || '—'}</Descriptions.Item>
          <Descriptions.Item label="来源数">{sourceCount(task)}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(task.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatTime(task.updated_at)}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{formatTime(task.started_at)}</Descriptions.Item>
          <Descriptions.Item label="完成时间">{formatTime(task.finished_at)}</Descriptions.Item>
          <Descriptions.Item label="重试次数">{task.retry_count}</Descriptions.Item>
        </Descriptions>
        <Divider />
        <Typography.Title level={4}>研究主题</Typography.Title>
        <Typography.Paragraph className="pre-wrap">{task.topic}</Typography.Paragraph>
        <Typography.Title level={4}>研究目标</Typography.Title>
        <Typography.Paragraph className="pre-wrap">{task.objective}</Typography.Paragraph>
      </Card>

      {(task.last_error_code || task.last_error_message) && (
        <Alert
          type="error"
          showIcon
          message={task.last_error_code || '任务执行失败'}
          description={task.last_error_message || '未提供错误说明'}
        />
      )}

      <Card title="中间结果">
        <pre className="pre-wrap" style={{ margin: 0 }}>{formatJson(task.checkpoint_data)}</pre>
      </Card>
    </Space>
  )
}
