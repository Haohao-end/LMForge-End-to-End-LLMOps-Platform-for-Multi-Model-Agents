import { config } from '@vue/test-utils'
import { createTestI18n } from '@/i18n'

config.global.plugins = [...(config.global.plugins || []), createTestI18n()]
