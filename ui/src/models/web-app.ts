import type { BaseResponse } from '@/models/base'

// 获取WebApp基础信息响应结构
export type GetWebAppResponse = BaseResponse<{
  id: string
  icon: string
  name: string
  description: string
  app_config: {
    opening_statement: string
    opening_questions: string[]
    suggested_after_answer: {
      enable: boolean
    }
    features: string[]
    capabilities: {
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
      image_output: {
        enabled: boolean
        reason_code: string
      }
      artifact_output: {
        enabled: boolean
        reason_code: string
      }
    }
    text_to_speech: {
      enable: boolean
      auto_play?: boolean
      voice?: string
    }
    speech_to_text: {
      enable: boolean
    }
  }
}>

// 获取WebApp会话消息列表响应结构
export type GetWebAppConversationsResponse = BaseResponse<
  {
    id: string
    name: string
    summary: string
    created_at: number
  }[]
>

// 与WebApp对话请求结构
export type WebAppChatRequest = {
  conversation_id?: string
  query: string
  image_urls?: string[]
  enable_deep_thinking?: boolean
}
