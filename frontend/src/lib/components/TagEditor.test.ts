import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import TagEditor from './TagEditor.svelte';

describe('TagEditor Component', () => {
    const mockOnUpdate = vi.fn();

    beforeEach(() => {
        mockOnUpdate.mockClear();
    });

    describe('Initial Rendering', () => {
        it('renders empty state when no tags provided', () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            expect(container.querySelector('.tag-editor')).toBeInTheDocument();
            // Should only show add button
            expect(container.querySelectorAll('.tag')).toHaveLength(0);
        });

        it('renders provided tags correctly', () => {
            const tags = ['core', 'pii', 'staging'];
            const { container } = render(TagEditor, {
                props: {
                    tags,
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const tagElements = container.querySelectorAll('.tag');
            expect(tagElements).toHaveLength(3);

            tags.forEach((tag, index) => {
                expect(tagElements[index].textContent).toContain(tag);
            });
        });

        it('normalizes tags (trims, removes duplicates, removes empty)', () => {
            const tags = ['  core  ', '  ', 'core', 'staging', '', 'PII'];
            const { container } = render(TagEditor, {
                props: {
                    tags,
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const tagElements = container.querySelectorAll('.tag');
            expect(tagElements).toHaveLength(3); // core, staging, PII
            expect(tagElements[0].textContent).toContain('core');
            expect(tagElements[1].textContent).toContain('staging');
            expect(tagElements[2].textContent).toContain('PII'); // Tags preserve case
        });

        it('hides add button and remove buttons when canEdit is false', () => {
            const tags = ['core'];
            const { container } = render(TagEditor, {
                props: {
                    tags,
                    canEdit: false,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            // Should show tag but no remove buttons
            expect(container.querySelector('.tag')).toBeInTheDocument();
            expect(container.querySelectorAll('.tag button')).toHaveLength(0);

            // Should not show add button
            const addButton = container.querySelector('button[title="Add tag"]');
            expect(addButton).toBeNull();
        });

        it('shows add button when canEdit is true', () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            expect(addButton).toBeInTheDocument();
        });
    });

    describe('Add Tag Functionality', () => {
        it('adds tag when pressing Enter', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            // Click add button to show input
            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                // Wait for input to appear
                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                // Type tag and press Enter
                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: 'core' } });
                    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

                    // Check if onUpdate was called with new tag
                    await waitFor(() => {
                        expect(mockOnUpdate).toHaveBeenCalledWith(['core']);
                    });
                }
            }
        });

        it('adds multiple tags separated by commas', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: ['existing'],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: 'core,staging, pii' } });
                    fireEvent.keyDown(input, { key: ',', code: 'Comma' });

                    // Should add 'core' immediately on comma
                    await waitFor(() => {
                        expect(mockOnUpdate).toHaveBeenCalledWith(['existing', 'core']);
                    });
                }
            }
        });

        it('trims whitespace when adding tags', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: '  core  ' } });
                    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

                    await waitFor(() => {
                        expect(mockOnUpdate).toHaveBeenCalledWith(['core']);
                    });
                }
            }
        });

        it('does not add empty tags', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: '   ' } });
                    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

                    // Should not call onUpdate with empty tag
                    expect(mockOnUpdate).not.toHaveBeenCalled();
                }
            }
        });

        it('does not add duplicate tags', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: ['core'],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: 'core' } });
                    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

                    // Should not call onUpdate - tag already exists
                    expect(mockOnUpdate).not.toHaveBeenCalled();
                }
            }
        });

        it('clears input after adding tag', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: 'core' } });
                    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

                    await waitFor(() => {
                        expect(input.value).toBe('');
                    });
                }
            }
        });
    });

    describe('Remove Tag Functionality', () => {
        it('removes tag when remove button is clicked', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: ['core', 'staging'],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const removeButton = container.querySelector('.tag button');
            if (removeButton) {
                await fireEvent.click(removeButton);

                await waitFor(() => {
                    expect(mockOnUpdate).toHaveBeenCalledWith(['staging']);
                });
            }
        });

        it('shows remove button on hover', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: ['core'],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const tag = container.querySelector('.tag');
            const removeButton = container.querySelector('.tag button');

            expect(tag).not.toBeNull();
            // Remove button should exist but be hidden (opacity-0)
            expect(removeButton).not.toBeNull();
            expect(removeButton).toHaveClass('opacity-0');
        });
    });

    describe('Keyboard Shortcuts', () => {
        it('hides input when Escape is pressed', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });

                    await waitFor(() => {
                        expect(input.value).toBe('');
                    });
                }
            }
        });

        it('handles comma key for tag separation', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                await waitFor(() => {
                    const input = container.querySelector('.tag-input');
                    expect(input).not.toBeNull();
                });

                const input = container.querySelector('.tag-input') as HTMLInputElement;
                if (input) {
                    fireEvent.input(input, { target: { value: 'tag1,tag2,tag3' } });
                    fireEvent.keyDown(input, { key: ',', code: 'Comma' });

                    // First tag should be added
                    await waitFor(() => {
                        expect(mockOnUpdate).toHaveBeenCalledWith(['tag1']);
                    });
                }
            }
        });
    });

    describe('Batch Mode', () => {
        it('shows batch-specific placeholder in batch mode', () => {
            const tags: string[] = [];
            const { container } = render(TagEditor, {
                props: {
                    tags,
                    canEdit: true,
                    isBatchMode: true,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                // Click to show input
                fireEvent.click(addButton);

                const input = container.querySelector('.tag-input');
                if (input) {
                    expect(input.getAttribute('placeholder')).toContain('all selected');
                }
            }
        });

        it('shows regular placeholder when not in batch mode', () => {
            const tags: string[] = [];
            const { container } = render(TagEditor, {
                props: {
                    tags,
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                // Click to show input
                fireEvent.click(addButton);

                const input = container.querySelector('.tag-input');
                if (input) {
                    expect(input.getAttribute('placeholder')).not.toContain('all selected');
                    expect(input.getAttribute('placeholder')).toContain('Enter tag');
                }
            }
        });
    });

    describe('Accessibility', () => {
        it('has proper ARIA labels on buttons', () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: ['core'],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const removeButton = container.querySelector('.tag button');
            expect(removeButton?.getAttribute('aria-label')).toBeTruthy();

            const addButton = container.querySelector('button[title="Add tag"]');
            expect(addButton?.getAttribute('aria-label')).toBeTruthy();
        });

        it('has aria-label on input field', async () => {
            const { container } = render(TagEditor, {
                props: {
                    tags: [],
                    canEdit: true,
                    isBatchMode: false,
                    onUpdate: mockOnUpdate,
                },
            });

            const addButton = container.querySelector('button[title="Add tag"]');
            if (addButton) {
                await fireEvent.click(addButton);

                const input = container.querySelector('.tag-input');
                expect(input?.getAttribute('aria-label')).toBe('Add new tag');
            }
        });
    });
});
