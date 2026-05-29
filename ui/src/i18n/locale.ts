import storage from '@/utils/storage'

export const SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const

export type AppLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: AppLocale = 'zh-CN'
export const FALLBACK_LOCALE: AppLocale = 'zh-CN'
export const APP_LOCALE_STORAGE_KEY = 'app:locale'

const supportedLocaleSet = new Set<string>(SUPPORTED_LOCALES)

export const isSupportedLocale = (value: unknown): value is AppLocale => {
  return typeof value === 'string' && supportedLocaleSet.has(value)
}

export const resolveStoredLocale = (): AppLocale => {
  const storedLocale = storage.get(APP_LOCALE_STORAGE_KEY, DEFAULT_LOCALE)

  if (isSupportedLocale(storedLocale)) {
    return storedLocale
  }

  return DEFAULT_LOCALE
}

export const syncDocumentLanguage = (locale: AppLocale) => {
  if (typeof document === 'undefined') return
  document.documentElement.lang = locale
}
