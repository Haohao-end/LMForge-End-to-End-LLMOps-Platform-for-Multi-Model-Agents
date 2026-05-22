# Atlas Cloud Provider Review

## Summary

- Added an `atlascloud` provider to the backend language model registry.
- Implemented an OpenAI-compatible Atlas Cloud chat adapter with env-based key and base URL resolution.
- Registered the `deepseek-v3-0324` Atlas Cloud model for chat usage, mapped to `deepseek-ai/DeepSeek-V3-0324`.
- Updated `api/.env.example` with Atlas Cloud configuration entries.
- Added the Atlas Cloud logo to the repository and referenced it from `README.md`.

## Files Changed

- `api/internal/core/language_model/providers/providers.yaml`
- `api/internal/core/language_model/providers/atlascloud/__init__.py`
- `api/internal/core/language_model/providers/atlascloud/chat.py`
- `api/internal/core/language_model/providers/atlascloud/positions.yaml`
- `api/internal/core/language_model/providers/atlascloud/deepseek-v3-0324.yaml`
- `api/.env.example`
- `README.md`
- `api/test/internal/core/language_model/test_language_model_core.py`

## Provider Behavior

- Reads `ATLASCLOUD_API_KEY` first, then falls back to `ATLAS_CLOUD_API_KEY`.
- Reads `ATLASCLOUD_API_BASE` first, then falls back to `ATLAS_CLOUD_API_BASE`.
- Uses `https://api.atlascloud.ai/v1` as the default OpenAI-compatible base URL.
- Supports regular chat completion and streaming through the existing `ChatOpenAI` integration path.

## Validation Plan

- Run focused backend tests covering Atlas Cloud env resolution and provider registry loading.
- Persist the Atlas Cloud key locally in `api/.env`.
- Execute a local, uncommitted integration script against Atlas Cloud to verify:
  - non-stream chat completion
  - streaming output
  - provider instantiation through the project codepath
