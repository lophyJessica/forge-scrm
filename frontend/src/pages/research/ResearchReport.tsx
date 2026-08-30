import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Descriptions, Divider, Form, Input, InputNumber, List, Modal, Select, Skeleton, Space, Tag, Typography, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { http } from '@/api/client'
import { statusTagColor } from '@/theme'
import { useMetaStore } from '@/store/meta'
import type { MaterialClassOut, PromptTemplateOut, ResearchReferenceOut, ResearchReportOut, ScriptOut, TopicOut } from '@/types'

function pretty(value: Record<string, unknown> | null | undefined) {
  return value ? JSON.stringify(value, null, 2) : '—'
}

function isExternalUrl(value?: string | null) {
  if (!value) return false
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

function snapshotText(value?: string | null) {
  if (!value) return ''
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
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
  const navigate = useNavigate()
  const [report, setReport] = useState<ResearchReportOut | null>(null)
  const [references, setReferences] = useState<ResearchReferenceOut[]>([])
  const [loading, setLoading] = useState(true)
  const [materialForm] = Form.useForm()
  const [topicForm] = Form.useForm()
  const [scriptForm] = Form.useForm()
  const options = useMetaStore((state) => state.options)
  const [materialClasses, setMaterialClasses] = useState<MaterialClassOut[]>([])
  const [topicTemplates, setTopicTemplates] = useState<PromptTemplateOut[]>([])
  const [scriptTemplates, setScriptTemplates] = useState<PromptTemplateOut[]>([])
  const [topics, setTopics] = useState<TopicOut[]>([])
  const [materialModalOpen, setMaterialModalOpen] = useState(false)
  const [topicModalOpen, setTopicModalOpen] = useState(false)
  const [scriptModalOpen, setScriptModalOpen] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

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

  useEffect(() => {
    if (!report) return
    void Promise.all([
      http.get<MaterialClassOut[]>('/material-classes'),
      http.get<{ items: PromptTemplateOut[] }>('/prompt-templates', { params: { task_type: '选题生成', status: '启用', page_size: 200 } }),
      http.get<{ items: PromptTemplateOut[] }>('/prompt-templates', { params: { task_type: '脚本生成', status: '启用', page_size: 200 } }),
      http.get<{ items: TopicOut[] }>('/topics', { params: { status: '已选定', page_size: 200 } }),
    ]).then(([classes, topicPrompt, scriptPrompt, topicRows]) => {
      setMaterialClasses(classes.data)
      setTopicTemplates(topicPrompt.data.items)
      setScriptTemplates(scriptPrompt.data.items)
      setTopics(topicRows.data.items)
    })
  }, [report])

  const sections = report?.sections && typeof report.sections === 'object' ? Object.keys(report.sections) : []

  const materialize = async () => {
    if (!id) return
    const values = await materialForm.validateFields()
    setActionLoading(true)
    try {
      const [validFrom, validUntil] = values.materialValidRange || []
      const { data } = await http.post<{ material_ids: number[] }>(`/research-reports/${id}/materials`, {
        class_id: values.materialClassId,
        trust_level: values.materialTrustLevel,
        valid_from: validFrom?.format('YYYY-MM-DD'),
        valid_until: validUntil?.format('YYYY-MM-DD'),
        section_keys: values.materialSections || [],
      })
      message.success(`已生成 ${data.material_ids.length} 条资料`)
      setMaterialModalOpen(false)
      navigate(`/materials/${data.material_ids[0]}`)
    } finally {
      setActionLoading(false)
    }
  }

  const generateTopics = async () => {
    if (!id) return
    const values = await topicForm.validateFields()
    setActionLoading(true)
    try {
      await http.post(`/research-reports/${id}/topics`, {
        direction: values.topicDirection,
        specialty: values.topicSpecialty,
        count: values.topicCount,
        material_ids: values.topicMaterialIds || [],
        ...(values.topicPromptTemplateId ? { prompt_template_id: values.topicPromptTemplateId } : {}),
      })
      message.success('选题已生成')
      setTopicModalOpen(false)
      navigate('/topics')
    } finally {
      setActionLoading(false)
    }
  }

  const generateScripts = async () => {
    if (!id) return
    const values = await scriptForm.validateFields()
    setActionLoading(true)
    try {
      const { data } = await http.post<{ scripts: ScriptOut[] }>(`/research-reports/${id}/scripts`, {
        topic_id: values.scriptTopicId,
        style: values.scriptStyle,
        content_elements: values.scriptContentElements || [],
        version_count: values.scriptVersionCount,
        material_ids: values.scriptMaterialIds || [],
        ...(values.scriptPromptTemplateId ? { prompt_template_id: values.scriptPromptTemplateId } : {}),
      })
      message.success('脚本已生成')
      setScriptModalOpen(false)
      if (data.scripts?.[0]) navigate(`/scripts/${data.scripts[0].id}`)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <Card><Skeleton active /></Card>
  if (!report) return <Alert type="error" message="研究报告不存在或加载失败" />

  return (
    <Space direction="vertical" size={16} style={{ display: 'flex' }}>
      <Card>
        <Space align="center" wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/research/tasks')}>返回列表</Button>
          <Typography.Title level={3} style={{ margin: 0 }}>{report.title}</Typography.Title>
          {report.is_ai_product && <Tag color="purple">AI 生成</Tag>}
          <Tag color={statusTagColor(report.status === 'success' ? '已完成' : '失败')}>{report.status}</Tag>
        </Space>
        {report.status === 'success' && (
          <Space wrap size={8} style={{ marginTop: 16 }}>
            <Button type="primary" onClick={() => { materialForm.resetFields(); materialForm.setFieldsValue({ materialTrustLevel: '中' }); setMaterialModalOpen(true) }}>沉淀为资料</Button>
            <Button onClick={() => { topicForm.resetFields(); topicForm.setFieldsValue({ topicDirection: report.title.slice(0, 50), topicCount: 10 }); setTopicModalOpen(true) }}>生成选题</Button>
            <Button onClick={() => { scriptForm.resetFields(); scriptForm.setFieldsValue({ scriptVersionCount: 3 }); setScriptModalOpen(true) }}>生成脚本</Button>
          </Space>
        )}
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
                title={(() => {
                  const title = reference.source_title || reference.source_url || '未命名来源'
                  if (reference.source_kind === 'external_url' && isExternalUrl(reference.source_url)) {
                    return <a href={reference.source_url!} target="_blank" rel="noreferrer">{title}</a>
                  }
                  if (reference.collection_result_id != null) {
                    const href = `/collection/tasks?result_id=${reference.collection_result_id}`
                    return <a href={href} onClick={(event) => { event.preventDefault(); navigate(href) }}>采集结果 #{reference.collection_result_id} · {title}</a>
                  }
                  if (reference.material_id != null) {
                    const href = `/materials/${reference.material_id}`
                    return <a href={href} onClick={(event) => { event.preventDefault(); navigate(href) }}>资料 #{reference.material_id} · {title}</a>
                  }
                  return <Typography.Text>{title}</Typography.Text>
                })()}
                description={(
                  <Space direction="vertical" size={8} style={{ display: 'flex' }}>
                    <Space wrap>
                      {reference.search_provider && <Tag>{reference.search_provider}</Tag>}
                      {reference.source_type && <Tag>{reference.source_type}</Tag>}
                      {reference.evidence_summary && <Typography.Text type="secondary">{reference.evidence_summary}</Typography.Text>}
                    </Space>
                    {reference.source_snapshot && (
                      <details>
                        <summary>历史快照</summary>
                        <pre className="pre-wrap" style={{ margin: '8px 0 0' }}>{snapshotText(reference.source_snapshot)}</pre>
                      </details>
                    )}
                  </Space>
                )}
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal open={materialModalOpen} title="确认沉淀为资料" width={640} confirmLoading={actionLoading} onCancel={() => setMaterialModalOpen(false)} onOk={() => void materialize()} okText="确认沉淀" cancelText="取消">
        <Form form={materialForm} layout="vertical">
          <Form.Item name="materialClassId" label="目标分类" rules={[{ required: true, message: '请选择目标分类' }]}>
            <Select showSearch optionFilterProp="label" options={materialClasses.map((item) => ({ label: item.name, value: item.id }))} />
          </Form.Item>
          <Form.Item name="materialSections" label="沉淀范围">
            <Select mode="multiple" allowClear options={sections.map((key) => ({ label: key, value: key }))} placeholder="不选则沉淀报告全文" />
          </Form.Item>
          <Space size={16} align="start">
            <Form.Item name="materialTrustLevel" label="可信度" rules={[{ required: true }]}><Select options={options('trust_level')} /></Form.Item>
            <Form.Item name="materialValidRange" label="有效期" rules={[{ required: true, message: '请选择有效期' }]}><DatePicker.RangePicker /></Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal open={topicModalOpen} title="确认生成选题" width={640} confirmLoading={actionLoading} onCancel={() => setTopicModalOpen(false)} onOk={() => void generateTopics()} okText="确认生成" cancelText="取消">
        <Form form={topicForm} layout="vertical">
          <Form.Item name="topicDirection" label="业务方向" rules={[{ required: true, message: '请输入业务方向' }]}><Input maxLength={50} /></Form.Item>
          <Form.Item name="topicSpecialty" label="专业方向" rules={[{ required: true, message: '请选择专业方向' }]}><Select options={options('specialty')} /></Form.Item>
          <Form.Item name="topicCount" label="生成条数"><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name="topicMaterialIds" label="参考资料（可选）"><Select mode="multiple" allowClear placeholder="报告内容会自动作为上下文" /></Form.Item>
          <Form.Item name="topicPromptTemplateId" label="提示词模板（可选）"><Select allowClear showSearch optionFilterProp="label" options={topicTemplates.map((item) => ({ label: item.name, value: item.id }))} /></Form.Item>
        </Form>
      </Modal>

      <Modal open={scriptModalOpen} title="确认生成脚本" width={640} confirmLoading={actionLoading} onCancel={() => setScriptModalOpen(false)} onOk={() => void generateScripts()} okText="确认生成" cancelText="取消">
        <Form form={scriptForm} layout="vertical">
          <Form.Item name="scriptTopicId" label="关联选题" rules={[{ required: true, message: '请选择已选定选题' }]}><Select showSearch optionFilterProp="label" options={topics.map((item) => ({ label: `#${item.id} ${item.title}`, value: item.id }))} placeholder="优先关联已选定选题" /></Form.Item>
          <Form.Item name="scriptStyle" label="语言风格" rules={[{ required: true, message: '请选择语言风格' }]}><Select options={options('script_style')} /></Form.Item>
          <Form.Item name="scriptContentElements" label="内容要素"><Select mode="multiple" allowClear options={options('content_element')} /></Form.Item>
          <Form.Item name="scriptVersionCount" label="生成版数"><InputNumber min={2} max={3} /></Form.Item>
          <Form.Item name="scriptPromptTemplateId" label="提示词模板（可选）"><Select allowClear showSearch optionFilterProp="label" options={scriptTemplates.map((item) => ({ label: item.name, value: item.id }))} /></Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
