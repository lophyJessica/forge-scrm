import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type Dayjs } from 'dayjs'
import { Button, Card, DatePicker, Form, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { PageResult, ReportGenerationStatus, ReportOut, ReportType } from '@/types'

const { RangePicker } = DatePicker

const REPORT_TYPES: ReportType[] = ['运营数据报告', '市场分析周报']
const STATUSES: ReportGenerationStatus[] = ['待生成', '生成中', '已完成', '失败']

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

export default function ReportList() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [rows, setRows] = useState<ReportOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState<number | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

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

  const create = async () => {
    const values = await form.validateFields()
    const [start, end] = values.period as [Dayjs, Dayjs]
    const { data } = await http.post<ReportOut>('/reports', {
      report_type: values.report_type,
      period_start: start.format('YYYY-MM-DDTHH:mm:ss'),
      period_end: end.format('YYYY-MM-DDTHH:mm:ss'),
    })
    message.success('报告已创建，开始生成')
    setModalOpen(false)
    setRunning(data.id)
    try {
      await http.post<ReportOut>(`/reports/${data.id}/generate`)
      message.success('报告已生成')
    } finally {
      setRunning(null)
      void load(1)
    }
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
    <Card title="数据报告" extra={<Button type="primary" onClick={() => { form.resetFields(); setModalOpen(true) }}>新建报告</Button>}>
      <Form form={queryForm} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load(1)}>
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

      <Modal open={modalOpen} title="新建报告" width={520} onCancel={() => setModalOpen(false)} onOk={create} okText="创建并生成" cancelText="取消">
        <Form form={form} layout="vertical">
          <Form.Item name="report_type" label="报告类型" rules={[{ required: true, message: '请选择报告类型' }]}>
            <Select options={REPORT_TYPES.map((value) => ({ label: value, value }))} />
          </Form.Item>
          <Form.Item name="period" label="统计周期" rules={[{ required: true, message: '请选择周期' }]}>
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
