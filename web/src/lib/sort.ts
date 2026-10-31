// Tablo sıralama: sütun başlığına tıklayınca artan/azalan. API ondalıkları metin gönderir ("1543.50"),
// bu yüzden sayıya benzeyen metinler sayı olarak karşılaştırılır; diğerleri Türkçe alfabe sırasıyla
// (ç, ğ, ı, ö, ş, ü doğru yerde; "LOT-2" < "LOT-10"). Tarih ve zaman ISO biçiminde geldiği için metin
// sırası zaman sırasıdır. Boş hücre sonda kalır.

import type { TableColumnsType } from 'antd'

const NUMERIC = /^-?\d+(\.\d+)?$/

const isEmpty = (value: unknown) => value === null || value === undefined || value === ''

export function compareValues(a: unknown, b: unknown): number {
  if (isEmpty(a) || isEmpty(b)) return isEmpty(a) === isEmpty(b) ? 0 : isEmpty(a) ? 1 : -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  const x = String(a)
  const y = String(b)
  if (NUMERIC.test(x) && NUMERIC.test(y)) return Number(x) - Number(y)
  return x.localeCompare(y, 'tr', { numeric: true, sensitivity: 'base' })
}

/** dataIndex'i olan her sütuna sıralama ekler; işlem sütunları ve kendi sıralaması olanlar olduğu gibi kalır. */
export function sortable<T>(columns: TableColumnsType<T>): TableColumnsType<T> {
  return columns.map((column) => {
    if (!('dataIndex' in column) || typeof column.dataIndex !== 'string' || column.sorter !== undefined) return column
    const field = column.dataIndex
    const value = (row: T) => (row as Record<string, unknown>)[field]
    return { ...column, sorter: (a: T, b: T) => compareValues(value(a), value(b)) }
  })
}
