// Ayarlar: herkesin kendi hesabı (bilgiler, şifre ve açık oturumlar, e-posta bildirimleri, dil) ve
// yöneticiye bütün işletmeyi etkileyen ayarların bağlantıları. Kişisel ayarlar yalnız kullanıcının
// kendisini etkiler; işletme ayarları ayrı bölümde ve "yalnız yönetici" diye yazılı.

import {
  AuditOutlined,
  KeyOutlined,
  LogoutOutlined,
  SettingOutlined,
  ShopOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Descriptions, Flex, List, Popconfirm, Radio, Switch, Tag, Typography } from 'antd'
import { useState, type ReactNode } from 'react'
import { api, errorMessage } from '../api/client'
import type { AlertKind, MailStatusInfo } from '../api/types'
import type { components } from '../api/schema'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { SystemStatus } from '../components/SystemStatus'
import { formatDateTime } from '../lib/format'
import { lang, LANGS, setLang, t } from '../lib/i18n'
import { ALERT_KIND, ALERT_WHEN } from '../lib/labels'
import { ROLE, ROLE_HELP } from '../lib/roles'
import { navigate } from '../lib/router'

type OpenSession = components['schemas']['SessionOut']
type Subscriptions = components['schemas']['SubscriptionsOut']

const sectionStyle = { marginBottom: 16 }

function Account() {
  const { user } = useSession()
  return (
    <Card title={t('Hesabım')} style={sectionStyle} id="hesap">
      <Descriptions
        column={1}
        size="small"
        items={[
          { key: 'name', label: t('Ad soyad'), children: user.full_name },
          { key: 'username', label: t('Kullanıcı adı'), children: user.username },
          {
            key: 'role',
            label: t('Rol'),
            children: (
              <>
                {ROLE[user.role]}
                <Typography.Text type="secondary"> — {ROLE_HELP[user.role]}</Typography.Text>
              </>
            ),
          },
          {
            key: 'email',
            label: t('E-posta'),
            children: user.email ?? <Tag color="warning">{t('Tanımlı değil')}</Tag>,
          },
          ...(user.warehouse_code ? [{ key: 'warehouse', label: t('Depo'), children: user.warehouse_code }] : []),
        ]}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
        {t('Ad ve e-posta adresini yönetici değiştirir (Yönetim → Kullanıcılar). E-posta bildirimleri ve size gönderilen raporlar bu adrese gider.')}
      </Typography.Paragraph>
    </Card>
  )
}

function Security() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const sessions = useQuery({ queryKey: ['auth', 'sessions'], queryFn: () => api<OpenSession[]>('/auth/sessions') })
  const closeOthers = useMutation({
    mutationFn: () => api<{ closed: number }>('/auth/sessions/close-others', { method: 'POST' }),
    onSuccess: (result) => {
      message.success(t('{n} oturum kapatıldı.', { n: result.closed }))
      void queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] })
    },
    onError: (error) => message.error(errorMessage(error)),
  })
  const others = (sessions.data ?? []).filter((row) => !row.current).length

  return (
    <Card title={t('Güvenlik')} style={sectionStyle} id="guvenlik">
      <Flex justify="space-between" align="center" gap="middle" wrap>
        <div>
          <Typography.Text strong>{t('Şifre')}</Typography.Text>
          <br />
          <Typography.Text type="secondary">{t('En az 8 karakter; harf ve rakam birlikte.')}</Typography.Text>
        </div>
        <Button icon={<KeyOutlined />} onClick={() => navigate('/sifre')}>
          {t('Şifremi değiştir')}
        </Button>
      </Flex>

      <Typography.Title level={5} style={{ marginTop: 24 }}>
        {t('Açık oturumlar')}
      </Typography.Title>
      {sessions.isError && <QueryError error={sessions.error} onRetry={() => sessions.refetch()} />}
      <List
        size="small"
        bordered
        loading={sessions.isPending}
        dataSource={sessions.data ?? []}
        locale={{ emptyText: t('Açık oturum yok.') }}
        renderItem={(row) => (
          <List.Item extra={row.current ? <Tag color="success">{t('Bu oturum')}</Tag> : null}>
            {t('Açıldı: {start} · biter: {end}', {
              start: formatDateTime(row.started_at),
              end: formatDateTime(row.expires_at),
            })}
          </List.Item>
        )}
      />
      <Flex justify="space-between" align="center" gap="middle" wrap style={{ marginTop: 12 }}>
        <Typography.Text type="secondary">
          {t('Oturum 12 saat sonra kendiliğinden kapanır; bu sekmeyi kapatınca bu tarayıcıdaki oturum da biter.')}
        </Typography.Text>
        <Popconfirm
          title={t('Diğer cihazlardan çıkış yapılsın mı?')}
          description={t('Bu oturum dışındaki {n} oturum hemen kapanır; o cihazlarda yeniden giriş gerekir. Geri alınamaz.', { n: others })}
          okText={t('Çıkış yap')}
          cancelText={t('Vazgeç')}
          onConfirm={() => closeOthers.mutate()}
          disabled={others === 0}
        >
          <Button danger icon={<LogoutOutlined />} disabled={others === 0} loading={closeOthers.isPending}>
            {t('Diğer cihazlardan çıkış yap')}
          </Button>
        </Popconfirm>
      </Flex>
    </Card>
  )
}

function Notifications() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const subscriptions = useQuery({
    queryKey: ['alerts', 'subscriptions'],
    queryFn: () => api<Subscriptions>('/alerts/subscriptions'),
  })
  const mail = useQuery({ queryKey: ['mail', 'status'], queryFn: () => api<MailStatusInfo>('/mail/status') })
  // Yalnız kullanıcının değiştirdikleri tutulur; ekrandaki değer = değişiklik ?? sunucudaki.
  const [choices, setChoices] = useState<Partial<Record<AlertKind, boolean>>>({})
  const changes = (subscriptions.data?.subscriptions ?? [])
    .filter((row) => choices[row.alert_type] !== undefined && choices[row.alert_type] !== row.enabled)
    .map((row) => ({ alert_type: row.alert_type, enabled: !row.enabled }))
  const save = useMutation({
    mutationFn: () =>
      api<Subscriptions>('/alerts/subscriptions', {
        method: 'PUT',
        body: { subscriptions: changes },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['alerts', 'subscriptions'], data)
      setChoices({})
      message.success(t('Bildirim tercihleri kaydedildi.'))
    },
    onError: (error) => message.error(errorMessage(error)),
  })

  return (
    <Card
      title={t('E-posta bildirimleri')}
      style={sectionStyle}
      id="bildirimler"
      extra={
        <Button type="primary" disabled={changes.length === 0} loading={save.isPending} onClick={() => save.mutate()}>
          {t('Kaydet')}
        </Button>
      }
    >
      <Typography.Paragraph type="secondary">
        {t('Bir alarm açıldığında hangi türler için e-posta almak istediğinizi seçin. Alarmlar her durumda Alarm merkezinde görünür; bu seçim yalnız e-postayı etkiler.')}
      </Typography.Paragraph>
      {subscriptions.data && !subscriptions.data.email && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          title={t('Hesabınızda e-posta adresi yok; bildirim e-postası gönderilemez. Yöneticinizden ekletin.')}
        />
      )}
      {mail.data && !mail.data.smtp_configured && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          title={t('E-posta sunucusu tanımlı değil; e-postalar giden kutusunda bekler.')}
        />
      )}
      {subscriptions.isError && <QueryError error={subscriptions.error} onRetry={() => subscriptions.refetch()} />}
      <List
        size="small"
        loading={subscriptions.isPending}
        dataSource={subscriptions.data?.subscriptions ?? []}
        renderItem={(row) => (
          <List.Item
            extra={
              <Switch
                checked={choices[row.alert_type] ?? row.enabled}
                onChange={(enabled) => setChoices((current) => ({ ...current, [row.alert_type]: enabled }))}
                aria-label={ALERT_KIND[row.alert_type]}
              />
            }
          >
            <List.Item.Meta
              title={ALERT_KIND[row.alert_type]}
              description={ALERT_WHEN[row.alert_type]}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

function Language() {
  return (
    <Card title={t('Dil')} style={sectionStyle} id="dil">
      <Radio.Group value={lang} onChange={(event) => setLang(event.target.value)} options={LANGS} optionType="button" />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
        {t('Seçim bu tarayıcıda hatırlanır. Telefon uygulamasında dil, Ayarlar ekranından ayrıca seçilir.')}
      </Typography.Paragraph>
    </Card>
  )
}

function AdminLink({ to, icon, title, text }: { to: string; icon: ReactNode; title: string; text: string }) {
  return (
    <List.Item
      extra={
        <Button onClick={() => navigate(to)} icon={icon}>
          {t('Aç')}
        </Button>
      }
    >
      <List.Item.Meta title={title} description={text} />
    </List.Item>
  )
}

function Business() {
  return (
    <Card title={t('İşletme ayarları (yalnız yönetici)')} style={sectionStyle} id="isletme">
      <Typography.Paragraph type="secondary">
        {t('Buradaki değişiklikler bütün kullanıcıları etkiler ve denetim günlüğüne yazılır.')}
      </Typography.Paragraph>
      <List size="small">
        <AdminLink to="/kullanicilar" icon={<TeamOutlined />} title={t('Kullanıcılar')} text={t('Hesap açma, rol, e-posta, pasifleştirme ve geçici şifre.')} />
        <AdminLink to="/urunler" icon={<ShopOutlined />} title={t('Ürünler ve fiyatlar')} text={t('Ürün kartları, birimler ve satış fiyatları.')} />
        <AdminLink to="/alarm-ayarlari" icon={<SettingOutlined />} title={t('Alarm ve e-posta ayarları')} text={t('Alarm eşikleri, kuralları elle çalıştırma, e-posta sunucusunun durumu.')} />
        <AdminLink to="/denetim" icon={<AuditOutlined />} title={t('Denetim günlüğü')} text={t('Kim, ne zaman, ne yaptı; CSV olarak dışa aktarma.')} />
      </List>
    </Card>
  )
}

function About() {
  return (
    <Card title={t('Hakkında ve yardım')} style={sectionStyle} id="hakkinda">
      <SystemStatus />
      <Typography.Title level={5} style={{ marginTop: 20 }}>
        {t('Yardım')}
      </Typography.Title>
      <ul style={{ paddingLeft: 20, marginBottom: 0 }}>
        <li>{t('Şifrenizi unuttuysanız yöneticinize başvurun; geçici şifre verir, ilk girişte kendi şifrenizi belirlersiniz.')}</li>
        <li>{t('Menüde göremediğiniz ekranlar rolünüze kapalıdır; gerekiyorsa yöneticinize başvurun.')}</li>
        <li>{t('Araçtaki satış elemanları telefon uygulamasını kullanır; web arayüzü ofis rolleri içindir.')}</li>
      </ul>
      <Typography.Title level={5} style={{ marginTop: 20 }}>
        {t('Kişisel veriler')}
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        {t('Sistem hesabınız için ad soyad, kullanıcı adı, rol ve e-posta adresini tutar. Giriş, çıkış ve yaptığınız işlemler zaman ve bağlanılan adresle denetim günlüğüne yazılır. Şifreniz geri çevrilemez biçimde (scrypt özeti) saklanır; yönetici de göremez.')}
      </Typography.Paragraph>
    </Card>
  )
}

export default function SettingsPage() {
  const { user } = useSession()
  return (
    <Page
      title={t('Ayarlar')}
      description={t('Kendi hesabınız, güvenlik, bildirimler ve dil. Bütün işletmeyi etkileyen ayarlar yalnız yöneticide.')}
    >
      <div style={{ maxWidth: 880 }}>
        <Account />
        <Security />
        <Notifications />
        <Language />
        {user.role === 'YONETICI' && <Business />}
        <About />
      </div>
    </Page>
  )
}
