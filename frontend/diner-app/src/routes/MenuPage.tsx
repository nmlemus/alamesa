import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMenu } from '../api/hooks'
import { useCartContext } from '../context/CartContext'
import type { MenuItemRead } from '../types'
import MenuCategoryTab from '../components/MenuCategoryTab'
import MenuItemCard from '../components/MenuItemCard'
import CartBar from '../components/CartBar'
import ItemDetailSheet from '../components/ItemDetailSheet'

function SkeletonBlock({
  width,
  height,
  style,
}: {
  width?: string | number
  height?: string | number
  style?: React.CSSProperties
}) {
  return (
    <div
      aria-hidden="true"
      style={{
        width,
        height,
        background: 'linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%)',
        backgroundSize: '200% 100%',
        animation: 'skeleton-pulse 1.5s ease-in-out infinite',
        borderRadius: 'var(--radius-md)',
        ...style,
      }}
    />
  )
}

function MenuLoadingSkeleton() {
  return (
    <div role="status" aria-label="Cargando menú">
      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-2)',
          padding: 'var(--spacing-4)',
          background: '#ffffff',
        }}
      >
        <SkeletonBlock width={96} height={32} style={{ borderRadius: 'var(--radius-full)', flexShrink: 0 }} />
        <SkeletonBlock width={96} height={32} style={{ borderRadius: 'var(--radius-full)', flexShrink: 0 }} />
      </div>
      <div style={{ padding: 'var(--spacing-4)' }}>
        {[0, 1, 2].map(i => (
          <div
            key={i}
            style={{
              background: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--spacing-4)',
              marginBottom: 'var(--spacing-3)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-3)',
            }}
          >
            <div style={{ flex: 1 }}>
              <SkeletonBlock width="60%" height={16} style={{ marginBottom: 'var(--spacing-2)' }} />
              <SkeletonBlock width="90%" height={12} style={{ marginBottom: 'var(--spacing-1)' }} />
              <SkeletonBlock width="40%" height={12} style={{ marginBottom: 'var(--spacing-3)' }} />
              <SkeletonBlock width={64} height={16} />
            </div>
            <SkeletonBlock width={36} height={36} style={{ borderRadius: 'var(--radius-full)', flexShrink: 0 }} />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function MenuPage() {
  const { slug, tableNumber } = useParams<{ slug: string; tableNumber: string }>()
  const navigate = useNavigate()
  const { categories, isLoading } = useMenu(slug ?? '')
  const cart = useCartContext()
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null)
  const [detailItem, setDetailItem] = useState<MenuItemRead | null>(null)

  const visibleCategories = categories.filter(c => c.is_visible)
  const resolvedCategoryId = activeCategoryId ?? visibleCategories[0]?.id ?? null
  const activeCategory = visibleCategories.find(c => c.id === resolvedCategoryId)

  return (
    <>
      <div
        style={{
          minHeight: '100vh',
          background: 'var(--color-surface)',
          paddingBottom: cart.item_count > 0 ? 80 : 0,
        }}
      >
        {isLoading && <MenuLoadingSkeleton />}

        {!isLoading && visibleCategories.length === 0 && (
          <p
            style={{
              padding: 'var(--spacing-8)',
              textAlign: 'center',
              color: '#64748b',
              fontSize: '0.9375rem',
            }}
          >
            El menú está vacío en este momento.
          </p>
        )}

        {!isLoading && visibleCategories.length > 0 && (
          <>
            <div
              style={{
                display: 'flex',
                gap: 'var(--spacing-2)',
                overflowX: 'auto',
                padding: 'var(--spacing-4)',
                background: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                scrollbarWidth: 'none',
              }}
            >
              {visibleCategories.map(category => (
                <MenuCategoryTab
                  key={category.id}
                  name={category.name}
                  isActive={category.id === resolvedCategoryId}
                  onClick={() => setActiveCategoryId(category.id)}
                />
              ))}
            </div>

            <div style={{ padding: 'var(--spacing-4)' }}>
              {activeCategory?.items.map(item => (
                <MenuItemCard
                  key={item.id}
                  item={item}
                  onBodyClick={() => setDetailItem(item)}
                  onAdd={() => cart.addItem(item, 1)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {cart.item_count > 0 && (
        <CartBar
          item_count={cart.item_count}
          total_cents={cart.total_cents}
          onClick={() => navigate(`/${slug}/mesa/${tableNumber}/carrito`)}
        />
      )}

      {detailItem && (
        <ItemDetailSheet
          item={detailItem}
          onClose={() => setDetailItem(null)}
          onAdd={(item, qty) => cart.addItem(item, qty)}
        />
      )}
    </>
  )
}
