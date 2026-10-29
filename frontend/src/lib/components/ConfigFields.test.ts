import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import ConfigFieldsTestHarness from './ConfigFieldsTestHarness.svelte';

describe('ConfigToggle / ConfigTextField', () => {
    afterEach(() => cleanup());

    it('renders the Ossie fields with beta badge, description and current values', () => {
        render(ConfigFieldsTestHarness, {
            props: { initial: { ossie: { enabled: true, source: { database: 'analytics' } } } },
        });

        expect(screen.getByLabelText('Ossie Export Enabled')).toBeChecked();
        expect(screen.getByText('Beta')).toBeInTheDocument();
        expect(screen.getByText('Enable Ossie export')).toBeInTheDocument();
        expect(screen.getByLabelText('Database Override')).toHaveValue('analytics');
        expect(screen.getByText('Database segment')).toBeInTheDocument();
    });

    it('writes toggle changes to the nested config path', async () => {
        const onConfig = vi.fn();
        render(ConfigFieldsTestHarness, { props: { onConfig } });

        await fireEvent.click(screen.getByLabelText('Ossie Export Enabled'));

        expect(onConfig).toHaveBeenLastCalledWith({ ossie: { enabled: true } });
    });

    it('stores a cleared text field as an empty string, never null', async () => {
        const onConfig = vi.fn();
        render(ConfigFieldsTestHarness, {
            props: { initial: { ossie: { source: { database: 'analytics' } } }, onConfig },
        });

        await fireEvent.input(screen.getByLabelText('Database Override'), { target: { value: '' } });

        expect(onConfig).toHaveBeenLastCalledWith({ ossie: { source: { database: '' } } });
    });

    it('shows an unset text field as empty', () => {
        render(ConfigFieldsTestHarness);
        expect(screen.getByLabelText('Database Override')).toHaveValue('');
    });

    it('disables both controls when disabled', () => {
        render(ConfigFieldsTestHarness, { props: { disabled: true } });
        expect(screen.getByLabelText('Ossie Export Enabled')).toBeDisabled();
        expect(screen.getByLabelText('Database Override')).toBeDisabled();
    });
});
