import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('PromptCompareView', () => {
  it('uses the compact markdown toolbar for compare prompt editors', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/space/apps/PromptCompareView.vue'), 'utf8')

    expect(source).toContain('toolbar-variant="compact"')
  })

  it('scopes the wider compare chat layout to the page-local wrapper', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/space/apps/PromptCompareView.vue'), 'utf8')

    expect(source).toContain('prompt-compare-page')
    expect(source).toContain('xl:grid-cols-[minmax(460px,1.45fr)_minmax(340px,2.9fr)]')
    expect(source).toContain('h-[560px]')
    expect(source).toContain('ml-auto flex flex-wrap items-center justify-end gap-3')
    expect(source).toContain('width: 100% !important')
    expect(source).toContain(':deep(.message-bubble-content)')
    expect(source).not.toContain('a-empty')
  })
})
