import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Divider,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Tag,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { http } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { PERM, useMetaStore } from '@/store/meta'
import { statusTagColor } from '@/theme'
import type { AnalysisResultOut, AnalysisTaskOut, MaterialClassOut } from '@/types'

export default function AnalysisTaskDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const can = useAuthStore((s) => s.can)
  const options = useMetaStore((s) => s.options)
  const [matForm] = Form.useForm()
  const [topicForm] = Form.useForm()
  const [task, setTask] = useState<AnalysisTaskOut | null>(null)
  const [classes, setClasses] = useState<MaterialClassOut[]>([])
  const [raw, setRaw] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [matTarget, setMatTarget] = useState<AnalysisResultOut | null>(null)
  const [topicTarget, setTopicTarget] = useState<AnalysisResultOut | null>(null)

  const load = useCallback(async () => {
    const { data } = await http.get<AnalysisTaskOut>(`/analysis-tasks/${id}`)
    setTask(data)
  }, [id])

  useEffect(() => {
    void load()
    void http.get<MaterialClassOut[]>('/material-classes').then((r) => setClasses(r.data))
  }, [load])

  if (!task) return <Card loading />

  const execute = async () => {
    setRunning(true)
    try {
      // D-T1：同步执行；失败时后端返回 400，错误详情由 http 拦截器统一提示
      await http.post<AnalysisTaskOut>(`/analysis-tasks/${id}/execute`)
      message.success('执行完成，结果待人工审核')
    } finally {
      setRunning(false)
      void load()
    }
  }

  const review = async (approved: boolean) => {
    await http.post(`/analysis-tasks/${id}/review`, { approved })
    message.success(approved ? '已确认' : '已驳回')
    void load()
  }

  const showRaw = async () => {
    const { data } = await http.get(`/analysis-tasks/${id}/ai-raw`)
    setRaw(typeof data === 'string' ? data : JSON.stringify(data, null, 2))
  }

  const openMaterial = (result: AnalysisResultOut) => {
    const candidates = result.result_content.material_candidates || []
    matForm.setFieldsValue({
      materials: candidates.length
        ? candidates.map((c) => ({
            title: c.title,
            content: c.content,
            class_id: classes[0]?.id,
            source_type: '报告',
            trust_level: '中',
            valid: [dayjs(), dayjs().add(1, 'year')],
            tags: [],
          }))
        : [{ class_id: classes[0]?.id, source_type: '报告', trust_level: '中', valid: [dayjs(), dayjs().add(1, 'year')], tags: [] }],
    })
    setMatTarget(result)
  }

  const submitMaterial = async () => {
    const values = await matForm.validateFields()
    const materials = values.materials.map((m: Record<string, any>) => ({
      title: m.title,
      content: m.content,
      class_id: m.class_id,
      source_type: m.source_type,
      trust_level: m.trust_level,
      valid_from: m.valid[0].format('YYYY-MM-DD'),
      valid_until: m.valid[1].format('YYYY-MM-DD'),
      tags: m.tags || [],
    }))
    await http.post(`/analysis-results/${matTarget!.id}/writeback-material`, { materials })
    message.success('已回写资料库（产物为「待审核」，需按流程审核）')
    setMatTarget(null)
    void load()
  }

  const openTopic = (result: AnalysisResultOut) => {
    const candidates = result.result_content.topic_candidates || []
    topicForm.setFieldsValue({
      topics: candidates.length
        ? candidates.map((c) => ({ title: c.title, core_angle: c.core_angle }))
        : [{}],
    })
    setTopicTarget(result)
  }

  const submitTopic = async () => {
    const values = await topicForm.validateFields()
    await http.post(`/analysis-results/${topicTarget!.id}/writeback-topic`, { topics: values.topics })
    message.success('已反哺选题库（产物为「待筛选」，需人工筛选）')
    setTopicTarget(null)
    void load()
  }

  return (
    <Card
      title={`分析任务 #${task.id}：${task.name || '未命名'}`}
      extra={
        <Space wrap>
          <Button onClick={() => navigate('/analysis/tasks')}>返回列表</Button>
          {task.has_ai_raw_response && <Button onClick={showRaw}>AI 原始响应</Button>}
          {['待执行', '失败'].includes(task.status) && can(PERM.分析任务执行) && (
            <Button type="primary" loading={running} onClick={execute}>
              {task.status === '失败' ? '重新执行' : '执行'}
            </Button>
          )}
          {task.status === '待审核' && can(PERM.分析结果审核) && (
            <>
              <Button type="primary" onClick={() => review(true)}>
                确认结果
              </Button>
              <Button
                danger
                onClick={() => Modal.confirm({
                  title: '确认驳回？',
                  content: '驳回后本次分析结果将不再用于回写或反哺。',
                  okText: '确认驳回',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => review(false),
                })}
              >
                驳回
              </Button>
            </>
          )}
        </Space>
      }
    >
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="任务类型">{task.type}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusTagColor(task.status)}>{task.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="重试次数">{task.retry_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{task.created_at}</Descriptions.Item>
        <Descriptions.Item label="输入原始数据" span={2}>
          {task.raw_data_ids.map((r) => (
            <Tag key={r}>#{r}</Tag>
          ))}
        </Descriptions.Item>
        <Descriptions.Item label="提示词版本快照" span={2}>
          <pre className="pre-wrap" style={{ maxHeight: 160, overflow: 'auto', marginBottom: 0 }}>
            {JSON.stringify(task.prompt_version_snapshot, null, 2)}
          </pre>
        </Descriptions.Item>
        <Descriptions.Item label="资料上下文快照" span={2}>
          <pre className="pre-wrap" style={{ maxHeight: 160, overflow: 'auto', marginBottom: 0 }}>
            {JSON.stringify(task.material_context_snapshot, null, 2)}
          </pre>
        </Descriptions.Item>
      </Descriptions>

      {task.error_message && (
        <Alert type="error" showIcon style={{ marginTop: 16 }} message={`执行失败：${task.error_message}`} />
      )}

      <Divider orientation="left">分析结果</Divider>
      {task.status !== '已确认' && task.results.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="分析结果需人工确认后，才能回写资料库或反哺选题库。"
        />
      )}
      <List
        dataSource={task.results}
        locale={{ emptyText: '暂无结果，请先执行任务' }}
        renderItem={(r) => (
          <Card type="inner" key={r.id} style={{ marginBottom: 12 }} title={`结果 #${r.id}`}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="效果">{r.result_content.effect || '—'}</Descriptions.Item>
              <Descriptions.Item label="结论">{r.result_content.conclusion || '—'}</Descriptions.Item>
              <Descriptions.Item label="建议">
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {(r.result_content.suggestions || []).map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </Descriptions.Item>
              <Descriptions.Item label="依据">{r.result_content.evidence || '—'}</Descriptions.Item>
              <Descriptions.Item label="回写资料库">
                <Tag color={r.writeback_material_status === '已回写' ? 'green' : 'default'}>
                  {r.writeback_material_status}
                </Tag>
                {r.material_ids.map((m) => (
                  <Tag key={m}>资料 #{m}</Tag>
                ))}
              </Descriptions.Item>
              <Descriptions.Item label="反哺选题库">
                <Tag color={r.writeback_topic_status === '已反哺' ? 'green' : 'default'}>
                  {r.writeback_topic_status}
                </Tag>
                {r.topic_ids.map((t) => (
                  <Tag key={t}>选题 #{t}</Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>
            {task.status === '已确认' && can(PERM.回写反哺) && (
              <Space style={{ marginTop: 8 }}>
                <Button
                  type="primary"
                  disabled={r.writeback_material_status === '已回写'}
                  onClick={() => openMaterial(r)}
                >
                  回写资料库
                </Button>
                <Button disabled={r.writeback_topic_status === '已反哺'} onClick={() => openTopic(r)}>
                  反哺选题库
                </Button>
              </Space>
            )}
          </Card>
        )}
      />

      <Modal open={!!matTarget} title="回写资料库" width={720} onCancel={() => setMatTarget(null)} onOk={submitMaterial} okText="确认回写" cancelText="取消">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="回写产物标记为 AI 产物且状态为「待审核」，必须经人工审核后才生效。"
        />
        <Form form={matForm} layout="vertical">
          <Form.List name="materials">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card key={field.key} size="small" style={{ marginBottom: 12 }} extra={<a onClick={() => remove(field.name)}>删除</a>}>
                    <Form.Item name={[field.name, 'title']} label="标题" rules={[{ required: true }]}>
                      <Input maxLength={200} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'content']} label="内容" rules={[{ required: true }]}>
                      <Input.TextArea rows={4} />
                    </Form.Item>
                    <Space align="start" wrap>
                      <Form.Item name={[field.name, 'class_id']} label="分类" rules={[{ required: true }]}>
                        <Select style={{ width: 180 }} options={classes.map((c) => ({ label: c.name, value: c.id }))} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'source_type']} label="来源类型" rules={[{ required: true }]}>
                        <Select style={{ width: 140 }} options={options('source_type')} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'trust_level']} label="可信度" rules={[{ required: true }]}>
                        <Select style={{ width: 100 }} options={options('trust_level')} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'valid']} label="有效期" rules={[{ required: true }]}>
                        <DatePicker.RangePicker />
                      </Form.Item>
                      <Form.Item name={[field.name, 'tags']} label="标签">
                        <Select mode="tags" style={{ width: 200 }} />
                      </Form.Item>
                    </Space>
                  </Card>
                ))}
                <Button onClick={() => add({ class_id: classes[0]?.id, source_type: '报告', trust_level: '中' })}>
                  添加一条
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal open={!!topicTarget} title="反哺选题库" width={720} onCancel={() => setTopicTarget(null)} onOk={submitTopic} okText="确认反哺" cancelText="取消">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="反哺产物状态为「待筛选」，需在选题库中人工筛选后才能使用。"
        />
        <Form form={topicForm} layout="vertical">
          <Form.List name="topics">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card key={field.key} size="small" style={{ marginBottom: 12 }} extra={<a onClick={() => remove(field.name)}>删除</a>}>
                    <Form.Item name={[field.name, 'title']} label="选题标题" rules={[{ required: true }]}>
                      <Input maxLength={200} />
                    </Form.Item>
                    <Space wrap align="start">
                      <Form.Item name={[field.name, 'direction']} label="业务方向" rules={[{ required: true }]}>
                        <Input style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'specialty']} label="专业方向" rules={[{ required: true }]}>
                        <Select style={{ width: 220 }} options={options('specialty')} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'customer_scenario']} label="客户场景" rules={[{ required: true }]}>
                        <Input style={{ width: 200 }} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'user_perspective']} label="用户视角" rules={[{ required: true }]}>
                        <Input style={{ width: 200 }} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'business_direction']} label="业务导向" rules={[{ required: true }]}>
                        <Input style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'topic_principle']} label="选题原则" rules={[{ required: true }]}>
                        <Input style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item name={[field.name, 'topic_angle']} label="选题角度" rules={[{ required: true }]}>
                        <Input style={{ width: 180 }} />
                      </Form.Item>
                    </Space>
                    <Form.Item name={[field.name, 'core_angle']} label="核心角度" rules={[{ required: true }]}>
                      <Input.TextArea rows={3} />
                    </Form.Item>
                  </Card>
                ))}
                <Button onClick={() => add({})}>添加一条</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal open={raw !== null} onCancel={() => setRaw(null)} footer={null} width={720} title="AI 原始响应留档">
        <pre className="pre-wrap" style={{ maxHeight: 520, overflow: 'auto' }}>
          {raw}
        </pre>
      </Modal>
    </Card>
  )
}
