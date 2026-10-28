<script module lang="ts">
    // Open modals, innermost last. Only the topmost one reacts to Escape/Tab,
    // so nested modals don't fight over the same keypress.
    const openModals: symbol[] = [];

    const FOCUSABLE =
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
</script>

<script lang="ts">
    /**
     * Shared modal shell: backdrop, Escape-to-close, focus trap + focus restore,
     * and dialog a11y attributes. Callers own the panel's look via `class`.
     *
     * Backdrop is always `bg-black/50 backdrop-blur-sm`.
     * Escape closes only the topmost open modal. Escape/Tab are ignored when an
     * inner handler already called `event.preventDefault()` (e.g. to close a dropdown).
     */
    import type { Snippet } from "svelte";
    import type { HTMLAttributes } from "svelte/elements";

    type Size = "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl";

    type Props = Omit<HTMLAttributes<HTMLDivElement>, "class" | "children"> & {
        open?: boolean;
        onClose: () => void;
        /** Max width of the panel. Omit to size it via `class`/`style`. */
        size?: Size;
        /** Panel classes (background, radius, padding, height, ...). */
        class?: string;
        zIndex?: number;
        closeOnBackdrop?: boolean;
        closeOnEscape?: boolean;
        labelledBy?: string;
        ariaLabel?: string;
        children: Snippet;
    };

    let {
        open = true,
        onClose,
        size,
        class: panelClass = "",
        zIndex = 50,
        closeOnBackdrop = true,
        closeOnEscape = true,
        labelledBy,
        ariaLabel,
        children,
        ...rest
    }: Props = $props();

    // Literal class names so Tailwind picks them up.
    const SIZE_CLASSES: Record<Size, string> = {
        sm: "max-w-sm",
        md: "max-w-md",
        lg: "max-w-lg",
        xl: "max-w-xl",
        "2xl": "max-w-2xl",
        "3xl": "max-w-3xl",
        "4xl": "max-w-4xl",
        "5xl": "max-w-5xl",
    };

    const id = Symbol("modal");
    let panel = $state<HTMLDivElement>();

    // Pre-effect: runs before the panel's DOM exists, so activeElement is still
    // the element that opened the modal.
    $effect.pre(() => {
        if (!open) return;
        const returnFocusTo =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
        openModals.push(id);
        // Only open modals listen, so closed instances (e.g. one per list row) cost nothing.
        window.addEventListener("keydown", handleWindowKeydown);
        return () => {
            window.removeEventListener("keydown", handleWindowKeydown);
            const index = openModals.indexOf(id);
            if (index !== -1) openModals.splice(index, 1);
            if (returnFocusTo?.isConnected) returnFocusTo.focus();
        };
    });

    // Move focus into the panel unless content already focused something
    // (e.g. an `autofocus` input).
    $effect(() => {
        if (open && panel && !panel.contains(document.activeElement)) {
            panel.focus();
        }
    });

    function isTopmost() {
        return openModals[openModals.length - 1] === id;
    }

    function trapFocus(event: KeyboardEvent) {
        if (!panel) return;
        const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (focusable.length === 0) {
            event.preventDefault();
            panel.focus();
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement;
        if (!panel.contains(active)) {
            event.preventDefault();
            first.focus();
        } else if (event.shiftKey && (active === first || active === panel)) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && active === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function handleWindowKeydown(event: KeyboardEvent) {
        // defaultPrevented: an inner widget (dropdown, autocomplete) already used the key.
        if (!isTopmost() || event.defaultPrevented) return;
        if (event.key === "Escape") {
            if (closeOnEscape) onClose();
        } else if (event.key === "Tab") {
            trapFocus(event);
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (closeOnBackdrop && event.target === event.currentTarget) onClose();
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        style:z-index={zIndex}
        onclick={handleBackdropClick}
    >
        <div
            {...rest}
            bind:this={panel}
            class="focus:outline-none {size ? SIZE_CLASSES[size] : ''} {panelClass}"
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            aria-label={ariaLabel}
            tabindex="-1"
        >
            {@render children()}
        </div>
    </div>
{/if}
