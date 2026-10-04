import pytest
from pydantic import ValidationError

from agentic_rag.models.query import QueryInput


def test_query_input():
    query = QueryInput(
        conversation_id="conv-123",
        query="What is the status of Project X?",
    )

    assert query.conversation_id == "conv-123"
    assert query.query == "What is the status of Project X?"


def test_query_input_without_conversation_id():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    assert query.conversation_id is None


def test_query_input_requires_query():
    with pytest.raises(ValidationError):
        QueryInput(conversation_id="conv-123")
