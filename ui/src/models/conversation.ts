import { type BasePaginatorRequest, type BasePaginatorResponse, type BaseResponse } from '@/models/base'
import type { ChatConversationMessage } from '@/models/chat'

// 获取指定会话消息列表请求结构
export type GetConversationMessagesWithPageRequest = BasePaginatorRequest & {
  created_at: number
}

// 获取指定会话消息列表响应结构
export type GetConversationMessagesWithPageResponse = BasePaginatorResponse<ChatConversationMessage>

export type RecentConversation = {
  id: string
  name: string
  source_type: 'assistant_agent' | 'app_debugger' | 'public_app'
  app_id: string
  app_name: string
  agent_name: string
  message_id: string
  is_active: boolean
  latest_message_at: number
  created_at: number
  human_message: string
  ai_message: string
}

export type GetRecentConversationsResponse = BaseResponse<RecentConversation[]>
