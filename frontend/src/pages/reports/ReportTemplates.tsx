import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Drawer, Form, Input, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import type { PageResult, ReportTemplateOut, ReportType } from '@/types'

const REPORT_TYPES: ReportType[] = ['运营数据报告', '市场分析周报']

function formatTime(value: string) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function shorten(value: string, length = 100) {
  return value.length > length ? `${value.slice(0, length)}...` : value
}

export default function ReportTemplates() {
  const [form] = Form.useForm()
  const canConfigure = useAuthStore((state) => state.can(PERM.提示词配置))
  const [rows, setRows] = useState<ReportTemplateOut[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ReportTemplateOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<ReportTemplateOut>>('/report-templates', { params: { page_size: 200 } })
      setRows(data.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openEditor = (row?: ReportTemplateOut) => {
    setEditing(row ?? null)
    form.resetFields()
    form.setFieldsValue(row
      ? {
          templateReportType: row.report_type,
          templateLabel: row.name,
          contentSchemaText: JSON.stringify(row.content_schema || {}, null, 2),
          templateDefault: row.is_default,
          templateStatus: row.status,
        }
      : { templateReportType: '运营数据报告', contentSchemaText: '{}', templateStatus: '启用', templateDefault: false })
    setModalOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    let contentSchema: Record<string, unknown>
    try {
      const parsed = JSON.parse(values.contentSchemaText || '{}')
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
      contentSchema = parsed
    } catch {
      message.error('模板内容结构必须是合法 JSON 对象')
      return
    }
    const payload = {
      report_type: values.templateReportType,
      name: values.templateLabel,
      content_schema: contentSchema,
      is_default: Boolean(values.templateDefault),
      status: values.templateStatus,
    }
    if (editing) await http.put(`/report-templates/${editing.id}`, payload)
    else await http.post('/report-templates', payload)
    message.success(editing ? '报告模板已更新' : '报告模板已创建')
    setModalOpen(false)
    void load()
  }

  const toggleStatus = async (row: ReportTemplateOut, enabled: boolean) => {
    await http.put(`/report-templates/${row.id}`, { status: enabled ? '启用' : '停用' })
    message.success(enabled ? '报告模板已启用' : '报告模板已停用')
    void load()
  }

  const setDefault = async (row: ReportTemplateOut) => {
    await http.post(`/report-templates/${row.id}/set-default`)
    message.success('默认模板已更新')
    void load()
  }

  const remove = async (row: ReportTemplateOut) => {
    await http.delete(`/report-templates/${row.id}`)
    message.success('报告模板已删除')
    void load()
  }

  return (
    <Card
      title="报告模板"
      extra={canConfigure ? <Button type="primary" onClick={() => openEditor()}>新建模板</Button> : null}
    >
      <Table<ReportTemplateOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        scroll={{ x: 980 }}
        pagination={{ ...TABLE_PAGINATION, pageSize: 20 }}
        columns={[
          { title: '名称', dataIndex: 'name', width: 200 },
          { title: '报告类型', dataIndex: 'report_type', width: 150, render: (value: string) => <Tag>{value}</Tag> },
          {
            title: '内容结构',
            dataIndex: 'content_schema',
            width: 320,
            render: (value: Record<string, unknown>) => <Typography.Text ellipsis={{ tooltip: JSON.stringify(value) }}>{shorten(JSON.stringify(value))}</Typography.Text>,
          },
          {
            title: '默认',
            dataIndex: 'is_default',
            width: 90,
            render: (value: boolean) => value ? <Tag color="green">默认</Tag> : <Typography.Text type="secondary">—</Typography.Text>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 140,
            render: (value: string, row) => (
              <Space size={8}>
                <Tag color={statusTagColor(value)}>{value}</Tag>
                {canConfigure && <Switch size="small" checked={value === '启用'} onChange={(checked) => void toggleStatus(row, checked)} />}
              </Space>
            ),
          },
          { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatTime(value) },
          {
            title: '操作',
            width: 220,
            fixed: 'right',
            render: (_, row) => (
              <Space size={8}>
                {canConfigure && <Button size="small" onClick={() => openEditor(row)}>编辑</Button>}
                {canConfigure && !row.is_default && row.status === '启用' && <Button size="small" onClick={() => void setDefault(row)}>设为默认</Button>}
                {canConfigure && (
                  <Popconfirm title="确认删除该模板？" description="已有报告使用的模板不能删除。" onConfirm={() => void remove(row)}>
                    <Button size="small" type="link" danger>删除</Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Drawer
        open={modalOpen}
        title={editing ? '编辑报告模板' : '新建报告模板'}
        width={640}
        onClose={() => setModalOpen(false)}
        footer={(
          <Space>
            <Button onClick={() => setModalOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void save()}>保存</Button>
          </Space>
        )}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="templateLabel" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="templateReportType" label="报告类型" rules={[{ required: true, message: '请选择报告类型' }]}>
            <Select options={REPORT_TYPES.map((value) => ({ label: value, value }))} disabled={!!editing} />
          </Form.Item>
          <Form.Item
            name="contentSchemaText"
            label="模板内容结构 JSON"
            extra="可用 section_order 控制章节顺序，section_titles 控制章节名称；留空则沿用默认输出。"
            rules={[{ required: true, message: '请输入模板内容结构' }]}
          >
            <Input.TextArea rows={10} placeholder={'例如：{"section_order":["研究助手报告","采集结果"]}'} />
          </Form.Item>
          <Space size={16}>
            <Form.Item name="templateDefault" label="设为默认" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="templateStatus" label="状态">
              <Select style={{ width: 120 }} options={[{ label: '启用', value: '启用' }, { label: '停用', value: '停用' }]} />
            </Form.Item>
          </Space>
        </Form>
      </Drawer>
    </Card>
  )
}
