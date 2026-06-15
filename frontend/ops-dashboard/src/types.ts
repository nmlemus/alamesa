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
  id: number;
  email: string;
  name: string;
}

export interface CategoryRead {
  id: number;
  restaurant_id: number;
  name: string;
  sort_order: number;
}

export interface MenuItemRead {
  id: number;
  restaurant_id: number;
  category_id: number;
  name: string;
  description: string | null;
  price_cents: number;
  available: boolean;
}

export interface TableRead {
  id: number;
  restaurant_id: number;
  number: number;
  label: string | null;
  qr_url: string;
}

export interface OrderItemRead {
  id: number;
  order_id: number;
  menu_item_id: number;
  quantity: number;
  unit_price_cents: number;
}

export interface OrderRead {
  id: number;
  restaurant_id: number;
  table_id: number;
  diner_id: number | null;
  status: OrderStatus;
  created_at: string;
}

export interface OrderReadWithItems extends OrderRead {
  items: OrderItemRead[];
}
