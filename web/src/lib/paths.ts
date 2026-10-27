// Birden çok ekranın kurduğu adresler.

export type TraceDirection = 'forward' | 'backward'

export function tracePath(lotNo: string, direction: TraceDirection = 'forward'): string {
  return `/izleme/${encodeURIComponent(lotNo)}${direction === 'backward' ? '/geri' : ''}`
}
