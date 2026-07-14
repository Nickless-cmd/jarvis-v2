"""Fase 6 (acceptance harness) — server-side fault-injection package.

Verifies the /v1/agent/step O1 envelope, A6 finish_reason plumbing, and A8
typed-forwarded-error contract by monkeypatching the openai-compat provider
seam (`core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat`
and `core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events`)
— never a real network call, never a real provider."""
