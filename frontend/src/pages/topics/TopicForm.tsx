import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Form, Input, Select, Space, message } from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, TopicOut } from '@/types'

export default function TopicForm() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const options = useMetaStore((s) => s.options)
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    if (id) {
      void http.get<TopicOut>(`/topics/${id}`).then((r) => form.setFieldsValue(r.data))
    }
  }, [id, form])

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (isEdit) {
        await http.put(`/topics/${id}`, values)
        message.success('已保存')
        navigate(`/topics/${id}`)
      } else {
        const { data } = await http.post<TopicOut>('/topics', values)
        message.success('已创建')
        navigate(`/topics/${data.id}`)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title={isEdit ? '修改选题' : '手动新增选题'}>
      <Form form={form} layout="vertical" style={{ maxWidth: 800 }} initialValues={{ material_ids: [] }}>
        <Form.Item name="title" label="选题标题" rules={[{ required: true }]}>
          <Input maxLength={200} showCount />
        </Form.Item>
        <Form.Item name="direction" label="业务方向" rules={[{ required: true }]}>
          <Input maxLength={50} />
        </Form.Item>
        <Form.Item name="specialty" label="专业方向" rules={[{ required: true }]}>
          <Select options={options('specialty')} />
        </Form.Item>
        <Form.Item name="customer_scenario" label="客户场景" rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="user_perspective" label="用户视角" rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="business_direction" label="业务导向" rules={[{ required: true }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="core_angle" label="核心角度" rules={[{ required: true }]}>
          <Input.TextArea rows={3} maxLength={500} showCount />
        </Form.Item>
        <Form.Item name="topic_principle" label="选题原则" rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="topic_angle" label="选题角度" rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="material_ids" label="关联资料（仅「已生效」）">
          <Select
            mode="multiple"
            allowClear
            options={materials.map((m) => ({ label: `#${m.id} ${m.title}`, value: m.id }))}
          />
        </Form.Item>
        <Space>
          <Button type="primary" loading={saving} onClick={submit}>
            保存
          </Button>
          <Button onClick={() => navigate(-1)}>取消</Button>
        </Space>
      </Form>
    </Card>
  )
}
