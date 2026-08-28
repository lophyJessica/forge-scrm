import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, DatePicker, Form, Input, Select, Space, message } from 'antd'
import dayjs from 'dayjs'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialClassOut, MaterialOut, TagOut } from '@/types'

export default function MaterialForm() {
  const { id } = useParams()
  const isEdit = !!id
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const options = useMetaStore((s) => s.options)
  const [classes, setClasses] = useState<MaterialClassOut[]>([])
  const [tags, setTags] = useState<TagOut[]>([])
  const [materialStatus, setMaterialStatus] = useState<string>()
  const [savingAction, setSavingAction] = useState<'draft' | 'review' | 'save'>()

  useEffect(() => {
    void http.get<MaterialClassOut[]>('/material-classes').then((r) => setClasses(r.data))
    void http.get<TagOut[]>('/tags').then((r) => setTags(r.data))
    if (isEdit) {
      void http.get<MaterialOut>(`/materials/${id}`).then(({ data }) => {
        setMaterialStatus(data.status)
        form.setFieldsValue({
          ...data,
          valid_range: [dayjs(data.valid_from), dayjs(data.valid_until)],
        })
      })
    }
  }, [id, isEdit, form])

  const submit = async (action: 'draft' | 'review' | 'save') => {
    const values = await form.validateFields()
    const validRange = values.valid_range
    const payload = {
      title: values.title,
      content: values.content,
      class_id: values.class_id,
      source_type: values.source_type,
      source_url: values.source_url || null,
      trust_level: values.trust_level,
      tags: values.tags || [],
      ...(validRange?.length === 2
        ? {
            valid_from: validRange[0].format('YYYY-MM-DD'),
            valid_until: validRange[1].format('YYYY-MM-DD'),
          }
        : {}),
    }
    setSavingAction(action)
    try {
      if (isEdit) {
        await http.put(`/materials/${id}`, payload)
        if (action === 'review' && materialStatus === '草稿') {
          await http.post(`/materials/${id}/submit`)
        }
      } else {
        await http.post('/materials', {
          ...payload,
          submit_for_review: action === 'review',
        })
      }
      message.success(action === 'draft' ? '草稿已保存' : action === 'review' ? '已提交审核' : '保存成功')
      navigate('/materials')
    } finally {
      setSavingAction(undefined)
    }
  }

  const canChooseReviewFlow = !isEdit || materialStatus === '草稿'

  return (
    <Card title={isEdit ? `编辑资料 #${id}` : '新建资料'}>
      <div style={{ maxWidth: 720 }}>
        <Form form={form} layout="vertical">
        <Form.Item name="title" label="标题" rules={[{ required: true, message: '标题必填' }]}>
          <Input maxLength={200} showCount />
        </Form.Item>
        <Form.Item name="content" label="正文" rules={[{ required: true, message: '正文必填' }]}>
          <Input.TextArea rows={10} />
        </Form.Item>
        <Space size={16} align="start" wrap>
          <Form.Item name="class_id" label="分类" rules={[{ required: true }]} style={{ width: 200 }}>
            <Select options={classes.map((c) => ({ label: c.name, value: c.id }))} />
          </Form.Item>
          <Form.Item name="source_type" label="来源类型" rules={[{ required: true }]} style={{ width: 160 }}>
            <Select options={options('source_type')} />
          </Form.Item>
          <Form.Item name="trust_level" label="可信度" rules={[{ required: true }]} style={{ width: 120 }}>
            <Select options={options('trust_level')} />
          </Form.Item>
        </Space>
        <Form.Item name="source_url" label="来源链接">
          <Input maxLength={500} placeholder="可选" />
        </Form.Item>
        <Form.Item name="valid_range" label="有效期（可选）">
          <DatePicker.RangePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="tags" label="标签（可自由创建，回车新增）">
          <Select
            mode="tags"
            tokenSeparators={[',', '|']}
            options={tags.map((t) => ({ label: t.name, value: t.name }))}
          />
        </Form.Item>
        <div className="form-actions">
          <Button onClick={() => navigate('/materials')}>取消</Button>
          {canChooseReviewFlow ? (
            <>
              <Button disabled={!!savingAction} loading={savingAction === 'draft'} onClick={() => void submit('draft')}>
                保存草稿
              </Button>
              <Button type="primary" disabled={!!savingAction} loading={savingAction === 'review'} onClick={() => void submit('review')}>
                提交审核
              </Button>
            </>
          ) : (
            <Button type="primary" disabled={!!savingAction} loading={savingAction === 'save'} onClick={() => void submit('save')}>
              保存修改
            </Button>
          )}
        </div>
        </Form>
      </div>
    </Card>
  )
}
