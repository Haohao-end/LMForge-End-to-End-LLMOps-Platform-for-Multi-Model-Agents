import {
  type BasePaginatorRequest,
  type BasePaginatorResponse,
  type BaseResponse,
} from '@/models/base' // 获取应用信息响应结构
import type { SkillBinding, SkillBindingRequest } from '@/models/skill'

// 应用版本类型
export type AppVersion = {
  id: string
  app_id: string
  version: number
  config_type: string
  config: Record<string, any>
  is_current_published: boolean
  label: string
  summary: string
  created_at: number
  updated_at: number
}

export type McpBinding = {
  name: string
  description: string
  transport: string
  url: string
  command: string
  enabled: boolean
  headers: { key: string; value: string }[]
  tool_names: string[]
  timeout_seconds: number
  args: string[]
  env: Record<string, string>
  provider_key?: string
  source_type?: string
  source_key?: string
  source_url?: string
  label?: string
  icon?: string
  category?: string
}

export type McpToolSnapshot = {
  binding_identity: string
  binding_hash: string
  binding: McpBinding
  status: string
  tool_definitions: Record<string, any>[]
  tool_names: string[]
  tool_count: number
  schema_hash: string
  last_attempt_at: number
  last_success_at: number | null
  last_error: string
  retry_count: number
  retryable: boolean
}

export type AgentBinding = {
  app_id: string
  invoke_mode?: 'a2a' | 'tool'
  name?: string
  icon?: string
  description?: string
  source_scope?: 'public' | 'own'
  is_public?: boolean
  status?: string
  tool_name?: string
}

export type AgentBindingRequest = {
  app_id: string
}

// 获取应用信息响应结构
export type GetAppResponse = BaseResponse<{
  id: string
  debug_conversation_id: string
  name: string
  icon: string
  description: string
  status: string
  is_public: boolean
  category: string
  draft_updated_at: number
  updated_at: number
  created_at: number
}>

// 新增应用请求结构
export type CreateAppRequest = { name: string; icon: string; description: string }

// 更新应用请求结构
export type UpdateAppRequest = { name: string; icon: string; description: string }

// 获取应用分页列表数据请求
export type GetAppsWithPageRequest = BasePaginatorRequest & {
  search_word: string
  published_only?: boolean
}

// 获取应用分页列表数据响应
export type GetAppsWithPageResponse = BasePaginatorResponse<{
  id: string
  name: string
  icon: string
  description: string
  preset_prompt: string
  model_config: {
    provider: string
    model: string
  }
  status: string
  is_public: boolean
  creator_name: string
  creator_avatar: string
  draft_updated_at: number
  updated_at: number
  created_at: number
}>

// 获取特定应用的草稿配置响应结构
export type GetDraftAppConfigResponse = BaseResponse<{
  id: string
  model_config: { provider: string; model: string; parameters: Record<string, any> }
  capabilities?: {
    requested_model: { provider: string; model: string }
    effective_model: { provider: string; model: string }
    features: string[]
    requested_features: string[]
    image_input: {
      enabled: boolean
      via_fallback: boolean
      policy: string
      requested_model_supports: boolean
      effective_model_supports: boolean
      fallback_model: { provider: string; model: string } | null
      fallback_model_supports: boolean
      reason_code: string
      message: string
    }
    image_output: { enabled: boolean; reason_code: string }
    artifact_output: { enabled: boolean; reason_code: string }
  }
  dialog_round: number
  preset_prompt: string
  tools: {
    type: string
    provider: { id: string; name: string; label: string; icon: string; description: string }
    tool: {
      id: string
      name: string
      label: string
      description: string
      params: Record<string, any>
    }
  }[]
  mcp_bindings: McpBinding[]
  mcp_tool_snapshots: McpToolSnapshot[]
  agent_bindings: AgentBinding[]
  skills: SkillBinding[]
  workflows: { id: string; name: string; icon: string; description: string }[]
  datasets: { id: string; name: string; icon: string; description: string }[]
  retrieval_config: { retrieval_strategy: string; k: number; score: number }
  long_term_memory: { enable: boolean }
  opening_statement: string
  opening_questions: string[]
  speech_to_text: { enable: boolean }
  text_to_speech: { enable: boolean; voice: string; auto_play: boolean }
  suggested_after_answer: { enable: boolean }
  review_config: {
    enable: boolean
    keywords: string[]
    inputs_config: { enable: boolean; preset_response: string }
    outputs_config: { enable: boolean }
  }
  updated_at: number
  created_at: number
}>

// 更新特定应用的草稿配置请求结构
export type UpdateDraftAppConfigRequest = {
  model_config?: { provider: string; model: string; parameters: Record<string, any> }
  dialog_round?: number
  preset_prompt?: string
  tools?: { type: string; provider_id: string; tool_id: string; params: Record<string, any> }[]
  mcp_bindings?: McpBinding[]
  agent_bindings?: AgentBindingRequest[]
  skills?: SkillBindingRequest[]
  workflows?: string[]
  datasets?: string[]
  retrieval_config?: { retrieval_strategy: string; k: number; score: number }
  long_term_memory?: { enable: boolean }
  opening_statement?: string
  opening_questions?: string[]
  speech_to_text?: { enable: boolean }
  text_to_speech?: { enable: boolean; voice: string; auto_play: boolean }
  suggested_after_answer?: { enable: boolean }
  review_config?: {
    enable: boolean
    keywords: string[]
    inputs_config: { enable: boolean; preset_response: string }
    outputs_config: { enable: boolean }
  }
}

export type PromptCompareHistoryItem = {
  query: string
  answer: string
}

export type PromptCompareChatRequest = {
  lane_id: string
  query: string
  preset_prompt: string
  model_config: { provider: string; model: string; parameters: Record<string, any> }
  history: PromptCompareHistoryItem[]
}

// 获取应用的调试会话消息列表响应结构
export type GetDebugConversationMessagesWithPageResponse = BasePaginatorResponse<{
  id: string
  conversation_id: string
  query: string
  image_urls: string[]
  input_parts: Array<Record<string, any>>
  answer: string
  answer_parts: Array<Record<string, any>>
  artifacts: Array<Record<string, any>>
  total_token_count: number
  latency: number
  agent_thoughts: {
    id: string
    position: number
    event: string
    thought: string
    observation: string
    tool: string
    tool_input: Record<string, any>
    latency: number
    created_at: number
  }[]
  suggested_questions: string[]
  created_at: number
}>

// 获取应用的发布历史配置列表分页响应结构
export type GetPublishHistoriesWithPageResponse = BasePaginatorResponse<{
  id: string
  app_id: string
  version: number
  config_type: string
  config: Record<string, any>
  updated_at: number
  created_at: number
  is_current_published: boolean
  label: string
  summary: string
}>

export type GetVersionsResponse = BaseResponse<{
  list: AppVersion[]
}>

// 获取应用的调试会话消息列表请求结构
export type GetDebugConversationMessagesWithPageRequest = BasePaginatorRequest & {
  created_at?: number
  conversation_id?: string
}

// 获取应用发布配置响应结构
export type GetPublishedConfigResponse = BaseResponse<{
  web_app: {
    token: string
    status: string
  }
}>

// 重新生成WebApp凭证标识响应结构
export type RegenerateWebAppTokenResponse = BaseResponse<{
  token: string
}>
