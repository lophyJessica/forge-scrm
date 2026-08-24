import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { useMetaStore } from '@/store/meta'
import type { DataSourceOut, PageResult } from '@/types'

export default function DataSources() {
  const [form] = Form.useForm()
  const options = useMetaStore((s) => s.options)
  const isAdmin = useAuthStore((s) => s.isAdmin)
  const [rows, setRows] = useState<DataSourceOut[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<DataSourceOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<DataSourceOut>>('/data-sources', {
        params: { page_size: 200 },
      })
      setRows(data.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = (row?: DataSourceOut) => {
    setEditing(row ?? null)
    form.resetFields()
    if (row) form.setFieldsValue(row)
    else form.setFieldsValue({ collection_method: '手动录入', is_benchmark: false, status: '启用' })
    setOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    if (editing) await http.put(`/data-sources/${editing.id}`, values)
    else await http.post('/data-sources', values)
    message.success('已保存')
    setOpen(false)
    void load()
  }

  const remove = async (id: number) => {
    await http.delete(`/data-sources/${id}`)
    message.success('已删除')
    void load()
  }

  return (
    <Card
      title="数据源管理"
      extra={isAdmin() && <Button type="primary" onClick={() => openModal()}>新增数据源</Button>}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="一期仅登记数据源并支持「手动录入 / CSV 导入」，不实现自动采集逻辑；采集方式字段已按文档预留。"
      />
      <Table<DataSourceOut>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '名称', dataIndex: 'name' },
          { title: '采集方式', dataIndex: 'collection_method', width: 120 },
          { title: '业务对象', dataIndex: 'business_object', width: 140 },
          { title: '平台', dataIndex: 'platform', width: 110, render: (v) => v || '—' },
          { title: '账号标识', dataIndex: 'account_identifier', width: 160, render: (v) => v || '—' },
          {
            title: '对标账号',
            dataIndex: 'is_benchmark',
            width: 100,
            render: (v: boolean) => (v ? <Tag color="gold">是</Tag> : '否'),
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 90,
            render: (v: string) => <Tag color={v === '启用' ? 'green' : 'default'}>{v}</Tag>,
          },
          {
            title: '操作',
            width: 150,
            render: (_, r) =>
              isAdmin() ? (
                <Space size={4}>
                  <Button size="small" onClick={() => openModal(r)}>
                    编辑
                  </Button>
                  <Popconfirm title="确认删除？" onConfirm={() => remove(r.id)}>
                    <Button size="small" danger>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ) : (
                '—'
              ),
          },
        ]}
      />

      <Modal open={open} title={editing ? '编辑数据源' : '新增数据源'} onCancel={() => setOpen(false)} onOk={save}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item name="collection_method" label="采集方式" rules={[{ required: true }]}>
            <Select options={options('collection_method')} />
          </Form.Item>
          <Form.Item name="business_object" label="业务对象" rules={[{ required: true }]}>
            <Select options={options('business_object')} />
          </Form.Item>
          <Form.Item name="platform" label="平台">
            <Select allowClear options={options('platform')} />
          </Form.Item>
          <Form.Item name="account_identifier" label="账号标识（账号类数据必填）">
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item name="is_benchmark" label="是否对标账号" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={options('data_source_status')} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
