<script setup lang="ts">
/**
 * DeepThinkingPanel — 深度思考过程展示面板
 *
 * 功能：
 * - 流式显示 deep_thinking 事件的思考内容
 * - 默认展开（思考中），思考完成后可折叠
 * - 支持脉冲动画表示正在思考
 * - 内容过长时内部滚动
 */
import { computed, ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  /** 思考内容文本（流式累积） */
  thought: { type: String, default: '' },
  /** 耗时（秒），0 表示还在思考中 */
  latency: { type: Number, default: 0 },
  /** 是否正在流式输出（控制动画） */
  loading: { type: Boolean, default: false },
})
const { t } = useI18n()

const isExpanded = ref(true)
const contentRef = ref<HTMLElement | null>(null)

/** 思考是否已完成 */
const isFinished = computed(() => !props.loading && props.latency > 0)

/** 折叠/展开标题文字 */
const toggleLabel = computed(() =>
  isExpanded.value
    ? isFinished.value ? t('chat.deepThinking.collapse') : t('chat.deepThinking.thinking')
    : t('chat.deepThinking.finished', { latency: props.latency.toFixed(1) }),
)

/** 内容区 class */
const contentClass = computed(() => [
  'deep-thinking-content text-xs text-gray-600 leading-relaxed whitespace-pre-wrap break-words',
  isExpanded.value ? 'deep-thinking-content--expanded' : 'deep-thinking-content--collapsed',
])

/** 思考中：内容有变化时自动滚到底部 */
watch(
  () => props.thought,
  async () => {
    if (!isExpanded.value || !contentRef.value) return
    await nextTick()
    contentRef.value.scrollTop = contentRef.value.scrollHeight
  },
)

/** 思考完成时自动折叠 */
watch(isFinished, (finished) => {
  if (finished) isExpanded.value = false
})
</script>

<template>
  <div class="deep-thinking-panel">
    <!-- 标题栏：点击折叠/展开 -->
    <button
      type="button"
      class="deep-thinking-header"
      :title="toggleLabel"
      @click="isExpanded = !isExpanded"
    >
      <!-- 左：脑波图标 + 文字 -->
      <div class="flex items-center gap-1.5 min-w-0">
        <!-- 思考中脉冲圆点 -->
        <span
          v-if="!isFinished"
          class="deep-thinking-pulse"
          aria-hidden="true"
        />
        <!-- 思考完成对勾 -->
        <svg
          v-else
          class="h-3.5 w-3.5 text-violet-500 flex-shrink-0"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="deep-thinking-label truncate">{{ toggleLabel }}</span>
      </div>

      <!-- 右：latency + 折叠箭头 -->
      <div class="flex items-center gap-1.5 flex-shrink-0 ml-2">
        <span v-if="isFinished" class="text-[10px] text-violet-400/80">
          {{ latency.toFixed(1) }}s
        </span>
        <svg
          :class="['h-3.5 w-3.5 text-gray-400 transition-transform duration-200', isExpanded ? 'rotate-180' : '']"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </button>

    <!-- 内容区：可折叠 -->
    <Transition name="deep-thinking-slide">
      <div
        v-if="isExpanded"
        ref="contentRef"
        :class="contentClass"
      >
        <span v-if="!thought" class="text-gray-400 italic">{{ t('chat.deepThinking.waiting') }}</span>
        <span v-else>{{ thought }}</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.deep-thinking-panel {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(139, 92, 246, 0.2);
  background: linear-gradient(
    135deg,
    rgba(245, 243, 255, 0.9) 0%,
    rgba(237, 233, 254, 0.7) 100%
  );
  backdrop-filter: blur(8px);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.08);
}

.deep-thinking-header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s ease;
}

.deep-thinking-header:hover {
  background-color: rgba(139, 92, 246, 0.06);
}

.deep-thinking-label {
  font-size: 12px;
  font-weight: 500;
  color: #6d28d9;
}

/* 思考中脉冲动画圆点 */
.deep-thinking-pulse {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #8b5cf6;
  flex-shrink: 0;
  animation: deep-thinking-breathe 1.2s ease-in-out infinite;
}

@keyframes deep-thinking-breathe {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.85);
    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0);
  }
}

/* 内容区 */
.deep-thinking-content {
  padding: 0 12px 10px 12px;
  overflow-y: auto;
  color: #4c1d95;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 11.5px;
  line-height: 1.65;
}

.deep-thinking-content--expanded {
  max-height: 240px;
}

.deep-thinking-content--collapsed {
  max-height: 0;
  overflow: hidden;
}

/* 折叠过渡动画 */
.deep-thinking-slide-enter-active,
.deep-thinking-slide-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease, padding 0.2s ease;
  overflow: hidden;
}

.deep-thinking-slide-enter-from,
.deep-thinking-slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.deep-thinking-slide-enter-to,
.deep-thinking-slide-leave-from {
  max-height: 240px;
  opacity: 1;
}

/* 滚动条 */
.deep-thinking-content::-webkit-scrollbar {
  width: 3px;
}
.deep-thinking-content::-webkit-scrollbar-track {
  background: transparent;
}
.deep-thinking-content::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.25);
  border-radius: 2px;
}
.deep-thinking-content::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 92, 246, 0.45);
}
</style>
