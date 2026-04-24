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
