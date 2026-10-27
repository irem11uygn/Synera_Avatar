// Birden çok sayfanın kullandığı sorgular. Sorgu anahtarları tek yerde: bir kayıt değişince
// ilgili listeler yenilenir.

import { useQuery, type QueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { DayEnd, Partner, Product, ProductKind, StockRow, Warehouse } from './types'

export function useProducts(kind?: ProductKind) {
  return useQuery({
    queryKey: ['products', kind ?? 'all'],
    queryFn: () => api<Product[]>('/products', { query: { kind } }),
  })
}

export function usePartners(role?: 'supplier' | 'customer' | 'subcontractor') {
  return useQuery({
    queryKey: ['partners', role ?? 'all'],
    queryFn: () => api<Partner[]>('/partners', { query: { role } }),
  })
}

export function useWarehouses() {
  return useQuery({ queryKey: ['warehouses'], queryFn: () => api<Warehouse[]>('/warehouses') })
}

export function useStock(params: { warehouse_id?: number; product_id?: number } = {}, enabled = true) {
  return useQuery({
    queryKey: ['stock', params],
    queryFn: () => api<StockRow[]>('/stock', { query: params }),
    enabled,
  })
}

export function useDayEnd(day: string, warehouseId?: number) {
  return useQuery({
    queryKey: ['day-end', day, warehouseId ?? 'all'],
    queryFn: () => api<DayEnd>('/day-end', { query: { day, warehouse_id: warehouseId } }),
  })
}

/**
 * Stok, lot, belge ya da ana veri değiştiren her işlemden sonra çağrılır. Oturum ve sistem
 * durumu sorguları dışında her şey yeniden yüklenir; ekranlar defterle tutarlı kalır.
 */
export function refreshBusinessData(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({
    predicate: (query) => !['me', 'health'].includes(String(query.queryKey[0])),
  })
}
