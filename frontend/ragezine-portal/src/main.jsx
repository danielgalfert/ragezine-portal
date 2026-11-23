import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import RoutedApp from './components/RoutedApp.jsx'
import './styles/base.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <RoutedApp />
    </BrowserRouter>
  </StrictMode>,
)
