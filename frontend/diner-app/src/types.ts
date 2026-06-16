export const OrderStatus = {
  PENDING: "pending",
  CONFIRMED: "confirmed",
  PREPARING: "preparing",
  READY: "ready",
  CLOSED: "closed",
  CANCELLED: "cancelled",
} as const;

export type OrderStatus = "pending" | "confirmed" | "preparing" | "ready" | "closed" | "cancelled";

export const RestaurantUserRole = {
  ADMIN: "admin",
  STAFF: "staff",
} as const;

export type RestaurantUserRole = "admin" | "staff";

export const OrderEventActorType = {
  DINER: "diner",
  STAFF: "staff",
  SYSTEM: "system",
} as const;

export type OrderEventActorType = "diner" | "staff" | "system";

export interface DinerRead {
  id: string;
  phone: string;
  name: string;
}

export interface CategoryRead {
  id: string;
  restaurant_id: string;
  name: string;
  display_order: number;
}

export interface MenuItemRead {
  id: string;
  restaurant_id: string;
  category_id: string;
  name: string;
  description: string | null;
  price_cents: number;
  available: boolean;
}

export interface TableRead {
  id: string;
  restaurant_id: string;
  number: number;
  label: string | null;
  qr_url: string;
}

export interface OrderItemRead {
  id: string;
  order_id: string;
  menu_item_id: string;
  quantity: number;
  unit_price_cents: number;
}

export interface OrderRead {
  id: string;
  restaurant_id: string;
  table_id: string;
  diner_id: string | null;
  status: OrderStatus;
  created_at: string;
}

export interface OrderReadWithItems extends OrderRead {
  items: OrderItemRead[];
}

export interface CartItem {
  menu_item: MenuItemRead;
  quantity: number;
  subtotal_cents: number;
}

export interface CartState {
  items: CartItem[];
  total_cents: number;
  item_count: number;
}
