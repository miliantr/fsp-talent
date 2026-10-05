import { ArrowRight, Award, CheckCircle2, CircleAlert, RotateCcw, TrendingUp } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { TestResult } from '../../api/types'
import { CompetencyBars, ErrorBox, Loading, OutcomeBadge, ScoreRing, ScoreScale } from '../../components/ui'
import { date } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function TestResultPage() {
  const { attemptId } = useParams()
  const { specName, gradeName } = useReference()
  const { data: r, error, loading } = useApi<TestResult>(`/candidate/testing/results/${attemptId}`)
  if (loading && !r) return <Loading label="Считаем результат…" />
  if (error) return <ErrorBox error={error} />
  if (!r) return null
  const ok = r.passed
  const icon = ok ? <CheckCircle2 size={34} /> : <CircleAlert size={34} />

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>Результат теста</h1><p className="sub">{specName(r.specialization_id)} · цель {gradeName(r.target_grade)} · {date(r.created_at)} · отвечено {r.answered} из {r.total}</p></div>
        <OutcomeBadge outcome={r.outcome} />
      </div>

      <div className="card" style={{ padding: 28, background: ok ? 'var(--brand-gradient)' : '#fff', color: ok ? '#fff' : 'var(--text)', border: ok ? 'none' : undefined }}>
        <div className="row between wrap" style={{ gap: 24 }}>
          <div className="stack" style={{ gap: 10, maxWidth: 620 }}>
            <div className="row" style={{ color: ok ? '#fff' : 'var(--warning)' }}>{icon}<h2 style={{ fontSize: 24 }}>
              {ok ? 'Категория подтверждена' : r.outcome === 'needs_confirmation' ? 'Нужна подтверждающая форма' : 'Грейд пока не подтверждён'}</h2></div>
            {r.category_label && <span className="category lg" style={{ background: 'rgba(255,255,255,.18)', width: 'fit-content' }}><span className="ok"><Award size={18} /></span>{r.category_label}</span>}
            <p style={{ opacity: ok ? 0.9 : 1 }}>{r.recommendation}</p>
            {r.grade_changed && <span className="badge" style={{ background: 'rgba(255,255,255,.18)', color: 'inherit', width: 'fit-content' }}>Грейд в профиле обновлён</span>}
          </div>
          <div className="row" style={{ gap: 24 }}>
            <div className="center"><ScoreRing value={r.scaled_score} size={110} label="из 100" color={ok ? '#fff' : undefined} /><div className="tiny" style={{ marginTop: 6, opacity: 0.8 }}>Шкальный балл</div></div>
            <div className="center"><ScoreRing value={Math.round(r.confidence * 100)} size={110} color={ok ? '#f0b8ff' : undefined} /><div className="tiny" style={{ marginTop: 6, opacity: 0.8 }}>Уверенность решения</div></div>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Положение на шкале грейдов</h3>
          <div style={{ marginTop: 12 }}><ScoreScale score={r.scaled_score} /></div>
          <div className="divider" />
          <dl className="kv small">
            <dt>Способность θ (IRT)</dt><dd>{r.theta.toFixed(2)} ± {r.theta_se.toFixed(2)}</dd>
            <dt>Доля верных ответов</dt><dd>{r.raw_percent}%</dd>
            <dt>Почему балл ≠ % верных</dt><dd style={{ fontWeight: 500 }}>Шкальный балл учитывает сложность именно ваших заданий, поэтому сопоставим между разными вариантами теста.</dd>
          </dl>
        </div>
        <div className="card"><h3>Компетенции</h3><div style={{ marginTop: 14 }}><CompetencyBars items={r.competencies} /></div></div>
      </div>

      <div className="row wrap">
        {r.upgrade_eligible && <Link to="/candidate/testing" className="btn"><TrendingUp size={16} />Пройти тест на грейд выше</Link>}
        {!ok && <Link to="/candidate/testing" className="btn"><RotateCcw size={16} />{r.outcome === 'needs_confirmation' ? 'Пройти подтверждающую форму' : 'Выбрать тест на грейд ниже'}</Link>}
        <Link to="/candidate" className="btn ghost">В кабинет <ArrowRight size={16} /></Link>
        {ok && <Link to="/candidate/settings" className="btn secondary">Настроить видимость профиля</Link>}
      </div>
    </div>
  )
}
