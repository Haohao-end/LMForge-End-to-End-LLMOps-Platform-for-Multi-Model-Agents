import { formatTimestampLong } from '@/utils/time-formatter'
import { type AccountSessionItem } from '@/models/account'

export type SessionMetaItem = {
  label: string
  value: string
}

type Translate = (key: string) => string

const formatTime = (timestamp: number | undefined, t: Translate) => {
  return formatTimestampLong(timestamp) || t('common.status.noRecord')
}

export const buildSessionMetaItems = (
  session: Pick<AccountSessionItem, 'legacy' | 'created_at' | 'last_active_at' | 'expires_at'>,
  t: Translate,
): SessionMetaItem[] => {
  if (session.legacy) {
    return [
      {
        label: t('settings.sessionMeta.credentialType'),
        value: t('settings.sessionMeta.legacyCredentialType'),
      },
      {
        label: t('settings.sessionMeta.lastLoginTime'),
        value: formatTime(session.created_at, t),
      },
      {
        label: t('settings.sessionMeta.sessionExpiresAt'),
        value: t('settings.sessionMeta.legacySessionUnsupported'),
      },
    ]
  }

  return [
    {
      label: t('settings.sessionMeta.firstLoginTime'),
      value: formatTime(session.created_at, t),
    },
    {
      label: t('settings.sessionMeta.lastActiveTime'),
      value: formatTime(session.last_active_at, t),
    },
    {
      label: t('settings.sessionMeta.sessionExpiresAt'),
      value: formatTime(session.expires_at, t),
    },
  ]
}
