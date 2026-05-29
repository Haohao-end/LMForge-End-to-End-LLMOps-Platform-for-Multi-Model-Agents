import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { ref } from 'vue'

import PreviewDebugChat from '../PreviewDebugChat.vue'

const mocks = vi.hoisted(() => ({
  route: {
    params: { app_id: 'app-1' },
    query: {},
    fullPath: '/space/apps/app-1',
  } as Record<string, any>,
  replace: vi.fn().mockResolvedValue(undefined),
  query: { value: '' },
  suggestedQuestions: { value: [] as string[] },
  messages: { value: [] as Record<string, any>[] },
  debugChatLoading: { value: false },
  deleteDebugConversationLoading: { value: false },
  getDebugConversationMessagesWithPageLoading: { value: false },
  stopDebugChatLoading: { value: false },
  audioToTextLoading: { value: false },
  isRecording: { value: false },
  uploadFileLoading: { value: false },
  handleDebugChat: vi.fn().mockResolvedValue(undefined),
  handleDeleteDebugConversation: vi.fn().mockResolvedValue(undefined),
  loadDebugConversationMessages: vi.fn().mockResolvedValue(undefined),
  handleStopDebugChat: vi.fn().mockResolvedValue(undefined),
  handleGenerateSuggestedQuestions: vi.fn().mockResolvedValue(undefined),
  handleAudioToText: vi.fn().mockResolvedValue(undefined),
  triggerFileInput: vi.fn(),
  handleFileChange: vi.fn(),
  adjustQueryTextareaHeight: vi.fn(),
  restoreQueryDraft: vi.fn(),
  startAudioStream: vi.fn(),
  stopAudioStream: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({
    replace: mocks.replace,
  }),
}))

vi.mock('@/hooks/use-chat-query-input', () => ({
  useChatQueryInput: () => ({
    query: mocks.query,
    queryTextareaRef: ref<HTMLTextAreaElement | null>(null),
    adjustQueryTextareaHeight: mocks.adjustQueryTextareaHeight,
    restoreQueryDraft: mocks.restoreQueryDraft,
  }),
}))

vi.mock('@/hooks/use-chat-image-upload', () => ({
  useChatImageUpload: () => ({
    triggerFileInput: mocks.triggerFileInput,
    handleFileChange: mocks.handleFileChange,
  }),
}))

vi.mock('@/hooks/use-audio', () => ({
  useAudioToText: () => ({
    loading: mocks.audioToTextLoading,
    text: ref(''),
    handleAudioToText: mocks.handleAudioToText,
  }),
  useAudioPlayer: () => ({
    startAudioStream: mocks.startAudioStream,
    stopAudioStream: mocks.stopAudioStream,
  }),
}))

vi.mock('@/hooks/use-ai', () => ({
  useGenerateSuggestedQuestions: () => ({
    suggested_questions: mocks.suggestedQuestions,
    handleGenerateSuggestedQuestions: mocks.handleGenerateSuggestedQuestions,
  }),
}))

vi.mock('@/hooks/use-app', () => ({
  useDebugChat: () => ({
    loading: mocks.debugChatLoading,
    handleDebugChat: mocks.handleDebugChat,
  }),
  useDeleteDebugConversation: () => ({
    loading: mocks.deleteDebugConversationLoading,
    handleDeleteDebugConversation: mocks.handleDeleteDebugConversation,
  }),
  useGetDebugConversationMessagesWithPage: () => ({
    loading: mocks.getDebugConversationMessagesWithPageLoading,
    messages: mocks.messages,
    loadDebugConversationMessages: mocks.loadDebugConversationMessages,
  }),
  useStopDebugChat: () => ({
    loading: mocks.stopDebugChatLoading,
    handleStopDebugChat: mocks.handleStopDebugChat,
  }),
}))

vi.mock('@/stores/account', () => ({
  useAccountStore: () => ({
    account: {
      id: 'account-1',
      name: 'Tester',
      avatar: '',
    },
  }),
}))

vi.mock('@/services/upload-file', () => ({
  uploadImage: vi.fn(),
}))

vi.mock('@arco-design/web-vue', () => ({
  Message: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}))

describe('PreviewDebugChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.route.query = {}
    mocks.route.params = { app_id: 'app-1' }
  })

  it('renders the light dynamic glass container for app debug chat', async () => {
    const wrapper = shallowMount(PreviewDebugChat, {
      global: {
        stubs: {
          'scroll-navigator': {
            template: '<div class="scroll-navigator-stub"><slot /></div>',
          },
          'chat-composer': true,
          'chat-conversation-skeleton': true,
          'dynamic-scroller': {
            template: '<div class="dynamic-scroller-stub"><slot /></div>',
          },
          'dynamic-scroller-item': {
            template: '<div class="dynamic-scroller-item-stub"><slot /></div>',
          },
          'human-message': true,
          'ai-message': true,
          'a-avatar': true,
          'a-button': true,
          'icon-poweroff': true,
          AiDynamicBackground: {
            template: '<div class="ai-dynamic-background-stub"></div>',
          },
        },
      },
      props: {
        app: {
          name: 'OpenAgent',
          icon: '',
        },
        suggested_after_answer: { enable: true },
        opening_statement: '',
        opening_questions: [],
        capabilities: {},
        text_to_speech: {
          enable: false,
          auto_play: false,
          voice: 'alex',
        },
      },
    })

    await flushPromises()

    expect(wrapper.find('.space-apps-debug-chat').exists()).toBe(true)
    expect(wrapper.find('.space-apps-debug-chat__ambient').exists()).toBe(true)
    expect(wrapper.find('.space-apps-debug-chat__veil').exists()).toBe(true)
    expect(wrapper.find('.space-apps-debug-chat__surface').exists()).toBe(true)
  })
})
