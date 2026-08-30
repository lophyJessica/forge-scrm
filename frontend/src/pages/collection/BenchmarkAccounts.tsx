import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { BenchmarkAccountOut, PageResult } from '@/types'

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

export default function BenchmarkAccounts() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const [rows, setRows] = useState<BenchmarkAccountOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<BenchmarkAccountOut | null>(null)

  const load = useCallback(async (targetPage = 1) => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<BenchmarkAccountOut>>('/benchmark-accounts', {
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

  const openModal = (row?: BenchmarkAccountOut) => {
    setEditing(row ?? null)
    form.resetFields()
    form.setFieldsValue(row ?? { enabled: true, benchmark_flag: true })
    setModalOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    if (editing) {
      await http.put(`/benchmark-accounts/${editing.id}`, values)
    } else {
      await http.post('/benchmark-accounts', values)
    }
    message.success(editing ? '账号已更新' : '账号已创建')
    setModalOpen(false)
    void load(page)
  }

  const toggleEnabled = async (row: BenchmarkAccountOut) => {
    await http.put(`/benchmark-accounts/${row.id}`, { enabled: !row.enabled })
    message.success(row.enabled ? '账号已停用' : '账号已启用')
    void load(page)
  }

  return (
    <Card title="对标账号" extra={<Button type="primary" onClick={() => openModal()}>新建账号</Button>}>
      <Form form={queryForm} layout="inline" style={{ marginBottom: 24 }} onFinish={() => load(1)}>
        <Form.Item name="platform">
          <Input allowClear placeholder="平台" style={{ width: 150 }} />
        </Form.Item>
        <Form.Item name="keyword">
          <Input allowClear placeholder="账号标识/名称" style={{ width: 210 }} />
        </Form.Item>
        <Form.Item name="enabled">
          <Select
            allowClear
            placeholder="启用状态"
            style={{ width: 130 }}
            options={[{ label: '启用', value: true }, { label: '已停用', value: false }]}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button onClick={() => { queryForm.resetFields(); void load(1) }}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<BenchmarkAccountOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        scroll={{ x: 980 }}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (nextPage) => load(nextPage) }}
        columns={[
          { title: '平台', dataIndex: 'platform', width: 120 },
          { title: '账号标识', dataIndex: 'account_identifier', width: 200 },
          { title: '账号名称', dataIndex: 'account_name', width: 180, render: (value: string | null) => value || '—' },
          { title: '公开主页', dataIndex: 'profile_url', ellipsis: true, render: (value: string | null) => value || '—' },
          { title: '最近采集', dataIndex: 'last_collected_at', width: 180, render: (value: string | null) => formatTime(value) },
          {
            title: '状态',
            dataIndex: 'enabled',
            width: 150,
            render: (enabled: boolean, row) => (
              <Space size={8}>
                <Tag color={statusTagColor(enabled ? '启用' : '已停用')}>{enabled ? '启用' : '已停用'}</Tag>
                <Switch size="small" checked={enabled} onChange={() => toggleEnabled(row)} />
              </Space>
            ),
          },
          {
            title: '操作',
            width: 90,
            fixed: 'right',
            render: (_, row) => (
              <Button size="small" onClick={() => openModal(row)}>编辑</Button>
            ),
          },
        ]}
      />

      <Modal open={modalOpen} title={editing ? '编辑对标账号' : '新建对标账号'} width={520} onCancel={() => setModalOpen(false)} onOk={save} okText="保存" cancelText="取消">
        <Form form={form} layout="vertical">
          <Form.Item name="platform" label="平台" rules={[{ required: true, message: '请输入平台' }]}>
            <Input maxLength={32} placeholder="例如：小红书" />
          </Form.Item>
          <Form.Item name="account_identifier" label="账号标识" rules={[{ required: true, message: '请输入账号标识' }]}>
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="account_name" label="账号名称"><Input maxLength={255} /></Form.Item>
          <Form.Item name="profile_url" label="公开主页 URL"><Input maxLength={1000} placeholder="采集公开内容时使用" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="enabled" label="允许新任务选择" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
