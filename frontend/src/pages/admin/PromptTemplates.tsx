import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { http } from '@/api/client'
import { PERM } from '@/store/meta'
import { useAuthStore } from '@/store/auth'
import type { PageResult, PromptTemplateOut } from '@/types'

const TASK_TYPE_OPTIONS = [
  { label: '选题生成', value: '选题生成' },
  { label: '脚本生成', value: '脚本生成' },
]

function formatTime(value: string | undefined) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function truncate(value: string, maxLength = 120) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

export default function PromptTemplates() {
  const [form] = Form.useForm()
  const can = useAuthStore((state) => state.can)
  const [rows, setRows] = useState<PromptTemplateOut[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PromptTemplateOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const templatesResponse = await http.get<PageResult<PromptTemplateOut>>('/prompt-templates', { params: { page_size: 200 } })
      setRows(templatesResponse.data.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = (row?: PromptTemplateOut) => {
    setEditing(row ?? null)
    form.resetFields()
    form.setFieldsValue(row ? row : { task_type: '选题生成' })
    setModalOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    const payload = {
      name: values.name,
      content: values.content,
      task_type: values.task_type,
      status: '启用',
    }
    if (editing) {
      await http.put(`/prompt-templates/${editing.id}`, payload)
    } else {
      await http.post('/prompt-templates', payload)
    }
    message.success(editing ? '模板已更新' : '模板已创建')
    setModalOpen(false)
    void load()
  }

  const remove = async (templateId: number) => {
    await http.delete(`/prompt-templates/${templateId}`)
    message.success('模板已删除')
    void load()
  }

  const toggleStatus = async (row: PromptTemplateOut, enabled: boolean) => {
    await http.put(`/prompt-templates/${row.id}`, { status: enabled ? '启用' : '停用' })
    message.success(enabled ? '模板已启用' : '模板已停用')
    void load()
  }

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card
        title="提示词模板"
        extra={can(PERM.提示词配置) ? <Button type="primary" onClick={() => openModal()}>新建模板</Button> : null}
      >
        <Table<PromptTemplateOut>
          rowKey="id"
          loading={loading}
          dataSource={rows}
          scroll={{ x: 980 }}
          columns={[
            { title: '名称', dataIndex: 'name', width: 180 },
            { title: '任务类型', dataIndex: 'task_type', width: 120, render: (value: string) => <Tag>{value}</Tag> },
            { title: '版本', dataIndex: 'version', width: 80, render: (value: number | null) => `v${value ?? 1}` },
            {
              title: '提示词正文',
              dataIndex: 'content',
              width: 360,
              render: (value: string) => <Typography.Text ellipsis={{ tooltip: value }}>{truncate(value)}</Typography.Text>,
            },
            { title: '描述', width: 150, render: () => <Typography.Text type="secondary">—</Typography.Text> },
            {
              title: '状态',
              dataIndex: 'status',
              width: 90,
              render: (value: string | null | undefined) => (
                <Tag color={value === '启用' ? 'green' : 'red'}>{value || '停用'}</Tag>
              ),
            },
            { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatTime(value) },
            {
              title: '操作',
              width: 210,
              fixed: 'right',
              render: (_, row) => (
                <Space size={4}>
                  {can(PERM.提示词配置) && <Button size="small" onClick={() => openModal(row)}>编辑</Button>}
                  {can(PERM.提示词配置) && (
                    <Switch
                      size="small"
                      checked={row.status === '启用'}
                      checkedChildren="启用"
                      unCheckedChildren="停用"
                      onChange={(checked) => void toggleStatus(row, checked)}
                    />
                  )}
                  <Popconfirm title="确认删除该模板？" description="删除后不可恢复；如果这是该任务类型的最后一条模板，后端会拒绝删除。" onConfirm={() => remove(row.id)}>
                    <Button size="small" danger>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={modalOpen}
        title={editing ? '编辑提示词模板' : '新建提示词模板'}
        width={820}
        onCancel={() => setModalOpen(false)}
        onOk={save}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input maxLength={100} placeholder="例如：选题生成-行业研究" />
          </Form.Item>
          <Form.Item name="task_type" label="任务类型" rules={[{ required: true, message: '请选择任务类型' }]}>
            <Select options={TASK_TYPE_OPTIONS} disabled={!!editing} />
          </Form.Item>
          <Form.Item name="content" label="提示词正文" rules={[{ required: true, message: '请输入提示词正文' }]}>
            <Input.TextArea rows={14} showCount />
          </Form.Item>
          <Typography.Text type="secondary">
            当前后端模板模型未提供可持久化的描述字段；版本号会在正文变更时由后端自动递增。
          </Typography.Text>
        </Form>
      </Modal>
    </Space>
  )
}
