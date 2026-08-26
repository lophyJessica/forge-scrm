import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type Dayjs } from 'dayjs'
import { Button, Card, DatePicker, Form, Input, Modal, Progress, Select, Space, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import type { PageResult, ResearchTaskOut } from '@/types'

const { RangePicker } = DatePicker

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  searching: 'processing',
  organizing: 'processing',
  success: 'success',
  failed: 'error',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '待执行',
  searching: '检索中',
  organizing: '整理中',
  success: '已完成',
  failed: '失败',
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

export default function ResearchTasks() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [rows, setRows] = useState<ResearchTaskOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState<number | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const load = useCallback(async (targetPage = 1) => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<ResearchTaskOut>>('/research-tasks', {
        params: { ...queryForm.getFieldsValue(), page: targetPage, page_size: 20 },
      })
      setRows(data.items)
      setTotal(data.total)
      setPage(data.page)
    } finally {
      setLoading(false)
    }
  }, [queryForm])

  useEffect(() => {
    void load(1)
  }, [load])

  const create = async () => {
    const values = await form.validateFields()
    let scopeConfig: Record<string, unknown> = {}
    if (values.scope_config?.trim()) {
      try {
        const parsed: unknown = JSON.parse(values.scope_config)
        if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error()
        scopeConfig = parsed as Record<string, unknown>
      } catch {
        message.error('scope_config 必须是合法 JSON 对象')
        return
      }
    }
    const payload: Record<string, unknown> = {
      topic: values.topic,
      objective: values.objective,
      scope_config: scopeConfig,
    }
    if (values.time_range) {
      const [start, end] = values.time_range as [Dayjs, Dayjs]
      payload.time_window_start = start.format('YYYY-MM-DDTHH:mm:ss')
      payload.time_window_end = end.format('YYYY-MM-DDTHH:mm:ss')
    }
    await http.post('/research-tasks', payload)
    message.success('研究任务已创建')
    setModalOpen(false)
    void load(1)
  }

  const execute = async (row: ResearchTaskOut) => {
    setRunning(row.id)
    try {
      const action = row.status === 'failed' ? 'retry' : 'execute'
      await http.post<ResearchTaskOut>(`/research-tasks/${row.id}/${action}`)
      message.success(action === 'retry' ? '研究任务已重试' : '研究任务执行完成')
      if (action === 'execute' || action === 'retry') navigate(`/research/reports/${row.id}`)
    } finally {
      setRunning(null)
      void load(page)
    }
  }

  return (
    <Card title="研究助手" extra={<Button type="primary" onClick={() => { form.resetFields(); setModalOpen(true) }}>新建研究任务</Button>}>
      <Form form={queryForm} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load(1)}>
        <Form.Item name="status">
          <Select allowClear placeholder="任务状态" style={{ width: 150 }} options={Object.keys(STATUS_LABEL).map((value) => ({ label: STATUS_LABEL[value], value }))} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button onClick={() => { queryForm.resetFields(); void load(1) }}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<ResearchTaskOut>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, total, pageSize: 20, onChange: (nextPage) => load(nextPage) }}
        scroll={{ x: 1080 }}
        columns={[
          { title: '任务编号', dataIndex: 'task_no', width: 180 },
          { title: '主题', dataIndex: 'topic', width: 220, ellipsis: true },
          { title: '目标', dataIndex: 'objective', width: 260, ellipsis: true },
          {
            title: '状态',
            dataIndex: 'status',
            width: 110,
            render: (value: string) => <Tag color={STATUS_COLOR[value]}>{STATUS_LABEL[value] || value}</Tag>,
          },
          {
            title: '阶段进度',
            width: 180,
            render: (_, row) => ['searching', 'organizing'].includes(row.status) ? (
              <Progress percent={row.progress_percent ?? 0} status="active" size="small" format={() => row.current_stage === 'organizing' ? '整理中' : '检索中'} />
            ) : row.progress_message || '—',
          },
          { title: '重试次数', dataIndex: 'retry_count', width: 90 },
          { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatTime(value) },
          {
            title: '操作',
            width: 180,
            fixed: 'right',
            render: (_, row) => (
              <Space size={4}>
                {['pending', 'failed'].includes(row.status) && (
                  <Button size="small" type="primary" loading={running === row.id} onClick={() => execute(row)}>
                    {row.status === 'failed' ? '重试' : '执行'}
                  </Button>
                )}
                {row.status === 'success' && <Button size="small" onClick={() => navigate(`/research/reports/${row.id}`)}>查看报告</Button>}
              </Space>
            ),
          },
        ]}
      />

      <Modal open={modalOpen} title="新建研究任务" width={680} onCancel={() => setModalOpen(false)} onOk={create}>
        <Form form={form} layout="vertical">
          <Form.Item name="topic" label="研究主题" rules={[{ required: true, message: '请输入研究主题' }]}><Input maxLength={500} /></Form.Item>
          <Form.Item name="objective" label="研究目标" rules={[{ required: true, message: '请输入研究目标' }]}><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="time_range" label="研究时间窗（可选）"><RangePicker showTime style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="scope_config" label="scope_config（可选 JSON）" extra="可传 query、max_results、search_provider 等后端支持的范围配置。">
            <Input.TextArea rows={5} placeholder={'例如：{"query":"企业获客趋势","max_results":5}'} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
