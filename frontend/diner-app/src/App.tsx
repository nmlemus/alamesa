import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Root from './routes/Root'
import QRLanding from './routes/QRLanding'
import Registration from './routes/Registration'
import MenuPage from './routes/MenuPage'
import CartReview from './routes/CartReview'
import OrderSubmitted from './routes/OrderSubmitted'
import OrderTracker from './routes/OrderTracker'

const router = createBrowserRouter([
  {
    path: '/:slug/mesa/:tableNumber',
    element: <Root />,
    children: [
      { index: true, element: <QRLanding /> },
      { path: 'registro', element: <Registration /> },
      { path: 'menu', element: <MenuPage /> },
      { path: 'carrito', element: <CartReview /> },
      { path: 'pedido-enviado/:orderId', element: <OrderSubmitted /> },
      { path: 'seguimiento/:orderId', element: <OrderTracker /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
