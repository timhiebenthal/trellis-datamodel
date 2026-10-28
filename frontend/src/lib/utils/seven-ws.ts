import type { AnnotationType } from '$lib/types';

/** The 7W annotation types in canonical display order. */
export const SEVEN_W_TYPES: readonly AnnotationType[] = ['who', 'what', 'when', 'where', 'how', 'why', 'how_many'];

/** Human-readable label for each 7W annotation type. */
export const SEVEN_W_LABELS: Record<AnnotationType, string> = {
    who: 'Who',
    what: 'What',
    when: 'When',
    where: 'Where',
    how: 'How',
    why: 'Why',
    how_many: 'How Many',
};

/** Iconify icon for each 7W annotation type. */
export const SEVEN_W_ICONS: Record<AnnotationType, string> = {
    who: 'lucide:user',
    what: 'lucide:box',
    when: 'lucide:calendar',
    where: 'lucide:map-pin',
    how: 'lucide:settings',
    why: 'lucide:help-circle',
    how_many: 'lucide:bar-chart-3',
};

/** Tailwind classes for the per-type badge shown on a dimension's `annotation_type`. */
export const SEVEN_W_BADGE_CLASSES: Record<AnnotationType, string> = {
    who: 'bg-blue-100 text-blue-800 border-blue-200',
    what: 'bg-purple-100 text-purple-800 border-purple-200',
    when: 'bg-green-100 text-green-800 border-green-200',
    where: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    how: 'bg-orange-100 text-orange-800 border-orange-200',
    why: 'bg-red-100 text-red-800 border-red-200',
    how_many: 'bg-indigo-100 text-indigo-800 border-indigo-200',
};

/**
 * Format an annotation entry text with optional role display.
 *
 * For role-playing dimensions, displays the dimension name followed by the role
 * in parentheses. For regular dimensions, displays just the dimension name.
 *
 * @param entry - The annotation entry containing text and optional role
 * @returns Formatted text: "Dimension (Role)" if role exists, otherwise "Dimension"
 *
 * @example
 * formatAnnotationText({ id: "1", text: "Date", role: "order_date" }) // "Date (order_date)"
 * formatAnnotationText({ id: "2", text: "Customer" }) // "Customer"
 * formatAnnotationText({ id: "3", text: "Date", role: "" }) // "Date" (empty role ignored)
 */
export function formatAnnotationText(entry: { text: string; role?: string }): string {
    if (entry.role && entry.role.trim() !== '') {
        return `${entry.text} (${entry.role})`;
    }
    return entry.text;
}
