import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Select,
  Space,
  Statistic,
  Table,
  Tooltip,
  message,
} from 'antd'
import { http } from '@/api/client'
import { useMetaStore } from '@/store/meta'
import type { MaterialOut, PageResult, TopicGenerateResult } from '@/types'

interface BusinessDirection {
  id: number
  name: string
}

interface SpecialtyItem {
  id: number
  business_direction_id: number
  name: string
  enumValue: string
}

interface BuiltinPrompt {
  task_type: '选题生成' | '脚本生成'
  content: string
}

/** 静态兜底：后端方向表接口未就绪时使用（待后端接口替换） */
const STATIC_BUSINESS_DIRECTIONS: BusinessDirection[] = [
  { id: 1, name: '制造业获客' },
  { id: 2, name: '服务业增长' },
  { id: 3, name: '招商加盟' },
]

const STATIC_SPECIALTIES: SpecialtyItem[] = [
  { id: 11, business_direction_id: 1, name: '短视频获客', enumValue: '市场营销' },
  { id: 12, business_direction_id: 1, name: '直播获客', enumValue: '企业经营' },
  { id: 13, business_direction_id: 1, name: '展会获客', enumValue: '市场营销' },
  { id: 21, business_direction_id: 2, name: '线上增长', enumValue: '自媒体平台流量与规划算法逻辑' },
  { id: 22, business_direction_id: 2, name: '私域运营', enumValue: '用户需求与痛点' },
  { id: 31, business_direction_id: 3, name: '招商获客', enumValue: '市场营销' },
]

let localIdSeq = 1000

export default function TopicGenerate() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const options = useMetaStore((s) => s.options)
  const specialtyEnums = options('specialty')
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [builtinPrompts, setBuiltinPrompts] = useState<BuiltinPrompt[]>([])
  const [loading, setLoading] = useState(false)
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false)
  const [saveTemplateName, setSaveTemplateName] = useState('自定义选题提示词')
  const [result, setResult] = useState<TopicGenerateResult | null>(null)
  const [businessDirections, setBusinessDirections] = useState<BusinessDirection[]>(STATIC_BUSINESS_DIRECTIONS)
  const [specialties, setSpecialties] = useState<SpecialtyItem[]>(STATIC_SPECIALTIES)
  const [directionsFromApi, setDirectionsFromApi] = useState(false)
  const [selectedBusinessId, setSelectedBusinessId] = useState<number | null>(null)
  const [addingBusiness, setAddingBusiness] = useState(false)
  const [newBusinessName, setNewBusinessName] = useState('')
  const [addingSpecialty, setAddingSpecialty] = useState(false)
  const [newSpecialtyName, setNewSpecialtyName] = useState('')

  useEffect(() => {
    void http
      .get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } })
      .then((r) => setMaterials(r.data.items))
    void http
      .get<BuiltinPrompt[]>('/prompt-templates/builtin')
      .then((r) => {
        const prompts = r.data.filter((item) => item.task_type === '选题生成')
        setBuiltinPrompts(prompts)
        if (prompts[0]) form.setFieldValue('builtin_prompt_type', prompts[0].task_type)
      })

    void (async () => {
      try {
        const { data } = await http.get<{
          business_directions?: BusinessDirection[]
          specialties?: SpecialtyItem[]
        }>('/directions')
        if (data.business_directions?.length) {
          setBusinessDirections(data.business_directions)
          setDirectionsFromApi(true)
        }
        if (data.specialties?.length) {
          setSpecialties(
            data.specialties.map((s) => {
              const staticMatch = STATIC_SPECIALTIES.find(
                (item) => item.business_direction_id === s.business_direction_id && item.name === s.name,
              )
              return {
                id: s.id,
                business_direction_id: s.business_direction_id,
                name: s.name,
                enumValue: s.enumValue || staticMatch?.enumValue || '市场营销',
              }
            }),
          )
        }
      } catch {
        setDirectionsFromApi(false)
      }
    })()
  }, [form])

  const specialtyOptions = useMemo(() => {
    if (!selectedBusinessId) return []
    const filtered = specialties.filter((s) => s.business_direction_id === selectedBusinessId)
    if (filtered.length > 0) {
      return filtered.map((s) => ({ label: s.name, value: s.enumValue }))
    }
    return specialtyEnums
  }, [selectedBusinessId, specialties, specialtyEnums])

  const onBusinessChange = (businessId: number) => {
    setSelectedBusinessId(businessId)
    const name = businessDirections.find((d) => d.id === businessId)?.name
    form.setFieldsValue({ direction: name, specialty: undefined })
  }

  const addBusinessDirection = async () => {
    const name = newBusinessName.trim()
    if (!name || name.length > 50) {
      message.warning('请输入 1-50 字符的业务方向名称')
      return
    }
    if (businessDirections.some((d) => d.name === name)) {
      message.error('该业务方向已存在')
      return
    }
    if (directionsFromApi) {
      try {
        const { data } = await http.post<BusinessDirection>('/directions/business', { name })
        setBusinessDirections((prev) => [...prev, data])
        setSelectedBusinessId(data.id)
        form.setFieldsValue({ direction: data.name, specialty: undefined })
        setAddingBusiness(false)
        setNewBusinessName('')
        return
      } catch {
        message.warning('方向接口暂不可用，已本地添加（待后端接口）')
      }
    }
    const item = { id: ++localIdSeq, name }
    setBusinessDirections((prev) => [...prev, item])
    setSelectedBusinessId(item.id)
    form.setFieldsValue({ direction: item.name, specialty: undefined })
    setAddingBusiness(false)
    setNewBusinessName('')
  }

  const addSpecialty = async () => {
    if (!selectedBusinessId) return
    const name = newSpecialtyName.trim()
    if (!name || name.length > 50) {
      message.warning('请输入 1-50 字符的专业方向名称')
      return
    }
    const dup = specialties.some(
      (s) => s.business_direction_id === selectedBusinessId && s.name === name,
    )
    if (dup) {
      message.error('该专业方向已存在')
      return
    }
    const defaultEnum = specialtyEnums[0]?.value || '市场营销'
    if (directionsFromApi) {
      try {
        const { data } = await http.post<SpecialtyItem>('/directions/specialties', {
          business_direction_id: selectedBusinessId,
          name,
        })
        const item: SpecialtyItem = {
          id: data.id,
          business_direction_id: data.business_direction_id,
          name: data.name,
          enumValue: data.enumValue || defaultEnum,
        }
        setSpecialties((prev) => [...prev, item])
        form.setFieldValue('specialty', item.enumValue)
        setAddingSpecialty(false)
        setNewSpecialtyName('')
        return
      } catch {
        message.warning('专业方向接口暂不可用，已本地添加（待后端接口）')
      }
    }
    const item: SpecialtyItem = {
      id: ++localIdSeq,
      business_direction_id: selectedBusinessId,
      name,
      enumValue: defaultEnum,
    }
    setSpecialties((prev) => [...prev, item])
    form.setFieldValue('specialty', item.enumValue)
    setAddingSpecialty(false)
    setNewSpecialtyName('')
  }

  const run = async () => {
    const values = await form.validateFields()
    const payload = {
      direction: values.direction,
      specialty: values.specialty,
      material_ids: values.material_ids || [],
      count: values.count,
      ...(values.prompt_mode === 'custom' ? { prompt_content: values.prompt_content } : {}),
    }
    setLoading(true)
    try {
      const { data } = await http.post<TopicGenerateResult>('/topics/generate', payload)
      setResult(data)
      message.success(`批次 ${data.batch_no}：入库 ${data.saved} 条，去重 ${data.deduped} 条`)
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
    setSaveTemplateName('自定义选题提示词')
    setSaveTemplateOpen(true)
  }

  const saveTemplate = async () => {
    const name = saveTemplateName.trim()
    if (!name) {
      message.warning('请输入模板名称')
      return
    }
    await http.post('/prompt-templates', { task_type: '选题生成', name, content: promptContent.trim() })
    message.success('已保存到模板库')
    setSaveTemplateOpen(false)
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
        <Form
          form={form}
          layout="vertical"
          initialValues={{ count: 10, prompt_mode: 'builtin', builtin_prompt_type: '选题生成' }}
          style={{ maxWidth: 720 }}
        >
          <Form.Item name="direction" hidden rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item label="业务方向" required>
            <Select
              showSearch
              placeholder="请选择或新增业务方向"
              value={selectedBusinessId ?? undefined}
              onChange={onBusinessChange}
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={businessDirections.map((d) => ({ label: d.name, value: d.id }))}
              dropdownRender={(menu) => (
                <>
                  {menu}
                  <Divider style={{ margin: '8px 0' }} />
                  {addingBusiness ? (
                    <Space style={{ padding: '0 8px 4px' }}>
                      <Input
                        size="small"
                        placeholder="新业务方向名称"
                        value={newBusinessName}
                        onChange={(e) => setNewBusinessName(e.target.value)}
                        onPressEnter={() => void addBusinessDirection()}
                      />
                      <Button type="link" size="small" onClick={() => void addBusinessDirection()}>
                        确定
                      </Button>
                      <Button type="link" size="small" onClick={() => setAddingBusiness(false)}>
                        取消
                      </Button>
                    </Space>
                  ) : (
                    <Button type="link" onClick={() => setAddingBusiness(true)}>
                      + 新增业务方向
                    </Button>
                  )}
                </>
              )}
            />
          </Form.Item>

          <Form.Item name="specialty" label="专业方向" rules={[{ required: true, message: '请选择专业方向' }]}>
            <Select
              showSearch
              disabled={!selectedBusinessId}
              placeholder={selectedBusinessId ? '请选择专业方向' : '请先选择业务方向'}
              options={specialtyOptions}
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              dropdownRender={(menu) => (
                <>
                  {menu}
                  {selectedBusinessId && (
                    <>
                      <Divider style={{ margin: '8px 0' }} />
                      {addingSpecialty ? (
                        <Space style={{ padding: '0 8px 4px' }}>
                          <Input
                            size="small"
                            placeholder="新专业方向名称"
                            value={newSpecialtyName}
                            onChange={(e) => setNewSpecialtyName(e.target.value)}
                            onPressEnter={() => void addSpecialty()}
                          />
                          <Button type="link" size="small" onClick={() => void addSpecialty()}>
                            确定
                          </Button>
                          <Button type="link" size="small" onClick={() => setAddingSpecialty(false)}>
                            取消
                          </Button>
                        </Space>
                      ) : (
                        <Button type="link" onClick={() => setAddingSpecialty(true)}>
                          + 新增专业方向
                        </Button>
                      )}
                    </>
                  )}
                </>
              )}
            />
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
