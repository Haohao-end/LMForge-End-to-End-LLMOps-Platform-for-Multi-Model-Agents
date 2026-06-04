type ChatMessageSizeSource = {
  query?: string
  image_urls?: string[]
  answer?: string
  answer_parts?: unknown[]
  artifacts?: unknown[]
  agent_thoughts?: unknown[]
  suggested_questions?: string[]
}

export const CHAT_MESSAGE_MIN_ITEM_SIZE = 180

const toStableJson = (value: unknown) => {
  try {
    return JSON.stringify(value ?? null)
  } catch {
    return String(value ?? '')
  }
}

const normalizeImageUrls = (value: unknown) => {
  if (!Array.isArray(value))
    return ''

  return value
    .map((item) => String(item ?? '').trim())
    .filter(Boolean)
    .join('|')
}

/**
 * Build a stable signature for message layout-relevant fields.
 *
 * DynamicScrollerItem only recomputes sizes when its sizeDependencies change.
 * The signature includes the content that can change rendered height.
 */
export const buildChatMessageSizeDependencies = (
  message: ChatMessageSizeSource,
  loading: boolean = false,
) => {
  return [
    String(message.query ?? ''),
    normalizeImageUrls(message.image_urls),
    String(message.answer ?? ''),
    toStableJson(message.answer_parts ?? []),
    toStableJson(message.artifacts ?? []),
    toStableJson(message.agent_thoughts ?? []),
    toStableJson(message.suggested_questions ?? []),
    loading ? 1 : 0,
  ]
}
