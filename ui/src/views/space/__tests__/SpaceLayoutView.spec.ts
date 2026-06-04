import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('SpaceLayoutView', () => {
  it('wraps routed content in a flex container so nested pages can scroll', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/space/SpaceLayoutView.vue'),
      'utf8',
    )

    expect(source).toContain('<div v-if="isLoggedIn" class="flex min-h-0 flex-1 overflow-hidden">')
    expect(source).toContain('<router-view />')
  })
})
