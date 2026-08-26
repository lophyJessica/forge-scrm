import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Table, message } from 'antd'
import { http } from '@/api/client'
import { TableActions } from '@/components/TableActions'
import { useAuthStore } from '@/store/auth'
import type { MaterialClassOut } from '@/types'

export default function MaterialClasses() {
  const isAdmin = useAuthStore((s) => s.isAdmin)()
  const [rows, setRows] = useState<MaterialClassOut[]>([])
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<MaterialClassOut | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    const { data } = await http.get<MaterialClassOut[]>('/material-classes')
    setRows(data)
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const save = async () => {
    const values = await form.validateFields()
    if (editing) await http.put(`/material-classes/${editing.id}`, values)
    else await http.post('/material-classes', values)
    message.success('保存成功')
    setOpen(false)
    void load()
  }

  return (
    <Card
      title="资料分类管理"
      extra={
        isAdmin && (
          <Button
            type="primary"
            onClick={() => {
              setEditing(null)
              form.resetFields()
              setOpen(true)
            }}
          >
            新建分类
          </Button>
        )
      }
    >
      <Table<MaterialClassOut>
        rowKey="id"
        dataSource={rows}
        pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: '分类名', dataIndex: 'name' },
          { title: '父级', dataIndex: 'parent_id', width: 100, render: (v) => v ?? '—' },
          { title: '排序', dataIndex: 'sort', width: 100 },
          {
            title: '操作',
            width: 160,
            render: (_, r) =>
              isAdmin && (
                <TableActions
                  items={[
                    <Button
                      key="edit"
                      size="small"
                      onClick={() => {
                        setEditing(r)
                        form.setFieldsValue(r)
                        setOpen(true)
                      }}
                    >
                      编辑
                    </Button>,
                    <Popconfirm
                      key="del"
                      title="确认删除该分类？"
                      onConfirm={async () => {
                        await http.delete(`/material-classes/${r.id}`)
                        message.success('已删除')
                        void load()
                      }}
                    >
                      <Button size="small" type="link" danger>
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                />
              ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? '编辑分类' : '新建分类'}
        width={520}
        onCancel={() => setOpen(false)}
        onOk={save}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="分类名" rules={[{ required: true }]}>
            <Input maxLength={50} />
          </Form.Item>
          <Form.Item name="parent_id" label="父级分类 ID（可选）">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="sort" label="排序">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
