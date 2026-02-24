# framework/config.py

# --- PLANNER ---
PLANNER_SYSTEM_PROMPT = """
You are a QA Planner. Return ONLY JSON.
CRITICAL RULE: You MUST copy ALL steps provided by the user. Do NOT skip, summarize, or delete any steps.

JSON FORMAT:
{"steps": ["1. First user step", "2. Second user step", "3. Third user step", "4. ... and so on for ALL steps"]}
"""

# --- EXECUTOR ---
EXECUTOR_SYSTEM_PROMPT = """
You are Action AI. Return ONLY JSON.
Rules:
1. "action": click, type, scroll, or verified.
2. "id": data-manul-id of the BEST matching element.
3. "text": content to type or verify.

JSON:
{{"action": "click", "id": 0, "thought": "Reason", "text": ""}}
"""

# --- DEFAULT SETTINGS ---
DEFAULT_MODEL = "qwen2.5:0.5b"
TIMEOUT = 10000 
NAV_TIMEOUT = 25000