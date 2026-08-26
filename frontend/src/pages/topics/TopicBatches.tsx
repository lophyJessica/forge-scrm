import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Table } from 'antd'
import { http } from '@/api/client'
import { TABLE_PAGINATION } from '@/theme'
import type { TopicBatchOut } from '@/types'

export default function TopicBatches() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<TopicBatchOut[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    http
      .get<TopicBatchOut[]>('/topics/batches')
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Card title="生成批次（批次记录保留，可回溯每次生成结果）">
      <Table<TopicBatchOut>
        rowKey="batch_no"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, pageSize: 20 }}
        columns={[
          { title: '批次号', dataIndex: 'batch_no', width: 220 },
          { title: '业务方向', dataIndex: 'direction' },
          { title: '选题数', dataIndex: 'count', width: 100 },
          { title: '生成时间', dataIndex: 'created_at', width: 200 },
          {
            title: '操作',
            width: 120,
            render: (_, r) => (
              <Button size="small" onClick={() => navigate(`/topics?batch_no=${r.batch_no}`)}>
                查看选题
              </Button>
            ),
          },
        ]}
      />
    </Card>
  )
}
