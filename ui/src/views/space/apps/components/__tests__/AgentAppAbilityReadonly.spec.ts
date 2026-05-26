import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AgentAppAbilityReadonly from '../AgentAppAbilityReadonly.vue'

vi.mock('@arco-design/web-vue', () => ({
  Message: {
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const slotStub = {
  template: '<div><slot /></div>',
}

const collapseItemStub = {
  props: {
    header: {
      type: String,
      default: '',
    },
  },
  template: '<div><div>{{ header }}</div><slot /></div>',
}

const globalStubs = {
  'a-collapse': slotStub,
  'a-collapse-item': collapseItemStub,
  'a-avatar': slotStub,
  'a-tag': slotStub,
  'a-tooltip': slotStub,
  'icon-down': slotStub,
  'icon-right': slotStub,
  'icon-question-circle': slotStub,
  'icon-apps': slotStub,
  'icon-storage': slotStub,
}

const makeBinding = (overrides: Record<string, unknown> = {}) => ({
  name: '12306-mcp',
  description: '12306 车票查询 MCP',
  transport: 'streamable_http',
  url: 'https://mcp.api-inference.modelscope.net/fbc1920197624e/mcp',
  command: '',
  enabled: true,
  headers: [],
  tool_names: [],
  timeout_seconds: 30,
  args: [],
  env: {},
  provider_key: 'catalog::QEpvb29vb2svMTIzMDYtbWNw',
  source_type: 'catalog',
  source_key: '@Joooook/12306-mcp',
  source_url: 'https://www.modelscope.cn/mcp/servers/@Joooook/12306-mcp',
  label: '12306 车票查询 MCP',
  icon: 'https://example.com/mcp.png',
  category: 'productivity',
  ...overrides,
})

const makeSnapshot = (overrides: Record<string, unknown> = {}) => ({
  binding_identity: 'catalog::QEpvb29vb2svMTIzMDYtbWNw',
  binding_hash: 'binding-hash',
  binding: makeBinding(),
  status: 'ready',
  tool_definitions: [{}],
  tool_names: ['query_train_info'],
  tool_count: 1,
  schema_hash: 'schema-hash',
  last_attempt_at: 1710000000,
  last_success_at: 1710000000,
  last_error: '',
  retry_count: 0,
  retryable: false,
  ...overrides,
})

describe('AgentAppAbilityReadonly', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders MCP bindings with normalized icon output', async () => {
    const wrapper = mount(AgentAppAbilityReadonly, {
      props: {
        draft_app_config: {
          tools: [],
          mcp_bindings: [makeBinding()],
          mcp_tool_snapshots: [makeSnapshot()],
          skills: [],
          agent_bindings: [],
          workflows: [],
          datasets: [],
          long_term_memory: { enable: false },
          opening_statement: '',
          opening_questions: [],
          suggested_after_answer: { enable: false },
          speech_to_text: { enable: false },
          text_to_speech: { enable: false },
          review_config: { enable: false },
        },
      },
      global: {
        stubs: globalStubs,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('MCP')
    expect(wrapper.text()).toContain('12306-mcp')

    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('https://example.com/mcp.png')
  })
})
