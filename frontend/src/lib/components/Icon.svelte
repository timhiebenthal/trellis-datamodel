<script lang="ts">
    import Icon from "@iconify/svelte";

    // Simple wrapper to keep a consistent Icon API across the app
    let { icon, ...rest } = $props<{ icon: string; class?: string; [key: string]: unknown }>();
</script>

<Icon {icon} {...rest} />
