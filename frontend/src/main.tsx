import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { ToastProvider } from '@/context/ToastContext'
import App from './App'
import './styles/globals.css'

// CRITICAL: BASE_URL is '/lms/' (trailing slash from vite base: '/lms/').
// BrowserRouter basename must NOT have trailing slash — React Router convention.
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') // '/lms'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
