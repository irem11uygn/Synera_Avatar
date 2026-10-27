// Dil seçeneği: Türkçe (varsayılan) ve İngilizce. Ekrandaki her metin Türkçe yazılır ve t() ile
// çevrilir; İngilizce sözlükte karşılığı yoksa Türkçesi görünür (eksik çeviri ekranı bozmaz).
// Seçim tarayıcıda hatırlanır; dil değişince sayfa yeniden yüklenir (sabit listeler de çevrilsin).

import { EN } from '../i18n/en'

export type Lang = 'tr' | 'en'

const KEY = 'synera.lang'

function initialLang(): Lang {
  try {
    const stored = localStorage.getItem(KEY)
    if (stored === 'tr' || stored === 'en') return stored
  } catch {
    // Depolama kapalıysa varsayılan dil.
  }
  return 'tr'
}

export const lang: Lang = initialLang()

export const LANGS: { value: Lang; label: string }[] = [
  { value: 'tr', label: 'Türkçe' },
  { value: 'en', label: 'English' },
]

export function setLang(next: Lang): void {
  if (next === lang) return
  try {
    localStorage.setItem(KEY, next)
  } catch {
    return
  }
  window.location.reload()
}

/** Türkçe metnin seçili dildeki karşılığı; {ad} yer tutucuları params ile doldurulur. */
export function t(text: string, params?: Record<string, string | number>): string {
  const translated = lang === 'en' ? (EN[text] ?? text) : text
  if (!params) return translated
  return translated.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match))
}
