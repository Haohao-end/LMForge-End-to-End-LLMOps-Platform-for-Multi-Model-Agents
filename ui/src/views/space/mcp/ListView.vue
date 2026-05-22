<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import CardGridSkeleton from '@/components/skeletons/CardGridSkeleton.vue'
import ResourceCardDescription from '@/components/ResourceCardDescription.vue'
import { getErrorMessage } from '@/utils/error'
import { formatTimestampShort } from '@/utils/time-formatter'
import { getUserAvatarUrl } from '@/utils/helper'
import { useAccountStore } from '@/stores/account'
import {
  deleteMcpProvider,
  getMcpProvidersWithPage,
  publishMcpProvider,
  unpublishMcpProvider,
} from '@/services/mcp'
import type { McpProvider } from '@/models/mcp'
import CreateOrUpdateMcpModal from './components/CreateOrUpdateMcpModal.vue'

const route = useRoute()
const accountStore = useAccountStore()

const props = defineProps({
  createType: { type: String, required: true },
})
const emits = defineEmits(['update:create-type'])

const loading = ref(false)
const providers = ref<McpProvider[]>([])
const hasMore = ref(true)
const page = ref(1)
const pageSize = ref(20)
const showCreateOrUpdateMcpModalVisible = ref(false)
const updateMcpProviderId = ref('')

const searchWord = computed(() => String(route.query?.search_word ?? ''))

const loadProviders = async (init = false) => {
  if (loading.value) return
  if (!hasMore.value && !init) return

  if (init) {
    page.value = 1
    hasMore.value = true
    providers.value = []
  }

  loading.value = true
  try {
    const res = await getMcpProvidersWithPage({
      current_page: page.value,
      page_size: pageSize.value,
      search_word: searchWord.value.trim(),
      category: '',
    })

    const list = res.data.list || []
    if (page.value === 1) {
      providers.value = list
    } else {
      providers.value.push(...list)
    }

    hasMore.value = page.value < res.data.paginator.total_page
    if (hasMore.value) {
      page.value += 1
    }
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 MCP 列表失败'))
  } finally {
    loading.value = false
  }
}

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement | null
  if (!target) return
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollTop + clientHeight >= scrollHeight - 10) {
    if (loading.value || !hasMore.value) return
    void loadProviders()
  }
}

const openCreateModal = () => {
  updateMcpProviderId.value = ''
  showCreateOrUpdateMcpModalVisible.value = true
}

const openEditModal = (provider: McpProvider) => {
  updateMcpProviderId.value = provider.id
  showCreateOrUpdateMcpModalVisible.value = true
}

const handleCardClick = (provider: McpProvider) => {
  openEditModal(provider)
}

const handleDelete = (provider: McpProvider) => {
  Modal.warning({
    title: '删除这个 MCP？',
    content: '删除 MCP 是不可逆的，相关绑定配置不会自动恢复。',
    hideCancel: false,
    onOk: async () => {
      try {
        const resp = await deleteMcpProvider(provider.id)
        Message.success(resp.message)
        await loadProviders(true)
      } catch (error: unknown) {
        Message.error(getErrorMessage(error, '删除 MCP 失败'))
      }
    },
  })
}

const handleTogglePublish = async (provider: McpProvider) => {
  try {
    const resp = provider.is_public
      ? await unpublishMcpProvider(provider.id)
      : await publishMcpProvider(provider.id)
    Message.success(resp.message)
    await loadProviders(true)
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, provider.is_public ? '取消发布失败' : '发布失败'))
  }
}

watch(
  () => route.query?.search_word,
  async () => {
    await loadProviders(true)
  },
)

watch(
  () => route.query?.create_type,
  (newValue) => {
    if (newValue === 'mcp') {
      emits('update:create-type', 'mcp')
    }
  },
  { immediate: true },
)

watch(
  () => props.createType,
  (newValue) => {
    if (newValue !== 'mcp') return
    openCreateModal()
    emits('update:create-type', '')
  },
)

onMounted(async () => {
  await loadProviders(true)
})
</script>

<template>
  <a-spin :loading="loading" class="block h-full w-full scrollbar-w-none overflow-y-scroll overflow-x-hidden" @scroll="handleScroll">
    <div class="p-6 flex flex-col h-full min-h-0">
      <card-grid-skeleton v-if="loading && providers.length === 0" :count="8" />
      <a-row v-else :gutter="[20, 20]" class="flex-1 min-h-0 overflow-hidden">
        <a-col
          v-for="provider in providers"
          :key="provider.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
          :xl="6"
        >
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
                  <a-tag size="small" :color="provider.is_public ? 'green' : 'orange'">
                    {{ provider.is_public ? '已发布' : '草稿' }}
                  </a-tag>
                </div>
                <div class="text-xs text-gray-500 line-clamp-1">
                  {{ provider.name }} · {{ provider.transport }} · {{ provider.tool_count }} 个工具
                </div>
              </div>
            </div>

            <resource-card-description :text="provider.description" />

            <div class="flex items-center gap-2 flex-wrap mt-3">
              <a-tag size="small" :color="provider.background">{{ provider.category }}</a-tag>
              <a-tag size="small" color="arcoblue">{{ provider.transport }}</a-tag>
              <a-tag size="small" :color="provider.is_bindable ? 'green' : 'gray'">
                {{ provider.is_bindable ? '可绑定' : '仅查看' }}
              </a-tag>
            </div>

            <div v-if="provider.bind_reason" class="mt-3 text-xs text-amber-700">
              {{ provider.bind_reason }}
            </div>

            <div class="flex items-center gap-1.5 mt-3">
              <a-avatar
                :size="18"
                class="bg-blue-700"
                :image-url="getUserAvatarUrl(provider.creator_avatar || accountStore.account.avatar, provider.creator_name || accountStore.account.name)"
              >
                {{ (provider.creator_name || accountStore.account.name || '我')[0] }}
              </a-avatar>
              <div class="text-xs text-gray-400">
                {{ provider.creator_name || accountStore.account.name || '我' }} ·
                {{ formatTimestampShort(provider.updated_at || provider.created_at) }}
              </div>
            </div>

            <div class="flex items-center justify-between gap-2 mt-4" @click.stop>
              <a-dropdown position="br" @click.stop>
                <a-button size="small" type="text" class="rounded-lg !text-gray-700">
                  <template #icon>
                    <icon-more />
                  </template>
                </a-button>
                <template #content>
                  <a-doption @click="() => openEditModal(provider)">
                    编辑
                  </a-doption>
                  <a-doption @click="() => handleTogglePublish(provider)">
                    {{ provider.is_public ? '取消发布' : '发布到广场' }}
                  </a-doption>
                  <a-doption class="text-red-700" @click="() => handleDelete(provider)">
                    删除
                  </a-doption>
                </template>
              </a-dropdown>

              <a-button
                size="small"
                type="primary"
                class="rounded-lg"
                @click.stop="openEditModal(provider)"
              >
                编辑
              </a-button>
            </div>
          </a-card>
        </a-col>

        <a-col v-if="providers.length === 0" :span="24">
          <a-empty description="暂无 MCP" class="py-20" />
        </a-col>
      </a-row>
    </div>

    <create-or-update-mcp-modal
      v-model:visible="showCreateOrUpdateMcpModalVisible"
      v-model:mcp_provider_id="updateMcpProviderId"
      :callback="async () => await loadProviders(true)"
    />
  </a-spin>
</template>

<style scoped>
.scrollbar-w-none {
  scrollbar-width: none;
}

.scrollbar-w-none::-webkit-scrollbar {
  display: none;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
