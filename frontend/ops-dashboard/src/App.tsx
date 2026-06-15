import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import DashboardRoot from './routes/DashboardRoot'
import OrdersPage from './routes/OrdersPage'

const router = createBrowserRouter([
  {
    path: '/dashboard',
    element: <DashboardRoot />,
    children: [
      { index: true, element: <Navigate to="orders" replace /> },
      { path: 'orders', element: <OrdersPage /> },
      { path: '*', element: <Navigate to="orders" replace /> },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/dashboard/orders" replace />,
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
