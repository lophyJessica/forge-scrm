import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { useParams } from 'react-router-dom'
import { Alert, Card, Descriptions, Divider, List, Skeleton, Space, Tag, Typography } from 'antd'
import { http } from '@/api/client'
import { statusTagColor } from '@/theme'
import type { ResearchReferenceOut, ResearchReportOut } from '@/types'

function pretty(value: Record<string, unknown> | null | undefined) {
  return value ? JSON.stringify(value, null, 2) : '—'
}

async function loadReport(taskOrReportId: string) {
  try {
    return (await http.get<ResearchReportOut>(`/research-tasks/${taskOrReportId}/report`)).data
  } catch (error) {
    if (!isAxiosError(error) || error.response?.status !== 404) throw error
    return (await http.get<ResearchReportOut>(`/research-reports/${taskOrReportId}`)).data
  }
}

export default function ResearchReport() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<ResearchReportOut | null>(null)
  const [references, setReferences] = useState<ResearchReferenceOut[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    if (!id) return undefined
    loadReport(id).then(async (loadedReport) => {
      if (!active) return
      setReport(loadedReport)
      if (loadedReport.references) {
        setReferences(loadedReport.references)
        return
      }
      const response = await http.get<{ items: ResearchReferenceOut[] }>(`/research-references`, { params: { report_id: loadedReport.id, page_size: 200 } })
      if (active) setReferences(response.data.items)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [id])

  if (loading) return <Card><Skeleton active /></Card>
  if (!report) return <Alert type="error" message="研究报告不存在或加载失败" />

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>{report.title}</Typography.Title>
          {report.is_ai_product && <Tag color="purple">AI 生成</Tag>}
          <Tag color={statusTagColor(report.status === 'success' ? '已完成' : '失败')}>{report.status}</Tag>
        </Space>
        <Descriptions column={{ xs: 1, sm: 3 }} size="small" style={{ marginTop: 18 }}>
          <Descriptions.Item label="研究任务">#{report.research_task_id}</Descriptions.Item>
          <Descriptions.Item label="来源数">{report.source_count}</Descriptions.Item>
          <Descriptions.Item label="生成时间">{report.created_at.replace('T', ' ').slice(0, 19)}</Descriptions.Item>
        </Descriptions>
        <Divider />
        <Typography.Title level={4}>摘要</Typography.Title>
        <Typography.Paragraph className="pre-wrap">{report.summary}</Typography.Paragraph>
      </Card>

      <Card title="报告正文">
        <Typography.Paragraph className="pre-wrap">{report.content}</Typography.Paragraph>
      </Card>

      <Card title="章节与结论">
        <Typography.Title level={5}>章节</Typography.Title>
        <pre className="pre-wrap">{pretty(report.sections)}</pre>
        <Typography.Title level={5}>结论</Typography.Title>
        <pre className="pre-wrap">{pretty(report.conclusions)}</pre>
      </Card>

      <Card title={`引用来源（${references.length}）`}>
        <List
          dataSource={references}
          locale={{ emptyText: '暂无可用引用；报告内容中的结论需按引用缺失规则谨慎使用。' }}
          renderItem={(reference) => (
            <List.Item>
              <List.Item.Meta
                title={reference.source_url ? <a href={reference.source_url} target="_blank" rel="noreferrer">{reference.source_title || reference.source_url}</a> : reference.source_title || '未命名来源'}
                description={(
                  <Space wrap>
                    {reference.search_provider && <Tag>{reference.search_provider}</Tag>}
                    {reference.source_type && <Tag>{reference.source_type}</Tag>}
                    {reference.evidence_summary && <Typography.Text type="secondary">{reference.evidence_summary}</Typography.Text>}
                  </Space>
                )}
              />
            </List.Item>
          )}
        />
      </Card>
    </Space>
  )
}
