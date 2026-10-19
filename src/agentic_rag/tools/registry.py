from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.tools.interface import Tool


class CapabilityRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._capabilities: dict[str, CapabilityDefinition] = {}

    def register(
        self,
        capability: CapabilityDefinition,
        tool: Tool,
    ) -> None:
        if capability.name in self._tools:
            raise ValueError(f"Capability already registered: {capability.name}")

        self._tools[capability.name] = tool
        self._capabilities[capability.name] = capability

    def get(self, capability: str) -> Tool:
        try:
            return self._tools[capability]
        except KeyError:
            raise ValueError(f"Unsupported capability: {capability}") from None

    def get_capability(self, capability: str) -> CapabilityDefinition:
        try:
            return self._capabilities[capability]
        except KeyError:
            raise ValueError(f"Unsupported capability: {capability}") from None

    def list_capabilities(self) -> list[CapabilityDefinition]:
        return list(self._capabilities.values())
