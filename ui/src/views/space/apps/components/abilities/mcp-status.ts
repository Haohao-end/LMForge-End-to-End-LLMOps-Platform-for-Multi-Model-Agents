import type { McpBinding, McpToolSnapshot } from '@/models/app'

export type McpBindingStatusKey =
  | 'ready'
  | 'warming'
  | 'disabled'
  | 'unsupported'
  | 'empty'
  | 'failed'

export type McpBindingStatus = {
  key: McpBindingStatusKey
  label: string
  color: 'green' | 'orange' | 'gray'
  tooltip: string
  show_help: boolean
}

type SnapshotLike = McpToolSnapshot | Record<string, unknown>

const normalizeText = (value: unknown) => String(value ?? '').trim()

export const buildMcpBindingIdentity = (
  binding: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>,
) => {
  const providerKey = normalizeText(binding.provider_key)
  if (providerKey) {
    return providerKey
  }

  const transport = normalizeText(binding.transport).toLowerCase() || 'streamable_http'
  const endpoint = normalizeText(binding.url || binding.command)
  const name = normalizeText(binding.name)
  if (!endpoint && !name) {
    return ''
  }

  return `${transport}:${endpoint}:${name}`
}

const getSnapshotIdentity = (snapshot: SnapshotLike) => {
  const bindingIdentity = normalizeText((snapshot as Record<string, unknown>).binding_identity)
  if (bindingIdentity) {
    return bindingIdentity
  }

  const binding = (snapshot as Record<string, unknown>).binding
  if (binding && typeof binding === 'object' && !Array.isArray(binding)) {
    return buildMcpBindingIdentity(binding as Pick<
      McpBinding,
      'provider_key' | 'transport' | 'url' | 'command' | 'name'
    >)
  }

  return ''
}

export const findMcpBindingSnapshot = (
  binding: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name'>,
  snapshots: SnapshotLike[] = [],
) => {
  const bindingIdentity = buildMcpBindingIdentity(binding)
  if (!bindingIdentity) {
    return undefined
  }

  return snapshots.find((snapshot) => getSnapshotIdentity(snapshot) === bindingIdentity)
}

export const resolveMcpBindingStatus = (
  binding: Pick<McpBinding, 'provider_key' | 'transport' | 'url' | 'command' | 'name' | 'enabled'>,
  snapshots: SnapshotLike[] = [],
): McpBindingStatus => {
  const isEnabled = binding.enabled !== false
  const snapshot = findMcpBindingSnapshot(binding, snapshots)
  const snapshotStatus = normalizeText((snapshot as Record<string, unknown> | undefined)?.status).toLowerCase()
  const toolCount = Number((snapshot as Record<string, unknown> | undefined)?.tool_count || 0)
  const toolDefinitions = (snapshot as Record<string, unknown> | undefined)?.tool_definitions
  const hasToolDefinitions = Array.isArray(toolDefinitions) && toolDefinitions.length > 0
  const hasTools = toolCount > 0 || hasToolDefinitions

  if (!isEnabled) {
    return {
      key: 'disabled',
      label: '不可用',
      color: 'gray',
      tooltip: '该绑定已停用。',
      show_help: true,
    }
  }

  if (!snapshot) {
    return {
      key: 'warming',
      label: '预热中',
      color: 'orange',
      tooltip: '请稍等，系统正在从远端预热 MCP 工具列表。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'ready') {
    return {
      key: 'ready',
      label: '已可用',
      color: 'green',
      tooltip: '',
      show_help: false,
    }
  }

  if (snapshotStatus === 'stale' && hasTools) {
    return {
      key: 'ready',
      label: '已可用',
      color: 'green',
      tooltip: '当前使用的是上次成功同步的工具快照，后台正在刷新。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'failed' && hasTools) {
    return {
      key: 'ready',
      label: '已可用',
      color: 'green',
      tooltip: '远端 MCP 暂时不可达，当前使用上次成功同步的工具快照，后台会继续重试。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'empty') {
    return {
      key: 'empty',
      label: '不可用',
      color: 'gray',
      tooltip: '远端 MCP 暂未返回可用工具。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'unsupported') {
    return {
      key: 'unsupported',
      label: '不可用',
      color: 'gray',
      tooltip: normalizeText((snapshot as Record<string, unknown> | undefined)?.last_error)
        || '当前运行环境不支持该 MCP 传输方式。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'disabled') {
    return {
      key: 'disabled',
      label: '不可用',
      color: 'gray',
      tooltip: '该绑定已停用。',
      show_help: true,
    }
  }

  if (snapshotStatus === 'warming' || snapshotStatus === 'failed') {
    return {
      key: 'warming',
      label: '预热中',
      color: 'orange',
      tooltip: snapshotStatus === 'failed'
        ? '工具列表预热失败，后台会自动重试。'
        : '请稍等，系统正在从远端预热 MCP 工具列表。',
      show_help: true,
    }
  }

  return {
    key: 'warming',
    label: '预热中',
    color: 'orange',
    tooltip: '请稍等，系统正在检查 MCP 工具可用性。',
    show_help: true,
  }
}
