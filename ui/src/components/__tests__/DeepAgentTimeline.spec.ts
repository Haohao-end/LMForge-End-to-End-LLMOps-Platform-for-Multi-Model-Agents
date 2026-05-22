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
})
