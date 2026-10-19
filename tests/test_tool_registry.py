import pytest

from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.tool import ToolRequest, ToolResult
from agentic_rag.tools.registry import CapabilityRegistry


class FakeTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            capability=request.capability,
            success=True,
            data={"message": "Executed"},
        )


def test_registry_registers_and_resolves_tool():
    registry = CapabilityRegistry()
    tool = FakeTool()

    capability = CapabilityDefinition(
        name="github.search",
        description="Search GitHub issues and pull requests.",
        arguments={"query": "string"},
    )

    registry.register(capability, tool)

    assert registry.get("github.search") is tool


def test_registry_rejects_duplicate_capability():
    registry = CapabilityRegistry()

    capability = CapabilityDefinition(
        name="github.search",
        description="Search GitHub issues and pull requests.",
        arguments={"query": "string"},
    )

    registry.register(capability, FakeTool())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(capability, FakeTool())


def test_registry_rejects_unknown_capability():
    registry = CapabilityRegistry()

    with pytest.raises(ValueError, match="Unsupported capability"):
        registry.get("github.search")


def test_registry_rejects_empty_capability():
    with pytest.raises(ValueError):
        CapabilityDefinition(
            name="",
            description="Test capability",
        )
