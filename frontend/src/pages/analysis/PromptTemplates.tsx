import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Input, Modal, Popconfirm, Select, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import MaterialComboField from '@/components/MaterialComboField'
import { TableActions } from '@/components/TableActions'
import { useAuthStore } from '@/store/auth'
import { PERM, useMetaStore } from '@/store/meta'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { PageResult, PromptTemplateOut } from '@/types'

export default function PromptTemplates() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const can = useAuthStore((s) => s.can)
  const isAdmin = useAuthStore((s) => s.isAdmin)
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<PromptTemplateOut[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<PromptTemplateOut | null>(null)
  const [view, setView] = useState<PromptTemplateOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<PromptTemplateOut>>('/prompt-templates', {
        params: { ...queryForm.getFieldsValue(), page_size: 200 },
      })
      setRows(data.items)
    } finally {
      setLoading(false)
    }
  }, [queryForm])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = (row?: PromptTemplateOut) => {
    setEditing(row ?? null)
    form.resetFields()
    if (row) {
      form.setFieldsValue({
        ...row,
        output_schema_text: row.output_schema ? JSON.stringify(row.output_schema, null, 2) : '',
      })
    } else {
      form.setFieldsValue({ status: '启用' })
    }
    setOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    let output_schema: Record<string, unknown> | null = null
    if (values.output_schema_text?.trim()) {
      try {
        output_schema = JSON.parse(values.output_schema_text)
      } catch {
        message.error('输出字段定义必须是合法 JSON')
        return
      }
    }
    const payload = {
      task_type: values.task_type,
      name: values.name,
      content: values.content,
      material_combo: values.material_combo || [],
      output_schema,
      status: values.status,
    }
    if (editing) await http.put(`/prompt-templates/${editing.id}`, payload)
    else await http.post('/prompt-templates', payload)
    message.success('已保存')
    setOpen(false)
    void load()
  }

  const remove = async (id: number) => {
    await http.delete(`/prompt-templates/${id}`)
    message.success('已删除')
    void load()
  }

  return (
    <Card
      title="提示词模板"
      extra={can(PERM.提示词配置) && <Button type="primary" onClick={() => openModal()}>新增模板</Button>}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="一期不设独立版本表：模板正文变更时版本号自动 +1，历史正文由使用它的任务/选题的「版本快照」留存。分析类模板必须填写输出字段定义。"
      />
      <Form form={queryForm} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load()}>
        <Form.Item name="task_type">
          <Select allowClear placeholder="任务类型" style={{ width: 180 }} options={options('prompt_task_type')} />
        </Form.Item>
        <Form.Item name="status">
          <Select allowClear placeholder="状态" style={{ width: 120 }} options={options('prompt_status')} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">
            查询
          </Button>
        </Form.Item>
      </Form>

      <Table<PromptTemplateOut>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, pageSize: 20 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '名称', dataIndex: 'name', render: (v, r) => <a onClick={() => setView(r)}>{v}</a> },
          { title: '任务类型', dataIndex: 'task_type', width: 160 },
          { title: '版本', dataIndex: 'version', width: 80, render: (v) => `v${v}` },
          {
            title: '状态',
            dataIndex: 'status',
            width: 90,
            render: (v: string) => <Tag color={statusTagColor(v)}>{v}</Tag>,
          },
          { title: '创建时间', dataIndex: 'created_at', width: 190 },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="v" size="small" onClick={() => setView(r)}>
                    查看
                  </Button>,
                  can(PERM.提示词配置) ? (
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

      <Modal open={open} title={editing ? '编辑提示词模板' : '新增提示词模板'} width={720} onCancel={() => setOpen(false)} onOk={save} okText="保存" cancelText="取消">
        <Form form={form} layout="vertical">
          <Form.Item name="task_type" label="任务类型" rules={[{ required: true }]}>
            <Select options={options('prompt_task_type')} disabled={!!editing} />
          </Form.Item>
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="content" label="提示词正文" rules={[{ required: true }]}>
            <Input.TextArea rows={10} />
          </Form.Item>
          <MaterialComboField />
          <Form.Item name="output_schema_text" label="输出字段定义 JSON（分析类必填）">
            <Input.TextArea rows={6} placeholder='{"results":[{"conclusion":"...","suggestions":["..."]}]}' />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={options('prompt_status')} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal open={!!view} title={view?.name} width={720} footer={null} onCancel={() => setView(null)}>
        <p>
          任务类型：{view?.task_type} · 版本 v{view?.version} · 状态 {view?.status}
        </p>
        <pre className="pre-wrap" style={{ maxHeight: 380, overflow: 'auto' }}>
          {view?.content}
        </pre>
        {view?.output_schema && (
          <>
            <p style={{ marginTop: 12 }}>输出字段定义：</p>
            <pre className="pre-wrap" style={{ maxHeight: 240, overflow: 'auto' }}>
              {JSON.stringify(view.output_schema, null, 2)}
            </pre>
          </>
        )}
      </Modal>
    </Card>
  )
}
