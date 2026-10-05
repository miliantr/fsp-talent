import type { Dictionary } from '../../core'
import { auth } from './auth'
import { candidate } from './candidate'
import { common } from './common'
import { employer } from './employer'
import { landing } from './landing'
import { testing } from './testing'

export const en: Dictionary = { ...common, ...landing, ...auth, ...candidate, ...testing, ...employer }
