<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import storage from '@/utils/storage'
import { isCredentialLoggedIn } from '@/utils/auth'
import { useRoute, useRouter } from 'vue-router'
import { useCredentialStore } from '@/stores/credential'
import { AUTH_REQUIRED_EVENT } from '@/utils/request'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const credentialStore = useCredentialStore()
const isLoggedIn = computed(() => isCredentialLoggedIn(credentialStore.credential))
const unauthDescription = computed(() => {
  if (route.path.startsWith('/space/apps')) return t('space.unauth.apps')
  if (route.path.startsWith('/space/tools')) return t('space.unauth.tools')
  if (route.path.startsWith('/space/workflows')) return t('space.unauth.workflows')
  if (route.path.startsWith('/space/mcp')) return t('space.unauth.mcp')
  if (route.path.startsWith('/space/datasets')) return t('space.unauth.datasets')
  return t('space.unauth.default')
})
const pendingCreateType = ref<string>('')
const searchWord = ref(String(route.query?.search_word ?? ''))
const SPACE_APPS_SEARCH_DRAFT_STORAGE_KEY = 'draft:space-apps:search-word'

const openLoginModal = () => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent(AUTH_REQUIRED_EVENT, {
      detail: { redirect: route.fullPath },
    }),
  )
}

const handleCreate = (type: 'app' | 'tool' | 'workflow' | 'dataset' | 'mcp') => {
  if (isLoggedIn.value) {
    void router.replace({
      path: route.path,
      query: {
        ...route.query,
        create_type: type,
      },
    })
    return
  }
  pendingCreateType.value = type
  openLoginModal()
}

const persistSpaceAppsSearchWord = (value: string) => {
  if (value.trim() === '') {
    storage.remove(SPACE_APPS_SEARCH_DRAFT_STORAGE_KEY)
    return
  }
  storage.set(SPACE_APPS_SEARCH_DRAFT_STORAGE_KEY, value)
}

const getSpaceAppsSearchWordDraft = () => {
  return String(storage.get(SPACE_APPS_SEARCH_DRAFT_STORAGE_KEY, ''))
}

// 绑定输入框的搜索事件
const search = (value: string) => {
  router.push({
    path: route.path,
    query: {
      search_word: value,
    },
  })
}

// 监听路由里的search_word变化
watch(
  [() => route.path, () => route.query?.search_word],
  ([path, routeSearchWord]) => {
    if (path.startsWith('/space/apps') && !routeSearchWord) {
      searchWord.value = getSpaceAppsSearchWordDraft()
      return
    }
    searchWord.value = String(routeSearchWord ?? '')
  },
  { immediate: true },
)

watch(searchWord, (value) => {
  if (!route.path.startsWith('/space/apps')) return
  persistSpaceAppsSearchWord(value)
})

watch(
  isLoggedIn,
  async (loggedIn) => {
    if (!loggedIn || !pendingCreateType.value) return
    const targetCreateType = pendingCreateType.value
    pendingCreateType.value = ''
    void router.replace({
      path: route.path,
      query: {
        ...route.query,
        create_type: targetCreateType,
      },
    })
  },
  { immediate: true },
)
</script>

<template>
  <!-- 调整边距+隐藏 -->
  <div class="flex h-full min-h-0 flex-col overflow-hidden px-6">
    <div class="shrink-0 bg-gray-50 pt-6">
      <!-- 顶层标题+创建按钮 -->
      <div class="flex items-center justify-between mb-6 flex-wrap gap-2">
        <!-- 左侧标题 -->
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-user :size="18" />
          </a-avatar>
          <div class="text-lg font-medium text-gray-900">{{ $t('space.title') }}</div>
        </div>
        <!-- 创建按钮 -->
        <a-button
          v-if="route.path.startsWith('/space/apps')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('app')"
        >
          {{ $t('space.createApp') }}
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/tools')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('tool')"
        >
          {{ $t('space.createTool') }}
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/workflows')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('workflow')"
        >
          {{ $t('space.createWorkflow') }}
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/mcp')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('mcp')"
        >
          {{ $t('space.createMcp') }}
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/mcp')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('mcp')"
        >
          创建 MCP
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/datasets')"
          type="primary"
          class="rounded-lg"
          @click="handleCreate('dataset')"
        >
          {{ $t('space.createDataset') }}
        </a-button>
      </div>
      <!-- 导航按钮+搜索框 -->
      <div class="flex items-center justify-between mb-6 flex-wrap gap-2">
        <!-- 左侧导航 -->
        <div class="flex items-center gap-2">
          <router-link
            to="/space/apps"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            {{ $t('space.nav.apps') }}
          </router-link>
          <router-link
            to="/space/tools"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            {{ $t('space.nav.tools') }}
          </router-link>
          <router-link
            to="/space/workflows"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            {{ $t('space.nav.workflows') }}
          </router-link>
          <router-link
            to="/space/mcp"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            {{ $t('space.nav.mcp') }}
          </router-link>
          <router-link
            to="/space/mcp"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            MCP
          </router-link>
          <router-link
            to="/space/datasets"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            {{ $t('space.nav.datasets') }}
          </router-link>
        </div>
        <!-- 右侧搜索 -->
        <a-input-search
          v-model="searchWord"
          :disabled="!isLoggedIn"
          :placeholder="t('space.searchPlaceholder')"
          class="w-[240px] bg-white rounded-lg border-gray-300"
          @search="search"
        />
      </div>
    </div>
    <!-- 中间内容 -->
    <div v-if="isLoggedIn" class="flex min-h-0 flex-1 overflow-hidden">
      <router-view />
    </div>
    <div v-else class="flex-1 flex items-center justify-center">
      <a-empty :description="unauthDescription" />
    </div>
  </div>
</template>

<style scoped></style>
