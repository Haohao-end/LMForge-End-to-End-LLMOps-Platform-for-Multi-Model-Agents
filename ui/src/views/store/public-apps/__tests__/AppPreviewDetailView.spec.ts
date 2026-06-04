import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('AppPreviewDetailView', () => {
  it('uses flex-based layout instead of viewport height constants', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/store/public-apps/AppPreviewDetailView.vue'),
      'utf8',
    )

    expect(source).not.toContain('100vh-77px')
    expect(source).not.toContain('100vh-141px')
    expect(source).toContain('grid-cols-[minmax(0,13fr)_minmax(0,12fr)]')
  })
})
