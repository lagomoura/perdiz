import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createProductImage,
  deleteProductImage,
  listProductImages,
  updateProductImage,
} from '@/services/productImages';
import {
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  transitionProductStatus,
  updateProduct,
  type ListProductsOpts,
} from '@/services/products';
import { uploadAdminFile } from '@/services/uploads';
import type {
  ProductCreatePayload,
  ProductStatus,
  ProductUpdatePayload,
} from '@/types/catalog';

const KEYS = {
  all: ['admin', 'products'] as const,
  list: (opts: ListProductsOpts) => [...KEYS.all, 'list', opts] as const,
  detail: (id: string) => [...KEYS.all, 'detail', id] as const,
  images: (productId: string) =>
    [...KEYS.all, 'detail', productId, 'images'] as const,
};

export function useProducts(opts: ListProductsOpts = {}) {
  return useQuery({
    queryKey: KEYS.list(opts),
    queryFn: () => listProducts(opts),
  });
}

export function useProduct(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(id ?? ''),
    queryFn: () => getProduct(id!),
    enabled: !!id,
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreatePayload) => createProduct(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: ProductUpdatePayload;
    }) => updateProduct(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useTransitionProductStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ProductStatus }) =>
      transitionProductStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useProductImages(productId: string | undefined) {
  return useQuery({
    queryKey: KEYS.images(productId ?? ''),
    queryFn: () => listProductImages(productId!),
    enabled: !!productId,
  });
}

export function useUploadAndAttachImage(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      altText,
      sortOrder,
    }: {
      file: File;
      altText?: string;
      sortOrder?: number;
    }) => {
      const media = await uploadAdminFile(file, 'image');
      return await createProductImage(productId, {
        mediaFileId: media.id,
        altText: altText ?? null,
        sortOrder,
      });
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.images(productId) }),
  });
}

export function useUpdateProductImage(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      imageId,
      payload,
    }: {
      imageId: string;
      payload: { altText?: string | null; sortOrder?: number };
    }) => updateProductImage(productId, imageId, payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.images(productId) }),
  });
}

export function useDeleteProductImage(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (imageId: string) => deleteProductImage(productId, imageId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.images(productId) }),
  });
}
