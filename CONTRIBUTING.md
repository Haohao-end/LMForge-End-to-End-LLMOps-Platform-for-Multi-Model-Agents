# Contributing to OpenAgent

First off, thank you for taking the time to contribute to OpenAgent! 🎉

This guide describes how to set up the project, the conventions we follow, and
the pull request process. It applies to both code and documentation
contributions.

> Looking for the Code of Conduct? See [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

---

## Table of Contents

1. [Project Stack](#project-stack)
2. [Before You Start](#before-you-start)
3. [Development Setup](#development-setup)
4. [Code Style](#code-style)
5. [Branching Strategy](#branching-strategy)
6. [Commit Messages](#commit-messages)
7. [Testing](#testing)
8. [Pull Request Process](#pull-request-process)
9. [Issue Reporting](#issue-reporting)
10. [Security Reports](#security-reports)

---

## Project Stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11+, Flask 3.x, SQLAlchemy, Celery, Flask-SocketIO |
| Frontend | Vue 3, TypeScript, Vite, Pinia, Vue Flow, Arco Design, TailwindCSS |
| Data | PostgreSQL, Redis, Weaviate, FAISS |
| AI | LangChain, LangGraph, workflow orchestration, A2A, MCP |
| Infra | Docker Compose, Nginx |

## Before You Start

- Check open issues and pull requests to avoid duplicating work.
- For new features or large changes, open an issue first to discuss the design.
- Keep contributions focused: one feature or fix per pull request.

## Development Setup

### 1. Clone

```bash
git clone https://github.com/Haohao-end/openagent.git
cd openagent
```

### 2. Backend

```bash
cd api
cp .env.example .env          # fill in the required keys
pip install -r requirements.txt
flask run --port 5001
```

Minimum required environment variables in `api/.env`:

- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `WEAVIATE_API_KEY`
- `VITE_API_PREFIX`
- At least one provider key, e.g. `OPENAI_API_KEY` / `ATLASCLOUD_API_KEY` / `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY`

### 3. Frontend

```bash
cd ui
npm install
npm run serve                 # Vite dev server, default port 5173
```

### 4. Full stack with Docker

```bash
cd docker
docker compose up -d --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:5001 |
| Nginx | http://localhost |

## Code Style

### Backend (Python)

- Follow [PEP 8](https://peps.python.org/pep-0008/) and keep imports sorted.
- Use type hints where practical.
- Do not commit secrets, tokens, or `.env` files.
- Add or update tests for changed behavior.

### Frontend (Vue 3 + TypeScript)

- Use the Composition API with `<script setup lang="ts">`.
- Do not use `any` unless unavoidable; prefer explicit types.
- Format with Prettier; lint with the project ESLint config.

```bash
cd ui
npm run lint      # auto-fix
npm run format    # prettier write
npm run type-check
```

## Branching Strategy

Base your work on the latest `main`:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <type>/<short-description>
```

Branch naming:

| Type | Use case | Example |
| --- | --- | --- |
| `feature/` | New feature | `feature/workflow-node-export` |
| `fix/` | Bug fix | `fix/openapi-stream-truncate` |
| `docs/` | Documentation only | `docs/readme-sync` |
| `chore/` | Tooling, deps, config | `chore/upgrade-langchain` |

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<optional body>

<optional footer>
```

Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`.

Examples:

```
feat(workflow): add HTTP request node timeout config
fix(openapi): handle truncated SSE chunk on stream end
docs(readme): sync provider list
chore(deps): upgrade langchain to 0.2.x
```

Tips:
- Use the imperative mood in the subject ("add", not "added").
- Reference issues in the footer when relevant (`Closes #123`).
- Keep the subject under 72 characters.

## Testing

All contributions that change runtime behavior must pass the existing checks.
For documentation-only changes, tests are not required but rendering must be
verified.

```bash
# Backend
cd api && pytest

# Frontend
cd ui && npm run type-check
cd ui && npm run lint
cd ui && npm run build
cd ui && npm run test:unit -- --run
```

If you add a feature, add a test alongside it.

## Pull Request Process

1. Make sure your branch is up to date with `main`:

   ```bash
   git fetch origin
   git rebase origin/main   # or merge if you prefer
   ```

2. Push your branch:

   ```bash
   git push -u origin <type>/<short-description>
   ```

3. Open a Pull Request against `main`.

4. In the PR description, include:
   - **What changed**
   - **Why**
   - **How to test**
   - **Screenshots or logs** (if applicable)

5. Make sure CI (type-check, lint, build, tests) passes.

6. Address review feedback by pushing new commits (avoid force-pushing after
   review unless asked).

A maintainer will review and merge. We may squash-merge small PRs.

## Issue Reporting

- Use the provided issue templates (bug report, feature request, or custom).
- Bug reports must include reproduction steps, expected vs actual behavior,
  and environment details.
- Search existing issues before opening a new one.

## Security Reports

Do **not** open a public issue for security vulnerabilities. See
[`SECURITY.md`](./SECURITY.md) and email **2227625024@qq.com**.

---

Thank you for helping make OpenAgent better!
