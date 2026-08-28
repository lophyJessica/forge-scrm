import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Upload,
  message,
} from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { download, http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import { TABLE_PAGINATION } from '@/theme'
import type { DataSourceOut, PageResult, RawDataImportResult, RawDataOut } from '@/types'

const FMT = 'YYYY-MM-DD HH:mm:ss'

export default function RawData() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const can = useAuthStore((s) => s.can)
  const isAdmin = useAuthStore((s) => s.isAdmin)
  const [sources, setSources] = useState<DataSourceOut[]>([])
  const [rows, setRows] = useState<RawDataOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<RawDataOut | null>(null)
  const [importResult, setImportResult] = useState<RawDataImportResult | null>(null)

  const load = useCallback(
    async (targetPage = 1) => {
      setLoading(true)
      try {
        const values = queryForm.getFieldsValue()
        const { data } = await http.get<PageResult<RawDataOut>>('/raw-data', {
          params: { source_id: values.source_id, page: targetPage, page_size: 20 },
        })
        setRows(data.items)
        setTotal(data.total)
        setPage(data.page)
      } finally {
        setLoading(false)
      }
    },
    [queryForm],
  )

  useEffect(() => {
    void http
      .get<PageResult<DataSourceOut>>('/data-sources', { params: { page_size: 200 } })
      .then((r) => setSources(r.data.items))
    void load(1)
  }, [load])

  const openModal = (row?: RawDataOut) => {
    setEditing(row ?? null)
    form.resetFields()
    if (row) {
      form.setFieldsValue({
        source_id: row.source_id,
        raw_content: row.raw_content,
        collected_at: row.collected_at ? dayjs(row.collected_at) : undefined,
        window: [dayjs(row.window_start), dayjs(row.window_end)],
        structured_text: row.structured ? JSON.stringify(row.structured, null, 2) : '',
      })
    }
    setOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    let structured: Record<string, unknown> | null = null
    if (values.structured_text?.trim()) {
      try {
        structured = JSON.parse(values.structured_text)
      } catch {
        message.error('结构化字段必须是合法 JSON')
        return
      }
    }
    const payload = {
      source_id: values.source_id,
      raw_content: values.raw_content,
      structured,
      collected_at: values.collected_at ? values.collected_at.format(FMT) : undefined,
      window_start: values.window[0].format(FMT),
      window_end: values.window[1].format(FMT),
    }
    if (editing) await http.put(`/raw-data/${editing.id}`, payload)
    else await http.post('/raw-data', payload)
    message.success('已保存')
    setOpen(false)
    void load(page)
  }

  const remove = async (id: number) => {
    await http.delete(`/raw-data/${id}`)
    message.success('已删除')
    void load(page)
  }

  const downloadTemplate = async () => {
    const { data } = await http.get('/raw-data/csv-template', { responseType: 'blob' })
    download(data as Blob, 'raw_data_import_template.csv')
  }

  return (
    <Card
      title="原始数据"
      extra={
        can(PERM.数据录入导入) && (
          <Button type="primary" onClick={() => openModal()}>
            手动录入
          </Button>
        )
      }
    >
      <Tabs
        items={[
          {
            key: 'list',
            label: '数据列表',
            children: (
              <>
                <Form form={queryForm} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load(1)}>
                  <Form.Item name="source_id">
                    <Select
                      allowClear
                      placeholder="数据源"
                      style={{ width: 220 }}
                      options={sources.map((s) => ({ label: s.name, value: s.id }))}
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit">
                      查询
                    </Button>
                  </Form.Item>
                </Form>
                <Table<RawDataOut>
                  locale={TABLE_EMPTY}
                  rowKey="id"
                  loading={loading}
                  dataSource={rows}
                  pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (p) => load(p) }}
                  expandable={{
                    expandedRowRender: (r) => (
                      <>
                        <pre className="pre-wrap">{r.raw_content}</pre>
                        {r.structured && <pre className="pre-wrap">{JSON.stringify(r.structured, null, 2)}</pre>}
                      </>
                    ),
                  }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '数据源', dataIndex: 'source_name', width: 180 },
                    {
                      title: '原始内容',
                      dataIndex: 'raw_content',
                      ellipsis: true,
                      render: (v: string | null) => v || '—',
                    },
                    { title: '采集时间', dataIndex: 'collected_at', width: 180 },
                    { title: '时间窗开始', dataIndex: 'window_start', width: 180 },
                    { title: '时间窗结束', dataIndex: 'window_end', width: 180 },
                    {
                      title: '操作',
                      width: 150,
                      render: (_, r) => (
                        <TableActions
                          items={[
                            can(PERM.数据录入导入) ? (
                              <Button key="e" size="small" onClick={() => openModal(r)}>
                                编辑
                              </Button>
                            ) : null,
                            isAdmin() ? (
                              <Popconfirm key="d" title="确认删除？" onConfirm={() => remove(r.id)}>
                                <Button size="small" type="link" danger>
                                  删除
                                </Button>
                              </Popconfirm>
                            ) : null,
                          ]}
                        />
                      ),
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'import',
            label: 'CSV 导入',
            children: (
              <>
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                  message="一期采用固定模板导入：请先下载模板，按列名填写后上传；失败行会逐行给出原因，成功行照常入库。"
                />
                <Space style={{ marginBottom: 16 }}>
                  <Button onClick={downloadTemplate}>下载导入模板</Button>
                  <Upload
                    accept=".csv,.txt"
                    showUploadList={false}
                    customRequest={async ({ file, onSuccess, onError }) => {
                      const fd = new FormData()
                      fd.append('file', file as File)
                      try {
                        const { data } = await http.post<RawDataImportResult>('/raw-data/import', fd)
                        setImportResult(data)
                        message.success(`导入完成：成功 ${data.success} 行，失败 ${data.failed} 行`)
                        void load(1)
                        onSuccess?.(data)
                      } catch (err) {
                        onError?.(err as Error)
                      }
                    }}
                  >
                    <Button type="primary" icon={<UploadOutlined />}>
                      上传 CSV
                    </Button>
                  </Upload>
                </Space>
                {importResult && (
                  <>
                    <p>
                      总行数 {importResult.total} · 成功 {importResult.success} · 失败 {importResult.failed} ·
                      原文件留档 {importResult.stored_file}
                    </p>
                    {importResult.errors.length > 0 && (
                      <Table
                        locale={TABLE_EMPTY}
                        rowKey={(r) => `${r.row}`}
                        size="small"
                        pagination={false}
                        dataSource={importResult.errors}
                        columns={[
                          { title: '行号', dataIndex: 'row', width: 90 },
                          { title: '失败原因', dataIndex: 'message' },
                        ]}
                      />
                    )}
                  </>
                )}
              </>
            ),
          },
        ]}
      />

      <Modal open={open} title={editing ? '编辑原始数据' : '手动录入原始数据'} onCancel={() => setOpen(false)} onOk={save} width={720} okText="保存" cancelText="取消">
        <Form form={form} layout="vertical">
          <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
            <Select options={sources.map((s) => ({ label: s.name, value: s.id }))} disabled={!!editing} />
          </Form.Item>
          <Form.Item name="raw_content" label="原始内容" rules={[{ required: true }]}>
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="window" label="统计时间窗" rules={[{ required: true }]}>
            <DatePicker.RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="collected_at" label="采集时间（留空取当前时间）">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="structured_text" label="结构化字段 JSON（可选）">
            <Input.TextArea rows={4} placeholder='{"播放量":12000,"点赞":320}' />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
