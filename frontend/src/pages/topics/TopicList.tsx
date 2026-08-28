import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button, Card, Form, Input, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { useMetaStore } from '@/store/meta'
import { TABLE_PAGINATION, statusTagColor } from '@/theme'
import type { PageResult, TopicOut } from '@/types'

export default function TopicList() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<TopicOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const load = useCallback(
    async (targetPage = 1) => {
      setLoading(true)
      try {
        const { data } = await http.get<PageResult<TopicOut>>('/topics', {
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
    const batch = search.get('batch_no')
    if (batch) form.setFieldValue('batch_no', batch)
    void load(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const screen = async (id: number, result: '选中' | '淘汰') => {
    await http.post(`/topics/${id}/screen`, { screening_result: result })
    message.success(result === '选中' ? '已选定' : '已淘汰')
    void load(page)
  }

  return (
    <Card
      title="选题列表"
      extra={
        <Space>
          <Link to="/topics/new">
            <Button>手动新增</Button>
          </Link>
          <Link to="/topics/generate">
            <Button type="primary">批量生成</Button>
          </Link>
        </Space>
      }
    >
      <Form form={form} layout="inline" style={{ marginBottom: 16 }} onFinish={() => load(1)}>
        <Form.Item name="keyword">
          <Input allowClear placeholder="标题关键词" style={{ width: 200 }} />
        </Form.Item>
        <Form.Item name="direction">
          <Input allowClear placeholder="业务方向" style={{ width: 150 }} />
        </Form.Item>
        <Form.Item name="specialty">
          <Select allowClear placeholder="专业方向" style={{ width: 200 }} options={options('specialty')} />
        </Form.Item>
        <Form.Item name="status">
          <Select allowClear placeholder="状态" style={{ width: 130 }} options={options('topic_status')} />
        </Form.Item>
        <Form.Item name="batch_no">
          <Input allowClear placeholder="批次号" style={{ width: 160 }} />
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

      <Table<TopicOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (p) => load(p) }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          {
            title: '标题',
            dataIndex: 'title',
            ellipsis: true,
            render: (v: string, r) => (
              <a onClick={() => navigate(`/topics/${r.id}`)}>
                <Tooltip title={v}>{v}</Tooltip>
              </a>
            ),
          },
          { title: '业务方向', dataIndex: 'direction', width: 130, ellipsis: true },
          { title: '专业方向', dataIndex: 'specialty', width: 160, ellipsis: true },
          {
            title: '批次',
            dataIndex: 'batch_no',
            width: 150,
            render: (v) => v || <Tag>独立创建</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 110,
            render: (v: string) => <Tag color={statusTagColor(v)}>{v}</Tag>,
          },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="detail" size="small" onClick={() => navigate(`/topics/${r.id}`)}>
                    详情
                  </Button>,
                  r.status === '待筛选' ? (
                    <Button key="ok" type="primary" size="small" onClick={() => screen(r.id, '选中')}>
                      选中
                    </Button>
                  ) : null,
                  r.status === '待筛选' ? (
                    <Button key="no" size="small" type="link" danger onClick={() => screen(r.id, '淘汰')}>
                      淘汰
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
