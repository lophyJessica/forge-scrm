import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Form, Input, Typography, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/store/auth'

export default function Login() {
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const resp = await login(values.username, values.password)
      if (resp.must_change_password) {
        message.warning('首次登录使用的是默认密码，请尽快修改密码')
      }
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f0f2f5',
      }}
    >
      <Card style={{ width: 380 }}>
        <Typography.Title level={4} style={{ textAlign: 'center' }}>
          姐夫新媒体运营系统
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          账号密码登录（一期不支持扫码/验证码）
        </Typography.Paragraph>
        <Form layout="vertical" onFinish={onFinish} autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入账号' }]}>
            <Input size="large" prefix={<UserOutlined />} placeholder="账号" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password size="large" prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" size="large" block htmlType="submit" loading={loading}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  )
}
