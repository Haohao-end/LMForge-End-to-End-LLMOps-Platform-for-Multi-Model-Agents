import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('PresetPromptTextarea', () => {
  it('uses the compact markdown toolbar for the prompt editor', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/space/apps/components/PresetPromptTextarea.vue'),
      'utf8',
    )

    expect(source).toContain('toolbar-variant="compact"')
  })
})
