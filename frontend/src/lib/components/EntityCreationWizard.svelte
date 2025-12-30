<script lang="ts">
    import Icon from "@iconify/svelte";
    import type { GuidanceConfig, EntityWizardData } from "$lib/types";
    import { generateSlug, toTitleCase } from "$lib/utils";

    type Props = {
        open: boolean;
        onComplete: (data: EntityWizardData) => void;
        onCancel: () => void;
        existingEntityIds: string[];
        config: GuidanceConfig;
    };

    let { open, onComplete, onCancel, existingEntityIds, config }: Props = $props();

    let currentStep = $state(1);
    let formData = $state({
        label: "New Entity",
        description: "",
    });
    let validationErrors = $state({
        label: null as string | null,
        description: null as string | null,
    });
    let showExamples = $state(false);

    const DESCRIPTION_EXAMPLES = [
        {
            entity: "Customer",
            description: "A person or organization that purchases at least 1 product or service from the business",
        },
        {
            entity: "Order",
            description: "A record of a customer's purchase, containing items, quantities, and payment information",
        },
        {
            entity: "Product",
            description: "An item or service offered for sale, with attributes like name, price, and category",
        },
    ];

    // Validation functions
    function validateLabel(label: string): string | null {
        if (!label || label.trim().length === 0) {
            return "Entity name is required";
        }
        if (label === "New Entity") {
            return "Please choose a meaningful name";
        }
        // Generate base slug (without uniqueness counter)
        const baseSlug = label
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '') || 'entity';
        
        // Check if base slug or any variant exists
        const isDuplicate = existingEntityIds.some(id => {
            // Check if ID matches base slug exactly, or starts with base slug followed by underscore and number
            return id === baseSlug || id.startsWith(`${baseSlug}_`);
        });
        
        if (isDuplicate) {
            return "An entity with this name already exists";
        }
        return null; // Valid
    }

    function validateDescription(description: string): string | null {
        if (!description || description.trim().length === 0) {
            return "Description is required";
        }
        if (description.trim().length < config.min_description_length) {
            return `Description must be at least ${config.min_description_length} characters`;
        }
        const placeholderPatterns = ["Enter description", "Description...", "Add description"];
        if (placeholderPatterns.some((p) => description.toLowerCase().includes(p.toLowerCase()))) {
            return "Please provide a meaningful description";
        }
        return null; // Valid
    }

    // Step navigation
    function nextStep() {
        if (currentStep === 1) {
            // Allow "New Entity" to proceed (will be auto-named when binding dbt model)
            if (formData.label !== "New Entity") {
                const error = validateLabel(formData.label);
                validationErrors.label = error;
                if (error) return;
            } else {
                validationErrors.label = null;
            }
            currentStep = 2;
        } else if (currentStep === 2) {
            const error = validateDescription(formData.description);
            validationErrors.description = error;
            if (error) return;
            // Check if step 3 should be shown
            if (config.disabled_guidance.includes("attribute_suggestions")) {
                complete();
            } else {
                currentStep = 3;
            }
        }
    }

    function previousStep() {
        if (currentStep > 1) {
            currentStep--;
        }
    }

    function skipStep() {
        if (currentStep === 1) {
            // Skip label - use default "New Entity" (will be auto-named when binding dbt model)
            validationErrors.label = null;
            currentStep = 2;
        } else if (currentStep === 2) {
            // Skip description - validate but allow empty
            validationErrors.description = null;
            if (config.disabled_guidance.includes("attribute_suggestions")) {
                complete();
            } else {
                currentStep = 3;
            }
        } else if (currentStep === 3) {
            complete();
        }
    }

    function complete() {
        // Validate label only if it's been changed from default
        // Allow "New Entity" to pass through (will be auto-named when binding dbt model)
        if (formData.label !== "New Entity") {
            const labelError = validateLabel(formData.label);
            if (labelError) {
                validationErrors.label = labelError;
                currentStep = 1;
                return;
            }
        }

        // Description is optional (user can add later)
        // If skipped, description will be empty string
        // Convert label to title-case
        const formattedLabel = formData.label === "New Entity" 
            ? formData.label 
            : toTitleCase(formData.label.trim());
        onComplete({
            label: formattedLabel,
            description: formData.description.trim(),
        });
        reset();
    }

    function reset() {
        currentStep = 1;
        formData = {
            label: "New Entity",
            description: "",
        };
        validationErrors = {
            label: null,
            description: null,
        };
        showExamples = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onCancel();
        } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            // Ctrl/Cmd+Enter to submit
            event.preventDefault();
            if (currentStep < 3) {
                nextStep();
            } else {
                complete();
            }
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    // Real-time validation
    $effect(() => {
        if (currentStep === 1 && formData.label) {
            // Allow "New Entity" without error (can be skipped/auto-named)
            if (formData.label === "New Entity") {
                validationErrors.label = null;
            } else {
                validationErrors.label = validateLabel(formData.label);
            }
        }
    });

    $effect(() => {
        if (currentStep === 2 && formData.description) {
            validationErrors.description = validateDescription(formData.description);
        }
    });

    // Reset when modal opens
    $effect(() => {
        if (open) {
            reset();
        }
    });
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
        aria-labelledby="wizard-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.stopPropagation()}
            aria-label="Entity creation wizard"
        >
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
                <h2 id="wizard-title" class="text-xl font-semibold text-gray-900">
                    Create New Entity
                </h2>
                <button
                    onclick={onCancel}
                    class="p-1 rounded-md hover:bg-gray-100 text-gray-500"
                    aria-label="Close"
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            <!-- Progress Indicator -->
            <div class="mb-6">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium text-gray-700">
                        Step {currentStep} of 3
                    </span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div
                        class="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style="width: {(currentStep / 3) * 100}%"
                    ></div>
                </div>
            </div>

            <!-- Step 1: Entity Name -->
            {#if currentStep === 1}
                <div class="space-y-4">
                    <div>
                        <label for="entity-label" class="block text-sm font-medium text-gray-700 mb-2">
                            Entity Label
                        </label>
                        <input
                            id="entity-label"
                            type="text"
                            bind:value={formData.label}
                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent {validationErrors.label ? 'border-red-500' : validationErrors.label === null && formData.label && formData.label !== 'New Entity' ? 'border-green-500' : ''}"
                            placeholder="e.g., Customer, Order, Product"
                        />
                        {#if validationErrors.label}
                            <p class="mt-1 text-sm text-red-600 flex items-center gap-1">
                                <Icon icon="lucide:alert-circle" class="w-4 h-4" />
                                {validationErrors.label}
                            </p>
                        {:else if formData.label && formData.label !== "New Entity" && !validationErrors.label}
                            <p class="mt-1 text-sm text-green-600 flex items-center gap-1">
                                <Icon icon="lucide:check-circle" class="w-4 h-4" />
                                Unique name
                            </p>
                        {/if}
                    </div>

                    <!-- Slug Preview -->
                    {#if formData.label && formData.label !== "New Entity"}
                        <div class="text-xs text-gray-500">
                            <span class="font-medium">ID:</span> {generateSlug(formData.label, existingEntityIds)}
                        </div>
                    {/if}

                    <!-- Guidance -->
                    <div class="bg-blue-50 border border-blue-200 rounded-md p-3">
                        <div class="flex items-start gap-2">
                            <Icon icon="lucide:lightbulb" class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                            <p class="text-sm text-blue-800">
                                Choose a clear, descriptive name (e.g., 'Customer', 'Order', 'Product')
                            </p>
                        </div>
                    </div>
                </div>
            {/if}

            <!-- Step 2: Description -->
            {#if currentStep === 2}
                <div class="space-y-4">
                    <div>
                        <label for="entity-description" class="block text-sm font-medium text-gray-700 mb-2">
                            Description
                        </label>
                        <textarea
                            id="entity-description"
                            bind:value={formData.description}
                            rows="4"
                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y {validationErrors.description ? 'border-red-500' : validationErrors.description === null && formData.description.trim().length >= config.min_description_length ? 'border-green-500' : ''}"
                            placeholder="Describe what this entity represents in business terms..."
                        ></textarea>
                        <div class="mt-1 flex items-center justify-between">
                            {#if validationErrors.description}
                                <p class="text-sm text-red-600 flex items-center gap-1">
                                    <Icon icon="lucide:alert-circle" class="w-4 h-4" />
                                    {validationErrors.description}
                                </p>
                            {:else if formData.description.trim().length >= config.min_description_length}
                                <p class="text-sm text-green-600 flex items-center gap-1">
                                    <Icon icon="lucide:check-circle" class="w-4 h-4" />
                                    Valid description
                                </p>
                            {:else}
                                <p class="text-sm text-gray-500">
                                    Minimum {config.min_description_length} characters
                                </p>
                            {/if}
                            <span class="text-xs text-gray-500">
                                {formData.description.length} / {config.min_description_length}+
                            </span>
                        </div>
                    </div>

                    <!-- Examples Panel -->
                    <div>
                        <button
                            onclick={() => showExamples = !showExamples}
                            class="w-full flex items-center justify-between p-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-md transition-colors"
                        >
                            <span class="flex items-center gap-2">
                                <Icon icon="lucide:book-open" class="w-4 h-4" />
                                Example Descriptions
                            </span>
                            <Icon
                                icon="lucide:chevron-down"
                                class="w-4 h-4 transition-transform {showExamples ? 'rotate-180' : ''}"
                            />
                        </button>
                        {#if showExamples}
                            <div class="mt-2 space-y-3 p-3 bg-gray-50 rounded-md border border-gray-200">
                                {#each DESCRIPTION_EXAMPLES as example}
                                    <div class="border-l-2 border-primary-500 pl-3">
                                        <p class="text-xs font-semibold text-gray-700 mb-1">
                                            {example.entity}
                                        </p>
                                        <p class="text-xs text-gray-600">{example.description}</p>
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>

                    <!-- Guidance -->
                    <div class="bg-blue-50 border border-blue-200 rounded-md p-3">
                        <div class="flex items-start gap-2">
                            <Icon icon="lucide:lightbulb" class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                            <p class="text-sm text-blue-800">
                                Describe what this entity represents in business terms
                            </p>
                        </div>
                    </div>
                </div>
            {/if}

            <!-- Step 3: Attributes (Optional) -->
            {#if currentStep === 3}
                <div class="space-y-4">
                    <div class="bg-gray-50 border border-gray-200 rounded-md p-4">
                        <div class="flex items-start gap-3">
                            <Icon icon="lucide:info" class="w-5 h-5 text-gray-600 mt-0.5 flex-shrink-0" />
                            <div class="flex-1">
                                <h3 class="text-sm font-medium text-gray-900 mb-2">
                                    Consider adding key fields/attributes describing the entity records
                                </h3>
                                <p class="text-sm text-gray-600 mb-3">
                                    Common fields:
                                </p>
                                <ul class="text-sm text-gray-600 list-disc list-inside space-y-1 mb-3">
                                    <li>Unique Identifiers (Primary/Foreign Keys)</li>
                                    <li>Timestamps</li>
                                    <li>Status Indicators</li>
                                    <li>Categorical Fields</li>
                                </ul>
                                <p class="text-xs text-gray-500">
                                    You can add fields after creating the entity by editing it in logical view.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}

            <!-- Footer Actions -->
            <div class="mt-6 flex items-center justify-between gap-3">
                <div>
                    {#if currentStep > 1}
                        <button
                            onclick={previousStep}
                            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        >
                            Previous
                        </button>
                    {/if}
                </div>
                <div class="flex gap-3">
                    {#if currentStep < 3}
                        <button
                            onclick={skipStep}
                            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                        >
                            Skip
                        </button>
                        <button
                            onclick={nextStep}
                            class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        >
                            Next
                        </button>
                    {:else}
                        <button
                            onclick={complete}
                            class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        >
                            Done
                        </button>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

