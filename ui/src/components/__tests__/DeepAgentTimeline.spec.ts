import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { QueueEvent } from '@/config'

import DeepAgentTimeline from '../DeepAgentTimeline.vue'

describe('DeepAgentTimeline.vue', () => {
  const mountTimeline = (props: Record<string, unknown> = {}) =>
    mount(DeepAgentTimeline, {
      props: {
        thoughts: [],
        ...props,
      },
      global: {
        stubs: {
          'a-image': {
            props: ['src', 'preview'],
            template: '<div class="image-stub" :data-src="src"></div>',
          },
        },
      },
    })

  it('groups image artifacts into a gallery and keeps non-image artifacts separate', async () => {
    const wrapper = mountTimeline({
      thoughts: [
        {
          id: 'step-1',
          event: QueueEvent.deepStep,
          thought: '正在生成图片',
          tool: 'qwen_image_text_to_image',
          tool_input: {
            timeline: {
              step_type: 'tool',
              status: 'success',
              title: '生成图片',
              detail: '图像生成完成',
            },
          },
          latency: 1.2,
        },
        {
          id: 'artifact-1',
          event: QueueEvent.deepArtifactCreated,
          thought: 'img-1.png',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'img-1.png',
              url: 'https://example.com/1.png',
              extension: 'png',
              mime_type: 'image/png',
            },
          },
        },
        {
          id: 'artifact-2',
          event: QueueEvent.deepArtifactCreated,
          thought: 'img-2.png',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'img-2.png',
              url: 'https://example.com/2.png',
              extension: 'png',
              mime_type: 'image/png',
            },
          },
        },
        {
          id: 'artifact-3',
          event: QueueEvent.deepArtifactCreated,
          thought: 'plan.pdf',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'plan.pdf',
              url: 'https://example.com/plan.pdf',
              extension: 'pdf',
              mime_type: 'application/pdf',
            },
          },
        },
      ],
    })

    expect(wrapper.find('.chat-image-gallery').exists()).toBe(true)
    expect(wrapper.text()).toContain('生成图片')
    expect(wrapper.text()).toContain('2 张')
    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/1.png')
    expect(wrapper.findAll('.chat-image-gallery__thumb')).toHaveLength(2)
    expect(wrapper.text()).toContain('plan.pdf')
    expect(wrapper.text()).toContain('下载附件')

    await wrapper.findAll('.chat-image-gallery__thumb')[1].trigger('click')

    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/2.png')
  })

  it('renders one unified gallery for images from different groups', async () => {
    const wrapper = mountTimeline({
      thoughts: [
        {
          id: 'artifact-1',
          event: QueueEvent.deepArtifactCreated,
          thought: 'img-1.png',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'img-1.png',
              url: 'https://example.com/1.png',
              extension: 'png',
              mime_type: 'image/png',
              group_id: 'batch-a',
              group_name: '通勤穿搭',
            },
          },
        },
        {
          id: 'artifact-2',
          event: QueueEvent.deepArtifactCreated,
          thought: 'img-2.png',
          tool: 'artifact',
          tool_input: {
            artifact: {
              name: 'img-2.png',
              url: 'https://example.com/2.png',
              extension: 'png',
              mime_type: 'image/png',
              group_id: 'batch-b',
              group_name: '雨天穿搭',
            },
          },
        },
      ],
    })

    const galleries = wrapper.findAll('.chat-image-gallery')
    expect(galleries).toHaveLength(1)
    expect(galleries[0].text()).toContain('1/2')
    expect(wrapper.findAll('.chat-image-gallery__thumb')).toHaveLength(2)

    await wrapper.findAll('.chat-image-gallery__thumb')[1].trigger('click')

    expect(wrapper.find('.image-stub').attributes('data-src')).toBe('https://example.com/2.png')
  })

  it('keeps the write_todos list visible while todo statuses update from start to success', async () => {
    const startThought = {
      id: 'step-1',
      event: QueueEvent.deepStep,
      thought: '正在拆解任务',
      tool: 'write_todos',
      tool_input: {
        timeline: {
          step_type: 'plan',
          status: 'start',
          title: '拆解任务',
          detail: '共 4 项待办',
          todos: [
            { content: '收集景点', status: 'pending' },
            { title: '预订酒店', status: 'in_progress' },
            { content: '规划路线', status: 'pending' },
            { content: '联系导游', status: 'pending' },
          ],
        },
      },
      latency: 0.8,
    }
    const successThought = {
      ...startThought,
      thought: '拆解完成',
      tool_input: {
        timeline: {
          step_type: 'plan',
          status: 'success',
          title: '拆解任务',
          detail: '待办已写入',
          todos: [
            { content: '收集景点', status: 'completed' },
            { title: '预订酒店', status: 'completed' },
            { content: '规划路线', status: 'completed' },
            { content: '联系导游', status: 'completed' },
          ],
        },
      },
      latency: 1.1,
    }

    const wrapper = mountTimeline({
      thoughts: [startThought],
    })

    expect(wrapper.attributes('style')).toBeUndefined()
    expect(wrapper.find('.deep-agent-timeline__brain').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('🧠')
    expect(wrapper.text()).toContain('共 4 项待办')
    expect(wrapper.text()).toContain('收集景点')
    expect(wrapper.text()).toContain('预订酒店')
    expect(wrapper.text()).toContain('规划路线')
    expect(wrapper.text()).toContain('联系导游')
    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(4)

    const startDots = wrapper.findAll('.deep-agent-todo__dot')
    expect(startDots).toHaveLength(4)
    expect(startDots[0].classes()).toContain('bg-slate-300')
    expect(startDots[1].classes()).toContain('bg-amber-500')
    expect(startDots[2].classes()).toContain('bg-slate-300')
    expect(startDots[3].classes()).toContain('bg-slate-300')

    await wrapper.setProps({
      thoughts: [successThought],
    })

    expect(wrapper.text()).toContain('待办已写入')
    expect(wrapper.text()).toContain('收集景点')
    expect(wrapper.text()).toContain('预订酒店')
    expect(wrapper.text()).toContain('规划路线')
    expect(wrapper.text()).toContain('联系导游')
    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(4)

    const successDots = wrapper.findAll('.deep-agent-todo__dot')
    expect(successDots).toHaveLength(4)
    successDots.forEach((dot) => {
      expect(dot.classes()).toContain('bg-emerald-500')
    })
  })

  it('renders normalized todo rows with colored status dots on a white timeline card', () => {
    const wrapper = mountTimeline({
      thoughts: [
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
                { content: '规划路线', status: 'completed' },
                { content: '联系导游', status: 'completed' },
              ],
            },
          },
          latency: 1.1,
        },
      ],
    })

    expect(wrapper.attributes('style')).toBeUndefined()
    expect(wrapper.find('.deep-agent-timeline__brain').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('🧠')
    expect(wrapper.text()).toContain('待办已写入')
    expect(wrapper.text()).toContain('收集景点')
    expect(wrapper.text()).toContain('预订酒店')
    expect(wrapper.text()).toContain('规划路线')
    expect(wrapper.text()).toContain('联系导游')
    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(4)

    const todoDots = wrapper.findAll('.deep-agent-todo__dot')
    expect(todoDots).toHaveLength(4)
    expect(todoDots[0].classes()).toContain('bg-emerald-500')
    expect(todoDots[1].classes()).toContain('bg-emerald-500')
    expect(todoDots[2].classes()).toContain('bg-emerald-500')
    expect(todoDots[3].classes()).toContain('bg-emerald-500')
  })

  it('renders warning status as an amber reminder dot', () => {
    const wrapper = mountTimeline({
      thoughts: [
        {
          id: 'step-1',
          event: QueueEvent.deepStep,
          thought: '最终检查',
          tool: 'self_check',
          tool_input: {
            timeline: {
              step_type: 'reflection',
              status: 'warning',
              title: '最终一致性检查',
              detail: '已完成轻量自检：答案未泄漏沙箱本地路径。提醒：本次未生成附件，但附件是可选补充材料，文本结果已可直接使用。',
            },
          },
          latency: 0.6,
        },
      ],
    })

    expect(wrapper.text()).toContain('提醒')
    const dots = wrapper.findAll('.deep-agent-step__dot')
    expect(dots).toHaveLength(1)
    expect(dots[0].classes()).toContain('bg-amber-500')
  })
})
