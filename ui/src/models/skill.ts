import type { BasePaginatorRequest, BasePaginatorResponse, BaseResponse } from '@/models/base'

export type SkillCategory = {
  id: string
  name: string
  count: number
}

export type SkillToolInput = {
  name: string
  type: string
  required: boolean
  description: string
}

export type SkillTool = {
  name: string
  label: string
  description: string
  entrypoint: string
  inputs: SkillToolInput[]
}

export type SkillPackage = {
  id: string
  source_key: string
  name: string
  label: string
  icon: string
  description: string
  readme: string
  category: string
  tags: string[]
  capabilities: Record<string, any>
  executor_type: string
  tool_count: number
  tools: SkillTool[]
  created_at: number
  updated_at: number
}

export type SkillBinding = SkillPackage & {
  skill_id: string
}

export type SkillBindingRequest = {
  skill_id: string
}

export type GetSkillsWithPageRequest = BasePaginatorRequest & {
  search_word?: string
  category?: string
}

export type GetSkillsCategoriesResponse = BaseResponse<{
  categories: SkillCategory[]
}>

export type GetSkillsWithPageResponse = BasePaginatorResponse<SkillPackage>

export type GetSkillResponse = BaseResponse<SkillPackage>
