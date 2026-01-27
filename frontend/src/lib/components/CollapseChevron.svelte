<script lang="ts">
    import Icon from "@iconify/svelte";

    type Props = {
        expanded: boolean;
        sizeClass?: string;
    };

    let { expanded, sizeClass = "w-4 h-4" }: Props = $props();
</script>

<span
    class={`inline-flex ${sizeClass} transition-transform`}
    class:-rotate-90={!expanded}
>
    <Icon icon="lucide:chevron-down" class={sizeClass} />
</span>
