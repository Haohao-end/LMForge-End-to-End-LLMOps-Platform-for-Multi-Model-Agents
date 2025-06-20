<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const createType = ref<string>('')
const searchWord = ref(route.query?.search_word || '')

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
  () => route.query?.search_word,
  () => {
    searchWord.value = route.query?.search_word || ''
  },
)
</script>

<template>
  <!-- 调整边距+隐藏 -->
  <div class="px-6 flex flex-col overflow-hidden h-full">
    <div class="pt-6 sticky top-0 z-20 bg-gray-50">
      <!-- 顶层标题+创建按钮 -->
      <div class="flex items-center justify-between mb-6">
        <!-- 左侧标题 -->
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-user :size="18" />
          </a-avatar>
          <div class="text-lg font-medium text-gray-900">个人空间</div>
        </div>
        <!-- 创建按钮 -->
        <a-button
          v-if="route.path.startsWith('/space/apps')"
          type="primary"
          class="rounded-lg"
          @click="createType = 'app'"
        >
          创建 AI 应用
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/tools')"
          type="primary"
          class="rounded-lg"
          @click="createType = 'tool'"
        >
          创建自定义插件
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/workflows')"
          type="primary"
          class="rounded-lg"
          @click="createType = 'workflow'"
        >
          创建工作流
        </a-button>
        <a-button
          v-if="route.path.startsWith('/space/datasets')"
          type="primary"
          class="rounded-lg"
          @click="createType = 'dataset'"
        >
          创建知识库
        </a-button>
      </div>
      <!-- 导航按钮+搜索框 -->
      <div class="flex items-center justify-between mb-6">
        <!-- 左侧导航 -->
        <div class="flex items-center gap-2">
          <router-link
            to="/space/apps"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            AI应用
          </router-link>
          <router-link
            to="/space/tools"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            插件
          </router-link>
          <router-link
            to="/space/workflows"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            工作流
          </router-link>
          <router-link
            to="/space/datasets"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            知识库
          </router-link>
        </div>
        <!-- 右侧搜索 -->
        <a-input-search
          v-model="searchWord"
          placeholder="输入关键词进行搜索"
          class="w-[240px] bg-white rounded-lg border-gray-300"
          @search="search"
        />
      </div>
    </div>
    <!-- 中间内容 -->
    <router-view v-model:create-type="createType" />
  </div>
</template>

<style scoped></style>
