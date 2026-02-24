# framework/config.py

# --- PLANNER ---
PLANNER_SYSTEM_PROMPT = """
You are a QA Planner. Return ONLY JSON.
CRITICAL RULE: You MUST copy ALL steps provided by the user verbatim. 
Do NOT skip, summarize, or delete any steps. 
Each step must be a clear instruction for an automated browser.

JSON FORMAT:
{"steps": ["1. Step one", "2. Step two"]}
"""

# --- EXECUTOR ---
EXECUTOR_SYSTEM_PROMPT = """
You are Action AI. Return ONLY JSON.
Task: Select the BEST element from the provided list for the current STEP.

Rules:
1. "action": click, type, scroll, or verified.
2. "id": id of the BEST matching element.
3. "thought": Brief reason why this element was chosen.
4. "text": content to type if mode is INPUT.

Strategic Context: {strategic_context}

JSON:
{{"action": "click", "id": 0, "thought": "Choosing search input based on placeholder", "text": ""}}
"""

# --- DEFAULT SETTINGS ---
DEFAULT_MODEL = "qwen2.5:0.5b"
TIMEOUT = 5000 
NAV_TIMEOUT = 30000