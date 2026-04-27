# Trading Bot — Project Context for Claude

## What this is
Autonomous intraday trading bot. Paper trading only on Trading212.
Stack: Python + Google Gemini 2.0 Flash + Trading212 REST API + React dashboard.
Scheduled via GitHub Actions cron pipelines. State persisted as JSON.

## Layout
- `bot/` — Python core: Gemini integration, decision loop, Trading212 client, indicator math (RSI, MACD, Bollinger Bands), state management
- `data/` — historical price data and intermediate caches
- `design/` — design docs, architecture notes
- `state.json` — runtime state (positions, last decisions, cash)
- `.github/workflows/` — scheduled bot runs and Claude Code review

## Conventions
- Python 3.11+. Use type hints. Prefer dataclasses or TypedDict for structured payloads.
- Every Gemini call must validate the response against a JSON schema and fall back to a deterministic template on parse failure. Never trust raw LLM output for trade decisions.
- API keys (Gemini, Trading212, Anthropic) live in `.env` locally and as repository secrets in CI. Never commit them.
- Paper trading only. No real-money endpoints, ever. Treat that as a hard invariant.

## Review priorities
1. Resilience to malformed LLM output (schema validation, fallbacks)
2. Trading212 API auth, retries, and rate limit handling
3. State persistence correctness (no torn writes, atomic updates)
4. Secret handling (no leaks, no logging of keys)
5. Indicator math correctness (RSI, MACD, Bollinger)
6. Test coverage for the decision loop and edge cases
