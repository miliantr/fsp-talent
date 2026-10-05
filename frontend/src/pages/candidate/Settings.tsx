import { Languages, Link2, Lock, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, CandidateSettings } from '../../api/types'
import { LanguageSwitcher } from '../../components/LanguageSwitcher'
import { ErrorBox, Loading, Switch, useToast } from '../../components/ui'
import { useI18n } from '../../i18n/context'

export default function SettingsPage() {
  const s = useApi<CandidateSettings>('/candidate/settings')
  const p = useApi<CandidateProfile>('/candidate/profile')
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [err, setErr] = useState<string | null>(null)

  if ((s.loading && !s.data) || (p.loading && !p.data)) return <Loading />
  if (s.error) return <ErrorBox error={s.error} />
  if (!s.data || !p.data) return null
  const st = s.data

  const update = async (patch: Record<string, boolean>) => {
    setErr(null)
    try {
      s.setData(await api<CandidateSettings>('/candidate/settings', { method: 'PUT', body: patch }))
      toast(t('cand.settings.saved'))
    } catch (e) {
      setErr(errorMessage(e))
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.settings')}</h1><p className="sub">{t('cand.settings.sub')}</p></div></div>
      <ErrorBox error={err} />
      <div className={`alert ${st.searchable ? 'success' : 'warning'}`}>
        {st.searchable ? <ShieldCheck size={18} /> : <Lock size={18} />}
        <span>{st.searchable ? t('cand.settings.searchable') : t('cand.settings.notSearchable')}</span>
      </div>
      <div className="grid grid-2">
        <div className="card">
          <h3>{t('cand.settings.visibility')}</h3>
          <div className="divider" />
          <Switch checked={st.open_to_offers} onChange={(v) => update({ open_to_offers: v })} label={t('cand.settings.open')} hint={t('cand.settings.openHint')} />
          <Switch checked={st.show_full_name} onChange={(v) => update({ show_full_name: v })} label={t('cand.settings.fullName')} hint={t('cand.settings.fullNameHint')} />
          <Switch checked={st.show_fsp} onChange={(v) => update({ show_fsp: v })} label={t('cand.settings.fsp')} hint={t('cand.settings.fspHint')} />
          <Switch checked={st.show_salary} onChange={(v) => update({ show_salary: v })} label={t('cand.settings.salary')} />
          <p className="small muted" style={{ marginTop: 10 }}>{t('cand.settings.contactsNote')}</p>
        </div>
        <div className="stack-lg">
          <div className="card">
            <h3>{t('cand.settings.consents')}</h3>
            <div className="divider" />
            <div className="row between" style={{ padding: '10px 0' }}><span><span className="bold">{t('cand.settings.processing')}</span>
              <span className="small muted" style={{ display: 'block' }}>{t('cand.settings.processingGiven', { date: fmt.date(st.consent_processing_at) })}</span></span>
              <span className="badge success">{t('cand.settings.given')}</span></div>
            <Switch checked={st.consent_publication_at !== null} onChange={(v) => update({ consent_publication: v })}
              label={t('cand.settings.publication')}
              hint={st.consent_publication_at ? t('cand.settings.publicationGiven', { date: fmt.date(st.consent_publication_at) }) : t('cand.settings.publicationHint')} />
          </div>
          <div className="card">
            <div className="row between"><h3 className="row"><Languages size={18} color="var(--primary)" />{t('lang.label')}</h3><LanguageSwitcher /></div>
            <p className="small muted" style={{ marginTop: 6 }}>{t('cand.settings.languageHint')}</p>
          </div>
          <div className="card">
            <h3>{t('cand.fsp.fspId')}</h3>
            <p className="small muted" style={{ marginTop: 6 }}>{p.data.fsp_id
              ? <>{t('cand.settings.fspLinked')} <b className="mono">{p.data.fsp_id}</b></> : t('cand.settings.fspNotLinked')}</p>
            <Link className="btn secondary sm" style={{ marginTop: 12 }} to="/candidate/fsp"><Link2 size={14} />{t('cand.settings.manage')}</Link>
          </div>
          <div className="card"><h3>{t('cand.settings.account')}</h3><p className="small muted" style={{ marginTop: 6 }}>{p.data.email}</p></div>
        </div>
      </div>
    </div>
  )
}
