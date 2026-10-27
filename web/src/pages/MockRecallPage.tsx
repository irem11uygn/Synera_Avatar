// Geri çağırma tatbikatı (mock recall): gıda güvenliği denetimlerinde istenir. Bir lot seçilir; geriye
// (tedarikçi) ve ileriye (müşteri, elimizdeki stok) izleme yapılır, ne kadar sürede bulunduğu ölçülür.
// Hiçbir lot satışa kapatılmaz, kayıt değişmez.

import { PlayCircleOutlined, PrinterOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, Row, Space, Table, Typography } from 'antd'
import { useState } from 'react'
import { errorMessage } from '../api/client'
import { LotPicker } from '../components/LotPicker'
import { Page } from '../components/Page'
import { Stat } from '../components/Stat'
import { runDrill, type Drill } from '../lib/drill'
import { formatDate, formatQty } from '../lib/format'
import { navigate } from '../lib/router'

export function DrillTables({ drill }: { drill: Drill }) {
  const { forward, backward } = drill
  return (
    <>
      <div className="section-title">1. Hammadde nereden geldi? (tedarikçiler)</div>
      <Table
        rowKey={(s) => `${s.lot_no}-${s.purchase_doc_no}`}
        size="small"
        pagination={false}
        dataSource={backward.suppliers}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Tedarikçi kaydı yok.' }}
        columns={[
          { title: 'Tedarikçi', dataIndex: 'supplier' },
          { title: 'Lot', dataIndex: 'lot_no' },
          { title: 'Fatura', dataIndex: 'purchase_doc_no' },
          { title: 'Tarih', dataIndex: 'purchase_date', render: formatDate },
          { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
          { title: 'Telefon', render: (_, s) => s.contact.phone ?? '—' },
        ]}
      />
      <div className="section-title">2. Elimizde kalan (hemen ayrılmalı)</div>
      <Table
        rowKey={(s) => `${s.lot_no}-${s.warehouse_code}`}
        size="small"
        pagination={false}
        dataSource={forward.stock}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Elimizde bu lottan ya da türevlerinden mal kalmamış.' }}
        columns={[
          { title: 'Yer', dataIndex: 'warehouse_name' },
          { title: 'Ürün', dataIndex: 'product_name' },
          { title: 'Lot', dataIndex: 'lot_no' },
          { title: 'Miktar', align: 'right', render: (_, s) => formatQty(s.qty, s.base_unit) },
        ]}
      />
      <div className="section-title">3. Hangi müşterilere gitti? (aranacaklar)</div>
      <Table
        rowKey={(r) => `${r.customer_id}-${r.lot_no}`}
        size="small"
        pagination={false}
        dataSource={forward.recipients}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Bu lottan satış yapılmamış.' }}
        columns={[
          { title: 'Müşteri', dataIndex: 'customer' },
          { title: 'Ürün / lot', render: (_, r) => `${r.product_name} · ${r.lot_no}` },
          { title: 'Müşteride', align: 'right', render: (_, r) => formatQty(r.qty, r.base_unit) },
          { title: 'Yetkili', render: (_, r) => r.contact.person ?? '—' },
          { title: 'Telefon', render: (_, r) => r.contact.phone ?? '—' },
          { title: 'E-posta', render: (_, r) => r.contact.email ?? '—' },
        ]}
      />
    </>
  )
}

export default function MockRecallPage() {
  const [lotNo, setLotNo] = useState('')
  const [drill, setDrill] = useState<Drill | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function start(value = lotNo) {
    const lot = value.trim().toUpperCase()
    if (!lot) return
    setBusy(true)
    setError(null)
    try {
      setDrill(await runDrill(lot))
    } catch (caught) {
      setDrill(null)
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  const customers = drill ? new Set(drill.forward.recipients.map((r) => r.customer_id)).size : 0

  return (
    <Page
      title="Geri çağırma tatbikatı"
      description="Denetimlerde istenen deneme: bir lot seçin, nereden geldiğini ve nereye gittiğini bulun. Hiçbir lot satışa kapatılmaz; yalnız ne kadar hızlı ve eksiksiz bulunduğu ölçülür."
      extra={
        drill && (
          <Button
            icon={<PrinterOutlined />}
            onClick={() => navigate(`/yazdir/tatbikat/${encodeURIComponent(drill.lotNo)}?sure=${drill.ms}`)}
          >
            Tatbikat raporu yazdır
          </Button>
        )
      }
    >
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <LotPicker value={lotNo} onChange={setLotNo} onPick={(value) => void start(value)} />
          <Button type="primary" icon={<PlayCircleOutlined />} loading={busy} onClick={() => void start()}>
            Tatbikatı başlat
          </Button>
        </Space>
        <Typography.Paragraph type="secondary" style={{ margin: '8px 0 0' }}>
          Örnek: ET-2026-001 (et) → sucuk → marketler.
        </Typography.Paragraph>
      </Card>
      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}
      {drill && (
        <>
          <Row gutter={[12, 12]} style={{ marginBottom: 8 }}>
            <Col xs={12} lg={6}>
              <Stat label="Bulma süresi" value={`${(drill.ms / 1000).toFixed(2)} sn`} hint="Hedef: 4 saat içinde" tone="success" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Etkilenen lot" value={drill.forward.lots.length} hint="Kaynak ve ondan yapılanlar" tone="brand" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Tedarikçi" value={new Set(drill.backward.suppliers.map((s) => s.supplier)).size} />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Aranacak müşteri" value={customers} tone={customers ? 'warning' : 'neutral'} />
            </Col>
          </Row>
          <DrillTables drill={drill} />
        </>
      )}
    </Page>
  )
}
