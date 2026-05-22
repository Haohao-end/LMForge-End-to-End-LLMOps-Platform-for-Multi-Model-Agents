<script setup lang="ts">
import { computed, nextTick, type PropType, ref, watch } from 'vue'
import { useUpdateDraftAppConfig } from '@/hooks/use-app'
import { cloneDeep, isEqual } from 'lodash'
import { Message } from '@arco-design/web-vue'
import type { McpBinding, McpToolSnapshot } from '@/models/app'
import McpMarketplacePickerModal from './McpMarketplacePickerModal.vue'
import { resolveMcpBindingStatus } from './mcp-status'

type McpBindingForm = McpBinding & {
  headers_text: string
  tool_names_text: string
  args_text: string
  env_text: string
}

const defaultForm = (): McpBindingForm => ({
  name: '',
  description: '',
  transport: 'streamable_http',
  url: '',
  command: '',
  enabled: true,
  headers: [],
  tool_names: [],
  timeout_seconds: 30,
  args: [],
  env: {},
  headers_text: '[]',
  tool_names_text: '',
  args_text: '',
  env_text: '{}',
})

const props = defineProps({
  app_id: { type: String, default: '', required: true },
  mcp_bindings: {
    type: Array as PropType<McpBinding[]>,
    default: () => [],
    required: true,
  },
  mcp_tool_snapshots: {
    type: Array as PropType<McpToolSnapshot[]>,
    default: () => [],
  },
})
const emits = defineEmits(['update:mcp_bindings', 'reload-draft-app-config'])
const { handleUpdateDraftAppConfig } = useUpdateDraftAppConfig()
const mcpBindingsModalVisible = ref(false)
const isMcpBindingsInit = ref(false)
const activateMcpBindings = ref<McpBindingForm[]>([])
const originMcpBindings = ref<McpBindingForm[]>([])
const editingIndex = ref<number>(-1)
const bindingForm = ref<McpBindingForm>(defaultForm())
const showMarketplacePickerModal = ref(false)
const hasLocalMcpBindingChanges = computed(() => !isEqual(activateMcpBindings.value, originMcpBindings.value))

const stripBindingForm = (binding: McpBindingForm): McpBinding => {
  const { headers_text, tool_names_text, args_text, env_text, ...rest } = binding
  return rest
}

const normalizeBindingToForm = (binding: McpBinding): McpBindingForm => {
  return {
    ...defaultForm(),
    ...binding,
    headers_text: JSON.stringify(binding.headers ?? [], null, 2),
    tool_names_text: (binding.tool_names ?? []).join(', '),
    args_text: (binding.args ?? []).join(', '),
    env_text: JSON.stringify(binding.env ?? {}, null, 2),
  }
}

const buildBindingIdentity = (binding: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>) => {
  if (String(binding.provider_key || '').trim()) {
    return `provider_key:${String(binding.provider_key || '').trim()}`
  }
  return `${String(binding.transport || '').trim()}:${String(binding.url || binding.command || '').trim()}:${String(binding.name || '').trim()}`
}

const buildBindingSignatures = (binding: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>) => {
  const signatures = [buildBindingIdentity(binding)]
  const providerKey = String(binding.provider_key || '').trim()
  if (providerKey) {
    signatures.push(`provider_key:${providerKey}`)
  }
  const transport = String(binding.transport || '').trim()
  const identity = `${transport}:${String(binding.url || binding.command || '').trim()}:${String(binding.name || '').trim()}`
  signatures.push(identity)
  return signatures
}

const isSameBinding = (
  left: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>,
  right: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>,
) => {
  const rightSignatures = new Set(buildBindingSignatures(right))
  return buildBindingSignatures(left).some((signature) => rightSignatures.has(signature))
}

const closeMcpBindingsModal = () => {
  mcpBindingsModalVisible.value = false
  editingIndex.value = -1
  bindingForm.value = defaultForm()
}

const syncLocalBindings = (newBindings: McpBindingForm[]) => {
  const normalized = cloneDeep(newBindings)
  originMcpBindings.value = normalized
  activateMcpBindings.value = cloneDeep(normalized)
  isMcpBindingsInit.value = true
}

const getBindingStatus = (binding: McpBindingForm) => resolveMcpBindingStatus(binding, props.mcp_tool_snapshots || [])

const openEditModal = (idx: number) => {
  const binding = activateMcpBindings.value[idx]
  if (!binding) return
  editingIndex.value = idx
  bindingForm.value = normalizeBindingToForm(binding)
  mcpBindingsModalVisible.value = true
}

const openMarketplacePicker = () => {
  showMarketplacePickerModal.value = true
}

const handleCancelMcpBindingsModal = () => {
  closeMcpBindingsModal()
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

const handleSubmitBinding = async () => {
  const form = bindingForm.value
  if (!form.name.trim()) {
    Message.warning('请填写 MCP 名称')
    return
  }
  if (!form.description.trim()) {
    Message.warning('请填写 MCP 描述')
    return
  }

  const transport = String(form.transport || 'streamable_http').trim()
  if (['http', 'sse', 'streamable_http', 'streamable-http'].includes(transport)) {
    if (!String(form.url || '').trim()) {
      Message.warning('请填写 MCP 地址')
      return
    }
  }
  if (transport === 'stdio' && !String(form.command || '').trim()) {
    Message.warning('请填写 MCP 命令')
    return
  }

  let headers: Array<{ key: string; value: string }> = []
  let env: Record<string, string> = {}
  try {
    headers = parseJsonArray(form.headers_text).map((item) => ({
      key: String(item?.key || '').trim(),
      value: String(item?.value || '').trim(),
    })).filter((item) => item.key)
    env = parseJsonObject(form.env_text)
  } catch (error) {
    Message.warning(`高级配置 JSON 格式错误: ${(error as Error).message}`)
    return
  }

  const toolNames = String(form.tool_names_text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  const args = String(form.args_text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  const nextBinding: McpBindingForm = {
    ...defaultForm(),
    ...form,
    name: form.name.trim(),
    description: form.description.trim(),
    transport,
    url: String(form.url || '').trim(),
    command: String(form.command || '').trim(),
    enabled: Boolean(form.enabled),
    headers,
    tool_names: toolNames,
    timeout_seconds: Number(form.timeout_seconds || 30),
    args,
    env,
    headers_text: JSON.stringify(headers, null, 2),
    tool_names_text: toolNames.join(', '),
    args_text: args.join(', '),
    env_text: JSON.stringify(env, null, 2),
  }

  const newBindings = [...activateMcpBindings.value]
  if (editingIndex.value === -1) {
    if (newBindings.length >= 5) {
      Message.warning('MCP 绑定已超过 5 个，无法继续添加')
      return
    }
    newBindings.push(nextBinding)
  } else {
    newBindings.splice(editingIndex.value, 1, nextBinding)
  }

  await handleUpdateDraftAppConfig(props.app_id, {
    mcp_bindings: newBindings.map((item) => stripBindingForm(item)),
  })

  syncLocalBindings(newBindings)
  await nextTick()
  emits('update:mcp_bindings', cloneDeep(newBindings.map((item) => stripBindingForm(item))))
  emits('reload-draft-app-config')
  closeMcpBindingsModal()
}

const handleDeleteBinding = async (idx: number) => {
  const newBindings = [...activateMcpBindings.value]
  newBindings.splice(idx, 1)

  await handleUpdateDraftAppConfig(props.app_id, {
    mcp_bindings: newBindings.map((item) => stripBindingForm(item)),
  })

  syncLocalBindings(newBindings)
  emits('update:mcp_bindings', cloneDeep(newBindings.map((item) => stripBindingForm(item))))
  emits('reload-draft-app-config')
}

const handleSelectMarketplaceBinding = async (binding: McpBinding) => {
  const nextBinding = normalizeBindingToForm(binding)
  const duplicate = activateMcpBindings.value.some((item) => isSameBinding(item, nextBinding))
  if (duplicate) {
    Message.warning('该 MCP 已添加到当前应用')
    return
  }

  if (activateMcpBindings.value.length >= 5) {
    Message.warning('MCP 绑定已超过 5 个，无法继续添加')
    return
  }

  const newBindings = [...activateMcpBindings.value, nextBinding]
  await handleUpdateDraftAppConfig(props.app_id, {
    mcp_bindings: newBindings.map((item) => stripBindingForm(item)),
  })

  syncLocalBindings(newBindings)
  await nextTick()
  emits('update:mcp_bindings', cloneDeep(newBindings.map((item) => stripBindingForm(item))))
  emits('reload-draft-app-config')
  Message.success('已添加 MCP 绑定')
  showMarketplacePickerModal.value = false
}

watch(
  () => props.mcp_bindings,
  (newValue) => {
    const initData = (newValue || []).map((binding) => normalizeBindingToForm(binding))
    if (!isMcpBindingsInit.value || !hasLocalMcpBindingChanges.value) {
      activateMcpBindings.value = cloneDeep(initData)
      originMcpBindings.value = cloneDeep(initData)
      isMcpBindingsInit.value = true
    }
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <a-collapse-item key="mcp_bindings" class="app-ability-item">
    <template #header>
      <div class="text-gray-700 font-bold">MCP</div>
    </template>
    <template #extra>
      <a-button size="mini" type="text" class="!text-gray-700" @click.stop="openMarketplacePicker">
        <template #icon>
          <icon-plus />
        </template>
      </a-button>
    </template>

    <div v-if="activateMcpBindings.length > 0" class="flex flex-col gap-2">
        <div
        v-for="(binding, idx) in activateMcpBindings"
        :key="`${binding.name}-${idx}`"
        class="flex items-start justify-between gap-3 bg-white p-3 rounded-lg cursor-pointer hover:shadow-sm group"
        @click="openEditModal(idx)"
      >
        <div class="flex flex-col gap-1 min-w-0 flex-1">
          <div class="flex items-center gap-2 min-w-0">
            <div class="text-gray-700 font-bold truncate">{{ binding.name }}</div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <a-tag size="small" :color="getBindingStatus(binding).color">
                {{ getBindingStatus(binding).label }}
              </a-tag>
              <a-tooltip
                v-if="getBindingStatus(binding).show_help && getBindingStatus(binding).tooltip"
                :content="getBindingStatus(binding).tooltip"
                position="top"
              >
                <icon-question-circle class="text-gray-400 text-sm" />
              </a-tooltip>
            </div>
            <a-tag size="small" color="arcoblue">{{ binding.transport }}</a-tag>
          </div>
          <div class="text-xs text-gray-500 truncate">{{ binding.description }}</div>
          <div class="text-xs text-gray-400 truncate">
            {{ binding.url || binding.command || '未配置地址' }}
          </div>
        </div>
        <a-button
          size="mini"
          type="text"
          class="hidden group-hover:block flex-shrink-0 ml-2 !text-red-700 rounded"
          @click.stop="handleDeleteBinding(idx)"
        >
          <template #icon>
            <icon-delete />
          </template>
        </a-button>
      </div>
    </div>
    <div v-else class="text-xs text-gray-500 leading-[22px]">
      点击右上角 + 从 MCP 广场添加 MCP，或点击已有条目继续编辑。绑定后可以在应用运行时动态加载服务器上的工具。
    </div>
  </a-collapse-item>

  <a-modal
    :visible="mcpBindingsModalVisible"
    hide-title
    :footer="false"
    :width="520"
    modal-class="h-[calc(100vh-32px)] right-4"
    @cancel="handleCancelMcpBindingsModal"
  >
    <div class="flex items-center justify-between mb-6">
      <div class="text-lg font-bold text-gray-700">
        {{ editingIndex === -1 ? '新增 MCP 绑定' : '编辑 MCP 绑定' }}
      </div>
      <a-button type="text" class="!text-gray-700" size="small" @click="handleCancelMcpBindingsModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>

    <div class="h-[calc(100vh-180px)] overflow-scroll scrollbar-w-none">
      <div class="space-y-3">
        <a-input v-model="bindingForm.name" placeholder="MCP 名称，例如 12306 MCP" />
        <a-textarea v-model="bindingForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="MCP 描述" />
        <div class="grid grid-cols-2 gap-3">
          <a-select v-model="bindingForm.transport" placeholder="Transport">
            <a-option value="streamable_http">streamable_http</a-option>
            <a-option value="http">http</a-option>
            <a-option value="sse">sse</a-option>
            <a-option value="stdio">stdio</a-option>
          </a-select>
          <a-input-number v-model="bindingForm.timeout_seconds" :min="1" :max="600" placeholder="超时秒数" />
        </div>
        <a-input v-model="bindingForm.url" placeholder="MCP 地址（HTTP / SSE）" />
        <a-input v-model="bindingForm.command" placeholder="stdio 命令（可选）" />
        <a-switch v-model="bindingForm.enabled">
          <template #checked>已启用</template>
          <template #unchecked>已停用</template>
        </a-switch>
        <a-input v-model="bindingForm.tool_names_text" placeholder="工具白名单，英文逗号分隔（可选）" />
        <a-input v-model="bindingForm.args_text" placeholder="stdio args，英文逗号分隔（可选）" />
        <a-textarea
          v-model="bindingForm.headers_text"
          :auto-size="{ minRows: 3, maxRows: 8 }"
          placeholder='请求头 JSON 数组，例如 [{"key":"Authorization","value":"Bearer xxx"}]'
        />
        <a-textarea
          v-model="bindingForm.env_text"
          :auto-size="{ minRows: 3, maxRows: 8 }"
          placeholder='stdio env JSON 对象，例如 {"API_KEY":"xxx"}'
        />
        <div class="flex justify-end gap-2 pt-2">
          <a-button @click="handleCancelMcpBindingsModal">取消</a-button>
          <a-button type="primary" @click="handleSubmitBinding">保存</a-button>
        </div>
      </div>
    </div>
  </a-modal>

  <mcp-marketplace-picker-modal
    v-model:visible="showMarketplacePickerModal"
    :selected_bindings="activateMcpBindings"
    @select="handleSelectMarketplaceBinding"
  />
</template>

<style scoped>
</style>
