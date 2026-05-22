import type { BasePaginatorRequest, BasePaginatorResponse, BaseResponse } from '@/models/base'

export type McpCategory = {
  id: string
  name: string
  priority: number
  background: string
}

export type McpToolInput = {
  name: string
  type: string
  required: boolean
  description: string
}

export type McpTool = {
  name: string
  label: string
  description: string
  inputs: McpToolInput[]
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

export type McpProvider = {
  id: string
  provider_key: string
  name: string
  label: string
  icon: string
  background: string
  description: string
  category: string
  transport: string
  url: string
  command: string
  headers: { key: string; value: string }[]
  tool_names: string[]
  args: string[]
  env: Record<string, string>
  timeout_seconds: number
  source_type: string
  source_key: string
  source_url: string
  creator_name: string
  creator_avatar: string
  is_public: boolean
  is_bindable: boolean
  bind_reason: string
  published_at: number
  created_at: number
  updated_at: number
  tool_count: number
  tools: McpTool[]
  binding: McpBinding
}

export type GetMcpProvidersWithPageRequest = BasePaginatorRequest & {
  search_word?: string
  category?: string
}

export type CreateMcpProviderRequest = {
  name: string
  label?: string
  icon?: string
  description: string
  category?: string
  transport?: string
  url?: string
  command?: string
  headers?: { key: string; value: string }[]
  tool_names?: string[]
  args?: string[]
  env?: Record<string, string>
  timeout_seconds?: number
}

export type UpdateMcpProviderRequest = CreateMcpProviderRequest

export type GetMcpCategoriesResponse = BaseResponse<{
  categories: McpCategory[]
}>

export type GetMcpProvidersWithPageResponse = BasePaginatorResponse<McpProvider>

export type GetMcpProviderResponse = BaseResponse<McpProvider>

