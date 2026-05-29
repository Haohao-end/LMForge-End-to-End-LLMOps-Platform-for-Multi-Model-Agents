import { beforeEach, describe, expect, it } from 'vitest'

import { APP_LOCALE_STORAGE_KEY, DEFAULT_LOCALE, getAppLocale, setAppLocale } from '@/i18n'
import { resolveStoredLocale } from '@/i18n/locale'

describe('i18n locale management', () => {
  beforeEach(() => {
    localStorage.clear()
    setAppLocale(DEFAULT_LOCALE)
  })

  it('defaults to zh-CN when localStorage is empty', () => {
    localStorage.clear()

    expect(resolveStoredLocale()).toBe(DEFAULT_LOCALE)
  })

  it('persists locale changes and updates the active locale immediately', () => {
    setAppLocale('en-US')

    expect(localStorage.getItem(APP_LOCALE_STORAGE_KEY)).toBe('en-US')
    expect(getAppLocale()).toBe('en-US')
    expect(document.documentElement.lang).toBe('en-US')
  })

  it('falls back to zh-CN when the stored locale is unsupported', () => {
    localStorage.setItem(APP_LOCALE_STORAGE_KEY, 'fr-FR')

    expect(resolveStoredLocale()).toBe(DEFAULT_LOCALE)
  })
})
