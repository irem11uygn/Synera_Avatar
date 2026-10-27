import { useQuery } from '@tanstack/react-query'
import { AutoComplete, Input } from 'antd'
import { api } from '../api/client'
import type { Lot } from '../api/types'

/** Lot numarası girişi: yazdıkça kayıtlı lotlardan öneri (bloke olanlar işaretli). */
export function LotPicker({
  value,
  onChange,
  onPick,
}: {
  value: string
  onChange: (value: string) => void
  onPick?: (value: string) => void
}) {
  const lots = useQuery({ queryKey: ['lots', 'all'], queryFn: () => api<Lot[]>('/lots') })
  const needle = value.trim().toUpperCase() // lot numaraları ASCII; tr-TR "sirt" → "SİRT" yapardı
  const options = (lots.data ?? [])
    .filter((lot) => !needle || lot.lot_no.includes(needle))
    .slice(0, 12)
    .map((lot) => ({
      value: lot.lot_no,
      label: `${lot.lot_no} · ${lot.product_name}${lot.status === 'BLOKE' ? ' · satışa kapalı' : ''}`,
    }))
  return (
    <AutoComplete value={value} options={options} onChange={onChange} onSelect={(v: string) => onPick?.(v)} style={{ minWidth: 260 }}>
      <Input aria-label="Lot numarası" placeholder="ET-2026-001" allowClear />
    </AutoComplete>
  )
}
