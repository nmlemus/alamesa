import { useState, useCallback } from 'react';
import type { CartItem, CartState, MenuItemRead } from '../types';

export function formatCents(cents: number): string {
  return `$ ${new Intl.NumberFormat('es', { maximumFractionDigits: 0, minimumFractionDigits: 0 }).format(cents)}`;
}

function deriveCart(items: CartItem[]): CartState {
  return {
    items,
    total_cents: items.reduce((sum, item) => sum + item.subtotal_cents, 0),
    item_count: items.reduce((sum, item) => sum + item.quantity, 0),
  };
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);

  const addItem = useCallback((menuItem: MenuItemRead, quantity: number) => {
    setItems(prev => {
      const existing = prev.find(i => i.menu_item.id === menuItem.id);
      if (existing) {
        return prev.map(i =>
          i.menu_item.id === menuItem.id
            ? {
                ...i,
                quantity: i.quantity + quantity,
                subtotal_cents: (i.quantity + quantity) * menuItem.price_cents,
              }
            : i,
        );
      }
      return [
        ...prev,
        { menu_item: menuItem, quantity, subtotal_cents: quantity * menuItem.price_cents },
      ];
    });
  }, []);

  const removeItem = useCallback((menuItemId: string) => {
    setItems(prev => prev.filter(i => i.menu_item.id !== menuItemId));
  }, []);

  const updateQuantity = useCallback((menuItemId: string, quantity: number) => {
    setItems(prev => {
      if (quantity <= 0) {
        return prev.filter(i => i.menu_item.id !== menuItemId);
      }
      return prev.map(i =>
        i.menu_item.id === menuItemId
          ? { ...i, quantity, subtotal_cents: quantity * i.menu_item.price_cents }
          : i,
      );
    });
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  return {
    ...deriveCart(items),
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
  };
}
