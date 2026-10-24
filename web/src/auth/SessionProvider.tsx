// Oturum: belirteç sessionStorage'da, kullanıcı bilgisi /auth/me ile doğrulanır.
// Web arayüzü yönetici hesabı içindir; satış kullanıcıları Android uygulamasını kullanır.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Flex, Spin } from 'antd'
import { useEffect, useState, type ReactNode } from 'react'
import { api, ApiError, errorMessage, getToken, onUnauthorized, setToken } from '../api/client'
import type { LoginResponse, User } from '../api/types'
import LoginPage from '../pages/LoginPage'
import { SessionContext } from './context'


const WEB_ROLE_MESSAGE = 'Web arayüzü yönetici hesabı içindir; satış kullanıcıları Android uygulamasını kullanır.'

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setTokenState] = useState(getToken)
  const [notice, setNotice] = useState<string | null>(null)

  function end(message: string | null) {
    setToken(null)
    setTokenState(null)
    queryClient.clear()
    setNotice(message)
  }

  useEffect(() => {
    onUnauthorized(() => {
      setToken(null)
      setTokenState(null)
      queryClient.clear()
      setNotice('Oturumun süresi doldu; yeniden giriş yapın.')
    })
  }, [queryClient])

  const me = useQuery({
    queryKey: ['me', token],
    queryFn: () => api<User>('/auth/me'),
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
  })

  async function login(username: string, password: string) {
    const response = await api<LoginResponse>('/auth/login', { method: 'POST', body: { username, password } })
    setToken(response.token)
    if (response.user.role !== 'YONETICI') {
      await api('/auth/logout', { method: 'POST' }).catch(() => undefined)
      setToken(null)
      throw new Error(WEB_ROLE_MESSAGE)
    }
    queryClient.setQueryData(['me', response.token], response.user)
    setNotice(null)
    setTokenState(response.token)
  }

  async function logout() {
    await api('/auth/logout', { method: 'POST' }).catch(() => undefined)
    end(null)
  }

  if (token === null) return <LoginPage onLogin={login} notice={notice} />

  if (me.isPending) {
    return (
      <Flex justify="center" align="center" style={{ minHeight: '100vh' }}>
        <Spin size="large" />
      </Flex>
    )
  }

  if (me.isError) {
    // 401'i istemci zaten girişe döndürür; burada kalan ağ/sunucu hatalarıdır.
    if (me.error instanceof ApiError && me.error.status === 401) return null
    return (
      <Flex justify="center" style={{ padding: 48 }}>
        <Alert
          type="error"
          showIcon
          title="Oturum doğrulanamadı"
          description={errorMessage(me.error)}
          action={<Button onClick={() => me.refetch()}>Yeniden dene</Button>}
        />
      </Flex>
    )
  }

  if (me.data.role !== 'YONETICI') {
    return (
      <Flex justify="center" style={{ padding: 48 }}>
        <Alert type="warning" showIcon title={WEB_ROLE_MESSAGE} action={<Button onClick={logout}>Çıkış</Button>} />
      </Flex>
    )
  }

  return <SessionContext value={{ user: me.data, logout }}>{children}</SessionContext>
}
