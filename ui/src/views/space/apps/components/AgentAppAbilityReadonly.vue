<script setup lang="ts">
import { computed } from 'vue'
import { apiPrefix } from '@/config'
import type { McpBinding } from '@/models/app'
import { resolveMcpBindingStatus } from './abilities/mcp-status'

// 只读版本的应用能力组件
const props = defineProps({
  draft_app_config: { type: Object, required: true },
})

const defaultActivateKeys = [
  'tools',
  'mcp_bindings',
  'skills',
  'agent_bindings',
  'workflows',
  'datasets',
  'long_term_memory',
  'opening',
  'suggested_after_answer',
  'review_config',
  'speech_to_text',
  'text_to_speech',
]

// 计算各项能力的状态
const toolsCount = computed(() => props.draft_app_config?.tools?.length || 0)
const mcpBindingsCount = computed(() => props.draft_app_config?.mcp_bindings?.length || 0)
const mcpToolSnapshots = computed(() => props.draft_app_config?.mcp_tool_snapshots || [])
const skillsCount = computed(() => props.draft_app_config?.skills?.length || 0)
const agentBindingsCount = computed(() => props.draft_app_config?.agent_bindings?.length || 0)
const workflowsCount = computed(() => props.draft_app_config?.workflows?.length || 0)
const datasetsCount = computed(() => props.draft_app_config?.datasets?.length || 0)
const longTermMemoryEnabled = computed(() => props.draft_app_config?.long_term_memory?.enable || false)
const openingStatementEnabled = computed(() => !!props.draft_app_config?.opening_statement)
const openingQuestionsCount = computed(() => props.draft_app_config?.opening_questions?.length || 0)
const suggestedAfterAnswerEnabled = computed(() => props.draft_app_config?.suggested_after_answer?.enable || false)
const speechToTextEnabled = computed(() => props.draft_app_config?.speech_to_text?.enable || false)
const textToSpeechEnabled = computed(() => props.draft_app_config?.text_to_speech?.enable || false)
const reviewConfigEnabled = computed(() => props.draft_app_config?.review_config?.enable || false)

const getMcpBindingStatus = (binding: Partial<McpBinding>) => {
  return resolveMcpBindingStatus(binding as Pick<
    McpBinding,
    'name' | 'url' | 'transport' | 'command' | 'provider_key' | 'enabled'
  >, mcpToolSnapshots.value)
}

// 统一处理图标地址，兼容绝对地址、相对地址以及 /api 路径
const normalizeIconUrl = (icon: string = '') => {
  if (!icon) return ''
  if (icon.startsWith('data:') || /^https?:\/\//.test(icon)) return icon
  const fallbackOrigin = globalThis.location?.origin ?? 'http://localhost'
  const apiUrl = new URL(apiPrefix, fallbackOrigin)
  const basePath = apiUrl.pathname.replace(/\/+$/, '')
  let path = icon.startsWith('/') ? icon : `/${icon}`

  // 本地开发常见：后端实际无 /api 前缀，但返回了 /api/xxx
  if (path.startsWith('/api/') && !basePath.startsWith('/api')) {
    path = path.replace(/^\/api/, '')
  }

  if (basePath && basePath !== '/' && !path.startsWith(`${basePath}/`)) {
    if (path.startsWith('/api/')) {
      path = path.replace(/^\/api/, '')
    }
    return `${apiUrl.origin}${basePath}${path}`
  }

  return `${apiUrl.origin}${path}`
}

const avatarPalettes = [
  ['#334155', '#0f172a'],
  ['#0369a1', '#1d4ed8'],
  ['#047857', '#0f766e'],
  ['#c2410c', '#d97706'],
  ['#be123c', '#e11d48'],
  ['#0f766e', '#14b8a6'],
]

const hashString = (value: string) => {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 33 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

const getBindingAvatarText = (binding: Pick<McpBinding, 'label' | 'name' | 'provider_key'>) => {
  const source = (binding.label || binding.name || binding.provider_key || 'M').trim()
  const latinParts = source.match(/[A-Za-z0-9]+/g)
  if (latinParts && latinParts.length > 0) {
    return latinParts
      .slice(0, 2)
      .map((item) => item[0]?.toUpperCase())
      .join('')
  }

  const chineseParts = source.match(/[\u4e00-\u9fff]/g)
  if (chineseParts && chineseParts.length > 0) {
    return chineseParts.slice(0, 2).join('')
  }

  return source.slice(0, 2).toUpperCase()
}

const getBindingAvatarStyle = (binding: Pick<McpBinding, 'provider_key' | 'category' | 'label'>) => {
  const palette = avatarPalettes[hashString(`${String(binding.provider_key || '').trim()}:${String(binding.category || '').trim()}:${String(binding.label || '').trim()}`) % avatarPalettes.length]
  return {
    background: `linear-gradient(135deg, ${palette[0]} 0%, ${palette[1]} 100%)`,
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.15)',
  }
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-141px)] min-w-0 w-full overflow-hidden">
    <!-- 应用能力标题 -->
    <div class="p-4 flex items-center justify-between">
      <div class="text-gray-700 font-bold">应用能力</div>
      <a-tag color="orange" size="small">预览模式</a-tag>
    </div>
    <!-- 应用能力列表 -->
    <div class="flex-1 min-w-0 overflow-y-auto overflow-x-hidden scrollbar-w-none">
      <a-collapse :bordered="false" :default-active-key="defaultActivateKeys" class="app-ability-readonly w-full min-w-0">
        <template #expand-icon="{ active }">
          <icon-down v-if="active" />
          <icon-right v-else />
        </template>

        <!-- 扩展插件 -->
        <a-collapse-item key="tools" header="扩展插件" class="app-ability-item">
          <div v-if="toolsCount > 0" class="space-y-2">
            <div
              v-for="(tool, index) in props.draft_app_config.tools"
              :key="index"
              class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar :size="32" shape="square" class="rounded-lg flex-shrink-0">
                <img v-if="tool.provider?.icon" :src="normalizeIconUrl(tool.provider.icon)" />
                <icon-apps v-else />
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-700 truncate">
                  {{ tool.tool?.label || tool.tool?.name || '未命名工具' }}
                </div>
                <div class="text-xs text-gray-500 truncate">
                  {{ tool.provider?.label || tool.provider?.name || '未知提供者' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置扩展插件</div>
        </a-collapse-item>

        <!-- MCP -->
        <a-collapse-item key="mcp_bindings" header="MCP" class="app-ability-item">
          <div v-if="mcpBindingsCount > 0" class="space-y-2">
            <div
              v-for="(binding, index) in (props.draft_app_config.mcp_bindings || [])"
              :key="index"
              class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar
                :size="34"
                shape="square"
                class="shrink-0 overflow-hidden"
                :style="binding.icon ? { backgroundColor: '#f3f4f6' } : getBindingAvatarStyle(binding)"
              >
                <img
                  v-if="binding.icon"
                  :src="normalizeIconUrl(binding.icon)"
                  :alt="binding.label || binding.name"
                  class="w-full h-full object-cover"
                />
                <span v-else class="text-white font-semibold text-[12px] tracking-wide">
                  {{ getBindingAvatarText(binding) }}
                </span>
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-700 truncate">
                  {{ binding.name || '未命名 MCP 绑定' }}
                </div>
                <div class="text-xs text-gray-500 truncate">
                  {{ binding.description || '无描述' }}
                </div>
                <div class="text-xs text-gray-400 truncate">
                  {{ binding.transport || 'streamable_http' }} · {{ binding.url || binding.command || '未配置地址' }}
                </div>
              </div>
              <div class="flex items-center gap-1 flex-shrink-0">
                <a-tag :color="getMcpBindingStatus(binding).color" size="small">
                  {{ getMcpBindingStatus(binding).label }}
                </a-tag>
                <a-tooltip
                  v-if="getMcpBindingStatus(binding).show_help && getMcpBindingStatus(binding).tooltip"
                  :content="getMcpBindingStatus(binding).tooltip"
                  position="top"
                >
                  <icon-question-circle class="text-gray-400 text-sm" />
                </a-tooltip>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置 MCP</div>
        </a-collapse-item>

        <!-- Skills -->
        <a-collapse-item key="skills" header="Skills" class="app-ability-item">
          <div v-if="skillsCount > 0" class="space-y-2">
            <div
              v-for="(skill, index) in props.draft_app_config.skills"
              :key="index"
              class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar :size="32" shape="square" class="rounded-lg flex-shrink-0">
                <img v-if="skill.icon" :src="normalizeIconUrl(skill.icon)" />
                <icon-storage v-else />
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-700 truncate">
                  {{ skill.label || skill.name || '未命名技能' }}
                </div>
                <div class="text-xs text-gray-500 truncate">
                  {{ skill.source_key || skill.name }}
                  <template v-if="skill.tool_count > 0"> · {{ skill.tool_count }} 个工具</template>
                  <template v-if="skill.executor_type"> · {{ skill.executor_type }}</template>
                </div>
                <div class="text-xs text-gray-400 truncate">
                  {{ skill.readme || skill.description || '无描述' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置 Skills</div>
        </a-collapse-item>

        <!-- Agent 子应用 -->
        <a-collapse-item key="agent_bindings" header="Agent 子应用" class="app-ability-item">
          <div v-if="agentBindingsCount > 0" class="space-y-2">
            <div
              v-for="(binding, index) in props.draft_app_config.agent_bindings"
              :key="index"
              class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar :size="32" shape="square" class="rounded-lg flex-shrink-0">
                <img v-if="binding.icon" :src="normalizeIconUrl(binding.icon)" />
                <icon-apps v-else />
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="text-sm font-medium text-gray-700 truncate">
                    {{ binding.name || '未命名 Agent' }}
                  </div>
                  <a-tag :color="binding.invoke_mode === 'a2a' ? 'arcoblue' : 'orange'" size="small">
                    {{ binding.invoke_mode === 'a2a' ? 'A2A' : 'Tool' }}
                  </a-tag>
                </div>
                <div class="text-xs text-gray-500 truncate">
                  {{ binding.source_scope === 'public' ? '应用广场' : '我的应用' }}
                  <template v-if="binding.is_public"> · 公开应用</template>
                  <template v-else> · 私有应用</template>
                </div>
                <div class="text-xs text-gray-400 truncate">
                  {{ binding.description || '无描述' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置 Agent 子应用</div>
        </a-collapse-item>

        <!-- 工作流 -->
        <a-collapse-item key="workflows" header="工作流" class="app-ability-item">
          <div v-if="workflowsCount > 0" class="space-y-2">
            <div
              v-for="(workflow, index) in props.draft_app_config.workflows"
              :key="index"
              class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar :size="32" shape="square" class="rounded-lg flex-shrink-0">
                <img v-if="workflow.icon" :src="workflow.icon" />
                <icon-apps v-else />
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-700 truncate">
                  {{ workflow.name || '未命名工作流' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置工作流</div>
        </a-collapse-item>

        <!-- 知识库 -->
        <a-collapse-item key="datasets" header="知识库" class="app-ability-item">
          <div v-if="datasetsCount > 0" class="space-y-2">
            <div
              v-for="(dataset, index) in props.draft_app_config.datasets"
              :key="index"
              class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <a-avatar :size="32" shape="square" class="rounded-lg flex-shrink-0">
                <icon-storage />
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-700 truncate">
                  {{ dataset.name || '未命名知识库' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 text-sm">未配置知识库</div>
        </a-collapse-item>

        <!-- 长期记忆召回 -->
        <a-collapse-item key="long_term_memory" header="长期记忆召回" class="app-ability-item">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-700">状态</span>
            <a-tag :color="longTermMemoryEnabled ? 'green' : 'gray'" size="small">
              {{ longTermMemoryEnabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>
        </a-collapse-item>

        <!-- 对话开场白 -->
        <a-collapse-item key="opening" header="对话开场白" class="app-ability-item">
          <div class="space-y-3">
            <div v-if="openingStatementEnabled" class="p-3 bg-gray-50 rounded-lg">
              <div class="text-xs text-gray-500 mb-1">开场白</div>
              <div class="text-sm text-gray-700 whitespace-pre-wrap">
                {{ props.draft_app_config.opening_statement }}
              </div>
            </div>
            <div v-if="openingQuestionsCount > 0" class="space-y-2">
              <div class="text-xs text-gray-500">开场问题 ({{ openingQuestionsCount }})</div>
              <div
                v-for="(question, index) in props.draft_app_config.opening_questions"
                :key="index"
                class="p-2 bg-gray-50 rounded text-sm text-gray-700"
              >
                {{ question }}
              </div>
            </div>
            <div v-if="!openingStatementEnabled && openingQuestionsCount === 0" class="text-gray-400 text-sm">
              未配置对话开场白
            </div>
          </div>
        </a-collapse-item>

        <!-- 回答后生成建议问题 -->
        <a-collapse-item key="suggested_after_answer" header="回答后生成建议问题" class="app-ability-item">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-700">状态</span>
            <a-tag :color="suggestedAfterAnswerEnabled ? 'green' : 'gray'" size="small">
              {{ suggestedAfterAnswerEnabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>
        </a-collapse-item>

        <!-- 语音输入 -->
        <a-collapse-item key="speech_to_text" header="语音输入" class="app-ability-item">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-700">状态</span>
            <a-tag :color="speechToTextEnabled ? 'green' : 'gray'" size="small">
              {{ speechToTextEnabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>
        </a-collapse-item>

        <!-- 语音输出 -->
        <a-collapse-item key="text_to_speech" header="语音输出" class="app-ability-item">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-700">状态</span>
            <a-tag :color="textToSpeechEnabled ? 'green' : 'gray'" size="small">
              {{ textToSpeechEnabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>
        </a-collapse-item>

        <!-- 内容审核 -->
        <a-collapse-item key="review_config" header="内容审核" class="app-ability-item">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-700">状态</span>
            <a-tag :color="reviewConfigEnabled ? 'green' : 'gray'" size="small">
              {{ reviewConfigEnabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>
        </a-collapse-item>
      </a-collapse>
    </div>
  </div>
</template>

<style>
.app-ability-readonly .app-ability-item {
  width: 100%;
  min-width: 0;

  .arco-collapse-item-header {
    background-color: transparent;
    border: none;
  }

  .arco-collapse-item-content {
    padding-left: 16px;
  }
}
</style>
