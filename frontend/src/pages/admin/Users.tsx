import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Checkbox, Form, Input, Modal, Select, Space, Switch, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { useMetaStore } from '@/store/meta'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { DataScope, DataSourceOut, MaterialClassOut, PageResult, UserOut } from '@/types'

export default function Users() {
  const [form] = Form.useForm()
  const [pwdForm] = Form.useForm()
  const permissions = useMetaStore((s) => s.permissions)
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<UserOut[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<UserOut | null>(null)
  const [pwdTarget, setPwdTarget] = useState<UserOut | null>(null)
  const [classes, setClasses] = useState<MaterialClassOut[]>([])
  const [sources, setSources] = useState<DataSourceOut[]>([])
  const [scopeType, setScopeType] = useState<string>('全量')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<UserOut>>('/users', { params: { page_size: 200 } })
      setRows(data.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    void http.get<MaterialClassOut[]>('/material-classes').then((r) => setClasses(r.data))
    void http
      .get<PageResult<DataSourceOut>>('/data-sources', { params: { page_size: 200 } })
      .then((r) => setSources(r.data.items))
  }, [load])

  const openModal = (row?: UserOut) => {
    setEditing(row ?? null)
    form.resetFields()
    const scope = (row?.data_scope || { type: '全量' }) as DataScope
    setScopeType(scope.type || '全量')
    if (row) {
      form.setFieldsValue({
        username: row.username,
        role: row.role,
        functional_permissions: row.functional_permissions || [],
        scope_type: scope.type || '全量',
        material_class_ids: scope.material_class_ids || [],
        data_source_ids: scope.data_source_ids || [],
      })
    } else {
      form.setFieldsValue({ role: '成员', functional_permissions: [], scope_type: '全量' })
    }
    setOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    const data_scope: DataScope = {
      type: values.scope_type,
      material_class_ids: values.scope_type === '指定' ? values.material_class_ids || [] : null,
      data_source_ids: values.scope_type === '指定' ? values.data_source_ids || [] : null,
    }
    if (editing) {
      await http.put(`/users/${editing.id}`, {
        role: values.role,
        functional_permissions: values.functional_permissions,
        data_scope,
      })
    } else {
      await http.post('/users', {
        username: values.username,
        password: values.password,
        role: values.role,
        functional_permissions: values.functional_permissions,
        data_scope,
      })
    }
    message.success('已保存')
    setOpen(false)
    void load()
  }

  const toggle = async (row: UserOut) => {
    await http.post(`/users/${row.id}/${row.status === '启用' ? 'disable' : 'enable'}`)
    message.success('已更新')
    void load()
  }

  const resetPassword = async () => {
    const values = await pwdForm.validateFields()
    await http.post(`/users/${pwdTarget!.id}/reset-password`, { new_password: values.new_password })
    message.success('密码已重置')
    setPwdTarget(null)
    pwdForm.resetFields()
  }

  return (
    <Card title="成员与权限" extra={<Button type="primary" onClick={() => openModal()}>新增成员</Button>}>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="管理员默认拥有全部功能权限；成员按下方勾选显式授权，未勾选即为拒绝。一期不设成员数量上限。"
      />
      <Table<UserOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, pageSize: 20 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '账号', dataIndex: 'username', width: 160 },
          {
            title: '角色',
            dataIndex: 'role',
            width: 100,
            render: (v: string) => <Tag color={v === '管理员' ? 'gold' : 'blue'}>{v}</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 150,
            render: (v: string, r) => (
              <Space size={8}>
                <Tag color={statusTagColor(v)}>{v}</Tag>
                <Switch size="small" checked={v === '启用'} onChange={() => toggle(r)} />
              </Space>
            ),
          },
          {
            title: '功能权限',
            dataIndex: 'functional_permissions',
            render: (v: string[], r) =>
              r.role === '管理员' ? (
                <Tag color="gold">全部</Tag>
              ) : v?.length ? (
                v.map((code) => (
                  <Tag key={code}>{permissions.find((p) => p.code === code)?.label || code}</Tag>
                ))
              ) : (
                '—'
              ),
          },
          {
            title: '数据范围',
            dataIndex: 'data_scope',
            width: 110,
            render: (v: DataScope) => v?.type || '全量',
          },
          { title: '最近登录', dataIndex: 'last_login_at', width: 180, render: (v) => v || '—' },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="e" size="small" onClick={() => openModal(r)}>
                    编辑
                  </Button>,
                  <Button key="p" size="small" onClick={() => setPwdTarget(r)}>
                    重置密码
                  </Button>,
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? `编辑 ${editing.username}` : '新增成员'}
        width={720}
        onCancel={() => setOpen(false)}
        onOk={save}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <>
              <Form.Item name="username" label="账号" rules={[{ required: true, min: 2 }]}>
                <Input maxLength={100} />
              </Form.Item>
              <Form.Item name="password" label="初始密码" rules={[{ required: true, min: 6 }]}>
                <Input.Password maxLength={128} />
              </Form.Item>
            </>
          )}
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={options('user_role')} />
          </Form.Item>
          <Form.Item name="functional_permissions" label="功能权限（管理员恒为全部，无需勾选）">
            <Checkbox.Group
              options={permissions.map((p) => ({ label: p.label, value: p.code }))}
              style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}
            />
          </Form.Item>
          <Form.Item name="scope_type" label="数据范围" rules={[{ required: true }]}>
            <Select options={options('data_scope_type')} onChange={setScopeType} />
          </Form.Item>
          {scopeType === '指定' && (
            <>
              <Form.Item name="material_class_ids" label="可见资料分类">
                <Select mode="multiple" allowClear options={classes.map((c) => ({ label: c.name, value: c.id }))} />
              </Form.Item>
              <Form.Item name="data_source_ids" label="可见数据源">
                <Select mode="multiple" allowClear options={sources.map((s) => ({ label: s.name, value: s.id }))} />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      <Modal
        open={!!pwdTarget}
        title={`重置 ${pwdTarget?.username} 的密码`}
        width={520}
        onCancel={() => setPwdTarget(null)}
        onOk={resetPassword}
        okText="确定"
        cancelText="取消"
      >
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="new_password" label="新密码（至少 6 位）" rules={[{ required: true, min: 6 }]}>
            <Input.Password maxLength={128} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
