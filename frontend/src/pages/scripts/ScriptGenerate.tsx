import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Radio, Select, Space, Table, Tooltip, message } from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, ScriptOut, TopicOut } from '@/types'

interface BuiltinPrompt {
  task_type: '选题生成' | '脚本生成'
  content: string
}

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
  const [builtinPrompts, setBuiltinPrompts] = useState<BuiltinPrompt[]>([])
  const [loading, setLoading] = useState(false)
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false)
  const [saveTemplateName, setSaveTemplateName] = useState('自定义脚本提示词')
  const [result, setResult] = useState<GenerateResult | null>(null)

  useEffect(() => {
    void http
      .get<PageResult<TopicOut>>('/topics', { params: { status: '已选定', page_size: 200 } })
      .then((r) => setTopics(r.data.items))
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    void http
      .get<BuiltinPrompt[]>('/prompt-templates/builtin')
      .then((r) => {
        const prompts = r.data.filter((item) => item.task_type === '脚本生成')
        setBuiltinPrompts(prompts)
        if (prompts[0]) form.setFieldValue('builtin_prompt_type', prompts[0].task_type)
      })
    const topicId = search.get('topic_id')
    if (topicId) form.setFieldValue('topic_id', Number(topicId))
  }, [search, form])

  const run = async () => {
    const values = await form.validateFields()
    const payload = {
      topic_id: values.topic_id,
      style: values.style,
      content_elements: values.content_elements || [],
      version_count: values.version_count,
      material_ids: values.material_ids || [],
      ...(values.prompt_mode === 'custom' ? { prompt_content: values.prompt_content } : {}),
    }
    setLoading(true)
    try {
      const { data } = await http.post<GenerateResult>('/scripts/generate', payload)
      setResult(data)
      message.success(`已生成 ${data.generated} 版脚本`)
    } finally {
      setLoading(false)
    }
  }

  const promptMode = Form.useWatch('prompt_mode', form) || 'builtin'
  const promptContent = Form.useWatch('prompt_content', form) || ''
  const builtinPromptType = Form.useWatch('builtin_prompt_type', form)
  const selectedBuiltin = builtinPrompts.find((prompt) => prompt.task_type === builtinPromptType)

  const openSaveTemplate = () => {
    if (!promptContent.trim()) {
      message.warning('请先输入自定义提示词')
      return
    }
    setSaveTemplateName('自定义脚本提示词')
    setSaveTemplateOpen(true)
  }

  const saveTemplate = async () => {
    const name = saveTemplateName.trim()
    if (!name) {
      message.warning('请输入模板名称')
      return
    }
    await http.post('/prompt-templates', { task_type: '脚本生成', name, content: promptContent.trim() })
    message.success('已保存到模板库')
    setSaveTemplateOpen(false)
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
          initialValues={{ version_count: 3, content_elements: [], prompt_mode: 'builtin', builtin_prompt_type: '脚本生成' }}
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
          <Form.Item name="prompt_mode" label="提示词使用方式">
            <Radio.Group options={[{ label: '模板库', value: 'builtin' }, { label: '自定义', value: 'custom' }]} />
          </Form.Item>
          {promptMode === 'builtin' ? (
            <Form.Item name="builtin_prompt_type" label="模板库">
              <Tooltip title={selectedBuiltin?.content} placement="topLeft">
                <Select
                  loading={!builtinPrompts.length}
                  placeholder="选择模板（默认即可）"
                  options={builtinPrompts.map((prompt) => ({
                    value: prompt.task_type,
                    label: `${prompt.task_type}：${prompt.content}`,
                  }))}
                  optionRender={(option) => (
                    <div style={{ whiteSpace: 'normal', lineHeight: 1.5 }}>{option.data.label}</div>
                  )}
                />
              </Tooltip>
            </Form.Item>
          ) : (
            <>
              <Form.Item name="prompt_content" label="自定义提示词" rules={[{ required: true, whitespace: true, message: '请输入自定义提示词' }]}>
                <Input.TextArea rows={6} placeholder="输入自定义提示词，将替代模板库内容生效" showCount />
              </Form.Item>
              <Form.Item>
                <Button disabled={!promptContent.trim()} onClick={openSaveTemplate}>保存为模板</Button>
              </Form.Item>
            </>
          )}
          <Button type="primary" loading={loading} onClick={run}>
            开始生成
          </Button>
        </Form>
      </Card>

      <Modal open={saveTemplateOpen} title="保存为模板" onCancel={() => setSaveTemplateOpen(false)} onOk={() => void saveTemplate()}>
        <Form layout="vertical">
          <Form.Item label="模板名称" required>
            <Input value={saveTemplateName} maxLength={100} onChange={(event) => setSaveTemplateName(event.target.value)} />
          </Form.Item>
        </Form>
      </Modal>

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
