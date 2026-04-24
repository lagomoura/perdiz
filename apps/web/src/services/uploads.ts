import { apiFetch } from './api/client';

export type UploadKind = 'image' | 'model_stl';

export interface PresignResponse {
  storageKey: string;
  uploadUrl: string;
  method: 'PUT';
  headers: Record<string, string>;
  expiresAt: string;
}

interface PresignApi {
  storage_key: string;
  upload_url: string;
  method: 'PUT';
  headers: Record<string, string>;
  expires_at: string;
}

export async function presignAdminUpload(params: {
  kind: UploadKind;
  mimeType: string;
  sizeBytes: number;
  filename: string;
}): Promise<PresignResponse> {
  const res = await apiFetch<PresignApi>('/admin/uploads/presign', {
    method: 'POST',
    body: JSON.stringify({
      kind: params.kind,
      mime_type: params.mimeType,
      size_bytes: params.sizeBytes,
      filename: params.filename,
    }),
  });
  return {
    storageKey: res.storage_key,
    uploadUrl: res.upload_url,
    method: res.method,
    headers: res.headers,
    expiresAt: res.expires_at,
  };
}

export interface CommittedMediaFile {
  id: string;
  kind: string;
  mimeType: string;
  sizeBytes: number;
  storageKey: string;
  publicUrl: string | null;
}

export async function commitAdminUpload(params: {
  storageKey: string;
  kind: UploadKind;
  mimeType: string;
  sizeBytes: number;
}): Promise<CommittedMediaFile> {
  const res = await apiFetch<{
    media_file: {
      id: string;
      kind: string;
      mime_type: string;
      size_bytes: number;
      storage_key: string;
      public_url: string | null;
    };
  }>('/admin/uploads/commit', {
    method: 'POST',
    body: JSON.stringify({
      storage_key: params.storageKey,
      kind: params.kind,
      mime_type: params.mimeType,
      size_bytes: params.sizeBytes,
    }),
  });
  return {
    id: res.media_file.id,
    kind: res.media_file.kind,
    mimeType: res.media_file.mime_type,
    sizeBytes: res.media_file.size_bytes,
    storageKey: res.media_file.storage_key,
    publicUrl: res.media_file.public_url,
  };
}

export async function putToStorage(
  uploadUrl: string,
  file: File,
  headers: Record<string, string>,
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers,
  });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }
}

/** Full admin upload flow: presign → PUT → commit. Returns the committed MediaFile. */
export async function uploadAdminFile(
  file: File,
  kind: UploadKind,
): Promise<CommittedMediaFile> {
  const presigned = await presignAdminUpload({
    kind,
    mimeType: file.type,
    sizeBytes: file.size,
    filename: file.name,
  });
  await putToStorage(presigned.uploadUrl, file, presigned.headers);
  return await commitAdminUpload({
    storageKey: presigned.storageKey,
    kind,
    mimeType: file.type,
    sizeBytes: file.size,
  });
}
