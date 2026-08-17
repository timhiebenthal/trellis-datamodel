<script lang="ts">
    type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

    interface Props {
        text: string;
        position?: TooltipPosition;
        children?: import('svelte').Snippet;
    }

    let { text, position = 'top', children }: Props = $props();

    let showTooltip = $state(false);
    let anchorElement = $state<HTMLDivElement>();
    let tooltipTop = $state(0);
    let tooltipLeft = $state(0);

    function updateTooltipPosition() {
        if (!anchorElement) return;

        const rect = anchorElement.getBoundingClientRect();
        switch (position) {
            case 'bottom':
                tooltipTop = rect.bottom + 8;
                tooltipLeft = rect.left + rect.width / 2;
                break;
            case 'left':
                tooltipTop = rect.top + rect.height / 2;
                tooltipLeft = rect.left - 8;
                break;
            case 'right':
                tooltipTop = rect.top + rect.height / 2;
                tooltipLeft = rect.right + 8;
                break;
            case 'top':
            default:
                tooltipTop = rect.top - 8;
                tooltipLeft = rect.left + rect.width / 2;
                break;
        }
    }

    function handleMouseEnter() {
        updateTooltipPosition();
        showTooltip = true;
    }

    function handleMouseLeave() {
        showTooltip = false;
    }

    $effect(() => {
        if (!showTooltip) return;

        window.addEventListener('scroll', updateTooltipPosition, true);
        window.addEventListener('resize', updateTooltipPosition);

        return () => {
            window.removeEventListener('scroll', updateTooltipPosition, true);
            window.removeEventListener('resize', updateTooltipPosition);
        };
    });

    const positionClasses: Record<TooltipPosition, string> = {
        top: '-translate-x-1/2 -translate-y-full',
        bottom: '-translate-x-1/2',
        left: '-translate-x-full -translate-y-1/2',
        right: '-translate-y-1/2',
    };

    const arrowClasses: Record<TooltipPosition, string> = {
        top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 border-l-transparent border-r-transparent border-b-transparent',
        bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 border-l-transparent border-r-transparent border-t-transparent',
        left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 border-t-transparent border-b-transparent border-r-transparent',
        right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 border-t-transparent border-b-transparent border-l-transparent',
    };

    // Ensure position is typed correctly for indexing
    const currentPosition = $derived((position ?? 'top') as TooltipPosition);
</script>

<div
    bind:this={anchorElement}
    class="relative inline-flex items-center"
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    role="presentation"
>
    {@render children?.()}
    {#if showTooltip}
        <div
            class="fixed z-[100] w-max max-w-[calc(100vw-1rem)] px-3 py-2 text-xs font-normal leading-4 text-white bg-gray-800 rounded-lg shadow-lg whitespace-normal break-words pointer-events-none {positionClasses[currentPosition]}"
            style={`top: ${tooltipTop}px; left: ${tooltipLeft}px;`}
            role="tooltip"
        >
            {text}
            <div
                class="absolute w-0 h-0 border-4 {arrowClasses[currentPosition]}"
            ></div>
        </div>
    {/if}
</div>
