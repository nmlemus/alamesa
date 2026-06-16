import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './routes/LoginPage'
import OrdersPage from './routes/OrdersPage'

function AuthLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  )
}

const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: '/dashboard/login', element: <LoginPage /> },
      {
        path: '/dashboard',
        element: <ProtectedRoute />,
        children: [
          { index: true, element: <Navigate to="orders" replace /> },
          { path: 'orders', element: <OrdersPage /> },
          { path: '*', element: <Navigate to="orders" replace /> },
        ],
      },
      { path: '*', element: <Navigate to="/dashboard/orders" replace /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
