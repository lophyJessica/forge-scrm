import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Modal, Popconfirm, Select, Space, Table, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import type { ScriptDiffOut, ScriptVersionOut } from '@/types'

export default function ScriptVersions() {
  const { id } = useParams()
  const navigate = useNavigate()
  const can = useAuthStore((s) => s.can)
  const [rows, setRows] = useState<ScriptVersionOut[]>([])
  const [loading, setLoading] = useState(false)
  const [left, setLeft] = useState<number>()
  const [right, setRight] = useState<number>()
  const [diff, setDiff] = useState<ScriptDiffOut | null>(null)
  const [preview, setPreview] = useState<ScriptVersionOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await http.get<ScriptVersionOut[]>(`/scripts/${id}/versions`)
      setRows(data)
      if (data.length >= 2) {
        setLeft(data[data.length - 2].version)
        setRight(data[data.length - 1].version)
      }
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const compare = async () => {
    if (!left || !right) {
      message.warning('请选择两个版本')
      return
    }
    const { data } = await http.get<ScriptDiffOut>(`/scripts/${id}/diff`, { params: { left, right } })
    setDiff(data)
  }

  const rollback = async (version: number) => {
    await http.post(`/scripts/${id}/rollback`, { version })
    message.success(`已回退到 v${version}（生成新版本并保留回退记录）`)
    void load()
  }

  const opts = rows.map((r) => ({ label: `v${r.version}`, value: r.version }))

  return (
    <Card
      title={`脚本 #${id} 版本历史`}
      extra={<Button onClick={() => navigate(`/scripts/${id}`)}>返回脚本</Button>}
    >
      <Space style={{ marginBottom: 24 }}>
        <Select value={left} onChange={setLeft} options={opts} style={{ width: 110 }} placeholder="左版本" />
        <span>对比</span>
        <Select value={right} onChange={setRight} options={opts} style={{ width: 110 }} placeholder="右版本" />
        <Button type="primary" onClick={compare}>
          查看差异
        </Button>
      </Space>

      <Table<ScriptVersionOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        columns={[
          { title: '版本', dataIndex: 'version', width: 90, render: (v) => `v${v}` },
          { title: '备注', dataIndex: 'note', render: (v) => v || '—' },
          { title: '修改人', dataIndex: 'changed_by', width: 100 },
          { title: '修改时间', dataIndex: 'changed_at', width: 200 },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <Space size={8}>
                <Button size="small" onClick={() => setPreview(r)}>
                  查看快照
                </Button>
                {can(PERM.脚本版本回退) && (
                  <Popconfirm title={`确认回退到 v${r.version}？`} onConfirm={() => rollback(r.version)}>
                    <Button size="small" type="link" danger>
                      回退
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal open={!!diff} onCancel={() => setDiff(null)} footer={null} width={720} title="版本差异">
        <pre className="pre-wrap" style={{ maxHeight: 520, overflow: 'auto' }}>
          {diff?.diff || '（两版本内容一致）'}
        </pre>
      </Modal>
      <Modal
        open={!!preview}
        onCancel={() => setPreview(null)}
        footer={null}
        width={720}
        title={`v${preview?.version} 内容快照`}
      >
        <pre className="pre-wrap" style={{ maxHeight: 520, overflow: 'auto' }}>
          {preview?.content_snapshot}
        </pre>
      </Modal>
    </Card>
  )
}
