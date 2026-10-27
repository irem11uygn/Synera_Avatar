import { SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { AutoComplete, Input } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { Lot } from '../api/types'
import { LOT_STATUS } from '../lib/labels'
import { navigate } from '../lib/router'

/** Üst çubukta lot arama: lot numarası ya da ürün adıyla bul, seçince lot kartına git. */
export function LotSearch() {
  const [text, setText] = useState('')
  const [active, setActive] = useState(false)
  const lots = useQuery({ queryKey: ['lots', 'all'], queryFn: () => api<Lot[]>('/lots'), enabled: active })
  const needle = text.trim().toUpperCase() // lot numaraları ASCII; "sirt" → "SIRT" (tr-TR "SİRT" yapardı)
  const words = text.trim().toLocaleLowerCase('tr-TR')
  const options = needle
    ? (lots.data ?? [])
        .filter((lot) => lot.lot_no.includes(needle) || lot.product_name.toLocaleLowerCase('tr-TR').includes(words))
        .slice(0, 10)
        .map((lot) => ({
          value: lot.lot_no,
          label: `${lot.lot_no} · ${lot.product_name}${lot.status === 'BLOKE' ? ` · ${LOT_STATUS.BLOKE}` : ''}`,
        }))
    : []

  function open(lotNo: string) {
    const value = lotNo.trim().toUpperCase()
    if (!value) return
    setText('')
    navigate(`/lotlar/${encodeURIComponent(value)}`)
  }

  return (
    <AutoComplete
      value={text}
      options={options}
      onChange={setText}
      onSelect={(value: string) => open(value)}
      onFocus={() => setActive(true)}
      style={{ width: '100%', maxWidth: 420 }}
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder="Lot no ya da ürün ara…"
        aria-label="Lot ara"
        allowClear
        onPressEnter={() => options.length === 0 && open(text)}
      />
    </AutoComplete>
  )
}
