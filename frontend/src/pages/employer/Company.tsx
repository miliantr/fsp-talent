import { Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Company } from '../../api/types'
import { ErrorBox, Loading, useToast } from '../../components/ui'

const FIELDS: { k: keyof Company; label: string; area?: boolean; ph?: string }[] = [
  { k: 'company_name', label: 'Название компании' },
  { k: 'industry', label: 'Направление деятельности', ph: 'FinTech, E-commerce…' },
  { k: 'description', label: 'Описание организации', area: true },
  { k: 'website', label: 'Сайт' },
  { k: 'city', label: 'Город' },
  { k: 'size', label: 'Размер', ph: '50–200' },
  { k: 'contact_name', label: 'Контактное лицо' },
  { k: 'contact_email', label: 'E-mail для кандидатов' },
  { k: 'contact_phone', label: 'Телефон' },
  { k: 'contact_telegram', label: 'Telegram' },
]

export default function CompanyPage() {
  const { data, error, loading, setData } = useApi<Company>('/employer/profile')
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
      toast('Профиль компании сохранён')
    } catch (ex) {
      setErr(errorMessage(ex))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack-lg" onSubmit={submit}>
      <div className="page-head"><div><h1>Профиль компании</h1><p className="sub">Кандидат видит эти данные в каждом приглашении.</p></div>
        <button className="btn" disabled={busy}><Save size={16} />{busy ? 'Сохраняем…' : 'Сохранить'}</button></div>
      <ErrorBox error={err} />
      <div className="card"><div className="grid grid-2">
        {FIELDS.map((f) => (
          <div key={f.k} className="field" style={f.area ? { gridColumn: '1 / -1' } : undefined}><label>{f.label}</label>
            {f.area ? <textarea className="textarea" value={form[f.k] ?? ''} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />
              : <input className="input" placeholder={f.ph} value={form[f.k] ?? ''} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />}</div>
        ))}
      </div></div>
    </form>
  )
}
