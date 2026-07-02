# Loops & Page Objects

> ManulEngine (Python) shares the same loop constructs and page-name registry as
> [ManulEngine (Go)](https://github.com/alexbeatnik/ManulEngineGo) — one grammar, two runtimes.

## Loops

### `REPEAT N TIMES:`

Execute a block of commands a fixed number of times.

```hunt
REPEAT 3 TIMES:
    CLICK the 'Next' button
    VERIFY that 'Step {i}' is present
```

The loop counter is automatically available as `{i}` (0-based).

### `FOR EACH {var} IN {collection}:`

Iterate over a comma-separated list stored in a variable.

```hunt
@var: {products} = Laptop, Headphones, Mouse

FOR EACH {product} IN {products}:
    FILL 'Search' field with '{product}'
    CLICK the 'Add to Cart' button NEAR '{product}'
```

### `WHILE condition:`

Repeat while a condition is true (max 100 iterations for safety).

```hunt
WHILE button 'Load More' exists:
    CLICK the 'Load More' button
    WAIT 1
```

### Nested loops

Loops can be nested inside each other and inside `IF` blocks:

```hunt
REPEAT 2 TIMES:
    FOR EACH {item} IN {items}:
        IF {item} != 'Skip':
            CLICK '{item}' button
```

---

## Page Objects (pages/ directory)

ManulEngine uses a `pages/` directory next to your hunt files to map URLs to human-readable page names (used in reports and `@custom_control` scoping).

### Fragment format

Each site gets its own JSON file: `pages/<safe-netloc>.json`

**Lean form** (recommended):
```json
{
    "site": "https://example.com/",
    "Domain": "Example",
    "https://example.com/login": "Login Page",
    "https://example.com/dashboard": "Dashboard"
}
```

**Wrapped form** (backward-compatible):
```json
{
    "https://example.com/": {
        "Domain": "Example",
        "/login": "Login Page"
    }
}
```

A legacy single `pages.json` can be split into per-site fragments with `manul pages migrate`
(the original is renamed to `pages.json.bak`); `manul pages list` prints every mapping.

### Matching logic

1. **Longest-prefix site match** — `https://app.example.com/` shadows `https://example.com/`
2. **Exact URL match**
3. **Regex pattern** match
4. **Substring fallback**
5. **`"Domain"` key** as final fallback

### Auto-populate

Unknown URLs are automatically added as `Auto: domain/path` placeholders:

```json
{
    "site": "https://new-site.io/",
    "Domain": "Auto: new-site.io",
    "https://new-site.io/profile": "Auto: new-site.io/profile"
}
```

This happens transparently on the first `NAVIGATE` to an unmapped URL. Lookups are
mtime-cached, so live edits to the registry are picked up within a running mission.

### Using page names in custom controls

Custom controls can target specific pages:

```python
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(ctx):
    ...
```

The page label is resolved via `document.title` first, then the `pages/` registry, then a URL-derived fallback.

### Comparison with ManulEngine (Go)

| Feature | Python | Go |
|---------|--------|----|
| Loop types | REPEAT, FOR EACH, WHILE | REPEAT, FOR EACH, WHILE |
| Max WHILE iterations | `MAX_LOOP_ITERATIONS = 100` | hard limit = 100 |
| Loop variable | `{i}` auto-set for REPEAT | `{i}` auto-set for REPEAT |
| Page registry | `pages/<site>.json` | `pages/<site>.json` |
| Auto-populate | `_auto_populate_registry()` | `Registry.autoPopulate()` |
| Lean/wrapped forms | both supported | both supported |
| Custom controls | `@custom_control(page, target)` decorator | `runtime.RegisterCustomControl(page, target, fn)` |
