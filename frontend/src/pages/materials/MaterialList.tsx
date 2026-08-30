import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  message,
} from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { useAuthStore } from '@/store/auth'
import { PERM, useMetaStore } from '@/store/meta'
import { FILTER_CARD_STYLE, TABLE_PAGINATION, displayStatus, statusTagColor, visibleStatusOptions } from '@/theme'
import type { MaterialClassOut, MaterialOut, PageResult, TagOut } from '@/types'

export default function MaterialList() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const can = useAuthStore((s) => s.can)
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<MaterialOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [classes, setClasses] = useState<MaterialClassOut[]>([])
  const [tags, setTags] = useState<TagOut[]>([])
  const [detail, setDetail] = useState<MaterialOut | null>(null)

  const load = useCallback(
    async (targetPage = page) => {
      setLoading(true)
      try {
        const values = form.getFieldsValue()
        const { data } = await http.get<PageResult<MaterialOut>>('/materials', {
          params: { ...values, page: targetPage, page_size: 20 },
        })
        setRows(data.items)
        setTotal(data.total)
        setPage(data.page)
      } finally {
        setLoading(false)
      }
    },
    [form, page],
  )

  useEffect(() => {
    void http.get<MaterialClassOut[]>('/material-classes').then((r) => setClasses(r.data))
    void http.get<TagOut[]>('/tags').then((r) => setTags(r.data))
    void load(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const act = async (id: number, action: string) => {
    await http.post(`/materials/${id}/${action}`)
    message.success('操作成功')
    void load()
  }

  return (
    <Card
      title="资料列表"
      extra={
        <Space>
          <Link to="/materials/import">
            <Button>批量导入</Button>
          </Link>
          <Link to="/materials/new">
            <Button type="primary">新建资料</Button>
          </Link>
        </Space>
      }
    >
      <Form form={form} layout="inline" style={FILTER_CARD_STYLE} onFinish={() => load(1)}>
        <Form.Item name="keyword">
          <Input allowClear placeholder="标题/正文关键词" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item name="class_id">
          <Select
            allowClear
            placeholder="分类"
            style={{ width: 160 }}
            options={classes.map((c) => ({ label: c.name, value: c.id }))}
          />
        </Form.Item>
        <Form.Item name="tag">
          <Select
            allowClear
            showSearch
            placeholder="标签"
            style={{ width: 160 }}
            options={tags.map((t) => ({ label: t.name, value: t.name }))}
          />
        </Form.Item>
        <Form.Item name="status">
          <Select allowClear placeholder="状态" style={{ width: 130 }} options={visibleStatusOptions(options('material_status'))} />
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

      <Table<MaterialOut>
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
              <a onClick={() => setDetail(r)}>
                <Tooltip title={v}>{v}</Tooltip> {r.is_ai_product && <Tag color="purple">AI 产物</Tag>}
              </a>
            ),
          },
          { title: '分类', dataIndex: 'class_name', width: 120, ellipsis: true },
          {
            title: '标签',
            dataIndex: 'tags',
            width: 160,
            ellipsis: true,
            render: (v: string[]) => v.map((t) => <Tag key={t}>{t}</Tag>),
          },
          { title: '来源', dataIndex: 'source_type', width: 90 },
          { title: '可信度', dataIndex: 'trust_level', width: 80 },
          {
            title: '有效期',
            width: 190,
            render: (_, r) => `${r.valid_from} ~ ${r.valid_until}`,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 90,
            render: (v: string) => {
              const label = displayStatus(v, '已生效')
              return <Tag color={statusTagColor(label)}>{label}</Tag>
            },
          },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="edit" size="small" onClick={() => navigate(`/materials/${r.id}`)}>
                    编辑
                  </Button>,
                  r.status === '已生效' ? (
                    <Button key="disable" size="small" onClick={() => act(r.id, 'disable')}>
                      停用
                    </Button>
                  ) : null,
                  r.status === '已停用' ? (
                    <Button key="enable" size="small" onClick={() => act(r.id, 'enable')}>
                      启用
                    </Button>
                  ) : null,
                  r.status === '已过期' ? (
                    <Button key="discard" size="small" danger onClick={() => act(r.id, 'discard')}>
                      确认废弃
                    </Button>
                  ) : null,
                  can(PERM.材料删除) ? (
                    <Popconfirm
                      key="del"
                      title="确认删除该资料？"
                      onConfirm={async () => {
                        await http.delete(`/materials/${r.id}`)
                        message.success('已删除')
                        void load()
                      }}
                    >
                      <Button size="small" type="link" danger>
                        删除
                      </Button>
                    </Popconfirm>
                  ) : null,
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={!!detail}
        title={detail?.title}
        width={720}
        footer={null}
        onCancel={() => setDetail(null)}
      >
        <p>
          分类：{detail?.class_name}　状态：{displayStatus(detail?.status, '已生效')}　可信度：{detail?.trust_level}
        </p>
        <p>
          有效期：{detail?.valid_from} ~ {detail?.valid_until}
        </p>
        {detail?.source_url && (
          <p>
            来源链接：<a href={detail.source_url}>{detail.source_url}</a>
          </p>
        )}
        <div className="pre-wrap">{detail?.content}</div>
      </Modal>
    </Card>
  )
}
