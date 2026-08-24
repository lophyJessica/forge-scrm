import { Button, Card, Descriptions, Form, Input, Tag, message } from 'antd'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'

export default function Profile() {
  const { user, logout } = useAuthStore()
  const [form] = Form.useForm()

  const onFinish = async (values: { old_password: string; new_password: string }) => {
    await http.post('/auth/change-password', values)
    message.success('密码已修改，请重新登录')
    await logout()
    location.href = '/login'
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Card title="我的账号">
        <Descriptions column={2}>
          <Descriptions.Item label="账号">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="角色">
            <Tag color={user?.role === '管理员' ? 'gold' : 'blue'}>{user?.role}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">{user?.status}</Descriptions.Item>
          <Descriptions.Item label="数据范围">{user?.data_scope?.type || '全量'}</Descriptions.Item>
          <Descriptions.Item label="功能权限" span={2}>
            {user?.role === '管理员'
              ? '全部'
              : (user?.functional_permissions || []).join('、') || '（未授权额外功能）'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="修改密码" style={{ maxWidth: 480 }}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, min: 6, message: '新密码至少 6 位' }]}
          >
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit">
            提交
          </Button>
        </Form>
      </Card>
    </div>
  )
}
