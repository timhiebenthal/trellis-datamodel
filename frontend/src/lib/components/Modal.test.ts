import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import ModalTestHarness from './ModalTestHarness.svelte';

describe('Modal', () => {
    afterEach(() => {
        cleanup();
    });

    it('renders nothing while closed', () => {
        render(ModalTestHarness);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('renders children in a labelled modal dialog', () => {
        render(ModalTestHarness, { startOpen: true });

        const dialog = screen.getByRole('dialog', { name: 'Outer modal' });
        expect(dialog).toHaveAttribute('aria-modal', 'true');
        expect(dialog).toHaveClass('max-w-lg');
        expect(screen.getByText('Outer modal')).toBeInTheDocument();
    });

    it('uses one backdrop style and the requested z-index', async () => {
        render(ModalTestHarness, { startOpen: true });
        await fireEvent.click(screen.getByText('Open inner'));

        const outerBackdrop = screen.getByRole('dialog', { name: 'Outer modal' }).parentElement!;
        const innerBackdrop = screen.getByRole('dialog', { name: 'Inner modal' }).parentElement!;
        expect(outerBackdrop).toHaveClass('fixed', 'inset-0', 'bg-black/50');
        expect(outerBackdrop.style.zIndex).toBe('50');
        expect(innerBackdrop.style.zIndex).toBe('60');
    });

    it('calls onClose on Escape', async () => {
        const onOuterClose = vi.fn();
        render(ModalTestHarness, { startOpen: true, onOuterClose });

        await fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

        expect(onOuterClose).toHaveBeenCalledTimes(1);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('ignores Escape that an inner handler already consumed', async () => {
        const onOuterClose = vi.fn();
        render(ModalTestHarness, { startOpen: true, onOuterClose });

        const button = screen.getByText('Last outer button');
        button.addEventListener('keydown', (e) => e.preventDefault());
        await fireEvent.keyDown(button, { key: 'Escape' });

        expect(onOuterClose).not.toHaveBeenCalled();
    });

    it('closes on backdrop click but not on panel click', async () => {
        const onOuterClose = vi.fn();
        render(ModalTestHarness, { startOpen: true, onOuterClose });

        const dialog = screen.getByRole('dialog');
        await fireEvent.click(dialog);
        expect(onOuterClose).not.toHaveBeenCalled();

        await fireEvent.click(dialog.parentElement!);
        expect(onOuterClose).toHaveBeenCalledTimes(1);
    });

    it('does not close on backdrop click when closeOnBackdrop is false', async () => {
        const onOuterClose = vi.fn();
        render(ModalTestHarness, { startOpen: true, onOuterClose, closeOnBackdrop: false });

        await fireEvent.click(screen.getByRole('dialog').parentElement!);

        expect(onOuterClose).not.toHaveBeenCalled();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('Escape closes only the topmost of nested modals', async () => {
        const onOuterClose = vi.fn();
        const onInnerClose = vi.fn();
        render(ModalTestHarness, { startOpen: true, onOuterClose, onInnerClose });
        await fireEvent.click(screen.getByText('Open inner'));
        expect(screen.getAllByRole('dialog')).toHaveLength(2);

        await fireEvent.keyDown(window, { key: 'Escape' });
        expect(onInnerClose).toHaveBeenCalledTimes(1);
        expect(onOuterClose).not.toHaveBeenCalled();
        expect(screen.getAllByRole('dialog')).toHaveLength(1);

        await fireEvent.keyDown(window, { key: 'Escape' });
        expect(onOuterClose).toHaveBeenCalledTimes(1);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('moves focus into the dialog and restores it on close', async () => {
        render(ModalTestHarness);
        const trigger = screen.getByText('Open outer');
        trigger.focus();

        await fireEvent.click(trigger);
        const dialog = screen.getByRole('dialog');
        expect(dialog.contains(document.activeElement)).toBe(true);

        await fireEvent.keyDown(window, { key: 'Escape' });
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(document.activeElement).toBe(trigger);
    });

    it('traps Tab focus inside the dialog', async () => {
        render(ModalTestHarness, { startOpen: true });
        const first = screen.getByText('Open inner');
        const last = screen.getByText('Last outer button');

        last.focus();
        await fireEvent.keyDown(last, { key: 'Tab' });
        expect(document.activeElement).toBe(first);

        await fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
        expect(document.activeElement).toBe(last);
    });
});
