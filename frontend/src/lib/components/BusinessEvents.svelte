<script lang="ts">
    import { getBusinessEvents, getBusinessEventDomains, updateBusinessEvent } from '$lib/api';
    import type { BusinessEvent, BusinessEventType } from '$lib/types';
    import { onMount } from 'svelte';
    import Icon from '@iconify/svelte';
    import CreateEventModal from './CreateEventModal.svelte';
    import AnnotateEventModal from './AnnotateEventModal.svelte';
    import EventCard from './EventCard.svelte';
    import SevenWsForm from './SevenWsForm.svelte';

    let events = $state<BusinessEvent[]>([]);
    let domains = $state<string[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let selectedFilter = $state<BusinessEventType | 'all'>('all');
    let selectedDomain = $state<string | null>(null);

    // Helper function to convert domain to title case
    function toTitleCase(str: string): string {
        return str.trim().charAt(0).toUpperCase() + str.trim().slice(1).toLowerCase();
    }
    let showCreateModal = $state(false);
    let showEditModal = $state(false);
    let showAnnotateModal = $state(false);
    let showSevenWsForm = $state(false);
    let showViewSevenWs = $state(false);
    let editingEvent = $state<BusinessEvent | null>(null);
    let annotatingEvent = $state<BusinessEvent | null>(null);
    let sevenWsEvent = $state<BusinessEvent | null>(null);

    // Filter events based on selected type and domain (combined filters)
    let filteredEvents = $derived.by(() => {
        let result = events;

        // Apply type filter
        if (selectedFilter !== 'all') {
            result = result.filter((event) => event.type === selectedFilter);
        }

        // Apply domain filter
        if (selectedDomain !== null) {
            if (selectedDomain === 'unassigned') {
                result = result.filter((event) => !event.domain);
            } else {
                result = result.filter((event) => event.domain === selectedDomain);
            }
        }

        return result;
    });

    onMount(async () => {
        try {
            loading = true;
            error = null;
            // Load events and domains separately to handle partial failures gracefully
            try {
                events = await getBusinessEvents();
            } catch (e) {
                const errorMessage = e instanceof Error ? e.message : String(e);
                const statusCode = (e as any)?.status;
                
                // Check for specific error types by status code first, then message
                if (statusCode === 403 || errorMessage.includes('403') || errorMessage.includes('feature_disabled') || errorMessage.includes('disabled')) {
                    error = 'Business events feature is disabled. Enable it in trellis.yml by setting business_events.enabled: true';
                } else if (statusCode === 400 || errorMessage.includes('400') || errorMessage.includes('configuration')) {
                    error = 'Configuration error. Please check your trellis.yml file.';
                } else if (statusCode === 404 || errorMessage.includes('404') || errorMessage.includes('not found')) {
                    error = 'Business events file not found. Create your first event to get started.';
                } else if (statusCode === 500 || errorMessage.includes('500') || errorMessage.includes('parse') || errorMessage.includes('YAML')) {
                    error = 'Invalid business events file format. Please check the file or contact support.';
                } else {
                    error = 'Failed to load business events. Please try again later.';
                }
                console.error('Error loading business events:', e);
                // Still try to load domains even if events fail
                events = [];
            }

            // Load domains separately - if this fails, we can still show events
            try {
                domains = await getBusinessEventDomains();
            } catch (e) {
                console.warn('Failed to load domain suggestions:', e);
                domains = []; // Continue without domain suggestions
            }
        } catch (e) {
            // Fallback error handling
            const errorMessage = e instanceof Error ? e.message : 'Failed to load business events';
            error = errorMessage.includes('403') || errorMessage.includes('disabled')
                ? 'Business events feature is disabled. Enable it in trellis.yml by setting business_events.enabled: true'
                : 'Failed to load business events. Please try again later.';
            console.error('Error loading business events:', e);
            events = [];
            domains = [];
        } finally {
            loading = false;
        }
    });

    async function reloadEvents() {
        try {
            error = null;
            // Load events and domains separately to handle partial failures
            try {
                events = await getBusinessEvents();
            } catch (e) {
                const errorMessage = e instanceof Error ? e.message : String(e);
                const statusCode = (e as any)?.status;
                
                // Check for specific error types
                if (statusCode === 403 || errorMessage.includes('403') || errorMessage.includes('feature_disabled') || errorMessage.includes('disabled')) {
                    error = 'Business events feature is disabled. Enable it in trellis.yml by setting business_events.enabled: true';
                } else if (statusCode === 400 || errorMessage.includes('400') || errorMessage.includes('configuration')) {
                    error = 'Configuration error. Please check your trellis.yml file.';
                } else if (statusCode === 404 || errorMessage.includes('404') || errorMessage.includes('not found')) {
                    error = 'Business events file not found. Create your first event to get started.';
                } else if (statusCode === 500 || errorMessage.includes('500') || errorMessage.includes('parse') || errorMessage.includes('YAML')) {
                    error = 'Invalid business events file format. Please check the file or contact support.';
                } else {
                    error = 'Failed to reload events. Please try again.';
                }
                console.error('Error reloading events:', e);
                events = [];
            }

            // Load domains separately
            try {
                domains = await getBusinessEventDomains();
            } catch (e) {
                console.warn('Failed to reload domain suggestions:', e);
                domains = [];
            }
        } catch (e) {
            console.error('Error reloading events:', e);
            const errorMessage = e instanceof Error ? e.message : 'Failed to reload events';
            error = errorMessage.includes('403') || errorMessage.includes('disabled')
                ? 'Business events feature is disabled. Enable it in trellis.yml by setting business_events.enabled: true'
                : 'Failed to reload events. Please try again.';
            events = [];
            domains = [];
        }
    }

    function handleCreateEvent() {
        showCreateModal = true;
    }

    function handleModalClose() {
        showCreateModal = false;
        reloadEvents();
    }

    function handleAnnotate(event: BusinessEvent) {
        // Use SevenWsForm for events with 7 Ws structure, fall back to old annotation modal
        if (event.seven_ws && Object.keys(event.seven_ws).some(key => event.seven_ws![key as keyof typeof event.seven_ws].length > 0)) {
            sevenWsEvent = event;
            showSevenWsForm = true;
        } else {
            annotatingEvent = event;
            showAnnotateModal = true;
        }
    }

    function handleViewSevenWs(event: BusinessEvent) {
        sevenWsEvent = event;
        showViewSevenWs = true;
    }

    function handleAnnotateModalClose() {
        showAnnotateModal = false;
        annotatingEvent = null;
        reloadEvents();
    }

    async function handleSevenWsSave(updatedEvent: BusinessEvent) {
        try {
            error = null;
            // Call updateBusinessEvent with seven_ws data
            await updateBusinessEvent(updatedEvent.id, {
                seven_ws: updatedEvent.seven_ws
            });
            showSevenWsForm = false;
            sevenWsEvent = null;
            reloadEvents();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Failed to save 7 Ws";
            // Handle 7 Ws specific errors
            if (errorMessage.includes('seven_w_type') || errorMessage.includes('Invalid seven_w_type')) {
                error = "Invalid 7 Ws category. Please check your entries.";
            } else if (errorMessage.includes('Duplicate entry IDs') || errorMessage.includes('duplicate')) {
                error = "Duplicate entries detected. Please check for duplicate entries.";
            } else if (errorMessage.includes('400') || errorMessage.includes('validation')) {
                error = "Invalid 7 Ws data. Please check your entries.";
            } else {
                error = errorMessage;
            }
            console.error('Error saving 7 Ws:', e);
        }
    }

    function handleSevenWsCancel() {
        showSevenWsForm = false;
        sevenWsEvent = null;
    }

    function handleViewSevenWsClose() {
        showViewSevenWs = false;
        sevenWsEvent = null;
    }

    function handleGenerateEntities(event: BusinessEvent) {
        console.log('Generate entities for event:', event);
        // TODO: Implement entity generation
    }

    function handleEdit(event: BusinessEvent) {
        editingEvent = event;
        showEditModal = true;
    }

    function handleEditModalClose() {
        showEditModal = false;
        editingEvent = null;
        reloadEvents();
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
                <div class="flex items-center gap-4 flex-wrap">
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

                    <div class="flex items-center gap-2">
                        <span class="text-sm font-medium text-gray-700">Filter by domain:</span>
                    </div>
                    <select
                        bind:value={selectedDomain}
                        class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                        <option value={null}>All Domains</option>
                        {#each domains as domain}
                            <option value={domain}>{toTitleCase(domain)}</option>
                        {/each}
                        <option value="unassigned">Unassigned</option>
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
                <div class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                    {#each filteredEvents as event (event.id)}
                        <EventCard
                            {event}
                            onAnnotate={handleAnnotate}
                            onGenerateEntities={handleGenerateEntities}
                            onEdit={handleEdit}
                            onDelete={reloadEvents}
                            onViewSevenWs={handleViewSevenWs}
                        />
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

    <!-- Edit Event Modal -->
    {#if showEditModal && editingEvent}
        <CreateEventModal
            open={showEditModal}
            onSave={handleEditModalClose}
            onCancel={() => { showEditModal = false; editingEvent = null; }}
            event={editingEvent}
        />
    {/if}

    <!-- Annotate Event Modal (Legacy) -->
    <AnnotateEventModal
        open={showAnnotateModal}
        event={annotatingEvent}
        onSave={handleAnnotateModalClose}
        onCancel={() => { showAnnotateModal = false; annotatingEvent = null; }}
    />

    <!-- 7 Ws Form Modal (Edit) -->
    {#if showSevenWsForm && sevenWsEvent}
        <SevenWsForm
            event={sevenWsEvent}
            onSave={handleSevenWsSave}
            onCancel={handleSevenWsCancel}
        />
    {/if}

    <!-- 7 Ws Form Modal (View - Read-only) -->
    {#if showViewSevenWs && sevenWsEvent}
        <SevenWsForm
            event={sevenWsEvent}
            onSave={handleSevenWsSave}
            onCancel={handleViewSevenWsClose}
        />
    {/if}
</div>
