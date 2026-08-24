/** 枚举字典（zustand）：统一从 /api/meta/enums 拉取，前端不硬编码第二套（context/05 §5）。 */
import { create } from 'zustand'
import { http } from '@/api/client'
import type { EnumMap, PermissionItem } from '@/types'

interface MetaState {
  enums: EnumMap
  permissions: PermissionItem[]
  loaded: boolean
  load: () => Promise<void>
  options: (key: string) => { label: string; value: string }[]
}

export const useMetaStore = create<MetaState>((set, get) => ({
  enums: {},
  permissions: [],
  loaded: false,

  load: async () => {
    if (get().loaded) return
    const [enumsResp, permsResp] = await Promise.all([
      http.get<EnumMap>('/meta/enums'),
      http.get<PermissionItem[]>('/meta/permissions'),
    ])
    set({ enums: enumsResp.data, permissions: permsResp.data, loaded: true })
  },

  options: (key) => (get().enums[key] || []).map((v) => ({ label: v, value: v })),
}))

/** 权限码常量（与后端 app/core/enums.py Permission 一一对应）。 */
export const PERM = {
  材料删除: 'material.delete',
  标签创建: 'tag.create',
  选题生成: 'topic.generate',
  选题手动新增: 'topic.create',
  选题修改: 'topic.update',
  脚本修改: 'script.update',
  脚本版本查看: 'script.version.view',
  脚本版本回退: 'script.version.rollback',
  数据录入导入: 'rawdata.input',
  分析任务执行: 'analysis.task.execute',
  分析结果审核: 'analysis.result.review',
  回写反哺: 'analysis.writeback',
  提示词配置: 'prompt.config',
} as const
