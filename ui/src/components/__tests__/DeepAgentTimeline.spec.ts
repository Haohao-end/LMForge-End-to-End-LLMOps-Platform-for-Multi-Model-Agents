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

  it('renders finalized todo snapshots without active progress dots', () => {
    const wrapper = mountTimeline({
      thoughts: [
        {
          id: 'todo-step-1',
          event: QueueEvent.deepStep,
          thought: '待办事项已完成',
          tool: 'write_todos',
          tool_input: {
            todos: [
              { content: '规划章节结构', status: 'completed' },
              { content: '生成 Markdown 文件', status: 'completed' },
            ],
            timeline: {
              step_type: 'plan',
              status: 'success',
              title: '拆解任务',
              detail: '待办事项已完成',
            },
          },
        },
      ],
    })

    expect(wrapper.findAll('.deep-agent-todo-item')).toHaveLength(2)
    expect(wrapper.text()).toContain('规划章节结构')
    expect(wrapper.text()).toContain('生成 Markdown 文件')
    expect(wrapper.findAll('.deep-agent-todo__dot').every(dot => !dot.classes().includes('animate-pulse'))).toBe(true)
  })

  it('renders command and result previews for execute steps', () => {
    const wrapper = mountTimeline({
      thoughts: [
        {
          id: 'execute-step-1',
          event: QueueEvent.deepStep,
          thought: '正在执行代码',
          tool: 'execute',
          tool_input: {
            timeline: {
              step_type: 'tool',
              status: 'success',
              title: '执行代码',
              detail: '命令已执行',
              preview: 'python3 -c "print(1)"',
              preview_kind: 'command',
              result_preview: '1\n',
              result_kind: 'stdout',
              error_kind: '',
              recovered: false,
              recoverable: false,
              output_empty: false,
            },
          },
        },
      ],
    })

    expect(wrapper.text()).toContain('命令预览')
    expect(wrapper.text()).toContain('结果预览')
    expect(wrapper.text()).toContain('python3 -c "print(1)"')
    expect(wrapper.text()).toContain('1')
  })

  it('renders recoverable write_file warnings and recovered attachment states', () => {
    const warningWrapper = mountTimeline({
      thoughts: [
        {
          id: 'write-step-warning',
          event: QueueEvent.deepStep,
          thought: '检测到可恢复的写文件协议',
          tool: 'write_file',
          tool_input: {
            timeline: {
              step_type: 'artifact',
              status: 'warning',
              title: '写文件协议待修复',
              detail: '检测到可恢复的写文件协议，正在尝试恢复附件：SpaceX_IPO_Prospectus_Draft.txt',
              preview: 'write_file -> SpaceX_IPO_Prospectus_Draft.txt',
              preview_kind: 'protocol',
              result_preview: '',
              result_kind: 'artifact',
              error_kind: 'protocol_error',
              recovered: false,
              recoverable: true,
              output_empty: true,
            },
          },
        },
      ],
    })

    expect(warningWrapper.text()).toContain('可恢复协议错误')
    expect(warningWrapper.text()).toContain('协议预览')
    expect(warningWrapper.text()).toContain('无输出')
    expect(warningWrapper.text()).toContain('write_file -> SpaceX_IPO_Prospectus_Draft.txt')

    const recoveredWrapper = mountTimeline({
      thoughts: [
        {
          id: 'write-step-recovered',
          event: QueueEvent.deepStep,
          thought: '已将文件写入沙箱',
          tool: 'write_file',
          tool_input: {
            timeline: {
              step_type: 'artifact',
              status: 'success',
              title: '已自动修复并恢复附件',
              detail: '已将 SpaceX_IPO_Prospectus_Draft.txt 写入沙箱，准备重新扫描产物',
              preview: 'write_file -> SpaceX_IPO_Prospectus_Draft.txt',
              preview_kind: 'protocol',
              result_preview: '已写入 SpaceX_IPO_Prospectus_Draft.txt',
              result_kind: 'artifact',
              error_kind: 'protocol_error',
              recovered: true,
              recoverable: true,
              output_empty: false,
            },
          },
        },
      ],
    })

    expect(recoveredWrapper.text()).toContain('已自动修复并恢复附件')
    expect(recoveredWrapper.text()).toContain('结果预览')
    expect(recoveredWrapper.text()).toContain('已写入 SpaceX_IPO_Prospectus_Draft.txt')
  })
})
