import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Form, Input, Modal, Popconfirm, Select, Table, Tag, message } from 'antd'
import { http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import { TableActions } from '@/components/TableActions'
import { useAuthStore } from '@/store/auth'
import { PERM, useMetaStore } from '@/store/meta'
import { FILTER_CARD_STYLE, TABLE_PAGINATION, displayStatus, statusTagColor, visibleStatusOptions } from '@/theme'
import type { AnalysisTaskOut, MaterialOut, PageResult, PromptTemplateOut, RawDataOut } from '@/types'

export default function AnalysisTasks() {
  const [queryForm] = Form.useForm()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const can = useAuthStore((s) => s.can)
  const isAdmin = useAuthStore((s) => s.isAdmin)
  const options = useMetaStore((s) => s.options)
  const [rows, setRows] = useState<AnalysisTaskOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState<number | null>(null)
  const [open, setOpen] = useState(false)
  const [rawData, setRawData] = useState<RawDataOut[]>([])
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [templates, setTemplates] = useState<PromptTemplateOut[]>([])

  const load = useCallback(
    async (targetPage = 1) => {
      setLoading(true)
      try {
        const { data } = await http.get<PageResult<AnalysisTaskOut>>('/analysis-tasks', {
          params: { ...queryForm.getFieldsValue(), page: targetPage, page_size: 20 },
        })
        setRows(data.items)
        setTotal(data.total)
        setPage(data.page)
      } finally {
        setLoading(false)
      }
    },
    [queryForm],
  )

  useEffect(() => {
    void load(1)
  }, [load])

  const openModal = async () => {
    form.resetFields()
    const [raw, mat, tpl] = await Promise.all([
      http.get<PageResult<RawDataOut>>('/raw-data', { params: { page_size: 200 } }),
      http.get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } }),
      http.get<PageResult<PromptTemplateOut>>('/prompt-templates', { params: { page_size: 100 } }),
    ])
    setRawData(raw.data.items)
    setMaterials(mat.data.items)
    setTemplates(tpl.data.items.filter((t) => t.task_type !== '选题生成' && t.task_type !== '脚本生成'))
    setOpen(true)
  }

  const create = async () => {
    const values = await form.validateFields()
    await http.post('/analysis-tasks', values)
    message.success('任务已创建（待执行）')
    setOpen(false)
    void load(1)
  }

  const execute = async (id: number) => {
    setRunning(id)
    try {
      // D-T1：同步执行；失败时后端返回 400，错误详情由 http 拦截器统一提示
      await http.post<AnalysisTaskOut>(`/analysis-tasks/${id}/execute`)
      message.success('执行完成')
    } finally {
      setRunning(null)
      void load(page)
    }
  }

  const remove = async (id: number) => {
    await http.delete(`/analysis-tasks/${id}`)
    message.success('已删除')
    void load(page)
  }

  return (
    <Card
      title="分析任务"
      extra={
        can(PERM.分析任务执行) && (
          <Button type="primary" onClick={openModal}>
            新建分析任务
          </Button>
        )
      }
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="一期为同步执行：点击「执行」后请等待返回（AI 调用失败自动重试 3 次），不做异步队列与通知。"
      />
      <Form form={queryForm} layout="inline" style={FILTER_CARD_STYLE} onFinish={() => load(1)}>
        <Form.Item name="type">
          <Select allowClear placeholder="任务类型" style={{ width: 180 }} options={options('analysis_task_type')} />
        </Form.Item>
        <Form.Item name="status">
          <Select allowClear placeholder="状态" style={{ width: 140 }} options={visibleStatusOptions(options('analysis_task_status'))} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">
            查询
          </Button>
        </Form.Item>
      </Form>

      <Table<AnalysisTaskOut>
        locale={TABLE_EMPTY}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ ...TABLE_PAGINATION, current: page, total, pageSize: 20, onChange: (p) => load(p) }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          {
            title: '任务名称',
            dataIndex: 'name',
            ellipsis: true,
            render: (v: string | null, r) => <a onClick={() => navigate(`/analysis/tasks/${r.id}`)}>{v || `任务 #${r.id}`}</a>,
          },
          { title: '类型', dataIndex: 'type', width: 160 },
          {
            title: '状态',
            dataIndex: 'status',
            width: 110,
            render: (v: string) => {
              const label = displayStatus(v, '已确认')
              return <Tag color={statusTagColor(label)}>{label}</Tag>
            },
          },
          { title: '重试次数', dataIndex: 'retry_count', width: 100 },
          { title: '创建时间', dataIndex: 'created_at', width: 190 },
          {
            title: '操作',
            width: 180,
            render: (_, r) => (
              <TableActions
                items={[
                  <Button key="d" size="small" onClick={() => navigate(`/analysis/tasks/${r.id}`)}>
                    详情
                  </Button>,
                  ['待执行', '失败'].includes(r.status) && can(PERM.分析任务执行) ? (
                    <Button key="run" size="small" type="primary" loading={running === r.id} onClick={() => execute(r.id)}>
                      {r.status === '失败' ? '重新执行' : '执行'}
                    </Button>
                  ) : null,
                  isAdmin() ? (
                    <Popconfirm key="del" title="确认删除？" onConfirm={() => remove(r.id)}>
                      <Button size="small" type="link" danger>
                        删除
                      </Button>
                    </Popconfirm>
                  ) : null,
                ]}
              />
            ),
          },
        ]}
      />

      <Modal open={open} title="新建分析任务" onCancel={() => setOpen(false)} onOk={create} width={720} okText="创建" cancelText="取消">
        <Form form={form} layout="vertical" initialValues={{ material_ids: [] }}>
          <Form.Item name="name" label="任务名称">
            <Input maxLength={100} placeholder="可留空" />
          </Form.Item>
          <Form.Item name="type" label="任务类型" rules={[{ required: true }]}>
            <Select options={options('analysis_task_type')} />
          </Form.Item>
          <Form.Item name="raw_data_ids" label="分析输入（原始数据）" rules={[{ required: true }]}>
            <Select
              mode="multiple"
              options={rawData.map((r) => ({
                label: `#${r.id} ${r.source_name || ''} ${(r.raw_content || '').slice(0, 24)}`,
                value: r.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="material_ids" label="资料上下文（仅「已生效」资料参与快照）">
            <Select
              mode="multiple"
              allowClear
              options={materials.map((m) => ({ label: `#${m.id} ${m.title}`, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="prompt_template_id" label="提示词模板（可选，缺省用内置模板）">
            <Select allowClear options={templates.map((t) => ({ label: `${t.name} v${t.version}`, value: t.id }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
