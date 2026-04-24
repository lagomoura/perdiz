import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { useCategories } from '@/features/admin/categories';
import { missingColumns, parseCsv } from '@/lib/csv';
import { slugify } from '@/lib/slug';
import { createCategory } from '@/services/categories';
import type { CategoryStatus } from '@/types/catalog';

interface ParsedRow {
  lineNo: number; // 2-based (header is line 1)
  name: string;
  slug: string;
  parentSlug: string;
  description: string;
  imageUrl: string;
  sortOrder: number;
  status: CategoryStatus;
}

interface RowResult {
  lineNo: number;
  name: string;
  ok: boolean;
  message: string;
}

const REQUIRED = ['name'];
const OPTIONAL = [
  'slug',
  'parent_slug',
  'description',
  'image_url',
  'sort_order',
  'status',
];

export function CategoriesImportPage() {
  const qc = useQueryClient();
  const { data: existing } = useCategories();
  const inputRef = useRef<HTMLInputElement>(null);

  const [parsed, setParsed] = useState<ParsedRow[] | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [results, setResults] = useState<RowResult[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setParseError(null);
    setResults([]);
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const { headers, rows } = parseCsv(String(reader.result ?? ''));
        const missing = missingColumns(headers, REQUIRED);
        if (missing.length > 0) {
          setParseError(
            `Faltan columnas obligatorias: ${missing.join(', ')}. Obligatorias: ${REQUIRED.join(', ')}. Opcionales: ${OPTIONAL.join(', ')}.`,
          );
          setParsed(null);
          return;
        }
        const parsed: ParsedRow[] = rows.map((r, idx) => {
          const name = r.name ?? '';
          const statusRaw = (r.status || 'active').toLowerCase();
          const status: CategoryStatus =
            statusRaw === 'archived' ? 'archived' : 'active';
          return {
            lineNo: idx + 2,
            name,
            slug: r.slug || slugify(name),
            parentSlug: (r.parent_slug ?? '').trim(),
            description: r.description ?? '',
            imageUrl: r.image_url ?? '',
            sortOrder: Number(r.sort_order) || 0,
            status,
          };
        });
        setParsed(parsed);
      } catch (err) {
        setParseError(String(err));
        setParsed(null);
      }
    };
    reader.readAsText(file);
  }

  async function runImport() {
    if (!parsed) return;
    setRunning(true);
    setResults([]);
    setProgress(0);

    // Build mutable slug → id map so children can reference parents created in
    // the same run. Start from already-existing categories.
    const slugToId = new Map<string, string>();
    (existing ?? []).forEach((c) => slugToId.set(c.slug, c.id));

    const log: RowResult[] = [];

    for (let i = 0; i < parsed.length; i++) {
      const row = parsed[i]!;
      try {
        if (!row.name.trim()) throw new Error('Nombre vacío');

        let parentId: string | null = null;
        if (row.parentSlug) {
          parentId = slugToId.get(row.parentSlug) ?? null;
          if (!parentId) {
            throw new Error(
              `parent_slug "${row.parentSlug}" no existe (tampoco en filas anteriores de este import)`,
            );
          }
        }

        const created = await createCategory({
          name: row.name.trim(),
          slug: row.slug,
          parentId,
          description: row.description || null,
          imageUrl: row.imageUrl || null,
          sortOrder: row.sortOrder,
          status: row.status,
        });
        slugToId.set(created.slug, created.id);
        log.push({
          lineNo: row.lineNo,
          name: row.name,
          ok: true,
          message: `Creada id=${created.id.slice(-6)}`,
        });
      } catch (err) {
        const msg =
          (err as { message?: string })?.message ?? 'Error desconocido';
        log.push({ lineNo: row.lineNo, name: row.name, ok: false, message: msg });
      }
      setResults([...log]);
      setProgress(i + 1);
    }

    setRunning(false);
    qc.invalidateQueries({ queryKey: ['admin', 'categories'] });
  }

  const okCount = results.filter((r) => r.ok).length;
  const failCount = results.filter((r) => !r.ok).length;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-brand-graphite-900">
          Importar categorías por CSV
        </h1>
        <Link
          to="/admin/categorias"
          className="text-sm text-neutral-600 hover:text-brand-graphite-900"
        >
          ← Volver a categorías
        </Link>
      </div>

      <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-6">
        <div>
          <p className="text-sm text-neutral-700">
            Subí un CSV con estas columnas. La primera fila es el header.
          </p>
          <ul className="mt-2 text-xs text-neutral-600">
            <li>
              <strong>Obligatorias:</strong> {REQUIRED.join(', ')}
            </li>
            <li>
              <strong>Opcionales:</strong> {OPTIONAL.join(', ')}
            </li>
          </ul>
          <pre className="mt-3 overflow-auto rounded-lg bg-neutral-50 p-3 text-xs">
{`name,slug,parent_slug,description,image_url,sort_order,status
Cocina,,,"Productos de cocina",,0,active
Utensilios,utensilios,cocina,,,0,active
Dinosaurios,,figuritas-3d,"Figuras de T-Rex, etc",,0,active`}
          </pre>
          <p className="mt-2 text-xs text-neutral-500">
            Si `slug` está vacío, se genera del nombre. `parent_slug` referencia
            a otra categoría existente (o creada antes en el mismo CSV).
            `status` default: <code>active</code>.
          </p>
        </div>

        <div className="pt-2">
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={handleFile}
          />
          <Button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={running}
          >
            Elegir archivo CSV
          </Button>
        </div>

        {parseError && (
          <div className="rounded-lg border border-error-500 bg-red-50 p-3 text-sm text-error-500">
            {parseError}
          </div>
        )}

        {parsed && (
          <div>
            <p className="text-sm text-neutral-700">
              <strong>{parsed.length}</strong> filas listas para importar.
            </p>
            <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-neutral-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 text-neutral-500">
                  <tr>
                    <th className="px-2 py-2">#</th>
                    <th className="px-2 py-2">Nombre</th>
                    <th className="px-2 py-2">Slug</th>
                    <th className="px-2 py-2">Padre</th>
                    <th className="px-2 py-2">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {parsed.map((r) => (
                    <tr key={r.lineNo} className="border-t border-neutral-100">
                      <td className="px-2 py-1 text-neutral-500">{r.lineNo}</td>
                      <td className="px-2 py-1">{r.name}</td>
                      <td className="px-2 py-1 font-mono">{r.slug}</td>
                      <td className="px-2 py-1 font-mono text-neutral-500">
                        {r.parentSlug || '—'}
                      </td>
                      <td className="px-2 py-1">{r.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Button type="button" onClick={runImport} loading={running}>
                {running
                  ? `Importando ${progress}/${parsed.length}…`
                  : `Importar ${parsed.length} categorías`}
              </Button>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="mt-4">
            <p className="text-sm">
              <strong className="text-green-700">{okCount}</strong> creadas ·{' '}
              <strong className="text-error-500">{failCount}</strong> con error
            </p>
            <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-neutral-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 text-neutral-500">
                  <tr>
                    <th className="px-2 py-2">#</th>
                    <th className="px-2 py-2">Nombre</th>
                    <th className="px-2 py-2">Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.lineNo} className="border-t border-neutral-100">
                      <td className="px-2 py-1 text-neutral-500">{r.lineNo}</td>
                      <td className="px-2 py-1">{r.name}</td>
                      <td
                        className={`px-2 py-1 ${r.ok ? 'text-green-700' : 'text-error-500'}`}
                      >
                        {r.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
