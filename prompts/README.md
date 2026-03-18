# Hunt Prompts

Ready-to-use LLM prompts for generating modern ManulEngine `.hunt` files in the canonical STEP-grouped DSL.

## Files

| File | When to use |
|------|-------------|
| [html_to_hunt.md](html_to_hunt.md) | Paste HTML source of a page → get hunt steps |
| [description_to_hunt.md](description_to_hunt.md) | Describe a page or flow in plain text → get hunt steps |

---

## How to use with different LLMs

### GitHub Copilot Chat (VS Code) — recommended

**Option A — attach the prompt file directly:**
1. Open Copilot Chat (`Ctrl+Alt+I`).
2. Click the paperclip icon (Attach context) → select the prompt file (e.g. `prompts/html_to_hunt.md`).
3. In the chat input type your HTML or description and press Enter.
4. Copilot will return the `.hunt` content; click **Insert into new file** or copy it manually.

**Option B — use `#file` reference:**
```
Write a hunt test using the rules in #file:prompts/html_to_hunt.md for this page:
<paste HTML here>
```

**Option C — inline edit (`Ctrl+I`) on an open `.hunt` file:**
1. Create an empty `tests/mytest.hunt` file and open it.
2. Press `Ctrl+I`, type:
   ```
   Generate hunt steps using @prompts/html_to_hunt.md for: <description or paste HTML>
   ```
3. Accept the suggestion.

---

### ChatGPT / Claude (web)

1. Open the prompt file you need.
2. Select all (`Ctrl+A`), copy.
3. Paste into the chat.
4. Replace `<!-- PASTE HTML HERE -->` (or `<!-- PASTE DESCRIPTION HERE -->`) with your actual content **before sending**.
5. Send. Copy the response into a `.hunt` file in `tests/`.

---

### Claude API / OpenAI API (programmatic)

Use the prompt file content as the **system message** and your HTML/description as the **user message**:

```python
import anthropic, pathlib

system = pathlib.Path("prompts/html_to_hunt.md").read_text()
html   = pathlib.Path("mypage.html").read_text()

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=2048,
    system=system,
    messages=[{"role": "user", "content": html}],
)
print(msg.content[0].text)
```

```python
from openai import OpenAI
import pathlib

system = pathlib.Path("prompts/description_to_hunt.md").read_text()
desc   = "Login page at https://app.example.com with Email and Password fields and a Submit button."

client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system},
        {"role": "user",   "content": desc},
    ],
)
print(resp.choices[0].message.content)
```

---

### Ollama (local, no cloud)

```bash
# put the prompt + your HTML into one file and pipe it to ollama
cat prompts/html_to_hunt.md mypage.html | ollama run qwen2.5:7b
```

Or with the API:
```bash
jq -Rs '{model: "qwen2.5:7b", prompt: ., stream: false}' prompts/html_to_hunt.md \
  | curl http://localhost:11434/api/generate \
      -H 'Content-Type: application/json' \
      --data-binary @- \
  | jq -r .response
```

---

## After you get the output

1. Save the result as `tests/<name>.hunt`.
2. Run it:
   ```bash
   manul tests/<name>.hunt
   ```
3. If a step fails, fix the quoted label to match the exact visible text on the page.
4. If the model produced numbered steps, rewrite them into STEP-grouped unnumbered syntax before keeping the file.

## Hunt file quick-reference

```
@context: Short description of what this test covers
@title: tag_name
@var: {email} = test@example.com
@var: {password} = Password123

STEP 1: Open the page
    NAVIGATE to https://example.com
    Wait for 'Username' to be visible

STEP 2: Login
    Fill 'Username' field with '{email}'
    Fill 'Password' field with '{password}'
    Click the 'Login' button
    VERIFY that 'Welcome' is present

DONE.
```

### Canonical formatting rules

- Use `STEP N: Description` headers.
- Put all action lines under a STEP with 4 spaces of indentation.
- Do not use legacy numbered action lines like `1.` / `2.`.
- Keep `DONE.` flush-left.
- Prefer `@var:` for static test data instead of hardcoding values inside `Fill` steps.

### Keywords
- `NAVIGATE to <url>`
- `WAIT <seconds>`
- `Wait for "Text" to be visible`
- `Wait for 'Spinner' to disappear`
- `Wait for "Element" to be hidden`
- `PRESS ENTER`
- `PRESS [Key]` (e.g. `PRESS Escape`, `PRESS Control+A`)
- `PRESS [Key] on [Element]` (e.g. `PRESS ArrowDown on 'Search Input'`)
- `RIGHT CLICK [Element]`
- `UPLOAD 'File' to 'Element'`
- `SCROLL DOWN`
- `EXTRACT the '<target>' into {var}`
- `SET {var} = value`
- `CALL PYTHON module.function into {var}`
- `VERIFY that '<target>' is present / is NOT present / is DISABLED / is checked`
- `VERIFY SOFTLY that '<target>' is present`
- `DONE.`

`disappear` maps to Playwright's `hidden` state. Use these explicit waits instead of recommending hardcoded sleep steps for async rendering.

### Interaction verbs
`Fill … with` · `Click` · `DOUBLE CLICK` · `RIGHT CLICK` · `Select … from` · `Check/Uncheck the checkbox for` · `Click the radio button for` · `HOVER over` · `Drag … and drop it into` · `UPLOAD … to`

Element type goes **outside** quotes, label goes **inside** quotes:
```
Click the 'Submit' button      ✓
Click 'Submit button'          ✗
```

### Generation rules for LLM output

- Prefer deterministic DSL steps over vague natural language.
- Add explicit waits when the page description suggests async loading, spinners, deferred content, or client-side rendering.
- Use `@var:` for login credentials, emails, names, IDs, and other static inputs.
- Use `CALL PYTHON ... into {var}` when the flow clearly needs OTPs, tokens, magic links, or backend-generated values.
- Add `VERIFY` after major state changes.
- Do not generate fake DSL steps for screenshots, retries, or reports.
