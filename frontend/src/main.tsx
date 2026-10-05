import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './components/ui'
import { ReferenceProvider } from './lib/reference'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <ReferenceProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ReferenceProvider>
    </AuthProvider>
  </StrictMode>,
)
