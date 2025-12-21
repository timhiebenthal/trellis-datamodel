## CSS best practices (Tailwind CSS)

This project uses Tailwind CSS for styling. Follow these conventions:

- **Tailwind Utility Classes**: Use Tailwind utility classes for styling; prefer utilities over custom CSS
- **Avoid Custom CSS**: Minimize custom CSS files; use Tailwind's `@apply` directive sparingly if needed
- **Tailwind Config**: Customize design tokens (colors, spacing, typography) in `tailwind.config.js` for consistency
- **Component Classes**: Extract repeated utility combinations into component classes using `@apply` or Svelte component composition
- **Responsive Design**: Use Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) for breakpoints
- **Dark Mode**: Use Tailwind's dark mode utilities (`dark:`) if dark mode is implemented
- **Performance**: Tailwind automatically purges unused styles in production builds via PostCSS
- **Custom Styles**: If custom CSS is needed, add it to `frontend/src/app.css` or use Svelte `<style>` blocks with scoped styles
