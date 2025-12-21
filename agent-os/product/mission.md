# Trellis Data Model - Product Mission

## Vision Statement

Trellis is a lightweight, local-first tool that bridges Conceptual Data Modeling, Logical Data Modeling, and Physical Implementation. We empower Analytics Engineers and Data Teams to maintain visual data models that stay in sync with their transformation code, eliminating the disconnect between business concepts and technical implementation.

## Core Problem We Solve

**The Data Modeling Gap:**
- ERD diagrams live in separate tools (Lucidchart, draw.io) and quickly become stale or unreadable for large projects
- Data transformations are done isolated from the conceptual data model
- No single view connecting business concepts to logical schema
- Stakeholders can't easily understand model structure without technical context
- Holistic Data Warehouse Automation Tools exist but don't integrate well with dbt and the Modern Data Stack

## Our Solution

Trellis provides a **visual data model editor** that:
- **Stays in sync** — reads directly from dbt `manifest.json` / `catalog.json`
- **Bidirectional workflow** — sketch entities and fields to auto-generate `schema.yml` files, or load existing dbt models to visualize and document
- **Relationship mapping** — draw relationships on canvas → auto-generates dbt `relationships` tests
- **Dual views** — toggle between **Conceptual** (entity names, descriptions) and **Logical** (columns, types, materializations) views
- **Organization** — organize entities based on subdirectories and tags from your physical implementation
- **Round-trip editing** — write descriptions and tags back to your dbt project

## Target Users

### Primary Personas

1. **Analytics Engineers**
   - Work daily with dbt-core
   - Need to visualize and document their data models
   - Want to maintain consistency between conceptual design and implementation
   - Value local-first, privacy-focused tools

2. **Data Engineers**
   - Design and maintain complex data warehouse schemas
   - Need to communicate data models to stakeholders
   - Require tools that integrate with existing dbt workflows

3. **Data Modelers**
   - Focus on conceptual and logical modeling
   - Need to bridge the gap between business requirements and technical implementation
   - Want tools that support both greenfield and brownfield projects

### Secondary Personas

4. **Data Stakeholders** (Business Analysts, Product Managers)
   - Need to understand data model structure without deep technical knowledge
   - Benefit from conceptual view of entities and relationships

## Core Values

1. **Local-First**: Your data stays on your machine. No cloud dependencies, no vendor lock-in.
2. **Tool-Agnostic Vision**: While currently focused on dbt-core, we believe "tools evolve, concepts don't" — data modeling concepts persist regardless of transformation framework.
3. **Developer Experience**: Seamless integration with existing dbt workflows. No disruption to current processes.
4. **Visual Clarity**: Make complex data models understandable through intuitive visual representation.
5. **Bidirectional Sync**: Changes flow both ways — from code to visualization and from visualization to code.

## Success Metrics

- **Adoption**: Number of active dbt projects using Trellis
- **Workflow Integration**: Percentage of users who use Trellis as part of their regular dbt workflow
- **Model Coverage**: Average percentage of dbt models visualized in Trellis
- **User Satisfaction**: Feedback on ease of use and time saved vs. manual documentation

## Long-Term Vision

Trellis is currently designed and tested specifically for **dbt-core**, but the vision is to be tool-agnostic. As the saying goes: *"tools evolve, concepts don't"* — data modeling concepts persist regardless of the transformation framework you use.

**Future Framework Support** (if project gains traction):
- **dbt-fusion** through adapter support
- **Pydantic models** as a simple output format
- Other frameworks like SQLMesh or Bruin through adapter patterns

**Current Focus**: Making Trellis work exceptionally well with dbt-core.

## Differentiation

What makes Trellis unique:
- **Only tool** that provides true bidirectional sync with dbt-core
- **Local-first** approach — no cloud account required, complete privacy
- **Lightweight** — fast, responsive, doesn't require heavy infrastructure
- **Visual-first** — designed for visual thinkers who work better with diagrams
- **Modern Stack** — built with modern web technologies, not legacy desktop apps
