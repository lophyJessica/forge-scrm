import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, Modal, Space, Tag, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { PERM } from '@/store/meta'
import { displayStatus, statusTagColor } from '@/theme'
import type { ScriptOut } from '@/types'

export default function ScriptDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const can = useAuthStore((s) => s.can)
  const [script, setScript] = useState<ScriptOut | null>(null)

  const load = useCallback(async () => {
    const { data } = await http.get<ScriptOut>(`/scripts/${id}`)
    setScript(data)
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (!script) return <Card loading />

  const statusLabel = displayStatus(script.status, '已通过')

  const act = async (path: string, tip: string, body?: unknown) => {
    await http.post(`/scripts/${id}/${path}`, body)
    message.success(tip)
    void load()
  }

  return (
    <Card
      title={`脚本 #${script.id} · v${script.current_version}`}
      extra={
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/scripts')}>返回列表</Button>
          {can(PERM.脚本版本查看) && (
            <Button onClick={() => navigate(`/scripts/${script.id}/versions`)}>版本历史</Button>
          )}
          {can(PERM.脚本修改) && <Button onClick={() => navigate(`/scripts/${script.id}/edit`)}>修改</Button>}
          {script.status === '已通过' && (
            <Button type="primary" onClick={() => act('mark-used', '已标记为已使用')}>
              标记已使用
            </Button>
          )}
          {['草稿', '待审核', '已通过'].includes(script.status) && (
            <Button
              danger
              onClick={() => Modal.confirm({
                title: '确认废弃该脚本？',
                content: '废弃后该脚本将不再进入后续使用流程。',
                okText: '确认废弃',
                okType: 'danger',
                cancelText: '取消',
                onOk: () => act('discard', '已废弃'),
              })}
            >
              废弃
            </Button>
          )}
        </Space>
      }
    >
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="状态">
          <Tag color={statusTagColor(statusLabel)}>{statusLabel}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="当前版本">v{script.current_version}</Descriptions.Item>
        <Descriptions.Item label="来源选题">
          {script.topic_id ? (
            <a onClick={() => navigate(`/topics/${script.topic_id}`)}>
              {script.topic_title || `#${script.topic_id}`}
            </a>
          ) : (
            <Tag>独立创建</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="语言风格">{script.style}</Descriptions.Item>
        <Descriptions.Item label="内容要素" span={2}>
          {script.content_elements.length ? script.content_elements.map((e) => <Tag key={e}>{e}</Tag>) : '—'}
        </Descriptions.Item>
        <Descriptions.Item label="引用资料" span={2}>
          {script.material_refs?.length ? script.material_refs.map((m) => <Tag key={m}>#{m}</Tag>) : '—'}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{script.created_at}</Descriptions.Item>
        <Descriptions.Item label="最后修改">{script.modified_at}</Descriptions.Item>
      </Descriptions>
      <Card type="inner" title="脚本正文">
        <pre className="pre-wrap">{script.content}</pre>
      </Card>
    </Card>
  )
}
