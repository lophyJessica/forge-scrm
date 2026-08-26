import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Form, Input, Select, Space, message } from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, ScriptOut, TopicOut } from '@/types'

export default function ScriptForm() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const options = useMetaStore((s) => s.options)
  const [topics, setTopics] = useState<TopicOut[]>([])
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void http
      .get<PageResult<TopicOut>>('/topics', { params: { page_size: 200 } })
      .then((r) => setTopics(r.data.items))
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    if (id) {
      void http.get<ScriptOut>(`/scripts/${id}`).then((r) => form.setFieldsValue(r.data))
    }
  }, [id, form])

  const submit = async () => {
    const values = await form.validateFields()
    if (!values.content || !values.content.trim()) {
      message.error('脚本正文不能为空')
      return
    }
    setSaving(true)
    try {
      if (isEdit) {
        await http.put(`/scripts/${id}`, values)
        message.success('已保存，版本号已递增')
        navigate(`/scripts/${id}`)
      } else {
        const { data } = await http.post<ScriptOut>('/scripts', values)
        message.success('已创建')
        navigate(`/scripts/${data.id}`)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title={isEdit ? '修改脚本' : '独立创建脚本'} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={
          isEdit
            ? '每次修改正文都会生成一个新版本并保留历史，可在「版本历史」中对比与回退。'
            : '独立创建时可不选来源选题（topic_id 允许为空），后续可在此页面补录关联。'
        }
      />
      <div style={{ width: '100%', maxWidth: 860 }}>
        <Form form={form} layout="vertical" style={{ width: '100%' }} initialValues={{ content_elements: [] }}>
        <Form.Item name="topic_id" label="来源选题（可选，可后补）">
          <Select
            allowClear
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
        <Form.Item name="material_refs" label="引用资料（可选）">
          <Select
            mode="multiple"
            allowClear
            options={materials.map((m) => ({ label: `#${m.id} ${m.title}`, value: m.id }))}
          />
        </Form.Item>
        <Form.Item
          name="content"
          label="脚本正文"
          rules={[{ required: true, message: '脚本正文不能为空' }]}
        >
          <Input.TextArea rows={14} />
        </Form.Item>
        {isEdit && (
          <Form.Item name="note" label="修改备注（写入版本历史）">
            <Input maxLength={200} placeholder="例如：调整开头钩子" />
          </Form.Item>
        )}
        <Space>
          <Button type="primary" loading={saving} onClick={submit}>
            保存
          </Button>
          <Button onClick={() => navigate(-1)}>取消</Button>
        </Space>
        </Form>
      </div>
    </Card>
  )
}
