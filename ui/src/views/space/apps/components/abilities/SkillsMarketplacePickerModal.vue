<script setup lang="ts">
import { computed, onMounted, ref, watch, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import { apiPrefix } from '@/config'
import { getErrorMessage } from '@/utils/error'
import { getSkillCategories, getSkillsWithPage } from '@/services/skill'
import type { SkillBinding, SkillCategory, SkillPackage } from '@/models/skill'

const props = defineProps({
  visible: { type: Boolean, default: false },
  selected_bindings: {
    type: Array as PropType<SkillBinding[]>,
    default: () => [],
  },
})

const emits = defineEmits(['update:visible', 'select'])

const loading = ref(false)
const categories = ref<SkillCategory[]>([])
const skills = ref<SkillPackage[]>([])
const selectedCategory = ref('all')
const searchWord = ref('')

const hideModal = () => emits('update:visible', false)

const selectedSkillIdSet = computed(() => {
  const set = new Set<string>()
  ;(props.selected_bindings || []).forEach((binding) => {
    const skillId = String(binding.skill_id || binding.id || '').trim()
    if (skillId) {
      set.add(skillId)
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

const isSelectedSkill = (skill: SkillPackage) => {
  return selectedSkillIdSet.value.has(String(skill.id || '').trim())
}

const loadCategories = async () => {
  try {
    const res = await getSkillCategories()
    categories.value = res.data.categories || []
  } catch (_error: unknown) {
    categories.value = []
  }
}

const loadSkills = async () => {
  loading.value = true
  try {
    const res = await getSkillsWithPage({
      current_page: 1,
      page_size: 50,
      search_word: searchWord.value.trim(),
      category: selectedCategory.value === 'all' ? '' : selectedCategory.value,
    })
    skills.value = res.data.list || []
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 Skills 广场失败'))
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  await loadSkills()
}

const handleCategoryChange = async (category: string) => {
  selectedCategory.value = category
  await loadSkills()
}

const handleSelect = (skill: SkillPackage) => {
  if (isSelectedSkill(skill)) return
  emits('select', skill)
}

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    await loadCategories()
    await loadSkills()
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
        <div class="text-lg font-bold text-gray-800">从 Skills 广场添加</div>
        <div class="text-xs text-gray-500">点击添加后会直接写入当前应用的 Skills 绑定</div>
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
          placeholder="搜索 Skills"
          class="w-full sm:w-[280px] bg-white rounded-lg border-gray-300"
          @search="handleSearch"
        />
      </div>

      <a-spin :loading="loading" class="block flex-1 overflow-hidden">
        <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="skill in skills"
              :key="skill.id"
              :xs="24"
              :sm="12"
              :md="8"
              :lg="6"
              :xl="6"
            >
              <a-card class="h-full rounded-lg" hoverable>
                <div class="flex items-start gap-3">
                  <a-avatar :size="40" shape="square" class="bg-gray-100">
                    <img
                      v-if="skill.icon"
                      :src="normalizeIconUrl(skill.icon)"
                      :alt="skill.label"
                      class="w-full h-full object-cover"
                    />
                    <span v-else class="text-gray-700 font-semibold">
                      {{ (skill.label || skill.name || 'S')[0] }}
                    </span>
                  </a-avatar>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 min-w-0">
                      <div class="text-sm font-semibold text-gray-900 truncate">{{ skill.label }}</div>
                    </div>
                    <div class="text-xs text-gray-500 line-clamp-1">
                      {{ skill.source_key }}
                      <template v-if="skill.tool_count > 0"> · {{ skill.tool_count }} 工具</template>
                    </div>
                  </div>
                </div>

                <div class="mt-3 text-sm text-gray-600 line-clamp-3">
                  {{ skill.description }}
                </div>

                <div class="flex items-center gap-2 flex-wrap mt-3">
                  <a-tag size="small" color="arcoblue">{{ skill.category }}</a-tag>
                  <a-tag size="small" color="orangered">{{ skill.executor_type }}</a-tag>
                </div>

                <div class="flex items-center justify-between gap-2 mt-4">
                  <a-button
                    type="primary"
                    size="small"
                    :disabled="isSelectedSkill(skill)"
                    @click.stop="handleSelect(skill)"
                  >
                    {{ isSelectedSkill(skill) ? '已添加' : '添加到应用' }}
                  </a-button>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>
      </a-spin>
    </div>
  </a-modal>
</template>
