export type CategoryStatus = 'active' | 'archived';

export interface Category {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  description: string | null;
  imageUrl: string | null;
  sortOrder: number;
  status: CategoryStatus;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export interface CategoryCreatePayload {
  name: string;
  slug: string;
  parentId?: string | null;
  description?: string | null;
  imageUrl?: string | null;
  sortOrder?: number;
  status?: CategoryStatus;
}

export type CategoryUpdatePayload = Partial<CategoryCreatePayload>;

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

export type StockMode = 'stocked' | 'print_on_demand';
export type ProductStatus = 'draft' | 'active' | 'archived';

export interface Product {
  id: string;
  categoryId: string;
  name: string;
  slug: string;
  description: string | null;
  basePriceCents: number;
  stockMode: StockMode;
  stockQuantity: number | null;
  leadTimeDays: number | null;
  weightGrams: number | null;
  dimensionsMm: number[] | null;
  sku: string;
  tags: string[];
  status: ProductStatus;
  modelFileId: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export interface ProductCreatePayload {
  categoryId: string;
  name: string;
  slug: string;
  description?: string | null;
  basePriceCents: number;
  stockMode: StockMode;
  stockQuantity?: number | null;
  leadTimeDays?: number | null;
  weightGrams?: number | null;
  dimensionsMm?: number[] | null;
  sku: string;
  tags?: string[];
  status?: ProductStatus;
  modelFileId?: string | null;
}

export type ProductUpdatePayload = Partial<ProductCreatePayload>;

export interface ProductImage {
  id: string;
  productId: string;
  mediaFileId: string;
  altText: string | null;
  sortOrder: number;
  url: string | null;
}

// -------- Public catalog ---------------------------------------------------

export type Availability = 'in_stock' | 'on_demand';
export type CatalogSort = 'newest' | 'price_asc' | 'price_desc' | 'relevance';

export interface PublicCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  imageUrl: string | null;
  sortOrder: number;
}

export interface PublicImage {
  url: string;
  alt: string | null;
}

export interface PublicCategoryRef {
  id: string;
  name: string;
  slug: string;
}

export interface PublicProduct {
  id: string;
  name: string;
  slug: string;
  priceCents: number;
  discountedPriceCents: number | null;
  currency: 'ARS';
  images: PublicImage[];
  category: PublicCategoryRef;
  availability: Availability;
  customizable: boolean;
  tags: string[];
}

export interface PublicProductDetail {
  id: string;
  name: string;
  slug: string;
  descriptionHtml: string | null;
  basePriceCents: number;
  discountedPriceCents: number | null;
  currency: 'ARS';
  category: PublicCategoryRef;
  images: PublicImage[];
  modelGlbUrl: string | null;
  stockMode: StockMode;
  stockQuantity: number | null;
  leadTimeDays: number | null;
  availability: Availability;
  customizable: boolean;
}

export interface PublicListPagination {
  nextCursor: string | null;
  hasMore: boolean;
  count: number;
}

export interface PublicProductsPage {
  data: PublicProduct[];
  pagination: PublicListPagination;
}
