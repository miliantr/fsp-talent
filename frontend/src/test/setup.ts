import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import { setCurrentLang } from '../i18n/core'

afterEach(() => {
  cleanup()
  localStorage.clear()
  setCurrentLang('ru')
  document.documentElement.lang = ''
})
