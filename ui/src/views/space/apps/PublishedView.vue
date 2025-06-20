<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGetPublishedConfig, useRegenerateWebAppToken } from '@/hooks/use-app'

// 1.定义页面所需数据
const route = useRoute()
const router = useRouter()
const {
  loading: getPublishedConfigLoading,
  published_config,
  loadPublishedConfig,
} = useGetPublishedConfig()
const {
  loading: regenerateWebAppTokenLoading,
  token,
  handleRegenerateWebAppToken,
} = useRegenerateWebAppToken()
const webAppUrl = computed(() => {
  if (published_config.value?.web_app?.status === 'published') {
    return getFullPath('web-apps-index', {
      token: published_config.value?.web_app?.token,
    })
  }
  return ''
})

// 2.定义获取完整路由路径函数
const getFullPath = (name: string, params = {}, query = {}) => {
  // 通过 router.resolve 获取路由的完整路径
  const { href } = router.resolve({ name, params, query })

  // 如果需要包括 host 部分，结合 window.location.origin
  return window.location.origin + href
}

onMounted(() => {
  loadPublishedConfig(String(route.params?.app_id))
})
</script>

<template>
  <div class="bg-white flex-1 w-full min-h-0 px-6 py-5">
    <!-- 顶部提示信息 -->
    <a-alert class="mb-5">
      如应用访问链接或二维码意外泄露，请及时重新生成或进行停止分发，避免资源出现异常消耗
    </a-alert>
    <!-- 发布渠道列表 -->
    <a-spin :loading="getPublishedConfigLoading" class="w-full">
      <table class="w-full">
        <thead>
          <tr class="h-10 bg-gray-100">
            <th class="font-normal text-left px-4 text-gray-700 border-r border-white">发布渠道</th>
            <th class="font-normal text-left px-4 text-gray-700 border-r border-white">状态</th>
            <th class="font-normal text-left px-4 text-gray-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr class="border-b">
            <td class="py-3 px-4 w-2/3">
              <div class="flex items-center gap-2">
                <a-avatar :size="36" shape="square" class="bg-blue-100">
                  <icon-compass :size="18" class="text-blue-700" />
                </a-avatar>
                <div class="flex flex-col">
                  <div class="text-gray-700 font-semibold">网页版</div>
                  <div class="text-gray-500">可通过访问PC网页立即开始对话。</div>
                </div>
              </div>
            </td>
            <td class="py-3 px-4 w-1/12">
              <a-tag v-if="published_config?.web_app?.status !== 'published'" color="gray" bordered>
                <template #icon>
                  <icon-minus-circle />
                </template>
                未发布
              </a-tag>
              <a-tag v-else color="blue" bordered>
                <template #icon>
                  <icon-check-circle-fill />
                </template>
                已发布
              </a-tag>
            </td>
            <td class="py-3 px-4">
              <div class="flex items-center gap-3">
                <!-- 左侧URL链接 -->
                <div class="flex items-center">
                  <div
                    class="bg-gray-100 h-8 leading-8 px-3 rounded-tl-lg rounded-bl-lg text-gray-700 w-[300px] max-w-[360px] line-clamp-1 break-all"
                  >
                    <template v-if="published_config?.web_app?.status === 'published'">
                      {{ webAppUrl }}
                    </template>
                    <template v-else>应用未发布，无可访问链接</template>
                  </div>
                  <a-button
                    :loading="regenerateWebAppTokenLoading"
                    :disabled="published_config?.web_app?.status !== 'published'"
                    type="primary"
                    class="rounded-tr-lg rounded-br-lg px-2"
                    @click="
                      async () => {
                        // 1.调用API接口发起请求
                        await handleRegenerateWebAppToken(String(route.params?.app_id))

                        // 2.更新web_app对应token的值
                        published_config.web_app.token = token
                      }
                    "
                  >
                    重新生成
                  </a-button>
                </div>
                <!-- 右侧访问按钮 -->
                <a-button class="rounded-lg px-2">
                  <template v-if="published_config?.web_app?.status !== 'published'">
                    立即访问
                  </template>
                  <template v-else>
                    <a :href="webAppUrl" target="_blank">立即访问</a>
                  </template>
                </a-button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </a-spin>
  </div>
</template>

<style scoped></style>
