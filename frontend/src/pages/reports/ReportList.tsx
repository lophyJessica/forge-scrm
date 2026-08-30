import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type Dayjs } from 'dayjs'
import { Alert, Button, Card, DatePicker, Descriptions, Form, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type {
  AnalysisTaskOut,
  CollectionResultOut,
  PageResult,
  RawDataOut,
  ReportGenerationStatus,
  ReportOut,
  ReportType,
  ResearchReferenceOut,
  ResearchReportOut,
  ResearchTaskOut,
} from '@/types'

const { RangePicker } = DatePicker

const REPORT_TYPES: ReportType[] = ['运营数据报告', '市场分析周报']
const STATUSES: ReportGenerationStatus[] = ['待生成', '生成中', '已完成', '失败']

type ReportSourceKey =
  | 'analysis_task_ids'
  | 'collection_result_ids'
  | 'raw_data_ids'
  | 'research_report_ids'
  | 'research_reference_ids'

type ReportFormValues = {
  report_type: ReportType
  period: [Dayjs, Dayjs]
} & Partial<Record<ReportSourceKey, number[]>>

type SourceOption = {
  label: string
  value: number
  times: string[]
}

type SourceField = {
  key: ReportSourceKey
  label: string
}

const SOURCE_KEYS: ReportSourceKey[] = [
  'analysis_task_ids',
  'collection_result_ids',
  'raw_data_ids',
  'research_report_ids',
  'research_reference_ids',
]

const REPORT_SOURCE_FIELDS: Record<ReportType, SourceField[]> = {
  运营数据报告: [
    { key: 'analysis_task_ids', label: '已确认分析任务结果' },
    { key: 'collection_result_ids', label: '自动采集结果' },
    { key: 'raw_data_ids', label: '业务原始数据' },
  ],
  市场分析周报: [
    { key: 'research_report_ids', label: '研究助手报告' },
    { key: 'collection_result_ids', label: '自动采集结果' },
    { key: 'research_reference_ids', label: '外部检索结论/引用' },
  ],
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function shortText(value: string, maxLength = 36) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

function optionsInPeriod(options: SourceOption[], period?: [Dayjs, Dayjs]) {
  if (!period?.[0] || !period?.[1]) return options
  const start = period[0].valueOf()
  const end = period[1].valueOf()
  return options.filter((option) => option.times.some((time) => {
    const value = new Date(time).getTime()
    return Number.isFinite(value) && value >= start && value <= end
  }))
}

function buildSourceConfig(values: ReportFormValues) {
  return REPORT_SOURCE_FIELDS[values.report_type].reduce<Record<string, number[]>>((config, field) => {
    const ids = values[field.key]
    if (ids?.length) config[field.key] = ids
    return config
  }, {})
}

function describeSourceIds(ids: number[]) {
  if (ids.length === 0) return '时间窗内全部可用数据'
  const shown = ids.slice(0, 8).map((id) => `#${id}`).join('、')
  const rest = ids.length > 8 ? ` 等 ${ids.length} 条` : ''
  return `指定 ${shown}${rest}`
}

export default function ReportList() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm<ReportFormValues>()
  const navigate = useNavigate()
  const [rows, setRows] = useState<ReportOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState<number | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [sourceLoading, setSourceLoading] = useState(false)
  const [sourceOptions, setSourceOptions] = useState<Partial<Record<ReportSourceKey, SourceOption[]>>>({})
  const sourceLoadId = useRef(0)
  const reportType = Form.useWatch('report_type', form)
  const period = Form.useWatch('period', form)

  const load = useCallback(async (targetPage = 1) => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<ReportOut>>('/reports', {
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

  const clearSourceSelection = () => {
    form.setFields(SOURCE_KEYS.map((name) => ({ name, value: undefined })))
  }

  const loadSourceOptions = async (type: ReportType) => {
    const loadId = ++sourceLoadId.current
    setSourceLoading(true)
    setSourceOptions({})
    try {
      if (type === '运营数据报告') {
        const [analysis, collection, rawData] = await Promise.all([
          http.get<PageResult<AnalysisTaskOut>>('/analysis-tasks', { params: { status: '已确认', page_size: 200 } }),
          http.get<PageResult<CollectionResultOut>>('/collection-results', { params: { page_size: 200 } }),
          http.get<PageResult<RawDataOut>>('/raw-data', { params: { page_size: 200 } }),
        ])
        if (sourceLoadId.current !== loadId) return
        setSourceOptions({
          analysis_task_ids: analysis.data.items.map((item) => ({
            value: item.id,
            label: `${item.name || item.type} (#${item.id}) · ${formatTime(item.created_at)}`,
            times: [item.created_at],
          })),
          collection_result_ids: collection.data.items.map((item) => ({
            value: item.id,
            label: `${item.platform || item.business_object} / ${item.account_identifier || item.business_object} (#${item.id}) · ${formatTime(item.collected_at)}`,
            times: [item.collected_at],
          })),
          raw_data_ids: rawData.data.items.map((item) => ({
            value: item.id,
            label: `${item.source_name || `数据源 #${item.source_id}`} (#${item.id}) · ${formatTime(item.collected_at)}`,
            times: [item.collected_at, item.window_start],
          })),
        })
        return
      }

      const [collection, tasks, references] = await Promise.all([
        http.get<PageResult<CollectionResultOut>>('/collection-results', { params: { page_size: 200 } }),
        http.get<PageResult<ResearchTaskOut>>('/research-tasks', { params: { status: 'success', page_size: 200 } }),
        http.get<PageResult<ResearchReferenceOut>>('/research-references', { params: { page_size: 200 } }),
      ])
      const reports = await Promise.all(
        tasks.data.items.map((task) => http.get<ResearchReportOut>(`/research-tasks/${task.id}/report`)),
      )
      if (sourceLoadId.current !== loadId) return
      setSourceOptions({
        research_report_ids: reports.map(({ data }) => ({
          value: data.id,
          label: `${shortText(data.title)} (#${data.id}) · ${formatTime(data.created_at)}`,
          times: [data.created_at],
        })),
        collection_result_ids: collection.data.items.map((item) => ({
          value: item.id,
          label: `${item.platform || item.business_object} / ${item.account_identifier || item.business_object} (#${item.id}) · ${formatTime(item.collected_at)}`,
          times: [item.collected_at],
        })),
        research_reference_ids: references.data.items
          .filter((item) => item.source_kind === 'external_url')
          .map((item) => ({
            value: item.id,
            label: `${shortText(item.source_title || item.source_url || '外部引用')} (#${item.id}) · ${formatTime(item.cited_at)}`,
            times: [item.cited_at],
          })),
      })
    } finally {
      if (sourceLoadId.current === loadId) setSourceLoading(false)
    }
  }

  const createReport = async (values: ReportFormValues, sourceConfig: Record<string, number[]>) => {
    const [start, end] = values.period as [Dayjs, Dayjs]
    setCreating(true)
    try {
      const { data } = await http.post<ReportOut>('/reports', {
        report_type: values.report_type,
        period_start: start.format('YYYY-MM-DDTHH:mm:ss'),
        period_end: end.format('YYYY-MM-DDTHH:mm:ss'),
        source_config: sourceConfig,
      })
      message.success('报告已创建，开始生成')
      setModalOpen(false)
      setRunning(data.id)
      try {
        await http.post<ReportOut>(`/reports/${data.id}/generate`)
        message.success('报告已生成')
      } catch {
        // 全局请求拦截器展示生成失败原因。
      } finally {
        setRunning(null)
        void load(1)
      }
    } finally {
      setCreating(false)
    }
  }

  const create = async () => {
    const values = await form.validateFields()
    const sourceConfig = buildSourceConfig(values)
    const fields = REPORT_SOURCE_FIELDS[values.report_type]
    Modal.confirm({
      title: '确认报告口径',
      width: 520,
      okText: '确认并生成',
      cancelText: '返回修改',
      content: (
        <Descriptions column={1} size="small">
          <Descriptions.Item label="报告类型">{values.report_type}</Descriptions.Item>
          <Descriptions.Item label="来源时间窗">
            {values.period[0].format('YYYY-MM-DD HH:mm:ss')} ~ {values.period[1].format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {fields.map((field) => {
            const selectedIds = values[field.key] || []
            return (
              <Descriptions.Item key={field.key} label={field.label}>
                {describeSourceIds(selectedIds)}
              </Descriptions.Item>
            )
          })}
        </Descriptions>
      ),
      onOk: () => createReport(values, sourceConfig),
    })
  }

  const run = async (row: ReportOut, action: 'generate' | 'retry') => {
    setRunning(row.id)
    try {
      await http.post<ReportOut>(`/reports/${row.id}/${action}`)
      message.success(action === 'retry' ? '已重试生成' : '报告已生成')
    } finally {
      setRunning(null)
      void load(page)
    }
  }

  const remove = (row: ReportOut) => {
    Modal.confirm({
      title: '确认删除该报告？删除后不可恢复',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await http.delete(`/reports/${row.id}`)
        message.success('报告已删除')
        await load(page)
      },
    })
  }

  return (
    <Card
      title="数据报告"
      extra={(
        <Button
          type="primary"
          onClick={() => {
            sourceLoadId.current += 1
            form.resetFields()
            setSourceOptions({})
            setModalOpen(true)
          }}
        >
          新建报告
        </Button>
      )}
    >
      <Form form={queryForm} layout="inline" style={{ marginBottom: 24 }} onFinish={() => load(1)}>
        <Form.Item name="report_type">
          <Select allowClear placeholder="报告类型" style={{ width: 180 }} options={REPORT_TYPES.map((value) => ({ label: value, value }))} />
        </Form.Item>
        <Form.Item name="generation_status">
          <Select allowClear placeholder="生成状态" style={{ width: 140 }} options={STATUSES.map((value) => ({ label: value, value }))} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button onClick={() => { queryForm.resetFields(); void load(1) }}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<ReportOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (nextPage) => load(nextPage) }}
        scroll={{ x: 1100 }}
        columns={[
          { title: '编号', dataIndex: 'report_no', width: 180 },
          { title: '类型', dataIndex: 'report_type', width: 140 },
          { title: '标题', dataIndex: 'title', width: 260, ellipsis: true, render: (value: string) => <Tooltip title={value}>{value}</Tooltip> },
          {
            title: '周期',
            width: 220,
            render: (_, row) => `${formatTime(row.period_start).slice(0, 10)} ~ ${formatTime(row.period_end).slice(0, 10)}`,
          },
          {
            title: '状态',
            dataIndex: 'generation_status',
            width: 110,
            render: (value: string) => <Tag color={statusTagColor(value)}>{value}</Tag>,
          },
          { title: '重试', dataIndex: 'retry_count', width: 70 },
          { title: '生成时间', dataIndex: 'generated_at', width: 180, render: (value?: string | null) => formatTime(value) },
          {
            title: '操作',
            width: 180,
            fixed: 'right',
            render: (_, row) => (
              <TableActions
                items={[
                  row.generation_status === '待生成' ? (
                    <Button key="gen" size="small" type="link" loading={running === row.id} onClick={() => run(row, 'generate')}>生成</Button>
                  ) : null,
                  row.generation_status === '失败' ? (
                    <Button key="retry" size="small" type="link" loading={running === row.id} onClick={() => run(row, 'retry')}>重试</Button>
                  ) : null,
                  <Button key="view" size="small" onClick={() => navigate(`/reports/${row.id}`)}>查看</Button>,
                  row.generation_status !== '生成中' ? (
                    <Button key="delete" type="link" size="small" danger onClick={() => remove(row)}>删除</Button>
                  ) : null,
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={modalOpen}
        title="新建报告"
        width={720}
        confirmLoading={creating}
        onCancel={() => {
          sourceLoadId.current += 1
          setSourceLoading(false)
          setModalOpen(false)
        }}
        onOk={create}
        okText="创建并生成"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="report_type" label="报告类型" rules={[{ required: true, message: '请选择报告类型' }]}>
            <Select
              options={REPORT_TYPES.map((value) => ({ label: value, value }))}
              onChange={(value: ReportType) => {
                clearSourceSelection()
                void loadSourceOptions(value)
              }}
            />
          </Form.Item>
          <Form.Item name="period" label="来源时间窗（统计周期）" rules={[{ required: true, message: '请选择时间窗' }]}>
            <RangePicker showTime style={{ width: '100%' }} onChange={clearSourceSelection} />
          </Form.Item>
          {reportType && (
            <>
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message="来源选择会在时间窗内进一步缩小范围；不指定时使用该类型在时间窗内的全部可用数据。"
              />
              {REPORT_SOURCE_FIELDS[reportType].map((field) => {
                const options = optionsInPeriod(sourceOptions[field.key] || [], period)
                return (
                  <Form.Item key={field.key} name={field.key} label={field.label}>
                    <Select
                      mode="multiple"
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      maxTagCount="responsive"
                      loading={sourceLoading}
                      disabled={!period || sourceLoading}
                      placeholder={period ? `不指定则使用时间窗内全部${field.label}` : '请先选择时间窗'}
                      options={options}
                      notFoundContent={sourceLoading ? '加载中...' : '当前时间窗内暂无可选数据'}
                    />
                  </Form.Item>
                )
              })}
            </>
          )}
        </Form>
      </Modal>
    </Card>
  )
}
