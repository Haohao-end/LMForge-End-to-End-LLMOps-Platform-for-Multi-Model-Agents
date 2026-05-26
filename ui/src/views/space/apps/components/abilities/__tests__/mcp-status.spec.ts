import { describe, expect, it } from 'vitest'

import { resolveMcpBindingStatus } from '../mcp-status'

const makeBinding = (overrides: Record<string, unknown> = {}) => ({
  name: '12306-mcp',
  description: '12306 车票查询 MCP',
  transport: 'streamable_http',
  url: 'https://mcp.api-inference.modelscope.net/fbc1920197624e/mcp',
  command: '',
  enabled: true,
  headers: [],
  tool_names: [],
  timeout_seconds: 30,
  args: [],
  env: {},
  provider_key: 'catalog::QEpvb29vb2svMTIzMDYtbWNw',
  source_type: 'catalog',
  source_key: '@Joooook/12306-mcp',
  source_url: 'https://www.modelscope.cn/mcp/servers/@Joooook/12306-mcp',
  label: '12306 车票查询 MCP',
  icon: '',
  category: 'productivity',
  ...overrides,
})

const makeSnapshot = (overrides: Record<string, unknown> = {}) => ({
  binding_identity: 'catalog::QEpvb29vb2svMTIzMDYtbWNw',
  binding_hash: 'binding-hash',
  binding: makeBinding(),
  status: 'failed',
  tool_definitions: [],
  tool_names: [],
  tool_count: 0,
  schema_hash: 'schema-hash',
  last_attempt_at: 1710000000,
  last_success_at: null,
  last_error: 'record not found',
  retry_count: 1,
  retryable: false,
  ...overrides,
})

describe('resolveMcpBindingStatus', () => {
  it('marks permanently failed snapshots as unavailable', () => {
    const status = resolveMcpBindingStatus(makeBinding(), [makeSnapshot()])

    expect(status.key).toBe('failed')
    expect(status.label).toBe('已失效')
    expect(status.color).toBe('gray')
    expect(status.show_help).toBe(true)
    expect(status.tooltip).toContain('更新 URL')
  })

  it('keeps cached tools available when a permanent failure still has tool definitions', () => {
    const status = resolveMcpBindingStatus(
      makeBinding(),
      [
        makeSnapshot({
          status: 'stale',
          tool_definitions: [
            {
              name: 'query_train_info',
            },
          ],
          tool_names: ['query_train_info'],
          tool_count: 1,
          last_success_at: 1710000000,
        }),
      ],
    )

    expect(status.key).toBe('ready')
    expect(status.label).toBe('已可用')
    expect(status.color).toBe('green')
    expect(status.show_help).toBe(true)
    expect(status.tooltip).toContain('远端 MCP 已失效')
  })
})
