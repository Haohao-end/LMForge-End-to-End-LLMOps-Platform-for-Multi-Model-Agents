export type ChatThought = {
  id: string
  position: number
  event: string
  thought: string
  observation: string
  tool: string
  tool_input: Record<string, unknown>
  latency: number
  created_at: number
}

export type ChatConversationMessage = {
  id: string
  conversation_id: string
  query: string
  image_urls: string[]
  input_parts?: Array<Record<string, unknown>>
  answer: string
  answer_parts: Array<Record<string, unknown>>
  artifacts: Array<Record<string, unknown>>
  total_token_count: number
  latency: number
  agent_thoughts: ChatThought[]
  suggested_questions: string[]
  created_at?: number
}
