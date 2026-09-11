import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

async function init() {
  // Activate offline demo mode when VITE_MOCK=true
  if (import.meta.env.VITE_MOCK === 'true') {
    const { setupMockInterceptors } = await import('./api/mock');
    setupMockInterceptors();
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

init();
