from __future__ import annotations

import logging
from typing import Any

from app.config.settings import Settings
from app.models.schemas import ChatMessage, ChatResponse, RecommendationItem
from app.prompts.agent import SYSTEM_PROMPT
from app.rag.catalog_models import ProcessedAssessment
from app.rag.vector_store import FaissRetriever
from app.services.groq_client import GroqClient, degraded_shortlist_fallback
from app.utils.json_extract import extract_json_object_best_effort
from app.utils.text import build_latest_user_retrieval_query, compact_history_for_retrieval

log = logging.getLogger(__name__)


def _prior_assistant_count(messages: list[ChatMessage]) -> int:
    return sum(1 for m in messages if m.role == "assistant")


def _should_force_commit(settings: Settings, messages: list[ChatMessage]) -> bool:
    assistants = _prior_assistant_count(messages)
    # Guardrail: evaluator conversations are capped; bias toward committing late.
    if assistants >= settings.evaluator_max_turns - 1:
        return True
    if len(messages) >= (settings.evaluator_max_turns * 2 - 2):
        return True
    return False


def _parse_decision(llm_raw: str) -> dict[str, Any]:
    obj = extract_json_object_best_effort(llm_raw) or {}

    mode = obj.get("mode")
    reply_raw = obj.get("reply")

    reply = reply_raw.strip() if isinstance(reply_raw, str) else ""

    raw_end = obj.get("end_of_conversation")
    if isinstance(raw_end, str):
        end_of_conversation = raw_end.strip().lower() in {"true", "1", "yes"}
    elif isinstance(raw_end, bool):
        end_of_conversation = raw_end
    else:
        end_of_conversation = False

    selected_raw = obj.get("selected_indices")
    indices: list[int] = []
    if isinstance(selected_raw, list):
        for item in selected_raw:
            try:
                indices.append(int(item))
            except (TypeError, ValueError):
                continue

    if mode not in {"clarify", "recommend", "refuse", "compare"}:
        mode = "clarify"

    return {
        "mode": mode,
        "reply": reply,
        "end_of_conversation": bool(end_of_conversation),
        "selected_indices": indices,
    }


def _map_indices_to_recommendations(
    *,
    picks: list[ProcessedAssessment],
    indices_one_based: list[int],
    max_items: int,
) -> list[RecommendationItem]:
    ordered_keys: list[str] = []
    items: dict[str, RecommendationItem] = {}

    for idx in indices_one_based:
        if idx < 1 or idx > len(picks):
            continue
        p = picks[idx - 1]
        key = p.entity_id
        if key in ordered_keys:
            continue
        ordered_keys.append(key)
        items[key] = RecommendationItem(
                name=p.name,
                url=p.url,
                test_type=(p.test_type[:32] if p.test_type else ""),
            )
        if len(ordered_keys) >= max_items:
            break

    return [items[k] for k in ordered_keys]


def _fallback_recommend_top(picks: list[ProcessedAssessment], max_items: int) -> list[RecommendationItem]:
    out: list[RecommendationItem] = []
    for p in picks:
        out.append(
            RecommendationItem(
                name=p.name,
                url=p.url,
                test_type=p.test_type[:32] if p.test_type else "",
            )
        )
        if len(out) >= max_items:
            break
    return out


def _build_recommendation_response(
    reply: str,
    picks: list[ProcessedAssessment],
    max_items: int,
    end_of_conversation: bool = True,
) -> ChatResponse:
    return ChatResponse(
        reply=reply,
        recommendations=_fallback_recommend_top(picks, max_items=max_items),
        end_of_conversation=end_of_conversation,
    )


def _query_looks_like_general_informational_request(last_user_message: str | None) -> bool:
    if not last_user_message:
        return False
    text = last_user_message.lower()
    info_signals = (
        "what is",
        "who is",
        "why is",
        "why are",
        "how is",
        "how are",
        "how does",
        "how do",
        "explain",
        "define",
        "meaning of",
        "difference between",
        "compare",
        "versus",
        "vs ",
    )
    recommendation_signals = (
        "recommend",
        "suggest",
        "shortlist",
        "battery",
        "assessment",
        "test",
        "hire",
        "select",
        "which test",
        "which assessment",
        "what should i use",
        "what should we use",
        "what would you recommend",
    )
    if any(token in text for token in info_signals):
        return not any(token in text for token in recommendation_signals)
    return False


def _build_answer_only_fallback(last_user_message: str | None) -> ChatResponse:
    msg = (
        "Groq is temporarily unavailable due to API limits. "
        "Your latest request appears to be a comparison or explanation question, "
        "so I’m returning a plain answer without a recommendation shortlist. "
        "Please retry once the service is restored for grounded catalog recommendations."
    )
    if last_user_message and last_user_message.strip():
        msg = (
            "Groq is temporarily unavailable due to API limits. "
            "Your latest request appears to be a comparison or explanation question, "
            f'"{last_user_message.strip()}". '
            "I’m returning a plain answer instead of a recommendation shortlist. "
            "Please retry once the service is restored for grounded catalog recommendations."
        )
    return ChatResponse(reply=msg, recommendations=[], end_of_conversation=False)


class ChatOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        retriever: FaissRetriever,
        groq: GroqClient | None,
    ):
        self.settings = settings
        self.retriever = retriever
        self.groq = groq

    async def reply(self, messages: list[ChatMessage]) -> ChatResponse:
        if not messages or messages[-1].role != "user":
            return ChatResponse(
                reply=(
                    "Your request must include a non-empty transcript whose last "
                    'message role is \"user\". The API remains stateless; include prior turns.'
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        msgs_tuples: list[tuple[str, str]] = []
        for msg in messages:
            if msg.role in {"user", "assistant"}:
                msgs_tuples.append((msg.role, msg.content))

        retrieval_query = compact_history_for_retrieval(msgs_tuples, max_turns=14)

        top_k = max(24, min(self.settings.top_k_retrieval, 96))
        picks = self.retriever.search(query_text=retrieval_query + "\n", top_k=top_k)

        assistants_before = _prior_assistant_count(messages)
        force_commit = _should_force_commit(self.settings, messages)

        cand_lines = [item.format_for_prompt(i) for i, item in enumerate(picks, start=1)]
        candidates_text = (
            "(Candidates for THIS turn only. Selecting items not numbered below is forbidden.)\n"
            + "\n\n".join(cand_lines)
        )

        decision: dict[str, Any]
        last_user_message = messages[-1].content if messages else None
        if self.groq is None:
            if last_user_message and last_user_message.strip():
                picks = self.retriever.search(
                    query_text=build_latest_user_retrieval_query(last_user_message),
                    top_k=top_k,
                )
            if _query_looks_like_general_informational_request(last_user_message):
                return _build_answer_only_fallback(last_user_message)
            return _build_recommendation_response(
                reply=degraded_shortlist_fallback(last_user_message=last_user_message)["reply"],
                picks=picks,
                max_items=self.settings.max_recommendations,
            )
        else:
            try:
                llm_raw = self.groq.chat_completion_jsonish(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=(
                        "CONVERSATION_META_JSON="
                        '{"prior_assistant_count": '
                        f"{assistants_before}, "
                        '"force_shortlist": '
                        f'{str(force_commit).lower()}'
                        "}\n\n"
                        "CONVERSATION_TEXT:\n"
                        f"{retrieval_query}\n\n"
                        f"{candidates_text}\n"
                    ),
                )
                decision = _parse_decision(llm_raw)
            except Exception as exc:  # noqa: BLE001
                if last_user_message and last_user_message.strip():
                    picks = self.retriever.search(
                        query_text=build_latest_user_retrieval_query(last_user_message),
                        top_k=top_k,
                    )
                if _query_looks_like_general_informational_request(last_user_message):
                    log.warning(
                        "Groq unavailable; falling back to plain answer-only response for general informational query."
                    )
                    return _build_answer_only_fallback(last_user_message)
                log.warning("Groq inference failed; using retrieval-only shortlist fallback. err=%s", exc)
                return _build_recommendation_response(
                    reply=degraded_shortlist_fallback(last_user_message=last_user_message)["reply"],
                    picks=picks,
                    max_items=self.settings.max_recommendations,
                )

        mode = decision["mode"]
        reply = decision["reply"].strip()
        end_flag = decision["end_of_conversation"]
        selected = decision["selected_indices"]

        def ok_non_commit() -> ChatResponse:
            fallback = reply or "Quick question: could you summarize the hiring goal and priorities?"
            return ChatResponse(
                reply=fallback,
                recommendations=[],
                end_of_conversation=False,
            )

        if mode == "refuse":
            return ChatResponse(
                reply=(
                    reply
                    if len(reply) > 60
                    else (
                        "I can only guide you toward SHL Individual Test Solutions from the catalog. "
                        "I can’t help with legal/policy interpretation, compensation advice, or unrelated topics."
                    )
                ),
                recommendations=[],
                end_of_conversation=True,
            )

        if mode == "compare" and not force_commit:
            return ChatResponse(
                reply=reply or "I can explain differences grounded in catalog fields.",
                recommendations=[],
                end_of_conversation=False,
            )

        if mode == "clarify" and not force_commit:
            return ChatResponse(
                reply=reply or "What role are you assessing, and what are the top priorities?",
                recommendations=[],
                end_of_conversation=False,
            )

        # If forced late in the transcript, comparisons should still remain non-committal on shortlists.
        if mode == "compare" and force_commit:
            return ChatResponse(
                reply=reply
                or "Here’s the comparison based on the grounded catalog excerpts in this retrieval window.",
                recommendations=[],
                end_of_conversation=False,
            )

        wants_commit = (mode == "recommend") or (force_commit and mode == "clarify")

        if not wants_commit:
            return ok_non_commit()

        recs = _map_indices_to_recommendations(
            picks=picks,
            indices_one_based=selected if mode == "recommend" else [],
            max_items=self.settings.max_recommendations,
        )

        if not recs:
            take = max(6, min(8, len(picks))) if force_commit else 0
            if take:
                recs = _fallback_recommend_top(picks[:take], max_items=min(take, 10))

        if not recs:
            recs = _fallback_recommend_top(picks, max_items=min(8, self.settings.max_recommendations))

        # If we are committing recommendations, treat this turn as a final shortlist delivery.
        if wants_commit and recs:
            end_flag = True

        # Committing should stay within catalog bounds enforced by retrieval mapping/fallback tops.
        return ChatResponse(
            reply=(
                reply
                if reply
                else "Here’s a pragmatic shortlist grounded in the SHL catalog candidates above."
            ),
            recommendations=recs[: self.settings.max_recommendations],
            end_of_conversation=bool(end_flag),
        )
