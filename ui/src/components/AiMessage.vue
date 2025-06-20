<script setup lang="ts">
import { computed, type PropType } from 'vue'
import MarkdownIt from 'markdown-it'
import DotFlashing from '@/components/DotFlashing.vue'
import AgentThought from './AgentThought.vue'
import 'github-markdown-css'

// 1.定义自定义组件所需数据
const props = defineProps({
  app: {
    type: Object,
    default: () => {
      return {}
    },
    required: true,
  },
  answer: { type: String, default: '', required: true },
  loading: { type: Boolean, default: false, required: false },
  latency: { type: Number, default: 0, required: false },
  total_token_count: { type: Number, default: 0, required: false },
  agent_thoughts: {
    type: Array as PropType<Record<string, any>[]>,
    default: () => [],
    required: true,
  },
  suggested_questions: { type: Array as PropType<string[]>, default: () => [], required: false },
  message_class: { type: String, default: '!bg-gray-100', required: false },
})
const emits = defineEmits(['selectSuggestedQuestion'])
const md = MarkdownIt()
const compiledMarkdown = computed(() => {
  return md.render(props.answer)
})
</script>

<template>
  <div class="flex gap-2">
    <!-- 左侧图标 -->
    <a-avatar
      v-if="props.app?.icon"
      :size="30"
      shape="circle"
      class="flex-shrink-0"
      :image-url="props.app?.icon"
    />
    <a-avatar v-else :size="30" shape="circle" class="flex-shrink-0 bg-blue-700">
      <icon-apps />
    </a-avatar>
    <!-- 右侧名称与消息 -->
    <div class="flex-1 flex flex-col items-start gap-2">
      <!-- 应用名称 -->
      <div class="text-gray-700 font-bold">{{ props.app?.name }}</div>
      <!-- 推理步骤 -->
      <agent-thought :agent_thoughts="props.agent_thoughts" :loading="props.loading" />
      <!-- AI消息 -->
      <div
        v-if="props.loading && props.answer.trim() === ''"
        :class="`${props.message_class} border border-gray-200 text-gray-700 px-4 py-3 rounded-2xl break-all`"
      >
        <dot-flashing />
      </div>
      <div
        v-else
        :class="`${props.message_class} markdown-body border border-gray-200 text-gray-700 px-4 py-3 rounded-2xl break-all`"
        v-html="compiledMarkdown"
      ></div>
      <!-- 消息展示与操作 -->
      <div class="flex items-center justify-between">
        <!-- 消息数据额外展示 -->
        <a-space class="text-xs">
          <template #split>
            <a-divider direction="vertical" class="m-0" />
          </template>
          <div class="flex items-center gap-1 text-gray-500">
            <icon-check />
            {{ props.latency.toFixed(2) }}s
          </div>
          <div class="text-gray-500">{{ props.total_token_count }} Tokens</div>
        </a-space>
        <!-- 操作 -->
      </div>
      <!-- 建议问题列表 -->
      <div v-if="props.suggested_questions.length > 0" class="flex flex-col gap-2">
        <div
          v-for="(suggested_question, idx) in props.suggested_questions"
          :key="idx"
          class="px-4 py-1.5 border rounded-lg text-gray-700 cursor-pointer bg-white hover:bg-gray-50"
          @click="() => emits('selectSuggestedQuestion', suggested_question)"
        >
          {{ suggested_question }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
