import pytest

from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.tools.argument_validator import validate_arguments


@pytest.fixture
def capability():
    return CapabilityDefinition(
        name="github.search",
        description="Search GitHub issues and pull requests.",
        arguments={"query": "string"},
    )


def test_accepts_valid_arguments(capability):
    validate_arguments(
        capability,
        {"query": "Project X"},
    )


def test_rejects_unknown_arguments(capability):
    with pytest.raises(ValueError, match="Unsupported arguments"):
        validate_arguments(
            capability,
            {"unknown": "Project X"},
        )


def test_rejects_missing_arguments(capability):
    with pytest.raises(ValueError, match="Missing required argument"):
        validate_arguments(capability, {})


def test_rejects_incorrect_argument_type(capability):
    with pytest.raises(TypeError, match="must be of type 'string'"):
        validate_arguments(
            capability,
            {"query": 123},
        )
