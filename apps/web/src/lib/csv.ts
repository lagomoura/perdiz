/** Minimal RFC-4180-ish CSV parser. Handles quoted fields with embedded
 *  commas, newlines, and doubled quotes (""). Returns { headers, rows } where
 *  rows are keyed by lowercased header. */

export interface CsvParseResult {
  headers: string[];
  rows: Record<string, string>[];
}

export function parseCsv(input: string): CsvParseResult {
  const raw = parseRaw(input.replace(/^﻿/, ''));
  if (raw.length === 0) return { headers: [], rows: [] };
  const headers = raw[0]!.map((h) => h.trim().toLowerCase());
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < raw.length; i++) {
    const line = raw[i]!;
    if (line.length === 1 && line[0] === '') continue; // blank line
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => {
      row[h] = (line[idx] ?? '').trim();
    });
    rows.push(row);
  }
  return { headers, rows };
}

function parseRaw(text: string): string[][] {
  const out: string[][] = [];
  let field = '';
  let row: string[] = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
      continue;
    }
    if (c === '"') {
      inQuotes = true;
      continue;
    }
    if (c === ',') {
      row.push(field);
      field = '';
      continue;
    }
    if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      out.push(row);
      row = [];
      field = '';
      continue;
    }
    field += c;
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    out.push(row);
  }
  return out;
}

export function missingColumns(
  found: string[],
  required: string[],
): string[] {
  const set = new Set(found);
  return required.filter((r) => !set.has(r));
}
