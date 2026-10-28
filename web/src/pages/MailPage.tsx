// Rapor gönder (e-posta): rapor seç → alıcı seç → not ekle → ön izleme → gönder.
// E-posta önce giden kutusuna yazılır; sunucuda e-posta (SMTP) ayarı varsa arka planda gider,
// yoksa "Kuyrukta" bekler. Hemen göndermek için kullanıcının kendi e-posta programı da açılabilir.

import { MailOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Form, Input, Row, Select, Space, Table, Tag, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { AlertRow, Charts, Dashboard, MailRecipient, MailRow, MailStatus, MailStatusInfo, Recall, RecallSummary } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDateTime } from '../lib/format'
import { t } from '../lib/i18n'
import { MAIL_STATUS } from '../lib/labels'
import { alarmList, costReport, dailySummary, mailtoLink, recallNotice, type MailDraft } from '../lib/reportMail'

type ReportKind = 'daily' | 'cost' | 'recall' | 'alarms'

const REPORTS: { value: ReportKind; label: string }[] = [
  { value: 'daily', label: t('Günlük özet (satış, stok, SKT, geri çağırma)') },
  { value: 'cost', label: t('Maliyet ve sevkiyat raporu (EKP, parça maliyeti)') },
  { value: 'recall', label: t('Geri çağırma bildirimi (müşterilere)') },
  { value: 'alarms', label: t('Açık alarmlar listesi') },
]

const STATUS_COLOR: Record<MailStatus, string> = { KUYRUKTA: 'gold', GONDERILDI: 'green', HATA: 'red' }
const GROUP_LABEL: Record<MailRecipient['group'], string> = {
  Kullanıcı: t('Kullanıcılar'),
  Müşteri: t('Müşteriler'),
  Tedarikçi: t('Tedarikçiler'),
  'Dış üretici': t('Dış üreticiler'),
}

export default function MailPage() {
  const { user } = useSession()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [kind, setKind] = useState<ReportKind>('daily')
  const [recallId, setRecallId] = useState<number>()
  const [to, setTo] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [edited, setEdited] = useState<MailDraft | null>(null)

  const status = useQuery({ queryKey: ['mail', 'status'], queryFn: () => api<MailStatusInfo>('/mail/status') })
  const recipients = useQuery({ queryKey: ['mail', 'recipients'], queryFn: () => api<MailRecipient[]>('/mail/recipients') })
  const outbox = useQuery({ queryKey: ['mail', 'outbox'], queryFn: () => api<MailRow[]>('/mail/outbox'), refetchInterval: 30_000 })
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/dashboard'), enabled: kind === 'daily' })
  const charts = useQuery({ queryKey: ['dashboard', 'charts'], queryFn: () => api<Charts>('/dashboard/charts'), enabled: kind === 'cost' })
  const recalls = useQuery({ queryKey: ['recalls'], queryFn: () => api<RecallSummary[]>('/recalls'), enabled: kind === 'recall' })
  const recall = useQuery({
    queryKey: ['recall', recallId],
    queryFn: () => api<Recall>(`/recalls/${recallId}`),
    enabled: kind === 'recall' && recallId != null,
  })
  const alarms = useQuery({
    queryKey: ['alerts', 'list', true, 'all'],
    queryFn: () => api<AlertRow[]>('/alerts', { query: { only_open: true } }),
    enabled: kind === 'alarms',
  })

  const generated: MailDraft | null = useMemo(() => {
    if (kind === 'daily' && dashboard.data) return dailySummary(dashboard.data, note)
    if (kind === 'cost' && charts.data) return costReport(charts.data, note)
    if (kind === 'recall' && recall.data) return recallNotice(recall.data, note)
    if (kind === 'alarms' && alarms.data) return alarmList(alarms.data, note)
    return null
  }, [kind, note, dashboard.data, charts.data, recall.data, alarms.data])
  const draft = edited ?? generated

  const send = useMutation({
    mutationFn: async () => {
      // Geri çağırma: her müşteriye yalnız kendi miktarını içeren ayrı e-posta (müşteriler birbirini görmez).
      const customers = new Map((recall.data?.recipients ?? []).filter((r) => r.contact.email).map((r) => [r.contact.email!, r.customer_id]))
      const perCustomer = kind === 'recall' && recall.data && !edited ? to.filter((email) => customers.has(email)) : []
      const others = to.filter((email) => !perCustomer.includes(email))
      let last: MailRow | undefined
      for (const email of perCustomer) {
        const own = recallNotice(recall.data!, note, customers.get(email))
        last = await api<MailRow>('/mail', { method: 'POST', body: { recipients: [email], subject: own.subject, body: own.body } })
      }
      if (others.length > 0)
        last = await api<MailRow>('/mail', { method: 'POST', body: { recipients: others, subject: draft!.subject, body: draft!.body } })
      return last!
    },
    onSuccess: (row) => {
      message.success(
        row.status === 'GONDERILDI' || status.data?.smtp_configured
          ? t('E-posta giden kutusuna alındı; birkaç saniye içinde gönderilir.')
          : t('E-posta giden kutusuna alındı (Kuyrukta). E-posta sunucusu tanımlanınca gönderilir.'),
      )
      setEdited(null)
      void queryClient.invalidateQueries({ queryKey: ['mail', 'outbox'] })
    },
    onError: (error) => message.error(errorMessage(error)),
  })
  const deliver = useMutation({
    mutationFn: () => api<{ sent: number; failed: number }>('/mail/deliver', { method: 'POST' }),
    onSuccess: (result) => {
      message.info(t('{s} gönderildi, {f} gönderilemedi.', { s: result.sent, f: result.failed }))
      void queryClient.invalidateQueries({ queryKey: ['mail', 'outbox'] })
    },
    onError: (error) => message.error(errorMessage(error)),
  })
  const retry = useMutation({
    mutationFn: (id: number) => api<MailRow>(`/mail/${id}/retry`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mail', 'outbox'] }),
    onError: (error) => message.error(errorMessage(error)),
  })

  const groups = (['Kullanıcı', 'Müşteri', 'Tedarikçi', 'Dış üretici'] as const)
    .map((group) => ({
      label: GROUP_LABEL[group],
      options: (recipients.data ?? [])
        .filter((r) => r.group === group)
        .map((r) => ({ value: r.email, label: `${r.name} <${r.email}>` })),
    }))
    .filter((g) => g.options.length > 0)

  const customerEmails = (recall.data?.recipients ?? []).map((r) => r.contact.email).filter((e): e is string => !!e)
  const mailto = draft && to.length > 0 ? mailtoLink(to, draft) : null

  return (
    <Page
      title={t('Rapor gönder (e-posta)')}
      description={t('Hazır raporlardan birini seçin, alıcıları ve notunuzu ekleyin; göndermeden önce metnin tamamını görün. Kritik alarmlar ayrıca kendiliğinden yönetici ve kaliteye gider.')}
    >
      {status.data && !status.data.smtp_configured && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={t('E-posta sunucusu (SMTP) tanımlı değil')}
          description={t('E-postalar giden kutusunda "Kuyrukta" bekler; yönetici SMTP ayarını yapınca gönderilir. Hemen göndermek için "E-posta programında aç" düğmesini kullanın.')}
        />
      )}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={11}>
          <Card title={t('1. Rapor ve alıcılar')}>
            <Form layout="vertical">
              <Form.Item label={t('Rapor')}>
                <Select<ReportKind>
                  value={kind}
                  options={REPORTS}
                  onChange={(value) => {
                    setKind(value)
                    setEdited(null)
                  }}
                />
              </Form.Item>
              {kind === 'recall' && (
                <Form.Item label={t('Geri çağırma')}>
                  <Select<number>
                    placeholder={t('Geri çağırma seçin')}
                    value={recallId}
                    loading={recalls.isPending}
                    onChange={(id) => {
                      setRecallId(id)
                      setEdited(null)
                    }}
                    options={(recalls.data ?? []).map((r) => ({
                      value: r.id,
                      label: `${r.recall_no} · ${r.source_lot_no} · ${r.status === 'ACIK' ? t('Açık') : t('Kapandı')}`,
                    }))}
                  />
                  {customerEmails.length > 0 && (
                    <Button type="link" style={{ paddingInline: 0 }} onClick={() => setTo([...new Set([...to, ...customerEmails])])}>
                      {t('Etkilenen müşterileri alıcı yap ({n})', { n: customerEmails.length })}
                    </Button>
                  )}
                </Form.Item>
              )}
              <Form.Item label={t('Alıcılar')} extra={t('Listeden seçin ya da adresi yazıp Enter’a basın.')}>
                <Select
                  mode="tags"
                  value={to}
                  onChange={setTo}
                  options={groups}
                  placeholder={t('ör. yonetici@firma.com')}
                  tokenSeparators={[',', ';', ' ']}
                  loading={recipients.isPending}
                />
              </Form.Item>
              <Form.Item label={t('Not (raporun başına eklenir)')}>
                <Input.TextArea
                  rows={3}
                  maxLength={1000}
                  value={note}
                  onChange={(event) => {
                    setNote(event.target.value)
                    setEdited(null)
                  }}
                  placeholder={t('ör. Yarın sabah toplantıda konuşalım.')}
                />
              </Form.Item>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={13}>
          <Card
            title={t('2. Ön izleme')}
            extra={
              edited && (
                <Button size="small" icon={<ReloadOutlined />} onClick={() => setEdited(null)}>
                  {t('Rapordan yeniden oluştur')}
                </Button>
              )
            }
          >
            {!draft ? (
              <Typography.Text type="secondary">
                {kind === 'recall' && recallId == null ? t('Önce bir geri çağırma seçin.') : t('Rapor hazırlanıyor…')}
              </Typography.Text>
            ) : (
              <>
                <Input
                  addonBefore={t('Konu')}
                  value={draft.subject}
                  maxLength={200}
                  onChange={(event) => setEdited({ ...draft, subject: event.target.value })}
                  style={{ marginBottom: 8 }}
                />
                <Input.TextArea
                  className="mail-preview"
                  value={draft.body}
                  autoSize={{ minRows: 10, maxRows: 22 }}
                  onChange={(event) => setEdited({ ...draft, body: event.target.value })}
                  aria-label={t('E-posta metni')}
                />
                <Space wrap style={{ marginTop: 12 }}>
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    disabled={to.length === 0}
                    loading={send.isPending}
                    onClick={() => send.mutate()}
                  >
                    {t('Gönder')}
                  </Button>
                  <Button icon={<MailOutlined />} disabled={!mailto} href={mailto?.href}>
                    {t('E-posta programında aç')}
                  </Button>
                  {to.length === 0 && <span className="muted">{t('Önce alıcı seçin.')}</span>}
                  {kind === 'recall' && !edited && customerEmails.some((email) => to.includes(email)) && (
                    <span className="muted">{t('Her müşteriye yalnız kendi miktarını içeren ayrı e-posta gider.')}</span>
                  )}
                  {mailto?.truncated && <span className="muted">{t('Metin uzun: e-posta programına kısaltılmış hâli gider.')}</span>}
                </Space>
              </>
            )}
          </Card>
        </Col>
      </Row>

      <Card
        title={t('Giden kutusu')}
        style={{ marginTop: 16 }}
        extra={
          user.role === 'YONETICI' && (
            <Button size="small" icon={<SendOutlined />} loading={deliver.isPending} onClick={() => deliver.mutate()}>
              {t('Kuyruktakileri şimdi gönder')}
            </Button>
          )
        }
      >
        {outbox.isError && <QueryError error={outbox.error} onRetry={() => outbox.refetch()} />}
        <Table<MailRow>
          rowKey="id"
          size="small"
          loading={outbox.isPending}
          dataSource={outbox.data}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: t('Giden kutusu boş.') }}
          expandable={{ expandedRowRender: (row) => <pre className="mail-body">{row.body}</pre> }}
          columns={[
            { title: t('Zaman'), dataIndex: 'created_at', render: formatDateTime },
            { title: t('Gönderen'), dataIndex: 'created_by_name', render: (name: string | null) => name ?? '—' },
            { title: t('Tür'), dataIndex: 'kind', render: (k: string) => (k === 'ALARM' ? <Tag color="red">{t('Alarm')}</Tag> : <Tag>{t('Rapor')}</Tag>) },
            { title: t('Konu'), dataIndex: 'subject' },
            { title: t('Alıcılar'), dataIndex: 'recipients', render: (value: string) => <span style={{ whiteSpace: 'normal', display: 'block', maxWidth: 280 }}>{value}</span> },
            {
              title: t('Durum'),
              key: 'status',
              render: (_, row) => (
                <Space orientation="vertical" size={0}>
                  <Tag color={STATUS_COLOR[row.status]}>{MAIL_STATUS[row.status]}</Tag>
                  {row.sent_at && <span className="muted">{formatDateTime(row.sent_at)}</span>}
                  {row.last_error && <span className="muted" title={row.last_error}>{row.last_error.slice(0, 60)}</span>}
                  {row.status === 'HATA' && user.role === 'YONETICI' && (
                    <Button size="small" type="link" style={{ padding: 0 }} onClick={() => retry.mutate(row.id)}>
                      {t('Yeniden dene')}
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </Page>
  )
}
