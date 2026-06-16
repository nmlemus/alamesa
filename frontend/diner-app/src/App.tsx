import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Root from './routes/Root'
import QRLanding from './routes/QRLanding'
import Registration from './routes/Registration'
import MenuPage from './routes/MenuPage'

const router = createBrowserRouter([
  {
    path: '/:slug/mesa/:tableNumber',
    element: <Root />,
    children: [
      { index: true, element: <QRLanding /> },
      { path: 'registro', element: <Registration /> },
      { path: 'menu', element: <MenuPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
