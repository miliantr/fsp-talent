import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { ExperienceItem } from '../api/types'
import { createFormatters } from '../i18n/core'
import { toMonth } from '../lib/format'
import { mockFetch, renderApp } from '../test/utils'
import { ExperienceEditor, ExperienceList } from './Experience'

const NOW = new Date(2026, 9, 8)

describe('work periods', () => {
  it('format the period and its length in both languages', () => {
    const ru = createFormatters('ru')
    const en = createFormatters('en')
    expect(ru.tenure('2023-02', '2024-09')).toBe('1 год 8 мес.')
    expect(en.tenure('2023-02', '2024-09')).toBe('1 year 8 mo')
    expect(en.tenure('2025-10', null, NOW)).toBe('1 year 1 mo')
    expect(en.tenure('2019', '2021')).toBe('3 years')  // bare years: January to December
    expect(en.period('2023', null)).toBe('2023 — present')
    expect(ru.period('2023', '2024')).toBe('2023 — 2024')
  })

  it('normalise a parsed year for a month input', () => {
    expect(toMonth('2023')).toBe('2023-01')
    expect(toMonth('2023-04')).toBe('2023-04')
    expect(toMonth(null)).toBe('')
  })
})

describe('work experience components', () => {
  const job: ExperienceItem = { company: 'ФинПоток', position: 'Backend developer', period_from: '2023-02',
    period_to: null, description: 'Payments API' }

  it('list the places of work with the period', () => {
    mockFetch()
    renderApp(<ExperienceList items={[job]} />, { lang: 'en' })
    expect(screen.getByText('Backend developer')).toBeInTheDocument()
    expect(screen.getByText('ФинПоток')).toBeInTheDocument()
    expect(screen.getByText(/present/)).toBeInTheDocument()
    expect(screen.getByText('Payments API')).toBeInTheDocument()
  })

  it('say when nothing is listed', () => {
    mockFetch()
    renderApp(<ExperienceList items={[]} />, { lang: 'ru' })
    expect(screen.getByText('Места работы не указаны')).toBeInTheDocument()
  })

  it('edit the list: add, fill, finish the current job, remove', async () => {
    mockFetch()
    const changes = vi.fn()
    function Host() {
      const [v, setV] = useState<ExperienceItem[]>([job])
      return <ExperienceEditor value={v} onChange={(x) => { changes(x); setV(x) }} />
    }
    renderApp(<Host />, { lang: 'en' })
    expect(screen.getByLabelText('End')).toBeDisabled()  // a current job has no end
    await userEvent.click(screen.getByLabelText('I work here now'))
    expect(changes.mock.lastCall?.[0][0].period_to).toBe('2023-02')
    await userEvent.click(screen.getByRole('button', { name: 'Add a place of work' }))
    expect(screen.getAllByLabelText('Company')).toHaveLength(2)
    fireEvent.change(screen.getAllByLabelText('Company')[1], { target: { value: 'Acme' } })
    expect(changes.mock.lastCall?.[0][1].company).toBe('Acme')
    await userEvent.click(screen.getAllByRole('button', { name: 'Remove the place of work' })[0])
    expect(changes.mock.lastCall?.[0].map((j: ExperienceItem) => j.company)).toEqual(['Acme'])
  })
})
