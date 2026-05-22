<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { type FileItem, Form, Message, type ValidatedError } from '@arco-design/web-vue'
import IconUploadGenerator from '@/components/IconUploadGenerator.vue'
import { useUploadImage } from '@/hooks/use-upload-file'
import { getErrorMessage } from '@/utils/error'
import { getMcpCategories, getMcpProvider, createMcpProvider, updateMcpProvider, generateMcpIconPreview, regenerateMcpIcon } from '@/services/mcp'
import { mcpSchemaAssistantChat } from '@/services/ai'
import type { McpCategory } from '@/models/mcp'

type HeaderItem = { key: string; value: string }

type McpForm = {
  fileList: FileItem[]
  icon: string
  name: string
  description: string
  category: string
  transport: string
  url: string
  command: string
  headers_text: string
  tool_names_text: string
  args_text: string
  env_text: string
  timeout_seconds: number
}

const props = defineProps({
  mcp_provider_id: { type: String, default: '', required: false },
  visible: { type: Boolean, required: true },
  callback: { type: Function, required: false },
})

const emits = defineEmits(['update:visible', 'update:mcp_provider_id'])

const categories = ref<McpCategory[]>([])
const formRef = ref<InstanceType<typeof Form>>()
const loadingProvider = ref(false)
const submitLoading = ref(false)
const generateLoading = ref(false)
const aiQuestion = ref('')
const aiAnswer = ref('')
const aiLoading = ref(false)
const { image_url, handleUploadImage } = useUploadImage()

const defaultForm = (): McpForm => ({
  fileList: [],
  icon: '',
  name: '',
  description: '',
  category: 'other',
  transport: 'streamable_http',
  url: '',
  command: '',
  headers_text: '[]',
  tool_names_text: '',
  args_text: '',
  env_text: '{}',
  timeout_seconds: 30,
})

const form = ref<McpForm>(defaultForm())

const isEditMode = computed(() => Boolean(props.mcp_provider_id))

const hideModal = () => emits('update:visible', false)

const loadCategories = async () => {
  try {
    const res = await getMcpCategories()
    categories.value = res.data.categories || []
  } catch (_error: unknown) {
    categories.value = []
  }
}

const parseJsonArray = (text: string) => {
  const normalized = String(text || '').trim()
  if (!normalized) return []
  const parsed = JSON.parse(normalized)
  if (!Array.isArray(parsed)) {
    throw new Error('必须是数组')
  }
  return parsed
}

const parseJsonObject = (text: string) => {
  const normalized = String(text || '').trim()
  if (!normalized) return {}
  const parsed = JSON.parse(normalized)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('必须是对象')
  }
  return parsed as Record<string, string>
}

const extractJsonObject = (content: string) => {
  const fenceMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const normalized = (fenceMatch?.[1] ?? content).trim()
  const firstBrace = normalized.indexOf('{')
  const lastBrace = normalized.lastIndexOf('}')
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    return normalized.slice(firstBrace, lastBrace + 1)
  }
  return normalized
}

const applyMcpPayload = (payload: Record<string, any>) => {
  const headers = Array.isArray(payload.headers) ? payload.headers : []
  const toolNames = Array.isArray(payload.tool_names) ? payload.tool_names : []
  const args = Array.isArray(payload.args) ? payload.args : []
  const env = payload.env && typeof payload.env === 'object' && !Array.isArray(payload.env) ? payload.env : {}

  form.value.name = String(payload.name || '').trim()
  form.value.description = String(payload.description || '').trim()
  form.value.category = String(payload.category || 'other').trim() || 'other'
  form.value.transport = String(payload.transport || 'streamable_http').trim() || 'streamable_http'
  form.value.url = String(payload.url || '').trim()
  form.value.command = String(payload.command || '').trim()
  form.value.headers_text = JSON.stringify(headers, null, 2)
  form.value.tool_names_text = toolNames.map((item) => String(item).trim()).filter(Boolean).join(', ')
  form.value.args_text = args.map((item) => String(item).trim()).filter(Boolean).join(', ')
  form.value.env_text = JSON.stringify(env, null, 2)
  form.value.timeout_seconds = Number(payload.timeout_seconds || 30)
  form.value.icon = String(payload.icon || form.value.icon || '')
  if (form.value.icon) {
    form.value.fileList = [{ uid: '1', name: 'MCP图标', url: form.value.icon }]
  }
}

const loadProvider = async (providerId: string) => {
  if (!providerId) {
    form.value = defaultForm()
    return
  }

  loadingProvider.value = true
  try {
    const res = await getMcpProvider(providerId)
    applyMcpPayload(res.data)
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '加载 MCP 详情失败'))
  } finally {
    loadingProvider.value = false
  }
}

const handleUploadIcon = async (file: File) => {
  await handleUploadImage(file)
  form.value.icon = image_url.value
  form.value.fileList = [{ uid: '1', name: 'MCP图标', url: image_url.value }]
  Message.success('图标上传成功')
}

const handleGenerateIcon = async () => {
  if (!form.value.name || form.value.name.trim() === '') {
    Message.warning('请先输入 MCP 名称')
    return
  }

  try {
    generateLoading.value = true
    if (isEditMode.value) {
      const providerId = props.mcp_provider_id
      const res = await regenerateMcpIcon(providerId)
      if (res.data.icon) {
        form.value.icon = res.data.icon
        form.value.fileList = [{ uid: '1', name: 'MCP图标', url: res.data.icon }]
        Message.success('图标生成成功')
      }
    } else {
      const res = await generateMcpIconPreview(form.value.name, form.value.description)
      if (res.data.icon) {
        form.value.icon = res.data.icon
        form.value.fileList = [{ uid: '1', name: 'MCP图标', url: res.data.icon }]
        Message.success('图标生成成功')
      }
    }
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '图标生成失败'))
  } finally {
    generateLoading.value = false
  }
}

const handleGenerateByAI = async () => {
  const question = aiQuestion.value.trim()
  if (!question) {
    Message.warning('请输入你希望生成的 MCP 描述')
    return
  }

  aiLoading.value = true
  aiAnswer.value = ''
  try {
    await mcpSchemaAssistantChat(question, (eventResponse) => {
      const content = String(eventResponse?.data?.content ?? '')
      if (!content) return
      aiAnswer.value += content
    })

    const jsonText = extractJsonObject(aiAnswer.value)
    const payload = JSON.parse(jsonText)
    applyMcpPayload(payload)
    Message.success('AI 已生成 MCP 配置')
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, 'AI 生成 MCP 失败，请调整描述后重试'))
  } finally {
    aiLoading.value = false
  }
}

const handleSubmit = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  if (errors) return

  let headers: HeaderItem[] = []
  let env: Record<string, string> = {}
  try {
    headers = parseJsonArray(form.value.headers_text)
      .map((item) => ({
        key: String(item?.key || '').trim(),
        value: String(item?.value || '').trim(),
      }))
      .filter((item) => item.key)
    env = parseJsonObject(form.value.env_text)
  } catch (error: unknown) {
    Message.warning(`高级配置 JSON 格式错误: ${(error as Error).message}`)
    return
  }

  const toolNames = String(form.value.tool_names_text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  const args = String(form.value.args_text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  const payload = {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    category: form.value.category,
    transport: form.value.transport,
    url: String(form.value.url || '').trim(),
    command: String(form.value.command || '').trim(),
    headers,
    tool_names: toolNames,
    args,
    env,
    timeout_seconds: Number(form.value.timeout_seconds || 30),
    icon: form.value.icon,
  }

  if (payload.transport === 'stdio' && !payload.command) {
    Message.warning('stdio 模式需要填写命令')
    return
  }
  if (['http', 'sse', 'streamable_http', 'streamable-http'].includes(payload.transport) && !payload.url) {
    Message.warning('请填写 MCP 地址')
    return
  }

  submitLoading.value = true
  try {
    if (isEditMode.value) {
      await updateMcpProvider(props.mcp_provider_id, payload)
      Message.success('MCP 更新成功')
    } else {
      await createMcpProvider(payload)
      Message.success('MCP 创建成功')
    }
    emits('update:visible', false)
    emits('update:mcp_provider_id', '')
    props.callback && props.callback()
  } catch (error: unknown) {
    Message.error(getErrorMessage(error, '保存 MCP 失败'))
  } finally {
    submitLoading.value = false
  }
}

watch(
  () => props.visible,
  async (visible) => {
    formRef.value?.resetFields()
    aiQuestion.value = ''
    aiAnswer.value = ''
    if (!visible) {
      form.value = defaultForm()
      emits('update:mcp_provider_id', '')
      return
    }

    await loadCategories()
    if (props.mcp_provider_id) {
      await loadProvider(props.mcp_provider_id)
    } else {
      form.value = defaultForm()
    }
  },
)
</script>

<template>
  <a-modal
    :visible="props.visible"
    hide-title
    :footer="false"
    :width="760"
    modal-class="rounded-xl"
    @cancel="hideModal"
  >
    <div class="flex items-center justify-between mb-6">
      <div class="text-xl font-bold text-gray-800">
        {{ isEditMode ? '编辑 MCP' : '创建 MCP' }}
      </div>
      <a-button type="text" class="!text-gray-500 hover:!text-gray-700" size="small" @click="hideModal">
        <template #icon>
          <icon-close :size="20" />
        </template>
      </a-button>
    </div>

    <a-spin :loading="loadingProvider" class="block">
      <a-form ref="formRef" :model="form" layout="vertical" @submit="handleSubmit">
        <div class="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
          <a-form-item field="icon" hide-label class="lg:sticky lg:top-0 self-start">
            <IconUploadGenerator
              :name="form.name"
              :description="form.description"
              :icon="form.icon"
              :file-list="form.fileList"
              :loading="generateLoading"
              placeholder="MCP"
              :on-upload="handleUploadIcon"
              :on-generate="handleGenerateIcon"
              @update:icon="(val) => (form.icon = val)"
              @update:fileList="(val) => (form.fileList = val)"
            />
          </a-form-item>

          <div class="space-y-4">
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div class="flex items-center justify-between gap-2 mb-3">
                <div class="text-sm font-semibold text-gray-800">AI 生成 MCP 配置</div>
                <a-button type="primary" size="small" :loading="aiLoading" @click="handleGenerateByAI">
                  AI 生成
                </a-button>
              </div>
              <a-textarea
                v-model="aiQuestion"
                :auto-size="{ minRows: 4, maxRows: 6 }"
                placeholder="例如：创建一个天气 MCP，支持查询当前天气和三天天气预报，使用 HTTP 方式，提供 get_current_weather 和 get_forecast 两个工具。"
              />
            </div>

            <a-form-item
              field="name"
              label="MCP 名称"
              asterisk-position="end"
              :rules="[{ required: true, message: 'MCP 名称不能为空' }]"
            >
              <a-input v-model:model-value="form.name" placeholder="请输入 MCP 名称" />
            </a-form-item>

            <a-form-item field="description" label="MCP 描述" asterisk-position="end" :rules="[{ required: true, message: 'MCP 描述不能为空' }]">
              <a-textarea
                v-model:model-value="form.description"
                :auto-size="{ minRows: 3, maxRows: 5 }"
                placeholder="请输入该 MCP 的能力描述"
              />
            </a-form-item>

            <div class="grid grid-cols-2 gap-3">
              <a-form-item field="category" label="分类">
                <a-select v-model:model-value="form.category" placeholder="请选择分类">
                  <a-option v-for="category in categories" :key="category.id" :value="category.id">
                    {{ category.name }}
                  </a-option>
                </a-select>
              </a-form-item>
              <a-form-item field="transport" label="Transport">
                <a-select v-model:model-value="form.transport" placeholder="请选择 transport">
                  <a-option value="streamable_http">streamable_http</a-option>
                  <a-option value="http">http</a-option>
                  <a-option value="sse">sse</a-option>
                  <a-option value="stdio">stdio</a-option>
                </a-select>
              </a-form-item>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <a-form-item field="timeout_seconds" label="超时秒数">
                <a-input-number v-model:model-value="form.timeout_seconds" :min="1" :max="600" />
              </a-form-item>
              <div />
            </div>

            <a-form-item field="url" label="MCP 地址">
              <a-input v-model:model-value="form.url" placeholder="HTTP / SSE / Streamable HTTP 地址" />
            </a-form-item>

            <a-form-item field="command" label="stdio 命令">
              <a-input v-model:model-value="form.command" placeholder="stdio 模式命令，例如 uvx" />
            </a-form-item>

            <a-form-item field="tool_names_text" label="工具白名单">
              <a-input v-model:model-value="form.tool_names_text" placeholder="英文逗号分隔，可选" />
            </a-form-item>

            <a-form-item field="args_text" label="stdio args">
              <a-input v-model:model-value="form.args_text" placeholder="英文逗号分隔，可选" />
            </a-form-item>

            <a-form-item field="headers_text" label="请求头 JSON">
              <a-textarea
                v-model:model-value="form.headers_text"
                :auto-size="{ minRows: 4, maxRows: 8 }"
                placeholder='例如 [{"key":"Authorization","value":"Bearer xxx"}]'
              />
            </a-form-item>

            <a-form-item field="env_text" label="stdio env JSON">
              <a-textarea
                v-model:model-value="form.env_text"
                :auto-size="{ minRows: 4, maxRows: 8 }"
                placeholder='例如 {"API_KEY":"xxx"}'
              />
            </a-form-item>

            <div class="flex items-center justify-end gap-3 pt-2">
              <a-button size="large" class="rounded-lg px-6" @click="hideModal">取消</a-button>
              <a-button
                :loading="submitLoading"
                type="primary"
                html-type="submit"
                size="large"
                class="rounded-lg px-6"
              >
                保存
              </a-button>
            </div>
          </div>
        </div>
      </a-form>
    </a-spin>
  </a-modal>
</template>

<style scoped></style>
