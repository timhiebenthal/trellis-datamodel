<script lang="ts">
    // Test-only harness for Modal.test.ts: snippets and nested modals can't be
    // built from a .ts test file directly.
    import Modal from "./Modal.svelte";

    type Props = {
        onOuterClose?: () => void;
        onInnerClose?: () => void;
        closeOnBackdrop?: boolean;
        startOpen?: boolean;
    };

    let {
        onOuterClose = () => {},
        onInnerClose = () => {},
        closeOnBackdrop = true,
        startOpen = false,
    }: Props = $props();

    let outerOpen = $state(startOpen);
    let innerOpen = $state(false);

    function closeOuter() {
        outerOpen = false;
        onOuterClose();
    }

    function closeInner() {
        innerOpen = false;
        onInnerClose();
    }
</script>

<button onclick={() => (outerOpen = true)}>Open outer</button>

<Modal open={outerOpen} onClose={closeOuter} labelledBy="outer-title" size="lg" {closeOnBackdrop}>
    <h2 id="outer-title">Outer modal</h2>
    <button onclick={() => (innerOpen = true)}>Open inner</button>
    <button>Last outer button</button>
</Modal>

<Modal open={innerOpen} onClose={closeInner} ariaLabel="Inner modal" zIndex={60}>
    <p>Inner content</p>
</Modal>
