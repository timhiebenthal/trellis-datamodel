## Responsive design best practices (Tailwind CSS)

This project uses Tailwind CSS with mobile-first responsive design. Follow these conventions:

- **Mobile-First Development**: Start with mobile layout (base styles) and progressively enhance for larger screens using Tailwind breakpoints
- **Tailwind Breakpoints**: Use Tailwind's standard breakpoints consistently:
  - `sm:` - 640px and up
  - `md:` - 768px and up
  - `lg:` - 1024px and up
  - `xl:` - 1280px and up
  - `2xl:` - 1536px and up
- **Responsive Utilities**: Use Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`, etc.) for breakpoint-specific styles
- **Flexible Layouts**: Use Tailwind's flexbox and grid utilities (`flex`, `grid`) for responsive layouts
- **Relative Units**: Tailwind uses rem units by default; use Tailwind spacing scale for consistent sizing
- **Test Across Devices**: Test UI changes across multiple screen sizes using browser dev tools and Playwright viewport testing
- **Touch-Friendly Design**: Use Tailwind's sizing utilities to ensure tap targets are appropriately sized (minimum 44x44px)
- **Performance**: Tailwind's utility classes are optimized for production; avoid unnecessary custom CSS
- **Readable Typography**: Use Tailwind's typography utilities (`text-sm`, `text-base`, `text-lg`, etc.) for consistent font sizes
- **Content Priority**: Use Tailwind's display utilities (`hidden`, `block`, `md:flex`) to show/hide content based on screen size
