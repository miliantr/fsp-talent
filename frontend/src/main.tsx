import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './components/ui'
import { I18nProvider } from './i18n/context'
import { ReferenceProvider } from './lib/reference'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <AuthProvider>
        <ReferenceProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </ReferenceProvider>
      </AuthProvider>
    </I18nProvider>
  </StrictMode>,
)
