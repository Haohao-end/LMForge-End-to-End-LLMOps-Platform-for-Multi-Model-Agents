<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  getPublicApps,
  getAppTags,
  forkPublicApp,
  type PublicApp,
  type AppTag
} from '@/services/public-app'
import { getErrorMessage } from '@/utils/error'
import { formatTimestampShort } from '@/utils/time-formatter'
import ResourceCardDescription from '@/components/ResourceCardDescription.vue'
import { getPublicAppTagDisplayName } from '@/utils/public-app-tag-display'

const router = useRouter()
const { t, locale } = useI18n()
const loading = ref(false)
const apps = ref<PublicApp[]>([])
const tags = ref<AppTag[]>([])
const selectedTags = ref<string[]>([])
const searchWord = ref('')
const page = ref(1)
const pageSize = ref(20)
const hasMore = ref(true)

const loadApps = async () => {
  if (loading.value) return
  if (!hasMore.value && page.value > 1) return

  loading.value = true
  try {
    const res = await getPublicApps({
      current_page: page.value,
      page_size: pageSize.value,
      tags: selectedTags.value.join(','),
      search_word: searchWord.value
    })
    const list = res.data.list
    if (page.value === 1) {
      apps.value = list
    } else {
      apps.value.push(...list)
    }
    hasMore.value = page.value < res.data.paginator.total_page
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('publicApps.list.loadAppsFailed')))
  } finally {
    loading.value = false
  }
}

const loadTags = async () => {
  try {
    const res = await getAppTags()
    tags.value = res.data.tags
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('publicApps.list.loadTagsFailed')))
  }
}

const handleFork = async (app: PublicApp) => {
  try {
    const res = await forkPublicApp(app.id)
    Message.success(t('publicApps.list.forkSuccess', { name: res.data.name }))
    await loadApps()
    router.push({ name: 'space-apps-detail', params: { app_id: res.data.id } })
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('publicApps.list.actionFailed')))
  }
}

const handlePreview = (app: PublicApp) => {
  router.push({ name: 'store-public-apps-preview', params: { app_id: app.id } })
}

const toggleTag = (tagId: string) => {
  const index = selectedTags.value.indexOf(tagId)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tagId)
  }
  page.value = 1
  hasMore.value = true
  loadApps()
}

const handleSearch = () => {
  page.value = 1
  hasMore.value = true
  loadApps()
}

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement | null
  if (!target) return
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollTop + clientHeight >= scrollHeight - 10) {
    if (loading.value || !hasMore.value) return
    page.value += 1
    void loadApps()
  }
}

const getDisplayTags = (appTags: string[]) => {
  if (!appTags || appTags.length === 0) return []
  return appTags.slice(0, 3)
}

const getTagName = (tagId: string) => {
  const tag = tags.value.find(t => t.id === tagId)
  if (!tag) return tagId
  return getPublicAppTagDisplayName(tag, locale.value as 'zh-CN' | 'en-US')
}

const getExtraTagCount = (appTags: string[]) => {
  if (!appTags || appTags.length <= 3) return 0
  return appTags.length - 3
}

const getExtraTagNames = (appTags: string[]) => {
  if (!appTags || appTags.length <= 3) return []
  return appTags.slice(3).map(tagId => getTagName(tagId))
}

onMounted(() => {
  loadTags()
  loadApps()
})
</script>

<template>
  <a-spin :loading="loading" class="block h-full w-full">
    <div class="p-6 flex flex-col h-full">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-apps :size="18" />
          </a-avatar>
          <div class="text-lg font-medium text-gray-900">{{ t('publicApps.list.title') }}</div>
        </div>
      </div>

      <div class="flex flex-col gap-4 mb-6">
        <div class="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1">
          <span class="text-sm text-gray-500 mr-1 whitespace-nowrap">
            {{ t('publicApps.list.tags') }}
          </span>
          <a
            v-for="tag in tags"
            :key="tag.id"
            class="rounded-lg px-3 h-8 leading-8 hover:bg-gray-200 transition-all cursor-pointer whitespace-nowrap text-sm"
            :class="selectedTags.includes(tag.id) ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-gray-100 text-gray-700'"
            @click="toggleTag(tag.id)"
          >
            {{ getTagName(tag.id) }}
          </a>
        </div>
        <a-input-search
          v-model="searchWord"
          :placeholder="t('publicApps.list.searchPlaceholder')"
          class="w-full sm:w-[240px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide" @scroll="handleScroll">
        <a-row :gutter="[20, 20]">
          <a-col v-for="app in apps" :key="app.id" :span="6">
            <a-card hoverable class="h-full rounded-lg flex flex-col" :body-style="{ padding: '16px' }">
              <button type="button" class="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg flex-1" @click="handlePreview(app)">
                <!-- 顶部应用名称和标签 -->
                <div class="flex items-center gap-3 mb-3">
                  <a-avatar :size="40" shape="square" :image-url="app.icon" />
                  <div class="flex-1 min-w-0">
                    <div class="text-base font-bold text-gray-900 truncate">{{ app.name }}</div>
                    <div class="flex items-center gap-1 flex-wrap">
                      <a-tag v-for="tag in getDisplayTags(app.tags)" :key="tag" size="small">
                        {{ getTagName(tag) }}
                      </a-tag>
                      <a-tag v-if="getExtraTagCount(app.tags) > 0" size="small" class="cursor-help" :title="getExtraTagNames(app.tags).join(', ')">
                        +{{ getExtraTagCount(app.tags) }}
                      </a-tag>
                    </div>
                  </div>
                </div>

                <!-- 应用描述 -->
                <resource-card-description :text="app.description" />
              </button>

              <!-- 发布者、发布时间和Fork按钮 -->
              <div class="mt-3 flex items-center justify-between gap-3">
                <div class="flex min-w-0 flex-1 items-center gap-1.5">
                  <a-avatar :size="18" :image-url="app.creator_avatar" />
                  <div class="min-w-0 flex-1 truncate text-xs text-gray-400">
                    {{ app.creator_name }} · {{ t('publicApps.list.publishedAt', { time: formatTimestampShort(app.published_at) }) }}
                  </div>
                </div>
                <a-tooltip :content="app.is_forked ? t('publicApps.list.addedToSpace') : t('publicApps.list.addToSpace')">
                  <button
                    type="button"
                    class="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 hover:scale-105"
                    :class="app.is_forked ? 'bg-gray-100 cursor-not-allowed opacity-50' : 'bg-blue-50 hover:bg-blue-100'"
                    :disabled="app.is_forked"
                    @click.stop="handleFork(app)"
                  >
                    <icon-branch
                      :size="16"
                      :style="{ color: app.is_forked ? '#9ca3af' : '#3b82f6' }"
                    />
                  </button>
                </a-tooltip>
              </div>
            </a-card>
          </a-col>

          <a-col v-if="apps.length === 0" :span="24">
            <a-empty :description="t('publicApps.list.empty')" class="py-20" />
          </a-col>
        </a-row>

        <div v-if="apps.length > 0" class="py-4 text-center">
          <a-space v-if="loading">
            <a-spin />
            <div class="text-gray-400">{{ t('publicApps.list.loading') }}</div>
          </a-space>
          <div v-else-if="!hasMore" class="text-gray-400">{{ t('publicApps.list.loadedAll') }}</div>
        </div>
      </div>
    </div>
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
</style>
