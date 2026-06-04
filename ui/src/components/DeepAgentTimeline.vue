<script setup lang="ts">
import { computed, ref, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import { QueueEvent } from '@/config'
import { isImageArtifact, type ChatArtifact } from '@/views/shared/chat-output'
import ChatImageGallery from './ChatImageGallery.vue'

type TimelineThought = Record<string, any>

const props = defineProps({
  thoughts: {
    type: Array as PropType<TimelineThought[]>,
    default: () => [],
    required: true,
  },
  loading: { type: Boolean, default: false },
})
const { t } = useI18n()

const expanded = ref(true)

const stepTypeLabelMap: Record<string, string> = {
  plan: t('chat.deepTimeline.stepTypes.plan'),
  tool: t('chat.deepTimeline.stepTypes.tool'),
  subagent: t('chat.deepTimeline.stepTypes.subagent'),
  reflection: t('chat.deepTimeline.stepTypes.reflection'),
  artifact: t('chat.deepTimeline.stepTypes.artifact'),
}

const normalizeTodoStatus = (status: unknown) => {
  const normalized = String(status ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_')

  if (!normalized)
    return 'pending'

  const aliases: Record<string, string> = {
    completed: 'completed',
    complete: 'completed',
    done: 'completed',
    success: 'completed',
    succeeded: 'completed',
    finished: 'completed',
    error: 'error',
    failed: 'error',
    fail: 'error',
    failure: 'error',
    in_progress: 'in_progress',
    progress: 'in_progress',
    running: 'in_progress',
    working: 'in_progress',
    doing: 'in_progress',
    start: 'in_progress',
    pending: 'pending',
    todo: 'pending',
    to_do: 'pending',
    wait: 'pending',
    waiting: 'pending',
    not_started: 'pending',
  }

  return aliases[normalized] || 'pending'
}

const normalizeTodoItems = (todos: unknown): Array<Record<string, any>> => {
  if (!Array.isArray(todos))
    return []

  return todos
    .map((todo, index) => {
      if (todo && typeof todo === 'object') {
        const record = todo as Record<string, any>
        const content = String(
          record.content ?? record.text ?? record.description ?? record.title ?? record.name ?? '',
        ).trim()
        const title = String(record.title ?? record.name ?? content).trim()
        const rawStatus = String(record.status ?? '').trim()

        return {
          ...record,
          content: content || title,
          title: title || content,
          status: normalizeTodoStatus(record.status),
          ...(rawStatus ? { raw_status: rawStatus } : {}),
          position: index,
        }
      }

      const text = String(todo ?? '').trim()
      return {
        content: text,
        title: text,
        status: 'pending',
        position: index,
      }
    })
    .filter((todo) => String(todo.content || todo.title || '').trim())
}

const getPreviewLabel = (previewKind: string) => {
  if (previewKind === 'protocol')
    return t('chat.deepTimeline.protocolPreview')
  if (previewKind === 'command')
    return t('chat.deepTimeline.commandPreview')
  return t('chat.deepTimeline.preview')
}

const getResultPreviewLabel = (resultKind: string) => {
  if (resultKind === 'stdout')
    return t('chat.deepTimeline.resultPreview')
  if (resultKind === 'artifact')
    return t('chat.deepTimeline.resultPreview')
  return t('chat.deepTimeline.resultPreview')
}

const getStateLabel = (status: string, errorKind: string, recovered: boolean, recoverable: boolean) => {
  if (recovered)
    return t('chat.deepTimeline.autoRecoveredAttachment')
  if (status === 'warning' && errorKind === 'protocol_error' && recoverable)
    return t('chat.deepTimeline.recoverableProtocolIssue')
  if (status === 'error')
    return t('chat.deepTimeline.finalFailure')
  if (status === 'warning')
    return t('chat.deepTimeline.recoverableProtocolIssue')
  return ''
}

const timelineItems = computed(() => {
  return props.thoughts.map((thought, index) => {
    const toolInput = (thought.tool_input || {}) as Record<string, any>
    const timeline = (toolInput.timeline || {}) as Record<string, any>
    const artifact = (toolInput.artifact || null) as Record<string, any> | null
    const todos = normalizeTodoItems(timeline.todos || toolInput.todos || [])
    const renderKey = String(thought.id || `step-${index}`)
    const tool = String(thought.tool || '')
    const preview = String(timeline.preview || '')
    const previewKind = String(timeline.preview_kind || '')
    const resultPreview = String(timeline.result_preview || '')
    const resultKind = String(timeline.result_kind || '')
    const errorKind = String(timeline.error_kind || '')
    const recovered = Boolean(timeline.recovered)
    const recoverable = Boolean(timeline.recoverable)
    const outputEmpty = Boolean(timeline.output_empty)

    if (thought.event === QueueEvent.deepArtifactCreated && artifact) {
      return {
        id: renderKey,
        renderKey: `${renderKey}-artifact-${index}`,
        event: thought.event,
        position: Number(thought.position ?? index),
        title: artifact.name || t('chat.deepTimeline.generatedAttachment'),
        detail: artifact.url || '',
        technicalDetail: artifact.path || '',
        stepType: 'artifact',
        stepTypeLabel: stepTypeLabelMap.artifact,
        status: 'success',
        tool: 'artifact',
        latency: Number(thought.latency ?? 0),
        artifact,
        preview: '',
        previewKind: '',
        resultPreview: '',
        resultKind: '',
        errorKind: '',
        recovered: false,
        recoverable: false,
        outputEmpty: false,
        stateLabel: '',
      }
    }

    const stepType = String(timeline.step_type || 'tool')
    const status = String(timeline.status || 'success')
    const title = String(timeline.title || thought.tool || t('chat.deepTimeline.fallbackStepTitle'))
    const detail = String(timeline.detail || thought.thought || thought.observation || '')
    const technicalDetail = String(timeline.technical_detail || thought.observation || '')

    return {
      id: renderKey,
      renderKey: `${renderKey}-${stepType}-${tool || 'step'}-${index}`,
      event: thought.event,
      position: Number(thought.position ?? index),
      title,
      detail,
      technicalDetail,
      stepType,
      stepTypeLabel: stepTypeLabelMap[stepType] || stepType,
      status,
      tool,
      latency: Number(thought.latency ?? 0),
      artifact: null,
      preview,
      previewKind,
      resultPreview,
      resultKind,
      errorKind,
      recovered,
      recoverable,
      outputEmpty,
      stateLabel: getStateLabel(status, errorKind, recovered, recoverable),
      todos,
      showTodos: tool === 'write_todos' && todos.length > 0,
      todoCount: todos.length,
    }
  }).sort((left, right) => left.position - right.position)
})

const imageGalleryImages = computed(() => {
  const images: Array<{ name: string, url: string, mime_type?: string, extension?: string }> = []
  const seenUrls = new Set<string>()

  for (const item of timelineItems.value) {
    if (!item.artifact || !isImageArtifact(item.artifact as ChatArtifact))
      continue
    const url = String(item.artifact.url || '').trim()
    if (!url || seenUrls.has(url))
      continue
    seenUrls.add(url)
    images.push({
      name: String(item.artifact.name || ''),
      url,
      mime_type: String(item.artifact.mime_type || ''),
      extension: String(item.artifact.extension || ''),
    })
  }

  return images
})

const imageCount = computed(() => {
  return imageGalleryImages.value.length
})

const visibleTimelineItems = computed(() => {
  return timelineItems.value.filter((item) => {
    if (!item.artifact) return true
    return !isImageArtifact(item.artifact as ChatArtifact)
  })
})

const summaryText = computed(() => {
  const count = visibleTimelineItems.value.length + (imageGalleryImages.value.length > 0 ? 1 : 0)
  const activeTodo = [...visibleTimelineItems.value].reverse().find((item) => item.showTodos) || null
  if (activeTodo) {
    return t('chat.deepTimeline.todoSummary', { count: activeTodo.todoCount })
  }
  const active = [...visibleTimelineItems.value].reverse().find((item) => item.status === 'start') || null
  if (active) {
    return `${active.title}`
  }
  return count > 0
    ? t('chat.deepTimeline.totalSteps', { count })
    : t('chat.deepTimeline.empty')
})

const getStepDotClass = (status: string) => {
  if (status === 'success') return 'bg-emerald-500'
  if (status === 'error') return 'bg-rose-500'
  if (status === 'warning') return 'bg-amber-500'
  if (status === 'start' || status === 'stream') return 'bg-amber-500 animate-pulse'
  return 'bg-slate-300'
}

const getTodoDotClass = (status: string) => {
  if (status === 'completed') return 'bg-emerald-500'
  if (status === 'error') return 'bg-rose-500'
  if (status === 'in_progress') return 'bg-amber-500 animate-pulse'
  return 'bg-slate-300'
}
</script>

<template>
  <div class="deep-agent-timeline">
    <button
      type="button"
      class="deep-agent-timeline__header"
      @click="expanded = !expanded"
    >
      <div class="flex items-center gap-2 min-w-0">
        <div class="min-w-0">
          <div class="deep-agent-timeline__title">{{ t('chat.deepTimeline.title') }}</div>
          <div class="deep-agent-timeline__summary truncate">{{ summaryText }}</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="loading"
          class="text-[11px] text-amber-700"
        >{{ t('chat.deepTimeline.running') }}</span>
        <span
          :class="['deep-agent-timeline__caret', expanded ? 'rotate-180' : '']"
        >⌄</span>
      </div>
    </button>

    <div v-if="expanded" class="deep-agent-timeline__body">
      <div
        v-if="imageGalleryImages.length > 0"
        class="deep-agent-gallery"
      >
        <div class="deep-agent-gallery__header">
          <span class="deep-agent-gallery__label">{{ t('chat.deepTimeline.generatedImages') }}</span>
          <span class="deep-agent-gallery__count">{{ t('chat.deepTimeline.imageCount', { count: imageCount }) }}</span>
        </div>
        <chat-image-gallery
          :images="imageGalleryImages"
          :title="t('chat.deepTimeline.generatedImages')"
        />
      </div>

      <div
        v-for="item in visibleTimelineItems"
        :key="item.renderKey"
        class="deep-agent-step"
      >
        <div class="deep-agent-step__rail">
          <span :class="['deep-agent-step__dot', getStepDotClass(item.status)]"></span>
        </div>

        <div class="deep-agent-step__content">
          <div class="deep-agent-step__meta">
            <span class="deep-agent-step__name">{{ item.title }}</span>
            <span class="deep-agent-badge">{{ item.stepTypeLabel }}</span>
            <span
              v-if="item.stateLabel"
              :class="[
                'deep-agent-badge',
                item.status === 'error'
                  ? 'deep-agent-badge--danger'
                  : item.recovered
                    ? 'deep-agent-badge--success'
                    : 'deep-agent-badge--state',
              ]"
            >{{ item.stateLabel }}</span>
            <span v-if="item.latency > 0" class="deep-agent-step__latency">{{ item.latency.toFixed(2) }}s</span>
          </div>

          <div v-if="item.detail" class="deep-agent-step__detail">
            {{ item.detail }}
          </div>

          <div v-if="item.preview || item.resultPreview || item.errorKind || item.recovered" class="deep-agent-step__preview-block">
            <div v-if="item.preview" class="deep-agent-step__preview-section">
              <div class="deep-agent-step__preview-label">{{ getPreviewLabel(item.previewKind) }}</div>
              <pre>{{ item.preview }}</pre>
            </div>
            <div v-if="item.resultPreview || item.outputEmpty || item.recovered" class="deep-agent-step__preview-section">
              <div class="deep-agent-step__preview-label">{{ getResultPreviewLabel(item.resultKind) }}</div>
              <pre>{{ item.resultPreview || (item.outputEmpty ? t('chat.deepTimeline.noOutput') : '') }}</pre>
            </div>
          </div>

          <div v-if="item.showTodos && item.todos.length > 0" class="deep-agent-todo-list">
            <div
              v-for="todo in item.todos"
              :key="`${item.id}-todo-${todo.position}-${todo.title}`"
              class="deep-agent-todo-item"
            >
              <span :class="['deep-agent-todo__dot', getTodoDotClass(todo.status)]"></span>
              <span class="deep-agent-todo__text">{{ todo.content || todo.title }}</span>
            </div>
          </div>

          <div v-if="item.artifact" class="deep-agent-artifact">
            <div class="deep-agent-artifact__name">{{ item.artifact.name }}</div>
            <a-image
              v-if="isImageArtifact(item.artifact as ChatArtifact)"
              class="deep-agent-artifact__image"
              :src="item.artifact.url"
              :preview="true"
            />
            <div class="deep-agent-artifact__meta">
              <span>{{ item.artifact.extension || 'file' }}</span>
              <span v-if="Number(item.artifact.size || 0) > 0">{{ item.artifact.size }} bytes</span>
            </div>
            <a
              class="deep-agent-artifact__link"
              :href="item.artifact.url"
              target="_blank"
              rel="noreferrer"
            >
              {{ t('chat.deepTimeline.downloadAttachment') }}
            </a>
          </div>

          <details v-if="item.technicalDetail && item.technicalDetail !== item.detail" class="deep-agent-step__technical">
            <summary>{{ t('chat.deepTimeline.technicalDetails') }}</summary>
            <pre>{{ item.technicalDetail }}</pre>
          </details>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deep-agent-timeline {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.96);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 24px rgba(148, 163, 184, 0.08);
  overflow: hidden;
}

.deep-agent-timeline__header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  text-align: left;
}

.deep-agent-timeline__title {
  font-size: 13px;
  font-weight: 700;
  color: #1f2937;
}

.deep-agent-timeline__summary {
  font-size: 12px;
  color: #6b7280;
}

.deep-agent-timeline__caret {
  font-size: 16px;
  color: #6b7280;
  transition: transform 0.2s ease;
}

.deep-agent-timeline__body {
  padding: 0 14px 14px 14px;
}

.deep-agent-gallery {
  margin-bottom: 12px;
}

.deep-agent-gallery__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.deep-agent-gallery__label {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.deep-agent-gallery__count {
  font-size: 11px;
  color: #64748b;
}

.deep-agent-step {
  display: flex;
  gap: 10px;
  padding: 10px 0;
}

.deep-agent-step + .deep-agent-step {
  border-top: 1px dashed rgba(148, 163, 184, 0.28);
}

.deep-agent-step__rail {
  padding-top: 5px;
}

.deep-agent-step__dot {
  display: inline-flex;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.9);
  transition:
    background-color 0.24s ease,
    box-shadow 0.24s ease,
    transform 0.24s ease;
}

.deep-agent-step__content {
  min-width: 0;
  flex: 1;
}

.deep-agent-step__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.deep-agent-step__name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.deep-agent-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 11px;
  color: #475569;
  background: rgba(148, 163, 184, 0.14);
}

.deep-agent-badge--state {
  background: rgba(251, 191, 36, 0.14);
  color: #92400e;
}

.deep-agent-badge--success {
  background: rgba(16, 185, 129, 0.14);
  color: #047857;
}

.deep-agent-badge--danger {
  background: rgba(244, 63, 94, 0.14);
  color: #be123c;
}

.deep-agent-step__latency {
  font-size: 11px;
  color: #94a3b8;
}

.deep-agent-step__detail {
  margin-top: 6px;
  font-size: 12px;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}

.deep-agent-step__preview-block {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deep-agent-step__preview-section {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.86);
}

.deep-agent-step__preview-label {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 6px;
}

.deep-agent-step__preview-section pre {
  margin: 0;
  font-size: 12px;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}

.deep-agent-todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.58);
}

.deep-agent-todo-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.deep-agent-todo-item + .deep-agent-todo-item {
  padding-top: 8px;
  border-top: 1px dashed rgba(148, 163, 184, 0.24);
}

.deep-agent-todo__dot {
  flex-shrink: 0;
  display: inline-flex;
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.85);
  transition:
    background-color 0.24s ease,
    box-shadow 0.24s ease,
    transform 0.24s ease;
}

.deep-agent-todo__text {
  min-width: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}

.deep-agent-step__technical {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}

.deep-agent-step__technical summary {
  cursor: pointer;
  color: #64748b;
}

.deep-agent-step__technical pre {
  margin-top: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.04);
  white-space: pre-wrap;
  word-break: break-word;
}

.deep-agent-artifact {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  background: rgba(239, 246, 255, 0.92);
}

.deep-agent-artifact__name {
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
}

.deep-agent-artifact__image {
  margin-top: 8px;
  width: 100%;
  max-width: 320px;
  border-radius: 12px;
  overflow: hidden;
}

.deep-agent-artifact__meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
}

.deep-agent-artifact__link {
  display: inline-flex;
  margin-top: 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.deep-agent-artifact__link:hover {
  text-decoration: underline;
}
</style>
