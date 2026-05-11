from __future__ import annotations

import json
import re


def extract_json_object_best_effort(llm_output: str) -> dict | None:
    """
    The model is instructed to return JSON only.
    Still, defensively peel common wrappers (` ```json ... ``` `) if present.
    """
    text = llm_output.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            text = fenced.group(1)

    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        end = None
        for idx in range(brace_start, len(text)):
            ch = text[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        if end is not None:
            try:
                return json.loads(text[brace_start:end])
            except json.JSONDecodeError:
                pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
