import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Table, Tag, Tooltip, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import type { PageResult, ScriptOut } from '@/types'

export default function ScriptReview() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<ScriptOut[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<ScriptOut>>('/scripts', {
        params: { status: '待审核', page_size: 100 },
      })
      setRows(data.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const review = async (id: number, approved: boolean) => {
    await http.post(`/scripts/${id}/review`, { approved })
    message.success(approved ? '已通过' : '已驳回（已废弃）')
    void load()
  }

  return (
    <Card title="脚本审核（一期仅管理员）">
      <Table<ScriptOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        expandable={{
          expandedRowRender: (r) => <pre className="pre-wrap">{r.content}</pre>,
        }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '正文摘要', dataIndex: 'content', ellipsis: true, render: (v: string) => <Tooltip title={v}>{v}</Tooltip> },
          {
            title: '来源选题',
            dataIndex: 'topic_title',
            width: 200,
            render: (v: string | null, r) => (r.topic_id ? v || `#${r.topic_id}` : <Tag>独立创建</Tag>),
          },
          { title: '语言风格', dataIndex: 'style', width: 110 },
          { title: '版本', dataIndex: 'current_version', width: 80, render: (v) => `v${v}` },
          {
            title: '操作',
            width: 220,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="d" size="small" onClick={() => navigate(`/scripts/${r.id}`)}>
                    详情
                  </Button>,
                  <Button key="ok" size="small" type="primary" onClick={() => review(r.id, true)}>
                    通过
                  </Button>,
                  <Button key="no" size="small" type="link" danger onClick={() => review(r.id, false)}>
                    驳回
                  </Button>,
                ]}
              />
            ),
          },
        ]}
      />
    </Card>
  )
}
