# ManulEngine Documentation

> **Version: 0.1.0** · Alpha · [GitHub](https://github.com/alexbeatnik/ManulEngine) · [PyPI](https://pypi.org/project/manul-engine/)

ManulEngine is a deterministic, DSL-first Web & Desktop Automation Runtime driving system Chrome over the Chrome DevTools Protocol (CDP). It interprets `.hunt` files — plain-English automation scripts — through heuristic DOM scoring without selectors, cloud APIs, or AI dependency.

## Table of Contents

| Document | Description |
|----------|-------------|
| [Overview](overview.md) | Architecture, philosophy, and the four automation pillars |
| [Installation](installation.md) | Requirements, install commands, and environment setup |
| [Getting Started](getting-started.md) | First `.hunt` file, running tests, viewing reports |
| [DSL Syntax Reference](dsl-syntax.md) | Full command reference, variables, conditionals, custom controls, page objects |
| [DSL for LLMs](dsl-for-llms.md) | Compact cheat-sheet + agent JSON shapes (`manul schema` is the machine mirror) |
| [Reports & Explainability](reports.md) | HTML reports, explain mode, scoring breakdowns |
| [Integration](integration.md) | Python API, CI/CD, Docker, ManulBot & MCP Server |
| [Extensions](extensions.md) | `CALL PYTHON`, `@custom_control`, lifecycle hooks |
| [Loops & Page Objects](loops-and-pages.md) | `REPEAT` / `FOR EACH` / `WHILE` and the `pages/` registry |

The Go engine ([ManulEngineGo](https://github.com/alexbeatnik/ManulEngineGo)) keeps the same documentation set — one DSL, two runtimes.

## Additional Resources

- [Contracts](../contracts/) — Machine-readable API, CLI, DSL, and scoring contracts
- [Demo & Benchmarks](../demo/) — Integration hunts and adversarial DOM fixtures

---

**Status: Alpha.** Solo-developed, actively battle-tested. Bugs are expected, APIs may evolve.
