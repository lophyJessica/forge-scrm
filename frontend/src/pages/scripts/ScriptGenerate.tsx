import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, Form, InputNumber, Select, Space, Table, message } from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, PromptTemplateOut, ScriptOut, TopicOut } from '@/types'

interface GenerateResult {
  topic_id: number
  generated: number
  scripts: ScriptOut[]
  ai_raw_archive: string
}

export default function ScriptGenerate() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const options = useMetaStore((s) => s.options)
  const [topics, setTopics] = useState<TopicOut[]>([])
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [templates, setTemplates] = useState<PromptTemplateOut[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GenerateResult | null>(null)

  useEffect(() => {
    void http
      .get<PageResult<TopicOut>>('/topics', { params: { status: '已选定', page_size: 200 } })
      .then((r) => setTopics(r.data.items))
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    void http
      .get<PageResult<PromptTemplateOut>>('/prompt-templates', {
        params: { task_type: '脚本生成', page_size: 100 },
      })
      .then((r) => setTemplates(r.data.items))
    const topicId = search.get('topic_id')
    if (topicId) form.setFieldValue('topic_id', Number(topicId))
  }, [search, form])

  const run = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const { data } = await http.post<GenerateResult>('/scripts/generate', values)
      setResult(data)
      message.success(`已生成 ${data.generated} 版脚本`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Card title="基于选题生成脚本">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="一期为同步生成：点击后请等待返回。每个选题生成 2-3 版脚本，生成后选题状态自动流转为「已生成脚本」。"
        />
        <Form
          form={form}
          layout="vertical"
          style={{ maxWidth: 720 }}
          initialValues={{ version_count: 3, content_elements: [] }}
        >
          <Form.Item name="topic_id" label="来源选题（仅「已选定」）" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={topics.map((t) => ({ label: `#${t.id} ${t.title}`, value: t.id }))}
            />
          </Form.Item>
          <Form.Item name="style" label="语言风格" rules={[{ required: true }]}>
            <Select options={options('script_style')} />
          </Form.Item>
          <Form.Item name="content_elements" label="内容要素">
            <Select mode="multiple" allowClear options={options('content_element')} />
          </Form.Item>
          <Form.Item name="version_count" label="生成版数（2-3）">
            <InputNumber min={2} max={3} />
          </Form.Item>
          <Form.Item name="material_ids" label="参考资料（可选，仅「已生效」）">
            <Select
              mode="multiple"
              allowClear
              options={materials.map((m) => ({ label: `#${m.id} ${m.title}`, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="prompt_template_id" label="提示词模板（可选）">
            <Select allowClear options={templates.map((t) => ({ label: `${t.name} v${t.version}`, value: t.id }))} />
          </Form.Item>
          <Button type="primary" loading={loading} onClick={run}>
            开始生成
          </Button>
        </Form>
      </Card>

      {result && (
        <Card title={`生成结果（${result.generated} 版）`}>
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={result.scripts}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '正文摘要', dataIndex: 'content', render: (v: string) => v.slice(0, 80) },
              { title: '版本', dataIndex: 'current_version', width: 80, render: (v) => `v${v}` },
              { title: '状态', dataIndex: 'status', width: 90 },
              {
                title: '操作',
                width: 100,
                render: (_, r) => (
                  <Button size="small" onClick={() => navigate(`/scripts/${r.id}`)}>
                    查看
                  </Button>
                ),
              },
            ]}
          />
          <p style={{ marginTop: 12, color: '#888' }}>AI 原始响应留档：{result.ai_raw_archive}</p>
        </Card>
      )}
    </Space>
  )
}
