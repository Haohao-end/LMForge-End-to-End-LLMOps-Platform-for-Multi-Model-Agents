import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('AppPreviewLayoutView', () => {
  it('uses a flex-1 container for routed content', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/store/public-apps/AppPreviewLayoutView.vue'),
      'utf8',
    )

    expect(source).toContain('class="flex flex-1 min-h-0 w-full flex-col overflow-hidden"')
    expect(source).toContain('<div class="flex min-h-0 flex-1 overflow-hidden">')
    expect(source).toContain(':key="String(route.params?.app_id ?? \'\')"')
    expect(source).toContain('<router-view')
    expect(source).toContain(':app="app"')
    expect(source).toContain('watch(')
    expect(source).not.toContain('min-h-screen flex flex-col h-full overflow-hidden')
  })
})
