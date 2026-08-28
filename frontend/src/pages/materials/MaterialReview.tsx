import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import type { MaterialOut, PageResult } from '@/types'

export default function MaterialReview() {
  const [rows, setRows] = useState<MaterialOut[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<PageResult<MaterialOut>>('/materials', {
        params: { status: '待审核', page: 1, page_size: 100 },
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
    await http.post(`/materials/${id}/review`, { approved })
    message.success(approved ? '已通过，资料生效' : '已驳回')
    void load()
  }

  return (
    <Card title="资料审核（待审核队列）">
      <Table<MaterialOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        expandable={{
          expandedRowRender: (r) => <div className="pre-wrap">{r.content}</div>,
        }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          {
            title: '标题',
            dataIndex: 'title',
            render: (v: string, r) => (
              <>
                {v} {r.is_ai_product && <Tag color="purple">AI 产物</Tag>}
              </>
            ),
          },
          { title: '分类', dataIndex: 'class_name', width: 140 },
          { title: '可信度', dataIndex: 'trust_level', width: 90 },
          {
            title: '有效期',
            width: 200,
            render: (_, r) => `${r.valid_from} ~ ${r.valid_until}`,
          },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="ok" type="primary" size="small" onClick={() => review(r.id, true)}>
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
