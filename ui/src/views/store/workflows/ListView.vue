<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  getPublicWorkflows,
  forkPublicWorkflow,
  type PublicWorkflow
} from '@/services/public-workflow'
import { getAppTags, type AppTag } from '@/services/public-app'
import { getErrorMessage } from '@/utils/error'
import { formatTimestampShort } from '@/utils/time-formatter'
import ResourceCardDescription from '@/components/ResourceCardDescription.vue'
import { getPublicAppTagDisplayName } from '@/utils/public-app-tag-display'

const router = useRouter()
const { t, locale } = useI18n()
const loading = ref(false)
const workflows = ref<PublicWorkflow[]>([])
const tags = ref<AppTag[]>([])
const selectedTags = ref<string[]>([])
const searchWord = ref('')
const page = ref(1)
const pageSize = ref(20)
const hasMore = ref(true)

const loadWorkflows = async () => {
  if (loading.value) return
  if (!hasMore.value && page.value > 1) return

  loading.value = true
  try {
    const res = await getPublicWorkflows({
      current_page: page.value,
      page_size: pageSize.value,
      tags: selectedTags.value.join(','),
      search_word: searchWord.value
    })
    const list = res.data.list
    if (page.value === 1) {
      workflows.value = list
    } else {
      workflows.value.push(...list)
    }
    hasMore.value = page.value < res.data.paginator.total_page
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('store.workflows.loadFailed')))
  } finally {
    loading.value = false
  }
}

const loadTags = async () => {
  try {
    const res = await getAppTags()
    tags.value = res.data.tags
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('store.workflows.loadTagsFailed')))
  }
}

const handleFork = async (workflow: PublicWorkflow) => {
  try {
    const res = await forkPublicWorkflow(workflow.id)
    Message.success(t('store.workflows.forkSuccess', { name: res.data.name }))
    await loadWorkflows()
    router.push({ name: 'space-workflows-detail', params: { workflow_id: res.data.id } })
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, t('store.workflows.actionFailed')))
  }
}

const handlePreview = (workflow: PublicWorkflow) => {
  router.push({ name: 'store-workflows-preview', params: { workflow_id: workflow.id } })
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
  loadWorkflows()
}

const handleSearch = () => {
  page.value = 1
  hasMore.value = true
  loadWorkflows()
}

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement | null
  if (!target) return
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollTop + clientHeight >= scrollHeight - 10) {
    if (loading.value || !hasMore.value) return
    page.value += 1
    void loadWorkflows()
  }
}

const getDisplayTags = (workflowTags: string[]) => {
  if (!workflowTags || workflowTags.length === 0) return []
  return workflowTags.slice(0, 3)
}

const getTagName = (tagId: string) => {
  const tag = tags.value.find(t => t.id === tagId)
  if (!tag) return tagId
  return getPublicAppTagDisplayName(tag, locale.value as 'zh-CN' | 'en-US')
}

const getExtraTagCount = (workflowTags: string[]) => {
  if (!workflowTags || workflowTags.length <= 3) return 0
  return workflowTags.length - 3
}

const getExtraTagNames = (workflowTags: string[]) => {
  if (!workflowTags || workflowTags.length <= 3) return []
  return workflowTags.slice(3).map(tagId => getTagName(tagId))
}

onMounted(() => {
  loadTags()
  loadWorkflows()
})
</script>

<template>
  <a-spin :loading="loading" class="block h-full w-full">
    <div class="p-6 flex flex-col h-full">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-relation :size="18" />
          </a-avatar>
          <div class="text-lg font-medium text-gray-900">{{ t('store.workflows.title') }}</div>
        </div>
      </div>

      <div class="flex flex-col gap-4 mb-6">
        <div class="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1">
          <span class="text-sm text-gray-500 mr-1 whitespace-nowrap">{{ t('store.workflows.tags') }}</span>
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
          :placeholder="t('store.workflows.searchPlaceholder')"
          class="w-full sm:w-[240px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide" @scroll="handleScroll">
        <a-row :gutter="[20, 20]">
          <a-col v-for="workflow in workflows" :key="workflow.id" :span="6">
            <a-card hoverable class="h-full rounded-lg flex flex-col" :body-style="{ padding: '16px' }">
              <button type="button" class="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg flex-1" @click="handlePreview(workflow)">
                <!-- 顶部工作流名称和标签 -->
                <div class="flex items-center gap-3 mb-3">
                  <a-avatar :size="40" shape="square" :image-url="workflow.icon" />
                  <div class="flex-1 min-w-0">
                    <div class="text-base font-bold text-gray-900 truncate">{{ workflow.name }}</div>
                    <div class="flex items-center gap-1 flex-wrap">
                      <a-tag v-for="tag in getDisplayTags(workflow.tags)" :key="tag" size="small">
                        {{ getTagName(tag) }}
                      </a-tag>
                      <a-tag v-if="getExtraTagCount(workflow.tags) > 0" size="small" class="cursor-help" :title="getExtraTagNames(workflow.tags).join(', ')">
                        +{{ getExtraTagCount(workflow.tags) }}
                      </a-tag>
                    </div>
                  </div>
                </div>

                <!-- 工作流描述 -->
                <resource-card-description :text="workflow.description" />
              </button>

              <!-- 发布者、发布时间和Fork按钮 -->
              <div class="mt-3 flex items-center justify-between gap-3">
                <div class="flex min-w-0 flex-1 items-center gap-1.5">
                  <a-avatar :size="18" :image-url="workflow.account_avatar" />
                  <div class="min-w-0 flex-1 truncate text-xs text-gray-400">
                    {{ workflow.account_name || t('store.workflows.unknownUser') }} · {{ t('store.workflows.publishedAt', { time: workflow.published_at > 0 ? formatTimestampShort(workflow.published_at) : t('store.workflows.unknownTime') }) }}
                  </div>
                </div>
                <a-tooltip :content="workflow.is_forked ? t('store.workflows.addedToSpace') : t('store.workflows.addToSpace')">
                  <button
                    type="button"
                    class="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 hover:scale-105"
                    :class="workflow.is_forked ? 'bg-gray-100 cursor-not-allowed opacity-50' : 'bg-blue-50 hover:bg-blue-100'"
                    :disabled="workflow.is_forked"
                    @click.stop="handleFork(workflow)"
                  >
                    <icon-branch
                      :size="16"
                      :style="{ color: workflow.is_forked ? '#9ca3af' : '#3b82f6' }"
                    />
                  </button>
                </a-tooltip>
              </div>
            </a-card>
          </a-col>
          <a-col v-if="workflows.length === 0" :span="24"><a-empty :description="t('store.workflows.empty')" class="py-20" /></a-col>
        </a-row>

        <div v-if="workflows.length > 0" class="py-4 text-center">
          <a-space v-if="loading">
            <a-spin />
            <div class="text-gray-400">{{ t('store.workflows.loading') }}</div>
          </a-space>
          <div v-else-if="!hasMore" class="text-gray-400">{{ t('store.workflows.loadedAll') }}</div>
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
