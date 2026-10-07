import { auth } from './auth'
import { candidate } from './candidate'
import { common } from './common'
import { employer } from './employer'
import { landing } from './landing'
import { tasks } from './tasks'
import { testing } from './testing'

/** The reference dictionary: every other language must define exactly these keys. */
export const ru = { ...common, ...landing, ...auth, ...candidate, ...testing, ...employer, ...tasks } as const
