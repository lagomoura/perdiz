import { useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { useCategories } from '@/features/admin/categories';
import { missingColumns, parseCsv } from '@/lib/csv';
import { slugify } from '@/lib/slug';
import { createProduct } from '@/services/products';
import type {
  ProductCreatePayload,
  ProductStatus,
  StockMode,
} from '@/types/catalog';

interface ParsedRow {
  lineNo: number;
  row: ProductCreatePayload | null;
  error: string | null;
  name: string; // for display
  categorySlug: string;
}

interface RowResult {
  lineNo: number;
  name: string;
  ok: boolean;
  message: string;
}

const REQUIRED = ['name', 'sku', 'category_slug', 'base_price_pesos', 'stock_mode'];
const OPTIONAL = [
  'slug',
  'description',
  'stock_quantity',
  'lead_time_days',
  'weight_grams',
  'dimensions_mm',
  'tags',
  'status',
];

function pesosToCents(input: string): number | null {
  const normalized = input.replace(/\./g, '').replace(',', '.').trim();
  if (!normalized) return null;
  const num = Number(normalized);
  if (!Number.isFinite(num) || num < 0) return null;
  return Math.round(num * 100);
}

function parseDimensions(s: string): number[] | null {
  const trimmed = s.trim();
  if (!trimmed) return null;
  const parts = trimmed
    .split(/[x×,]/i)
    .map((p) => Number(p.trim()))
    .filter((n) => Number.isFinite(n) && n >= 0);
  return parts.length > 0 ? parts : null;
}

function parseTags(s: string): string[] {
  return s
    .split(/[,;|]/)
    .map((t) => t.trim())
    .filter(Boolean);
}

export function ProductsImportPage() {
  const qc = useQueryClient();
  const { data: categories } = useCategories();
  const inputRef = useRef<HTMLInputElement>(null);

  const [parsed, setParsed] = useState<ParsedRow[] | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [results, setResults] = useState<RowResult[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  const categoryBySlug = useMemo(() => {
    const m = new Map<string, { id: string; status: string }>();
    (categories ?? []).forEach((c) =>
      m.set(c.slug, { id: c.id, status: c.status }),
    );
    return m;
  }, [categories]);

  function buildPayload(
    row: Record<string, string>,
  ): { payload: ProductCreatePayload; displayName: string; categorySlug: string } | { error: string } {
    const name = (row.name ?? '').trim();
    const sku = (row.sku ?? '').trim();
    const categorySlug = (row.category_slug ?? '').trim();
    const priceStr = (row.base_price_pesos ?? '').trim();
    const stockModeRaw = (row.stock_mode ?? '').trim().toLowerCase();

    if (!name) return { error: 'name vacío' };
    if (!sku) return { error: 'sku vacío' };
    if (!categorySlug) return { error: 'category_slug vacío' };

    const cat = categoryBySlug.get(categorySlug);
    if (!cat) return { error: `category_slug "${categorySlug}" no existe` };
    if (cat.status !== 'active')
      return { error: `category_slug "${categorySlug}" no está activa` };

    const cents = pesosToCents(priceStr);
    if (cents === null) return { error: `base_price_pesos inválido: "${priceStr}"` };

    if (stockModeRaw !== 'stocked' && stockModeRaw !== 'print_on_demand')
      return {
        error: `stock_mode inválido: "${stockModeRaw}" (esperado: stocked | print_on_demand)`,
      };
    const stockMode = stockModeRaw as StockMode;

    let stockQuantity: number | null = null;
    let leadTimeDays: number | null = null;
    if (stockMode === 'stocked') {
      const q = row.stock_quantity ?? '';
      stockQuantity = q === '' ? 0 : Number(q);
      if (!Number.isFinite(stockQuantity) || stockQuantity < 0)
        return { error: 'stock_quantity inválido' };
    } else {
      const l = row.lead_time_days ?? '';
      leadTimeDays = l === '' ? 7 : Number(l);
      if (!Number.isFinite(leadTimeDays) || leadTimeDays < 1)
        return { error: 'lead_time_days debe ser >= 1' };
    }

    const weightRaw = (row.weight_grams ?? '').trim();
    const weightGrams = weightRaw ? Number(weightRaw) : null;
    if (weightGrams !== null && (!Number.isFinite(weightGrams) || weightGrams < 0))
      return { error: 'weight_grams inválido' };

    const statusRaw = (row.status || 'draft').toLowerCase();
    const status: ProductStatus = ['draft', 'active', 'archived'].includes(
      statusRaw,
    )
      ? (statusRaw as ProductStatus)
      : 'draft';

    const slug = (row.slug || slugify(name)).trim();
    if (!/^[a-z0-9][a-z0-9-]*$/.test(slug))
      return { error: `slug inválido: "${slug}"` };

    return {
      payload: {
        categoryId: cat.id,
        name,
        slug,
        description: row.description ? row.description : null,
        basePriceCents: cents,
        stockMode,
        stockQuantity,
        leadTimeDays,
        weightGrams,
        dimensionsMm: parseDimensions(row.dimensions_mm ?? ''),
        sku,
        tags: parseTags(row.tags ?? ''),
        status,
      },
      displayName: name,
      categorySlug,
    };
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setParseError(null);
    setResults([]);
    const file = e.target.files?.[0];
    if (!file) return;
    if (!categories) {
      setParseError('Esperá a que carguen las categorías y probá de nuevo.');
      return;
    }
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
          const built = buildPayload(r);
          if ('error' in built) {
            return {
              lineNo: idx + 2,
              row: null,
              error: built.error,
              name: r.name ?? '',
              categorySlug: r.category_slug ?? '',
            };
          }
          return {
            lineNo: idx + 2,
            row: built.payload,
            error: null,
            name: built.displayName,
            categorySlug: built.categorySlug,
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
    const log: RowResult[] = [];

    for (let i = 0; i < parsed.length; i++) {
      const row = parsed[i]!;
      if (!row.row) {
        log.push({
          lineNo: row.lineNo,
          name: row.name,
          ok: false,
          message: row.error ?? 'Fila inválida',
        });
      } else {
        try {
          const created = await createProduct(row.row);
          log.push({
            lineNo: row.lineNo,
            name: row.name,
            ok: true,
            message: `Creado id=${created.id.slice(-6)}`,
          });
        } catch (err) {
          const msg =
            (err as { message?: string })?.message ?? 'Error desconocido';
          log.push({
            lineNo: row.lineNo,
            name: row.name,
            ok: false,
            message: msg,
          });
        }
      }
      setResults([...log]);
      setProgress(i + 1);
    }

    setRunning(false);
    qc.invalidateQueries({ queryKey: ['admin', 'products'] });
  }

  const validRows = parsed?.filter((r) => r.row !== null).length ?? 0;
  const invalidRows = parsed?.filter((r) => r.row === null).length ?? 0;
  const okCount = results.filter((r) => r.ok).length;
  const failCount = results.filter((r) => !r.ok).length;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-neutral-900">
          Importar productos por CSV
        </h1>
        <Link
          to="/admin/productos"
          className="text-sm text-neutral-600 hover:text-neutral-900"
        >
          ← Volver a productos
        </Link>
      </div>

      <div className="space-y-4 rounded-xl border border-neutral-200 bg-neutral-50 p-6">
        <div>
          <p className="text-sm text-neutral-600">
            Subí un CSV con estas columnas. Las imágenes se cargan después
            entrando a cada producto.
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
{`name,sku,category_slug,base_price_pesos,stock_mode,stock_quantity,lead_time_days,weight_grams,dimensions_mm,tags,status,description,slug
Colador de Hojas,COL-001,cocina,15000,stocked,10,,100,100x50x30,"cocina,food,petg",active,Colador resistente,
T-Rex chico,DIN-TRX-S,dinosaurios,8500,print_on_demand,,7,50,80x40x60,"figura,dino",draft,,`}
          </pre>
          <p className="mt-2 text-xs text-neutral-500">
            <code>base_price_pesos</code> en pesos argentinos (ej.{' '}
            <code>15000</code> o <code>15.000,00</code>).{' '}
            <code>stock_mode</code>: <code>stocked</code> (llena{' '}
            <code>stock_quantity</code>) o <code>print_on_demand</code> (llena{' '}
            <code>lead_time_days</code>). <code>status</code> default{' '}
            <code>draft</code>.
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
            <p className="text-sm text-neutral-600">
              <strong className="text-green-700">{validRows}</strong> válidas ·{' '}
              <strong className="text-error-500">{invalidRows}</strong> con
              error (se van a saltear)
            </p>
            <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-neutral-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 text-neutral-500">
                  <tr>
                    <th className="px-2 py-2">#</th>
                    <th className="px-2 py-2">Nombre</th>
                    <th className="px-2 py-2">Categoría</th>
                    <th className="px-2 py-2">Estado fila</th>
                  </tr>
                </thead>
                <tbody>
                  {parsed.map((r) => (
                    <tr key={r.lineNo} className="border-t border-neutral-100">
                      <td className="px-2 py-1 text-neutral-500">{r.lineNo}</td>
                      <td className="px-2 py-1">{r.name || '—'}</td>
                      <td className="px-2 py-1 font-mono text-neutral-500">
                        {r.categorySlug}
                      </td>
                      <td
                        className={`px-2 py-1 ${r.row ? 'text-green-700' : 'text-error-500'}`}
                      >
                        {r.row ? 'ok' : r.error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Button
                type="button"
                onClick={runImport}
                loading={running}
                disabled={validRows === 0}
              >
                {running
                  ? `Importando ${progress}/${parsed.length}…`
                  : `Importar ${validRows} productos`}
              </Button>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="mt-4">
            <p className="text-sm">
              <strong className="text-green-700">{okCount}</strong> creados ·{' '}
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
