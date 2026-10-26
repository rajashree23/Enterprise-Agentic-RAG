from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
    ToolCalled,
    ToolError,
)
from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.argument_validator import validate_arguments
from agentic_rag.tools.registry import CapabilityRegistry


class ToolExecutionOperation:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        step: ExecutionStep,
    ) -> ExecutionResult:
        tool_called = ToolCalled(
            tool_id=step.capability,
            tool_name=step.capability,
        )

        try:
            tool = self.registry.get(step.capability)
            capability_definition = self.registry.get_capability(step.capability)

            validate_arguments(
                capability_definition,
                step.arguments,
            )

            request = ToolRequest(
                capability=step.capability,
                arguments=step.arguments,
            )

            tool_result = await tool.execute(request)

            if not tool_result.success:
                return ExecutionResult(
                    step_id=step.step_id,
                    sub_query_id=step.sub_query_id,
                    status=ExecutionStatus.FAILED,
                    tool_called=tool_called,
                    tool_error=ToolError(
                        error_id="tool_execution_failed",
                        error_title="Tool execution failed",
                        error_msg=(
                            tool_result.error
                            or "The tool returned an unsuccessful result."
                        ),
                    ),
                )

            items = tool_result.data.get("items")

            if isinstance(items, list) and all(
                isinstance(item, dict) for item in items
            ):
                response = items
                metadata = {
                    key: value
                    for key, value in tool_result.data.items()
                    if key != "items"
                }
            else:
                response = [tool_result.data]
                metadata = {}

            return ExecutionResult(
                step_id=step.step_id,
                sub_query_id=step.sub_query_id,
                status=ExecutionStatus.SUCCESS,
                tool_called=tool_called,
                tool_response=response,
                tool_metadata=metadata,
            )

        except (ValueError, TypeError, TimeoutError) as exc:
            return ExecutionResult(
                step_id=step.step_id,
                sub_query_id=step.sub_query_id,
                status=ExecutionStatus.FAILED,
                tool_called=tool_called,
                tool_error=ToolError(
                    error_id="tool_execution_error",
                    error_title="Tool execution error",
                    error_msg=str(exc),
                ),
            )
