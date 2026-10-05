import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { useApi } from '../api/hooks'
import type { ReferenceOut } from '../api/types'

interface RefValue {
  ref: ReferenceOut | null
  specName: (id?: string | null) => string
  gradeName: (id?: string | null) => string
  skillName: (slug: string) => string
}

const RefContext = createContext<RefValue | null>(null)

/** Reference data (specializations, grades, skills, weight presets) loaded once from the API. */
export function ReferenceProvider({ children }: { children: ReactNode }) {
  const { data } = useApi<ReferenceOut>('/reference')
  const value = useMemo<RefValue>(() => {
    const specs = new Map(data?.specializations.map((s) => [s.id, s.name]))
    const grades = new Map(data?.grades.map((g) => [g.id, g.name]))
    const skills = new Map(data?.skills.map((s) => [s.slug, s.name]))
    return {
      ref: data,
      specName: (id) => (id ? specs.get(id) ?? id : '—'),
      gradeName: (id) => (id ? grades.get(id) ?? id : '—'),
      skillName: (slug) => skills.get(slug) ?? slug,
    }
  }, [data])
  return <RefContext.Provider value={value}>{children}</RefContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useReference(): RefValue {
  const ctx = useContext(RefContext)
  if (!ctx) throw new Error('useReference outside ReferenceProvider')
  return ctx
}
