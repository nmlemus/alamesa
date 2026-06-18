import { Outlet } from 'react-router-dom'
import SidebarNav from './SidebarNav'

export default function DashboardLayout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-surface)' }}>
      <SidebarNav />
      <main style={{ flex: 1, overflow: 'auto', padding: 'var(--spacing-6)' }}>
        <Outlet />
      </main>
    </div>
  )
}
