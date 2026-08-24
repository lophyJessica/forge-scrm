/** 后端返回的数据结构（与 backend/app/schemas 对齐）。 */

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface DataScope {
  type: '全量' | '指定'
  material_class_ids?: number[] | null
  data_source_ids?: number[] | null
}

export interface UserOut {
  id: number
  username: string
  role: '管理员' | '成员'
  status: '启用' | '停用'
  functional_permissions: string[]
  data_scope: DataScope
  created_by?: number | null
  created_at: string
  last_login_at?: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  must_change_password: boolean
  user: UserOut
}

export interface MaterialClassOut {
  id: number
  name: string
  parent_id?: number | null
  sort?: number | null
}

export interface TagOut {
  id: number
  name: string
  group_name?: string | null
}

export interface MaterialOut {
  id: number
  title: string
  content: string
  class_id: number
  class_name?: string | null
  source_type: string
  source_url?: string | null
  trust_level: string
  valid_from: string
  valid_until: string
  status: string
  is_ai_product: boolean
  source_analysis_task_id?: number | null
  reviewer_id?: number | null
  reviewed_at?: string | null
  created_by: number
  created_at: string
  tags: string[]
}

export interface TopicOut {
  id: number
  title: string
  direction: string
  specialty: string
  customer_scenario: string
  user_perspective: string
  business_direction: string
  core_angle: string
  topic_principle: string
  topic_angle: string
  status: string
  screening_result?: string | null
  batch_no?: string | null
  has_ai_raw_response: boolean
  material_ids: number[]
  created_by: number
  created_at: string
}

export interface TopicBatchOut {
  batch_no: string
  direction: string
  count: number
  created_at: string
  created_by: number
}

export interface TopicGenerateResult {
  batch_no: string
  requested: number
  generated: number
  deduped: number
  saved: number
  topics: TopicOut[]
  ai_raw_archive: string
}

export interface ScriptOut {
  id: number
  topic_id?: number | null
  topic_title?: string | null
  content: string
  style: string
  content_elements: string[]
  current_version: number
  status: string
  reviewer_id?: number | null
  reviewed_at?: string | null
  created_by: number
  created_at: string
  modified_by: number
  modified_at: string
  material_refs?: number[] | null
}

export interface ScriptVersionOut {
  id: number
  script_id: number
  version: number
  content_snapshot: string
  changed_by: number
  changed_at: string
  note?: string | null
}

export interface ScriptDiffOut {
  left_version: number
  right_version: number
  left_content: string
  right_content: string
  diff: string
}

export interface DataSourceOut {
  id: number
  name: string
  collection_method: string
  business_object: string
  platform?: string | null
  account_identifier?: string | null
  is_benchmark: boolean
  config?: Record<string, unknown> | null
  status?: string | null
}

export interface RawDataOut {
  id: number
  source_id: number
  source_name?: string | null
  collected_at: string
  raw_content?: string | null
  structured?: Record<string, unknown> | null
  window_start: string
  window_end: string
  clean_dedup_record: Record<string, unknown>
}

export interface AnalysisResultOut {
  id: number
  task_id: number
  result_content: {
    effect?: string
    conclusion?: string
    suggestions?: string[]
    evidence?: string
    material_candidates?: { title: string; content: string }[]
    topic_candidates?: { title: string; core_angle: string }[]
  }
  writeback_material_status: string
  writeback_topic_status: string
  material_ids: number[]
  topic_ids: number[]
}

export interface AnalysisTaskOut {
  id: number
  name?: string | null
  type: string
  status: string
  prompt_version_snapshot?: Record<string, unknown> | null
  material_context_snapshot?: Record<string, unknown> | null
  output_schema: Record<string, unknown>
  has_ai_raw_response: boolean
  error_message?: string | null
  reviewer_id?: number | null
  reviewed_at?: string | null
  created_by: number
  created_at: string
  retry_count?: number | null
  raw_data_ids: number[]
  results: AnalysisResultOut[]
}

export interface PromptTemplateOut {
  id: number
  task_type: string
  name: string
  content: string
  version?: number | null
  material_combo?: number[] | null
  output_schema?: Record<string, unknown> | null
  status?: string | null
  created_by: number
  created_at: string
}

export interface ImportResult {
  total_rows: number
  success: number
  failed: number
  errors: { row: number; message: string }[]
  stored_file: string
  created_ids: number[]
}

export interface RawDataImportResult {
  total: number
  success: number
  failed: number
  errors: { row: number; message: string }[]
  stored_file: string
}

/** /api/meta/enums 返回的枚举字典（前端不硬编码第二套，context/05 §5）。 */
export type EnumMap = Record<string, string[]>

export interface PermissionItem {
  code: string
  label: string
}
