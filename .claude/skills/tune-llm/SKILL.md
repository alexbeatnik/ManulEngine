---
name: tune-llm
description: Edit ManulEngine's optional local-LLM layer — the Ollama transport in llm.py and the model-size-aware prompts/thresholds in prompts.py — without breaking determinism or the contracts. Invoke when the user says "tune the LLM", "change the prompt", "edit the executor/planner prompt", "the model picks the wrong element", "make the AI fallback better", "налаштуй LLM", "зміни промпт", or asks to add an Ollama sampling option.
---

# tune-llm

The LLM is a **last-resort fallback**, not the primary resolver. The heuristic `DOMScorer` decides almost everything; the model is only consulted for genuinely ambiguous targets (or always, when `ai_always=True`). Every change here must preserve the engine's core promise: **same page + same step ⇒ same result**.

## Where the LLM lives

| Concern | File / symbol |
| --- | --- |
| Transport (Ollama call, JSON parse, retry, sanitize) | `manul_engine/llm.py` — `OllamaProvider`, `NullProvider`, `create_provider`, `_parse_llm_json`, `sanitize_for_llm`, `truncate_for_llm` |
| Sampling config (read once at construction) | `llm.py` module globals `LLM_TEMPERATURE` / `LLM_NUM_CTX` / `LLM_MAX_RETRIES` / `LLM_KEEP_ALIVE` (env `MANUL_LLM_*`) |
| Element-picker + planner prompts | `manul_engine/prompts.py` — `PLANNER_SYSTEM_PROMPT`, `_RULES_CORE`, `EXECUTOR_PROMPT_TINY/SMALL/LARGE`, `get_executor_prompt()` |
| Model-size → threshold | `prompts.py` — `_threshold_for_model()`, `get_threshold()` |
| Call sites | `core.py` — `_llm_json`, `_llm_plan`, `_llm_select_element` |
| What-If (debug) prompt | `manul_engine/explain_next.py` — `WHAT_IF_SYSTEM_PROMPT` |

## When to invoke

- User wants to change how the model is prompted, retried, or sampled, or to add an Ollama option.
- "The AI picks the wrong element" / "the planner drops steps" — usually a prompt-rules fix in `_RULES_CORE` or `PLANNER_SYSTEM_PROMPT`.

## Invariants — do not break these

1. **Determinism.** Ollama calls go through `OllamaProvider._chat`, which sends `options` built by `_build_options()` with `temperature=0` by default. Keep greedy decoding the default; never hard-code a non-zero temperature.
2. **Read config once.** Sampling settings are snapshotted into `self._options` / `self._max_retries` in `OllamaProvider.__init__`. Never read the `LLM_*` globals (or env) at call time — same rule as `prompts.*` (see CLAUDE.md "Configuration layering").
3. **Fail closed, never raise.** `call_json` must return `dict | None`. `_parse_llm_json` returns `None` (never raises) on junk. A dead server is reported once via `_is_connection_error` and **not** retried; only empty/malformed replies are retried (`LLM_MAX_RETRIES`).
4. **JSON-only outputs.** Every prompt instructs "Return ONLY valid JSON". The element picker expects `{"id": <int|null>, "thought": "..."}`; the planner expects `{"steps": [...]}`. If you change a response shape, update the consumer in `core.py` **and** the contract.
5. **Sanitize page text before prompting.** Page prose handed to a model goes through `sanitize_for_llm` (strip base64/`data-*`/SVG noise) and is bounded with `truncate_for_llm`. Re-use these — don't hand-roll trimming.

## Prompt editing notes

- `_RULES_CORE` is shared by all three executor sizes; edit it once and all sizes inherit. Size-specific extras (examples, verbosity) live in the `TINY/SMALL/LARGE` wrappers. `get_executor_prompt()` picks by parameter count parsed from the model name (`<n>b`).
- The picker is fed a **compact candidate payload** (`_llm_select_element` in `core.py`) — id, score, name, tag, attrs. If you add a field the model should weigh, add it to that payload **and** describe it in `_RULES_CORE`'s field list, or the model can't see it.
- `score` is given to the model as a **prior, not a shackle** (rule 3 in `_RULES_CORE`). Preserve that framing — clamping the model to max-score belongs in the deterministic `MANUL_AI_POLICY=strict` guard in `_llm_select_element`, not in the prompt.

## Contracts & docs to keep in sync

- New / changed `MANUL_LLM_*` env var → `contracts/MANUL_CONFIG_CONTRACT.md` (`environmentVariables.runtimeOnly`) + the README env table.
- Changed What-If response schema or `LLMProvider` surface → `contracts/MANUL_DEBUG_CONTRACT.md` (`llmIntegration.responseSchema`).
- **Changing `_threshold_for_model` numbers or scoring weights is "Ask first"** per CLAUDE.md — it shifts test goldens (`test_34_scoring_math`, `test_28_heuristic_weights`) and `contracts/MANUL_SCORING_CONTRACT.md`. Confirm with the user before touching thresholds.
- Any contract-affecting change → bump the version (`bump-version` skill) in the same change.

## Testing

- Transport logic is testable **without Playwright or a real server** by stubbing the `ollama` module — see how `test_49_explain_next.py` injects a `MockLLM` with `call_json`. Cover: retry-recovers-malformed, connection-error-fails-fast (one attempt), `temperature==0` passed, non-dict reply → `None`.
- `test_49_explain_next.py` (112 assertions) exercises the What-If path end-to-end with `NullProvider` (heuristics-only) and a mock LLM. Run it after any change here:
  `.venv/bin/python manul_engine/test/test_49_explain_next.py`.

## Common pitfalls

- Hard-coding sampling values in `_chat` instead of `_build_options()` / the `LLM_*` globals — breaks the config-layering rule and determinism.
- Making `call_json` raise — callers in `core.py` treat exceptions as hard failures; the provider must absorb them and return `None`.
- Editing a prompt's JSON shape but not the parser in `core.py` — symptom: every pick becomes a rejection (`id=null`).
- Retrying connection errors — a down `ollama serve` won't recover on retry; only empty/unparseable replies are worth a second attempt.

## Reference

- Provider + helpers: `manul_engine/llm.py`
- Prompts + thresholds: `manul_engine/prompts.py`
- Call sites: `manul_engine/core.py` (`_llm_json`, `_llm_plan`, `_llm_select_element`)
- Config contract: `contracts/MANUL_CONFIG_CONTRACT.md` · Debug contract: `contracts/MANUL_DEBUG_CONTRACT.md`
