"""Map SHL catalog 'keys' (categories) to compact test type codes matching SHL UX."""

KEY_TO_CODE: dict[str, str] = {
    "Knowledge & Skills": "K",
    "Ability & Aptitude": "A",
    "Personality & Behavior": "P",
    "Biodata & Situational Judgment": "B",
    "Simulations": "S",
    "Competencies": "C",
    "Assessment Exercises": "E",
    "Development & 360": "D",
}


def keys_to_test_type(keys: list[str]) -> str:
    codes: list[str] = []
    for k in keys or []:
        code = KEY_TO_CODE.get(str(k).strip())
        if code and code not in codes:
            codes.append(code)
    return ",".join(codes)
