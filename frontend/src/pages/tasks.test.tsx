import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { GradeStatusLine } from '../components/GradeStatus'
import { DeclaredGradeBadge, MoreCategories } from '../components/ui'
import { ReferenceProvider } from '../lib/reference'
import { mockFetch, renderApp } from '../test/utils'
import CandidateTasks from './candidate/Tasks'
import EmployerTasks from './employer/Tasks'

const company = { id: 1, name: 'Технологии Будущего' }
const task = (over: Record<string, unknown> = {}) => ({
  id: 5, title: 'Пропускная способность', description: '40 мс, 8 воркеров', mode: 'solve', audience: 'targeted',
  answer_kind: 'number', specialization_id: 'backend', specialization_name: 'Backend', grade_id: null, grade_name: null,
  competency_id: 'be_arch', competency_name: 'Architecture', requirement_title: 'Python Backend Developer',
  time_limit_days: 7, is_active: true, created_at: '2026-10-01T10:00:00', company, ...over,
})
const tasksView = {
  offered: [{
    assignment_id: 9, source: 'system', offered_at: '2026-10-07T10:00:00', due_at: '2026-10-14T10:00:00', task: task(),
    reasons: ['Fits your category Backend · Middle', 'The employer is considering you for “Python Backend Developer”'],
  }],
  challenges: [],
  history: [{
    id: 3, task_id: 2, task_title: 'Идемпотентность', mode: 'approach', company, answer: 'Ключ идемпотентности…',
    status: 'reviewed', correct: null, rubric: { correctness: 2, completeness: 1, reasoning: 1 }, score: 67,
    reviewer_comment: 'Не хватает TTL', created_at: '2026-10-01T10:00:00', reviewed_at: '2026-10-02T10:00:00',
  }],
  next_offer_at: null, interval_days: 7, verified: true,
}
const reference = {
  specializations: [{ id: 'backend', name: 'Backend', description: '', competencies: [{ id: 'be_api', name: 'API', weight: 0.2 }] }],
  grades: [{ id: 'junior', name: 'Junior', description: '', rank: 1 }, { id: 'middle', name: 'Middle', description: '', rank: 2 }],
  skills: [], weight_presets: [], component_labels: {},
}

describe('candidate tasks', () => {
  it('explain why a task is offered and check a numeric answer at once', async () => {
    const { calls } = mockFetch({
      'GET /api/candidate/tasks': tasksView,
      'POST /api/candidate/tasks/5/submit': { ...tasksView.history[0], id: 4, task_id: 5, mode: 'solve', correct: true, score: 100 },
    })
    renderApp(<CandidateTasks />, { lang: 'en' })
    expect(await screen.findByText('Offered to you')).toBeInTheDocument()
    expect(screen.getByText('The employer is considering you for “Python Backend Developer”')).toBeInTheDocument()
    expect(screen.getByText('A new addressed task at most once every 7 days.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Solve' }))
    await userEvent.type(screen.getByLabelText('Answer (a number)'), '200')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('The answer was checked automatically: Correct')).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ answer: '200' })
  })

  it('show the employer rubric and comment in the history (Russian)', async () => {
    mockFetch({ 'GET /api/candidate/tasks': tasksView })
    renderApp(<CandidateTasks />, { lang: 'ru' })
    expect(await screen.findByText('Оценка 67%')).toBeInTheDocument()
    expect(screen.getByText('Полнота: 1/2')).toBeInTheDocument()
    expect(screen.getByText('Комментарий: Не хватает TTL')).toBeInTheDocument()
  })

  it('decline an offer', async () => {
    const { calls } = mockFetch({
      'GET /api/candidate/tasks': tasksView,
      'POST /api/candidate/tasks/offers/9/decline': { message: 'Task declined' },
    })
    renderApp(<CandidateTasks />, { lang: 'en' })
    await userEvent.click(await screen.findByRole('button', { name: 'Decline' }))
    expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/candidate/tasks/offers/9/decline'))).toBe(true)
  })
})

describe('employer tasks', () => {
  it('review an approach with the rubric; the pre-score shows covered and missed key points', async () => {
    const employerTask = { ...task({ id: 7, mode: 'approach', answer_kind: null, title: 'Идемпотентность' }), job_id: null,
      answer_spec: null, key_points: ['Ключ', 'TTL'], max_offers: 20,
      stats: { offered: 3, submitted: 1, pending_review: 1, avg_score: null } }
    const { calls } = mockFetch({
      'GET /api/reference': reference,
      'GET /api/employer/tasks': [employerTask],
      'GET /api/employer/requirements': [],
      'GET /api/employer/tasks/7/submissions': [{
        id: 11, answer: 'Ключ в заголовке', status: 'pending_review', auto_score: 0.5,
        auto_detail: { matched: ['Ключ'], missed: ['TTL'] }, rubric: null, score: null, rating: null,
        reviewer_comment: null, created_at: '2026-10-07T10:00:00', candidate_id: 1, candidate_name: 'Алексей Демидов',
        category_label: 'Backend · Middle',
      }],
      'POST /api/employer/submissions/11/review': { message: 'Rating saved' },
    })
    renderApp(<ReferenceProvider><EmployerTasks /></ReferenceProvider>, { lang: 'en' })
    expect(await screen.findByText('Offered 3 · solutions 1 · awaiting review 1')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Solutions' }))
    expect(await screen.findByText('Pre-score: 50%')).toBeInTheDocument()
    expect(screen.getByText('TTL')).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('group', { name: 'Correctness' })).getByRole('button', { name: '2' }))
    await userEvent.click(within(screen.getByRole('group', { name: 'Reasoning' })).getByRole('button', { name: '0' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save score' }))
    expect(await screen.findByText('Score saved')).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      rubric: { correctness: 2, completeness: 1, reasoning: 0 }, comment: null })
  })
})

describe('categories and the declared grade', () => {
  const cat = (label: string, primary: boolean) => ({
    label, specialization_id: label.startsWith('DevOps') ? 'devops' : 'backend', specialization_name: '', grade_id: 'junior',
    grade_name: 'Junior', verified_at: null, scaled_score: 60, confidence: 0.9, theta: 0, locked_until: null,
    upgrade_eligible: false, is_primary: primary,
  })

  it('list the other categories besides the shown one', () => {
    mockFetch()
    const all = [cat('Backend · Middle', true), cat('DevOps · Junior', false)]
    renderApp(<MoreCategories categories={all} shown={all[0]} />, { lang: 'en' })
    expect(screen.getByText('DevOps · Junior')).toBeInTheDocument()
    expect(screen.queryByText('Backend · Middle')).not.toBeInTheDocument()
  })

  it('mark an unconfirmed declared grade', () => {
    mockFetch()
    renderApp(<DeclaredGradeBadge declared={{ label: 'Backend · Senior', specialization_id: 'backend', grade_id: 'senior', confirmed: false }} />, { lang: 'en' })
    expect(screen.getByText('Backend · Senior — grade not confirmed')).toBeInTheDocument()
  })

  it.each([
    ['not_tested', 'Middle declared — grade not confirmed: no test taken yet'],
    ['not_confirmed', 'Middle declared — grade not confirmed: the test was not passed'],
    ['confirmed_lower', 'Middle declared, the test confirmed Junior'],
  ] as const)('describe the grade status %s', async (status, text) => {
    mockFetch({ 'GET /api/reference': reference })
    renderApp(<ReferenceProvider><GradeStatusLine status={{ status, specialization_id: 'backend', declared_grade_id: 'middle',
      confirmed_grade_id: status === 'confirmed_lower' ? 'junior' : null }} /></ReferenceProvider>, { lang: 'en' })
    expect(await screen.findByText(text)).toBeInTheDocument()
  })
})
