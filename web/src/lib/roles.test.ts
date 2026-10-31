import { describe, expect, it } from 'vitest'
import { canOpenPage } from './roles'

describe('ekran erişimi', () => {
  it('yönetici ekranları adres elle yazılınca da kapalı', () => {
    expect(canOpenPage('/kullanicilar', 'YONETICI')).toBe(true)
    expect(canOpenPage('/kullanicilar', 'DEPO')).toBe(false)
    expect(canOpenPage('/denetim', 'KALITE')).toBe(false)
    expect(canOpenPage('/alarm-ayarlari', 'MAGAZA')).toBe(false)
    expect(canOpenPage('/gun-sonu', 'MAGAZA')).toBe(true)
    expect(canOpenPage('/gun-sonu', 'URETIM')).toBe(false)
  })

  it('okuma herkese açık ekranlar ve alarm bağlantıları açık kalır', () => {
    expect(canOpenPage('/uretim/5', 'KALITE')).toBe(true) // verim sapması alarmının bağlantısı
    expect(canOpenPage('/geri-cagirma/3', 'DEPO')).toBe(true)
    expect(canOpenPage('/kullanicilar-yok', 'DEPO')).toBe(true) // yalnız tam yol ya da alt yol
  })
})
