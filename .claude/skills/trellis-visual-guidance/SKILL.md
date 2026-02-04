---
name: trellis-visual-guidance
description: Applies Trellis visual guidance for UI work, including color schemes and visual consistency. Use when modifying frontend UI, canvas views, annotations, badges, or any visual styling.
---

# Trellis Visual Guidance

## Quick Rules (Checklist)

- Use the existing Trellis brand palette; do not introduce new core colors
- Use green styling for dimensions: `bg-green-100`, `text-green-700` (badges), `text-green-600` (icons), icon `lucide:list`
- Use blue styling for facts: `bg-blue-100`, `text-blue-700` (badges), `text-blue-600` (icons), icon `lucide:bar-chart-3`
- Keep dimension/fact colors consistent across canvas, sidebar, annotations, badges, and lists
- Prefer Tailwind utility classes over custom CSS for UI styling
- Avoid introducing new color tokens unless required by an existing design system

## Scope

Apply these rules to all UI changes in the app, especially:
- Canvas and lineage views
- Sidebar entity/model items
- Node badges, labels, and annotations
- Entity lists, cards, and detail panels where entity types are shown
- Dropdown menus and type selectors

## Brand Colors

The Trellis brand color is `primary` (Tailwind teal). Use `primary-600` as the main action color, with `primary-50/100/500/700` for states and emphasis:
- Primary actions: `bg-primary-600 text-white` (hover: `bg-primary-700`)
- Subtle highlights: `bg-primary-50 text-primary-700 border-primary-300`
- Focus rings: `focus:ring-primary-500 focus:border-primary-500`
Keep the neutral scaffolding in slate grays (`gray` from Tailwind slate). Use `danger` (rose) and `success` (emerald) only for semantic status.

## Highlighting and Selection

Use the primary teal for selection and interactive emphasis:
- Selected rows/cards: `bg-primary-50 border-primary-300 text-primary-700`
- Active tabs/links: `text-primary-600` (hover: `text-primary-700`)
- Hover states: prefer `hover:bg-gray-50` for neutral surfaces; use `hover:bg-primary-50` only when reinforcing selection
- Toggles/checkboxes: `peer-checked:bg-primary-600` with `peer-focus:ring-primary-500`

## Icon Style

Use simple, outline icons (lucide) to keep the UI lightweight and consistent:
- Favor 1-color icons that inherit text color
- Avoid mixed icon styles (filled vs outline) in the same surface
- Dimension icon: `lucide:list`; fact icon: `lucide:bar-chart-3`
- Only add new icons when they map cleanly to an entity type or action

## Dimension & Fact Color Reference

### Dimensions (green)
- **Icons**: `text-green-600` (standalone icons, sidebar items)
- **Badges**: `bg-green-100 text-green-700 border-green-300`
- **Node badges**: `bg-green-100 text-green-800`
- **Icon**: `lucide:list`

### Facts (blue)
- **Icons**: `text-blue-600` (standalone icons, sidebar items)
- **Badges**: `bg-blue-100 text-blue-700 border-blue-300`
- **Node badges**: `bg-blue-100 text-blue-800`
- **Icon**: `lucide:bar-chart-3`

### Examples

```svelte
<!-- Sidebar/List Icon -->
<Icon icon="lucide:list" class="w-5 h-5 text-green-600" />
<Icon icon="lucide:bar-chart-3" class="w-5 h-5 text-blue-600" />

<!-- Type Badge -->
<span class="bg-green-100 text-green-700 border-green-300 px-2 py-1 rounded border">
  Dimension
</span>
<span class="bg-blue-100 text-blue-700 border-blue-300 px-2 py-1 rounded border">
  Fact
</span>

<!-- Entity Node Badge (canvas) -->
<button class="bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
  <Icon icon="lucide:list" class="w-3 h-3" />
</button>
```

## Glass Areas (Frosted Surfaces)

Glass surfaces are used sparingly to separate overlays and focus areas:
- Use translucency and subtle blur (frosted effect), not opaque cards
- Keep borders light and avoid heavy shadows
- Ensure text contrast remains readable on glass surfaces
