import { humanizeTagIdLabel } from '@/utils/public-app-tag-display'

export type SupportedLocale = 'zh-CN' | 'en-US'

const CATEGORY_LABEL_MAP: Record<string, { 'zh-CN': string; 'en-US': string }> = {
  all: { 'zh-CN': '全部', 'en-US': 'All' },
  general: { 'zh-CN': '通用', 'en-US': 'General' },
  productivity: { 'zh-CN': '效率工具', 'en-US': 'Productivity' },
  coding: { 'zh-CN': '编程工具', 'en-US': 'Coding' },
  content_creation: { 'zh-CN': '内容创作', 'en-US': 'Content Creation' },
  media: { 'zh-CN': '媒体音视频', 'en-US': 'Media & Audio' },
  data_analysis: { 'zh-CN': '数据分析', 'en-US': 'Data Analysis' },
  observability: { 'zh-CN': '可观测运维', 'en-US': 'Observability' },
  search: { 'zh-CN': '搜索', 'en-US': 'Search' },
  code: { 'zh-CN': '编程', 'en-US': 'Code' },
  dev: { 'zh-CN': '开发', 'en-US': 'Development' },
  design: { 'zh-CN': '设计', 'en-US': 'Design' },
  security: { 'zh-CN': '安全', 'en-US': 'Security' },
  other: { 'zh-CN': '其他', 'en-US': 'Other' },
}

const TYPE_LABEL_MAP: Record<string, { 'zh-CN': string; 'en-US': string }> = {
  str: { 'zh-CN': '字符串', 'en-US': 'String' },
  int: { 'zh-CN': '整型', 'en-US': 'Integer' },
  float: { 'zh-CN': '浮点型', 'en-US': 'Float' },
  bool: { 'zh-CN': '布尔值', 'en-US': 'Boolean' },
  string: { 'zh-CN': '字符串', 'en-US': 'String' },
  number: { 'zh-CN': '数字', 'en-US': 'Number' },
  boolean: { 'zh-CN': '布尔值', 'en-US': 'Boolean' },
}

const SKILL_CATEGORY_LABEL_MAP: Record<string, { 'zh-CN': string; 'en-US': string }> = {
  通用: { 'zh-CN': '通用', 'en-US': 'General' },
  效率工具: { 'zh-CN': '效率工具', 'en-US': 'Productivity' },
  编程工具: { 'zh-CN': '编程工具', 'en-US': 'Coding' },
  内容创作: { 'zh-CN': '内容创作', 'en-US': 'Content Creation' },
  媒体音视频: { 'zh-CN': '媒体音视频', 'en-US': 'Media & Audio' },
  数据分析: { 'zh-CN': '数据分析', 'en-US': 'Data Analysis' },
  可观测运维: { 'zh-CN': '可观测运维', 'en-US': 'Observability' },
  搜索: { 'zh-CN': '搜索', 'en-US': 'Search' },
  编程: { 'zh-CN': '编程', 'en-US': 'Code' },
  开发: { 'zh-CN': '开发', 'en-US': 'Development' },
  设计: { 'zh-CN': '设计', 'en-US': 'Design' },
  安全: { 'zh-CN': '安全', 'en-US': 'Security' },
  其他: { 'zh-CN': '其他', 'en-US': 'Other' },
}

const SKILL_CATEGORY_ALIAS_RULES: Array<{
  test: RegExp
  label: { 'zh-CN': string; 'en-US': string }
}> = [
  { test: /通用/, label: { 'zh-CN': '通用', 'en-US': 'General' } },
  { test: /效率|办公|效率工具/, label: { 'zh-CN': '效率工具', 'en-US': 'Productivity' } },
  { test: /编程|代码|程序|开发工具/, label: { 'zh-CN': '编程工具', 'en-US': 'Coding' } },
  { test: /开发|研发|软件/, label: { 'zh-CN': '开发', 'en-US': 'Development' } },
  { test: /内容|创作|写作|文案/, label: { 'zh-CN': '内容创作', 'en-US': 'Content Creation' } },
  { test: /媒体|音频|视频|音视频/, label: { 'zh-CN': '媒体音视频', 'en-US': 'Media & Audio' } },
  { test: /数据|分析|统计/, label: { 'zh-CN': '数据分析', 'en-US': 'Data Analysis' } },
  { test: /可观测|运维|监控|观测/, label: { 'zh-CN': '可观测运维', 'en-US': 'Observability' } },
  { test: /搜索|检索/, label: { 'zh-CN': '搜索', 'en-US': 'Search' } },
  { test: /设计|视觉|UI/, label: { 'zh-CN': '设计', 'en-US': 'Design' } },
  { test: /安全|风控|合规/, label: { 'zh-CN': '安全', 'en-US': 'Security' } },
  { test: /其他|其它/, label: { 'zh-CN': '其他', 'en-US': 'Other' } },
]

const isChineseText = (value: string) => /[\u4e00-\u9fff]/.test(value)

const pickLocaleLabel = (entry: { 'zh-CN': string; 'en-US': string }, locale: SupportedLocale) => {
  return entry[locale] || entry['zh-CN'] || entry['en-US']
}

export const getStoreCategoryDisplayName = (value: string, locale: SupportedLocale) => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  const mapped = CATEGORY_LABEL_MAP[normalized]
  if (mapped) {
    return pickLocaleLabel(mapped, locale)
  }

  if (locale === 'en-US' && isChineseText(normalized)) {
    const alias = SKILL_CATEGORY_ALIAS_RULES.find((rule) => rule.test.test(normalized))
    if (alias) {
      return pickLocaleLabel(alias.label, locale)
    }
    return humanizeTagIdLabel(normalized)
  }

  return normalized
}

export const getStoreTypeDisplayName = (value: string, locale: SupportedLocale) => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  const mapped = TYPE_LABEL_MAP[normalized]
  if (mapped) {
    return pickLocaleLabel(mapped, locale)
  }

  return locale === 'en-US' ? humanizeTagIdLabel(normalized) : normalized
}

export const getSkillCategoryDisplayName = (value: string, locale: SupportedLocale) => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  const mapped = SKILL_CATEGORY_LABEL_MAP[normalized]
  if (mapped) {
    return pickLocaleLabel(mapped, locale)
  }

  if (isChineseText(normalized)) {
    const alias = SKILL_CATEGORY_ALIAS_RULES.find((rule) => rule.test.test(normalized))
    if (alias) {
      return pickLocaleLabel(alias.label, locale)
    }
  }

  return getStoreCategoryDisplayName(normalized, locale)
}
