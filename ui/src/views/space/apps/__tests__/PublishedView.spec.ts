import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('PublishedView', () => {
  it('does not render the leak alert banner in the published configuration page', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/space/apps/PublishedView.vue'),
      'utf8',
    )

    expect(source).not.toContain("t('appStudio.published.leakAlert')")
    expect(source).not.toContain('<a-alert class="mb-5">')
  })
})
