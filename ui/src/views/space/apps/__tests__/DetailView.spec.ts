import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DetailView from '../DetailView.vue'

const mocks = vi.hoisted(() => ({
  route: {
    params: { app_id: 'app-1' },
  } as any,
  draftAppConfigForm: null as null | { value: Record<string, any> },
  loadDraftAppConfig: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRoute: () => mocks.route,
  }
})

vi.mock('@/hooks/use-app', async () => {
  const { ref } = await import('vue')
  if (!mocks.draftAppConfigForm) {
    mocks.draftAppConfigForm = ref({
      dialog_round: 3,
      model_config: { provider: 'deepseek', model: 'deepseek-chat', parameters: {} },
      capabilities: { image_input: { enabled: false } },
      preset_prompt: 'prompt',
      long_term_memory: { enable: false },
      opening_statement: '',
      opening_questions: [],
      suggested_after_answer: { enable: false },
      review_config: { enable: false },
      datasets: [],
      retrieval_config: { retrieval_strategy: 'semantic', k: 10, score: 0.5 },
      tools: [],
      mcp_bindings: [],
      mcp_tool_snapshots: [],
      workflows: [],
      speech_to_text: { enable: false },
      text_to_speech: { enable: false, voice: 'alex', auto_play: false },
    })
  }
  return {
    useGetDraftAppConfig: () => ({
      loading: ref(false),
      draftAppConfigForm: mocks.draftAppConfigForm,
      loadDraftAppConfig: mocks.loadDraftAppConfig,
    }),
  }
})

describe('DetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const draftAppConfigForm = mocks.draftAppConfigForm
    if (!draftAppConfigForm) {
      throw new Error('draftAppConfigForm mock not initialized')
    }
    draftAppConfigForm.value = {
      dialog_round: 3,
      model_config: { provider: 'deepseek', model: 'deepseek-chat', parameters: {} },
      capabilities: { image_input: { enabled: false } },
      preset_prompt: 'prompt',
      long_term_memory: { enable: false },
      opening_statement: '',
      opening_questions: [],
      suggested_after_answer: { enable: false },
      review_config: { enable: false },
      datasets: [],
      retrieval_config: { retrieval_strategy: 'semantic', k: 10, score: 0.5 },
      tools: [],
      mcp_bindings: [],
      mcp_tool_snapshots: [],
      workflows: [],
      speech_to_text: { enable: false },
      text_to_speech: { enable: false, voice: 'alex', auto_play: false },
    }
  })

  it('reloads draft config when the selected model changes', async () => {
    shallowMount(DetailView, {
      props: {
        app: {
          id: 'app-1',
        },
      },
      global: {
        stubs: {
          'agent-app-ability': true,
          'model-config': true,
          'preset-prompt-textarea': true,
          'preview-debug-chat': true,
          'preview-debug-header': true,
        },
      },
    })

    await flushPromises()
    expect(mocks.loadDraftAppConfig).toHaveBeenCalledTimes(1)

    const draftAppConfigForm = mocks.draftAppConfigForm
    if (!draftAppConfigForm) {
      throw new Error('draftAppConfigForm mock not initialized')
    }

    draftAppConfigForm.value.model_config = {
      provider: 'openai',
      model: 'gpt-4o-mini',
      parameters: {},
    }

    await flushPromises()

    expect(mocks.loadDraftAppConfig).toHaveBeenCalledTimes(2)
  })
})
