import { useQuery } from '@tanstack/react-query';

import {
  getPublicProduct,
  listPublicCategories,
  listPublicProducts,
  type ListPublicProductsOpts,
} from '@/services/publicCatalog';

const KEYS = {
  categories: ['public', 'catalog', 'categories'] as const,
  products: (opts: ListPublicProductsOpts) =>
    ['public', 'catalog', 'products', opts] as const,
  detail: (slug: string) => ['public', 'catalog', 'detail', slug] as const,
};

export function usePublicCategories() {
  return useQuery({
    queryKey: KEYS.categories,
    queryFn: listPublicCategories,
    staleTime: 5 * 60_000,
  });
}

export function usePublicProducts(opts: ListPublicProductsOpts = {}) {
  return useQuery({
    queryKey: KEYS.products(opts),
    queryFn: () => listPublicProducts(opts),
  });
}

export function usePublicProduct(slug: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(slug ?? ''),
    queryFn: () => getPublicProduct(slug!),
    enabled: !!slug,
  });
}
