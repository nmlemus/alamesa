import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

type NavItem = {
  key: string
  label: string
  path: string
  adminOnly: boolean
  icon: React.ReactElement
}

function OrdersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="M9 12h6M9 16h4" />
    </svg>
  )
}

function KitchenIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 13.87A4 4 0 0 1 7.41 6a5.11 5.11 0 0 1 1.05-1.54 5 5 0 0 1 7.08 0A5.11 5.11 0 0 1 16.59 6 4 4 0 0 1 18 13.87V21H6Z" />
      <line x1="6" y1="17" x2="18" y2="17" />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  )
}

function TablesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18M9 21V9" />
    </svg>
  )
}

function TeamIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function ChevronLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

const NAV_ITEMS: NavItem[] = [
  { key: 'orders', label: 'Live Orders', path: '/dashboard/orders', adminOnly: false, icon: <OrdersIcon /> },
  { key: 'kitchen', label: 'Kitchen View', path: '/dashboard/kitchen', adminOnly: false, icon: <KitchenIcon /> },
  { key: 'menu', label: 'Menu', path: '/dashboard/menu', adminOnly: true, icon: <MenuIcon /> },
  { key: 'tables', label: 'Tables', path: '/dashboard/tables', adminOnly: true, icon: <TablesIcon /> },
  { key: 'team', label: 'Team', path: '/dashboard/team', adminOnly: true, icon: <TeamIcon /> },
  { key: 'settings', label: 'Settings', path: '/dashboard/settings', adminOnly: true, icon: <SettingsIcon /> },
]

const SIDEBAR_EXPANDED = 240
const SIDEBAR_COLLAPSED = 64
const TABLET_BREAKPOINT = 767

function isTablet() {
  return typeof window !== 'undefined' && window.matchMedia(`(max-width: ${TABLET_BREAKPOINT}px)`).matches
}

export default function SidebarNav() {
  const { role } = useAuth()
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(isTablet)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia(`(max-width: ${TABLET_BREAKPOINT}px)`)
    const handler = (e: MediaQueryListEvent) => setCollapsed(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || role === 'admin')

  const sidebarStyle: React.CSSProperties = {
    width: collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED,
    minWidth: collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED,
    height: '100vh',
    position: 'sticky',
    top: 0,
    display: 'flex',
    flexDirection: 'column',
    background: '#ffffff',
    borderRight: '1px solid #e2e8f0',
    transition: 'width 0.2s ease, min-width 0.2s ease',
    overflow: 'hidden',
  }

  const logoStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: collapsed ? '20px 0' : '20px 16px',
    justifyContent: collapsed ? 'center' : 'flex-start',
    borderBottom: '1px solid #e2e8f0',
    minHeight: 64,
    overflow: 'hidden',
  }

  const navStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    padding: '8px 0',
    gap: 2,
  }

  const toggleStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '12px',
    borderTop: '1px solid #e2e8f0',
    background: 'none',
    border: 'none',
    borderTopColor: '#e2e8f0',
    borderTopStyle: 'solid',
    borderTopWidth: 1,
    cursor: 'pointer',
    color: '#64748b',
    width: '100%',
  }

  return (
    <nav aria-label="Main navigation" style={sidebarStyle}>
      <div style={logoStyle}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'var(--color-primary)',
            color: '#fff',
            fontSize: 14,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          M
        </span>
        {!collapsed && (
          <span style={{ fontWeight: 700, fontSize: 16, color: '#0f172a', whiteSpace: 'nowrap' }}>
            MesaDigital
          </span>
        )}
      </div>

      <ul style={{ ...navStyle, listStyle: 'none' }}>
        {visibleItems.map(item => {
          const isActive = pathname === item.path || pathname.startsWith(item.path + '/')
          const linkStyle: React.CSSProperties = {
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: collapsed ? '10px 0' : '10px 16px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            textDecoration: 'none',
            borderRadius: 8,
            margin: '0 8px',
            color: isActive ? 'var(--color-primary)' : '#475569',
            background: isActive ? 'var(--color-primary-surface)' : 'transparent',
            fontWeight: isActive ? 600 : 400,
            fontSize: 14,
            transition: 'background 0.15s, color 0.15s',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }
          return (
            <li key={item.key}>
              <Link
                to={item.path}
                style={linkStyle}
                aria-label={collapsed ? item.label : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.icon}
                {!collapsed && <span>{item.label}</span>}
              </Link>
            </li>
          )
        })}
      </ul>

      <button
        style={toggleStyle}
        onClick={() => setCollapsed(c => !c)}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-expanded={!collapsed}
      >
        {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
      </button>
    </nav>
  )
}
