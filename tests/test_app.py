from agentic_rag.app import hello


def test_hello():
    assert hello() == "Agentic RAG is running!"
