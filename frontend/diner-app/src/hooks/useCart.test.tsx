import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useCart, formatCents } from './useCart';
import type { MenuItemRead } from '../types';

const item1: MenuItemRead = {
  id: 'item-1',
  restaurant_id: 'rest-1',
  category_id: 'cat-1',
  name: 'Hamburguesa',
  description: null,
  price_cents: 15000,
  is_available: true,
  display_order: 1,
};

const item2: MenuItemRead = {
  id: 'item-2',
  restaurant_id: 'rest-1',
  category_id: 'cat-1',
  name: 'Gaseosa',
  description: null,
  price_cents: 5000,
  is_available: true,
  display_order: 2,
};

describe('formatCents', () => {
  it('formats 15000 as $ 15.000', () => {
    expect(formatCents(15000)).toBe('$ 15.000');
  });

  it('formats 0 as $ 0', () => {
    expect(formatCents(0)).toBe('$ 0');
  });

  it('formats 1000000 as $ 1.000.000', () => {
    expect(formatCents(1000000)).toBe('$ 1.000.000');
  });

  it('formats 500 as $ 500', () => {
    expect(formatCents(500)).toBe('$ 500');
  });
});

describe('useCart', () => {
  it('starts with empty state', () => {
    const { result } = renderHook(() => useCart());
    expect(result.current.items).toEqual([]);
    expect(result.current.total_cents).toBe(0);
    expect(result.current.item_count).toBe(0);
  });

  it('addItem adds a new item with correct subtotal', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 2); });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].quantity).toBe(2);
    expect(result.current.items[0].subtotal_cents).toBe(30000);
    expect(result.current.total_cents).toBe(30000);
    expect(result.current.item_count).toBe(2);
  });

  it('addItem increments an existing item', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 1); });
    act(() => { result.current.addItem(item1, 2); });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].quantity).toBe(3);
    expect(result.current.items[0].subtotal_cents).toBe(45000);
  });

  it('addItem keeps different items separate', () => {
    const { result } = renderHook(() => useCart());
    act(() => {
      result.current.addItem(item1, 1);
      result.current.addItem(item2, 3);
    });
    expect(result.current.items).toHaveLength(2);
  });

  it('removeItem removes the item by id', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 2); });
    act(() => { result.current.removeItem(item1.id); });
    expect(result.current.items).toHaveLength(0);
    expect(result.current.total_cents).toBe(0);
    expect(result.current.item_count).toBe(0);
  });

  it('removeItem only removes the matching item', () => {
    const { result } = renderHook(() => useCart());
    act(() => {
      result.current.addItem(item1, 1);
      result.current.addItem(item2, 2);
    });
    act(() => { result.current.removeItem(item1.id); });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].menu_item.id).toBe(item2.id);
  });

  it('updateQuantity updates quantity and subtotal', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 1); });
    act(() => { result.current.updateQuantity(item1.id, 5); });
    expect(result.current.items[0].quantity).toBe(5);
    expect(result.current.items[0].subtotal_cents).toBe(75000);
    expect(result.current.total_cents).toBe(75000);
    expect(result.current.item_count).toBe(5);
  });

  it('updateQuantity removes item when quantity is 0', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 3); });
    act(() => { result.current.updateQuantity(item1.id, 0); });
    expect(result.current.items).toHaveLength(0);
  });

  it('updateQuantity removes item when quantity is negative', () => {
    const { result } = renderHook(() => useCart());
    act(() => { result.current.addItem(item1, 3); });
    act(() => { result.current.updateQuantity(item1.id, -1); });
    expect(result.current.items).toHaveLength(0);
  });

  it('clearCart empties all items', () => {
    const { result } = renderHook(() => useCart());
    act(() => {
      result.current.addItem(item1, 2);
      result.current.addItem(item2, 1);
    });
    act(() => { result.current.clearCart(); });
    expect(result.current.items).toHaveLength(0);
    expect(result.current.total_cents).toBe(0);
    expect(result.current.item_count).toBe(0);
  });

  it('total_cents and item_count are derived across multiple items', () => {
    const { result } = renderHook(() => useCart());
    act(() => {
      result.current.addItem(item1, 2);  // 2 × 15000 = 30000
      result.current.addItem(item2, 3);  // 3 × 5000  = 15000
    });
    expect(result.current.total_cents).toBe(45000);
    expect(result.current.item_count).toBe(5);
  });
});
