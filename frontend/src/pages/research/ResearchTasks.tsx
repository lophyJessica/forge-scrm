import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type Dayjs } from 'dayjs'
import { Button, Card, DatePicker, Form, Input, InputNumber, Modal, Progress, Select, Space, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { FILTER_CARD_STYLE, TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { CollectionResultOut, MaterialOut, PageResult, ResearchTaskOut } from '@/types'

const { RangePicker } = DatePicker

const STATUS_LABEL: Record<string, string> = {
  pending: '待执行',
  searching: '检索中',
  organizing: '整理中',
  success: '已完成',
  failed: '失败',
}

const SCOPE_TYPES = [
  { label: '资料库', value: 'material' },
  { label: '自动采集结果', value: 'collection_result' },
  { label: '外部检索', value: 'external_search' },
]

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
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [collectionResults, setCollectionResults] = useState<CollectionResultOut[]>([])

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

  useEffect(() => {
    void Promise.all([
      http.get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } }),
      http.get<PageResult<CollectionResultOut>>('/collection-results', { params: { page_size: 200 } }),
    ]).then(([materialResponse, collectionResponse]) => {
      setMaterials(materialResponse.data.items)
      setCollectionResults(collectionResponse.data.items)
    })
  }, [])

  const create = async () => {
    const values = await form.validateFields()
    const scopeTypes = (values.sourceTypes || []) as string[]
    if (!scopeTypes.length) {
      message.error('请至少选择一种研究来源')
      return
    }
    const scopeConfig: Record<string, unknown> = {
      source_types: scopeTypes,
      material_ids: values.materialIds || [],
      collection_result_ids: values.collectionResultIds || [],
      external_search: {
        keywords: values.searchKeywords?.trim() || undefined,
        max_results: values.searchMaxResults || 5,
      },
    }
    const payload: Record<string, unknown> = {
      topic: values.researchTopic,
      objective: values.researchObjective,
      scope_config: scopeConfig,
    }
    if (values.researchTimeRange) {
      const [start, end] = values.researchTimeRange as [Dayjs, Dayjs]
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
      <Form form={queryForm} layout="inline" style={FILTER_CARD_STYLE} onFinish={() => load(1)}>
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
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (nextPage) => load(nextPage) }}
        scroll={{ x: 1080 }}
        columns={[
          { title: '任务编号', dataIndex: 'task_no', width: 180 },
          { title: '主题', dataIndex: 'topic', width: 220, ellipsis: true },
          { title: '目标', dataIndex: 'objective', width: 260, ellipsis: true },
          {
            title: '状态',
            dataIndex: 'status',
            width: 110,
            render: (value: string) => <Tag color={statusTagColor(STATUS_LABEL[value] || value)}>{STATUS_LABEL[value] || value}</Tag>,
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
              <Space size={8}>
                <Button size="small" onClick={() => navigate(`/research/tasks/${row.id}`)}>详情</Button>
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

      <Modal open={modalOpen} title="新建研究任务" width={720} onCancel={() => setModalOpen(false)} onOk={create} okText="创建" cancelText="取消">
        <Form
          form={form}
          layout="vertical"
          initialValues={{ sourceTypes: ['external_search'], searchMaxResults: 5 }}
        >
          <Form.Item name="researchTopic" label="研究主题" rules={[{ required: true, message: '请输入研究主题' }]}><Input maxLength={500} /></Form.Item>
          <Form.Item name="researchObjective" label="研究目标" rules={[{ required: true, message: '请输入研究目标' }]}><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="researchTimeRange" label="研究时间窗（可选）"><RangePicker showTime style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="sourceTypes" label="研究来源" rules={[{ required: true, message: '请选择至少一种研究来源' }]}>
            <Select mode="multiple" options={SCOPE_TYPES} placeholder="选择资料库、采集结果或外部检索" />
          </Form.Item>
          <Form.Item name="materialIds" label="资料库资料（可选）">
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              options={materials.map((item) => ({ value: item.id, label: `#${item.id} ${item.title}` }))}
              placeholder="不指定则使用时间窗内全部已生效资料"
            />
          </Form.Item>
          <Form.Item name="collectionResultIds" label="自动采集结果（可选）">
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              options={collectionResults.map((item) => ({
                value: item.id,
                label: `#${item.id} ${item.platform || item.business_object} / ${item.account_identifier || '采集结果'}`,
              }))}
              placeholder="不指定则使用时间窗内全部采集结果"
            />
          </Form.Item>
          <Space size={16} align="start" style={{ width: '100%' }}>
            <Form.Item name="searchKeywords" label="外部检索关键词" style={{ flex: 1 }}>
              <Input placeholder="留空则使用研究主题和目标" />
            </Form.Item>
            <Form.Item name="searchMaxResults" label="检索条数">
              <InputNumber min={1} max={20} style={{ width: 120 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  )
}
