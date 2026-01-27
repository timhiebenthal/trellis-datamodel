<script lang="ts">
import {
    getBusinessEvents,
    getBusinessEventDomains,
    updateBusinessEvent,
    getBusinessEventProcesses,
    resolveBusinessEventProcess,
    updateBusinessEventProcess,
} from '$lib/api';
import type {
    BusinessEvent,
    BusinessEventType,
    BusinessEventProcess,
    BusinessEventAnnotations,
} from '$lib/types';
    import { onMount } from 'svelte';
    import Icon from '@iconify/svelte';
    import CreateEventModal from './CreateEventModal.svelte';
    import CollapseChevron from './CollapseChevron.svelte';
    import EventCard from './EventCard.svelte';
    import ProcessRow from './ProcessRow.svelte';
    import ProcessEditModal from './ProcessEditModal.svelte';
    import SevenWsForm from './SevenWsForm.svelte';
    import GenerateEntitiesDialog from './GenerateEntitiesDialog.svelte';
    import ProcessGroupModal from './ProcessGroupModal.svelte';

    let events = $state<BusinessEvent[]>([]);
    let processes = $state<BusinessEventProcess[]>([]);
    let domains = $state<string[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let selectedFilter = $state<BusinessEventType | 'all'>('all');
    let selectedDomain = $state<string | null>(null);
    let selectedProcess = $state<string | null>(null);
    
    // Multi-select state
    let selectedEventIds = $state<Set<string>>(new Set());
    let showProcessGroupModal = $state(false);

const UNASSIGNED_DOMAIN_KEY = 'unassigned';

type ProcessGroup = {
    process: BusinessEventProcess;
    events: BusinessEvent[];
};

type DomainGroup = {
    domainKey: string;
    domainLabel: string;
    processes: ProcessGroup[];
    ungroupedEvents: BusinessEvent[];
    totalEvents: number;
};

let domainCollapseState = $state<Record<string, boolean>>({});
let processCollapseState = $state<Record<string, boolean>>({});
let processActionError = $state<string | null>(null);
let showProcessSevenWsForm = $state(false);
let processUnderAnnotation = $state<BusinessEventProcess | null>(null);
let processAnnotationEvent = $state<BusinessEvent | null>(null);
let showProcessEditModal = $state(false);
let processUnderEdit = $state<BusinessEventProcess | null>(null);
let dragState = $state<{ eventId: string; processId: string | null } | null>(null);
let dragOverEventId = $state<string | null>(null);
let dragOverProcessId = $state<string | null>(null);
let dragOverUngroupedDomainKey = $state<string | null>(null);
let dropIndicatorPosition = $state<'before' | 'after' | null>(null);

    // Helper function to convert domain to title case
    function toTitleCase(str: string): string {
        return str.trim().charAt(0).toUpperCase() + str.trim().slice(1).toLowerCase();
    }
    let showCreateModal = $state(false);
    let showEditModal = $state(false);
    let editEvent = $state<BusinessEvent | null>(null);
    let showSevenWsForm = $state(false);
    let showGenerateEntitiesDialog = $state(false);
    let sevenWsEvent = $state<BusinessEvent | null>(null);
    let generateEntitiesEvent = $state<BusinessEvent | null>(null);

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

        // Apply process filter
        if (selectedProcess !== null) {
            if (selectedProcess === 'ungrouped') {
                result = result.filter((event) => !event.process_id);
            } else {
                result = result.filter((event) => event.process_id === selectedProcess);
            }
        }

        // Clear selection if filtered events don't include selected items
        const filteredIds = new Set(result.map(e => e.id));
        const stillSelected = Array.from(selectedEventIds).filter(id => filteredIds.has(id));
        if (stillSelected.length !== selectedEventIds.size) {
            selectedEventIds = new Set(stillSelected);
        }

        return result;
    });

    function getDomainLabel(domainKey: string) {
        return domainKey === UNASSIGNED_DOMAIN_KEY ? 'Unassigned' : toTitleCase(domainKey);
    }

    const activeProcesses = $derived.by(() =>
        processes.filter((process) => !process.resolved_at)
    );
    const hasActiveProcesses = $derived(() => activeProcesses.length > 0);

    const domainGroups = $derived.by(() => {
        const processLookup = new Map(activeProcesses.map((proc) => [proc.id, proc]));
        const eventsById = new Map(filteredEvents.map((event) => [event.id, event]));

        const groupsMap = new Map<string, DomainGroup>();

        function ensureGroup(key: string): DomainGroup {
            const existing = groupsMap.get(key);
            if (existing) return existing;
            const group: DomainGroup = {
                domainKey: key,
                domainLabel: getDomainLabel(key),
                processes: [],
                ungroupedEvents: [],
                totalEvents: 0,
            };
            groupsMap.set(key, group);
            return group;
        }

        activeProcesses.forEach((process) => {
            const domainKey = process.domain ?? UNASSIGNED_DOMAIN_KEY;
            const eventsForProcess = process.event_ids
                .map((eventId) => eventsById.get(eventId))
                .filter((event): event is BusinessEvent => Boolean(event));
            if (eventsForProcess.length === 0) {
                return;
            }
            const group = ensureGroup(domainKey);
            group.processes.push({ process, events: eventsForProcess });
        });

        filteredEvents.forEach((event) => {
            const domainKey = event.domain ?? UNASSIGNED_DOMAIN_KEY;
            if (event.process_id && processLookup.has(event.process_id)) {
                return;
            }
            const group = ensureGroup(domainKey);
            group.ungroupedEvents.push(event);
        });

        const groups = Array.from(groupsMap.values())
            .map((group) => ({
                ...group,
                totalEvents:
                    group.ungroupedEvents.length +
                    group.processes.reduce((sum, procGroup) => sum + procGroup.events.length, 0),
            }))
            .filter((group) => group.totalEvents > 0)
            .sort((a, b) => a.domainLabel.localeCompare(b.domainLabel));

        return groups;
    });

    function toggleDomainCollapse(domainKey: string) {
        domainCollapseState = {
            ...domainCollapseState,
            [domainKey]: !isDomainExpanded(domainKey),
        };
    }

    function isDomainExpanded(domainKey: string) {
        return domainCollapseState[domainKey] !== false;
    }

    function toggleProcessCollapse(processId: string) {
        processCollapseState = {
            ...processCollapseState,
            [processId]: !isProcessExpanded(processId),
        };
    }

    function isProcessExpanded(processId: string) {
        return processCollapseState[processId] !== false;
    }

    function createEmptyAnnotations(): BusinessEventAnnotations {
        return {
            who: [],
            what: [],
            when: [],
            where: [],
            how: [],
            how_many: [],
            why: [],
        };
    }

    function mapProcessToEvent(process: BusinessEventProcess): BusinessEvent {
        return {
            id: process.id,
            text: process.name,
            type: process.type,
            domain: process.domain ?? undefined,
            created_at: process.created_at,
            updated_at: process.updated_at,
            annotations: process.annotations_superset ?? createEmptyAnnotations(),
            derived_entities: [],
        };
    }

    function handleProcessAnnotate(process: BusinessEventProcess) {
        processUnderAnnotation = process;
        processAnnotationEvent = mapProcessToEvent(process);
        showProcessSevenWsForm = true;
    }

    async function handleProcessSevenWsSave(updatedEvent: BusinessEvent) {
        if (!processUnderAnnotation) return;
        try {
            processActionError = null;
            await updateBusinessEventProcess(processUnderAnnotation.id, {
                annotations_superset: updatedEvent.annotations,
            });
            showProcessSevenWsForm = false;
            processUnderAnnotation = null;
            processAnnotationEvent = null;
            await reloadEvents();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : 'Failed to save process annotations';
            processActionError = errorMessage;
        }
    }

    function handleProcessSevenWsCancel() {
        showProcessSevenWsForm = false;
        processUnderAnnotation = null;
        processAnnotationEvent = null;
    }

    function handleProcessEdit(process: BusinessEventProcess) {
        processUnderEdit = process;
        showProcessEditModal = true;
    }

    function handleProcessEditCancel() {
        showProcessEditModal = false;
        processUnderEdit = null;
    }

    function handleProcessEditSave() {
        showProcessEditModal = false;
        processUnderEdit = null;
        reloadEvents();
    }

    function handleProcessCanvasLink(process: BusinessEventProcess, derivedIds?: string[]) {
        const params: string[] = [];
        if (derivedIds && derivedIds.length > 0) {
            const entityParam = derivedIds.map(encodeURIComponent).join(',');
            params.push(`entities=${entityParam}`);
        }
        params.push(`processId=${encodeURIComponent(process.id)}`);
        params.push(`processName=${encodeURIComponent(process.name)}`);

        const canvasUrl = `/canvas?${params.join('&')}`;

        if (typeof window !== 'undefined') {
            window.open(canvasUrl, '_blank');
        }
    }

    async function handleProcessResolve(processId: string) {
        try {
            processActionError = null;
            await resolveBusinessEventProcess(processId);
            await reloadEvents();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : 'Failed to resolve process';
            processActionError = errorMessage;
        }
    }

    function reorderIds(ids: string[], fromId: string, toId: string): string[] {
        const fromIndex = ids.indexOf(fromId);
        const toIndex = ids.indexOf(toId);
        if (fromIndex === -1 || toIndex === -1 || fromIndex === toIndex) {
            return ids;
        }
        const next = [...ids];
        const [moved] = next.splice(fromIndex, 1);
        next.splice(toIndex, 0, moved);
        return next;
    }

    function handleEventDragStart(
        event: BusinessEvent,
        processId: string | null,
        dragEvent: DragEvent
    ) {
        dragState = { eventId: event.id, processId };
        dragOverEventId = null;
        dragOverProcessId = null;
        dragOverUngroupedDomainKey = null;
        dropIndicatorPosition = null;
        if (dragEvent.dataTransfer) {
            dragEvent.dataTransfer.effectAllowed = 'move';
            dragEvent.dataTransfer.setData('text/plain', event.id);
        }
    }

    function handleEventDragOver(event: BusinessEvent, processId: string, dragEvent: DragEvent, processGroup: ProcessGroup) {
        // Allow reordering within the same process - only reject if dragging onto itself or no drag state
        if (!dragState || dragState.eventId === event.id) {
            return;
        }
        // Only allow drag-over if both events are in the same process
        if (dragState.processId !== processId) {
            return;
        }
        dragEvent.preventDefault();
        dragOverEventId = event.id;
        dragOverProcessId = processId;
        dragOverUngroupedDomainKey = null;
        
        // Determine if we should show indicator before or after this event
        const draggedIndex = processGroup.process.event_ids.indexOf(dragState.eventId);
        const targetIndex = processGroup.process.event_ids.indexOf(event.id);
        dropIndicatorPosition = draggedIndex < targetIndex ? 'after' : 'before';
        
        if (dragEvent.dataTransfer) {
            dragEvent.dataTransfer.dropEffect = 'move';
        }
    }

    async function handleEventDrop(
        event: BusinessEvent,
        processGroup: ProcessGroup,
        dragEvent: DragEvent
    ) {
        if (!dragState || dragState.processId !== processGroup.process.id) {
            return;
        }
        dragEvent.preventDefault();
        const fromId = dragState.eventId;
        const toId = event.id;
        dragState = null;
        dragOverEventId = null;
        dragOverProcessId = null;
        dragOverUngroupedDomainKey = null;
        dropIndicatorPosition = null;

        if (fromId === toId) {
            return;
        }

        const currentOrder = processGroup.process.event_ids;
        const nextOrder = reorderIds(currentOrder, fromId, toId);
        if (nextOrder.join('|') === currentOrder.join('|')) {
            return;
        }

        try {
            processActionError = null;
            await updateBusinessEventProcess(processGroup.process.id, { event_ids: nextOrder });
            await reloadEvents();
        } catch (e) {
            const errorMessage =
                e instanceof Error ? e.message : 'Failed to reorder process events';
            processActionError = errorMessage;
        }
    }

    function handleEventDragEnd() {
        dragState = null;
        dragOverEventId = null;
        dragOverProcessId = null;
        dragOverUngroupedDomainKey = null;
        dropIndicatorPosition = null;
    }

    function handleProcessDragOver(processId: string, dragEvent: DragEvent) {
        if (!dragState) {
            return;
        }
        if (dragState.processId === processId) {
            return;
        }
        dragEvent.preventDefault();
        dragOverProcessId = processId;
        dragOverUngroupedDomainKey = null;
        if (dragEvent.dataTransfer) {
            dragEvent.dataTransfer.dropEffect = 'move';
        }
    }

    async function handleProcessDrop(processGroup: ProcessGroup, dragEvent: DragEvent) {
        if (!dragState) {
            return;
        }
        dragEvent.preventDefault();
        const { eventId, processId: sourceProcessId } = dragState;
        const targetProcessId = processGroup.process.id;
        dragState = null;
        dragOverEventId = null;
        dragOverProcessId = null;
        dragOverUngroupedDomainKey = null;

        if (sourceProcessId === targetProcessId) {
            return;
        }

        try {
            processActionError = null;
            if (sourceProcessId) {
                const sourceProcess = processes.find((proc) => proc.id === sourceProcessId);
                if (sourceProcess) {
                    const nextSourceIds = sourceProcess.event_ids.filter((id) => id !== eventId);
                    if (nextSourceIds.length > 0) {
                        await updateBusinessEventProcess(sourceProcessId, { event_ids: nextSourceIds });
                    } else {
                        await resolveBusinessEventProcess(sourceProcessId);
                    }
                }
            }

            const targetProcess = processes.find((proc) => proc.id === targetProcessId);
            const targetIds = targetProcess?.event_ids ?? [];
            if (!targetIds.includes(eventId)) {
                await updateBusinessEventProcess(targetProcessId, {
                    event_ids: [...targetIds, eventId],
                });
            }
            await reloadEvents();
        } catch (e) {
            const errorMessage =
                e instanceof Error ? e.message : 'Failed to move event into process';
            processActionError = errorMessage;
        }
    }

    function handleUngroupedDragOver(domainKey: string, dragEvent: DragEvent) {
        if (!dragState) {
            return;
        }
        if (!dragState.processId) {
            return;
        }
        dragEvent.preventDefault();
        dragOverUngroupedDomainKey = domainKey;
        dragOverProcessId = null;
        if (dragEvent.dataTransfer) {
            dragEvent.dataTransfer.dropEffect = 'move';
        }
    }

    async function handleUngroupedDrop(domainKey: string, dragEvent: DragEvent) {
        if (!dragState || !dragState.processId) {
            return;
        }
        dragEvent.preventDefault();
        const { eventId, processId: sourceProcessId } = dragState;
        dragState = null;
        dragOverEventId = null;
        dragOverProcessId = null;
        dragOverUngroupedDomainKey = null;

        try {
            processActionError = null;
            const sourceProcess = processes.find((proc) => proc.id === sourceProcessId);
            if (sourceProcess) {
                const nextSourceIds = sourceProcess.event_ids.filter((id) => id !== eventId);
                if (nextSourceIds.length > 0) {
                    await updateBusinessEventProcess(sourceProcessId, { event_ids: nextSourceIds });
                } else {
                    await resolveBusinessEventProcess(sourceProcessId);
                }
            }
            await reloadEvents();
        } catch (e) {
            const errorMessage =
                e instanceof Error ? e.message : 'Failed to move event out of process';
            processActionError = errorMessage;
        }
    }

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

            // Load processes separately
            try {
                processes = await getBusinessEventProcesses();
            } catch (e) {
                console.warn('Failed to load processes:', e);
                processes = []; // Continue without processes
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
            processActionError = null;
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

            // Load processes separately
            try {
                processes = await getBusinessEventProcesses();
            } catch (e) {
                console.warn('Failed to reload processes:', e);
                processes = [];
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

    function handleEditEvent(event: BusinessEvent) {
        editEvent = event;
        showEditModal = true;
    }

    function handleEditModalClose() {
        showEditModal = false;
        editEvent = null;
        reloadEvents();
    }

    function handleEditModalCancel() {
        showEditModal = false;
        editEvent = null;
    }

    function handleEditSevenWs(event: BusinessEvent) {
        sevenWsEvent = event;
        showSevenWsForm = true;
    }

    async function handleSevenWsSave(updatedEvent: BusinessEvent) {
        try {
            error = null;
            // Call updateBusinessEvent with annotations data
            await updateBusinessEvent(updatedEvent.id, {
                annotations: updatedEvent.annotations
            });
            showSevenWsForm = false;
            sevenWsEvent = null;
            reloadEvents();
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Failed to save annotations";
            // Handle annotation specific errors
            if (errorMessage.includes('annotation_type') || errorMessage.includes('Invalid annotation_type')) {
                error = "Invalid annotation category. Please check your entries.";
            } else if (errorMessage.includes('Duplicate entry IDs') || errorMessage.includes('duplicate')) {
                error = "Duplicate entries detected. Please check for duplicate entries.";
            } else if (errorMessage.includes('400') || errorMessage.includes('validation')) {
                error = "Invalid annotation data. Please check your entries.";
            } else {
                error = errorMessage;
            }
            console.error('Error saving annotations:', e);
        }
    }

    function handleSevenWsCancel() {
        showSevenWsForm = false;
        sevenWsEvent = null;
    }

    function handleGenerateEntities(event: BusinessEvent) {
        generateEntitiesEvent = event;
        showGenerateEntitiesDialog = true;
    }

    function handleGenerateEntitiesClose() {
        showGenerateEntitiesDialog = false;
        generateEntitiesEvent = null;
        reloadEvents();
    }

    // Multi-select handlers
    function handleEventSelect(eventId: string, selected: boolean) {
        if (selected) {
            selectedEventIds = new Set([...selectedEventIds, eventId]);
        } else {
            const newSet = new Set(selectedEventIds);
            newSet.delete(eventId);
            selectedEventIds = newSet;
        }
    }

    function handleSelectAll() {
        if (selectedEventIds.size === filteredEvents.length) {
            selectedEventIds = new Set();
        } else {
            selectedEventIds = new Set(filteredEvents.map(e => e.id));
        }
    }

    const selectedCount = $derived(selectedEventIds.size);
    const canGroup = $derived(selectedEventIds.size >= 2);

    function handleGroupIntoProcess() {
        if (canGroup) {
            showProcessGroupModal = true;
        }
    }

    function handleProcessGroupSave() {
        showProcessGroupModal = false;
        selectedEventIds = new Set();
        reloadEvents();
    }

    function handleProcessGroupCancel() {
        showProcessGroupModal = false;
    }

    function getDerivedEntityIds(events: BusinessEvent[]): string[] {
        const ids = events
            .flatMap((event) => event.derived_entities ?? [])
            .map((entry) => (typeof entry === "string" ? entry : entry.entity_id))
            .filter((id): id is string => Boolean(id));
        return Array.from(new Set(ids));
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
                            Document business events during the conception phase of dimensional data modeling.
                            <br />
                            Identify granular events by asking "What happens?" (e.g. "Customer buys Product") and annotate them with analytical context answering "Who, What, When, Where, How, Why, and How Many".
                            <br />
                            Optionally group related events into a holistic process to consolidate multiple events into the same fact table.
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
                <div class="flex items-center justify-between flex-wrap gap-4">
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

                        <div class="flex items-center gap-2">
                            <span class="text-sm font-medium text-gray-700">Filter by process:</span>
                        </div>
                        <select
                            bind:value={selectedProcess}
                            class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        >
                            <option value={null}>All Processes</option>
                            {#each activeProcesses as process}
                                <option value={process.id}>{process.name}</option>
                            {/each}
                            <option value="ungrouped">Ungrouped</option>
                        </select>
                    </div>

                    <!-- Multi-select controls -->
                    {#if filteredEvents.length > 0}
                        <div class="flex items-center gap-3">
                            {#if selectedCount > 0}
                                <span class="text-sm text-gray-600">
                                    {selectedCount} selected
                                </span>
                                <button
                                    onclick={handleSelectAll}
                                    class="text-sm text-primary-600 hover:text-primary-700 font-medium"
                                >
                                    {selectedCount === filteredEvents.length ? 'Deselect All' : 'Select All'}
                                </button>
                                <button
                                    onclick={() => selectedEventIds = new Set()}
                                    class="text-sm text-gray-600 hover:text-gray-700"
                                >
                                    Clear
                                </button>
                            {:else}
                                <button
                                    onclick={handleSelectAll}
                                    class="text-sm text-primary-600 hover:text-primary-700 font-medium"
                                >
                                    Select All
                                </button>
                            {/if}
                            {#if canGroup}
                                <button
                                    onclick={handleGroupIntoProcess}
                                    class="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-sm"
                                >
                                    <Icon icon="lucide:layers" class="w-4 h-4" />
                                    Group into Process
                                </button>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>

            {#if events.length > 0}
                {#if !hasActiveProcesses}
                    <div class="mb-4 rounded-lg border border-dashed border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-800">
                        <p class="font-semibold text-primary-800">No processes yet</p>
                        <p class="text-xs text-primary-700">
                            Select multiple events and click "Group into Process" to create the first process.
                        </p>
                    </div>
                {/if}
                {#if domains.length === 0}
                    <div class="mb-4 rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                        <p class="font-semibold text-gray-800">No domains assigned</p>
                        <p class="text-xs text-gray-600">
                            Edit an event and add a business domain so events appear under meaningful headings.
                        </p>
                    </div>
                {/if}
            {/if}

            <!-- Event List -->
            {#if domainGroups.length === 0}
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
                                "customer buys product" - a discrete event that can be annotated with
                                Who, What, When, Where, How, How Many, and Why to generate dimensional entities.
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
                {#if processActionError}
                    <div class="mb-3 rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
                        {processActionError}
                    </div>
                {/if}
                <div class="space-y-4">
                    {#each domainGroups as domainGroup (domainGroup.domainKey)}
                        <div class="rounded-lg border border-gray-200 shadow-sm bg-white overflow-hidden">
                            <div
                                class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-100"
                            >
                                <div class="flex items-center gap-2">
                                    <button
                                        class="flex items-center gap-2 text-sm font-semibold text-gray-700 focus:outline-none"
                                        onclick={() => toggleDomainCollapse(domainGroup.domainKey)}
                                        aria-expanded={isDomainExpanded(domainGroup.domainKey)}
                                        aria-controls={`domain-${domainGroup.domainKey}`}
                                    >
                                        <CollapseChevron
                                            expanded={isDomainExpanded(domainGroup.domainKey)}
                                        />
                                        <span>{domainGroup.domainLabel}</span>
                                    </button>
                                </div>
                                <span class="text-xs text-gray-500">
                                    {domainGroup.totalEvents} event{domainGroup.totalEvents !== 1 ? 's' : ''}
                                </span>
                            </div>
                            {#if isDomainExpanded(domainGroup.domainKey)}
                                <div class="space-y-3 px-4 py-3" id={`domain-${domainGroup.domainKey}`}>
                                    {#each domainGroup.processes as processGroup (processGroup.process.id)}
                                        {@const derivedIds = getDerivedEntityIds(processGroup.events)}
                                        <div
                                            class="space-y-2 rounded-lg border border-gray-200 bg-gray-50 shadow-sm"
                                            class:border-primary-300={dragOverProcessId === processGroup.process.id}
                                            class:ring-2={dragOverProcessId === processGroup.process.id}
                                            class:ring-primary-200={dragOverProcessId === processGroup.process.id}
                                            ondragover={(event) =>
                                                handleProcessDragOver(processGroup.process.id, event)}
                                            ondrop={(event) => handleProcessDrop(processGroup, event)}
                                        >
                                            <div class="flex items-center gap-3 px-3 py-2">
                                                <button
                                                    class="p-1 text-gray-500 hover:text-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                                                    onclick={() => toggleProcessCollapse(processGroup.process.id)}
                                                    aria-expanded={isProcessExpanded(processGroup.process.id)}
                                                    aria-controls={`process-${processGroup.process.id}`}
                                                >
                                                    <CollapseChevron
                                                        expanded={isProcessExpanded(processGroup.process.id)}
                                                    />
                                                </button>
                                                <ProcessRow
                                                    process={processGroup.process}
                                                    eventCount={processGroup.events.length}
                                                    onEdit={() => handleProcessEdit(processGroup.process)}
                                                    onAnnotate={() => handleProcessAnnotate(processGroup.process)}
                                                    onOpenCanvas={
                                                        derivedIds.length > 0
                                                            ? () =>
                                                                  handleProcessCanvasLink(processGroup.process, derivedIds)
                                                            : undefined
                                                    }
                                                    onResolve={handleProcessResolve}
                                                />
                                            </div>
                                            {#if isProcessExpanded(processGroup.process.id)}
                                                <div
                                                    class="space-y-2 px-5 py-3"
                                                    id={`process-${processGroup.process.id}`}
                                                >
                                                    {#each processGroup.events as event (event.id)}
                                                        <div class="relative">
                                                            {#if dragOverEventId === event.id && dropIndicatorPosition === 'before'}
                                                                <div class="absolute -top-1 left-0 right-0 h-0.5 bg-primary-500 z-10">
                                                                    <div class="absolute -left-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
                                                                    <div class="absolute -right-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
                                                                </div>
                                                            {/if}
                                                            <EventCard
                                                                {event}
                                                                process={processGroup.process}
                                                                selected={selectedEventIds.has(event.id)}
                                                                draggable={true}
                                                                onSelect={(selected) => handleEventSelect(event.id, selected)}
                                                                onEditEvent={handleEditEvent}
                                                                onEditSevenWs={handleEditSevenWs}
                                                                onGenerateEntities={handleGenerateEntities}
                                                                onDelete={reloadEvents}
                                                                onResolveProcess={handleProcessResolve}
                                                                onDragStart={(dragEvent) =>
                                                                    handleEventDragStart(
                                                                        event,
                                                                        processGroup.process.id,
                                                                        dragEvent
                                                                    )}
                                                                onDragOver={(_, dragEvent) =>
                                                                    handleEventDragOver(
                                                                        event,
                                                                        processGroup.process.id,
                                                                        dragEvent,
                                                                        processGroup
                                                                    )}
                                                                onDrop={(_, dragEvent) =>
                                                                    handleEventDrop(event, processGroup, dragEvent)}
                                                                onDragEnd={handleEventDragEnd}
                                                            />
                                                            {#if dragOverEventId === event.id && dropIndicatorPosition === 'after'}
                                                                <div class="absolute -bottom-1 left-0 right-0 h-0.5 bg-primary-500 z-10">
                                                                    <div class="absolute -left-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
                                                                    <div class="absolute -right-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
                                                                </div>
                                                            {/if}
                                                        </div>
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>
                                    {/each}
                                    {#if domainGroup.ungroupedEvents.length > 0}
                                        <div
                                            class="space-y-2 pt-2"
                                            class:border-primary-300={dragOverUngroupedDomainKey === domainGroup.domainKey}
                                            class:ring-2={dragOverUngroupedDomainKey === domainGroup.domainKey}
                                            class:ring-primary-200={dragOverUngroupedDomainKey === domainGroup.domainKey}
                                            ondragover={(event) =>
                                                handleUngroupedDragOver(domainGroup.domainKey, event)}
                                            ondrop={(event) => handleUngroupedDrop(domainGroup.domainKey, event)}
                                        >
                                            {#each domainGroup.ungroupedEvents as event (event.id)}
                                                <EventCard
                                                    {event}
                                                    selected={selectedEventIds.has(event.id)}
                                                    draggable={true}
                                                    onSelect={(selected) => handleEventSelect(event.id, selected)}
                                                    onEditEvent={handleEditEvent}
                                                    onEditSevenWs={handleEditSevenWs}
                                                    onGenerateEntities={handleGenerateEntities}
                                                    onDelete={reloadEvents}
                                                    onDragStart={(dragEvent) =>
                                                        handleEventDragStart(event, null, dragEvent)}
                                                    onDragEnd={handleEventDragEnd}
                                                />
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                            {/if}
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

    <!-- Edit Event Modal -->
    <CreateEventModal
        open={showEditModal}
        event={editEvent ?? undefined}
        onSave={handleEditModalClose}
        onCancel={handleEditModalCancel}
    />


    <!-- Annotations Form Modal -->
    {#if showSevenWsForm && sevenWsEvent}
        <SevenWsForm
            event={sevenWsEvent}
            onSave={handleSevenWsSave}
            onCancel={handleSevenWsCancel}
        />
    {/if}

    {#if showProcessSevenWsForm && processAnnotationEvent}
        <SevenWsForm
            event={processAnnotationEvent}
            onSave={handleProcessSevenWsSave}
            onCancel={handleProcessSevenWsCancel}
        />
    {/if}

    <ProcessEditModal
        open={showProcessEditModal}
        process={processUnderEdit ?? undefined}
        onSave={handleProcessEditSave}
        onCancel={handleProcessEditCancel}
        domains={domains}
    />

    <!-- Generate Entities Dialog -->
    <GenerateEntitiesDialog
        open={showGenerateEntitiesDialog}
        event={generateEntitiesEvent}
        onConfirm={handleGenerateEntitiesClose}
        onCancel={handleGenerateEntitiesClose}
    />

    <!-- Process Group Modal -->
    <ProcessGroupModal
        open={showProcessGroupModal}
        eventIds={Array.from(selectedEventIds)}
        onSave={handleProcessGroupSave}
        onCancel={handleProcessGroupCancel}
        domains={domains}
    />
</div>
