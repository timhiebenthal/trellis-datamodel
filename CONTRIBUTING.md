# Contributing to Trellis Datamodel

Thanks for helping improve Trellis Datamodel! This guide explains how to contribute and the expectations for inbound licensing.

## Licensing
- The project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). By contributing, you agree that your contributions are released under AGPL-3.0.
- See `LICENSE` for full terms and `NOTICE` for summary information.

## Contributor License Agreement (CLA)
- All pull requests must be covered by a signed CLA.
- The CLA workflow is automated via GitHub Actions. When you open a PR, a bot will prompt you to sign by adding a comment like:  
  `I have read the CLA Document and I hereby sign the CLA`
- You only need to sign once per GitHub account; the signature is stored in `.github/cla/signatures.json`.
- If you contribute on behalf of a company, ensure you are authorized. If your organization needs a separate corporate CLA, contact the maintainers.

## Developer Certificate of Origin (DCO) (optional but recommended)
- Use `Signed-off-by: Your Name <you@example.com>` in commits (`git commit -s`) to document authorship and intent. This is helpful but not enforced by CI today.

## How to contribute
1. **Fork & branch**: Create a branch from `main`.
2. **Run tests** before submitting:
   - Backend: `uv run pytest`
   - Frontend: `cd frontend && npm run test:smoke` (or `npm run test` for full)
3. **Lint/format**: Follow existing project conventions.
4. **PR guidelines**:
   - Keep PRs focused and include context in the description.
   - Update docs and changelog entries when behavior or interfaces change.
   - Ensure CI passes (including the CLA check).

## Reporting issues
- Use GitHub issues with clear reproduction steps, expected vs. actual behavior, and environment details.

## Communication
- For questions or corporate CLA requests, open an issue or reach out to the maintainers.

