import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Form, Input, Space, Table, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_PAGINATION } from '@/theme'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import type { TagOut } from '@/types'

export default function Tags() {
  const can = useAuthStore((s) => s.can)
  const [rows, setRows] = useState<TagOut[]>([])
  const [form] = Form.useForm()

  const load = useCallback(async (keyword?: string) => {
    const { data } = await http.get<TagOut[]>('/tags', { params: { keyword } })
    setRows(data)
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Card title="标签管理（一期自由创建，标签组可选）">
      {can(PERM.标签创建) && (
        <Form
          form={form}
          layout="inline"
          style={{ marginBottom: 16 }}
          onFinish={async (values) => {
            await http.post('/tags', values)
            message.success('标签已创建')
            form.resetFields()
            void load()
          }}
        >
          <Form.Item name="name" rules={[{ required: true, message: '请输入标签名' }]}>
            <Input placeholder="新标签名" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="group_name">
            <Input placeholder="标签组（可选）" style={{ width: 180 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit">
            新建标签
          </Button>
        </Form>
      )}

      <Space style={{ marginBottom: 12 }}>
        <Input.Search placeholder="搜索标签" onSearch={(v) => load(v)} style={{ width: 260 }} allowClear />
      </Space>

      <Table<TagOut>
        rowKey="id"
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, pageSize: 20 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: '标签名', dataIndex: 'name' },
          { title: '标签组', dataIndex: 'group_name', render: (v) => v || '—' },
        ]}
      />
    </Card>
  )
}
