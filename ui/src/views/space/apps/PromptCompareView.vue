<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useI18n } from 'vue-i18n'
import HumanMessage from '@/components/HumanMessage.vue'
import AiMessage from '@/components/AiMessage.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import PromptOptimizeTrigger from '@/components/PromptOptimizeTrigger.vue'
import { useGetDraftAppConfig, useUpdateDraftAppConfig } from '@/hooks/use-app'
import { useAccountStore } from '@/stores/account'
import { getErrorMessage } from '@/utils/error'
import { promptCompareChat, stopPromptCompareChat } from '@/services/app'
import type { PromptCompareChatRequest } from '@/models/app'
import PromptCompareModelConfigTrigger from './components/PromptCompareModelConfigTrigger.vue'
import {
  applyChatStreamEvent,
  type ChatThought,
  type StreamState,
} from '@/views/shared/chat-stream'
import { normalizeMessageMetrics, type MessageMetrics } from '@/views/shared/chat-metrics'

type LaneKey = 'baseline' | 'candidate'

type CompareMessage = {
  id: string
  conversation_id: string
  query: string
  image_urls: string[]
  answer: string
  answer_parts: Array<Record<string, unknown>>
  artifacts: Array<Record<string, unknown>>
  total_token_count: number
  latency: number
  agent_thoughts: ChatThought[]
  suggested_questions: string[]
  created_at: number
}

type CompareLane = {
  key: LaneKey
  title: string
  description: string
  preset_prompt: string
  model_config: {
    provider: string
    model: string
    parameters: Record<string, unknown>
  }
  lane_id: string
  messages: CompareMessage[]
  loading: boolean
  task_id: string
}

const route = useRoute()
const { t } = useI18n()
const props = defineProps({
  app: {
    type: Object,
    default: () => ({}),
    required: true,
  },
})
const accountStore = useAccountStore()
const query = ref('')
const stopLoading = ref(false)
const appliedPresetPrompt = ref('')
const laneScrollRefs = ref<Record<LaneKey, HTMLDivElement | null>>({
  baseline: null,
  candidate: null,
})
const lanes = ref<CompareLane[]>([])
const { draftAppConfigForm, loadDraftAppConfig } = useGetDraftAppConfig()
const { handleUpdateDraftAppConfig } = useUpdateDraftAppConfig()

const appId = computed(() => String(route.params?.app_id || ''))
const anyLaneLoading = computed(() => lanes.value.some((lane) => lane.loading))

const createLocalUuid = () => {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const createCompareMessage = (value: string): CompareMessage => {
  return {
    id: '',
    conversation_id: '',
    query: value,
    image_urls: [],
    answer: '',
    answer_parts: [],
    artifacts: [],
    total_token_count: 0,
    latency: 0,
    agent_thoughts: [],
    suggested_questions: [],
    created_at: Date.now(),
  }
}

const cloneModelConfig = (value: Record<string, unknown>) => {
  return JSON.parse(JSON.stringify(value || {})) as CompareLane['model_config']
}

const createLaneApp = (title: string) => {
  return {
    ...props.app,
    name: title,
  }
}

const setLaneScrollRef = (laneKey: LaneKey, element: HTMLDivElement | null) => {
  laneScrollRefs.value[laneKey] = element
}

const scrollLaneToBottom = (laneKey: LaneKey) => {
  nextTick(() => {
    const element = laneScrollRefs.value[laneKey]
    if (!element) return
    element.scrollTop = element.scrollHeight
  })
}

const initializeLanes = () => {
  const modelConfig = (draftAppConfigForm.value.model_config || {}) as CompareLane['model_config']
  const presetPrompt = String(draftAppConfigForm.value.preset_prompt || '')
  appliedPresetPrompt.value = presetPrompt
  lanes.value = [
    {
      key: 'baseline',
      title: t('appStudio.promptCompare.baselineTitle'),
      description: t('appStudio.promptCompare.baselineDescription'),
      preset_prompt: presetPrompt,
      model_config: cloneModelConfig(modelConfig),
      lane_id: createLocalUuid(),
      messages: [],
      loading: false,
      task_id: '',
    },
    {
      key: 'candidate',
      title: t('appStudio.promptCompare.candidateTitle'),
      description: t('appStudio.promptCompare.candidateDescription'),
      preset_prompt: presetPrompt,
      model_config: cloneModelConfig(modelConfig),
      lane_id: createLocalUuid(),
      messages: [],
      loading: false,
      task_id: '',
    },
  ]
}

const getHistoryPayload = (lane: CompareLane) => {
  return lane.messages
    .filter((message) => message.query.trim() !== '' && message.answer.trim() !== '')
    .map((message) => ({
      query: message.query,
      answer: message.answer,
    }))
}

const handleApplyPrompt = async (lane: CompareLane) => {
  if (lane.preset_prompt.trim() === '') {
    Message.warning(t('appStudio.promptCompare.promptEmpty'))
    return
  }

  await handleUpdateDraftAppConfig(appId.value, {
    preset_prompt: lane.preset_prompt,
  })
  appliedPresetPrompt.value = lane.preset_prompt
}

const isAppliedPromptLane = (lane: CompareLane) => lane.preset_prompt === appliedPresetPrompt.value

const validateBeforeSubmit = () => {
  if (query.value.trim() === '') {
    Message.warning(t('appStudio.promptCompare.queryEmpty'))
    return false
  }

  for (const lane of lanes.value) {
    if (lane.preset_prompt.trim() === '') {
      Message.warning(t('appStudio.promptCompare.promptEmpty'))
      return false
    }
    if (!lane.model_config?.provider || !lane.model_config?.model) {
      Message.warning(t('appStudio.promptCompare.modelNotSelected', { title: lane.title }))
      return false
    }
  }

  if (anyLaneLoading.value) {
    Message.warning(t('appStudio.promptCompare.requestInProgress'))
    return false
  }

  return true
}

const streamLane = async (lane: CompareLane, userQuery: string) => {
  const history = getHistoryPayload(lane)
  const currentMessage = createCompareMessage(userQuery)
  lane.messages.push(currentMessage)
  lane.loading = true
  lane.task_id = ''
  scrollLaneToBottom(lane.key)

  let streamState: StreamState = {
    position: 0,
    message_id: '',
    task_id: '',
    conversation_id: lane.lane_id,
  }
  const requestStartAt = Date.now()

  try {
    const resp = await promptCompareChat(
      appId.value,
      {
        lane_id: lane.lane_id,
        query: userQuery,
        preset_prompt: lane.preset_prompt,
        model_config: lane.model_config,
        history,
      } satisfies PromptCompareChatRequest,
      (eventResponse) => {
        const streamResult = applyChatStreamEvent(
          currentMessage,
          eventResponse,
          streamState,
        )
        streamState = streamResult.state
        if (streamState.task_id) {
          lane.task_id = streamState.task_id
        }
        if (streamResult.didUpdate) {
          scrollLaneToBottom(lane.key)
        }
      },
    )

    const apiResp = resp as { code?: unknown; message?: unknown } | void
    if (apiResp && apiResp.code && apiResp.code !== 'success') {
      throw new Error(String(apiResp.message || t('appStudio.promptCompare.debugFailed')))
    }
  } catch (error) {
    currentMessage.answer = getErrorMessage(error, t('appStudio.promptCompare.debugFailed'))
  } finally {
    lane.loading = false
    lane.task_id = ''
    normalizeMessageMetrics(currentMessage as MessageMetrics, Math.max(Date.now() - requestStartAt, 0))
    scrollLaneToBottom(lane.key)
  }
}

const handleSubmit = async () => {
  if (!validateBeforeSubmit()) return

  const userQuery = query.value.trim()
  query.value = ''
  await Promise.all(lanes.value.map((lane) => streamLane(lane, userQuery)))
}

const handleStop = async () => {
  const taskIds = lanes.value
    .map((lane) => lane.task_id)
    .filter((taskId) => taskId.trim() !== '')

  if (!taskIds.length) return

  try {
    stopLoading.value = true
    await Promise.all(taskIds.map((taskId) => stopPromptCompareChat(appId.value, taskId)))
  } finally {
    stopLoading.value = false
  }
}

const handleClear = () => {
  if (anyLaneLoading.value) {
    Message.warning(t('appStudio.promptCompare.clearWhileRunning'))
    return
  }

  lanes.value = lanes.value.map((lane) => ({
    ...lane,
    lane_id: createLocalUuid(),
    messages: [],
    task_id: '',
    loading: false,
  }))
}

onMounted(async () => {
  await loadDraftAppConfig(appId.value)
  initializeLanes()
})
</script>

<template>
  <div class="flex-1 min-h-0 overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(219,234,254,0.9),_rgba(248,250,252,1)_40%,_rgba(255,255,255,1)_100%)]">
    <div class="grid h-full min-h-0 gap-5 p-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div class="compare-editor-scroll min-h-0 overflow-y-auto pr-2">
        <div class="space-y-4">
          <div
            v-for="lane in lanes"
            :key="lane.key"
            class="rounded-2xl border border-white/70 bg-white/85 p-5 shadow-sm backdrop-blur"
          >
            <div class="flex flex-col gap-3 2xl:flex-row 2xl:items-start 2xl:justify-between">
              <div>
                <div class="text-base font-semibold text-gray-800">{{ lane.title }}</div>
                <div class="mt-1 text-sm text-gray-500">{{ lane.description }}</div>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <prompt-compare-model-config-trigger
                  :model_config="lane.model_config"
                  @update:model_config="
                    (value) => {
                      lane.model_config = value
                    }
                  "
                />
                <prompt-optimize-trigger
                  :button-label="t('chat.promptOptimize.button')"
                  :apply-button-text="t('chat.promptOptimize.applyToCurrentInput')"
                  @apply="
                    (value) => {
                      lane.preset_prompt = value
                    }
                  "
                />
              </div>
            </div>

            <div class="mt-3">
              <markdown-editor
                :model-value="lane.preset_prompt"
                :max-length="5000"
                min-height="420px"
                toolbar-variant="compact"
                default-mode="edit"
                @update:model-value="
                  (value) => {
                    lane.preset_prompt = value
                  }
                "
              />
            </div>

            <div class="mt-4 flex justify-end">
              <a-button
                v-if="!isAppliedPromptLane(lane)"
                type="primary"
                class="rounded-lg"
                @click="handleApplyPrompt(lane)"
              >
                {{ t('appStudio.promptCompare.applyAndUpdate') }}
              </a-button>
              <div
                v-else
                class="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-600"
              >
                <icon-check />
                {{ t('appStudio.promptCompare.selected') }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-white/70 bg-white/80 shadow-sm backdrop-blur">
        <div class="grid min-h-0 flex-1 gap-px bg-gray-100 xl:grid-cols-2">
          <div
            v-for="lane in lanes"
            :key="`chat-${lane.key}`"
            class="min-h-0 flex flex-col bg-white"
          >
            <div class="flex items-center justify-between border-b border-gray-100 px-3 py-2.5">
              <div>
                <div class="text-sm font-semibold text-gray-800">{{ lane.title }}</div>
                <div class="text-xs text-gray-500">
                  {{ lane.model_config.provider }} · {{ lane.model_config.model }}
                </div>
              </div>
              <a-tag :color="lane.loading ? 'arcoblue' : 'gray'" bordered>
                {{ lane.loading ? t('appStudio.promptCompare.generating') : t('appStudio.promptCompare.ready') }}
              </a-tag>
            </div>

            <div
              :ref="(el) => setLaneScrollRef(lane.key, el as HTMLDivElement | null)"
              class="compare-output-scroll flex-1 min-h-0 overflow-y-auto px-3 py-3"
            >
              <div v-if="lane.messages.length === 0" class="flex h-full items-center justify-center">
                <a-empty :description="t('appStudio.promptCompare.emptyLane')" />
              </div>
              <div v-else class="flex flex-col gap-6">
                <div v-for="message in lane.messages" :key="`${lane.key}-${message.created_at}-${message.id || message.query}`" class="flex flex-col gap-6">
                  <human-message :account="accountStore.account" :query="message.query" :image_urls="[]" />
                  <ai-message
                    :app="createLaneApp(lane.title)"
                    :enable_text_to_speech="false"
                    :message_id="message.id"
                    :answer="message.answer"
                    :answer_parts="message.answer_parts || []"
                    :artifacts="message.artifacts || []"
                    :loading="lane.loading && message === lane.messages[lane.messages.length - 1]"
                    :latency="message.latency"
                    :total_token_count="message.total_token_count"
                    :agent_thoughts="message.agent_thoughts"
                    :show_agent_thought="true"
                    :agent_thought_default_visible="false"
                    :agent_thought_follow_latest="false"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-gray-100 px-4 py-3">
          <div class="rounded-[28px] border border-gray-200 bg-white px-4 py-3 shadow-sm">
            <textarea
              v-model="query"
              rows="4"
              class="w-full resize-none border-0 bg-transparent text-gray-700 outline-none"
              :placeholder="t('appStudio.promptCompare.queryPlaceholder')"
              @keydown.enter.exact.prevent="handleSubmit"
            />
            <div class="mt-3 flex items-center justify-between gap-3">
              <div class="text-xs text-gray-500">
                {{ t('appStudio.promptCompare.keyboardHint') }}
              </div>
              <a-space :size="8">
                <a-button class="rounded-lg" :disabled="anyLaneLoading" @click="handleClear">
                  {{ t('appStudio.promptCompare.clearCompare') }}
                </a-button>
                <a-button
                  class="rounded-lg"
                  :loading="stopLoading"
                  :disabled="!anyLaneLoading"
                  @click="handleStop"
                >
                  {{ t('appStudio.promptCompare.stopResponse') }}
                </a-button>
                <a-button
                  type="primary"
                  class="rounded-lg"
                  :loading="anyLaneLoading"
                  @click="handleSubmit"
                >
                  <template #icon>
                    <icon-send />
                  </template>
                  {{ t('appStudio.promptCompare.send') }}
                </a-button>
              </a-space>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.compare-editor-scroll {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.compare-editor-scroll::-webkit-scrollbar {
  display: none;
}

.compare-output-scroll {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.compare-output-scroll::-webkit-scrollbar {
  display: none;
}
</style>
