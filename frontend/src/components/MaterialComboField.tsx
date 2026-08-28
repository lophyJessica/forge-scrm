import { useEffect, useMemo, useState } from 'react'
import { Collapse, Form, Input, Select, Space, Typography } from 'antd'
import { http } from '@/api/client'
import type { MaterialClassOut, MaterialOut, PageResult, TagOut } from '@/types'

export default function MaterialComboField() {
  const form = Form.useFormInstance()
  const selectedIds = Form.useWatch<number[]>('material_combo', form) ?? []
  const [materials, setMaterials] = useState<MaterialOut[]>([])
  const [classes, setClasses] = useState<MaterialClassOut[]>([])
  const [tags, setTags] = useState<TagOut[]>([])
  const [keyword, setKeyword] = useState('')
  const [classId, setClassId] = useState<number>()
  const [tag, setTag] = useState<string>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([
      http.get<PageResult<MaterialOut>>('/materials', { params: { status: '已生效', page_size: 200 } }),
      http.get<MaterialClassOut[]>('/material-classes'),
      http.get<TagOut[]>('/tags'),
    ]).then(([materialResponse, classResponse, tagResponse]) => {
      if (!active) return
      setMaterials(materialResponse.data.items)
      setClasses(classResponse.data)
      setTags(tagResponse.data)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [])

  const options = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase()
    const selected = new Set(selectedIds)
    const visible = materials.filter((material) => (
      (!classId || material.class_id === classId)
      && (!tag || material.tags.includes(tag))
      && (!normalizedKeyword
        || material.title.toLowerCase().includes(normalizedKeyword)
        || material.content.toLowerCase().includes(normalizedKeyword))
    ))
    const visibleIds = new Set(visible.map((material) => material.id))
    const selectedOutsideFilter = materials.filter(
      (material) => selected.has(material.id) && !visibleIds.has(material.id),
    )
    return [...visible, ...selectedOutsideFilter].map((material) => ({
      value: material.id,
      label: `#${material.id} ${material.title}${material.class_name ? `（${material.class_name}）` : ''}`,
    }))
  }, [classId, keyword, materials, selectedIds, tag])

  const selectedMaterials = useMemo(() => {
    const materialById = new Map(materials.map((material) => [material.id, material]))
    return selectedIds.flatMap((id) => {
      const material = materialById.get(id)
      return material ? [material] : []
    })
  }, [materials, selectedIds])

  return (
    <Space direction="vertical" size={8} style={{ display: 'flex' }}>
      <Space wrap>
        <Input
          allowClear
          value={keyword}
          placeholder="标题/正文关键词"
          style={{ width: 220 }}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Select
          allowClear
          value={classId}
          placeholder="分类"
          style={{ width: 160 }}
          options={classes.map((item) => ({ label: item.name, value: item.id }))}
          onChange={setClassId}
        />
        <Select
          allowClear
          showSearch
          value={tag}
          placeholder="标签"
          style={{ width: 160 }}
          options={tags.map((item) => ({ label: item.name, value: item.name }))}
          onChange={setTag}
        />
      </Space>
      <Form.Item
        name="material_combo"
        label="引用资料（生成时自动注入最新内容）"
        extra="勾选后，每次使用该模板生成时会自动附带这些资料的最新内容；资料更新无需修改模板"
        style={{ marginBottom: 0 }}
      >
        <Select
          mode="multiple"
          allowClear
          showSearch
          loading={loading}
          optionFilterProp="label"
          maxTagCount="responsive"
          placeholder="选择已生效资料"
          options={options}
        />
      </Form.Item>
      {selectedMaterials.length > 0 && (
        <Collapse
          size="small"
          items={[
            {
              key: 'material-preview',
              label: `引用预览（${selectedMaterials.length} 条）`,
              children: (
                <Space direction="vertical" size={8} style={{ display: 'flex' }}>
                  {selectedMaterials.map((material) => (
                    <div key={material.id}>
                      <Typography.Text strong>
                        【{material.class_name || '未分类'}】{material.title}
                      </Typography.Text>
                      <Typography.Paragraph style={{ margin: 0 }} type="secondary">
                        {material.content.slice(0, 200)}{material.content.length > 200 ? '...' : ''}
                      </Typography.Paragraph>
                    </div>
                  ))}
                </Space>
              ),
            },
          ]}
        />
      )}
    </Space>
  )
}
