/** 主框架：侧边菜单（按角色/权限过滤）+ 顶栏 + 路由出口。 */
import { useEffect, useMemo } from 'react'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Alert, Avatar, Dropdown, Layout, Menu, Tag, Typography } from 'antd'
import {
  BarChartOutlined,
  BookOutlined,
  BulbOutlined,
  FileTextOutlined,
  LogoutOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/store/auth'
import { useMetaStore } from '@/store/meta'

const { Header, Sider, Content } = Layout

export default function MainLayout() {
  const { user, token, logout, isAdmin, mustChangePassword } = useAuthStore()
  const loadMeta = useMetaStore((s) => s.load)
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (token) void loadMeta()
  }, [token, loadMeta])

  const items = useMemo(() => {
    const base = [
      {
        key: 'materials',
        icon: <BookOutlined />,
        label: '资料库',
        children: [
          { key: '/materials', label: <Link to="/materials">资料列表</Link> },
          { key: '/materials/new', label: <Link to="/materials/new">新建资料</Link> },
          { key: '/materials/import', label: <Link to="/materials/import">批量导入</Link> },
          { key: '/materials/review', label: <Link to="/materials/review">资料审核</Link> },
          { key: '/material-classes', label: <Link to="/material-classes">分类管理</Link> },
          { key: '/tags', label: <Link to="/tags">标签管理</Link> },
        ],
      },
      {
        key: 'topics',
        icon: <BulbOutlined />,
        label: '选题库',
        children: [
          { key: '/topics', label: <Link to="/topics">选题列表</Link> },
          { key: '/topics/generate', label: <Link to="/topics/generate">批量生成</Link> },
          { key: '/topics/batches', label: <Link to="/topics/batches">生成批次</Link> },
          { key: '/topics/new', label: <Link to="/topics/new">手动新增</Link> },
        ],
      },
      {
        key: 'scripts',
        icon: <FileTextOutlined />,
        label: '脚本库',
        children: [
          { key: '/scripts', label: <Link to="/scripts">脚本列表</Link> },
          { key: '/scripts/generate', label: <Link to="/scripts/generate">基于选题生成</Link> },
          { key: '/scripts/new', label: <Link to="/scripts/new">独立创建</Link> },
          { key: '/scripts/review', label: <Link to="/scripts/review">脚本审核</Link> },
        ],
      },
      {
        key: 'analysis',
        icon: <BarChartOutlined />,
        label: '数据分析',
        children: [
          { key: '/analysis/data-sources', label: <Link to="/analysis/data-sources">数据源管理</Link> },
          { key: '/analysis/raw-data', label: <Link to="/analysis/raw-data">原始数据</Link> },
          { key: '/analysis/tasks', label: <Link to="/analysis/tasks">分析任务</Link> },
          { key: '/analysis/prompts', label: <Link to="/analysis/prompts">提示词模板</Link> },
        ],
      },
    ]
    if (isAdmin()) {
      base.push({
        key: 'admin',
        icon: <TeamOutlined />,
        label: '权限管理',
        children: [{ key: '/admin/users', label: <Link to="/admin/users">成员与权限</Link> }],
      })
    }
    return base
  }, [isAdmin])

  if (!token) return <Navigate to="/login" replace />

  const openKeys = items.map((i) => i.key)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="dark">
        <div style={{ color: '#fff', padding: '18px 16px', fontSize: 16, fontWeight: 600 }}>
          Forge 新媒体运营系统
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={openKeys}
          items={items}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: 12,
            paddingInline: 24,
          }}
        >
          <Tag color={user?.role === '管理员' ? 'gold' : 'blue'}>{user?.role}</Tag>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'profile',
                  icon: <SettingOutlined />,
                  label: '修改密码',
                  onClick: () => navigate('/profile'),
                },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: async () => {
                    await logout()
                    navigate('/login')
                  },
                },
              ],
            }}
          >
            <span style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} />{' '}
              <Typography.Text>{user?.username}</Typography.Text>
            </span>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16 }}>
          {mustChangePassword && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              message="您正在使用默认密码登录，请尽快前往「修改密码」更换。"
              action={<Link to="/profile">去修改</Link>}
            />
          )}
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
