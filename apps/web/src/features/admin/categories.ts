import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createCategory,
  deleteCategory,
  getCategory,
  listCategories,
  updateCategory,
} from '@/services/categories';
import type {
  Category,
  CategoryCreatePayload,
  CategoryStatus,
  CategoryTreeNode,
  CategoryUpdatePayload,
} from '@/types/catalog';

const KEYS = {
  all: ['admin', 'categories'] as const,
  list: (status?: CategoryStatus) => [...KEYS.all, 'list', status ?? 'any'] as const,
  detail: (id: string) => [...KEYS.all, 'detail', id] as const,
};

export function useCategories(status?: CategoryStatus) {
  return useQuery({
    queryKey: KEYS.list(status),
    queryFn: () => listCategories(status ? { status } : undefined),
  });
}

export function useCategory(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(id ?? ''),
    queryFn: () => getCategory(id!),
    enabled: !!id,
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreatePayload) => createCategory(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CategoryUpdatePayload }) =>
      updateCategory(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCategory(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function buildTree(flat: Category[]): CategoryTreeNode[] {
  const byId = new Map<string, CategoryTreeNode>();
  const roots: CategoryTreeNode[] = [];

  for (const cat of flat) {
    byId.set(cat.id, { ...cat, children: [] });
  }
  for (const node of byId.values()) {
    if (node.parentId && byId.has(node.parentId)) {
      byId.get(node.parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  const byOrder = (a: CategoryTreeNode, b: CategoryTreeNode) =>
    a.sortOrder - b.sortOrder || a.name.localeCompare(b.name);
  const sortRec = (list: CategoryTreeNode[]) => {
    list.sort(byOrder);
    list.forEach((n) => sortRec(n.children));
  };
  sortRec(roots);
  return roots;
}

export function flattenTree(
  nodes: CategoryTreeNode[],
  depth = 0,
): Array<CategoryTreeNode & { depth: number }> {
  const out: Array<CategoryTreeNode & { depth: number }> = [];
  for (const n of nodes) {
    out.push({ ...n, depth });
    out.push(...flattenTree(n.children, depth + 1));
  }
  return out;
}

function findNode(
  nodes: CategoryTreeNode[],
  id: string,
): CategoryTreeNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    const hit = findNode(n.children, id);
    if (hit) return hit;
  }
  return null;
}

/** Returns ids of descendants of `targetId` (excluding the target itself).
 * Used to forbid picking self or a descendant as parent (cycle prevention). */
export function descendantIds(
  nodes: CategoryTreeNode[],
  targetId: string,
): Set<string> {
  const target = findNode(nodes, targetId);
  if (!target) return new Set();
  const out = new Set<string>();
  const collect = (list: CategoryTreeNode[]) => {
    for (const n of list) {
      out.add(n.id);
      collect(n.children);
    }
  };
  collect(target.children);
  return out;
}
