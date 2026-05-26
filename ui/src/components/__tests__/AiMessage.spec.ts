import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { QueueEvent } from '@/config'

import AiMessage from '../AiMessage.vue'

vi.mock('@/hooks/use-audio', () => ({
  useAudioPlayer: () => ({
    messageAudioLoading: { value: false },
    thoughtAudioLoading: { value: false },
    isPlaying: { value: false },
    activeMessageId: { value: '' },
    activeThoughtId: { value: '' },
    activeStreamType: { value: '' },
    startAudioStream: vi.fn(),
    startTextAudioStream: vi.fn(),
    stopAudioStream: vi.fn(),
  }),
}))

vi.mock('@/hooks/use-markdown-renderer', () => ({
  useMarkdownRenderer: () => ({
    renderMarkdown: (value: string) => value,
    handleMarkdownCopyClick: vi.fn(),
  }),
}))

describe('AiMessage.vue', () => {
  const mountAiMessage = (props: Record<string, unknown> = {}) =>
    mount(AiMessage, {
      props: {
        app: {
          name: 'OpenAgent',
          avatar_text: 'OpenAgent',
        },
        answer: '欢迎使用 OpenAgent',
        agent_thoughts: [],
        ...props,
      },
      global: {
        stubs: {
          AgentThought: true,
          DotFlashing: true,
          'a-image': {
            props: ['src', 'preview'],
            template: '<div class="image-stub" :data-src="src"></div>',
          },
          'a-avatar': {
            props: ['imageUrl', 'size', 'shape'],
            template: '<div class="avatar-stub" :data-image-url="imageUrl"><slot /></div>',
          },
          'a-space': { template: '<div><slot /></div>' },
          'a-divider': true,
          'icon-apps': true,
          'icon-check': true,
          'icon-copy': true,
          'icon-loading': true,
          'icon-pause': true,
          'icon-play-circle': true,
        },
      },
    })

  it('renders the OpenAgent full-text avatar when avatar_text is provided', () => {
    const wrapper = mountAiMessage()

    expect(wrapper.find('.avatar-stub').text()).toBe('OpenAgent')
    expect(wrapper.text()).toContain('OpenAgent')
    expect(wrapper.find('.avatar-stub').attributes('data-image-url')).toBeUndefined()
  })

  it('constrains the answer bubble to the available chat column width', () => {
    const wrapper = mountAiMessage({
      answer: '这是一段非常长的 AI 输出内容 '.repeat(20),
    })

    const root = wrapper.get('.group')
    const bubble = wrapper.get('.message-bubble-content')
    const bubbleClasses = bubble.classes()

    expect(root.classes()).toEqual(expect.arrayContaining(['max-w-full', 'min-w-0']))
    expect(bubbleClasses).toContain('message-bubble-content')
    expect(bubbleClasses).toContain('markdown-body')
    expect(bubbleClasses).not.toContain('max-w-[600px]')
  })

  it('uses the same width contract for the loading bubble', () => {
    const wrapper = mountAiMessage({
      answer: '',
      loading: true,
    })

    const bubble = wrapper.get('.message-bubble-content')

    expect(bubble.classes()).toContain('message-bubble-content')
    expect(bubble.classes()).not.toContain('max-w-[600px]')
  })

  it('renders the deep agent timeline when deep step thoughts exist', () => {
    const wrapper = mountAiMessage({
      agent_thoughts: [
        {
          id: 'step-1',
          event: QueueEvent.deepStep,
          thought: '正在拆解任务',
          tool: 'write_todos',
          tool_input: {
            timeline: {
              step_type: 'plan',
              status: 'start',
              title: '拆解任务',
              detail: '共 3 项待办',
              todos: [
                { content: '收集景点', status: 'completed' },
                { title: '预订酒店', status: 'in_progress' },
                { content: '确认交通', status: 'pending' },
              ],
            },
          },
          latency: 1.8,
        },
      ],
    })

    expect(wrapper.find('.deep-agent-timeline').exists()).toBe(true)
    expect(wrapper.find('.deep-agent-timeline__brain').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('🧠')
    expect(wrapper.text()).toContain('共 3 项待办')
    expect(wrapper.text()).toContain('收集景点')
    expect(wrapper.text()).toContain('预订酒店')
    expect(wrapper.text()).toContain('确认交通')
    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(3)
  })

  it('keeps the deep agent todo list visible after write_todos resolves successfully', () => {
    const wrapper = mountAiMessage({
      agent_thoughts: [
        {
          id: 'step-1',
          event: QueueEvent.deepStep,
          thought: '拆解完成',
          tool: 'write_todos',
          tool_input: {
            timeline: {
              step_type: 'plan',
              status: 'success',
              title: '拆解任务',
              detail: '待办已写入',
              todos: [
                { content: '收集景点', status: 'completed' },
                { title: '预订酒店', status: 'completed' },
                { content: '确认交通', status: 'completed' },
              ],
            },
          },
          latency: 2.1,
        },
      ],
    })

    expect(wrapper.find('.deep-agent-timeline').exists()).toBe(true)
    expect(wrapper.find('.deep-agent-timeline__brain').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('🧠')
    expect(wrapper.text()).toContain('待办已写入')
    expect(wrapper.text()).toContain('收集景点')
    expect(wrapper.text()).toContain('预订酒店')
    expect(wrapper.text()).toContain('确认交通')
    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(3)
  })

  it('renders image previews inside the deep agent timeline for image artifacts', () => {
    const wrapper = mountAiMessage({
      answer: '',
      answer_parts: [],
      agent_thoughts: [
        {
          id: 'artifact-1',
          event: QueueEvent.deepArtifactCreated,
          thought: 'cover.png',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'cover.png',
              url: 'https://example.com/cover.png',
              extension: 'png',
              mime_type: 'image/png',
            },
          },
        },
      ],
    })

    expect(wrapper.find('.deep-agent-timeline').exists()).toBe(true)
    expect(wrapper.find('.chat-image-gallery').exists()).toBe(true)
    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/cover.png')
    expect(wrapper.text()).toContain('生成图片')
    expect(wrapper.text()).toContain('png · image/png')
  })

  it('falls back to the legacy deep thinking panel when only deep_thinking exists', () => {
    const wrapper = mountAiMessage({
      agent_thoughts: [
        {
          id: 'deep-1',
          event: QueueEvent.deepThinking,
          thought: '先分析约束，再拆解步骤',
          latency: 1.8,
        },
      ],
    })

    expect(wrapper.find('.deep-thinking-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('先分析约束，再拆解步骤')
  })

  it('renders image and artifact parts from the unified multimodal output protocol', async () => {
    const wrapper = mountAiMessage({
      answer: '已生成图片与附件',
      answer_parts: [
        { type: 'text', text: '已生成图片与附件' },
        { type: 'image', url: 'https://example.com/cover.png', name: 'cover.png' },
        { type: 'image', url: 'https://example.com/detail.png', name: 'detail.png' },
        { type: 'artifact', url: 'https://example.com/plan.docx', name: 'plan.docx', extension: 'docx' },
      ],
    })

    expect(wrapper.find('.chat-image-gallery').exists()).toBe(true)
    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/cover.png')
    expect(wrapper.findAll('.chat-image-gallery__thumb')).toHaveLength(2)
    expect(wrapper.text()).toContain('1/2')

    await wrapper.findAll('.chat-image-gallery__thumb')[1].trigger('click')

    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/detail.png')
    expect(wrapper.find('.message-artifact-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('plan.docx')
    expect(wrapper.text()).toContain('下载附件')
  })

  it('renders one unified gallery for images from different groups', async () => {
    const wrapper = mountAiMessage({
      answer: '已生成两组穿搭图',
      answer_parts: [
        { type: 'text', text: '已生成两组穿搭图' },
        { type: 'image', url: 'https://example.com/1.png', name: 'look-1.png', group_id: 'batch-a', group_name: '通勤穿搭' },
        { type: 'image', url: 'https://example.com/2.png', name: 'look-2.png', group_id: 'batch-a', group_name: '通勤穿搭' },
        { type: 'image', url: 'https://example.com/3.png', name: 'look-3.png', group_id: 'batch-b', group_name: '雨天穿搭' },
      ],
    })

    const galleries = wrapper.findAll('.chat-image-gallery')
    expect(galleries).toHaveLength(1)
    expect(galleries[0].text()).toContain('1/3')
    expect(wrapper.findAll('.chat-image-gallery__thumb')).toHaveLength(3)

    await wrapper.findAll('.chat-image-gallery__thumb')[2].trigger('click')

    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/3.png')
  })
})
