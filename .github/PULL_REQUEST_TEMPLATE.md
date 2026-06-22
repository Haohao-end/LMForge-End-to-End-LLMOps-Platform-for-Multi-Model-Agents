## Description

<!-- What does this PR do? Provide a clear summary of the changes. -->

## Related Issue

<!-- Link the issue this PR addresses. Use "Closes #123" to auto-close. -->
Closes #

## Motivation and Context

<!-- Why is this change needed? What problem does it solve? -->

## Type of Change

<!-- Check all that apply. -->
- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `docs` — Documentation only
- [ ] `refactor` — Code change that neither fixes a bug nor adds a feature
- [ ] `perf` — Performance improvement
- [ ] `test` — Adding or correcting tests
- [ ] `chore` — Tooling, deps, config
- [ ] 💥 Breaking change — would cause existing functionality to not work as expected

## Changes Made

<!-- Bullet list of the key changes. -->
-
-
-

## How to Test

<!-- Step-by-step instructions so a reviewer can verify the change. -->
1.
2.
3.

## Screenshots / Recordings

<!-- For UI changes, attach before/after screenshots or recordings. -->

## Impact

<!-- Does this PR affect any of the following? Check all that apply. -->
- [ ] Backend API (REST/SSE endpoints changed or added)
- [ ] Database (migrations, schema changes)
- [ ] Frontend (UI/UX, components, routes)
- [ ] Configuration (env vars, Docker, Nginx)
- [ ] Dependencies (requirements.txt, package.json)
- [ ] Documentation

## Checklist

<!-- Confirm before requesting review. -->
- [ ] I have self-reviewed my code.
- [ ] My code follows the project style (PEP 8 for Python; Composition API with `<script setup lang="ts">` for Vue).
- [ ] I have added or updated tests for changed behavior.
- [ ] Tests pass:
  - [ ] `cd api && pytest`
  - [ ] `cd ui && npm run test:unit -- --run`
- [ ] Quality gates pass:
  - [ ] `cd ui && npm run type-check`
  - [ ] `cd ui && npm run lint`
  - [ ] `cd ui && npm run build`
- [ ] I have NOT committed secrets, tokens, or `.env` files.
- [ ] My commits follow [Conventional Commits](https://www.conventionalcommits.org/).
- [ ] I have updated documentation where relevant.
