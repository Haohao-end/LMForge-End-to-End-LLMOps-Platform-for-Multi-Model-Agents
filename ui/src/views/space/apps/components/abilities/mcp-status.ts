import type { McpBinding, McpToolSnapshot } from '@/models/app'
import { i18n } from '@/i18n'

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
const t = (key: string, params?: Record<string, unknown>) =>
  params ? i18n.global.t(key, params) : i18n.global.t(key)

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
  const isRetryable = Boolean((snapshot as Record<string, unknown> | undefined)?.retryable)

  if (!isEnabled) {
    return {
      key: 'disabled',
      label: t('appStudio.abilities.mcp.status.unavailable'),
      color: 'gray',
      tooltip: t('appStudio.abilities.mcp.status.tooltipDisabled'),
      show_help: true,
    }
  }

  if (!snapshot) {
    return {
      key: 'warming',
      label: t('appStudio.abilities.mcp.status.warming'),
      color: 'orange',
      tooltip: t('appStudio.abilities.mcp.status.tooltipWarming'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'ready') {
    return {
      key: 'ready',
      label: t('appStudio.abilities.mcp.status.ready'),
      color: 'green',
      tooltip: '',
      show_help: false,
    }
  }

  if (snapshotStatus === 'stale' && hasTools) {
    return {
      key: 'ready',
      label: t('appStudio.abilities.mcp.status.ready'),
      color: 'green',
      tooltip: isRetryable
        ? t('appStudio.abilities.mcp.status.tooltipStaleRetryable')
        : t('appStudio.abilities.mcp.status.tooltipStaleFailed'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'failed' && hasTools) {
    return {
      key: 'ready',
      label: t('appStudio.abilities.mcp.status.ready'),
      color: 'green',
      tooltip: isRetryable
        ? t('appStudio.abilities.mcp.status.tooltipFailedRetryable')
        : t('appStudio.abilities.mcp.status.tooltipFailedNoRetry'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'failed' && !hasTools && !isRetryable) {
    return {
      key: 'failed',
      label: t('appStudio.abilities.mcp.status.failed'),
      color: 'gray',
      tooltip: t('appStudio.abilities.mcp.status.tooltipExpired'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'empty') {
    return {
      key: 'empty',
      label: t('appStudio.abilities.mcp.status.unavailable'),
      color: 'gray',
      tooltip: t('appStudio.abilities.mcp.status.tooltipEmpty'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'unsupported') {
    return {
      key: 'unsupported',
      label: t('appStudio.abilities.mcp.status.unavailable'),
      color: 'gray',
      tooltip: normalizeText((snapshot as Record<string, unknown> | undefined)?.last_error)
        || t('appStudio.abilities.mcp.status.tooltipUnsupported'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'disabled') {
    return {
      key: 'disabled',
      label: t('appStudio.abilities.mcp.status.unavailable'),
      color: 'gray',
      tooltip: t('appStudio.abilities.mcp.status.tooltipDisabled'),
      show_help: true,
    }
  }

  if (snapshotStatus === 'warming' || snapshotStatus === 'failed') {
    return {
      key: 'warming',
      label: t('appStudio.abilities.mcp.status.warming'),
      color: 'orange',
      tooltip: snapshotStatus === 'failed' && isRetryable
        ? t('appStudio.abilities.mcp.status.tooltipFailedRetryLater')
        : snapshotStatus === 'failed'
          ? t('appStudio.abilities.mcp.status.tooltipFailedStopped')
        : t('appStudio.abilities.mcp.status.tooltipWarming'),
      show_help: true,
    }
  }

  return {
    key: 'warming',
    label: t('appStudio.abilities.mcp.status.warming'),
    color: 'orange',
    tooltip: t('appStudio.abilities.mcp.status.tooltipWarmingChecking'),
    show_help: true,
  }
}
