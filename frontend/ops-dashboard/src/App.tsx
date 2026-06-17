import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LoginPage from './routes/LoginPage'
import OrdersPage from './routes/OrdersPage'
import KitchenPage from './routes/KitchenPage'
import MenuAdminPage from './routes/MenuAdminPage'
import TablesPage from './routes/TablesPage'
import TeamPage from './routes/TeamPage'
import SettingsPage from './routes/SettingsPage'

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
          {
            element: <DashboardLayout />,
            children: [
              { index: true, element: <Navigate to="orders" replace /> },
              { path: 'orders', element: <OrdersPage /> },
              { path: 'kitchen', element: <KitchenPage /> },
              { path: 'menu', element: <MenuAdminPage /> },
              { path: 'tables', element: <TablesPage /> },
              { path: 'team', element: <TeamPage /> },
              { path: 'settings', element: <SettingsPage /> },
              { path: '*', element: <Navigate to="orders" replace /> },
            ],
          },
        ],
      },
      { path: '*', element: <Navigate to="/dashboard/orders" replace /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
