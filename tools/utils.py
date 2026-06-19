import json
import re


def parse_json(text: str):
    """Parse JSON from Claude response, handling markdown code blocks."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def strip_dashes(value):
    """Recursively remove em dashes and standalone hyphens from strings in dicts/lists."""
    if isinstance(value, str):
        value = value.replace("—", ",")        # em dash → comma
        value = re.sub(r" - ", ", ", value)    # spaced hyphen → comma
        return value
    if isinstance(value, dict):
        return {k: strip_dashes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_dashes(item) for item in value]
    return value
