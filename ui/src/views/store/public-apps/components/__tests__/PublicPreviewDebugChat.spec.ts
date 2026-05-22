import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'

import PublicPreviewDebugChat from '@/views/store/public-apps/components/PublicPreviewDebugChat.vue'

const mocks = vi.hoisted(() => ({
  route: {
    params: { app_id: 'app-1' },
    query: {},
  } as any,
  queryRef: null as null | { value: string },
  getPublicAppA2aConversationMessages: vi.fn().mockResolvedValue({
    data: [],
  }),
  sendPublicAppA2aMessage: vi.fn().mockResolvedValue(undefined),
  triggerFileInput: vi.fn(),
  handleFileChange: vi.fn(),
  uploadImage: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
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

vi.mock('@/hooks/use-chat-query-input', async () => {
  const { ref } = await import('vue')
  if (!mocks.queryRef) {
    mocks.queryRef = ref('')
  }
  return {
    useChatQueryInput: () => ({
      query: mocks.queryRef,
      queryTextareaRef: ref<HTMLTextAreaElement | null>(null),
      adjustQueryTextareaHeight: vi.fn(),
    }),
  }
})

vi.mock('@/hooks/use-chat-image-upload', () => ({
  useChatImageUpload: () => ({
    triggerFileInput: mocks.triggerFileInput,
    handleFileChange: mocks.handleFileChange,
  }),
}))

vi.mock('@/hooks/use-audio', async () => {
  const { ref } = await import('vue')
  return {
    useAudioToText: () => ({
      loading: ref(false),
    }),
  }
})

vi.mock('@/services/public-app', () => ({
  getPublicAppA2aConversationMessages: mocks.getPublicAppA2aConversationMessages,
  sendPublicAppA2aMessage: mocks.sendPublicAppA2aMessage,
}))

vi.mock('@/services/upload-file', () => ({
  uploadImage: mocks.uploadImage,
}))

vi.mock('@arco-design/web-vue', () => ({
  Message: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}))

const chatComposerStub = defineComponent({
  name: 'ChatComposer',
  props: {
    modelValue: { type: String, default: '' },
    showUploadButton: { type: Boolean, default: false },
    showImagePreviews: { type: Boolean, default: false },
    uploadDisabled: { type: Boolean, default: false },
  },
  template: '<div />',
})

describe('PublicPreviewDebugChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    if (mocks.queryRef) {
      mocks.queryRef.value = ''
    }
  })

  it('renders the upload entry in disabled state for public preview', async () => {
    const wrapper = shallowMount(PublicPreviewDebugChat, {
      props: {
        app: {
          draft_app_config: {
            capabilities: {
              image_input: { enabled: false },
            },
          },
        },
        suggested_after_answer: { enable: true },
        opening_statement: '',
        opening_questions: [],
        text_to_speech: { enable: false },
      },
      global: {
        stubs: {
          ChatComposer: chatComposerStub,
          ChatConversationSkeleton: true,
          ChatMessageTimeline: true,
          HumanMessage: true,
          'a-avatar': true,
        },
      },
    })

    await flushPromises()

    const composer = wrapper.getComponent(chatComposerStub)
    expect(composer.props('showUploadButton')).toBe(true)
    expect(composer.props('showImagePreviews')).toBe(true)
    expect(composer.props('uploadDisabled')).toBe(true)
  })
})
