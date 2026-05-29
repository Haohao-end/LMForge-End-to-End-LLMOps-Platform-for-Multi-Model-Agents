<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CodeHighLight from '@/components/CodeHighLight.vue'
import {
  getBlockApiOutput,
  getBlockApiShell,
  getContinueConversationOutput,
  getContinueConversationShell,
  getContinueConversationStreamOutput,
  getContinueConversationStreamShell,
  getStreamApiOutput,
  getStreamApiShell,
} from '@/views/openapi/quick-start'

// 动态获取当前域名
const currentOrigin = computed(() => {
  return globalThis.location?.origin || 'http://localhost'
})

// 动态生成 API 端点
const apiEndpoint = computed(() => {
  return `${currentOrigin.value}/api/openapi/chat`
})

// 动态生成示例 URL
const exampleAppUrl = computed(() => {
  return `${currentOrigin.value}/space/apps/`
})
const { t, locale } = useI18n()

// 动态生成 Shell 命令
const blockApiShell = computed(() => getBlockApiShell(apiEndpoint.value, locale.value as 'zh-CN' | 'en-US'))
const blockApiOutput = computed(() => getBlockApiOutput(locale.value as 'zh-CN' | 'en-US'))
const streamApiShell = computed(() => getStreamApiShell(apiEndpoint.value, locale.value as 'zh-CN' | 'en-US'))
const streamApiOutput = computed(() => getStreamApiOutput(locale.value as 'zh-CN' | 'en-US'))
const continueConversationShell = computed(() =>
  getContinueConversationShell(apiEndpoint.value, locale.value as 'zh-CN' | 'en-US'),
)
const continueConversationOutput = computed(() =>
  getContinueConversationOutput(locale.value as 'zh-CN' | 'en-US'),
)
const continueConversationStreamShell = computed(() =>
  getContinueConversationStreamShell(apiEndpoint.value, locale.value as 'zh-CN' | 'en-US'),
)
const continueConversationStreamOutput = computed(() =>
  getContinueConversationStreamOutput(locale.value as 'zh-CN' | 'en-US'),
)
</script>

<template>
  <div class="pb-6">
    <div class="bg-white p-6 rounded-lg h-[calc(100vh-160px)] overflow-scroll scrollbar-w-none">
      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.overviewTitle') }}</h2>
      <p class="text-gray-700 mb-6 leading-relaxed">
        {{ t('openapi.quickStart.overviewDescription') }}
      </p>

      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.prerequisitesTitle') }}</h2>
      <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
        <p class="text-gray-700 mb-2">{{ t('openapi.quickStart.prerequisitesDescription') }}</p>
        <ol class="list-decimal list-inside text-gray-700 space-y-1 ml-2">
          <li>{{ t('openapi.quickStart.prerequisite1') }}</li>
          <li>{{ t('openapi.quickStart.prerequisite2') }}</li>
          <li>{{ t('openapi.quickStart.prerequisite3') }}</li>
        </ol>
      </div>

      <h3 class="text-lg text-gray-900 font-semibold mb-3">{{ t('openapi.quickStart.appIdTitle') }}</h3>
      <div class="bg-gray-50 p-4 rounded-lg mb-6">
        <p class="text-gray-700 mb-2">{{ t('openapi.quickStart.appIdDescription') }}</p>
        <div class="bg-white p-3 rounded border border-gray-200 mb-2">
          <code class="text-sm text-blue-600">{{ exampleAppUrl }}<span class="bg-yellow-200 font-semibold">f7826c92-c7b3-4dde-9fc2-a89788fb4936</span></code>
        </div>
        <p class="text-gray-600 text-sm">
          <span class="inline-block w-2 h-2 bg-yellow-400 rounded-full mr-1"></span>
          {{ t('openapi.quickStart.appIdHint') }}
        </p>
      </div>

      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.apiEndpointTitle') }}</h2>
      <div class="bg-gray-50 p-4 rounded-lg mb-6">
        <p class="text-sm text-gray-600 mb-2">POST</p>
        <code class="text-base font-mono text-gray-900">{{ apiEndpoint }}</code>
      </div>

      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.requestParamsTitle') }}</h2>
      <div class="overflow-x-auto mb-6">
        <table class="min-w-full border border-gray-200 rounded-lg">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.table.name') }}</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.table.type') }}</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.table.required') }}</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.table.description') }}</th>
            </tr>
          </thead>
          <tbody class="bg-white">
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">app_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">{{ t('openapi.quickStart.table.required') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.appIdDescription') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">query</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">{{ t('openapi.quickStart.table.required') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.queryDescription') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">stream</td>
              <td class="px-4 py-3 text-sm text-gray-700">boolean</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">{{ t('openapi.quickStart.table.optional') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.streamDescription') }}</td>
            </tr>
            <tr class="border-b bg-blue-50">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">end_user_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">{{ t('openapi.quickStart.table.autoGenerated') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.endUserId') }}</td>
            </tr>
            <tr class="border-b bg-blue-50">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">conversation_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">{{ t('openapi.quickStart.table.autoGenerated') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.conversationId') }}</td>
            </tr>
            <tr class="border-b bg-blue-50">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">message_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">{{ t('openapi.quickStart.table.autoGenerated') }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.messageId') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6">
        <p class="text-sm text-gray-700">
          <span class="font-semibold">{{ t('openapi.quickStart.tips') }}</span>
          {{ t('openapi.quickStart.firstConversationTip') }}
        </p>
      </div>

      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.examplesTitle') }}</h2>

      <a-tabs type="text" default-active-key="block">
        <a-tab-pane key="block" :title="t('openapi.quickStart.blockTitle')">
          <div class="mb-4">
            <p class="text-gray-700 mb-2 font-medium">{{ t('openapi.quickStart.scenarios') }}</p>
            <p class="text-gray-600 text-sm mb-4">{{ t('openapi.quickStart.blockScenario') }}</p>
          </div>

          <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.requestExample') }}</p>
          <code-high-light language="shell">{{ blockApiShell }}</code-high-light>

          <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.responseExample') }}</p>
          <code-high-light language="json">{{ blockApiOutput }}</code-high-light>
        </a-tab-pane>

        <a-tab-pane key="stream" :title="t('openapi.quickStart.streamTitle')">
          <div class="mb-4">
            <p class="text-gray-700 mb-2 font-medium">{{ t('openapi.quickStart.scenarios') }}</p>
            <p class="text-gray-600 text-sm mb-4">{{ t('openapi.quickStart.streamScenario') }}</p>
          </div>

          <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.requestExample') }}</p>
          <code-high-light language="shell">{{ streamApiShell }}</code-high-light>

          <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.responseExampleStream') }}</p>
          <code-high-light language="json">{{ streamApiOutput }}</code-high-light>
        </a-tab-pane>

        <a-tab-pane key="continue" :title="t('openapi.quickStart.continueTitle')">
          <div class="mb-4">
            <p class="text-gray-700 mb-2 font-medium">{{ t('openapi.quickStart.scenarios') }}</p>
            <p class="text-gray-600 text-sm mb-4">{{ t('openapi.quickStart.continueScenario') }}</p>
          </div>

          <div class="bg-green-50 border-l-4 border-green-500 p-4 mb-4">
            <p class="text-sm text-gray-700 mb-2">
              <span class="font-semibold">{{ t('openapi.quickStart.continueStepsTitle') }}</span>
            </p>
            <ol class="list-decimal list-inside text-gray-700 text-sm space-y-1 ml-2">
              <li>{{ t('openapi.quickStart.continueStep1') }}</li>
              <li>{{ t('openapi.quickStart.continueStep2') }}</li>
              <li>{{ t('openapi.quickStart.continueStep3') }}</li>
            </ol>
          </div>

          <a-tabs type="text" default-active-key="continue-block">
            <a-tab-pane key="continue-block" :title="t('openapi.quickStart.continueBlockTitle')">
              <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.requestExample') }}</p>
              <code-high-light language="shell">{{ continueConversationShell }}</code-high-light>

              <p class="text-gray-700 mb-2 font-semibold mt-4">{{ t('openapi.quickStart.responseExample') }}</p>
              <code-high-light language="json">{{ continueConversationOutput }}</code-high-light>

              <div class="bg-amber-50 border-l-4 border-amber-500 p-4 mt-4">
                <p class="text-sm text-gray-700">
                  <span class="font-semibold">{{ t('openapi.quickStart.continueKeyPointTitle') }}</span>
                  {{ t('openapi.quickStart.continueKeyPointDescription') }}
                </p>
              </div>
            </a-tab-pane>

            <a-tab-pane key="continue-stream" :title="t('openapi.quickStart.continueStreamTitle')">
              <p class="text-gray-700 mb-2 font-semibold">{{ t('openapi.quickStart.requestExample') }}</p>
              <code-high-light language="shell">{{ continueConversationStreamShell }}</code-high-light>

              <p class="text-gray-700 mb-2 font-semibold mt-4">{{ t('openapi.quickStart.responseExampleStream') }}</p>
              <code-high-light language="json">{{ continueConversationStreamOutput }}</code-high-light>

              <div class="bg-amber-50 border-l-4 border-amber-500 p-4 mt-4">
                <p class="text-sm text-gray-700">
                  <span class="font-semibold">{{ t('openapi.quickStart.continueKeyPointTitle') }}</span>
                  {{ t('openapi.quickStart.continueStreamKeyPointDescription') }}
                </p>
              </div>
            </a-tab-pane>
          </a-tabs>

          <p class="text-gray-600 text-sm mt-4">
            <span class="inline-block w-2 h-2 bg-green-500 rounded-full mr-1"></span>
            {{ t('openapi.quickStart.continueNeedIds') }}
          </p>
        </a-tab-pane>
      </a-tabs>

      <h2 class="text-xl text-gray-900 font-bold mb-4 mt-8">{{ t('openapi.quickStart.responseFieldsTitle') }}</h2>
      <div class="overflow-x-auto mb-6">
        <table class="min-w-full border border-gray-200 rounded-lg">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.responseFieldLabel') }}</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.responseFieldType') }}</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">{{ t('openapi.quickStart.responseFieldDescription') }}</th>
            </tr>
          </thead>
          <tbody class="bg-white">
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">answer</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.answer') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">conversation_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.conversationId') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">end_user_id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.endUserId') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">id</td>
              <td class="px-4 py-3 text-sm text-gray-700">string</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.id') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">agent_thoughts</td>
              <td class="px-4 py-3 text-sm text-gray-700">array</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.agentThoughts') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">latency</td>
              <td class="px-4 py-3 text-sm text-gray-700">number</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.latency') }}</td>
            </tr>
            <tr class="border-b">
              <td class="px-4 py-3 text-sm font-mono text-gray-900">total_token_count</td>
              <td class="px-4 py-3 text-sm text-gray-700">number</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ t('openapi.quickStart.responseFields.totalTokenCount') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 class="text-xl text-gray-900 font-bold mb-4">{{ t('openapi.quickStart.faqTitle') }}</h2>
      <div class="space-y-4 mb-6">
        <div class="border border-gray-200 rounded-lg p-4">
          <h3 class="text-base font-semibold text-gray-900 mb-2">Q: {{ t('openapi.quickStart.faq1Question') }}</h3>
          <p class="text-sm text-gray-700">
            A: {{ t('openapi.quickStart.faq1Answer') }}
          </p>
        </div>

        <div class="border border-gray-200 rounded-lg p-4">
          <h3 class="text-base font-semibold text-gray-900 mb-2">Q: {{ t('openapi.quickStart.faq2Question') }}</h3>
          <p class="text-sm text-gray-700">
            A: {{ t('openapi.quickStart.faq2Answer') }}
          </p>
        </div>

        <div class="border border-gray-200 rounded-lg p-4">
          <h3 class="text-base font-semibold text-gray-900 mb-2">Q: {{ t('openapi.quickStart.faq3Question') }}</h3>
          <p class="text-sm text-gray-700">
            A: {{ t('openapi.quickStart.faq3Answer') }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
