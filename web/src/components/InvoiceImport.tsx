// Faturadan doldur: fatura ya da irsaliye metni yapıştırılır, sunucu tedarikçi, belge no, tarih ve
// satırları (ürün, miktar, lot, fiyat, SKT) önerir. Öneri yalnız formu doldurur; kaydetmek için
// kullanıcı her alanı kontrol edip "Alışı kaydet"e basar (insan onayı).

import { FileTextOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Input, Modal, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { InvoiceSuggestion, LineSuggestion } from '../api/types'
import { formatDate, formatDecimal } from '../lib/format'
import { t } from '../lib/i18n'

const EXAMPLE = `Örnek Et Tedarik
Fatura No: FAT-ET-2026-0420   Tarih: 27.10.2026
Sucukluk et   LOT: ET-2026-002   120 kg x 9,90 € = 1.188,00 €   SKT: 15.11.2026
Doğal bağırsak   BAG-2026-008   6 kg   11,60 €/kg`

const MATCH: Record<string, { color: string; label: string }> = {
  kod: { color: 'green', label: t('Kodla eşleşti') },
  ad: { color: 'green', label: t('Adla eşleşti') },
  benzer: { color: 'orange', label: t('Benzer ad — kontrol edin') },
  yok: { color: 'red', label: t('Ürün bulunamadı') },
}

export function InvoiceImport({ onApply }: { onApply: (suggestion: InvoiceSuggestion) => void }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const parse = useMutation({
    mutationFn: () => api<InvoiceSuggestion>('/purchases/parse-text', { method: 'POST', body: { text } }),
  })
  const result = parse.data

  return (
    <>
      <Button icon={<FileTextOutlined />} onClick={() => setOpen(true)}>
        {t('Faturadan doldur')}
      </Button>
      <Modal
        open={open}
        width={880}
        title={t('Fatura / irsaliye metninden doldur')}
        onCancel={() => setOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setOpen(false)}>{t('Vazgeç')}</Button>
            <Button onClick={() => parse.mutate()} loading={parse.isPending} disabled={!text.trim()}>
              {t('Öneri çıkar')}
            </Button>
            <Button
              type="primary"
              disabled={!result || result.lines.length === 0}
              onClick={() => {
                onApply(result!)
                setOpen(false)
              }}
            >
              {t('Forma aktar')}
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary">
          {t('E-faturadaki ya da irsaliyedeki metni kopyalayıp buraya yapıştırın. Sistem ürünü, miktarı, lot numarasını, fiyatı ve SKT’yi önerir; hiçbir şey kaydedilmez. Forma aktardıktan sonra her alanı kontrol edin.')}
        </Typography.Paragraph>
        <Input.TextArea
          rows={7}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={EXAMPLE}
          aria-label={t('Fatura metni')}
          className="mail-preview"
        />
        <Button type="link" size="small" style={{ paddingInline: 0 }} onClick={() => setText(EXAMPLE)}>
          {t('Örnek metni dene')}
        </Button>
        {parse.isError && <Alert type="error" showIcon title={errorMessage(parse.error)} style={{ marginTop: 12 }} />}
        {result && (
          <div style={{ marginTop: 12 }}>
            <Space wrap style={{ marginBottom: 8 }}>
              <Tag color={result.supplier_name ? 'green' : 'red'}>
                {t('Tedarikçi')}: {result.supplier_name ?? t('bulunamadı')}
              </Tag>
              <Tag color={result.doc_no ? 'green' : 'red'}>
                {t('Belge no')}: {result.doc_no ?? t('bulunamadı')}
              </Tag>
              <Tag color={result.doc_date ? 'green' : 'red'}>
                {t('Tarih')}: {result.doc_date ? formatDate(result.doc_date) : t('bulunamadı')}
              </Tag>
            </Space>
            {result.warnings.map((warning) => (
              <Alert key={warning} type="warning" showIcon title={warning} style={{ marginBottom: 6 }} />
            ))}
            <Table<LineSuggestion>
              size="small"
              rowKey={(row) => row.source}
              pagination={false}
              dataSource={result.lines}
              scroll={{ x: 'max-content' }}
              columns={[
                {
                  title: t('Ürün'),
                  key: 'product',
                  render: (_, row) => (
                    <>
                      {row.product_name ?? '—'}
                      <div>
                        <Tag color={MATCH[row.match]?.color}>{MATCH[row.match]?.label ?? row.match}</Tag>
                      </div>
                    </>
                  ),
                },
                { title: t('Miktar'), key: 'qty', align: 'right', render: (_, row) => (row.qty ? `${formatDecimal(row.qty, 0, 3)} ${row.unit ?? ''}` : '—') },
                { title: t('Lot'), dataIndex: 'lot_no', render: (v: string | null) => v ?? <Tag color="red">{t('yok')}</Tag> },
                { title: t('Birim fiyat'), dataIndex: 'unit_price', align: 'right', render: (v: string | null) => (v ? `${formatDecimal(v, 2, 4)} €` : '—') },
                { title: t('SKT'), dataIndex: 'expiry_date', render: (v: string | null) => (v ? formatDate(v) : '—') },
                {
                  title: t('Not'),
                  dataIndex: 'warnings',
                  render: (warnings: string[]) =>
                    warnings.length === 0 ? <Tag color="green">{t('Tamam')}</Tag> : <span className="invoice-warn">{warnings.join(' ')}</span>,
                },
              ]}
            />
          </div>
        )}
      </Modal>
    </>
  )
}
