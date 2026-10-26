from typing import Protocol

from agentic_rag.models.evidence import Evidence
from agentic_rag.models.execution_result import ExecutionResult


class EvidenceNormalizer(Protocol):
    def normalize(self, result: ExecutionResult) -> list[Evidence]: ...
