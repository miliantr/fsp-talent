import { AlertCircle, ShieldCheck } from 'lucide-react'
import type { GradeStatus } from '../api/types'
import { useI18n } from '../i18n/context'
import { useReference } from '../lib/reference'

/** The self-declared grade against the grade confirmed by the test. */
export function GradeStatusLine({ status, light }: { status: GradeStatus; light?: boolean }) {
  const { t } = useI18n()
  const { gradeName } = useReference()
  if (status.status === 'no_claim') return null
  const grade = gradeName(status.declared_grade_id)
  const text =
    status.status === 'confirmed' ? t('grade.status.confirmed', { grade })
      : status.status === 'confirmed_lower' ? t('grade.status.confirmed_lower', { declared: grade, confirmed: gradeName(status.confirmed_grade_id) })
        : status.status === 'not_confirmed' ? t('grade.status.not_confirmed', { grade })
          : t('grade.status.not_tested', { grade })
  const ok = status.status === 'confirmed'
  const tone = light ? 'light' : ok ? 'success' : 'warning'
  return (
    <span className={`badge ${tone}`} title={t('grade.status.hint')} style={{ whiteSpace: 'normal' }}>
      {ok ? <ShieldCheck size={13} /> : <AlertCircle size={13} />}{text}
    </span>
  )
}
