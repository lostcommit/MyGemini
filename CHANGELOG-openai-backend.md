Changelog

- added per-user LLM backend selection between Google Gemini and OpenAI
- added OpenAI API key and model persistence in the users table
- introduced shared LLM routing layer and refactored Gemini/OpenAI service architecture
- updated settings UI to support backend selection and backend-specific API key/model flows
- made chat, translate, image, account, status header, and usage flows backend-aware
- added DEFAULT_LLM_BACKEND support for new users and fallback paths
- added OPENAI_API_KEY environment fallback support
- updated README and in-app guides for OpenAI setup and backend selection
- added regression tests for backend selection, usage, personal account, runtime context, request builders, parsers, and services
- OpenAI voice messages remain explicitly unsupported with a user-friendly message
