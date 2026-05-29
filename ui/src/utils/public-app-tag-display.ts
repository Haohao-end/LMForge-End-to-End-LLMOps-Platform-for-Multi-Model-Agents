import { type AppLocale } from '@/i18n'

const CHINESE_CHAR_PATTERN = /[\u4e00-\u9fff]/

const humanizeTagId = (value: string) => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  const spaced = normalized
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()

  if (!spaced) return normalized
  return spaced
    .split(' ')
    .map((segment) => {
      if (!segment) return segment
      if (/^[A-Z0-9]+$/.test(segment)) return segment
      return segment.charAt(0).toUpperCase() + segment.slice(1)
    })
    .join(' ')
}

export const getPublicAppTagDisplayName = (
  tag: { id: string; name: string },
  locale: AppLocale,
) => {
  const fallbackName = humanizeTagId(tag.id)
  const rawName = String(tag.name || '').trim()

  if (locale === 'en-US') {
    if (rawName && !CHINESE_CHAR_PATTERN.test(rawName)) {
      return rawName
    }
    return fallbackName || rawName || tag.id
  }

  return rawName || fallbackName || tag.id
}

export const humanizeTagIdLabel = humanizeTagId
