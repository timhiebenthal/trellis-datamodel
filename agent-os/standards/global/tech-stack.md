## Tech stack

Define your technical stack below. This serves as a reference for all team members and helps maintain consistency across the project.

### Framework & Runtime
- **Application Framework:** [e.g., Rails, Django, Next.js, Express]
- **Language/Runtime:** The end user is an Analytics Engineering Profile. Therefore Python and SQL (dbt) are the usual setup he's working with
- **Package Manager:** Let's use `uv` for package and python environment management unless specified otherwise (devcontainer)

### Frontend
- **JavaScript Framework:** Use SvelteKit unless specified otherwise or other frameworks offer an significant advantage.
- **CSS Framework:** favor Tailwind CSS
- **UI Components:** [e.g., shadcn/ui, Material UI, custom library]

### Database & Storage
- **Database:** Use duckDB as a local default unless specified otherwise
- **Storage** Store data in a dedicated /data-directory and ask if it should be git-tracked


### Testing & Quality
- **Test Framework:** [e.g., Jest, RSpec, pytest]
- **Linting/Formatting:** [e.g., ESLint, Prettier, RuboCop]

### Deployment & Infrastructure
- **Hosting:** Google Cloud
- **CI/CD:** Github Actions

