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


@pytest.mark.parametrize("query", ["", "   "])
def test_query_input_rejects_blank_query(query):
    with pytest.raises(ValidationError):
        QueryInput(query=query)


def test_query_input_strips_query_whitespace():
    query = QueryInput(query="  What is the status of Project X?  ")

    assert query.query == "What is the status of Project X?"


def test_query_input_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        QueryInput(query="What is the status?", unexpected=True)
