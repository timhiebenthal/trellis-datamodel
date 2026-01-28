<script lang="ts">
    import Icon from "@iconify/svelte";
    import { createBusinessEventProcess } from "$lib/api";
    import type { BusinessEventType, CreateProcessRequest } from "$lib/types";

    type Props = {
        open: boolean;
        eventIds: string[];
        onSave: () => void;
        onCancel: () => void;
        domains?: string[];
    };

    let { open, eventIds, onSave, onCancel, domains = [] }: Props = $props();

    // Form state
    let processName = $state("");
    let processType = $state<BusinessEventType>("discrete");
    let domain = $state("");
    let loading = $state(false);
    let error = $state<string | null>(null);

    // Character limit
    const MAX_NAME_LENGTH = 200;
    let characterCount = $derived(processName.length);
    let remainingChars = $derived(MAX_NAME_LENGTH - characterCount);

    let isValid = $derived.by(() => {
        if (processName.trim().length === 0) return false;
        if (processName.length > MAX_NAME_LENGTH) return false;
        if (!processType) return false;
        if (domain.trim().length === 0) return false;
        if (loading) return false;
        if (eventIds.length < 2) return false;
        return true;
    });

    // Reset form when modal opens/closes
    $effect(() => {
        if (open) {
            processName = "";
            processType = "discrete";
            domain = "";
            error = null;
            loading = false;
        }
    });

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onCancel();
        } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            handleSave();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    async function handleSave() {
        // Validate name length before API call
        if (processName.length > MAX_NAME_LENGTH) {
            error = `Process name cannot exceed ${MAX_NAME_LENGTH} characters`;
            return;
        }

        if (!isValid) return;

        error = null;
        loading = true;

        try {
            const request: CreateProcessRequest = {
                name: processName.trim(),
                type: processType,
                domain: domain.trim(),
                event_ids: eventIds,
            };

            await createBusinessEventProcess(request);

            // Success: close modal and refresh list
            onSave();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Failed to create process";
            // Provide user-friendly error messages
            if (errorMessage.includes("400") || errorMessage.includes("validation")) {
                error = "Invalid process data. Please check your input and try again.";
            } else if (errorMessage.includes("404") || errorMessage.includes("not found")) {
                error = "One or more events not found. Please refresh and try again.";
            } else if (errorMessage.includes("already attached")) {
                error = "One or more events are already in another process.";
            } else if (errorMessage.includes("500") || errorMessage.includes("server")) {
                error = "Server error. Please try again later.";
            } else {
                error = errorMessage;
            }
        } finally {
            loading = false;
        }
    }

    function handleCancel() {
        error = null;
        loading = false;
        onCancel();
    }
</script>

{#if open}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center backdrop-blur-sm"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="process-modal-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
        >
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <h2 id="process-modal-title" class="text-xl font-semibold text-gray-900">
                    Group into Process
                </h2>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    onclick={handleCancel}
                    aria-label="Close"
                    disabled={loading}
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            <!-- Form -->
            <div class="space-y-4">
                <!-- Info about selected events -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
                    <div class="flex items-start gap-2">
                        <Icon icon="lucide:info" class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div class="text-sm text-blue-800">
                            <p class="font-medium mb-1">Grouping {eventIds.length} event{eventIds.length !== 1 ? 's' : ''}</p>
                            <p class="text-blue-700">Create a process to consolidate these events with unified annotations.</p>
                        </div>
                    </div>
                </div>

                <!-- Process Name -->
                <div>
                    <label for="process-name" class="block text-sm font-medium text-gray-700 mb-2">
                        Process Name
                    </label>
                    <input
                        id="process-name"
                        type="text"
                        bind:value={processName}
                        maxlength={MAX_NAME_LENGTH}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        placeholder="e.g., Customer Order Fulfillment"
                        disabled={loading}
                    />
                    <div class="flex items-center justify-between mt-1">
                        <span class="text-xs text-gray-500">
                            {remainingChars} characters remaining
                        </span>
                        {#if processName.trim().length === 0}
                            <span class="text-xs text-red-600">Process name is required</span>
                        {:else if processName.length > MAX_NAME_LENGTH}
                            <span class="text-xs text-red-600">Process name cannot exceed {MAX_NAME_LENGTH} characters</span>
                        {/if}
                    </div>
                </div>

                <!-- Process Type -->
                <div>
                    <div class="flex items-center gap-2 mb-2">
                        <label for="process-type" class="block text-sm font-medium text-gray-700">
                            Process Type
                        </label>
                        <div class="group relative">
                            <Icon
                                icon="lucide:help-circle"
                                class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                            />
                            <!-- Tooltip -->
                            <div
                                class="absolute left-0 bottom-full mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10"
                            >
                                <div class="space-y-2">
                                    <div>
                                        <strong class="text-blue-300">Discrete:</strong> One-time
                                        events grouped together (e.g., "order fulfillment")
                                    </div>
                                    <div>
                                        <strong class="text-yellow-300">Evolving:</strong> Events
                                        that change over time (e.g., "sales opportunity funnel")
                                    </div>
                                    <div>
                                        <strong class="text-purple-300">Recurring:</strong> Events
                                        that repeat (e.g., "monthly account statement")
                                    </div>
                                </div>
                                <div class="absolute left-4 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                            </div>
                        </div>
                    </div>
                    <select
                        id="process-type"
                        bind:value={processType}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        disabled={loading}
                    >
                        <option value="discrete">Discrete</option>
                        <option value="evolving">Evolving</option>
                        <option value="recurring">Recurring</option>
                    </select>
                </div>

                <!-- Process Domain -->
                <div>
                    <label for="process-domain" class="block text-sm font-medium text-gray-700 mb-2">
                        Process Domain
                    </label>
                    <input
                        id="process-domain"
                        type="text"
                        list="domain-suggestions"
                        bind:value={domain}
                        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                        placeholder="e.g., Sales"
                        disabled={loading}
                    />
                    <datalist id="domain-suggestions">
                        {#each domains as domainOption}
                            <option value={domainOption} />
                        {/each}
                    </datalist>
                    {#if domain.trim().length === 0}
                        <span class="text-xs text-red-600 mt-1 block">Process domain is required</span>
                    {/if}
                </div>

                <!-- Error Message -->
                {#if error}
                    <div
                        class="flex items-center gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
                    >
                        <Icon icon="lucide:alert-triangle" class="w-5 h-5 flex-shrink-0" />
                        <span class="text-sm">{error}</span>
                    </div>
                {/if}

                <!-- Actions -->
                <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
                    <button
                        onclick={handleCancel}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        onclick={handleSave}
                        class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        disabled={!isValid}
                    >
                        {#if loading}
                            <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                            <span>Creating...</span>
                        {:else}
                            <Icon icon="lucide:layers" class="w-4 h-4" />
                            <span>Create Process</span>
                        {/if}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
