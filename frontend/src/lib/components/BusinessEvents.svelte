<script lang="ts">
    import { getBusinessEvents } from '$lib/api';
    import type { BusinessEvent, BusinessEventType } from '$lib/types';
    import { onMount } from 'svelte';
    import Icon from '@iconify/svelte';
    import CreateEventModal from './CreateEventModal.svelte';

    let events = $state<BusinessEvent[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let selectedFilter = $state<BusinessEventType | 'all'>('all');
    let showCreateModal = $state(false);

    // Filter events based on selected type
    let filteredEvents = $derived(
        selectedFilter === 'all'
            ? events
            : events.filter((event) => event.type === selectedFilter)
    );

    onMount(async () => {
        try {
            loading = true;
            error = null;
            events = await getBusinessEvents();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : 'Failed to load business events';
            // Provide user-friendly error message
            if (errorMessage.includes('404') || errorMessage.includes('not found')) {
                error = 'Business events file not found. Create your first event to get started.';
            } else if (errorMessage.includes('500') || errorMessage.includes('parse') || errorMessage.includes('YAML')) {
                error = 'Invalid business events file format. Please check the file or contact support.';
            } else {
                error = 'Failed to load business events. Please try again later.';
            }
            console.error('Error loading business events:', e);
        } finally {
            loading = false;
        }
    });

    async function reloadEvents() {
        try {
            error = null;
            events = await getBusinessEvents();
        } catch (e) {
            console.error('Error reloading events:', e);
            const errorMessage = e instanceof Error ? e.message : 'Failed to reload events';
            // Provide user-friendly error message
            if (errorMessage.includes('500') || errorMessage.includes('parse') || errorMessage.includes('YAML')) {
                error = 'Invalid business events file format. Please check the file or contact support.';
            } else {
                error = 'Failed to reload events. Please try again.';
            }
        }
    }

    function handleCreateEvent() {
        showCreateModal = true;
    }

    function handleModalClose() {
        showCreateModal = false;
        // Reload events after modal closes (assuming event was created)
        reloadEvents();
    }

    function getTypeBadgeColor(type: BusinessEventType): string {
        switch (type) {
            case 'discrete':
                return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'evolving':
                return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'recurring':
                return 'bg-purple-100 text-purple-800 border-purple-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    }
</script>

<div class="h-full w-full overflow-auto bg-gray-50">
    {#if loading}
        <div class="flex items-center justify-center h-full">
            <div class="text-center">
                <div class="w-8 h-8 animate-spin border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                <p class="text-sm text-gray-600">Loading business events...</p>
            </div>
        </div>
    {:else if error}
        <div class="flex items-center justify-center h-full">
            <div class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-red-200 shadow-xl text-center max-w-md mx-4">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Icon icon="lucide:alert-circle" class="w-8 h-8 text-red-500" />
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-2">Error Loading Business Events</h3>
                <p class="text-slate-600 mb-4">{error}</p>
            </div>
        </div>
    {:else}
        <div class="p-6">
            <!-- Header -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h2 class="text-xl font-bold text-gray-800">Business Events</h2>
                        <p class="text-sm text-gray-600 mt-1">
                            Document and annotate business events during the conception phase of dimensional data modeling.
                            Capture events like "customer buys product" and classify them using BEAM* methodology.
                        </p>
                    </div>
                    <button
                        onclick={handleCreateEvent}
                        class="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                    >
                        <Icon icon="lucide:plus" class="w-4 h-4" />
                        Add Event
                    </button>
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:filter" class="w-4 h-4 text-gray-500" />
                        <span class="text-sm font-medium text-gray-700">Filter by type:</span>
                    </div>
                    <select
                        bind:value={selectedFilter}
                        class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                        <option value="all">All</option>
                        <option value="discrete">Discrete</option>
                        <option value="evolving">Evolving</option>
                        <option value="recurring">Recurring</option>
                    </select>
                </div>
            </div>

            <!-- Event List -->
            {#if filteredEvents.length === 0}
                <div class="flex items-center justify-center min-h-[400px]">
                    <div class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-amber-200 shadow-xl text-center max-w-md mx-4">
                        <div class="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Icon icon="lucide:calendar-check" class="w-8 h-8 text-amber-600" />
                        </div>
                        <h3 class="text-xl font-bold text-slate-800 mb-2">No Business Events</h3>
                        <p class="text-slate-600 mb-4">
                            Get started by creating your first business event. Business events help you document
                            business processes before designing your dimensional data model.
                        </p>
                        <div class="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 text-left mt-4">
                            <strong class="block mb-1">Example event:</strong>
                            <p class="text-amber-900">
                                "customer buys product" - a discrete event that can be annotated with dimensions
                                (customer, product) and facts (buys) to generate dimensional entities.
                            </p>
                        </div>
                        <button
                            onclick={handleCreateEvent}
                            class="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                        >
                            Create Your First Event
                        </button>
                    </div>
                </div>
            {:else}
                <div class="space-y-4">
                    {#each filteredEvents as event (event.id)}
                        <!-- Event Card (basic version - will be replaced by EventCard component in Stream C) -->
                        <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 hover:shadow-md transition-shadow">
                            <div class="flex items-start justify-between mb-2">
                                <div class="flex-1">
                                    <div class="flex items-center gap-2 mb-2">
                                        <span
                                            class="px-2 py-1 text-xs font-medium rounded border {getTypeBadgeColor(event.type)}"
                                        >
                                            {event.type}
                                        </span>
                                        {#if event.derived_entities.length > 0}
                                            <span class="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800 border border-green-200">
                                                <Icon icon="lucide:check" class="w-3 h-3 inline mr-1" />
                                                Entities Generated
                                            </span>
                                        {/if}
                                    </div>
                                    <p class="text-gray-800 mb-2">{event.text}</p>
                                    {#if event.annotations.length > 0}
                                        <div class="flex flex-wrap gap-2 mt-2">
                                            {#each event.annotations as annotation}
                                                <span
                                                    class="px-2 py-1 text-xs rounded {annotation.type === 'dimension'
                                                        ? 'bg-blue-100 text-blue-800'
                                                        : 'bg-green-100 text-green-800'}"
                                                >
                                                    {annotation.text} ({annotation.type})
                                                </span>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                                <div class="flex items-center gap-2 ml-4">
                                    <button
                                        class="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                        title="Annotate"
                                    >
                                        <Icon icon="lucide:tag" class="w-4 h-4" />
                                    </button>
                                    <button
                                        class="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                        title="Generate Entities"
                                        disabled={event.annotations.length === 0}
                                    >
                                        <Icon icon="lucide:sparkles" class="w-4 h-4" />
                                    </button>
                                    <button
                                        class="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                        title="Edit"
                                    >
                                        <Icon icon="lucide:edit" class="w-4 h-4" />
                                    </button>
                                    <button
                                        class="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                                        title="Delete"
                                    >
                                        <Icon icon="lucide:trash" class="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}

    <!-- Create Event Modal -->
    <CreateEventModal
        open={showCreateModal}
        onSave={handleModalClose}
        onCancel={() => { showCreateModal = false; }}
    />
</div>
