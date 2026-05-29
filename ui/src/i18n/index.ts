import { createI18n } from 'vue-i18n'
import storage from '@/utils/storage'
import {
  APP_LOCALE_STORAGE_KEY,
  DEFAULT_LOCALE,
  FALLBACK_LOCALE,
  type AppLocale,
  isSupportedLocale,
  resolveStoredLocale,
  syncDocumentLanguage,
} from '@/i18n/locale'
import enUS from '@/i18n/messages/en-US'
import zhCN from '@/i18n/messages/zh-CN'

const messages = {
  'zh-CN': zhCN,
  'en-US': enUS,
} as const

const createI18nOptions = (locale: AppLocale) => ({
  legacy: false,
  globalInjection: true,
  locale,
  fallbackLocale: FALLBACK_LOCALE,
  missingWarn: false,
  fallbackWarn: false,
  messages,
})

const initialLocale = resolveStoredLocale()

export const i18n = createI18n(createI18nOptions(initialLocale))

type GlobalLocaleRef = {
  value: AppLocale
}

const getGlobalLocaleRef = () => i18n.global.locale as unknown as GlobalLocaleRef

const applyLocale = (
  locale: AppLocale,
  options: {
    persist?: boolean
    updateI18n?: boolean
  } = {},
) => {
  const { persist = true, updateI18n = true } = options

  if (updateI18n) {
    getGlobalLocaleRef().value = locale
  }

  syncDocumentLanguage(locale)

  if (persist && typeof window !== 'undefined') {
    storage.set(APP_LOCALE_STORAGE_KEY, locale)
  }
}

applyLocale(initialLocale, { persist: false, updateI18n: false })

export const getAppLocale = (): AppLocale => {
  const currentLocale = getGlobalLocaleRef().value
  return isSupportedLocale(currentLocale) ? currentLocale : DEFAULT_LOCALE
}

export const setAppLocale = (locale: AppLocale) => {
  applyLocale(locale)
}

export const createTestI18n = (locale: AppLocale = DEFAULT_LOCALE) => {
  return createI18n(createI18nOptions(locale))
}

export type AppI18nSchema = typeof zhCN
export type { AppLocale } from '@/i18n/locale'

export { APP_LOCALE_STORAGE_KEY, DEFAULT_LOCALE, FALLBACK_LOCALE, isSupportedLocale }
