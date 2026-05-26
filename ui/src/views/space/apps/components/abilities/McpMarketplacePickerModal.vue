<script setup lang="ts">
import { computed, onMounted, ref, watch, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import { apiPrefix } from '@/config'
import ResourceCardDescription from '@/components/ResourceCardDescription.vue'
import { getErrorMessage } from '@/utils/error'
import { formatTimestampShort } from '@/utils/time-formatter'
import {
  getPublicMcpCategories,
  getPublicMcpProvidersWithPage,
} from '@/services/mcp'
import type { McpBinding, McpCategory, McpProvider } from '@/models/mcp'

type PaginatorState = {
  total_page: number
  total_record: number
  current_page: number
  page_size: number
}

const PAGE_SIZE = 50

const props = defineProps({
  visible: { type: Boolean, default: false },
  selected_bindings: {
    type: Array as PropType<McpBinding[]>,
    default: () => [],
  },
})

const emits = defineEmits(['update:visible', 'select'])

const loading = ref(false)
const categories = ref<McpCategory[]>([])
const providers = ref<McpProvider[]>([])
const selectedCategory = ref('all')
const searchWord = ref('')
const paginator = ref<PaginatorState>({
  total_page: 0,
  total_record: 0,
  current_page: 0,
  page_size: PAGE_SIZE,
})

const hideModal = () => emits('update:visible', false)

const avatarPalettes = [
  ['#334155', '#0f172a'],
  ['#0369a1', '#1d4ed8'],
  ['#047857', '#0f766e'],
  ['#c2410c', '#d97706'],
  ['#be123c', '#e11d48'],
  ['#0f766e', '#14b8a6'],
]

const FALLBACK_CATEGORY_NAMES: Record<string, string> = {
  general: '通用',
  productivity: '效率工具',
  coding: '编程工具',
  content_creation: '内容创作',
  media: '媒体音视频',
  data_analysis: '数据分析',
  observability: '可观测运维',
  other: '其他',
}

const getBindingSignatures = (binding: McpBinding) => {
  const signatures = [
    `${String(binding.transport || '').trim()}:${String(binding.url || binding.command || '').trim()}:${String(binding.name || '').trim()}`,
  ]
  const providerKey = String(binding.provider_key || '').trim()
  if (providerKey) {
    signatures.push(`provider_key:${providerKey}`)
  }
  return signatures
}

const selectedBindingSignatureSet = computed(() => {
  const set = new Set<string>()
  ;(props.selected_bindings || []).forEach((binding) => {
    getBindingSignatures(binding).forEach((signature) => set.add(signature))
  })
  return set
})

const isSelectedBinding = (binding: McpBinding) => {
  return getBindingSignatures(binding).some((signature) => selectedBindingSignatureSet.value.has(signature))
}

const hashString = (value: string) => {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 33 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

const getAvatarText = (provider: McpProvider) => {
  const source = (provider.label || provider.name || provider.provider_key || 'M').trim()
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

const getAvatarStyle = (provider: McpProvider) => {
  const palette = avatarPalettes[hashString(`${provider.provider_key}:${provider.category}:${provider.label}`) % avatarPalettes.length]
  return {
    background: `linear-gradient(135deg, ${palette[0]} 0%, ${palette[1]} 100%)`,
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.15)',
  }
}

const normalizeIconUrl = (icon: string = '') => {
  if (!icon) return ''
  if (icon.startsWith('data:') || /^https?:\/\//.test(icon)) return icon
  const fallbackOrigin = globalThis.location?.origin ?? 'http://localhost'
  const apiUrl = new URL(apiPrefix, fallbackOrigin)
  const basePath = apiUrl.pathname.replace(/\/+$/, '')
  let path = icon.startsWith('/') ? icon : `/${icon}`

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

const categoryNameMap = computed(() => {
  return new Map(categories.value.map((item) => [item.id, item.name]))
})

const getCategoryName = (category: string) => {
  return categoryNameMap.value.get(category) || FALLBACK_CATEGORY_NAMES[category] || category || '其他'
}

const loadCategories = async () => {
  try {
    const res = await getPublicMcpCategories()
    categories.value = res.data.categories || []
  } catch (_error: unknown) {
    categories.value = []
  }
}

const loadProviders = async (reset = false) => {
  if (loading.value) return
  if (!reset && paginator.value.current_page > 0 && paginator.value.current_page >= paginator.value.total_page) {
    return
  }

  const nextPage = reset ? 1 : paginator.value.current_page + 1 || 1
  loading.value = true
  try {
    if (reset) {
      providers.value = []
      paginator.value = {
        total_page: 0,
        total_record: 0,
        current_page: 0,
        page_size: PAGE_SIZE,
      }
    }

    const res = await getPublicMcpProvidersWithPage({
      current_page: nextPage,
      page_size: PAGE_SIZE,
      search_word: searchWord.value.trim(),
      category: selectedCategory.value === 'all' ? '' : selectedCategory.value,
    })
    providers.value = reset ? (res.data.list || []) : [...providers.value, ...(res.data.list || [])]
    paginator.value = res.data.paginator || {
      total_page: nextPage,
      total_record: providers.value.length,
      current_page: nextPage,
      page_size: PAGE_SIZE,
    }
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 MCP 广场失败'))
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  await loadProviders(true)
}

const handleCategoryChange = async (category: string) => {
  selectedCategory.value = category
  await loadProviders(true)
}

const handleSelect = (provider: McpProvider) => {
  if (!provider.is_bindable) return
  if (isSelectedBinding(provider.binding)) {
    Message.warning('该 MCP 已添加到当前应用')
    return
  }
  emits('select', provider.binding)
}

const handleScroll = async (event: Event) => {
  const { scrollTop, scrollHeight, clientHeight } = event.target as HTMLElement
  if (scrollTop + clientHeight < scrollHeight - 10) return
  if (loading.value || paginator.value.current_page >= paginator.value.total_page) return
  await loadProviders()
}

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    await loadCategories()
    await loadProviders(true)
  },
  { immediate: true },
)

onMounted(async () => {
  await loadCategories()
})
</script>

<template>
  <a-modal
    :visible="props.visible"
    :footer="false"
    hide-title
    :width="980"
    class="tools-modal"
    modal-class="right-4 app-tools-modal-shell"
    @cancel="hideModal"
  >
    <div class="flex w-full h-full flex-col md:flex-row">
      <div
        class="flex flex-col flex-shrink-0 bg-gray-50 w-full md:w-56 lg:w-64 h-full px-3 py-4 overflow-auto scrollbar-w-none"
      >
        <div class="text-gray-900 font-bold text-lg mb-2">关联 MCP</div>
        <div class="text-xs text-gray-500 mb-4">从 MCP 广场中选择要绑定的工具提供方</div>
        <div class="flex flex-col gap-1 mb-4">
          <div
            data-testid="mcp-category-all"
            :class="`rounded-lg h-8 leading-8 px-3 flex items-center gap-2 cursor-pointer hover:bg-white hover:text-blue-700 ${selectedCategory === 'all' ? 'text-blue-700 bg-white' : 'text-gray-700'}`"
            @click="handleCategoryChange('all')"
          >
            <icon-apps />
            全部
          </div>
          <div
            v-for="item in categories"
            :key="item.id"
            :data-testid="`mcp-category-${item.id}`"
            :class="`rounded-lg h-8 leading-8 px-3 flex items-center gap-2 cursor-pointer hover:bg-white hover:text-blue-700 ${selectedCategory === item.id ? 'text-blue-700 bg-white' : 'text-gray-700'}`"
            @click="handleCategoryChange(item.id)"
          >
            <icon-apps />
            {{ item.name }}
          </div>
        </div>
        <div class="text-xs text-gray-500 leading-5">
          仅展示可添加的 MCP。选择后会直接纳入当前应用的 MCP 绑定。
        </div>
      </div>

      <div class="flex-1 p-4 min-w-0 flex flex-col overflow-hidden">
        <div class="w-full flex items-center justify-between gap-2 mb-7">
          <div class="text-lg font-bold text-gray-700">MCP 广场</div>
          <a-input-search
            v-model="searchWord"
            placeholder="搜索 MCP"
            class="w-full sm:w-[280px] bg-white rounded-lg border-gray-300"
            @search="handleSearch"
          />
        </div>

        <a-spin :loading="loading" class="block flex-1 min-w-0 overflow-hidden">
          <div data-testid="mcp-binding-list" class="block app-modal-list-scroll scrollbar-w-none" @scroll="handleScroll">
            <div class="flex flex-col gap-2 pr-1">
              <div
                v-for="provider in providers"
                :key="provider.provider_key"
                :class="`flex items-start justify-between gap-3 px-3 py-3 rounded-lg border cursor-pointer hover:bg-blue-50 hover:border-blue-700 ${isSelectedBinding(provider.binding) ? 'bg-blue-50 border-blue-700' : 'bg-white border-gray-200'}`"
              >
                <div class="flex items-start gap-3 min-w-0 flex-1">
                  <a-avatar
                    :size="34"
                    shape="square"
                    class="shrink-0 overflow-hidden"
                    :style="provider.icon ? { backgroundColor: '#f3f4f6' } : getAvatarStyle(provider)"
                  >
                    <img
                      v-if="provider.icon"
                      :src="normalizeIconUrl(provider.icon)"
                      :alt="provider.name"
                      class="w-full h-full object-cover"
                    />
                    <span v-else class="text-white font-semibold text-[12px] tracking-wide">
                      {{ getAvatarText(provider) }}
                    </span>
                  </a-avatar>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <div class="text-sm font-bold text-gray-900 truncate">{{ provider.label }}</div>
                      <a-tag size="small" :color="provider.is_bindable ? 'green' : 'gray'">
                        {{ provider.is_bindable ? '可添加' : '仅查看' }}
                      </a-tag>
                    </div>
                    <div class="text-[11px] text-gray-500 line-clamp-1">
                      {{ provider.name }} · {{ provider.tool_count }} 个工具
                    </div>
                    <resource-card-description :text="provider.description" />

                    <div class="flex items-center gap-1.5 flex-wrap mt-2.5">
                      <a-tag size="small" color="gray">
                        {{ getCategoryName(provider.category) }}
                      </a-tag>
                      <a-tag size="small" color="arcoblue">
                        {{ provider.transport }}
                      </a-tag>
                    </div>

                    <div v-if="!provider.is_bindable && provider.bind_reason" class="mt-2.5 text-xs text-amber-700">
                      {{ provider.bind_reason }}
                    </div>

                    <div class="flex items-center gap-1.5 mt-2.5">
                      <a-avatar
                        :size="16"
                        class="bg-blue-700"
                        :image-url="provider.creator_avatar"
                      >
                        {{ (provider.creator_name || '公开目录')[0] }}
                      </a-avatar>
                      <div class="text-[11px] text-gray-400">
                        {{ provider.creator_name || '公开目录' }} ·
                        {{ formatTimestampShort(provider.published_at || provider.created_at) }}
                      </div>
                    </div>
                  </div>
                </div>

                <div class="flex flex-col items-end gap-2 flex-shrink-0">
                  <a-button
                    type="primary"
                    size="small"
                    :disabled="!provider.is_bindable || isSelectedBinding(provider.binding)"
                    @click.stop="handleSelect(provider)"
                  >
                    {{
                      isSelectedBinding(provider.binding)
                        ? '已添加'
                        : provider.is_bindable
                          ? '添加到应用'
                          : '仅查看'
                    }}
                  </a-button>
                </div>
              </div>

              <a-empty v-if="providers.length === 0" description="暂无可添加的 MCP" class="py-20" />

              <div v-if="paginator.total_page >= 2" class="w-full">
                <div v-if="loading" class="text-center py-4">
                  <a-space>
                    <a-spin />
                    <div class="text-gray-400">加载中</div>
                  </a-space>
                </div>
                <div v-else-if="paginator.current_page >= paginator.total_page" class="text-center py-4">
                  <div class="text-gray-400">数据已加载完成</div>
                </div>
              </div>
            </div>
          </div>
        </a-spin>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
