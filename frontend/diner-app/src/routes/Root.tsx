import { Outlet } from 'react-router-dom'
import { CartProvider } from '../context/CartContext'

export default function Root() {
  return (
    <CartProvider>
      <Outlet />
    </CartProvider>
  )
}
