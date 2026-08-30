/** 登录后默认首页：数据概览 + 快捷入口 + 待办 + 最近动态。 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BulbOutlined,
  CheckCircleOutlined,
  FileAddOutlined,
  FileTextOutlined,
  ImportOutlined,
  PlusCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { Badge, Button, Card, Col, List, Row, Space, Statistic, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { displayStatus } from '@/theme'
import type {
  AnalysisTaskOut,
  MaterialOut,
  PageResult,
  ScriptOut,
  TopicOut,
} from '@/types'

interface StatCard {
  key: string
  title: string
  total: number | null
  sub: string
}

interface TodoItem {
  key: string
  label: string
  count: number
  path: string
}

interface ActivityItem {
  key: string
  icon: React.ReactNode
  description: string
  time: string
  sortAt: number
}

const EMPTY_STATS: StatCard[] = [
  { key: 'materials', title: '资料总数', total: null, sub: '已生效 --' },
  { key: 'topics', title: '选题总数', total: null, sub: '待筛选 --' },
  { key: 'scripts', title: '脚本总数', total: null, sub: '已通过 --' },
  { key: 'analysis', title: '分析任务数', total: null, sub: '详情查看执行状态' },
]

async function safeTotal(path: string, params?: Record<string, string | number>): Promise<number | null> {
  try {
    const { data } = await http.get<PageResult<unknown>>(path, { params: { ...params, page: 1, page_size: 1 } })
    return data.total
  } catch {
    return null
  }
}

async function safeItems<T>(path: string, params?: Record<string, string | number>): Promise<T[]> {
  try {
    const { data } = await http.get<PageResult<T>>(path, { params: { ...params, page: 1, page_size: 5 } })
    return data.items
  } catch {
    return []
  }
}

export default function Home() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<StatCard[]>(EMPTY_STATS)
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [
        matTotal,
        matActive,
        topicTotal,
        topicPending,
        scriptTotal,
        scriptApproved,
        analysisTotal,
        recentTopics,
        recentScripts,
        recentMaterials,
        recentTasks,
      ] = await Promise.all([
        safeTotal('/materials'),
        safeTotal('/materials', { status: '已生效' }),
        safeTotal('/topics'),
        safeTotal('/topics', { status: '待筛选' }),
        safeTotal('/scripts'),
        safeTotal('/scripts', { status: '已通过' }),
        safeTotal('/analysis-tasks'),
        safeItems<TopicOut>('/topics'),
        safeItems<ScriptOut>('/scripts'),
        safeItems<MaterialOut>('/materials'),
        safeItems<AnalysisTaskOut>('/analysis-tasks'),
      ])

      setStats([
        {
          key: 'materials',
          title: '资料总数',
          total: matTotal,
          sub: matActive !== null ? `已生效 ${matActive}` : '已生效 --',
        },
        {
          key: 'topics',
          title: '选题总数',
          total: topicTotal,
          sub: topicPending !== null ? `待筛选 ${topicPending}` : '待筛选 --',
        },
        {
          key: 'scripts',
          title: '脚本总数',
          total: scriptTotal,
          sub: scriptApproved !== null ? `已通过 ${scriptApproved}` : '已通过 --',
        },
        {
          key: 'analysis',
          title: '分析任务数',
          total: analysisTotal,
          sub: '详情查看执行状态',
        },
      ])

      const todoList: TodoItem[] = []
      if (topicPending !== null && topicPending > 0) {
        todoList.push({ key: 'topic', label: '待筛选选题', count: topicPending, path: '/topics' })
      }
      setTodos(todoList)

      const acts: ActivityItem[] = []
      recentTopics.forEach((t) => {
        acts.push({
          key: `topic-${t.id}`,
          icon: <BulbOutlined style={{ color: '#faad14' }} />,
          description: t.batch_no
            ? `生成选题批次 ${t.batch_no}（${t.title}）`
            : `新建选题「${t.title}」`,
          time: dayjs(t.created_at).format('MM-DD HH:mm'),
          sortAt: dayjs(t.created_at).valueOf(),
        })
      })
      recentScripts.forEach((s) => {
        const desc =
          s.status === '已通过' && s.reviewed_at
            ? `脚本已通过（#${s.id}）`
            : `脚本更新（#${s.id}，${displayStatus(s.status, '已通过')}）`
        acts.push({
          key: `script-${s.id}`,
          icon: <FileTextOutlined style={{ color: '#1677ff' }} />,
          description: desc,
          time: dayjs(s.reviewed_at || s.modified_at || s.created_at).format('MM-DD HH:mm'),
          sortAt: dayjs(s.reviewed_at || s.modified_at || s.created_at).valueOf(),
        })
      })
      recentMaterials.forEach((m) => {
        acts.push({
          key: `mat-${m.id}`,
          icon: <FileAddOutlined style={{ color: '#52c41a' }} />,
          description: `资料「${m.title}」（${displayStatus(m.status, '已生效')}）`,
          time: dayjs(m.created_at).format('MM-DD HH:mm'),
          sortAt: dayjs(m.created_at).valueOf(),
        })
      })
      recentTasks.forEach((task) => {
        acts.push({
          key: `task-${task.id}`,
          icon: <CheckCircleOutlined style={{ color: '#722ed1' }} />,
          description: `分析任务「${task.name || task.type}」（${displayStatus(task.status, '已确认')}）`,
          time: dayjs(task.created_at).format('MM-DD HH:mm'),
          sortAt: dayjs(task.created_at).valueOf(),
        })
      })
      acts.sort((a, b) => b.sortAt - a.sortAt)
      setActivities(acts.slice(0, 5))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const roleLabel = user?.role === '管理员' ? '管理员' : '成员'

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Typography.Title level={4} style={{ margin: 0 }}>
              欢迎回来，{user?.username || '操盘手'}
            </Typography.Title>
            <Tag color={user?.role === '管理员' ? 'gold' : 'blue'}>{roleLabel}</Tag>
          </Space>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
            刷新
          </Button>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        {stats.map((s) => (
          <Col xs={24} sm={12} lg={6} key={s.key}>
            <Card loading={loading}>
              <Statistic title={s.title} value={s.total ?? '--'} />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{s.sub}</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="快捷入口">
        <Space wrap>
          <Button type="primary" icon={<BulbOutlined />} onClick={() => navigate('/topics/generate')}>
            去生成选题
          </Button>
          <Button icon={<FileTextOutlined />} onClick={() => navigate('/scripts/generate')}>
            去生成脚本
          </Button>
          <Button icon={<ImportOutlined />} onClick={() => navigate('/materials/import')}>
            导入资料
          </Button>
          <Button icon={<PlusCircleOutlined />} onClick={() => navigate('/analysis/tasks')}>
            新建分析
          </Button>
        </Space>
      </Card>

      <Card title="待办提醒">
        {todos.length === 0 ? (
          <Typography.Text type="secondary">暂无待办，去生成一批选题吧</Typography.Text>
        ) : (
          <List
            dataSource={todos}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(item.path)}
                extra={<Badge count={item.count} />}
              >
                {item.label}
              </List.Item>
            )}
          />
        )}
      </Card>

      <Card title="最近动态">
        {activities.length === 0 ? (
          <Typography.Text type="secondary">暂无动态</Typography.Text>
        ) : (
          <List
            dataSource={activities}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta avatar={item.icon} title={item.description} description={item.time} />
              </List.Item>
            )}
          />
        )}
      </Card>
    </Space>
  )
}
