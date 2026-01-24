<script lang="ts">
    import Icon from "@iconify/svelte";

    type Props = {
        domain: string;
        size?: "small" | "medium";
        onclick?: () => void;
    };

    let { domain, size = "medium", onclick }: Props = $props();

    /**
     * Convert domain to title case (trimmed, first letter uppercase, rest lowercase).
     */
    function toTitleCase(str: string): string {
        return str.trim().charAt(0).toUpperCase() + str.trim().slice(1).toLowerCase();
    }

    const displayDomain = $derived(toTitleCase(domain));

    /**
     * Hash domain string to consistent color from palette.
     * Uses simple hash function to deterministically assign colors.
     */
    function getDomainColor(domain: string): { bg: string; text: string } {
        // Color palette: purple, teal, orange, indigo, pink, amber, emerald
        const colors = [
            { bg: "bg-purple-100", text: "text-purple-700" },
            { bg: "bg-teal-100", text: "text-teal-700" },
            { bg: "bg-orange-100", text: "text-orange-700" },
            { bg: "bg-indigo-100", text: "text-indigo-700" },
            { bg: "bg-pink-100", text: "text-pink-700" },
            { bg: "bg-amber-100", text: "text-amber-700" },
            { bg: "bg-emerald-100", text: "text-emerald-700" },
        ];

        // Simple hash function
        let hash = 0;
        for (let i = 0; i < domain.length; i++) {
            const char = domain.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            hash = hash & hash; // Convert to 32-bit integer
        }

        // Use absolute value and modulo to get index
        const index = Math.abs(hash) % colors.length;
        return colors[index];
    }

    const colorClasses = $derived(getDomainColor(domain));
    const sizeClasses = $derived(
        size === "small" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-xs"
    );
    const iconSize = $derived(size === "small" ? "w-3 h-3" : "w-3.5 h-3.5");
</script>

{#if onclick}
    <button
        onclick={onclick}
        class="inline-flex items-center gap-1.5 {colorClasses.bg} {colorClasses.text} border rounded font-medium hover:opacity-80 transition-opacity {sizeClasses} focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-400"
        title={displayDomain}
    >
        <Icon icon="lucide:tag" class={iconSize} />
        <span>{displayDomain}</span>
    </button>
{:else}
    <span
        class="inline-flex items-center gap-1.5 {colorClasses.bg} {colorClasses.text} border rounded font-medium {sizeClasses}"
        title={displayDomain}
    >
        <Icon icon="lucide:tag" class={iconSize} />
        <span>{displayDomain}</span>
    </span>
{/if}
