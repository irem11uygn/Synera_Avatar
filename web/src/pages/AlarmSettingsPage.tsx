// Alarm ve e-posta ayarları (yalnız yönetici): kural eşikleri, kuralları elle çalıştırma,
// e-posta sunucusu durumu. Eşik değişikliği denetim günlüğüne yazılır.

import { CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Col, Descriptions, Form, InputNumber, Row, Space, Typography } from 'antd'
import { useEffect } from 'react'
import { api, errorMessage } from '../api/client'
import type { MailStatusInfo, RuleRun, Thresholds } from '../api/types'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { t } from '../lib/i18n'
import { ALERT_KIND, ALERT_WHEN } from '../lib/labels'
import { navigate } from '../lib/router'

type Values = { yield_z: number; price_increase_pct: number; failed_logins: number }

const RULES: { kind: keyof typeof ALERT_KIND; when: string; who: string }[] = [
  { kind: 'VERIM_SAPMASI', when: ALERT_WHEN.VERIM_SAPMASI, who: t('Uyarı · yönetici, kalite, üretim') },
  { kind: 'FIYAT_ARTISI', when: ALERT_WHEN.FIYAT_ARTISI, who: t('Uyarı · yönetici, depo') },
  { kind: 'BLOKE_STOK', when: ALERT_WHEN.BLOKE_STOK, who: t('Uyarı · yönetici, kalite, depo') },
  { kind: 'GERI_CAGIRMA', when: ALERT_WHEN.GERI_CAGIRMA, who: t('Kritik · yönetici, kalite') },
  { kind: 'BLOKE_SATIS_DENEMESI', when: ALERT_WHEN.BLOKE_SATIS_DENEMESI, who: t('Kritik · yönetici, kalite, mağaza') },
  { kind: 'GERI_CAGIRMA_IHLALI', when: ALERT_WHEN.GERI_CAGIRMA_IHLALI, who: t('Kritik · yönetici, kalite') },
  { kind: 'HATALI_GIRIS', when: ALERT_WHEN.HATALI_GIRIS, who: t('Kritik · yalnız yönetici') },
  { kind: 'SKT_YAKLASIYOR', when: ALERT_WHEN.SKT_YAKLASIYOR, who: t('Uyarı · yönetici, kalite, depo, mağaza') },
  { kind: 'SAYIM_FARKI', when: ALERT_WHEN.SAYIM_FARKI, who: t('Uyarı · yönetici, depo') },
]

export default function AlarmSettingsPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<Values>()
  const thresholds = useQuery({ queryKey: ['thresholds'], queryFn: () => api<Thresholds>('/settings/alarm-thresholds') })
  const mail = useQuery({ queryKey: ['mail', 'status'], queryFn: () => api<MailStatusInfo>('/mail/status') })

  useEffect(() => {
    if (thresholds.data)
      form.setFieldsValue({
        yield_z: Number(thresholds.data.yield_z),
        price_increase_pct: Number(thresholds.data.price_increase_pct),
        failed_logins: Number(thresholds.data.failed_logins),
      })
  }, [thresholds.data, form])

  const save = useMutation({
    mutationFn: (values: Values) =>
      api<Thresholds>('/settings/alarm-thresholds', {
        method: 'PUT',
        body: {
          yield_z: String(values.yield_z),
          price_increase_pct: String(values.price_increase_pct),
          failed_logins: String(values.failed_logins),
        },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['thresholds'], data)
      message.success(t('Eşikler kaydedildi. Kurallar bir sonraki çalışmada yeni eşikleri kullanır.'))
    },
    onError: (error) => message.error(errorMessage(error)),
  })
  const run = useMutation({
    mutationFn: () => api<RuleRun>('/alerts/run-rules', { method: 'POST' }),
    onSuccess: (result) => {
      message.success(
        result.created.length > 0
          ? t('Kurallar çalıştı: {n} yeni alarm.', { n: result.created.length })
          : t('Kurallar çalıştı: yeni alarm yok.'),
      )
      result.notes.forEach((note) => message.warning(note))
      void queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
    onError: (error) => message.error(errorMessage(error)),
  })

  return (
    <Page
      title={t('Alarm ve e-posta ayarları')}
      description={t('Alarm kurallarının eşiklerini buradan değiştirin. Kurallar her girişte, ilgili kayıttan sonra ve aşağıdaki düğmeyle çalışır.')}
      extra={
        <Button type="primary" icon={<ThunderboltOutlined />} loading={run.isPending} onClick={() => run.mutate()}>
          {t('Kuralları şimdi çalıştır')}
        </Button>
      }
    >
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={t('Eşikler')}>
            {thresholds.isError && <QueryError error={thresholds.error} onRetry={() => thresholds.refetch()} />}
            <Form form={form} layout="vertical" onFinish={(values) => save.mutate(values)} disabled={thresholds.isPending}>
              <Form.Item
                name="yield_z"
                label={t('Verim sapması: z-skoru eşiği')}
                extra={t('2 = gerçek verim, beklenenden 2 standart sapmadan fazla uzaksa alarm. Küçük sayı daha çok alarm demektir.')}
                rules={[{ required: true }]}
              >
                <InputNumber min={0.5} max={10} step={0.5} decimalSeparator="," style={{ width: 160 }} />
              </Form.Item>
              <Form.Item
                name="price_increase_pct"
                label={t('Alış fiyatı artışı eşiği (%)')}
                extra={t('Bir önceki alışa göre bu yüzdeden fazla artış alarm açar.')}
                rules={[{ required: true }]}
              >
                <InputNumber min={0} max={500} step={1} decimalSeparator="," addonAfter="%" style={{ width: 160 }} />
              </Form.Item>
              <Form.Item
                name="failed_logins"
                label={t('Art arda hatalı giriş sayısı')}
                extra={t('Bir hesaba bu kadar hatalı giriş denenince kritik alarm açılır ve yöneticiye e-posta gider.')}
                rules={[{ required: true }]}
              >
                <InputNumber min={2} max={20} step={1} precision={0} style={{ width: 160 }} />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={save.isPending}>
                {t('Kaydet')}
              </Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('E-posta')}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label={t('E-posta sunucusu')}>
                {mail.data?.smtp_configured ? (
                  <Space>
                    <CheckCircleOutlined style={{ color: 'var(--success)' }} />
                    {t('Tanımlı ({host})', { host: mail.data.host ?? '' })}
                  </Space>
                ) : (
                  <Space>
                    <CloseCircleOutlined style={{ color: 'var(--warning)' }} />
                    {t('Tanımlı değil — e-postalar kuyrukta bekler')}
                  </Space>
                )}
              </Descriptions.Item>
              {mail.data?.sender && <Descriptions.Item label={t('Gönderen adresi')}>{mail.data.sender}</Descriptions.Item>}
            </Descriptions>
            <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
              {t('Sunucu ayarı .env dosyasındaki SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS ve MAIL_FROM ile yapılır (şifre kodda tutulmaz; varsayılan yerel Mailpit). Alarm e-postası, kullanıcı kartında e-postası olan abonelere gider: yönetici bütün türlere, diğer roller kendi işini ilgilendiren türlere (aşağıda). Herkes kendi aboneliğini değiştirebilir.')}
            </Typography.Paragraph>
            <Space wrap>
              <Button onClick={() => navigate('/e-posta')}>{t('Giden kutusu')}</Button>
              <Button onClick={() => navigate('/kullanicilar')}>{t('Kullanıcı e-postaları')}</Button>
            </Space>
          </Card>
          <Card title={t('Kurallar')} style={{ marginTop: 16 }}>
            <ul className="rule-list">
              {RULES.map((rule) => (
                <li key={rule.kind}>
                  <strong>{ALERT_KIND[rule.kind]}</strong>
                  <div>{rule.when}</div>
                  <div className="muted">{rule.who}</div>
                </li>
              ))}
            </ul>
          </Card>
        </Col>
      </Row>
    </Page>
  )
}
