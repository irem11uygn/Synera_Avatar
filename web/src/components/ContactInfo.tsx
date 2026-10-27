import { Space } from 'antd'
import type { Recipient } from '../api/types'

/** Yetkili, tıklanınca arayan telefon ve e-posta (geri çağırma iletişim listesi, FR-307). */
export function ContactInfo({ contact }: { contact: Recipient['contact'] }) {
  return (
    <Space orientation="vertical" size={0}>
      {contact.person && <span>{contact.person}</span>}
      {contact.phone && <a href={`tel:${contact.phone.replace(/\s/g, '')}`}>{contact.phone}</a>}
      {contact.email && <a href={`mailto:${contact.email}`}>{contact.email}</a>}
    </Space>
  )
}
