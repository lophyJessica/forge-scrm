import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import { http } from '@/api/client'
import { TableActions } from '@/components/TableActions'
import { useMetaStore } from '@/store/meta'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { PageResult, ScriptOut } from '@/types'

export default function ScriptList() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<ScriptOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const load = useCallback(
    async (targetPage = 1) => {
      setLoading(true)
      try {
        const { data } = await http.get<PageResult<ScriptOut>>('/scripts', {
          params: { ...form.getFieldsValue(), page: targetPage, page_size: 20 },
        })
        setRows(data.items)
        setTotal(data.total)
        setPage(data.page)
      } finally {
        setLoading(false)
      }
    },
    [form],
  )

  useEffect(() => {
    const topicId = search.get('topic_id')
    if (topicId) form.setFieldValue('topic_id', Number(topicId))
    void load(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const act = async (id: number, path: string, tip: string) => {
    await http.post(`/scripts/${id}/${path}`)
    message.success(tip)
    void load(page)
  }

  return (
    <Card
      title="脚本列表"
      extra={
        <Space>
          <Link to="/scripts/new">
            <Button>独立创建</Button>
          </Link>
          <Link to="/scripts/generate">
            <Button type="primary">基于选题生成</Button>
          </Link>
        </Space>
      }
    >
      <Form form={form} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load(1)}>
        <Form.Item name="keyword">
          <Input allowClear placeholder="正文关键词" style={{ width: 200 }} />
        </Form.Item>
        <Form.Item name="topic_id">
          <Input allowClear placeholder="选题 ID" style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="style">
          <Select allowClear placeholder="语言风格" style={{ width: 140 }} options={options('script_style')} />
        </Form.Item>
        <Form.Item name="status">
          <Select allowClear placeholder="状态" style={{ width: 130 }} options={options('script_status')} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              查询
            </Button>
            <Button
              onClick={() => {
                form.resetFields()
                void load(1)
              }}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<ScriptOut>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (p) => load(p) }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          {
            title: '正文摘要',
            dataIndex: 'content',
            ellipsis: true,
            render: (v: string, r) => (
              <a onClick={() => navigate(`/scripts/${r.id}`)}>
                <Tooltip title={v}>
                  <Typography.Text ellipsis style={{ maxWidth: 360 }}>
                    {v}
                  </Typography.Text>
                </Tooltip>
              </a>
            ),
          },
          {
            title: '来源选题',
            dataIndex: 'topic_title',
            width: 180,
            ellipsis: true,
            render: (v: string | null, r) =>
              r.topic_id ? <a onClick={() => navigate(`/topics/${r.topic_id}`)}>{v || `#${r.topic_id}`}</a> : <Tag>独立创建</Tag>,
          },
          { title: '语言风格', dataIndex: 'style', width: 110 },
          { title: '版本', dataIndex: 'current_version', width: 80, render: (v) => `v${v}` },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (v: string) => <Tag color={statusTagColor(v)}>{v}</Tag>,
          },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="d" size="small" onClick={() => navigate(`/scripts/${r.id}`)}>
                    详情
                  </Button>,
                  <Button key="v" size="small" onClick={() => navigate(`/scripts/${r.id}/versions`)}>
                    版本
                  </Button>,
                  r.status === '草稿' ? (
                    <Button key="s" size="small" type="primary" onClick={() => act(r.id, 'submit', '已提交审核')}>
                      提交审核
                    </Button>
                  ) : null,
                  r.status === '已通过' ? (
                    <Button key="u" size="small" type="primary" onClick={() => act(r.id, 'mark-used', '已标记为已使用')}>
                      标记已使用
                    </Button>
                  ) : null,
                  ['草稿', '待审核', '已通过'].includes(r.status) ? (
                    <Button key="x" size="small" type="link" danger onClick={() => act(r.id, 'discard', '已废弃')}>
                      废弃
                    </Button>
                  ) : null,
                ]}
              />
            ),
          },
        ]}
      />
    </Card>
  )
}
