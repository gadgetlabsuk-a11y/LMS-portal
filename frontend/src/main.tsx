import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/globals.css'

// CRITICAL: BASE_URL is '/lms/' (with trailing slash from vite base).
// BrowserRouter basename must NOT have trailing slash — React Router convention.
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') // '/lms'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
