<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import ResourceCardDescription from '@/components/ResourceCardDescription.vue'
import CardGridSkeleton from '@/components/skeletons/CardGridSkeleton.vue'
import { formatTimestampShort } from '@/utils/time-formatter'
import { getErrorMessage } from '@/utils/error'
import {
  getPublicMcpCategories,
  getPublicMcpProvider,
  getPublicMcpProvidersWithPage,
} from '@/services/mcp'
import type { McpCategory, McpProvider } from '@/models/mcp'
import CreateOrUpdateMcpModal from '@/views/space/mcp/components/CreateOrUpdateMcpModal.vue'

const loading = ref(false)
const categories = ref<McpCategory[]>([])
const providers = ref<McpProvider[]>([])
const selectedCategory = ref('all')
const searchWord = ref('')
const showDetailVisible = ref(false)
const detailLoading = ref(false)
const activeProvider = ref<McpProvider | null>(null)
const showCreateMcpModalVisible = ref(false)

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

const categoryNameMap = computed(() => {
  return new Map(categories.value.map((item) => [item.id, item.name]))
})

const getCategoryName = (category: string) => {
  return categoryNameMap.value.get(category) || FALLBACK_CATEGORY_NAMES[category] || category || '其他'
}

const getCategoryButtonClass = (active: boolean) =>
  [
    'mcp-category-btn',
    active ? 'mcp-category-btn-active' : 'mcp-category-btn-inactive',
  ].join(' ')

const openCreateModal = () => {
  showCreateMcpModalVisible.value = true
}

const loadCategories = async () => {
  try {
    const res = await getPublicMcpCategories()
    categories.value = res.data.categories || []
  } catch (_error: unknown) {
    categories.value = []
  }
}

const loadProviders = async () => {
  loading.value = true
  try {
    const res = await getPublicMcpProvidersWithPage({
      current_page: 1,
      page_size: 50,
      search_word: searchWord.value.trim(),
      category: selectedCategory.value === 'all' ? '' : selectedCategory.value,
    })
    providers.value = res.data.list || []
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 MCP 广场失败'))
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  await loadProviders()
}

const handleCategoryChange = async (category: string) => {
  selectedCategory.value = category
  await loadProviders()
}

const loadProviderDetail = async (providerKey: string) => {
  detailLoading.value = true
  showDetailVisible.value = true
  try {
    const res = await getPublicMcpProvider(providerKey)
    activeProvider.value = res.data
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 MCP 详情失败'))
    showDetailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const handleCardClick = async (provider: McpProvider) => {
  await loadProviderDetail(provider.provider_key)
}

onMounted(async () => {
  await loadCategories()
  await loadProviders()
})
</script>

<template>
  <a-spin :loading="loading" class="block h-full w-full">
    <div class="p-6 flex flex-col h-full">
      <div class="flex items-center justify-between mb-6 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-storage :size="18" />
          </a-avatar>
          <div>
            <div class="text-lg font-medium text-gray-900">MCP广场</div>
          </div>
        </div>
        <a-button
          data-testid="store-mcp-create-button"
          type="primary"
          class="rounded-lg"
          @click="openCreateModal"
        >
          创建 MCP
        </a-button>
      </div>

      <div class="flex items-center justify-between mb-6 flex-wrap gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <a-button
            type="text"
            :class="getCategoryButtonClass(selectedCategory === 'all')"
            @click="handleCategoryChange('all')"
          >
            全部
          </a-button>
          <a-button
            v-for="item in categories"
            :key="item.id"
            type="text"
            :class="getCategoryButtonClass(selectedCategory === item.id)"
            @click="handleCategoryChange(item.id)"
          >
            {{ item.name }}
          </a-button>
        </div>

        <a-input-search
          v-model="searchWord"
          placeholder="搜索 MCP 名称、描述或来源"
          class="w-full sm:w-[240px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <card-grid-skeleton v-if="loading && providers.length === 0" :count="8" />
      <div v-else class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden scrollbar-hide">
        <a-row :gutter="[16, 16]">
          <a-col v-for="provider in providers" :key="provider.provider_key" :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
            <a-card
              hoverable
              class="cursor-pointer rounded-lg h-full overflow-hidden"
              :body-style="{ padding: '10px' }"
              @click="handleCardClick(provider)"
            >
              <div class="flex items-start gap-2.5 mb-2">
                <a-avatar
                  :size="34"
                  shape="square"
                  class="shrink-0 overflow-hidden"
                  :style="provider.icon ? { backgroundColor: '#f3f4f6' } : getAvatarStyle(provider)"
                >
                  <img
                    v-if="provider.icon"
                    :src="provider.icon"
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
                  <a-tag size="small" color="green">可绑定</a-tag>
                </div>
                  <div class="text-[11px] text-gray-500 line-clamp-1">
                    {{ provider.name }} · {{ provider.tool_count }} 个工具
                  </div>
                </div>
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

              <div class="flex items-center gap-1.5 mt-2.5">
                <a-avatar :size="16" class="bg-blue-700" :image-url="provider.creator_avatar">
                  {{ (provider.creator_name || 'M')[0] }}
                </a-avatar>
                <div class="text-[11px] text-gray-400">
                  {{ provider.creator_name || '公开目录' }} ·
                  {{ formatTimestampShort(provider.published_at || provider.created_at) }}
                </div>
              </div>
            </a-card>
          </a-col>

          <a-col v-if="providers.length === 0" :span="24">
            <a-empty description="暂无 MCP" class="py-20" />
          </a-col>
        </a-row>
      </div>
    </div>

    <a-drawer
      :visible="showDetailVisible"
      :width="560"
      :footer="false"
      title="MCP 详情"
      :drawer-style="{ background: '#F9FAFB' }"
      @cancel="showDetailVisible = false"
    >
      <a-spin :loading="detailLoading" class="block h-full w-full">
        <div v-if="activeProvider" class="flex flex-col gap-4">
          <div class="flex items-start gap-3">
            <a-avatar
              :size="40"
              shape="square"
              class="overflow-hidden"
              :style="activeProvider.icon ? { backgroundColor: '#f3f4f6' } : getAvatarStyle(activeProvider)"
            >
              <img
                v-if="activeProvider.icon"
                :src="activeProvider.icon"
                :alt="activeProvider.name"
                class="w-full h-full object-cover"
              />
              <span v-else class="text-white font-semibold text-[12px] tracking-wide">
                {{ getAvatarText(activeProvider) }}
              </span>
            </a-avatar>
            <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <div class="text-sm font-bold text-gray-900">{{ activeProvider.label }}</div>
              <a-tag size="small" color="green">可绑定</a-tag>
            </div>
              <div class="text-[11px] text-gray-500 mt-1">
                {{ activeProvider.creator_name || '公开目录' }} · 公开来源
              </div>
            </div>
          </div>

          <div class="rounded-lg bg-white p-3.5">
            <div class="text-sm text-gray-600 whitespace-pre-wrap">
              {{ activeProvider.description }}
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="rounded-lg bg-white p-3">
              <div class="text-xs text-gray-500 mb-1">Transport</div>
              <div class="text-sm text-gray-800">{{ activeProvider.transport }}</div>
            </div>
            <div class="rounded-lg bg-white p-3">
              <div class="text-xs text-gray-500 mb-1">工具数量</div>
              <div class="text-sm text-gray-800">{{ activeProvider.tool_count }}</div>
            </div>
            <div class="rounded-lg bg-white p-3">
              <div class="text-xs text-gray-500 mb-1">来源</div>
              <div class="text-sm text-gray-800 break-all">公开目录</div>
            </div>
            <div class="rounded-lg bg-white p-3">
              <div class="text-xs text-gray-500 mb-1">分类</div>
              <a-tag size="small" color="gray">{{ getCategoryName(activeProvider.category) }}</a-tag>
            </div>
          </div>

          <div v-if="activeProvider.bind_reason" class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            {{ activeProvider.bind_reason }}
          </div>

          <div>
            <div class="flex items-center gap-2 mb-3">
              <div class="text-sm font-semibold text-gray-800">工具列表</div>
              <a-tag size="small">{{ activeProvider.tools.length }} 个</a-tag>
            </div>

            <div v-if="activeProvider.tools.length > 0" class="flex flex-col gap-2">
              <a-card
                v-for="tool in activeProvider.tools"
                :key="tool.name"
                class="rounded-lg"
                :body-style="{ padding: '12px' }"
              >
                <div class="font-semibold text-gray-900 mb-1">{{ tool.label }}</div>
                <div class="text-xs text-gray-500">{{ tool.description || '暂无描述' }}</div>
                <div v-if="tool.inputs.length > 0" class="mt-3">
                  <div class="text-xs text-gray-500 mb-2">参数</div>
                  <div class="flex flex-col gap-2">
                    <div v-for="input in tool.inputs" :key="input.name" class="rounded-md bg-gray-50 p-2">
                      <div class="flex items-center gap-2 text-xs">
                        <div class="font-semibold text-gray-800">{{ input.name }}</div>
                        <div class="text-gray-500">{{ input.type }}</div>
                        <a-tag v-if="input.required" size="small" color="red">必填</a-tag>
                      </div>
                      <div class="text-xs text-gray-500 mt-1">{{ input.description }}</div>
                    </div>
                  </div>
                </div>
              </a-card>
            </div>

            <a-empty v-else description="暂无可展示的工具" />
          </div>
        </div>
      </a-spin>
    </a-drawer>

    <create-or-update-mcp-modal
      v-model:visible="showCreateMcpModalVisible"
      :callback="loadProviders"
    />
  </a-spin>
</template>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mcp-category-btn {
  height: 32px;
  border-radius: 10px;
  padding: 0 12px;
  font-size: 12px;
}

.mcp-category-btn-active {
  background: #eef2f7 !important;
  color: #111827 !important;
}

.mcp-category-btn-inactive {
  color: #4b5563 !important;
}

.mcp-category-btn:hover {
  background: #f3f4f6 !important;
}

.mcp-category-btn-active:hover {
  background: #e5e7eb !important;
}
</style>
