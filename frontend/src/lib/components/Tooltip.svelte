<script lang="ts">
    let { text, position = 'top' } = $props<{
        text: string;
        position?: 'top' | 'bottom' | 'left' | 'right';
    }>();

    let showTooltip = $state(false);

    function handleMouseEnter() {
        showTooltip = true;
    }

    function handleMouseLeave() {
        showTooltip = false;
    }

    const positionClasses = {
        top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
        bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
        left: 'right-full top-1/2 -translate-y-1/2 mr-2',
        right: 'left-full top-1/2 -translate-y-1/2 ml-2',
    };

    const arrowClasses = {
        top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 border-l-transparent border-r-transparent border-b-transparent',
        bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 border-l-transparent border-r-transparent border-t-transparent',
        left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 border-t-transparent border-b-transparent border-r-transparent',
        right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 border-t-transparent border-b-transparent border-l-transparent',
    };
</script>

<div
    class="relative inline-flex items-center"
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
>
    <slot />
    {#if showTooltip}
        <div
            class="absolute z-50 px-3 py-2 text-xs font-normal text-white bg-gray-800 rounded-lg shadow-lg whitespace-normal w-80 max-w-lg pointer-events-none {positionClasses[position]}"
            role="tooltip"
        >
            {text}
            <div
                class="absolute w-0 h-0 border-4 {arrowClasses[position]}"
            ></div>
        </div>
    {/if}
</div>
