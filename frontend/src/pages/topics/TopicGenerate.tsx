import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Form, InputNumber, Input, Select, Space, Statistic, Table, message } from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, PromptTemplateOut, TopicGenerateResult } from '@/types'

export default function TopicGenerate() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const options = useMetaStore((s) => s.options)
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [templates, setTemplates] = useState<PromptTemplateOut[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TopicGenerateResult | null>(null)

  useEffect(() => {
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    void http
      .get<PageResult<PromptTemplateOut>>('/prompt-templates', {
        params: { task_type: '选题生成', page_size: 100 },
      })
      .then((r) => setTemplates(r.data.items))
  }, [])

  const run = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const { data } = await http.post<TopicGenerateResult>('/topics/generate', values)
      setResult(data)
      message.success(`批次 ${data.batch_no}：入库 ${data.saved} 条，去重 ${data.deduped} 条`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Card title="批量生成选题">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="一期为同步生成：点击后请等待返回，不做后台队列。每个方向默认生成 10 条，完全重复的标题会跨批次自动去重。"
        />
        <Form form={form} layout="vertical" initialValues={{ count: 10 }} style={{ maxWidth: 720 }}>
          <Form.Item name="direction" label="业务方向" rules={[{ required: true }]}>
            <Input placeholder="例如：制造业获客" maxLength={50} />
          </Form.Item>
          <Form.Item name="specialty" label="专业方向" rules={[{ required: true }]}>
            <Select options={options('specialty')} />
          </Form.Item>
          <Form.Item name="count" label="生成条数（上限 10）">
            <InputNumber min={1} max={10} />
          </Form.Item>
          <Form.Item name="material_ids" label="参考资料（仅可选「已生效」资料）">
            <Select
              mode="multiple"
              allowClear
              placeholder="可不选"
              options={materials.map((m) => ({ label: `#${m.id} ${m.title}`, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="prompt_template_id" label="提示词模板（可选，不选用内置模板）">
            <Select
              allowClear
              options={templates.map((t) => ({ label: `${t.name} v${t.version}`, value: t.id }))}
            />
          </Form.Item>
          <Button type="primary" loading={loading} onClick={run}>
            开始生成
          </Button>
        </Form>
      </Card>

      {result && (
        <Card
          title={`生成结果 · 批次 ${result.batch_no}`}
          extra={
            <Button onClick={() => navigate(`/topics?batch_no=${result.batch_no}`)}>
              去列表筛选
            </Button>
          }
        >
          <Space size={40} style={{ marginBottom: 16 }}>
            <Statistic title="AI 返回" value={result.generated} />
            <Statistic title="重复去重" value={result.deduped} />
            <Statistic title="入库" value={result.saved} />
          </Space>
          <Table
            rowKey="id"
            size="small"
            dataSource={result.topics}
            pagination={false}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '标题', dataIndex: 'title' },
              { title: '核心角度', dataIndex: 'core_angle' },
              { title: '状态', dataIndex: 'status', width: 100 },
            ]}
          />
          <p style={{ marginTop: 12, color: '#888' }}>AI 原始响应留档：{result.ai_raw_archive}</p>
        </Card>
      )}
    </Space>
  )
}
