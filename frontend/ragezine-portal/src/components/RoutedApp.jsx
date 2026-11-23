import { useLocation } from 'react-router-dom'

import App from '../App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'

export default function RoutedApp() {
  const location = useLocation()

  return (
    <ErrorBoundary key={location.key}>
      <App />
    </ErrorBoundary>
  )
}
