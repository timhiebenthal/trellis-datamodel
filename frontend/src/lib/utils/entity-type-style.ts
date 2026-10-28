export type EntityTypeValue = 'fact' | 'dimension' | 'unclassified' | 'entity';

export interface EntityTypeStyle {
    /** Iconify icon name */
    icon: string;
    /** Badge background, text and border colour classes */
    badge: string;
    /** Icon colour class */
    iconClass: string;
    /** Standalone text colour class (e.g. group headings) */
    textClass: string;
    /** Human-readable label */
    label: string;
}

const DIMENSION: EntityTypeStyle = {
    icon: 'lucide:list',
    badge: 'bg-green-100 text-green-700 border-green-300',
    iconClass: 'text-green-600',
    textClass: 'text-green-700',
    label: 'Dimension',
};

const FACT: EntityTypeStyle = {
    icon: 'lucide:bar-chart-3',
    badge: 'bg-blue-100 text-blue-700 border-blue-300',
    iconClass: 'text-blue-600',
    textClass: 'text-blue-700',
    label: 'Fact',
};

const NEUTRAL = {
    icon: 'lucide:circle-dashed',
    badge: 'bg-gray-100 text-gray-700 border-gray-300',
    iconClass: 'text-gray-500',
    textClass: 'text-gray-500',
};

const UNCLASSIFIED: EntityTypeStyle = { ...NEUTRAL, label: 'Unclassified' };
const ENTITY: EntityTypeStyle = { ...NEUTRAL, label: 'Entity' };

/**
 * Presentation for an entity type: dimension = green, fact = blue,
 * everything else (unclassified, generic entity, unknown) = neutral gray.
 */
export function getEntityTypeStyle(type: EntityTypeValue | string | null | undefined): EntityTypeStyle {
    switch (type) {
        case 'dimension':
            return DIMENSION;
        case 'fact':
            return FACT;
        case 'entity':
            return ENTITY;
        default:
            return UNCLASSIFIED;
    }
}
