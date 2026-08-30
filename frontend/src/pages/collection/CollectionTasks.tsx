import { useCallback, useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { type Dayjs } from 'dayjs'
import { useSearchParams } from 'react-router-dom'
import { Button, Card, DatePicker, Descriptions, Divider, Drawer, Form, Input, Modal, Select, Space, Spin, Table, Tabs, Tag, Typography, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { BenchmarkAccountOut, CollectionRecordOut, CollectionResultOut, CollectionTaskOut, PageResult } from '@/types'

const { RangePicker } = DatePicker

const STATUS_LABEL: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  success: '已完成',
  partial_success: '部分成功',
  failed: '失败',
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

async function loadNestedOrFlat<T>(nestedPath: string, flatPath: string, params: Record<string, number>) {
  try {
    const response = await http.get<PageResult<T>>(nestedPath)
    return response.data.items
  } catch (error) {
    if (!isAxiosError(error) || error.response?.status !== 404) throw error
    const response = await http.get<PageResult<T>>(flatPath, { params: { ...params, page_size: 200 } })
    return response.data.items
  }
}

function ResultDetail({ result }: { result: CollectionResultOut }) {
  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="结果 ID">{result.id}</Descriptions.Item>
        <Descriptions.Item label="记录 ID">{result.record_id}</Descriptions.Item>
        <Descriptions.Item label="任务 ID">{result.task_id}</Descriptions.Item>
        <Descriptions.Item label="业务对象">{result.business_object || '—'}</Descriptions.Item>
        <Descriptions.Item label="平台">{result.platform || '—'}</Descriptions.Item>
        <Descriptions.Item label="账号标识">{result.account_identifier || '—'}</Descriptions.Item>
        <Descriptions.Item label="采集时间">{formatTime(result.collected_at)}</Descriptions.Item>
        <Descriptions.Item label="时间窗">{formatTime(result.window_start)} ~ {formatTime(result.window_end)}</Descriptions.Item>
        <Descriptions.Item label="AI 产物">{result.is_ai_product ? '是' : '否'}</Descriptions.Item>
        <Descriptions.Item label="来源链接">
          {result.source_url ? <a href={result.source_url} target="_blank" rel="noreferrer">{result.source_url}</a> : '—'}
        </Descriptions.Item>
      </Descriptions>
      <div>
        <Typography.Title level={5} style={{ marginTop: 0 }}>结构化数据</Typography.Title>
        <pre className="pre-wrap" style={{ margin: 0 }}>{formatJson(result.structured_data)}</pre>
      </div>
      <Divider style={{ margin: 0 }} />
      <div>
        <Typography.Title level={5} style={{ marginTop: 0 }}>原始内容</Typography.Title>
        <Typography.Paragraph className="pre-wrap" style={{ marginBottom: 0 }}>{result.raw_content || '—'}</Typography.Paragraph>
      </div>
    </Space>
  )
}

function TaskDetails({ taskId, onOpenResult }: { taskId: number; onOpenResult: (result: CollectionResultOut) => void }) {
  const [records, setRecords] = useState<CollectionRecordOut[]>([])
  const [results, setResults] = useState<CollectionResultOut[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      loadNestedOrFlat<CollectionRecordOut>(`/collection-tasks/${taskId}/records`, '/collection-records', { task_id: taskId }),
      loadNestedOrFlat<CollectionResultOut>(`/collection-tasks/${taskId}/results`, '/collection-results', { task_id: taskId }),
    ]).then(([recordRows, resultRows]) => {
      if (!active) return
      setRecords(recordRows)
      setResults(resultRows)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [taskId])

  if (loading) return <Spin />

  return (
    <Tabs
      items={[
        {
          key: 'records',
          label: `采集记录（${records.length}）`,
          children: (
            <Table<CollectionRecordOut>
              locale={TABLE_EMPTY}
              size="small"
              rowKey="id"
              dataSource={records}
              pagination={false}
              scroll={{ x: 900 }}
              columns={[
                { title: '账号 ID', dataIndex: 'benchmark_account_id', width: 90 },
                { title: '状态', dataIndex: 'status', width: 90, render: (value: string) => <Tag color={statusTagColor(value === 'success' ? '已完成' : value === 'failed' ? '失败' : value === 'running' ? '执行中' : value)}>{value}</Tag> },
                { title: '尝试次数', dataIndex: 'attempt_no', width: 90 },
                { title: '条目数', dataIndex: 'item_count', width: 80 },
                { title: 'HTTP', dataIndex: 'http_status', width: 80, render: (value: number | null) => value || '—' },
                { title: '错误', dataIndex: 'error_message', ellipsis: true, render: (value: string | null) => value || '—' },
                { title: '完成时间', dataIndex: 'completed_at', width: 180, render: (value: string | null) => formatTime(value) },
              ]}
            />
          ),
        },
        {
          key: 'results',
          label: `采集结果（${results.length}）`,
          children: (
            <Table<CollectionResultOut>
              locale={TABLE_EMPTY}
              size="small"
              rowKey="id"
              dataSource={results}
              pagination={false}
              scroll={{ x: 1000 }}
              columns={[
                { title: '平台', dataIndex: 'platform', width: 100 },
                { title: '账号标识', dataIndex: 'account_identifier', width: 180 },
                { title: '来源链接', dataIndex: 'source_url', width: 240, ellipsis: true, render: (value: string | null) => value || '—' },
                { title: '原始内容', dataIndex: 'raw_content', ellipsis: true, render: (value: string) => <Typography.Text ellipsis={{ tooltip: value }}>{value}</Typography.Text> },
                { title: 'AI 产物', dataIndex: 'is_ai_product', width: 90, render: (value: boolean) => value ? <Tag color="purple">是</Tag> : <Tag>否</Tag> },
                { title: '采集时间', dataIndex: 'collected_at', width: 180, render: (value: string) => formatTime(value) },
                { title: '操作', width: 80, fixed: 'right', render: (_, result) => <Button size="small" onClick={() => onOpenResult(result)}>详情</Button> },
              ]}
            />
          ),
        },
      ]}
    />
  )
}

export default function CollectionTasks() {
  const [searchParams] = useSearchParams()
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const [rows, setRows] = useState<CollectionTaskOut[]>([])
  const [accounts, setAccounts] = useState<BenchmarkAccountOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState<number | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [resultDetail, setResultDetail] = useState<CollectionResultOut | null>(null)

  const load = useCallback(async (targetPage = 1) => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<CollectionTaskOut>>('/collection-tasks', {
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
    void http.get<PageResult<BenchmarkAccountOut>>('/benchmark-accounts', { params: { enabled: true, page_size: 200 } }).then((response) => setAccounts(response.data.items))
  }, [load])

  useEffect(() => {
    const rawResultId = searchParams.get('result_id')
    if (!rawResultId) return
    const resultId = Number(rawResultId)
    if (!Number.isInteger(resultId) || resultId < 1) {
      message.warning('采集结果编号无效')
      return
    }
    let active = true
    http.get<PageResult<CollectionResultOut>>('/collection-results', { params: { page: 1, page_size: 200 } })
      .then(({ data }) => {
        if (!active) return
        const result = data.items.find((item) => item.id === resultId)
        if (result) setResultDetail(result)
        else message.warning('采集结果不存在或已不可见')
      })
    return () => { active = false }
  }, [searchParams])

  const openModal = () => {
    form.resetFields()
    setModalOpen(true)
  }

  const create = async () => {
    const values = await form.validateFields()
    let publicUrls: Record<string, string> | undefined
    if (values.public_urls?.trim()) {
      try {
        const parsed: unknown = JSON.parse(values.public_urls)
        if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error()
        publicUrls = parsed as Record<string, string>
      } catch {
        message.error('public_urls 必须是合法 JSON 对象')
        return
      }
    }
    const [start, end] = values.time_range as [Dayjs, Dayjs]
    await http.post('/collection-tasks', {
      scope_type: 'benchmark_account',
      scope_config: {
        benchmark_account_ids: values.account_ids,
        ...(publicUrls ? { public_urls: publicUrls } : {}),
      },
      time_window_start: start.format('YYYY-MM-DDTHH:mm:ss'),
      time_window_end: end.format('YYYY-MM-DDTHH:mm:ss'),
    })
    message.success('采集任务已创建')
    setModalOpen(false)
    void load(1)
  }

  const execute = async (row: CollectionTaskOut) => {
    setRunning(row.id)
    try {
      const action = row.status === 'failed' ? 'retry' : 'execute'
      await http.post<CollectionTaskOut>(`/collection-tasks/${row.id}/${action}`)
      message.success(action === 'retry' ? '采集任务已重试' : '采集任务执行完成')
    } finally {
      setRunning(null)
      void load(page)
    }
  }

  return (
    <Card title="自动采集任务" extra={<Button type="primary" onClick={openModal}>新建采集任务</Button>}>
      <Form form={queryForm} layout="inline" style={{ marginBottom: 24 }} onFinish={() => load(1)}>
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

      <Table<CollectionTaskOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        expandable={{ expandedRowRender: (row) => <TaskDetails taskId={row.id} onOpenResult={setResultDetail} /> }}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (nextPage) => load(nextPage) }}
        scroll={{ x: 1050 }}
        columns={[
          { title: '任务编号', dataIndex: 'task_no', width: 190 },
          { title: '时间窗', width: 330, render: (_, row) => `${formatTime(row.time_window_start)} ~ ${formatTime(row.time_window_end)}` },
          { title: '进度', width: 150, render: (_, row) => `${row.success_count}/${row.total_count} 成功，${row.failure_count} 失败` },
          { title: '状态', dataIndex: 'status', width: 110, render: (value: string) => <Tag color={statusTagColor(STATUS_LABEL[value] || value)}>{STATUS_LABEL[value] || value}</Tag> },
          { title: '重试次数', dataIndex: 'retry_count', width: 90 },
          { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatTime(value) },
          {
            title: '操作',
            width: 120,
            fixed: 'right',
            render: (_, row) => ['pending', 'failed'].includes(row.status) && (
              <Button size="small" type="primary" loading={running === row.id} onClick={() => execute(row)}>
                {row.status === 'failed' ? '重试' : '执行'}
              </Button>
            ),
          },
        ]}
      />

      <Modal open={modalOpen} title="新建采集任务" width={720} onCancel={() => setModalOpen(false)} onOk={create} okText="创建" cancelText="取消">
        <Form form={form} layout="vertical">
          <Form.Item name="account_ids" label="对标账号" rules={[{ required: true, message: '请选择至少一个对标账号' }]}>
            <Select mode="multiple" options={accounts.map((account) => ({ label: `${account.platform} / ${account.account_name || account.account_identifier}`, value: account.id }))} placeholder="选择启用中的对标账号" />
          </Form.Item>
          <Form.Item name="time_range" label="采集时间窗" rules={[{ required: true, message: '请选择时间窗' }]}>
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="public_urls" label="public_urls（可选 JSON）" extra="键可使用账号 ID 或账号标识；留空时使用账号公开主页 URL。">
            <Input.TextArea rows={4} placeholder={'例如：{"12":"https://example.com/public.json"}'} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        open={!!resultDetail}
        width={640}
        title={resultDetail ? `采集结果 #${resultDetail.id}` : '采集结果详情'}
        onClose={() => setResultDetail(null)}
        destroyOnClose
      >
        {resultDetail && <ResultDetail result={resultDetail} />}
      </Drawer>
    </Card>
  )
}
