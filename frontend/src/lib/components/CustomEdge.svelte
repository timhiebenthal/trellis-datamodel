<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabel,
    getBezierPath,
    type EdgeProps
  } from '@xyflow/svelte';
  import { edges } from '$lib/stores';

  type $$Props = EdgeProps;

  let { 
    id, 
    sourceX, 
    sourceY, 
    targetX, 
    targetY, 
    sourcePosition, 
    targetPosition,
    style,
    markerEnd,
    data 
  } = $props<$$Props>();

  let [edgePath, labelX, labelY] = $derived(getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition
  }));

  // Use raw data.label for input value, default to empty
  let label = $derived(data?.label as string || '');
  let type = $derived(data?.type as string || 'one_to_many');

  function updateEdge(partial: Record<string, unknown>) {
    edges.update((list) =>
      list.map((edge) =>
        edge.id === id
          ? {
              ...edge,
              data: {
                ...(edge.data || {}),
                ...partial
              }
            }
          : edge
      )
    );
  }

  function onLabelChange(e: Event) {
    updateEdge({ label: (e.target as HTMLInputElement).value });
  }

  function toggleType(e: MouseEvent) {
    // Explicitly stop propagation at all levels
    e.stopPropagation();
    e.stopImmediatePropagation();
    const nextType = type === 'one_to_many' ? 'one_to_one' : 'one_to_many';
    updateEdge({ type: nextType });
  }
</script>

<BaseEdge path={edgePath} {markerEnd} {style} />

<EdgeLabel
  x={labelX}
  y={labelY}
>
  <div
    class="pointer-events-auto nodrag nopan bg-white px-1 py-0.5 rounded shadow-sm flex flex-col items-center w-auto"
    onmousedown={(e) => e.stopPropagation()}
    click={(e) => e.stopPropagation()}
    role="presentation"
  >
    <input
      value={label}
      oninput={onLabelChange}
      onchange={onLabelChange}
      class="text-xs font-medium text-center focus:outline-none focus:bg-gray-50 w-20 bg-transparent"
      placeholder="name me"
    />
    <button 
        class="text-[9px] text-gray-500 hover:text-blue-600 hover:underline cursor-pointer bg-transparent border-none p-0 relative z-50"
        onclick={toggleType}
        title="Click to toggle type"
        type="button"
    >
        ({type})
    </button>
  </div>
</EdgeLabel>
