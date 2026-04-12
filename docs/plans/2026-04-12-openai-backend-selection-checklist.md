# OpenAI Backend + Backend Selection Checklist

## Phase 1 — Schema and repository
- [x] Add `llm_backend` column to `users`
- [x] Add `openai_api_key` column to `users`
- [x] Add `openai_model` column to `users`
- [x] Set safe defaults for existing users (`llm_backend='gemini'`)
- [x] Add `set_user_llm_backend()` / `get_user_llm_backend()`
- [x] Add `set_user_openai_api_key()` / `get_user_openai_api_key()`
- [x] Add `set_user_openai_model()` / `get_user_openai_model()`
- [x] Export new repo methods via `database/db_manager.py`
- [x] Add migration/repository tests

## Phase 2 — Backend metadata and routing facade
- [x] Create `services/llm_backends.py`
- [x] Define backend ids and display names
- [x] Create `services/llm_service.py`
- [x] Route provider-agnostic calls through facade
- [x] Keep handlers unaware of provider-specific modules

## Phase 3 — OpenAI backend implementation
- [x] Create `services/openai_client.py`
- [x] Add shared session + retries + `OpenAIAPIError`
- [x] Create `services/openai_request_builder.py`
- [x] Map text/image prompts into OpenAI payloads
- [x] Create `services/openai_response_parser.py`
- [x] Normalize text/sources/usage output
- [x] Create `services/openai_service.py`
- [x] Implement `generate_response`
- [x] Implement `generate_content_simple`
- [x] Implement `validate_api_key`
- [x] Implement `get_available_models`
- [x] Add OpenAI unit tests

## Phase 4 — Settings and backend selection UI
- [x] Add backend constants to `config/settings.py`
- [x] Add backend callback ids
- [x] Add backend texts to localization
- [x] Add backend selection keyboard in markup helpers
- [x] Refactor `settings_service` to be backend-aware
- [x] Add backend selection callbacks
- [x] Make `/set_api_key` work for current backend
- [x] Make model menu depend on current backend
- [x] Add settings/backend tests

## Phase 5 — Message routing and behavior
- [x] Replace direct `gemini_service` calls in handlers with `llm_service`
- [x] Route normal chat through active backend
- [x] Route translation through active backend or document exception
- [x] Decide and implement OpenAI voice behavior
- [x] Clear history cache on backend switch
- [x] Add routing/integration tests

## Phase 6 — Cleanup and validation
- [x] Remove remaining Gemini-specific assumptions from generic flows used by handlers/settings
- [ ] Update personal account / status views if needed
- [x] Run full test suite
- [ ] Manual Telegram smoke-test for Gemini user
- [ ] Manual Telegram smoke-test for OpenAI user
- [x] Update docs
