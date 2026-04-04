# ManulEngine — Hooks & Lifecycle Contract

> **Machine-readable contract for the hook system, lifecycle decorators, variable scoping, and module resolution.**
> Consumed by test framework integrations, CI/CD runners, and downstream tooling that extends ManulEngine's execution lifecycle.

```json
{
  "version": "0.0.9.22",
  "generatedFrom": "manul_engine/hooks.py :: HookResult, extract_hook_blocks(), execute_hook_line(), run_hooks(); manul_engine/lifecycle.py :: GlobalContext, @before_all, @after_all, @before_group, @after_group, _HookRegistry, load_hooks_file(); manul_engine/variables.py :: ScopedVariables",

  "fileHooks": {
    "description": "Per-hunt-file [SETUP] and [TEARDOWN] blocks. Run synchronous Python functions outside the browser for data injection and cleanup.",

    "blocks": {
      "SETUP": {
        "markers": ["[SETUP]", "[END SETUP]"],
        "timing": "Runs BEFORE browser launches.",
        "failureBehavior": "Mission status set to 'broken'; browser steps are skipped entirely.",
        "allowedInstructions": ["CALL PYTHON", "PRINT"]
      },
      "TEARDOWN": {
        "markers": ["[TEARDOWN]", "[END TEARDOWN]"],
        "timing": "Runs in a finally block AFTER the mission (pass or fail). Only executes if [SETUP] succeeded.",
        "failureBehavior": "Logged but does not override the mission result.",
        "allowedInstructions": ["CALL PYTHON", "PRINT"]
      }
    },

    "hookResult": {
      "class": "HookResult",
      "frozen": true,
      "fields": [
        { "name": "success",        "type": "bool",              "description": "True if the line executed without error." },
        { "name": "message",        "type": "str",               "default": "",   "description": "Human-readable status message." },
        { "name": "return_value",   "type": "str | None",        "default": null, "description": "Stringified function return value when 'into {var}' was requested." },
        { "name": "var_name",       "type": "str | None",        "default": null, "description": "Variable name from 'into {var}' clause." },
        { "name": "return_mapping", "type": "dict[str, str]",    "default": {},   "description": "Key-value pairs when function returns a dict." }
      ]
    },

    "callPythonSyntax": {
      "variants": [
        "CALL PYTHON <module>.<function>",
        "CALL PYTHON {alias}.<function>",
        "CALL PYTHON {callable_alias}",
        "CALL PYTHON <module>.<function> \"arg1\" 'arg2' {var}",
        "CALL PYTHON <module>.<function> into {result}",
        "CALL PYTHON <module>.<function> \"arg1\" {var} into {result}"
      ],
      "argumentParsing": "shlex.split() — single-quoted, double-quoted, and unquoted tokens accepted. {var} placeholders resolved from runtime memory.",
      "captureKeyword": "'into' (primary) or 'to' (alias) followed by {variable_name}",
      "scriptAlias": "@script: {alias} = package.module declares file-local alias. Parser rewrites to real dotted paths.",
      "restrictions": [
        "Target functions MUST be synchronous. Async callables are rejected with a descriptive error.",
        "Only valid as hook instructions or inline mission steps."
      ]
    },

    "printSyntax": {
      "format": "PRINT \"message with {vars}\"",
      "description": "Variable-interpolated console output. Valid only inside [SETUP]/[TEARDOWN] blocks."
    },

    "functions": {
      "extract_hook_blocks": {
        "signature": "(raw_text: str) -> tuple[list[str], list[str], str]",
        "returns": "(setup_lines, teardown_lines, mission_body)",
        "description": "Strips [SETUP]/[TEARDOWN] blocks from raw mission text."
      },
      "execute_hook_line": {
        "signature": "(line: str, hunt_dir: str | None = None, variables: dict[str, str] | None = None) -> HookResult",
        "description": "Execute one CALL PYTHON or PRINT instruction. Returns HookResult."
      },
      "run_hooks": {
        "signature": "(lines: list[str], label: str = 'HOOK', hunt_dir: str | None = None, variables: dict[str, str] | None = None) -> bool",
        "returns": "True if all succeeded; False on first failure.",
        "description": "Run hook block sequentially. Stops on first failure."
      },
      "clear_module_cache": {
        "signature": "() -> None",
        "description": "Reset the JIT module cache. Used between test runs for isolation."
      }
    },

    "moduleResolution": {
      "order": [
        "1. Hunt file's directory (hunt_dir parameter)",
        "2. Current working directory (Path.cwd())",
        "3. Standard sys.path / importlib (installed packages, PYTHONPATH)"
      ],
      "caching": "_module_cache: dict[str, ModuleType] keyed by absolute file path. JIT loaded.",
      "isolation": "File-based modules executed in isolated ModuleType sandbox — NEVER inserted into sys.modules. Prevents cross-test contamination.",
      "perFileIdempotency": "_LOADED_FILES set prevents duplicate module imports across sequential runs."
    }
  },

  "globalLifecycleHooks": {
    "description": "Suite-level hooks registered via decorators in manul_hooks.py. Run before/after the entire suite or per tag group.",

    "globalContext": {
      "class": "GlobalContext",
      "fields": [
        { "name": "variables", "type": "dict[str, str]", "default": {}, "description": "Key-value store passed to hunt files as {placeholder} variables. Serialised to MANUL_GLOBAL_VARS for parallel workers." },
        { "name": "metadata",  "type": "dict[str, object]", "default": {}, "description": "Hook-to-hook scratch space. Not serialised or passed to hunt files." }
      ]
    },

    "decorators": [
      {
        "name": "@before_all",
        "signature": "@before_all def fn(ctx: GlobalContext) -> None",
        "timing": "Once before entire suite (before any hunt file runs).",
        "failureBehavior": "Abort — no hunt files are executed."
      },
      {
        "name": "@after_all",
        "signature": "@after_all def fn(ctx: GlobalContext) -> None",
        "timing": "Once after all missions complete (always, even on failure).",
        "failureBehavior": "Logged but does not affect results."
      },
      {
        "name": "@before_group",
        "signature": "@before_group(tag='smoke') def fn(ctx: GlobalContext) -> None",
        "timing": "Before each mission whose @tags: includes the specified tag.",
        "failureBehavior": "Abort — the tagged mission is skipped."
      },
      {
        "name": "@after_group",
        "signature": "@after_group(tag='smoke') def fn(ctx: GlobalContext) -> None",
        "timing": "After each mission whose @tags: includes the specified tag.",
        "failureBehavior": "Logged but does not affect results."
      }
    ],

    "registry": {
      "class": "_HookRegistry",
      "singleton": "manul_engine.lifecycle.registry",
      "methods": [
        { "name": "register_before_all",  "signature": "(fn: Callable) -> Callable" },
        { "name": "register_after_all",   "signature": "(fn: Callable) -> Callable" },
        { "name": "register_before_group","signature": "(tag: str) -> Callable[[Callable], Callable]" },
        { "name": "register_after_group", "signature": "(tag: str) -> Callable[[Callable], Callable]" },
        { "name": "run_before_all",       "signature": "(ctx: GlobalContext) -> bool", "description": "Execute all @before_all. Abort on first failure." },
        { "name": "run_after_all",        "signature": "(ctx: GlobalContext) -> None", "description": "Execute all @after_all regardless of errors." },
        { "name": "run_before_group",     "signature": "(tags: list[str], ctx: GlobalContext) -> bool" },
        { "name": "run_after_group",      "signature": "(tags: list[str], ctx: GlobalContext) -> None" },
        { "name": "is_empty",             "type": "property -> bool" },
        { "name": "clear",                "signature": "() -> None", "description": "Reset all registrations (test isolation)." }
      ]
    },

    "autoDiscovery": {
      "function": "load_hooks_file(directory: str) -> bool",
      "filename": "manul_hooks.py",
      "behavior": "Silently attempts import from specified directory. Decorators mutate the global registry singleton.",
      "returnsTrue": "File found and imported (may register 0 hooks).",
      "returnsFalse": "File not present (normal — no hooks configured).",
      "isolation": "Executed in isolated ModuleType sandbox (not inserted into sys.modules)."
    },

    "serialization": {
      "serialize": {
        "function": "serialize_global_vars(ctx: GlobalContext) -> str",
        "description": "Serialise ctx.variables to JSON string for MANUL_GLOBAL_VARS env var."
      },
      "deserialize": {
        "function": "deserialize_global_vars() -> dict[str, str]",
        "description": "Read MANUL_GLOBAL_VARS from environment and parse JSON. Returns empty dict when absent or malformed."
      },
      "purpose": "Parallel workers (--workers > 1) receive @before_all results via MANUL_GLOBAL_VARS env var."
    },

    "importPath": "from manul_engine import before_all, after_all, before_group, after_group, GlobalContext"
  },

  "scopedVariables": {
    "class": "ScopedVariables",
    "module": "manul_engine/variables.py",
    "description": "Five-level variable hierarchy with strict precedence resolution. Used throughout the engine for {placeholder} substitution.",

    "levels": [
      { "constant": "LEVEL_ROW",     "priority": 1, "label": "row",     "description": "Per-iteration from @data CSV/JSON rows. Cleared between iterations." },
      { "constant": "LEVEL_STEP",    "priority": 2, "label": "step",    "description": "Runtime: EXTRACT, SET, CALL PYTHON ... into. Default write target for dict[]-style access." },
      { "constant": "LEVEL_MISSION", "priority": 3, "label": "mission", "description": "File-level @var: declarations and [SETUP] hook returns." },
      { "constant": "LEVEL_GLOBAL",  "priority": 4, "label": "global",  "description": "CLI/env context and @before_all lifecycle hook variables." },
      { "constant": "LEVEL_IMPORT",  "priority": 5, "label": "import",  "description": "@var: declarations inherited from @import: source files. Lowest priority — overridden by all other levels." }
    ],
    "resolutionOrder": "Highest priority first: row → step → mission → global → import. First non-null match wins.",

    "methods": [
      { "name": "resolve",        "signature": "(name: str) -> str | None" },
      { "name": "resolve_level",  "signature": "(name: str) -> tuple[str | None, str | None]" },
      { "name": "as_flat_dict",   "signature": "() -> dict[str, str]" },
      { "name": "substitute",     "signature": "(text: str) -> str" },
      { "name": "set",            "signature": "(name: str, value: str, level: str) -> None" },
      { "name": "set_many",       "signature": "(mapping: dict[str, str], level: str) -> None" },
      { "name": "clear_level",    "signature": "(level: str) -> None" },
      { "name": "clear_runtime",  "signature": "() -> None", "description": "Clear ROW + STEP levels (between @data iterations)." },
      { "name": "clear_all",      "signature": "() -> None" },
      { "name": "dump",           "signature": "() -> str" }
    ],

    "dictCompatibility": {
      "supported": true,
      "operations": [
        "__contains__ (in operator)",
        "__getitem__ / __setitem__ (writes to LEVEL_STEP)",
        "get(name, default)",
        "items(), keys(), values() (iterate merged flat dict)",
        "update() (bulk-set at LEVEL_STEP)",
        "clear() (delegates to clear_all())",
        "__eq__ (compare with ScopedVariables or dict)",
        "__repr__"
      ]
    }
  }
}
```
