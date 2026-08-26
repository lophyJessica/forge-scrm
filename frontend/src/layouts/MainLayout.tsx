/** 主框架：侧边菜单（默认折叠 + 记忆）+ 顶栏 + 路由出口。 */
import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Alert, Avatar, Breadcrumb, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import {
  BarChartOutlined,
  BookOutlined,
  BulbOutlined,
  FileTextOutlined,
  HomeOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
  RadarChartOutlined,
  RobotOutlined,
  SlidersOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/store/auth'
import { useMetaStore } from '@/store/meta'

const { Header, Sider, Content } = Layout

const SIDER_COLLAPSED_KEY = 'scrm_sider_collapsed'
const SIDER_WIDTH = 220
const SIDER_COLLAPSED_WIDTH = 64

function readCollapsed(): boolean {
  const stored = localStorage.getItem(SIDER_COLLAPSED_KEY)
  return stored === null ? true : stored === 'true'
}

interface MenuRouteDefinition {
  key: string
  label: string
}

interface MenuGroupDefinition {
  key: string
  label: string
  icon: React.ReactNode
  parentPath: string
  children: MenuRouteDefinition[]
}

interface BreadcrumbRouteDefinition {
  label: string
  groupKey?: string
  path?: string
  match?: RegExp
}

const NAV_GROUPS: MenuGroupDefinition[] = [
  {
    key: 'materials',
    icon: <BookOutlined />,
    label: '资料库',
    parentPath: '/materials',
    children: [
      { key: '/materials', label: '资料列表' },
      { key: '/materials/new', label: '新建资料' },
      { key: '/materials/import', label: '批量导入' },
      { key: '/materials/review', label: '资料审核' },
      { key: '/material-classes', label: '分类管理' },
      { key: '/tags', label: '标签管理' },
    ],
  },
  {
    key: 'topics',
    icon: <BulbOutlined />,
    label: '选题库',
    parentPath: '/topics',
    children: [
      { key: '/topics', label: '选题列表' },
      { key: '/topics/generate', label: '批量生成' },
      { key: '/topics/batches', label: '生成批次' },
      { key: '/topics/new', label: '手动新增' },
    ],
  },
  {
    key: 'scripts',
    icon: <FileTextOutlined />,
    label: '脚本库',
    parentPath: '/scripts',
    children: [
      { key: '/scripts', label: '脚本列表' },
      { key: '/scripts/generate', label: '基于选题生成' },
      { key: '/scripts/new', label: '独立创建' },
      { key: '/scripts/review', label: '脚本审核' },
    ],
  },
  {
    key: 'analysis',
    icon: <BarChartOutlined />,
    label: '数据分析',
    parentPath: '/analysis/tasks',
    children: [
      { key: '/analysis/data-sources', label: '数据源管理' },
      { key: '/analysis/raw-data', label: '原始数据' },
      { key: '/analysis/tasks', label: '分析任务' },
    ],
  },
]

const ADMIN_GROUP: MenuGroupDefinition = {
  key: 'admin',
  icon: <TeamOutlined />,
  label: '权限管理',
  parentPath: '/admin/users',
  children: [
    { key: '/admin/users', label: '成员与权限' },
  ],
}

const PHASE2_GROUPS: MenuGroupDefinition[] = [
  {
    key: 'collection',
    icon: <RadarChartOutlined />,
    label: '内容管理',
    parentPath: '/collection/tasks',
    children: [
      { key: '/collection/benchmark-accounts', label: '对标账号' },
      { key: '/collection/tasks', label: '自动采集' },
    ],
  },
  {
    key: 'templates',
    icon: <SlidersOutlined />,
    label: '模板管理',
    parentPath: '/admin/prompt-templates',
    children: [{ key: '/admin/prompt-templates', label: '提示词模板' }],
  },
  {
    key: 'research',
    icon: <RobotOutlined />,
    label: 'AI 模块',
    parentPath: '/research/tasks',
    children: [{ key: '/research/tasks', label: '研究助手' }],
  },
]

const ALL_NAV_GROUPS = [...NAV_GROUPS, ...PHASE2_GROUPS, ADMIN_GROUP]

// 详情页不在侧边菜单中，仍由当前真实路由匹配出面包屑标题。
const DETAIL_ROUTES: BreadcrumbRouteDefinition[] = [
  { match: /^\/materials\/[^/]+$/, label: '编辑资料', groupKey: 'materials' },
  { match: /^\/topics\/[^/]+\/edit$/, label: '修改选题', groupKey: 'topics' },
  { match: /^\/topics\/[^/]+$/, label: '选题详情', groupKey: 'topics' },
  { match: /^\/scripts\/[^/]+\/versions$/, label: '版本历史', groupKey: 'scripts' },
  { match: /^\/scripts\/[^/]+\/edit$/, label: '修改脚本', groupKey: 'scripts' },
  { match: /^\/scripts\/[^/]+$/, label: '脚本详情', groupKey: 'scripts' },
  { match: /^\/analysis\/tasks\/[^/]+$/, label: '分析任务详情', groupKey: 'analysis' },
  { match: /^\/research\/reports\/[^/]+$/, label: '研究报告', groupKey: 'research' },
  { path: '/profile', label: '修改密码' },
]

function routeDefinitionForPath(path: string): BreadcrumbRouteDefinition | undefined {
  for (const group of ALL_NAV_GROUPS) {
    const route = group.children.find((child) => child.key === path)
    if (route) return { path: route.key, label: route.label, groupKey: group.key }
  }
  return DETAIL_ROUTES.find((route) => route.path === path || route.match?.test(path))
}

function breadcrumbItemsForPath(path: string) {
  if (path === '/') return []
  const route = routeDefinitionForPath(path)
  if (!route) return []
  const group = route.groupKey ? ALL_NAV_GROUPS.find(({ key }) => key === route.groupKey) : undefined
  return [
    ...(group ? [{ title: <Link to={group.parentPath}>{group.label}</Link> }] : []),
    { title: route.label },
  ]
}

function parentKeyForPath(path: string, menuGroups: MenuGroupDefinition[]): string | undefined {
  if (path === '/') return undefined
  return menuGroups.find(
    ({ key, children }) =>
      path.startsWith(`/${key}`) ||
      children?.some(({ key: childKey }) => path === childKey || path.startsWith(`${childKey}/`)),
  )?.key
}

export default function MainLayout() {
  const { user, token, logout, isAdmin, mustChangePassword } = useAuthStore()
  const loadMeta = useMetaStore((s) => s.load)
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [openKeys, setOpenKeys] = useState<string[]>([])

  useEffect(() => {
    if (token) void loadMeta()
  }, [token, loadMeta])

  const visibleGroups = useMemo(() => (isAdmin() ? ALL_NAV_GROUPS : NAV_GROUPS), [isAdmin])

  const moduleItems = useMemo(
    () =>
      visibleGroups.map((group) => ({
        key: group.key,
        icon: group.icon,
        label: group.label,
        children: group.children.map((route) => ({
          key: route.key,
          label: <Link to={route.key}>{route.label}</Link>,
        })),
      })),
    [visibleGroups],
  )

  const items = useMemo(
    () => [
      {
        key: '/',
        icon: <HomeOutlined />,
        label: <Link to="/">首页</Link>,
      },
      ...moduleItems,
    ],
    [moduleItems],
  )

  useEffect(() => {
    if (collapsed) {
      setOpenKeys([])
      return
    }
    const parent = parentKeyForPath(location.pathname, visibleGroups)
    setOpenKeys(parent ? [parent] : [])
  }, [collapsed, location.pathname, visibleGroups])

  const toggleCollapsed = () => {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem(SIDER_COLLAPSED_KEY, String(next))
    if (next) setOpenKeys([])
  }

  if (!token) return <Navigate to="/login" replace />

  const selectedKey = location.pathname === '/' ? '/' : location.pathname
  const breadcrumbItems = breadcrumbItemsForPath(location.pathname)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={SIDER_WIDTH}
        collapsedWidth={SIDER_COLLAPSED_WIDTH}
        theme="dark"
      >
        <div
          style={{
            color: '#fff',
            padding: collapsed ? '18px 8px' : '18px 16px',
            fontSize: collapsed ? 12 : 16,
            fontWeight: 600,
            textAlign: collapsed ? 'center' : 'left',
            whiteSpace: collapsed ? 'normal' : 'nowrap',
            lineHeight: 1.4,
          }}
        >
          {collapsed ? 'Forge' : 'Forge 新媒体运营系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          openKeys={collapsed ? [] : openKeys}
          onOpenChange={(keys) => {
            if (!collapsed) setOpenKeys(keys as string[])
          }}
          items={items}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingInline: 24,
          }}
        >
          <Space>
            <span style={{ cursor: 'pointer', fontSize: 18 }} onClick={toggleCollapsed}>
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
            {breadcrumbItems.length > 0 ? (
              <Breadcrumb items={breadcrumbItems} />
            ) : (
              <Typography.Text type="secondary">首页</Typography.Text>
            )}
          </Space>
          <Space>
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
          </Space>
        </Header>
        <Content style={{ margin: 16, background: 'transparent' }}>
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
