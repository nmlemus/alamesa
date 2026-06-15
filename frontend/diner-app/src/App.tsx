import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Root from './routes/Root'

const router = createBrowserRouter([
  {
    path: '/:slug/mesa/:tableNumber/*',
    element: <Root />,
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
