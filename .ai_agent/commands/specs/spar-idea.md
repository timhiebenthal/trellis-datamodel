# Idea Validation Process

Validate and refine new idea. Goal: analyze project state, challenge idea, ask clarifying questions → well-formed spec.

## Process

1. Analyze Current Project State
2. Challenge the Idea
3. Ask Clarification Questions
4. Document Findings

## Step 1: Analyze Current Project State

Read:
- `.cursor/project.md` — mission + tech stack
- Codebase structure — current implementation
- Recent changes — if related to existing features

## Step 2: Challenge the Idea

Evaluate:
- **Alignment**: Matches mission/values?
- **Feasible**: Tech stack supports?
- **Scope**: Appropriate? Too broad/narrow?
- **Dependencies**: Prerequisites needed?
- **Impact**: Affect existing functionality?
- **Alternatives**: Simpler approaches?

Present analysis to user:
- Risks/concerns
- Areas needing clarification
- Refinement suggestions

## Step 3: Ask Clarification Questions

Based on analysis, ask targeted questions:

- **Scope**: What's included/excluded?
- **UX**: How do users interact?
- **Edge Cases**: Error scenarios to handle?
- **Success Criteria**: How measure success?
- **Priority**: Urgent or can wait?

Ask 3-5 focused questions. Wait for response.

## Step 4: Document Findings

After clarification, summarize:

- **Idea Summary**: Clear description
- **Key Decisions**: Choices/constraints identified
- **Open Questions**: Remaining uncertainties
- **Next Steps**: Recommendation (usually `/create-specs`)

Save format:
- Temporary note in conversation
- Ask user if save to file
- Proceed to `/create-specs` if ready

## Guidelines

- Constructive but critical — challenge assumptions
- Focus on clarity and feasibility
- Keep questions actionable
- Don't skip challenging phase
- Reference `.cursor/project.md`