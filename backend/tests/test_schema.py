import pytest
from pydantic import ValidationError

from app.models.schemas import ChatRequest, ChatResponse, RecommendationItem


def test_chat_response_schema_roundtrip():
    obj = ChatResponse(
        reply="hello",
        recommendations=[
            RecommendationItem(name="Foo", url="https://www.shl.com/ex", test_type="K"),
        ],
        end_of_conversation=False,
    )
    dumped = obj.model_dump(mode="json")
    assert set(dumped.keys()) == {"reply", "recommendations", "end_of_conversation"}


def test_chat_request_requires_messages():
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])


def test_recommendations_only_expected_fields():
    item = RecommendationItem(name="Foo", url="https://www.shl.com/ex", test_type="")
    dumped = item.model_dump(mode="json")
    assert set(dumped.keys()) == {"name", "url", "test_type"}
