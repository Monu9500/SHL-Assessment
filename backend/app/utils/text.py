from __future__ import annotations


def compact_history_for_retrieval(messages: list[tuple[str, str]], max_turns: int = 10) -> str:
    tail = messages[-max_turns:]
    parts: list[str] = []
    for role, content in tail:
        c = content.strip()
        if not c:
            continue
        prefix = "User" if role == "user" else "Assistant"
        parts.append(f"{prefix}: {c}")
    return "\n".join(parts)


def build_latest_user_retrieval_query(last_user_message: str | None) -> str:
    if not last_user_message:
        return ""
    return "Latest user request:\n" + last_user_message.strip()
