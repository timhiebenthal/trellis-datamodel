        <!-- Floating View Mode Switcher - Only show on canvas (conceptual/logical views) -->
        {#if $viewMode === "conceptual" || $viewMode === "logical"}
            <button
                class="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 pointer-events-auto flex bg-white rounded-full border-[3px] border-primary-600 shadow-lg relative overflow-hidden transition-all duration-200"
                style="box-shadow: 0 0 8px rgba(13, 148, 136, 0.4), 0 0 16px rgba(13, 148, 136, 0.25);"
            >
                <button
                    type="button"
                    class="px-4 py-[8px] text-sm font-medium flex items-center gap-2 transition-all duration-200 border-0 bg-transparent cursor-pointer"
                    class:text-primary-600={$viewMode === "conceptual"}
                    class:text-gray-500={$viewMode !== "conceptual"}
                    class:hover:text-gray-900={$viewMode !== "conceptual"}
                    onclick={() => ($viewMode = "conceptual")}
                    title="Conceptual View"
                >
                    <Icon icon="octicon:workflow-16" class="w-3.5 h-3.5" />
                    Conceptual
                </button>

                <div class="w-[1px] bg-gray-200"></div>

                <button
                    type="button"
                    class="px-4 py-[8px] text-sm font-medium flex items-center gap-2 transition-all duration-200 border-0 bg-transparent cursor-pointer"
                    class:text-primary-600={$viewMode === "logical"}
                    class:text-gray-500={$viewMode !== "logical"}
                    class:hover:text-gray-900={$viewMode !== "logical"}
                    onclick={() => ($viewMode = "logical")}
                    title="Logical View"
                >
                    <Icon icon="lucide:database" class="w-3.5 h-3.5" />
                    Logical
                </button>
            </div>
        {/if}
        {/if}
