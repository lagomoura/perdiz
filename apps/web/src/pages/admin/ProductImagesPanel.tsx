import { useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';
import {
  useDeleteProductImage,
  useProductImages,
  useUpdateProductImage,
  useUploadAndAttachImage,
} from '@/features/admin/products';
import { getErrorMessage } from '@/lib/errors';

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

export function ProductImagesPanel({ productId }: { productId: string }) {
  const { data: images, isLoading } = useProductImages(productId);
  const uploadMut = useUploadAndAttachImage(productId);
  const updateMut = useUpdateProductImage(productId);
  const deleteMut = useDeleteProductImage(productId);

  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Solo PNG, JPEG o WebP.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError(`La imagen supera los ${MAX_IMAGE_BYTES / 1024 / 1024} MB.`);
      e.target.value = '';
      return;
    }

    const nextSortOrder =
      images && images.length > 0
        ? Math.max(...images.map((i) => i.sortOrder)) + 1
        : 0;

    try {
      await uploadMut.mutateAsync({
        file,
        sortOrder: nextSortOrder,
      });
    } catch (err) {
      const code = (err as { code?: string })?.code ?? 'UPLOAD_ERROR';
      const msg =
        (err as { message?: string })?.message ?? 'Error al subir la imagen.';
      setError(getErrorMessage(code, msg));
    } finally {
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function handleAltChange(imageId: string, altText: string) {
    try {
      await updateMut.mutateAsync({ imageId, payload: { altText } });
    } catch {
      // swallow — the input keeps the typed value, user can retry
    }
  }

  async function handleDelete(imageId: string) {
    if (!confirm('¿Eliminar esta imagen?')) return;
    await deleteMut.mutateAsync(imageId);
  }

  async function handleMove(imageId: string, direction: -1 | 1) {
    if (!images) return;
    const sorted = [...images].sort((a, b) => a.sortOrder - b.sortOrder);
    const idx = sorted.findIndex((i) => i.id === imageId);
    const swapIdx = idx + direction;
    if (idx === -1 || swapIdx < 0 || swapIdx >= sorted.length) return;
    const current = sorted[idx];
    const other = sorted[swapIdx];
    if (!current || !other) return;
    await Promise.all([
      updateMut.mutateAsync({
        imageId: current.id,
        payload: { sortOrder: other.sortOrder },
      }),
      updateMut.mutateAsync({
        imageId: other.id,
        payload: { sortOrder: current.sortOrder },
      }),
    ]);
  }

  const sorted = images ? [...images].sort((a, b) => a.sortOrder - b.sortOrder) : [];

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-brand-graphite-900">
          Imágenes
        </h2>
        <label>
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={handleFile}
          />
          <Button
            type="button"
            size="sm"
            loading={uploadMut.isPending}
            onClick={() => inputRef.current?.click()}
          >
            {uploadMut.isPending ? 'Subiendo…' : 'Subir imagen'}
          </Button>
        </label>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-error-500 bg-red-50 p-3 text-sm text-error-500">
          {error}
        </div>
      )}

      {isLoading && <p className="text-sm text-neutral-500">Cargando…</p>}

      {!isLoading && sorted.length === 0 && (
        <p className="text-sm text-neutral-500">
          Todavía no hay imágenes. Subí la primera para que aparezca en el
          catálogo.
        </p>
      )}

      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sorted.map((img, idx) => (
          <li
            key={img.id}
            className="flex items-start gap-3 rounded-lg border border-neutral-200 p-3"
          >
            {img.url ? (
              <img
                src={img.url}
                alt={img.altText ?? ''}
                className="h-24 w-24 shrink-0 rounded-lg object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-xs text-neutral-500">
                sin URL
              </div>
            )}
            <div className="flex-1 space-y-2">
              <input
                type="text"
                placeholder="Texto alternativo (alt)"
                defaultValue={img.altText ?? ''}
                onBlur={(e) =>
                  e.target.value !== (img.altText ?? '') &&
                  handleAltChange(img.id, e.target.value)
                }
                className="w-full rounded border border-neutral-300 px-2 py-1 text-sm"
              />
              <div className="flex items-center justify-between text-xs text-neutral-600">
                <span>Orden: {img.sortOrder}</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleMove(img.id, -1)}
                    disabled={idx === 0}
                    className="rounded px-2 py-1 hover:bg-neutral-100 disabled:opacity-40"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMove(img.id, 1)}
                    disabled={idx === sorted.length - 1}
                    className="rounded px-2 py-1 hover:bg-neutral-100 disabled:opacity-40"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(img.id)}
                    className="rounded px-2 py-1 text-error-500 hover:bg-red-50"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
