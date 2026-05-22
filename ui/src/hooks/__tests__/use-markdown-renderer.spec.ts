import { describe, expect, it } from 'vitest'
import { useMarkdownRenderer } from '@/hooks/use-markdown-renderer'

describe('useMarkdownRenderer', () => {
  it('renders http links as clickable anchors', () => {
    const { renderMarkdown } = useMarkdownRenderer()

    const html = renderMarkdown('[下载附件](https://example.com/file.svg)')

    expect(html).toContain('href="https://example.com/file.svg"')
  })

  it('rejects sandbox links from markdown output', () => {
    const { renderMarkdown } = useMarkdownRenderer()

    const html = renderMarkdown('[下载附件](sandbox:/mnt/data/file.svg)')

    expect(html).not.toContain('href="sandbox:/mnt/data/file.svg"')
    expect(html).toContain('[下载附件](sandbox:/mnt/data/file.svg)')
  })
})
