---
name: add-config-key
description: Add a new configuration setting to ManulEngine end-to-end — EngineConfig field, MANUL_* env var, JSON config key, prompts.py global, and the MANUL_CONFIG_CONTRACT.md entry — honoring the precedence layering. Invoke when the user says "add a config option", "new setting", "new MANUL_ env var", "make X configurable", "додай налаштування", "новий конфіг". A new public ctor kwarg is "Ask first" per CLAUDE.md.
---

# add-config-key

ManulEngine resolves each setting through a fixed precedence chain (highest → lowest), and a new key has to slot into **every** layer or it will behave inconsistently depending on how the user sets it:

1. Explicit kwarg to `ManulEngine(...)` / `ManulSession(...)`
2. `EngineConfig` instance passed via `config=`
3. Module globals in `prompts.py` (read at construction time, **not** runtime)
4. Environment variable `MANUL_*`
5. `manul_engine_configuration.json`

## When to invoke

- User wants to expose a new tunable: a timeout, a directory, a feature flag, a threshold, etc.
- **Stop and ask first** if the setting needs to be a *new public constructor kwarg* on `ManulEngine`/`ManulSession` — CLAUDE.md lists new public ctor kwargs under "Ask first". Most settings need only the config/env path, not a ctor kwarg.

## Execution order

1. **EngineConfig field.** Add the field with a typed default to the dataclass in `manul_engine/config.py` (the `timeout: int = 5000`, `semantic_cache_enabled: bool = True`, … block). Keep the type and default identical to what the contract will state.
2. **Construction in `from_file`.** Wire it in the `cls(...)` call in `config.py:from_file`, using the right helper:
   - string → `_optional_str("key", "MANUL_KEY")` (or `_str(...)` with a default)
   - int → `_optional_int(...)` / `_int(...)`
   - bool → `_bool("key", "MANUL_KEY")`
   - list → follow the `browser_args` / `custom_controls_dirs` special-casing (env is comma/space-split; JSON is a native array).
   Env var **always wins** over the JSON value — preserve that ordering inside the helper usage.
3. **prompts.py global + `_KEY_MAP`.** Add a module global read from env (mirror `TIMEOUT = int(os.getenv("MANUL_TIMEOUT", "5000"))`) for the legacy `prompts.*` path, and add `"key": "MANUL_KEY"` to `_KEY_MAP` so the JSON-config → env overlay loop picks it up. Booleans are lowercased into the env by that loop, so parse with `env_bool`.
4. **Consume it at `__init__`, never at runtime.** In `core.py.__init__` (or wherever it is used), read the value **once** — prefer `EngineConfig` when present, fall back to the `prompts.*` global — and store it on `self`. Do not read `prompts.X` or `os.getenv` at action time. (The one sanctioned exception is `prompts.lookup_page_name()`'s mtime cache — don't add new ones.)
5. **Contract.** Add the key to `contracts/MANUL_CONFIG_CONTRACT.md`:
   - a config-file/EngineConfig setting → an entry in the `keys` array (with `key`, `envVar`, `type`, `default`, `description`, and `cliFlag` if any).
   - an env-only knob with no JSON/EngineConfig home (like `MANUL_LOG_LEVEL` or `MANUL_PAGES_DIR`) → an entry in `environmentVariables.runtimeOnly` instead.
6. **README.** Add a row to the "Configuration reference" table in `README.md` (and `README_DEV.md` if it has implementation notes).
7. **CLI flag (only if asked).** If it should be settable from the CLI, add the flag in `manul_engine/cli.py` and document it in `contracts/MANUL_CLI_CONTRACT.md` with `cliFlag` on the config entry.
8. **Test.** Add coverage to the config test (precedence: env beats JSON, JSON beats default; invalid value falls back to default). `test_*config*` / the `EngineConfig.from_file` tests are the template.
9. **Bump version.** Contract changed → bump via the `bump-version` skill in the same change.

## Common pitfalls

- Adding the `EngineConfig` field but forgetting `_KEY_MAP` — the JSON key then silently never reaches the env overlay, so file config is ignored while env still works.
- Reading the value at runtime (`prompts.X` / `os.getenv`) instead of snapshotting at `__init__` — violates the layering rule and makes behavior non-deterministic across a run.
- Letting the JSON value win over the env var — env is layer 4 but **always overrides** the JSON file (layer 5); the `_optional_*` helpers already enforce this, so use them rather than reading `raw[...]` directly.
- Forgetting the contract entry — `MANUL_CONFIG_CONTRACT.md` is the source of truth consumed by the VS Code config panel and downstream tooling; a key absent there is invisible to them.
- Putting an env-only knob into the `keys` array (implying a JSON/EngineConfig field that doesn't exist) — use `environmentVariables.runtimeOnly` for those.
- Booleans: the JSON→env overlay stores them as lowercase strings; parse with `env_bool`, not `bool(os.getenv(...))` (which is truthy for the string `"false"`).

## Reference

- Dataclass + loader: `manul_engine/config.py` (`EngineConfig`, `from_file`, `_optional_str/_optional_int/_bool/_int`)
- Legacy globals + overlay: `manul_engine/prompts.py` (`_KEY_MAP`, module globals, JSON-config loop)
- Boolean parsing: `manul_engine/helpers.py:env_bool`
- Contract: `contracts/MANUL_CONFIG_CONTRACT.md` (`keys` vs `environmentVariables.runtimeOnly`)
- CLI flags: `manul_engine/cli.py` + `contracts/MANUL_CLI_CONTRACT.md`
