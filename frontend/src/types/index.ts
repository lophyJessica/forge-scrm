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

export interface BenchmarkAccountOut {
  id: number
  platform: string
  account_identifier: string
  account_name?: string | null
  profile_url?: string | null
  benchmark_flag: boolean
  enabled: boolean
  notes?: string | null
  created_by: number
  created_at: string
  updated_at: string
  last_collected_at?: string | null
}

export type CollectionTaskStatus = 'pending' | 'running' | 'success' | 'partial_success' | 'failed'

export interface CollectionTaskOut {
  id: number
  task_no: string
  trigger_type: string
  status: CollectionTaskStatus
  scope_type: string
  scope_config: Record<string, unknown>
  time_window_start: string
  time_window_end: string
  requested_by: number
  started_at?: string | null
  finished_at?: string | null
  total_count: number
  success_count: number
  failure_count: number
  retry_count: number
  error_message?: string | null
  idempotency_key?: string | null
  created_at: string
}

export interface CollectionRecordOut {
  id: number
  task_id: number
  benchmark_account_id?: number | null
  source_type: string
  source_url?: string | null
  status: string
  attempt_no: number
  requested_at: string
  completed_at?: string | null
  raw_response?: string | null
  http_status?: number | null
  item_count: number
  error_code?: string | null
  error_message?: string | null
  retryable: boolean
}

export interface CollectionResultOut {
  id: number
  record_id: number
  task_id: number
  benchmark_account_id?: number | null
  business_object: string
  platform?: string | null
  account_identifier?: string | null
  is_benchmark: boolean
  source_url?: string | null
  raw_content: string
  structured_data?: Record<string, unknown> | null
  collected_at: string
  window_start: string
  window_end: string
  data_cleaning_note?: string | null
  is_ai_product: boolean
  ai_derivative_id?: number | null
  created_at: string
}

export type ResearchTaskStatus = 'pending' | 'searching' | 'organizing' | 'success' | 'failed'

export interface ResearchTaskOut {
  id: number
  task_no: string
  topic: string
  objective: string
  scope_config: Record<string, unknown>
  time_window_start?: string | null
  time_window_end?: string | null
  status: ResearchTaskStatus
  current_stage?: string | null
  progress_percent?: number | null
  progress_message?: string | null
  checkpoint_data?: Record<string, unknown> | null
  retry_count: number
  last_error_code?: string | null
  last_error_message?: string | null
  started_at?: string | null
  finished_at?: string | null
  requested_by: number
  created_at: string
  updated_at: string
}

export interface ResearchReferenceOut {
  id: number
  report_id: number
  source_kind: string
  source_url?: string | null
  source_title?: string | null
  search_provider?: string | null
  collection_result_id?: number | null
  material_id?: number | null
  source_snapshot?: string | null
  page_number?: string | null
  paragraph_locator?: string | null
  evidence_summary?: string | null
  source_type?: string | null
  cited_at: string
  created_at: string
}

export interface ResearchReportOut {
  id: number
  research_task_id: number
  title: string
  summary: string
  content: string
  sections?: Record<string, unknown> | null
  conclusions?: Record<string, unknown> | null
  generation_trace?: Record<string, unknown> | null
  raw_ai_response?: string | null
  is_ai_product: boolean
  status: string
  source_count: number
  created_at: string
  updated_at: string
  references?: ResearchReferenceOut[]
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

export type ReportType = '运营数据报告' | '市场分析周报'
export type ReportGenerationStatus = '待生成' | '生成中' | '已完成' | '失败'
export type ReportReviewStatus = '默认通过' | '抽查中' | '已确认' | '待审核' | '已废弃'
export type ReportPushChannel = '飞书' | '微信'
export type ReportPushStatus = '待推送' | '推送中' | '已推送' | '失败' | '已取消'

export interface ReportOut {
  id: number
  report_no: string
  report_type: ReportType
  title: string
  period_start: string
  period_end: string
  template_id?: number | null
  source_config: Record<string, unknown>
  source_snapshot?: Record<string, unknown> | null
  summary: string
  content: string
  sections?: Record<string, unknown> | null
  conclusions?: Record<string, unknown> | null
  generation_trace?: Record<string, unknown> | null
  raw_ai_response?: string | null
  is_ai_product: boolean
  generation_status: ReportGenerationStatus
  review_status: ReportReviewStatus
  retry_count: number
  error_code?: string | null
  error_message?: string | null
  created_by: number
  created_at: string
  updated_at: string
  generated_at?: string | null
}

export interface ReportPushRecordOut {
  id: number
  push_task_id: number
  channel: ReportPushChannel
  target_object: string
  recipient_type: string
  message_summary: string
  sent_at?: string | null
  status: ReportPushStatus
  error_code?: string | null
  error_message?: string | null
  attempt_no: number
  created_at: string
}

export interface ReportPushTaskOut {
  id: number
  task_no: string
  report_id: number
  channel: ReportPushChannel
  recipient_type: string
  target_object: string
  message_config?: Record<string, unknown> | null
  status: ReportPushStatus
  retry_count: number
  created_by: number
  created_at: string
  updated_at: string
  records?: ReportPushRecordOut[]
}

export interface PermissionItem {
  code: string
  label: string
}
