import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ProtectedRoute() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/dashboard/login" replace />
  return <Outlet />
}
