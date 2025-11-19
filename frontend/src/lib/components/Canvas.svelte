<script lang="ts">
    import { 
        SvelteFlow, 
        Controls, 
        Background, 
        BackgroundVariant, 
        MiniMap,
        type Node,
        type Connection,
        type Edge
    } from '@xyflow/svelte';
    
    import { nodes, edges } from '$lib/stores';
    import EntityNode from './EntityNode.svelte';
    import CustomEdge from './CustomEdge.svelte';
    
    const nodeTypes = {
        entity: EntityNode
    };
    
    const edgeTypes = {
        custom: CustomEdge
    };
    
    function onConnect(connection: Connection) {
        const edge: Edge = {
            ...connection,
            id: crypto.randomUUID(),
            type: 'custom',
            data: {
                label: '',
                type: 'one_to_many'
            }
        };
        $edges = [...$edges, edge];
    }
    
    function addEntity() {
        const id = crypto.randomUUID();
        const newNode: Node = {
            id,
            type: 'entity',
            position: { 
                x: 100 + Math.random() * 200, 
                y: 100 + Math.random() * 200 
            },
            data: { 
                label: 'New Entity', 
                description: '',
                width: 280,
                panelHeight: 200,
            }
        };
        $nodes = [...$nodes, newNode];
    }
</script>

<div class="flex-1 h-full relative w-full">
    <SvelteFlow
        bind:nodes={$nodes}
        bind:edges={$edges}
        {nodeTypes}
        {edgeTypes}
        onconnect={onConnect}
        fitView
        class="bg-gray-50"
    >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <MiniMap />
        
        <div class="absolute top-4 right-4 z-10 shadow-lg">
            <button 
                class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 font-medium transition-colors flex items-center gap-2"
                onclick={addEntity}
            >
                <span>+</span> Add Entity
            </button>
        </div>
    </SvelteFlow>
</div>
