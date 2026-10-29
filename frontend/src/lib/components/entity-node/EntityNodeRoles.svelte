<script lang="ts">
    let { wrapperClass, roles }: { wrapperClass: string; roles: string[] } = $props();
</script>

<!-- Roles Display (for dimensions only, read-only in node view) -->
<div class={wrapperClass}>
    <div class="flex items-center gap-2 flex-wrap">
        <span
            class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
            >Roles</span>
        <div class="flex flex-wrap gap-1.5">
            {#each roles as role}
                <span
                    class="px-2 py-0.5 bg-green-100 text-green-800 rounded text-[10px] font-semibold border border-green-200"
                    title="Role: {role}"
                >
                    {role}
                </span>
            {/each}
        </div>
    </div>
</div>
