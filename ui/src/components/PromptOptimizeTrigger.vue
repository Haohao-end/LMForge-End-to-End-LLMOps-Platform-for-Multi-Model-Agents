<script setup lang="ts">
import { type PropType, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useI18n } from 'vue-i18n'
import { useOptimizePrompt } from '@/hooks/use-ai'

const props = defineProps({
  buttonLabel: { type: String, default: '' },
  buttonClass: { type: String, default: 'rounded-lg px-2' },
  buttonSize: {
    type: String as PropType<'mini' | 'small' | 'medium' | 'large'>,
    default: 'mini',
  },
  applyButtonText: { type: String, default: '' },
  inputPlaceholder: { type: String, default: '' },
})
const emits = defineEmits<{
  apply: [prompt: string]
}>()
const { t } = useI18n()
const popupVisible = ref(false)
const originPrompt = ref('')
const { loading, optimize_prompt, handleOptimizePrompt } = useOptimizePrompt()

const handleSubmit = async () => {
  if (originPrompt.value.trim() === '') {
    Message.warning(t('chat.promptOptimize.emptyOrigin'))
    return
  }

  await handleOptimizePrompt(originPrompt.value)
}

const handleApply = () => {
  if (optimize_prompt.value.trim() === '') {
    Message.warning(t('chat.promptOptimize.emptyOptimized'))
    return
  }

  emits('apply', optimize_prompt.value)
  popupVisible.value = false
}
</script>

<template>
  <a-trigger
    v-model:popup-visible="popupVisible"
    :trigger="['click']"
    position="bl"
    :popup-translate="[0, 8]"
  >
      <a-button :size="props.buttonSize" :class="props.buttonClass">
        <template #icon>
          <icon-sync />
        </template>
      {{ props.buttonLabel || t('chat.promptOptimize.button') }}
    </a-button>
    <template #content>
      <a-card class="rounded-lg w-[422px]">
        <div class="flex flex-col">
          <div v-if="optimize_prompt" class="mb-4 flex flex-col">
            <div class="max-h-[321px] overflow-scroll scrollbar-w-none mb-2 text-gray-700 whitespace-pre-line">
              {{ optimize_prompt }}
            </div>
            <a-space v-if="!loading">
              <a-button
                size="small"
                type="primary"
                class="rounded-lg"
                @click="handleApply"
              >
                {{ props.applyButtonText || t('chat.promptOptimize.apply') }}
              </a-button>
              <a-button size="small" class="rounded-lg" @click="popupVisible = false">
                {{ t('chat.promptOptimize.close') }}
              </a-button>
            </a-space>
          </div>
          <div class="h-[50px] flex items-center gap-2 px-4 flex-1 border border-gray-200 rounded-full">
            <input
              v-model="originPrompt"
              type="text"
              class="flex-1 outline-0"
              :placeholder="props.inputPlaceholder || t('chat.promptOptimize.placeholder')"
            />
            <a-button :loading="loading" type="text" shape="circle" @click="handleSubmit">
              <template #icon>
                <icon-send :size="16" class="!text-blue-700" />
              </template>
            </a-button>
          </div>
        </div>
      </a-card>
    </template>
  </a-trigger>
</template>
