import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const source = readFileSync(
  resolve(process.cwd(), 'src/views/space/apps/components/PresetPromptTextareaReadonly.vue'),
  'utf8',
)

describe('PresetPromptTextareaReadonly', () => {
  it('uses shrinkable split columns and allows the preview pane to scroll', () => {
    expect(source).toContain('grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);')
    expect(source).toContain('min-width: 0;')
    expect(source).toContain('overflow: auto;')
  })
})
