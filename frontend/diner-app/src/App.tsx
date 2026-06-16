import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Root from './routes/Root'
import MenuPage from './routes/MenuPage'

const router = createBrowserRouter([
  {
    path: '/:slug/mesa/:tableNumber',
    element: <Root />,
    children: [
      { path: 'menu', element: <MenuPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
