import { describe, expect, it } from 'vitest'
import { buildChatMessageSizeDependencies } from '../chat-message-size'

describe('chat-message-size', () => {
  it('changes the layout signature when content that affects height changes', () => {
    const base = buildChatMessageSizeDependencies({
      query: '请总结这张图',
      image_urls: ['https://example.com/image-a.png'],
      answer: '第一版回答',
      answer_parts: [{ type: 'text', text: '第一版回答' }],
      artifacts: [{ name: 'plan.docx', url: 'https://example.com/plan.docx' }],
      agent_thoughts: [
        {
          id: 'thought-1',
          event: 'deepStep',
          thought: '正在整理步骤',
          tool: 'write_todos',
          tool_input: {
            timeline: {
              title: '整理步骤',
            },
          },
        },
      ],
      suggested_questions: ['继续'],
    })

    const updated = buildChatMessageSizeDependencies({
      query: '请总结这张图',
      image_urls: ['https://example.com/image-a.png'],
      answer: '第一版回答',
      answer_parts: [{ type: 'text', text: '第一版回答' }],
      artifacts: [{ name: 'plan.docx', url: 'https://example.com/plan.docx' }],
      agent_thoughts: [
        {
          id: 'thought-1',
          event: 'deepStep',
          thought: '正在整理更完整的步骤说明',
          tool: 'write_todos',
          tool_input: {
            timeline: {
              title: '整理步骤',
            },
          },
        },
      ],
      suggested_questions: ['继续'],
    })

    expect(base).toHaveLength(8)
    expect(updated).toHaveLength(8)
    expect(base).not.toEqual(updated)
    expect(base[7]).toBe(0)
    expect(buildChatMessageSizeDependencies({ query: 'x' }, true)[7]).toBe(1)
  })
})
