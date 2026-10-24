import { describe, expect, it } from 'vitest'
import { matchPath } from './router'

describe('yol eşleme', () => {
  it('kök ve sabit yollar', () => {
    expect(matchPath('/', '/')).toEqual({})
    expect(matchPath('/uretim', '/uretim')).toEqual({})
    expect(matchPath('/uretim', '/uretim/')).toEqual({})
    expect(matchPath('/', '/uretim')).toBeNull()
  })

  it('parametreler çözülür', () => {
    expect(matchPath('/uretim/:id', '/uretim/7')).toEqual({ id: '7' })
    expect(matchPath('/lotlar/:lotNo', '/lotlar/SUC-2026-045')).toEqual({ lotNo: 'SUC-2026-045' })
    expect(matchPath('/lotlar/:lotNo', '/lotlar/A%2FB')).toEqual({ lotNo: 'A/B' })
  })

  it('farklı uzunluk ya da parça eşleşmez', () => {
    expect(matchPath('/uretim/:id', '/uretim')).toBeNull()
    expect(matchPath('/uretim/:id', '/lotlar/7')).toBeNull()
  })
})
