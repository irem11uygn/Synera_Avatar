// Geri çağırma tatbikatı: bir lot için geriye (tedarikçi) ve ileriye (müşteri, stok) izleme ve süresi.

import { api } from '../api/client'
import type { Trace } from '../api/types'

export type Drill = { lotNo: string; forward: Trace; backward: Trace; ms: number; at: string }

export async function runDrill(lotNo: string): Promise<Drill> {
  const started = performance.now()
  const [forward, backward] = await Promise.all([
    api<Trace>(`/trace/forward/${encodeURIComponent(lotNo)}`),
    api<Trace>(`/trace/backward/${encodeURIComponent(lotNo)}`),
  ])
  return { lotNo, forward, backward, ms: Math.max(1, Math.round(performance.now() - started)), at: new Date().toISOString() }
}
