<script lang="ts">
    import { 
        SvelteFlow, 
        Controls, 
        Background, 
        BackgroundVariant, 
        MiniMap,
        addEdge,
        type Node,
        type Connection
    } from '@xyflow/svelte';
    
    import { nodes, edges } from '$lib/stores';
    import EntityNode from './EntityNode.svelte';
    
    const nodeTypes = {
        entity: EntityNode
    };
    
    function onConnect(connection: Connection) {
        $edges = addEdge(connection, $edges);
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
                description: '' 
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

