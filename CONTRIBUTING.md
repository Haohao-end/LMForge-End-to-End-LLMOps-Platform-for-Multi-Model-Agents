# Contributing to OpenAgent / 贡献指南

First off, thank you for taking the time to contribute to OpenAgent! 🎉

This guide describes how to set up the project, the conventions we follow, and
the pull request process. It applies to both code and documentation
contributions.

首先,感谢你愿意为 OpenAgent 做贡献!🎉

本指南说明如何搭建项目、我们遵循的规范以及 Pull Request 流程,适用于代码与文档贡献。

> Looking for the Code of Conduct? See [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
> 行为准则请见 [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)。

---

## Table of Contents / 目录

1. [Project Stack / 技术栈](#project-stack--技术栈)
2. [Before You Start / 开始之前](#before-you-start--开始之前)
3. [Development Setup / 开发环境搭建](#development-setup--开发环境搭建)
4. [Code Style / 代码规范](#code-style--代码规范)
5. [Branching Strategy / 分支策略](#branching-strategy--分支策略)
6. [Commit Messages / 提交信息](#commit-messages--提交信息)
7. [Testing / 测试](#testing--测试)
8. [Pull Request Process / Pull Request 流程](#pull-request-process--pull-request-流程)
9. [Issue Reporting / Issue 报告](#issue-reporting--issue-报告)
10. [Security Reports / 安全报告](#security-reports--安全报告)

---

## Project Stack / 技术栈

| Layer / 层 | Stack / 技术栈 |
| --- | --- |
| Backend / 后端 | Python 3.11+, Flask 3.x, SQLAlchemy, Celery, Flask-SocketIO |
| Frontend / 前端 | Vue 3, TypeScript, Vite, Pinia, Vue Flow, Arco Design, TailwindCSS |
| Data / 数据 | PostgreSQL, Redis, Weaviate, FAISS |
| AI / 智能体 | LangChain, LangGraph, workflow orchestration, A2A, MCP |
| Infra / 基础设施 | Docker Compose, Nginx |

## Before You Start / 开始之前

- Check open issues and pull requests to avoid duplicating work.
- For new features or large changes, open an issue first to discuss the design.
- Keep contributions focused: one feature or fix per pull request.

- 先查看已有的 issue 和 pull request,避免重复劳动。
- 新功能或大改动请先开 issue 讨论设计。
- 保持贡献聚焦:每个 pull request 只做一件事。

## Development Setup / 开发环境搭建

### 1. Clone / 克隆仓库

```bash
git clone https://github.com/Haohao-end/openagent.git
cd openagent
```

### 2. Backend / 后端

```bash
cd api
cp .env.example .env          # fill in the required keys / 填写必需的密钥
pip install -r requirements.txt
flask run --port 5001
```

Minimum required environment variables in `api/.env`:

`api/.env` 中必需的最小环境变量:

- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `WEAVIATE_API_KEY`
- `VITE_API_PREFIX`
- At least one provider key, e.g. `OPENAI_API_KEY` / `ATLASCLOUD_API_KEY` / `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY`

### 3. Frontend / 前端

```bash
cd ui
npm install
npm run serve                 # Vite dev server, default port 5173 / Vite 默认端口 5173
```

### 4. Full stack with Docker / 用 Docker 启动全栈

```bash
cd docker
docker compose up -d --build
```

| Service / 服务 | URL |
| --- | --- |
| Frontend / 前端 | http://localhost:3000 |
| API / 接口 | http://localhost:5001 |
| Nginx | http://localhost |

## Code Style / 代码规范

### Backend (Python) / 后端

- Follow [PEP 8](https://peps.python.org/pep-0008/) and keep imports sorted.
- Use type hints where practical.
- Do not commit secrets, tokens, or `.env` files.
- Add or update tests for changed behavior.

- 遵循 [PEP 8](https://peps.python.org/pep-0008/),保持导入有序。
- 适当使用类型注解。
- 不要提交密钥、token 或 `.env` 文件。
- 为改动行为新增或更新测试。

### Frontend (Vue 3 + TypeScript) / 前端

- Use the Composition API with `<script setup lang="ts">`.
- Do not use `any` unless unavoidable; prefer explicit types.
- Format with Prettier; lint with the project ESLint config.

- 使用 Composition API 与 `<script setup lang="ts">`。
- 避免使用 `any`,优先使用明确类型。
- 使用 Prettier 格式化,使用项目 ESLint 配置检查。

```bash
cd ui
npm run lint      # auto-fix / 自动修复
npm run format    # prettier write / prettier 格式化
npm run type-check
```

## Branching Strategy / 分支策略

Base your work on the latest `main`:

请基于最新的 `main` 分支开发:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <type>/<short-description>
```

Branch naming / 分支命名:

| Type / 类型 | Use case / 用途 | Example / 示例 |
| --- | --- | --- |
| `feature/` | New feature / 新功能 | `feature/workflow-node-export` |
| `fix/` | Bug fix / 缺陷修复 | `fix/openapi-stream-truncate` |
| `docs/` | Documentation only / 仅文档 | `docs/readme-bilingual-sync` |
| `chore/` | Tooling, deps, config / 工具、依赖、配置 | `chore/upgrade-langchain` |

## Commit Messages / 提交信息

We follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范:

```
<type>(<scope>): <subject>

<optional body / 可选正文>

<optional footer / 可选页脚>
```

Common types / 常用类型: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`.

Examples / 示例:

```
feat(workflow): add HTTP request node timeout config
fix(openapi): handle truncated SSE chunk on stream end
docs(readme): sync provider list in EN and ZH
chore(deps): upgrade langchain to 0.2.x
```

Tips / 提示:
- Use the imperative mood in the subject ("add", not "added").
- Reference issues in the footer when relevant (`Closes #123`).
- Keep the subject under 72 characters.

- 标题使用祈使语气("add",而非 "added")。
- 相关时在页脚引用 issue(`Closes #123`)。
- 标题控制在 72 字符以内。

## Testing / 测试

All contributions that change runtime behavior must pass the existing checks.
For documentation-only changes, tests are not required but rendering must be
verified.

所有改变运行时行为的贡献都必须通过现有检查;纯文档改动无需测试,但需验证渲染正确。

```bash
# Backend / 后端
cd api && pytest

# Frontend / 前端
cd ui && npm run type-check
cd ui && npm run lint
cd ui && npm run build
cd ui && npm run test:unit -- --run
```

If you add a feature, add a test alongside it.

新增功能时,请同步补充测试。

## Pull Request Process / Pull Request 流程

1. Make sure your branch is up to date with `main`:
   确保分支已与 `main` 同步:

   ```bash
   git fetch origin
   git rebase origin/main   # or merge if you prefer / 也可使用 merge
   ```

2. Push your branch:
   推送分支:

   ```bash
   git push -u origin <type>/<short-description>
   ```

3. Open a Pull Request against `main`.
   向 `main` 发起 Pull Request。

4. In the PR description, include:
   PR 描述中应包含:
   - **What changed / 改动了什么**
   - **Why / 为什么改**
   - **How to test / 如何测试**
   - **Screenshots or logs / 截图或日志(如适用)**

5. Make sure CI (type-check, lint, build, tests) passes.
   确保 CI(type-check、lint、build、tests)通过。

6. Address review feedback by pushing new commits (avoid force-pushing after
   review unless asked).
   通过提交新 commit 来回应评审意见(评审后请勿强推,除非被要求)。

A maintainer will review and merge. We may squash-merge small PRs.

维护者会评审并合并;小 PR 可能采用 squash-merge。

## Issue Reporting / Issue 报告

- Use the provided issue templates (bug report, feature request, or custom).
- 使用提供的 issue 模板(bug report、feature request 或自定义)。
- Bug reports must include reproduction steps, expected vs actual behavior,
  and environment details.
- Bug 报告须包含复现步骤、预期与实际行为、以及环境信息。
- Search existing issues before opening a new one.
- 开新 issue 前请先搜索已有 issue。

## Security Reports / 安全报告

Do **not** open a public issue for security vulnerabilities. See
[`SECURITY.md`](./SECURITY.md) and email **2227625024@qq.com**.

请**不要**为安全漏洞提交公开 issue,参见 [`SECURITY.md`](./SECURITY.md),并邮件至 **2227625024@qq.com**。

---

Thank you for helping make OpenAgent better! / 感谢你帮助 OpenAgent 变得更好!
