import { useState } from 'react'
import { Alert, Button, Card, Space, Table, Typography, Upload, message } from 'antd'
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { download, http } from '@/api/client'
import { TABLE_EMPTY } from '@/components/tableEmpty'
import type { ImportResult } from '@/types'

export default function MaterialImport() {
  const [result, setResult] = useState<ImportResult | null>(null)
  const [loading, setLoading] = useState(false)

  const getTemplate = async () => {
    const { data } = await http.get('/materials/csv-template', { responseType: 'blob' })
    download(data as Blob, 'material_import_template.csv')
  }

  return (
    <Card title="资料批量导入（CSV / TXT）">
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="一期为固定模板导入"
        description="请先下载模板，按列填写后上传。必填列：标题、内容、分类、来源类型、可信度、有效期起、有效期止；标签多个用 | 分隔。导入成功的资料会按系统默认规则保存，可在资料列表中查看。"
      />
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<DownloadOutlined />} onClick={getTemplate}>
          下载导入模板
        </Button>
        <Upload
          accept=".csv,.txt"
          showUploadList={false}
          customRequest={async (opt) => {
            const fd = new FormData()
            fd.append('file', opt.file as File)
            setLoading(true)
            try {
              const { data } = await http.post<ImportResult>('/materials/import', fd)
              setResult(data)
              message.success(`导入完成：成功 ${data.success} 行，失败 ${data.failed} 行`)
            } finally {
              setLoading(false)
            }
          }}
        >
          <Button type="primary" icon={<UploadOutlined />} loading={loading}>
            选择文件并导入
          </Button>
        </Upload>
      </Space>

      {result && (
        <>
          <Typography.Paragraph>
            共 {result.total_rows} 行，成功 {result.success} 行，失败 {result.failed} 行。原文件留档：
            <code>{result.stored_file}</code>
          </Typography.Paragraph>
          {result.failed > 0 && (
            <Table
              locale={TABLE_EMPTY}
              rowKey="row"
              size="small"
              dataSource={result.errors}
              pagination={false}
              columns={[
                { title: '行号', dataIndex: 'row', width: 100 },
                { title: '失败原因', dataIndex: 'message' },
              ]}
            />
          )}
        </>
      )}
    </Card>
  )
}
