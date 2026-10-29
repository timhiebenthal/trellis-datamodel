<script lang="ts">
    import Icon from "@iconify/svelte";

    let { count }: { count: number } = $props();
</script>

<div class="mb-1 px-1.5 py-1 bg-purple-50 border border-purple-200 rounded text-[10px] text-purple-700 flex items-center gap-1">
    <Icon icon="lucide:layers" class="w-3 h-3" />
    Batch editing {count} entities
</div>
