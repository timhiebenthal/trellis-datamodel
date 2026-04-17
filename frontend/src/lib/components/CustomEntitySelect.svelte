<script lang="ts">
    import Icon from "@iconify/svelte";

    type Option = { id: string; label: string };
    type Group = { label: string; options: Option[] };

    type Props = {
        value: string;
        groups: Group[];
        onChange: (value: string) => void;
        class?: string;
    };

    let { value, groups, onChange, class: className = "" }: Props = $props();

    let isOpen = $state(false);
    let containerRef = $state<HTMLDivElement>();

    const selectedOption = $derived(
        groups.flatMap((g) => g.options).find((o) => o.id === value)
    );

    function toggle() {
        isOpen = !isOpen;
    }

    function selectOption(id: string) {
        onChange(id);
        isOpen = false;
    }

    $effect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                isOpen = false;
            }
        }

        if (isOpen) {
            document.addEventListener("click", handleClickOutside);
        }

        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });
</script>

<div class="relative w-full {className}" bind:this={containerRef}>
    <button
        type="button"
        onclick={toggle}
        class="flex w-full min-w-[11rem] items-center justify-between rounded-lg border border-gray-200 bg-white py-2 pl-3 pr-3 text-sm font-medium text-gray-800 shadow-sm transition-colors hover:border-gray-300 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
    >
        <span class="truncate pr-4">{selectedOption?.label || "Select entity..."}</span>
        <Icon
            icon="lucide:chevron-down"
            class="h-4 w-4 shrink-0 text-gray-500 transition-transform {isOpen ? 'rotate-180' : ''}"
        />
    </button>

    {#if isOpen}
        <div
            class="absolute left-0 z-50 mt-1 max-h-60 w-full min-w-[14rem] overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5"
        >
            <ul role="listbox" class="focus:outline-none">
                {#each groups as group}
                    {#if group.options.length > 0}
                        <li
                            class="bg-gray-50/80 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-500"
                        >
                            {group.label}
                        </li>
                        {#each group.options as opt}
                            {@const isSelected = opt.id === value}
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <li
                                role="option"
                                aria-selected={isSelected}
                                class="relative cursor-pointer select-none py-2 pl-3 pr-9 text-sm text-gray-900 hover:bg-primary-50 hover:text-primary-700 {isSelected
                                    ? 'bg-primary-50 font-medium text-primary-700'
                                    : ''}"
                                onclick={() => selectOption(opt.id)}
                            >
                                <span class="block truncate">{opt.label}</span>
                                {#if isSelected}
                                    <span
                                        class="absolute inset-y-0 right-0 flex items-center pr-3 text-primary-600"
                                    >
                                        <Icon icon="lucide:check" class="h-4 w-4" />
                                    </span>
                                {/if}
                            </li>
                        {/each}
                    {/if}
                {/each}
            </ul>
        </div>
    {/if}
</div>
