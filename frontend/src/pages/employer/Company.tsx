import { Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Company } from '../../api/types'
import { ErrorBox, Loading, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'

const FIELDS: { k: keyof Company; area?: boolean; ph?: string }[] = [
  { k: 'company_name' },
  { k: 'industry', ph: 'FinTech, E-commerce…' },
  { k: 'description', area: true },
  { k: 'website' },
  { k: 'city' },
  { k: 'size', ph: '50–200' },
  { k: 'contact_name' },
  { k: 'contact_email' },
  { k: 'contact_phone' },
  { k: 'contact_telegram' },
]

export default function CompanyPage() {
  const { data, error, loading, setData } = useApi<Company>('/employer/profile')
  const { t } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (data) setForm(Object.fromEntries(FIELDS.map((f) => [f.k, (data[f.k] as string | null) ?? ''])))
  }, [data])

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      setData(await api<Company>('/employer/profile', { method: 'PUT', body: form }))
      toast(t('emp.company.saved'))
    } catch (ex) {
      setErr(errorMessage(ex))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack-lg" onSubmit={submit}>
      <div className="page-head"><div><h1>{t('nav.company')}</h1><p className="sub">{t('emp.company.sub')}</p></div>
        <button className="btn" disabled={busy}><Save size={16} />{busy ? t('common.saving') : t('common.save')}</button></div>
      <ErrorBox error={err} />
      <div className="card"><div className="grid grid-2">
        {FIELDS.map((f) => (
          <div key={f.k} className="field" style={f.area ? { gridColumn: '1 / -1' } : undefined}>
            <label htmlFor={`company-${f.k}`}>{t(`emp.company.field.${f.k}` as MessageKey)}</label>
            {f.area ? <textarea id={`company-${f.k}`} className="textarea" value={form[f.k] ?? ''} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />
              : <input id={`company-${f.k}`} className="input" placeholder={f.ph} value={form[f.k] ?? ''} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />}</div>
        ))}
      </div></div>
    </form>
  )
}
