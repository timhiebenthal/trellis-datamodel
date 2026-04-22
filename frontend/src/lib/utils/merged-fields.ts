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

export function mergeFields(
  dbtColumns: DbtColumn[] | undefined,
  drafted: DraftedField[] | undefined,
): MergedField[] {
  const dbtNames = new Set((dbtColumns ?? []).map((c) => c.name));
  const dbtRows: MergedField[] = (dbtColumns ?? []).map((c) => ({
    origin: 'dbt' as const,
    name: c.name,
    datatype: c.type,
    description: c.description,
  }));
  const draftRows: MergedField[] = [];
  (drafted ?? []).forEach((d, i) => {
    if (dbtNames.has(d.name)) return;
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
