import { describe, expect, it } from 'vitest'
import { compare, discountPercent, divide, fromScaled, multiply, parseUserDecimal, sum, toScaled } from './decimal'

describe('ondalık hesap (kayan nokta yok)', () => {
  it('ölçekleme ve geri çevirme kayıpsız', () => {
    expect(toScaled('1543.5', 2)).toBe(154350n)
    expect(fromScaled(154350n, 2)).toBe('1543.50')
    expect(fromScaled(-5n, 3)).toBe('-0.005')
    expect(fromScaled(7n, 0)).toBe('7')
  })

  it('fazla basamak yarım yukarı yuvarlanır (sunucudaki ROUND_HALF_UP gibi)', () => {
    expect(fromScaled(toScaled('18.158824', 2), 2)).toBe('18.16')
    expect(fromScaled(toScaled('0.125', 2), 2)).toBe('0.13')
    expect(fromScaled(toScaled('-0.125', 2), 2)).toBe('-0.13')
  })

  it('şartname örneği: 85 × 5,50 = 467,50 € ve hammadde toplamı 1.076,00 €', () => {
    expect(multiply('85', '5.50', 2)).toBe('467.50')
    expect(sum([multiply('100', '9.70', 2), multiply('2', '24.00', 2), multiply('5', '11.60', 2)], 2)).toBe(
      '1076.00',
    )
  })

  it('bölme: EKP = 1.543,50 / 85 = 18,158824 (gösterim 18,16)', () => {
    expect(divide('1543.50', '85', 6)).toBe('18.158824')
    expect(divide('1543.50', '85', 2)).toBe('18.16')
    expect(divide('-1', '3', 2)).toBe('-0.33')
    expect(() => divide('1', '0', 2)).toThrow()
  })

  it('0,1 + 0,2 tam olarak 0,3', () => {
    expect(sum(['0.1', '0.2'], 2)).toBe('0.30')
    expect(compare(sum(['0.1', '0.2'], 3), '0.3')).toBe(0)
  })

  it('karşılaştırma', () => {
    expect(compare('2', '1.999')).toBe(1)
    expect(compare('1.5', '1.50')).toBe(0)
    expect(compare('0.5', '2')).toBe(-1)
  })
})

describe('kullanıcı girişi', () => {
  it('virgül ve nokta ondalık ayırıcı olarak kabul edilir', () => {
    expect(parseUserDecimal('9,70', 4)).toBe('9.70')
    expect(parseUserDecimal(' 100 ', 3)).toBe('100')
    expect(parseUserDecimal('0.5', 3)).toBe('0.5')
  })

  it('binlik ayırıcı, eksi, harf ve fazla basamak reddedilir', () => {
    expect(parseUserDecimal('1.543,50', 2)).toBeNull()
    expect(parseUserDecimal('-1', 3)).toBeNull()
    expect(parseUserDecimal('12a', 3)).toBeNull()
    expect(parseUserDecimal('1,2345', 3)).toBeNull()
    expect(parseUserDecimal('', 3)).toBeNull()
  })
})

describe('liste fiyatı altı', () => {
  it('yüzde olarak bulunur; liste fiyatı ve üstü indirim değildir', () => {
    expect(discountPercent('20.80', '26.00')).toBe(20)
    expect(discountPercent('24.89', '24.90')).toBe(1)
    expect(discountPercent('24.90', '24.90')).toBeNull()
    expect(discountPercent('30.00', '24.90')).toBeNull()
    expect(discountPercent('10.00', null)).toBeNull()
  })
})
