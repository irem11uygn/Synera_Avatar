import { createContext, use } from 'react'
import type { User } from '../api/types'
import { t } from '../lib/i18n'

export type SessionValue = { user: User; logout: () => Promise<void>; setUser: (user: User) => void }

export const SessionContext = createContext<SessionValue | null>(null)

export function useSession(): SessionValue {
  const value = use(SessionContext)
  if (!value) throw new Error(t('useSession yalnız oturum açıkken kullanılabilir.'))
  return value
}
