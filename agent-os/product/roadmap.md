# Trellis Data Model - Product Roadmap

## Roadmap Overview

This roadmap outlines the development plan for Trellis based on **documented features and explicit vision statements**. Features are organized by implementation status and explicit future plans mentioned in the project documentation.

## Phase 1: Core Features (Implemented) ✅

**Status**: Completed  
**Version**: 0.3.4 (Beta)

### Implemented Features (from README and codebase)
- ✅ Visual ERD canvas with entity and relationship visualization
- ✅ Bidirectional sync with dbt manifest.json and catalog.json
- ✅ Conceptual and Logical view toggle
- ✅ Auto-generation of dbt schema.yml files
- ✅ Auto-generation of dbt relationship tests
- ✅ Entity organization by subdirectories and tags
- ✅ Write descriptions and tags back to dbt project
- ✅ Local-first architecture with no cloud dependencies
- ✅ CLI interface (`trellis run`, `trellis init`)
- ✅ Relationship inference from existing dbt relationship tests
- ✅ Folder and tag filtering
- ✅ Undo/redo functionality
- ✅ Entity expand/collapse
- ✅ Frontend testing infrastructure (Vitest, Playwright)

### Known Issues & Improvements (from CHANGELOG)
- Performance optimization for large dbt projects
- Enhanced error handling and user feedback
- Improved canvas layout algorithms
- Better handling of complex relationship patterns

## Phase 2: Framework Expansion (Future Vision)

**Goal**: Expand beyond dbt-core to support multiple transformation frameworks  
**Status**: Aspirational - depends on project traction  
**Source**: Explicitly mentioned in README.md "Vision" section

### Planned Framework Support (from README)
- [ ] **dbt-fusion** through adapter support
- [ ] **Pydantic models** as a simple output format
- [ ] **SQLMesh** adapter (if compatible)
- [ ] **Bruin** adapter (if compatible)

**Note**: These are explicitly mentioned in the README vision section. The README states: *"If this project gains traction, we might explore support for..."*

## Future Considerations

### Potential Enhancements (Not Yet Planned)
The following are common patterns in data modeling tools but are **not explicitly documented** as planned features. They may be considered based on:
- User feedback via GitHub Issues
- Community requests
- Project traction and resources

**Examples** (not committed):
- Export to PNG/SVG/PDF
- VS Code extension
- Real-time collaboration features
- Data lineage visualization
- Performance optimizations for 1000+ model projects

## Feature Prioritization

### How Features Are Added to Roadmap

1. **Explicit Documentation**: Features mentioned in README.md vision section
2. **GitHub Issues**: User-requested features tracked in GitHub Issues
3. **Community Feedback**: Features requested through community channels
4. **Technical Needs**: Improvements needed for stability/performance

### Prioritization Criteria

When evaluating new features:
1. **User Impact**: How many users benefit? How significant is the benefit?
2. **Workflow Integration**: Does it improve daily workflow or remove friction?
3. **Technical Feasibility**: Can we build it with current resources?
4. **Strategic Alignment**: Does it advance the mission and vision?
5. **Dependencies**: Are there blocking dependencies or prerequisites?

## Notes

- **Current Version**: 0.3.4 (Beta)
- **Stability Focus**: Current focus is on making Trellis work well with dbt-core
- **Framework Expansion**: Phase 2 is aspirational and depends on project traction (as stated in README)
- **Flexibility**: Roadmap is subject to change based on user needs and feedback
- **Source Transparency**: This roadmap only includes features that are:
  - ✅ Already implemented (Phase 1)
  - 📋 Explicitly mentioned in project documentation (Phase 2)
  - 💡 Suggested as potential future considerations (not committed)
