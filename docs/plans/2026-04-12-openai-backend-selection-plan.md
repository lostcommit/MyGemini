# OpenAI Backend + Backend Selection Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add support for OpenAI alongside Gemini and let each user choose the active backend and model from the UI/settings.

**Architecture:** Introduce a provider-agnostic chat backend layer with a small stable service API (`generate_response`, `generate_content_simple`, `validate_api_key`, `get_available_models`). Keep existing Gemini behavior working by moving provider-specific logic behind adapters. Store `llm_backend` + provider-specific model/API key settings in `users`, then route runtime calls through a backend router.

**Tech Stack:** Python, async services, existing SQLite migrations, current service-layer architecture (`settings_service`, `dialog_service`, `gemini_*` modules), Telegram handlers.

---

## 0. Constraints and decisions

Before implementation, assume these rules unless product requirements change:

1. Supported backends in phase 1:
   - `gemini`
   - `openai`

2. Backend selection is per-user, not global.

3. API keys are per-user and provider-specific:
   - keep existing `api_key` column as Gemini key for backward compatibility in phase 1 migration
   - add separate OpenAI key storage column instead of overloading one field

4. Model selection is backend-specific:
   - Gemini users keep current `gemini_model`
   - OpenAI gets a dedicated `openai_model`

5. Existing public service contract should stay stable for handlers:
   - handlers should eventually depend on a provider-agnostic service facade, not on `gemini_service`

6. Non-goals for phase 1:
   - tool calling/function calling
   - image generation
   - embeddings
   - streaming responses
   - assistant threads API

---

## 1. Target architecture

### New modules

- `services/llm_backends.py`
  - backend constants / registry
  - helper metadata for UI labels

- `services/llm_service.py`
  - provider-agnostic facade used by handlers and settings flows

- `services/openai_client.py`
  - low-level OpenAI HTTP client/session/retries/errors

- `services/openai_request_builder.py`
  - build OpenAI chat/completions payloads from current prompt types

- `services/openai_response_parser.py`
  - normalize OpenAI responses into the same internal output shape

- `services/openai_runtime_context.py`
  - load OpenAI runtime context if provider-specific differences are needed

Optional if needed:
- `services/openai_history_cache.py`
  - only if OpenAI needs a different cached history shape than Gemini
  - preferably avoid this in phase 1; reuse dialog history from DB and adapt in request builder

### Existing modules to extend

- `config/settings.py`
- `database/migrations.py`
- `database/users_repo.py`
- `database/db_manager.py`
- `services/settings_service.py`
- `handlers/callback_handlers.py`
- `handlers/message_handlers.py`
- `utils/markup_helpers.py`
- `utils/localization.py`
- maybe `features/personal_account.py` if backend/model should be shown there

### Service flow after refactor

`handlers/*`
→ `services/llm_service.py`
→ backend router (`gemini_service` or `openai_service`/OpenAI adapter)
→ normalized `(response_text, sources)` result

This keeps Telegram/UI logic ignorant of provider-specific details.

---

## 2. Data model changes

### Current state

`users` currently has:
- `api_key` (Gemini key effectively)
- `gemini_model`
- no backend selector
- no OpenAI-specific key/model

### Proposed schema additions

Add columns to `users`:
- `llm_backend TEXT DEFAULT 'gemini' NOT NULL`
- `openai_api_key TEXT DEFAULT NULL`
- `openai_model TEXT DEFAULT NULL`

Keep existing columns:
- `api_key` → interpreted as Gemini API key in phase 1
- `gemini_model` → unchanged

### Migration rules

For existing users:
- `llm_backend = 'gemini'`
- existing `api_key` remains valid and untouched
- existing `gemini_model` remains valid and untouched
- `openai_*` fields start as NULL

### Repository methods to add

In `database/users_repo.py`:
- `set_user_llm_backend(user_id: int, backend: str)`
- `get_user_llm_backend(user_id: int) -> str`
- `set_user_openai_api_key(user_id: int, api_key: Optional[str])`
- `get_user_openai_api_key(user_id: int) -> Optional[str]`
- `set_user_openai_model(user_id: int, model_name: str)`
- `get_user_openai_model(user_id: int) -> Optional[str]`

In `database/db_manager.py`:
- export all new methods

---

## 3. Provider abstraction design

### Provider-agnostic interface

Create a thin contract that both backends satisfy:

- `generate_response(user_id, prompt) -> tuple[str, list[dict[str, str]]]`
- `generate_content_simple(api_key, prompt) -> str`
- `validate_api_key(api_key) -> bool`
- `get_available_models(api_key) -> list[dict[str, str]]`

### llm_service responsibilities

`services/llm_service.py` should:
- read user backend from DB
- dispatch to the correct backend service
- expose a stable API for handlers/settings
- expose backend-aware helper methods for settings UI

Recommended facade methods:
- `generate_response(user_id, prompt)`
- `generate_content_simple_for_user(user_id, prompt)` only if needed later
- `validate_api_key_for_backend(backend, api_key)`
- `get_available_models_for_backend(backend, api_key)`
- `get_user_backend(user_id)`
- `set_user_backend(user_id, backend)`

Important:
- do not let handlers decide backend routing directly
- handlers should ask `settings_service` / `llm_service`, not `gemini_service`

---

## 4. OpenAI provider design

### API choice

Use Chat Completions-compatible endpoint first.

Reason:
- simplest parity with current architecture
- straightforward text + image support
- easy model listing and validation strategy

### OpenAI payload mapping

Current Gemini input shape:
- text: `str`
- image flow: `[caption, PIL.Image.Image]`
- voice flow: `[prompt_text, bytes]`

Phase 1 recommendation:
- text: supported
- image: supported if mapped to image input content items
- voice: do NOT claim full support until verified against chosen OpenAI endpoint
  - safest phase-1 path: for OpenAI backend return a clear “voice unsupported for selected backend yet” error
  - or route voice through local STT first in a later phase

### OpenAI modules

`services/openai_client.py`
- shared aiohttp session
- retry logic mirroring `gemini_client.py`
- `OpenAIAPIError`
- methods for POST/GET requests

`services/openai_request_builder.py`
- convert user prompt/history to OpenAI `messages`
- map system instruction/persona/style into `system` message
- map images to OpenAI-compatible content parts

`services/openai_response_parser.py`
- extract assistant text
- normalize token usage into:
  - `prompt_tokens`
  - `completion_tokens`
  - `total_tokens`
- return `sources=[]` for now unless web-search/citation support is later added

### OpenAI model listing

Use `/models` and filter to chat-capable models via allowlist/metadata mapping.

Do not rely on raw `/models` output alone for UI.
Keep an allowlist in config or backend metadata, e.g.:
- `gpt-4.1-mini`
- `gpt-4.1`
- `gpt-4o-mini`
- `gpt-4o`

This avoids exposing irrelevant or unsupported IDs.

---

## 5. Backend selection UX

### Settings UI changes

Add a backend selection entry to settings menu.

Expected user flow:
1. Open settings
2. Choose “Backend”
3. Choose Gemini or OpenAI
4. If API key for selected backend is missing:
   - prompt user to set that backend’s API key
5. After backend selection, model selection menu should show models only for active backend

### Callback/data additions

Add config constants in `config/settings.py`:
- `CALLBACK_SETTINGS_BACKEND_MENU`
- `CALLBACK_SETTINGS_BACKEND_PREFIX`

Possible values:
- `settings_backend_menu`
- `settings_backend_` + backend id

### Markup helpers

In `utils/markup_helpers.py` add:
- `create_backend_selection_keyboard(user_id)`

Display:
- current backend mark
- friendly labels, e.g. “Google Gemini”, “OpenAI”

### Localization

Add texts in `utils/localization.py` for:
- backend selection title
- backend selection description
- backend changed success notice
- API key required for selected backend
- unsupported content for selected backend if needed

---

## 6. Settings flow changes

### settings_service evolution

Current `settings_service` is Gemini-specific in API validation and model listing.

Refactor it to provider-aware methods:

- `set_backend(user_id, backend) -> bool`
- `get_backend_selection_context(user_id) -> tuple[list, str]`
- `validate_and_store_api_key(user_id, backend, api_key) -> bool`
- `reset_user_api_key(user_id, backend) -> bool`
- `set_model(user_id, model_name) -> str`
- `get_model_selection_context(user_id) -> tuple[Optional[list], Optional[str]]`

Behavior rules:
- model context should use the user’s active backend
- API key validation should use the selected backend
- changing backend should reset active dialog cache/history to avoid mixed-provider context interpretation

### API key state handling

Current `/set_api_key` flow is ambiguous once multiple providers exist.

Need one of these designs:

Option A — recommended:
- `/set_api_key` updates key for current backend
- backend-specific settings screen clearly shows which backend is active
- text prompt includes backend name

Option B:
- add explicit commands later (`/set_openai_key`, `/set_gemini_key`)
- keep current `/set_api_key` as shortcut for current backend

---

## 7. Message handling changes

### Current state

`handlers/message_handlers.py` directly calls:
- `gemini_service.generate_response(...)`
- `gemini_service.generate_content_simple(...)` for translation

### Target state

Replace with provider-agnostic calls:
- `llm_service.generate_response(...)`
- for translation, either:
  - keep Gemini-only if product wants that, or
  - route through current user backend, or
  - always use active backend with a single normalized helper

Recommendation:
- use active backend consistently everywhere user-facing LLM text is generated
- do not keep translation hardcoded to Gemini unless there is a product reason

### Voice handling caveat

Plan for OpenAI backend must explicitly decide what happens to voice:

Recommended phase 1:
- if backend = Gemini → current behavior unchanged
- if backend = OpenAI and content_type = voice:
  - return localized message: voice for OpenAI backend not supported yet

This keeps rollout safe and honest.

---

## 8. Config changes

In `config/settings.py` add:
- `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")` only if there is a system/admin key use-case
- `DEFAULT_LLM_BACKEND = os.getenv("DEFAULT_LLM_BACKEND", "gemini")`
- `OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")`

Also add backend metadata maps, e.g.:
- `SUPPORTED_LLM_BACKENDS`
- `BACKEND_DISPLAY_NAMES`
- `OPENAI_MODELS_METADATA` (if needed)

Important product decision:
- if all keys are strictly per-user, `OPENAI_API_KEY` env var may be unnecessary in phase 1
- mention this explicitly in implementation notes to avoid accidental mixed auth modes

---

## 9. Testing strategy

### New test files

Add:
- `tests/test_openai_client.py`
- `tests/test_openai_request_builder.py`
- `tests/test_openai_response_parser.py`
- `tests/test_llm_service.py`
- `tests/test_backend_selection_settings.py`
- `tests/test_gemini_history_cache.py` already exists and should remain green

### Extend existing tests

Update:
- `tests/test_settings_service.py`
- `tests/test_refactor_smoke.py`
- `tests/test_dialog_service.py` only if backend changes require cache reset assertions

### Minimum acceptance test matrix

1. Existing Gemini user with old DB:
   - still chats successfully
   - existing API key still works
   - existing model still works

2. New user default backend:
   - gets `DEFAULT_LLM_BACKEND`
   - can set API key for that backend

3. Switch to OpenAI:
   - backend saved
   - model menu shows OpenAI models only
   - text chat routes to OpenAI service

4. Switch back to Gemini:
   - Gemini models shown again
   - existing history cache cleared on switch

5. Validation errors:
   - invalid OpenAI key rejected
   - invalid Gemini key rejected
   - missing key blocks chat for active backend

6. Voice behavior:
   - Gemini path preserved
   - OpenAI path returns explicit unsupported message if phase-1 unsupported

---

## 10. Detailed implementation sequence

### Phase A — schema and repository layer

1. Update `database/migrations.py`
   - add missing-user-column migration support for:
     - `llm_backend`
     - `openai_api_key`
     - `openai_model`

2. Update `database/users_repo.py`
   - add getters/setters for backend and OpenAI-specific fields
   - keep encryption for `openai_api_key` identical to existing `api_key`

3. Update `database/db_manager.py`
   - export new repository functions

4. Add tests for migration/backward compatibility

### Phase B — backend metadata and facade

5. Create `services/llm_backends.py`
   - backend IDs
   - display names
   - validation helpers

6. Create `services/llm_service.py`
   - dispatch to Gemini/OpenAI implementations
   - keep public methods stable

7. Update `services/settings_service.py`
   - remove direct Gemini assumptions
   - route validation/model listing via `llm_service`

### Phase C — OpenAI backend implementation

8. Create `services/openai_client.py`
9. Create `services/openai_request_builder.py`
10. Create `services/openai_response_parser.py`
11. Create `services/openai_service.py` or implement OpenAI adapter functions in `llm_service.py`

Recommendation:
- create `services/openai_service.py` to mirror current `gemini_service.py`
- keep parity with current service organization

### Phase D — UI/settings integration

12. Extend `config/settings.py` callback constants and backend metadata
13. Extend `utils/localization.py` backend-related strings
14. Extend `utils/markup_helpers.py` backend selection keyboard
15. Update `handlers/callback_handlers.py`
   - add backend selection menu and backend switch callback
16. Update `handlers/command_handlers.py` if settings/help text needs changes

### Phase E — message routing

17. Update `handlers/message_handlers.py`
   - replace direct Gemini calls with `llm_service`
   - add active-backend-specific behavior for translation and voice

### Phase F — cleanup

18. Remove Gemini-specific assumptions from remaining handlers/services
19. Add/update docs
20. Run full tests and manual Telegram flow verification

---

## 11. Exact file change map

### Create
- `services/llm_backends.py`
- `services/llm_service.py`
- `services/openai_client.py`
- `services/openai_request_builder.py`
- `services/openai_response_parser.py`
- `services/openai_service.py` (recommended)
- `tests/test_openai_client.py`
- `tests/test_openai_request_builder.py`
- `tests/test_openai_response_parser.py`
- `tests/test_llm_service.py`
- `tests/test_backend_selection_settings.py`

### Modify
- `config/settings.py`
- `database/migrations.py`
- `database/users_repo.py`
- `database/db_manager.py`
- `services/settings_service.py`
- `handlers/callback_handlers.py`
- `handlers/message_handlers.py`
- `utils/markup_helpers.py`
- `utils/localization.py`
- possibly `features/personal_account.py`

### Keep but adapt
- `services/gemini_service.py`
- existing `services/gemini_*` helper modules

---

## 12. Risks and mitigations

### Risk 1: Mixed-provider history semantics

Problem:
- existing dialog history may contain turns generated by Gemini, then backend switches to OpenAI

Mitigation:
- on backend switch, clear cached history immediately
- optionally consider starting a fresh dialog on backend switch in a later phase
- for phase 1, cache reset is minimum required

### Risk 2: API key ambiguity

Problem:
- current `/set_api_key` doesn’t say which provider it targets

Mitigation:
- tie it to current backend and show backend name in prompt
- add backend-specific labels in settings UI

### Risk 3: OpenAI feature mismatch for media

Problem:
- text/image parity is straightforward; voice is not

Mitigation:
- explicitly scope voice support out of OpenAI phase 1 unless fully implemented and tested

### Risk 4: Hardcoded Gemini naming in DB and code

Problem:
- `gemini_model` is provider-specific and leaks into generic flows

Mitigation:
- do not rename immediately if you want low-risk rollout
- add generic backend layer first
- consider later migration to `selected_model` only after stable multi-backend support

---

## 13. Recommended implementation decisions

To keep rollout safe, use this exact strategy:

1. Do not replace `gemini_service`; wrap it.
2. Add OpenAI as a parallel provider.
3. Add `llm_service` as the only handler-facing entry point.
4. Keep provider-specific DB fields in phase 1.
5. Keep current user experience unchanged for existing Gemini users.
6. Treat OpenAI voice support as out of scope unless explicitly required.

This is the lowest-risk path.

---

## 14. Definition of done

Feature is done when:

- user can choose `Gemini` or `OpenAI` in settings
- active backend is saved per user
- user can set/validate API key for chosen backend
- user can choose a model for chosen backend
- text chat works through both backends
- existing Gemini users continue working without migration pain
- automated tests cover routing, persistence, and backend-specific parsing
- full `python -m pytest -q` passes

---

## 15. Suggested first implementation PR split

### PR 1
Schema + repo support:
- migrations
- users_repo/db_manager
- tests

### PR 2
OpenAI provider internals:
- openai_client
- openai_request_builder
- openai_response_parser
- openai_service
- tests

### PR 3
Provider router + settings integration:
- llm_backends
- llm_service
- settings_service changes
- callback/settings UI
- tests

### PR 4
Message routing + cleanup:
- message_handlers switched to llm_service
- translation/backend cleanup
- docs/tests

This split keeps reviews manageable and rollback easy.
