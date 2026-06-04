import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const markdownEditorSource = readFileSync(
  resolve(process.cwd(), 'src/components/MarkdownEditor.vue'),
  'utf8',
)

describe('MarkdownEditor.vue', () => {
  it('keeps split mode shrinkable instead of forcing fixed-width tracks', () => {
    expect(markdownEditorSource).toContain('.editor-body.split-mode')
    expect(markdownEditorSource).not.toContain('max(600px')
    expect(markdownEditorSource).toContain('grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);')
    expect(markdownEditorSource).toContain('min-width: 0;')
  })

  it('supports a compact toolbar variant for prompt editors', () => {
    const compactToolbarSource = markdownEditorSource
      .split('<template v-if="isCompactToolbar">')[1]
      ?.split('<template v-else>')[0] ?? ''

    expect(markdownEditorSource).toContain(
      "toolbarVariant: { type: String as () => 'full' | 'compact', default: 'full' }",
    )
    expect(markdownEditorSource).toContain(
      "const isCompactToolbar = computed(() => props.toolbarVariant === 'compact')",
    )
    expect(markdownEditorSource).toContain('v-if="isCompactToolbar"')
    expect(markdownEditorSource).toContain('v-else')
    expect(compactToolbarSource).not.toContain('icon-more')
    expect(compactToolbarSource).not.toContain('icon-quote')
    expect(compactToolbarSource).not.toContain('icon-code-block')
    expect(compactToolbarSource).toContain('toolbar-text-btn')
    expect(compactToolbarSource).toContain('H2')
    expect(compactToolbarSource).toContain('H3')
    expect(compactToolbarSource).toContain('icon-bold')
    expect(compactToolbarSource).toContain('icon-italic')
    expect(compactToolbarSource).toContain('icon-unordered-list')
    expect(compactToolbarSource).toContain('icon-ordered-list')
    expect(compactToolbarSource).toContain('icon-code')
    expect(compactToolbarSource).toContain('icon-link')
  })
})
