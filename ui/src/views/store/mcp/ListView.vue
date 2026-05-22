<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

const loading = ref(false)
const categories = ref<McpCategory[]>([])
const providers = ref<McpProvider[]>([])
const selectedCategory = ref('all')
const searchWord = ref('')
const showDetailVisible = ref(false)
const detailLoading = ref(false)
const activeProvider = ref<McpProvider | null>(null)

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
    providers.value = res.data.list
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
            <div class="text-xs text-gray-500">公开免费 MCP 目录</div>
          </div>
        </div>
        <router-link :to="{ name: 'space-mcp-list', query: { create_type: 'mcp' } }">
          <a-button type="primary" class="rounded-lg">创建 MCP</a-button>
        </router-link>
      </div>

      <div class="flex items-center justify-between mb-6 flex-wrap gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <a-button
            :type="selectedCategory === 'all' ? 'primary' : 'text'"
            class="rounded-lg"
            @click="handleCategoryChange('all')"
          >
            全部
          </a-button>
          <a-button
            v-for="item in categories"
            :key="item.id"
            :type="selectedCategory === item.id ? 'primary' : 'text'"
            class="rounded-lg"
            @click="handleCategoryChange(item.id)"
          >
            {{ item.name }}
          </a-button>
        </div>

        <a-input-search
          v-model="searchWord"
          placeholder="搜索 MCP 名称、描述或来源"
          class="w-full sm:w-[280px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <card-grid-skeleton v-if="loading && providers.length === 0" :count="8" />
      <a-row v-else :gutter="[20, 20]" class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
        <a-col v-for="provider in providers" :key="provider.provider_key" :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
          <a-card hoverable class="cursor-pointer rounded-lg h-full" @click="handleCardClick(provider)">
            <div class="flex items-start gap-3 mb-3">
              <a-avatar :size="40" shape="square" :style="{ backgroundColor: provider.background }">
                <img
                  v-if="provider.icon"
                  :src="provider.icon"
                  :alt="provider.name"
                  class="w-full h-full object-cover"
                />
                <span v-else class="text-white font-semibold">
                  {{ (provider.label || provider.name || 'M')[0] }}
                </span>
              </a-avatar>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="text-base font-bold text-gray-900 truncate">{{ provider.label }}</div>
                  <a-tag size="small" :color="provider.is_bindable ? 'green' : 'gray'">
                    {{ provider.is_bindable ? '可绑定' : '仅查看' }}
                  </a-tag>
                </div>
                <div class="text-xs text-gray-500 line-clamp-1">
                  {{ provider.name }} · {{ provider.tool_count }} 个工具
                </div>
              </div>
            </div>

            <resource-card-description :text="provider.description" />

            <div class="flex items-center gap-2 flex-wrap mt-3">
              <a-tag size="small" :color="provider.background">{{ provider.category }}</a-tag>
              <a-tag size="small" color="arcoblue">{{ provider.transport }}</a-tag>
            </div>

            <div class="flex items-center gap-1.5 mt-3">
              <a-avatar :size="18" class="bg-blue-700" :image-url="provider.creator_avatar">
                {{ (provider.creator_name || 'M')[0] }}
              </a-avatar>
              <div class="text-xs text-gray-400">
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

    <a-drawer
      :visible="showDetailVisible"
      :width="520"
      :footer="false"
      title="MCP 详情"
      :drawer-style="{ background: '#F9FAFB' }"
      @cancel="showDetailVisible = false"
    >
      <a-spin :loading="detailLoading" class="block h-full w-full">
        <div v-if="activeProvider" class="flex flex-col gap-4">
          <div class="flex items-start gap-3">
            <a-avatar :size="48" shape="square" :style="{ backgroundColor: activeProvider.background }">
              <img
                v-if="activeProvider.icon"
                :src="activeProvider.icon"
                :alt="activeProvider.name"
                class="w-full h-full object-cover"
              />
              <span v-else class="text-white font-semibold">{{ (activeProvider.label || activeProvider.name || 'M')[0] }}</span>
            </a-avatar>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <div class="text-lg font-bold text-gray-900">{{ activeProvider.label }}</div>
                <a-tag size="small" :color="activeProvider.is_bindable ? 'green' : 'gray'">
                  {{ activeProvider.is_bindable ? '可绑定' : '仅查看' }}
                </a-tag>
              </div>
              <div class="text-xs text-gray-500 mt-1">
                {{ activeProvider.creator_name || '公开目录' }} · 公开来源
              </div>
            </div>
          </div>

          <div class="text-sm text-gray-600 whitespace-pre-wrap">
            {{ activeProvider.description }}
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
              <div class="text-sm text-gray-800">{{ activeProvider.category }}</div>
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
              <a-card v-for="tool in activeProvider.tools" :key="tool.name" class="rounded-lg">
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
</style>
