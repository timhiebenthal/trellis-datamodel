<script lang="ts">
  import { 
    BaseEdge, 
    EdgeLabelRenderer, 
    getBezierPath,
    type EdgeProps,
    useSvelteFlow
  } from '@xyflow/svelte';

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

  const { updateEdgeData } = useSvelteFlow();

  let [edgePath, labelX, labelY] = $derived(getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition
  }));

  let label = $derived(data?.label as string || 'name me');
  let type = $derived(data?.type as string || 'one_to_many');

  function onLabelChange(e: Event) {
    updateEdgeData(id, { label: (e.target as HTMLInputElement).value });
  }

  function toggleType() {
    const nextType = type === 'one_to_many' ? 'one_to_one' : 'one_to_many';
    updateEdgeData(id, { type: nextType });
  }
</script>

<BaseEdge path={edgePath} {markerEnd} {style} />

<EdgeLabelRenderer>
  <div
    style:transform="translate(-50%, -50%) translate({labelX}px, {labelY}px)"
    class="absolute pointer-events-auto bg-white px-2 py-1 rounded border border-gray-300 shadow-sm flex flex-col items-center min-w-[100px]"
  >
    <input
      value={label}
      oninput={onLabelChange}
      class="text-xs font-medium text-center focus:outline-none focus:bg-gray-50 w-full bg-transparent"
      placeholder="name me"
    />
    <button 
        class="text-[9px] text-gray-500 mt-0.5 hover:text-blue-600 hover:underline cursor-pointer bg-transparent border-none p-0"
        onclick={toggleType}
        title="Click to toggle type"
    >
        ({type})
    </button>
  </div>
</EdgeLabelRenderer>

