import type { DbtColumn, DraftedField } from '$lib/types';

export type MergedField =
  | { origin: 'dbt'; name: string; datatype?: string; description?: string }
  | {
      origin: 'draft';
      name: string;
      datatype?: string;
      description?: string;
      draftIndex: number;
    };

function normalizeFieldName(name: string): string {
  return name.toLowerCase();
}

export function mergeFields(
  dbtColumns: DbtColumn[] | undefined,
  drafted: DraftedField[] | undefined,
): MergedField[] {
  const dbtColumnList = dbtColumns ?? [];
  const draftedList = drafted ?? [];
  const dbtCanonicalNames = new Set(dbtColumnList.map((c) => normalizeFieldName(c.name)));
  const dbtRows: MergedField[] = dbtColumnList.map((c) => ({
    origin: 'dbt' as const,
    name: c.name,
    datatype: c.type,
    description: c.description,
  }));
  const draftRows: MergedField[] = [];
  draftedList.forEach((d, i) => {
    if (dbtCanonicalNames.has(normalizeFieldName(d.name))) return;
    draftRows.push({
      origin: 'draft' as const,
      name: d.name,
      datatype: d.datatype,
      description: d.description,
      draftIndex: i,
    });
  });
  return [...dbtRows, ...draftRows];
}
