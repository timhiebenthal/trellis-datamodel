import { describe, it, expect } from 'vitest';
import { autoPromoteAllNodes } from './auto-promote-nodes';
import type { Node } from '@xyflow/svelte';
import type { DbtModel, EntityData } from '$lib/types';

function makeEntityNode(id: string, dbtModel: string | undefined, draftedFields: { name: string; datatype: string }[]): Node {
  return {
    id,
    type: 'entity',
    position: { x: 0, y: 0 },
    data: {
      label: id,
      model_ref: dbtModel,
      drafted_fields: draftedFields.length > 0 ? draftedFields : undefined,
    } as unknown as EntityData,
  } as Node;
}

function makeDbtModel(uniqueId: string, columnNames: string[]): DbtModel {
  return {
    unique_id: uniqueId,
    name: uniqueId.split('.').pop() ?? uniqueId,
    schema: 'public',
    table: uniqueId,
    columns: columnNames.map((n) => ({ name: n, type: 'text' })),
  };
}

describe('autoPromoteAllNodes', () => {
  it('promotes (removes) draft field whose name matches a dbt column', () => {
    const nodes = [
      makeEntityNode('booking', 'model.a.booking', [
        { name: 'id', datatype: 'int' },
        { name: 'new_field', datatype: 'text' },
      ]),
    ];
    const dbtModels: DbtModel[] = [makeDbtModel('model.a.booking', ['id'])];
    const { nodes: result, changed } = autoPromoteAllNodes(nodes, dbtModels);
    expect(changed).toBe(true);
    const entityData = result[0].data as unknown as EntityData;
    expect(entityData.drafted_fields).toEqual([{ name: 'new_field', datatype: 'text' }]);
  });

  it('returns same node reference when no drafts match dbt columns', () => {
    const nodes = [
      makeEntityNode('booking', 'model.a.booking', [
        { name: 'custom_field', datatype: 'text' },
      ]),
    ];
    const dbtModels: DbtModel[] = [makeDbtModel('model.a.booking', ['id'])];
    const { nodes: result, changed } = autoPromoteAllNodes(nodes, dbtModels);
    expect(changed).toBe(false);
    expect(result[0]).toBe(nodes[0]); // Same reference
  });

  it('leaves unbound nodes untouched', () => {
    const nodes = [makeEntityNode('unbound', undefined, [{ name: 'x', datatype: 'text' }])];
    const dbtModels: DbtModel[] = [makeDbtModel('model.a.something', ['x'])];
    const { nodes: result, changed } = autoPromoteAllNodes(nodes, dbtModels);
    expect(changed).toBe(false);
    expect(result[0]).toBe(nodes[0]);
  });

  it('handles node with no drafted_fields', () => {
    const nodes = [makeEntityNode('booking', 'model.a.booking', [])];
    const dbtModels: DbtModel[] = [makeDbtModel('model.a.booking', ['id'])];
    const { nodes: result, changed } = autoPromoteAllNodes(nodes, dbtModels);
    expect(changed).toBe(false);
    expect(result[0]).toBe(nodes[0]);
  });

  it('is case-sensitive: draft X does not match dbt x', () => {
    const nodes = [
      makeEntityNode('booking', 'model.a.booking', [{ name: 'X', datatype: 'text' }]),
    ];
    const dbtModels: DbtModel[] = [makeDbtModel('model.a.booking', ['x'])];
    const { nodes: result, changed } = autoPromoteAllNodes(nodes, dbtModels);
    expect(changed).toBe(false);
    const entityData = result[0].data as unknown as EntityData;
    expect(entityData.drafted_fields).toHaveLength(1);
  });

  it('returns original nodes array reference when nothing changed', () => {
    const nodes = [makeEntityNode('booking', 'model.a.booking', [])];
    const dbtModels: DbtModel[] = [];
    const { nodes: result } = autoPromoteAllNodes(nodes, dbtModels);
    expect(result).toBe(nodes); // Same array reference
  });
});
