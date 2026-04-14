# ManulEngine Documentation

> **Version: 0.0.9.29** · Alpha · [GitHub](https://github.com/alexbeatnik/ManulEngine) · [PyPI](https://pypi.org/project/manul-engine/)

ManulEngine is a deterministic, DSL-first Web & Desktop Automation Runtime backed by Playwright. It interprets `.hunt` files — plain-English automation scripts — through heuristic DOM scoring without selectors, cloud APIs, or AI dependency.

## Table of Contents

| Document | Description |
|----------|-------------|
| [Overview](overview.md) | Architecture, philosophy, and the four automation pillars |
| [Installation](installation.md) | Requirements, install commands, and environment setup |
| [Getting Started](getting-started.md) | First `.hunt` file, running tests, viewing reports |
| [DSL Syntax Reference](dsl-syntax.md) | Full command reference, variables, conditionals, custom controls, page objects |
| [Reports & Explainability](reports.md) | HTML reports, explain mode, scoring breakdowns |
| [Integration](integration.md) | Python API, CI/CD, Docker, ManulBot & MCP Server |

## Additional Resources

- [Architecture Decision Records](adr/) — ADR-001 through ADR-004
- [Contracts](../contracts/) — Machine-readable API, CLI, DSL, and scoring contracts
- [Demo & Benchmarks](../demo/) — Integration hunts and adversarial DOM fixtures

---

**Status: Alpha.** Solo-developed, actively battle-tested. Bugs are expected, APIs may evolve.
