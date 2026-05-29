import { get } from '@/utils/request'
import { getAppLocale } from '@/i18n'
import type { GetHomeIntentResponse } from '@/models/home'

export const getHomeIntent = () => {
  return get<GetHomeIntentResponse>(`/home/intent`, {
    headers: {
      'Accept-Language': getAppLocale(),
      'X-App-Locale': getAppLocale(),
    },
  })
}
