<script setup lang="ts">
import { computed, onMounted, ref, watch, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getErrorMessage } from '@/utils/error'
import {
  getPublicMcpCategories,
  getPublicMcpProvidersWithPage,
} from '@/services/mcp'
import type { McpBinding, McpCategory, McpProvider } from '@/models/mcp'

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

const hideModal = () => emits('update:visible', false)

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

const handleSelect = (provider: McpProvider) => {
  if (!provider.is_bindable) return
  if (isSelectedBinding(provider.binding)) {
    Message.warning('该 MCP 已添加到当前应用')
    return
  }
  emits('select', provider.binding)
}

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    await loadCategories()
    await loadProviders()
  },
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
    modal-class="h-[calc(100vh-32px)] right-4"
    @cancel="hideModal"
  >
    <div class="flex items-center justify-between mb-4">
      <div>
        <div class="text-lg font-bold text-gray-800">从 MCP 广场添加</div>
        <div class="text-xs text-gray-500">点击添加后会直接写入当前应用的 MCP 绑定</div>
      </div>
      <a-button type="text" size="small" class="!text-gray-700" @click="hideModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>

    <div class="flex flex-col gap-4 h-[calc(100vh-150px)] overflow-hidden">
      <div class="flex items-center justify-between gap-3 flex-wrap">
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
          placeholder="搜索 MCP"
          class="w-full sm:w-[280px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <a-spin :loading="loading" class="block flex-1 overflow-hidden">
        <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="provider in providers"
              :key="provider.provider_key"
              :xs="24"
              :sm="12"
              :md="8"
              :lg="6"
              :xl="6"
            >
              <a-card class="h-full rounded-lg" hoverable>
                <div class="flex items-start gap-3">
                  <a-avatar :size="40" shape="square" :style="{ backgroundColor: provider.background }">
                    <img
                      v-if="provider.icon"
                      :src="provider.icon"
                      :alt="provider.name"
                      class="w-full h-full object-cover"
                    />
                    <span v-else class="text-white font-semibold">{{ (provider.label || provider.name || 'M')[0] }}</span>
                  </a-avatar>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 min-w-0">
                      <div class="text-sm font-semibold text-gray-900 truncate">{{ provider.label }}</div>
                      <a-tag size="small" :color="provider.is_bindable ? 'green' : 'gray'">
                        {{ provider.is_bindable ? '可添加' : '仅查看' }}
                      </a-tag>
                    </div>
                    <div class="text-xs text-gray-500 line-clamp-1">
                      {{ provider.name }} · {{ provider.tool_count }} 工具
                    </div>
                  </div>
                </div>

                <div class="mt-3 text-sm text-gray-600 line-clamp-3">
                  {{ provider.description }}
                </div>

                <div class="flex items-center gap-2 flex-wrap mt-3">
                  <a-tag size="small" :color="provider.background">{{ provider.category }}</a-tag>
                  <a-tag size="small" color="arcoblue">{{ provider.transport }}</a-tag>
                </div>

                <div class="flex items-center justify-between gap-2 mt-4">
                  <div class="text-xs text-gray-500 truncate">
                    {{ provider.creator_name || '公开目录' }}
                  </div>
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

                <div v-if="!provider.is_bindable && provider.bind_reason" class="mt-3 text-xs text-amber-700">
                  {{ provider.bind_reason }}
                </div>
              </a-card>
            </a-col>

            <a-col v-if="providers.length === 0" :span="24">
              <a-empty description="暂无可添加的 MCP" class="py-20" />
            </a-col>
          </a-row>
        </div>
      </a-spin>
    </div>
  </a-modal>
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

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
