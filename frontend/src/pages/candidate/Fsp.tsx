import { Info, Link2, RefreshCcw, Trophy, Unlink } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { FSPLinkOut, FSPOut } from '../../api/types'
import { AchievementList, Empty, ErrorBox, Loading, ScoreRing, useToast } from '../../components/ui'
import { date, plural } from '../../lib/format'

export default function FspPage() {
  const { data, error, loading, setData, reload } = useApi<FSPOut>('/candidate/fsp')
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
        toast('ФСП ID привязан, достижения загружены')
      } else setPending(r)
    })
  }

  const confirm = (e: FormEvent) => {
    e.preventDefault()
    void run(async () => {
      setData(await api<FSPOut>('/candidate/fsp/confirm', { method: 'POST', body: { code } }))
      setPending(null)
      toast('Привязка подтверждена')
    })
  }

  const p = data.profile
  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>Достижения ФСП</h1><p className="sub">Результаты соревнований Федерации спортивного программирования — объективное подтверждение практических навыков.
          Они автоматически подтягиваются из реестра ФСП и усиливают ваш профиль в подборках.</p></div>
      </div>
      <ErrorBox error={err} />

      {data.linked && p ? (
        <div className="split">
          <div className="card">
            <div className="card-title"><h3><Trophy size={18} color="var(--accent)" />{p.achievements.length} {plural(p.achievements.length, 'достижение', 'достижения', 'достижений')} в реестре</h3>
              <div className="row">
                <button className="btn sm ghost" disabled={busy} onClick={() => run(async () => { setData(await api<FSPOut>('/candidate/fsp/sync', { method: 'POST' })); toast('Данные обновлены') })}><RefreshCcw size={14} />Синхронизировать</button>
              </div></div>
            {p.achievements.length ? <AchievementList items={p.achievements} /> : <Empty title="В реестре нет достижений" text="Участие появится здесь автоматически после соревнований." />}
          </div>
          <div className="stack-lg sticky">
            <div className="card stack">
              <div className="row between"><h3>Участник ФСП</h3><span className="badge success">привязан</span></div>
              <dl className="kv small" style={{ gridTemplateColumns: '110px 1fr' }}>
                <dt>ФСП ID</dt><dd className="mono">{p.fsp_id}</dd>
                <dt>ФИО в реестре</dt><dd>{p.full_name}</dd>
                <dt>Регион</dt><dd>{p.region ?? '—'}</dd>
                <dt>Разряд</dt><dd>{p.sport_rank ?? '—'}</dd>
                <dt>Обновлено</dt><dd>{date(p.synced_at)}</dd>
                <dt>Источник</dt><dd>{p.source === 'mock' ? 'Мок-реестр ФСП' : 'API ФСП'}</dd>
              </dl>
              <button className="btn danger sm" disabled={busy} onClick={() => run(async () => { setData(await api<FSPOut>('/candidate/fsp/link', { method: 'DELETE' })) })}><Unlink size={14} />Отвязать</button>
            </div>
            <div className="card stack" style={{ alignItems: 'center' }}>
              <ScoreRing value={Math.round(data.summary.strength * 100)} size={96} label="сила" color="var(--accent)" />
              <p className="small muted center">Сила сигнала ФСП для вашей специализации: учитывает уровень соревнований, место, давность и роль в команде.</p>
              {data.summary.best_text && <p className="small center"><b>Лучший результат:</b> {data.summary.best_text}</p>}
            </div>
          </div>
        </div>
      ) : (
        <div className="split">
          <div className="card">
            <Empty icon={<Trophy size={26} />} title="История ФСП не найдена"
              text={<>Это нормально: отсутствие достижений <b>не снижает</b> ваш рейтинг — в подборе используется нейтральная оценка.
                Если вы участвовали в соревнованиях ФСП, привяжите ФСП ID.</>} />
          </div>
          <div className="card stack-lg sticky">
            <h3><Link2 size={18} style={{ verticalAlign: -3 }} /> Привязать ФСП ID</h3>
            {!pending ? (
              <form className="stack" onSubmit={link}>
                <div className="field"><label htmlFor="fsp-f1">ФСП ID</label><input id="fsp-f1" className="input mono" placeholder="FSP-200001" value={fspId} onChange={(e) => setFspId(e.target.value)} required /></div>
                <button className="btn" disabled={busy}>Найти в реестре</button>
                <p className="tiny muted">Если e-mail в реестре ФСП совпадает с вашим — привязка мгновенная. Иначе отправим код на почту из реестра (в будущем — вход через ФСП ID на Keycloak).</p>
                <div className="alert info small"><Info size={16} /><span>Для демо: ФСП ID <b className="mono">FSP-200001</b>, <b className="mono">FSP-200002</b>, <b className="mono">FSP-200003</b> свободны.</span></div>
              </form>
            ) : (
              <form className="stack" onSubmit={confirm}>
                <p className="small">Код подтверждения отправлен на {pending.masked_email ?? 'почту из реестра ФСП'}.</p>
                {pending.dev_code && <div className="alert violet small">Демо-режим: код <b className="mono">{pending.dev_code}</b>
                  <button type="button" className="btn sm secondary" onClick={() => setCode(pending.dev_code!)}>Подставить</button></div>}
                <input className="input code-input" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />
                <button className="btn" disabled={busy || code.length !== 6}>Подтвердить привязку</button>
                <button type="button" className="btn ghost" onClick={() => setPending(null)}>Отмена</button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
