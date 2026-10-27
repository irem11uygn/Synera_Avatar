// Parçalamalar (Görev 2): taslak → onaylandı.

import { useQuery } from '@tanstack/react-query'
import { Button, Table, type TableColumnsType } from 'antd'
import { api } from '../api/client'
import type { AllocationMethod, Cutting, CuttingStatus } from '../api/types'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { CuttingStatusTag } from '../components/StatusTags'
import { formatDateTime, formatMoney, formatQty } from '../lib/format'
import { ALLOCATION_METHOD } from '../lib/labels'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

const COLUMNS: TableColumnsType<Cutting> = [
  {
    title: t('Parçalama no'),
    dataIndex: 'cutting_no',
    render: (no: string, row) => <Link to={`/parcalama/${row.id}`}>{no}</Link>,
  },
  { title: t('Durum'), dataIndex: 'status', render: (status: CuttingStatus) => <CuttingStatusTag status={status} /> },
  { title: t('Reçete'), dataIndex: 'recipe_name' },
  {
    title: t('Giriş lotu'),
    dataIndex: 'input_lot_no',
    render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link>,
  },
  { title: t('Giriş'), dataIndex: 'input_qty', align: 'right', render: (v: string) => formatQty(v, 'KG') },
  { title: t('Yöntem'), dataIndex: 'method', render: (m: AllocationMethod) => ALLOCATION_METHOD[m] },
  { title: t('Toplam maliyet'), dataIndex: 'total_cost', align: 'right', render: formatMoney },
  { title: t('Tarih'), dataIndex: 'cut_at', render: formatDateTime },
]

export default function CuttingListPage() {
  const cuttings = useQuery({ queryKey: ['cuttings'], queryFn: () => api<Cutting[]>('/cuttings') })

  return (
    <Page
      title={t('Parçalama')}
      description={t('Bütün karkas parçalara ayrılır; maliyet parçalara dağıtılır. Tartım girilip onaylanınca parçalar stoka girer.')}
      extra={
        <Button type="primary" onClick={() => navigate('/parcalama/yeni')}>
          {t('Yeni parçalama')}
        </Button>
      }
    >
      {cuttings.isError && <QueryError error={cuttings.error} onRetry={() => cuttings.refetch()} />}
      <Table<Cutting>
        rowKey="id"
        size="middle"
        loading={cuttings.isPending}
        columns={COLUMNS}
        dataSource={cuttings.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('Henüz parçalama yok.') }}
      />
    </Page>
  )
}
