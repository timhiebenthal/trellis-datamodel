<script lang="ts">
    import TagEditor from "../TagEditor.svelte";
    import BatchEditBanner from "./BatchEditBanner.svelte";

    let {
        wrapperClass,
        tags,
        readOnlyTags,
        isBatchEditing,
        batchCount,
        onUpdate,
    }: {
        wrapperClass: string;
        tags: string[];
        /** Omitted where the editor shows no read-only chips (TagEditor default). */
        readOnlyTags?: string[];
        isBatchEditing: boolean;
        batchCount: number;
        onUpdate: (newTags: string[]) => void;
    } = $props();
</script>

<!-- Tags Editor -->
<div class={wrapperClass}>
    {#if isBatchEditing}
        <BatchEditBanner count={batchCount} />
    {/if}
    <div class="flex items-center gap-2 flex-wrap mb-1">
        <span
            class="font-medium text-[10px] uppercase tracking-wider text-gray-500"
        >Tags</span>
        <TagEditor
            tags={tags}
            readOnlyTags={readOnlyTags}
            canEdit={true}
            isBatchMode={isBatchEditing}
            onUpdate={(newTags) => onUpdate(newTags)}
        ></TagEditor>
    </div>
</div>
