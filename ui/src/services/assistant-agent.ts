import { get, post, ssePost } from '@/utils/request'
import type { BaseResponse } from '@/models/base'
import type {
  GetAssistantAgentMessagesWithPageRequest,
  GetAssistantAgentMessagesWithPageResponse,
} from '@/models/assistant-agent'

// 与辅助Agent进行对话
export const assistantAgentChat = (
  query: string,
  onData: (event_response: Record<string, any>) => void,
) => {
  return ssePost(`/assistant-agent/chat`, { body: { query } }, onData)
}

// 停止与辅助Agent进行对话
export const stopAssistantAgentChat = (task_id: string) => {
  return post<BaseResponse<any>>(`/assistant-agent/chat/${task_id}/stop`)
}

// 获取当前登录账号的辅助 Agent 对话历史列表
export const getAssistantAgentMessagesWithPage = (
  req?: GetAssistantAgentMessagesWithPageRequest,
) => {
  return get<GetAssistantAgentMessagesWithPageResponse>(`/assistant-agent/messages`, {
    params: req,
  })
}

// 清空当前登录账号与辅助 Agent 的对话列表
export const deleteAssistantAgentConversation = () => {
  return post<BaseResponse<any>>(`/assistant-agent/delete-conversation`)
}
