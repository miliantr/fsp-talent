import { Info, Link2, RefreshCcw, Trophy, Unlink } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { FSPLinkOut, FSPOut } from '../../api/types'
import { AchievementList, Empty, ErrorBox, Loading, ScoreRing, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'

/** Sport ranks come from the registry in Russian; known ones are translated, others shown as is. */
const RANK_ID: Record<string, string> = { 'МС': 'ms', 'КМС': 'cms', 'I разряд': 'r1', 'II разряд': 'r2', 'III разряд': 'r3' }

export default function FspPage() {
  const { data, error, loading, setData, reload } = useApi<FSPOut>('/candidate/fsp')
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [fspId, setFspId] = useState('')
  const [pending, setPending] = useState<FSPLinkOut | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setErr(null)
    try { await fn() } catch (e) { setErr(errorMessage(e)) } finally { setBusy(false) }
  }

  const link = (e: FormEvent) => {
    e.preventDefault()
    void run(async () => {
      const r = await api<FSPLinkOut>('/candidate/fsp/link', { method: 'POST', body: { fsp_id: fspId } })
      if (r.status === 'linked') {
        await reload()
        toast(t('cand.fsp.linked'))
      } else setPending(r)
    })
  }

  const confirm = (e: FormEvent) => {
    e.preventDefault()
    void run(async () => {
      setData(await api<FSPOut>('/candidate/fsp/confirm', { method: 'POST', body: { code } }))
      setPending(null)
      toast(t('cand.fsp.confirmed'))
    })
  }

  const rank = (r: string | null | undefined) => (r ? (RANK_ID[r] ? t(`cand.fsp.rank.${RANK_ID[r]}` as MessageKey) : r) : '—')
  const p = data.profile
  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{t('nav.fsp')}</h1><p className="sub">{t('cand.fsp.sub')}</p></div>
      </div>
      <ErrorBox error={err} />

      {data.linked && p ? (
        <div className="split">
          <div className="card">
            <div className="card-title"><h3><Trophy size={18} color="var(--accent)" />{t('cand.fsp.inRegistry', { n: p.achievements.length })}</h3>
              <div className="row">
                <button className="btn sm ghost" disabled={busy} onClick={() => run(async () => {
                  setData(await api<FSPOut>('/candidate/fsp/sync', { method: 'POST' }))
                  toast(t('cand.fsp.synced'))
                })}><RefreshCcw size={14} />{t('cand.fsp.sync')}</button>
              </div></div>
            {p.achievements.length ? <AchievementList items={p.achievements} />
              : <Empty title={t('cand.fsp.emptyTitle')} text={t('cand.fsp.emptyText')} />}
          </div>
          <div className="stack-lg sticky">
            <div className="card stack">
              <div className="row between"><h3>{t('cand.fsp.participant')}</h3><span className="badge success">{t('cand.fsp.linkedBadge')}</span></div>
              <dl className="kv small" style={{ gridTemplateColumns: '110px 1fr' }}>
                <dt>{t('cand.fsp.fspId')}</dt><dd className="mono">{p.fsp_id}</dd>
                <dt>{t('cand.fsp.fullName')}</dt><dd>{p.full_name}</dd>
                <dt>{t('cand.fsp.region')}</dt><dd>{p.region ?? '—'}</dd>
                <dt>{t('cand.fsp.rank')}</dt><dd>{rank(p.sport_rank)}</dd>
                <dt>{t('cand.fsp.updated')}</dt><dd>{fmt.date(p.synced_at)}</dd>
                <dt>{t('cand.fsp.source')}</dt><dd>{p.source === 'mock' ? t('cand.fsp.sourceMock') : t('cand.fsp.sourceApi')}</dd>
              </dl>
              <button className="btn danger sm" disabled={busy} onClick={() => run(async () => {
                setData(await api<FSPOut>('/candidate/fsp/link', { method: 'DELETE' }))
              })}><Unlink size={14} />{t('cand.fsp.unlink')}</button>
            </div>
            <div className="card stack" style={{ alignItems: 'center' }}>
              <ScoreRing value={Math.round(data.summary.strength * 100)} size={96} label={t('cand.fsp.strength')} color="var(--accent)" />
              <p className="small muted center">{t('cand.fsp.strengthHint')}</p>
              {data.summary.best_text && <p className="small center"><b>{t('cand.fsp.best')}</b> {data.summary.best_text}</p>}
            </div>
          </div>
        </div>
      ) : (
        <div className="split">
          <div className="card">
            <Empty icon={<Trophy size={26} />} title={t('cand.fsp.noHistoryTitle')}
              text={<>{t('cand.fsp.noHistory1')} <b>{t('cand.fsp.noHistoryEmph')}</b> {t('cand.fsp.noHistory2')}</>} />
          </div>
          <div className="card stack-lg sticky">
            <h3><Link2 size={18} style={{ verticalAlign: -3 }} /> {t('cand.fsp.linkTitle')}</h3>
            {!pending ? (
              <form className="stack" onSubmit={link}>
                <div className="field"><label htmlFor="fsp-f1">{t('cand.fsp.fspId')}</label>
                  <input id="fsp-f1" className="input mono" placeholder="FSP-200001" value={fspId} onChange={(e) => setFspId(e.target.value)} required /></div>
                <button className="btn" disabled={busy}>{t('cand.fsp.find')}</button>
                <p className="tiny muted">{t('cand.fsp.linkHint')}</p>
                <div className="alert info small"><Info size={16} /><span>{t('cand.fsp.demoIds')} <b className="mono">FSP-200001</b>,
                  {' '}<b className="mono">FSP-200002</b>, <b className="mono">FSP-200003</b> {t('cand.fsp.demoIdsFree')}</span></div>
              </form>
            ) : (
              <form className="stack" onSubmit={confirm}>
                <p className="small">{t('cand.fsp.codeSent', { email: pending.masked_email ?? t('cand.fsp.registryEmail') })}</p>
                {pending.dev_code && <div className="alert violet small">{t('cand.fsp.demoCode')} <b className="mono">{pending.dev_code}</b>
                  <button type="button" className="btn sm secondary" onClick={() => setCode(pending.dev_code!)}>{t('auth.verify.fill')}</button></div>}
                <input className="input code-input" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  aria-label={t('auth.verify.code')} />
                <button className="btn" disabled={busy || code.length !== 6}>{t('cand.fsp.confirm')}</button>
                <button type="button" className="btn ghost" onClick={() => setPending(null)}>{t('common.cancel')}</button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
