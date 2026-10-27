import { createContext, use } from 'react'
import type { User } from '../api/types'

export type SessionValue = { user: User; logout: () => Promise<void>; setUser: (user: User) => void }

export const SessionContext = createContext<SessionValue | null>(null)

export function useSession(): SessionValue {
  const value = use(SessionContext)
  if (!value) throw new Error('useSession yalnız oturum açıkken kullanılabilir.')
  return value
}
