export type Restaurant = {
  name: string;
  address: string;
  hoursLabel: string;
  hoursLines: string[];
  deliveryOpen: boolean;
  instagram: string;
  maps: string;
  review: {
    quote: string;
    author: string;
    place: string;
    source: string;
    reviews: { quote: string; author: string }[];
  };
  offer: string;
};

export type User = {
  name: string;
  email: string;
  phone: string;
  role: string;
};

export type PickupSlot = { id: number; label: string; date?: string; start?: string; end?: string };

export type PickupPoint = { id: number; name: string; address: string };

export type Session = {
  csrf: string;
  user: User | null;
  cartCount: number;
  latestOrderRef?: string | null;
  restaurant: Restaurant;
  slots: PickupSlot[];
  points: PickupPoint[];
};

export type Category = {
  slug: string;
  name: string;
  count: number;
  description?: string;
  image?: string | null;
};

export type Product = {
  id: number;
  slug: string;
  name: string;
  description: string;
  image: string | null;
  video: string | null;
  categorySlug: string;
  categoryName: string;
  priceLabel: string;
  priceCents: number | null;
  priceConfirmed: boolean;
  available: boolean;
  orderable: boolean;
  availability: string;
  featured: boolean;
  hasOptions?: boolean;
};

export type Choice = {
  id: number;
  name: string;
  extra: string;
  deltaCents: number | null;
  deltaConfirmed: boolean;
  available: boolean;
};

export type OptionGroup = {
  id: number;
  name: string;
  required: boolean;
  choices: Choice[];
};

export type ProductPayload = {
  product: Product;
  groups: OptionGroup[];
  allowNotes: boolean;
};

export type CartLine = {
  id: number;
  slug: string;
  name: string;
  summary: string;
  notes: string;
  quantity: number;
  lineLabel: string;
  issues: string[];
  image: string | null;
};

export type TrackedOrder = {
  ref: string;
  statusLabel: string;
  lines: { name: string; quantity: number; lineLabel: string }[];
  subtotalLabel: string;
  deliveryLabel: string;
  discountLabel: string;
  totalLabel: string;
  events: { status: string; label?: string; at: string }[];
};

export type Cart = {
  lines: CartLine[];
  priced: boolean;
  subtotalLabel: string;
  discountLabel: string;
  beforeDeliveryLabel: string;
  promo: string;
  promoError: string;
  issues: string[];
  cartCount: number;
  suivi?: TrackedOrder[];
};

export type CheckoutPayload = {
  cart: Cart;
  idempotencyKey: string;
  zones: { id: number; name: string; feeLabel: string }[];
  slots: PickupSlot[];
  points: PickupPoint[];
  payments: { code: string; label: string }[];
  stripeReady?: boolean;
  stripeMessage?: string;
  deliveryMode?: "zones" | "distance";
  terms: string;
  customer: { nom: string; email: string; telephone: string };
};

export type OrderPayload = {
  ref: string;
  status: string;
  statusLabel: string;
  paymentStatus: string;
  paymentLabel: string;
  paymentMethod: string;
  paymentMethodLabel?: string;
  confirmedByProvider?: boolean;
  canRetry?: boolean;
  canReview?: boolean;
  reviewId?: number | null;
  lines: { name: string; quantity: number; options: string; lineLabel: string }[];
  subtotalLabel: string;
  deliveryLabel: string;
  discountLabel: string;
  totalLabel: string;
  events: { status: string; label?: string; at: string }[];
};

export type HomeReview = {
  id: number;
  author: string;
  initials: string;
  stars: number;
  body: string;
  dateLabel: string;
  verified: boolean;
};

export type HomePayload = {
  featured: Product[];
  categories: Category[];
  restaurant: Restaurant;
  signatureVideo: string | null;
  avis?: {
    average: number | null;
    count: number;
    histogram: { stars: number; count: number }[];
    reviews: HomeReview[];
  };
};

export type CatalogPayload = {
  categories: Category[];
  category: string;
  query: string;
  products: Product[];
};
