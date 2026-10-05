import { dashboard } from './candidate/dashboard'
import { fsp } from './candidate/fsp'
import { invitations } from './candidate/invitations'
import { jobs } from './candidate/jobs'
import { misc } from './candidate/misc'
import { profile } from './candidate/profile'

export const candidate = { ...dashboard, ...profile, ...fsp, ...invitations, ...jobs, ...misc } as const
