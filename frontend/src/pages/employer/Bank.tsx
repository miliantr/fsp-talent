import { ChevronRight, Search, Send } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { BankOut, CandidateCard, Company } from '../../api/types'
import { InviteModal } from '../../components/InviteModal'
import { SkillSelect } from '../../components/SkillPicker'
import { Avatar, CategoryBadge, Empty, ErrorBox, FspSummary, InvitationStatusBadge, Loading, ScoreRing, useToast } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { workFormatKey } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function Bank() {
  const { ref } = useReference()
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [spec, setSpec] = useState('')
  const [grades, setGrades] = useState<string[]>([])
  const [skills, setSkills] = useState<string[]>([])
  const [hasFsp, setHasFsp] = useState('')
  const { data, error, loading, reload } = useApi<BankOut>('/employer/candidates', {
    specialization_id: spec, grades, skills, has_fsp: hasFsp || undefined,
  })
  const company = useApi<Company>('/employer/profile')
  const [invite, setInvite] = useState<CandidateCard | null>(null)

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.bank')}</h1>
        <p className="sub">{t('emp.bank.sub')} <Link to="/employer/requirements/new">{t('emp.bank.describeLink')}</Link>.</p></div></div>
      <div className="card">
        <div className="grid grid-4" style={{ alignItems: 'end' }}>
          <div className="field"><label htmlFor="bank-f1">{t('cand.profile.spec')}</label><select id="bank-f1" className="select" value={spec} onChange={(e) => setSpec(e.target.value)}>
            <option value="">{t('common.all')}</option>{ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
          <div className="field"><label>{t('emp.match.grade')}</label><div className="row wrap">
            {ref?.grades.map((g) => <button key={g.id} className={`chip selectable ${grades.includes(g.id) ? 'on' : ''}`}
              onClick={() => setGrades(grades.includes(g.id) ? grades.filter((x) => x !== g.id) : [...grades, g.id])}>{g.name}</button>)}</div></div>
          <div className="field"><label htmlFor="bank-f2">{t('nav.fsp')}</label><select id="bank-f2" className="select" value={hasFsp} onChange={(e) => setHasFsp(e.target.value)}>
            <option value="">{t('emp.match.fspAny')}</option><option value="true">{t('emp.bank.fspYes')}</option><option value="false">{t('emp.bank.fspNo')}</option></select></div>
          <div className="field"><label>{t('emp.bank.stack')}</label><SkillSelect value={skills} onChange={setSkills} specialization={spec} placeholder={t('skills.addPlaceholder')} /></div>
        </div>
      </div>
      {data && <div className="row wrap">{data.categories.map((c) => <span key={c.label} className="chip">{c.label} · {c.count}</span>)}</div>}
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} onRetry={reload} /> : !data || data.items.length === 0 ? (
        <div className="card"><Empty icon={<Search size={26} />} title={t('emp.bank.emptyTitle')} text={t('emp.bank.emptyText')} /></div>
      ) : (
        <div className="stack">
          <span className="small muted">{t('emp.bank.found', { n: data.total })}</span>
          {data.items.map((c) => (
            <div key={c.candidate_id} className="cand">
              <div className="stack" style={{ alignItems: 'center', gap: 4 }}><ScoreRing value={c.profile_strength ?? 0} size={70} label={t('cand.fsp.strength')} /></div>
              <div className="stack" style={{ gap: 8 }}>
                <div className="row"><Avatar name={c.display_name} /><div><div className="name">{c.display_name}</div>
                  <div className="small muted">{c.headline} · {fmt.years(c.experience_years)} · {c.city ?? '—'} · {t(workFormatKey(c.work_format))}{c.expected_salary ? ` · ${fmt.money(c.expected_salary)}` : ''}</div></div></div>
                <div className="row wrap"><CategoryBadge category={c.category} /><span className="badge outline">{t('emp.match.test', { score: c.category?.scaled_score ?? 0 })}</span><FspSummary fsp={c.fsp} compact /></div>
                <div className="row wrap">{c.skills.map((s) => <span key={s.slug} className={`chip ${s.verified ? 'verified' : ''}`}>{s.name}</span>)}</div>
              </div>
              <div className="actions">
                {c.invitation_status && <InvitationStatusBadge status={c.invitation_status} />}
                <Link className="btn secondary sm" to={`/employer/candidates/${c.candidate_id}`}>{t('cand.dash.profile')}<ChevronRight size={14} /></Link>
                <button className="btn sm" onClick={() => setInvite(c)}><Send size={14} />{t('emp.invite')}</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {invite && (
        <InviteModal candidateId={invite.candidate_id} candidateName={invite.display_name}
          defaultContact={[company.data?.contact_telegram, company.data?.contact_email].filter(Boolean).join(' · ')}
          onClose={() => setInvite(null)} onSent={() => { setInvite(null); toast(t('emp.invitationSent')); void reload() }} />
      )}
    </div>
  )
}
