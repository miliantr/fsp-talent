import type { Msg } from '../../../core'
import type { jobs as ru } from '../../ru/candidate/jobs'

export const jobs: { readonly [K in keyof typeof ru]: Msg } = {
  'cand.jobs.sub': 'An additional scenario: while there are no invitations, you can take the initiative. Vacancies are sorted by how well they match your verified profile.',
  'cand.jobs.tabJobs': 'Vacancies',
  'cand.jobs.tabMine': 'My applications',
  'cand.jobs.search': 'Position, company, technology',
  'cand.jobs.allSpecs': 'All specializations',
  'cand.jobs.emptyTitle': 'No vacancies found',
  'cand.jobs.emptyText': 'Try changing the query or the filter.',
  'cand.jobs.apply': 'Apply',
  'cand.jobs.applied': 'Application sent — the employer will see your contacts',
  'cand.jobs.mineEmptyTitle': 'No applications yet',
  'cand.jobs.mineEmptyText': 'Apply to a vacancy — its status will show up here.',
  'cand.jobs.col.vacancy': 'Vacancy',
  'cand.jobs.col.company': 'Company',
  'cand.jobs.col.salary': 'Salary',
  'cand.jobs.col.match': 'Match',
  'cand.jobs.col.status': 'Status',
  'cand.jobs.col.date': 'Date',
  'cand.jobs.modalTitle': 'Apply: {title}',
  'cand.jobs.contactsNotice': 'By applying you disclose your contacts to the employer.',
  'cand.jobs.letter': 'Cover letter',
  'cand.jobs.letterPlaceholder': 'Why this vacancy interests you',
  'cand.jobs.send': 'Send application',
}
