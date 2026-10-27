import { Select } from 'antd'
import { lang, LANGS, setLang, t, type Lang } from '../lib/i18n'

/** Dil seçimi (Türkçe / English); kutuda kısa kod, listede tam ad. Seçim tarayıcıda hatırlanır. */
export function LanguageSwitch() {
  return (
    <Select<Lang>
      value={lang}
      onChange={setLang}
      options={LANGS}
      labelRender={({ value }) => String(value).toUpperCase()}
      aria-label={t('Dil')}
      popupMatchSelectWidth={false}
      style={{ width: 72 }}
    />
  )
}
