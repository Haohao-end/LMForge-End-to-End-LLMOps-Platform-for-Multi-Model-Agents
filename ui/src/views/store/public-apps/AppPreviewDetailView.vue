<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import AgentAppAbilityReadonly from '@/views/space/apps/components/AgentAppAbilityReadonly.vue'
import ModelConfigReadonly from '@/views/space/apps/components/ModelConfigReadonly.vue'
import PresetPromptTextareaReadonly from '@/views/space/apps/components/PresetPromptTextareaReadonly.vue'
import PublicPreviewDebugChat from './components/PublicPreviewDebugChat.vue'

type DraftAppConfigForm = {
  dialog_round?: number
  model_config?: Record<string, unknown>
  preset_prompt?: string
  mcp_bindings?: Array<Record<string, unknown>>
  skills?: Array<Record<string, unknown>>
  agent_bindings?: Array<Record<string, unknown>>
  long_term_memory?: { enable: boolean }
  suggested_after_answer?: { enable: boolean }
  opening_questions?: string[]
  opening_statement?: string
  text_to_speech?: {
    enable: boolean
    auto_play: boolean
    voice: string
  }
}

type AppPreview = {
  id?: string
  draft_app_config?: DraftAppConfigForm
}

const route = useRoute()
const { t } = useI18n()
const props = defineProps({
  app: {
    type: Object as () => AppPreview,
    default: () => ({}),
    required: true,
  },
})

const draftAppConfigForm = ref<DraftAppConfigForm>({})

watch(
  () => props.app,
  (newApp) => {
    if (newApp?.draft_app_config) {
      draftAppConfigForm.value = newApp.draft_app_config
    }
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <div class="flex flex-1 min-h-0 w-full flex-col bg-white overflow-hidden">
    <div class="grid flex-1 min-h-0 grid-cols-[minmax(0,26fr)_minmax(0,14fr)] w-full overflow-hidden">
      <div class="bg-gray-50 flex min-h-0 flex-col min-w-0 overflow-hidden">
        <div class="flex items-center h-16 border-b p-4 gap-4">
          <div class="text-lg text-gray-700">{{ t('publicApps.preview.appConfig') }}</div>
          <model-config-readonly
            :model_config="draftAppConfigForm.model_config"
          />
        </div>
        <div class="grid flex-1 min-h-0 grid-cols-[minmax(0,13fr)_minmax(0,12fr)] overflow-hidden">
          <div class="border-r py-4 min-w-0 overflow-hidden">
            <preset-prompt-textarea-readonly :preset_prompt="draftAppConfigForm.preset_prompt" />
          </div>
          <agent-app-ability-readonly class="min-w-0" :draft_app_config="draftAppConfigForm" />
        </div>
      </div>
      <div class="min-w-[404px] flex min-h-0 flex-col overflow-hidden">
        <div class="flex items-center justify-between border-b h-[64px] px-4">
          <div class="text-lg text-gray-700">{{ t('publicApps.preview.previewAndDebug') }}</div>
          <a-button size="mini" type="text" class="rounded-lg px-1 !text-blue-700" disabled>
            <template #icon>
              <icon-save />
            </template>
            {{ t('publicApps.preview.longTermMemory') }}
          </a-button>
        </div>
        <public-preview-debug-chat
          class="flex-1 min-h-0 overflow-hidden"
          :suggested_after_answer="draftAppConfigForm.suggested_after_answer"
          :opening_questions="draftAppConfigForm.opening_questions"
          :opening_statement="draftAppConfigForm.opening_statement"
          :text_to_speech="draftAppConfigForm.text_to_speech"
          :app="props.app"
          :app_id="String(route.params?.app_id)"
        />
      </div>
    </div>
  </div>
</template>
