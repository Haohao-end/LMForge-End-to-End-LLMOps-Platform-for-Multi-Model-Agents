<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import { apiPrefix } from '@/config'
import { getErrorMessage } from '@/utils/error'
import { getAppsWithPage } from '@/services/app'
import { getPublicApps, type PublicApp } from '@/services/public-app'
import type { AgentBinding } from '@/models/app'

type BindingTarget = {
  app_id: string
  name: string
  icon: string
  description: string
  source_scope: 'public' | 'own'
  invoke_mode: 'a2a' | 'tool'
  is_public: boolean
  status: string
}

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
    type: Array as PropType<AgentBinding[]>,
    default: () => [],
  },
  current_app_id: {
    type: String,
    default: '',
  },
})

const emits = defineEmits(['update:visible', 'select'])

const activeTab = ref<'own' | 'public'>('own')
const searchWord = ref('')
const loadingOwn = ref(false)
const loadingPublic = ref(false)
const ownApps = ref<BindingTarget[]>([])
const publicApps = ref<BindingTarget[]>([])
const ownPaginator = ref<PaginatorState>({
  total_page: 0,
  total_record: 0,
  current_page: 0,
  page_size: PAGE_SIZE,
})
const publicPaginator = ref<PaginatorState>({
  total_page: 0,
  total_record: 0,
  current_page: 0,
  page_size: PAGE_SIZE,
})

const hideModal = () => emits('update:visible', false)

const selectedAppIdSet = computed(() => {
  const set = new Set<string>()
  ;(props.selected_bindings || []).forEach((binding) => {
    const appId = String(binding.app_id || '').trim()
    if (appId) {
      set.add(appId)
    }
  })
  return set
})

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

const isSelectedBinding = (binding: BindingTarget) => selectedAppIdSet.value.has(binding.app_id)

const normalizeOwnApp = (app: Record<string, any>): BindingTarget | null => {
  const appId = String(app.id || '').trim()
  if (!appId || appId === String(props.current_app_id || '').trim()) {
    return null
  }

  return {
    app_id: appId,
    name: String(app.name || '').trim(),
    icon: String(app.icon || '').trim(),
    description: String(app.description || '').trim(),
    source_scope: 'own',
    invoke_mode: app.is_public ? 'a2a' : 'tool',
    is_public: Boolean(app.is_public),
    status: String(app.status || '').trim(),
  }
}

const normalizePublicApp = (app: PublicApp): BindingTarget | null => {
  const appId = String(app.id || '').trim()
  if (!appId || appId === String(props.current_app_id || '').trim()) {
    return null
  }

  return {
    app_id: appId,
    name: String(app.name || '').trim(),
    icon: String(app.icon || '').trim(),
    description: String(app.description || '').trim(),
    source_scope: 'public',
    invoke_mode: 'a2a',
    is_public: true,
    status: String(app.status || '').trim(),
  }
}

const activeApps = computed(() => (activeTab.value === 'own' ? ownApps.value : publicApps.value))
const activeLoading = computed(() => (activeTab.value === 'own' ? loadingOwn.value : loadingPublic.value))
const activePaginator = computed(() => (activeTab.value === 'own' ? ownPaginator.value : publicPaginator.value))

const hasMoreActiveApps = computed(() => {
  return activePaginator.value.current_page > 0 && activePaginator.value.current_page < activePaginator.value.total_page
})

const loadOwnApps = async (reset = false) => {
  if (loadingOwn.value) return
  if (!reset && ownPaginator.value.current_page > 0 && ownPaginator.value.current_page >= ownPaginator.value.total_page) {
    return
  }

  const nextPage = reset ? 1 : ownPaginator.value.current_page + 1 || 1
  loadingOwn.value = true
  try {
    if (reset) {
      ownApps.value = []
      ownPaginator.value = {
        total_page: 0,
        total_record: 0,
        current_page: 0,
        page_size: PAGE_SIZE,
      }
    }

    const res = await getAppsWithPage({
      current_page: nextPage,
      page_size: PAGE_SIZE,
      search_word: searchWord.value.trim(),
      published_only: true,
    })

    const nextApps = (res.data.list || [])
      .map((app) => normalizeOwnApp(app))
      .filter((item): item is BindingTarget => Boolean(item))

    ownApps.value = reset ? nextApps : [...ownApps.value, ...nextApps]
    ownPaginator.value = res.data.paginator || {
      total_page: nextPage,
      total_record: ownApps.value.length,
      current_page: nextPage,
      page_size: PAGE_SIZE,
    }
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载我的已发布应用失败'))
  } finally {
    loadingOwn.value = false
  }
}

const loadPublicApps = async (reset = false) => {
  if (loadingPublic.value) return
  if (!reset && publicPaginator.value.current_page > 0 && publicPaginator.value.current_page >= publicPaginator.value.total_page) {
    return
  }

  const nextPage = reset ? 1 : publicPaginator.value.current_page + 1 || 1
  loadingPublic.value = true
  try {
    if (reset) {
      publicApps.value = []
      publicPaginator.value = {
        total_page: 0,
        total_record: 0,
        current_page: 0,
        page_size: PAGE_SIZE,
      }
    }

    const res = await getPublicApps({
      current_page: nextPage,
      page_size: PAGE_SIZE,
      search_word: searchWord.value.trim(),
    })

    const nextApps = (res.data.list || [])
      .map((app) => normalizePublicApp(app))
      .filter((item): item is BindingTarget => Boolean(item))

    publicApps.value = reset ? nextApps : [...publicApps.value, ...nextApps]
    publicPaginator.value = res.data.paginator || {
      total_page: nextPage,
      total_record: publicApps.value.length,
      current_page: nextPage,
      page_size: PAGE_SIZE,
    }
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载应用广场失败'))
  } finally {
    loadingPublic.value = false
  }
}

const loadActiveTab = async (reset = false) => {
  if (activeTab.value === 'own') {
    await loadOwnApps(reset)
    return
  }
  await loadPublicApps(reset)
}

const switchActiveTab = async (tab: 'own' | 'public') => {
  activeTab.value = tab
  await loadActiveTab(true)
}

const handleSearch = async () => {
  await loadActiveTab(true)
}

const handleSelect = (binding: BindingTarget) => {
  if (isSelectedBinding(binding)) return
  emits('select', binding)
}

const handleScroll = (event: Event) => {
  const { scrollTop, scrollHeight, clientHeight } = event.target as HTMLElement
  if (scrollTop + clientHeight < scrollHeight - 10) return
  if (!hasMoreActiveApps.value || activeLoading.value) return
  void loadActiveTab()
}

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    await loadActiveTab(true)
  },
  { immediate: true },
)
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
      <div class="flex flex-col flex-shrink-0 bg-gray-50 w-full md:w-56 lg:w-64 h-full px-3 py-4 overflow-auto scrollbar-w-none">
        <div class="text-gray-900 font-bold text-lg mb-2">关联 Agent</div>
        <div class="text-xs text-gray-500 mb-4">从我的已发布应用或应用广场中选择要绑定的子 Agent</div>
        <div class="flex flex-col gap-1 mb-4">
          <div
            data-testid="agent-source-own"
            :class="`rounded-lg h-8 leading-8 px-3 flex items-center gap-2 cursor-pointer hover:bg-white hover:text-blue-700 ${activeTab === 'own' ? 'text-blue-700 bg-white' : 'text-gray-700'}`"
            @click="switchActiveTab('own')"
          >
            <icon-apps />
            我的已发布
            <span class="ml-auto text-xs text-gray-400">{{ ownPaginator.total_record > 0 ? ownPaginator.total_record : '' }}</span>
          </div>
          <div
            data-testid="agent-source-public"
            :class="`rounded-lg h-8 leading-8 px-3 flex items-center gap-2 cursor-pointer hover:bg-white hover:text-blue-700 ${activeTab === 'public' ? 'text-blue-700 bg-white' : 'text-gray-700'}`"
            @click="switchActiveTab('public')"
          >
            <icon-apps />
            应用广场
            <span class="ml-auto text-xs text-gray-400">{{ publicPaginator.total_record > 0 ? publicPaginator.total_record : '' }}</span>
          </div>
        </div>
        <div class="text-xs text-gray-500 leading-5">
          仅展示已发布且可绑定的 Agent。选择后会直接纳入当前应用的运行时工具。
        </div>
      </div>

      <div class="flex-1 p-4 min-w-0 flex flex-col overflow-hidden">
        <div class="w-full flex items-center justify-between gap-2 mb-7">
          <div class="text-lg font-bold text-gray-700">
            {{ activeTab === 'own' ? '我的已发布应用' : '应用广场' }}
          </div>
          <a-input-search
            v-model="searchWord"
            placeholder="搜索应用名称或描述"
            class="w-full sm:w-[280px] bg-white rounded-lg border-gray-300"
            @search="handleSearch"
          />
        </div>

        <a-spin :loading="activeLoading" class="block flex-1 min-w-0 overflow-hidden">
          <div data-testid="agent-binding-list" class="block app-modal-list-scroll scrollbar-hide" @scroll="handleScroll">
            <div class="flex flex-col gap-2 pr-1">
              <div
                v-for="app in activeApps"
                :key="app.app_id"
                :class="`flex items-start justify-between gap-3 px-3 py-3 rounded-lg border cursor-pointer hover:bg-blue-50 hover:border-blue-700 ${isSelectedBinding(app) ? 'bg-blue-50 border-blue-700' : 'bg-white border-gray-200'}`"
              >
                <div class="flex items-start gap-3 min-w-0 flex-1">
                  <a-avatar :size="40" shape="square" class="bg-gray-100 flex-shrink-0">
                    <img
                      v-if="app.icon"
                      :src="normalizeIconUrl(app.icon)"
                      :alt="app.name"
                      class="w-full h-full object-cover"
                    />
                    <span v-else class="text-gray-700 font-semibold">
                      {{ (app.name || 'A')[0] }}
                    </span>
                  </a-avatar>
                  <div class="flex flex-col flex-1 min-w-0 gap-1">
                    <div class="flex items-center gap-2 min-w-0">
                      <div class="text-sm font-semibold text-gray-900 truncate">{{ app.name }}</div>
                      <a-tag size="small" :color="app.invoke_mode === 'a2a' ? 'arcoblue' : 'orange'">
                        {{ app.invoke_mode === 'a2a' ? 'A2A' : 'Tool' }}
                      </a-tag>
                      <a-tag size="small" :color="app.source_scope === 'public' ? 'arcoblue' : 'green'">
                        {{ app.source_scope === 'public' ? '应用广场' : '我的应用' }}
                      </a-tag>
                      <a-tag size="small" color="gray">
                        {{ app.is_public ? '公开应用' : '私有应用' }}
                      </a-tag>
                    </div>
                    <div class="text-xs text-gray-500 truncate">
                      {{ app.status || 'published' }}
                    </div>
                    <div class="text-sm text-gray-600 line-clamp-2">
                      {{ app.description || '未填写描述' }}
                    </div>
                  </div>
                </div>

                <div class="flex flex-col items-end gap-2 flex-shrink-0">
                  <a-button
                    type="primary"
                    size="small"
                    :disabled="isSelectedBinding(app)"
                    @click.stop="handleSelect(app)"
                  >
                    {{ isSelectedBinding(app) ? '已添加' : '添加到应用' }}
                  </a-button>
                </div>
              </div>

              <a-empty v-if="activeApps.length === 0" description="暂无可绑定的 Agent 应用" class="py-20" />

              <div v-if="activePaginator.total_page >= 2" class="w-full">
                <div v-if="activeLoading" class="text-center py-4">
                  <a-space>
                    <a-spin />
                    <div class="text-gray-400">加载中</div>
                  </a-space>
                </div>
                <div v-else-if="activePaginator.current_page >= activePaginator.total_page" class="text-center py-4">
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
.scrollbar-w-none {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-w-none::-webkit-scrollbar {
  display: none;
}

.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
