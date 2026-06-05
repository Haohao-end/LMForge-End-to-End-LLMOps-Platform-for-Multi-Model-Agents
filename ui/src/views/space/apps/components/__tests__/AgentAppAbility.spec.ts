import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AgentAppAbility from '../AgentAppAbility.vue'
import AgentBindingsAbilityItem from '../abilities/AgentBindingsAbilityItem.vue'

vi.mock('../abilities/AgentBindingsAbilityItem.vue', () => ({
  default: {
    name: 'AgentBindingsAbilityItem',
    props: {
      app_id: {
        type: String,
        default: '',
      },
      agent_bindings: {
        type: Array,
        default: () => [],
      },
    },
    template: '<div class="agent-bindings-ability-item-stub" />',
  },
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/hooks/use-app', () => ({
  useUpdateDraftAppConfig: () => ({
    handleUpdateDraftAppConfig: vi.fn(),
  }),
}))

vi.mock('@arco-design/web-vue', () => ({
  Message: {
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const slotStub = {
  template: '<div><slot /><slot name="icon" /><slot name="content" /></div>',
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

const mountAbility = () => {
  return mount(AgentAppAbility, {
    props: {
      app_id: 'app-1',
      draft_app_config: {
        tools: [],
        mcp_bindings: [],
        mcp_tool_snapshots: [],
        skills: [],
        agent_bindings: [
          {
            app_id: 'agent-1',
            invoke_mode: 'tool',
            name: '客服助手',
            icon: '',
            description: '示例 Agent',
            source_scope: 'own',
            is_public: false,
            status: 'published',
            tool_name: '',
          },
        ],
        workflows: [],
        datasets: [],
        retrieval_config: {},
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
      stubs: {
        'a-collapse': slotStub,
        'a-collapse-item': collapseItemStub,
        'a-button': slotStub,
        'a-avatar': slotStub,
        'a-tag': slotStub,
        'a-tooltip': slotStub,
        'a-modal': slotStub,
        'a-input-search': slotStub,
        'a-spin': slotStub,
        'a-empty': slotStub,
        'a-space': slotStub,
        'tools-ability-item': slotStub,
        'mcp-bindings-ability-item': slotStub,
        'skills-ability-item': slotStub,
        'workflows-ability-item': slotStub,
        'datasets-ability-item': slotStub,
        'long-term-memory-ability-item': slotStub,
        'opening-ability-item': slotStub,
        'suggested-after-answer-ability-item': slotStub,
        'speech-to-text-ability-item': slotStub,
        'text-to-speech-abiliti-item': slotStub,
        'review-config-ability-item': slotStub,
        'icon-down': slotStub,
        'icon-right': slotStub,
        'icon-plus': slotStub,
        'icon-delete': slotStub,
        'icon-apps': slotStub,
        'icon-storage': slotStub,
        'icon-question-circle': slotStub,
      },
    },
  })
}

describe('AgentAppAbility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the agent bindings ability item in edit mode', async () => {
    const wrapper = mountAbility()

    await flushPromises()

    const agentBindings = wrapper.findComponent(AgentBindingsAbilityItem)
    expect(agentBindings.exists()).toBe(true)
    expect(agentBindings.props('agent_bindings')).toHaveLength(1)
    expect(wrapper.find('.agent-bindings-ability-item-stub').exists()).toBe(true)
  })
})
