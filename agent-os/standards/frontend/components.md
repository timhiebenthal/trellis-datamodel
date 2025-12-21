## UI component best practices (SvelteKit)

This project uses SvelteKit with Svelte 5. Follow these conventions:

- **Single Responsibility**: Each component should have one clear purpose and do it well
- **Component Location**: Place reusable components in `frontend/src/lib/` directory
- **Svelte 5 Syntax**: Use Svelte 5 runes (`$state`, `$derived`, `$effect`) for reactivity instead of the options API
- **Props Definition**: Use TypeScript interfaces for prop types, define props with `let` declarations
- **Reusability**: Design components to be reused across different contexts with configurable props
- **Composability**: Build complex UIs by combining smaller, simpler components rather than monolithic structures
- **Clear Interface**: Define explicit, well-documented props with sensible defaults for ease of use
- **Encapsulation**: Keep internal implementation details private and expose only necessary APIs
- **Consistent Naming**: Use clear, descriptive names that indicate the component's purpose (PascalCase for components)
- **State Management**: Keep state as local as possible using Svelte runes; lift it up only when needed by multiple components
- **Stores**: Use Svelte stores (writable/readable) for shared state across components when needed
- **Minimal Props**: Keep the number of props manageable; if a component needs many props, consider composition or splitting it
- **Tailwind CSS**: Use Tailwind utility classes for styling; avoid inline styles or separate CSS files when possible
- **TypeScript**: Use TypeScript for type safety in components and props
