import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('PromptCompareView', () => {
  it('uses the compact markdown toolbar for compare prompt editors', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/space/apps/PromptCompareView.vue'), 'utf8')

    expect(source).toContain('toolbar-variant="compact"')
  })
})
