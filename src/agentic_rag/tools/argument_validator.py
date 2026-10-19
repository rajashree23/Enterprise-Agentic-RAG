from typing import Any

from agentic_rag.models.capability import CapabilityDefinition

SUPPORTED_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def validate_arguments(
    capability: CapabilityDefinition,
    arguments: dict[str, Any],
) -> None:
    """Validate tool arguments against a capability's declared schema."""

    unknown_arguments = set(arguments) - set(capability.arguments)

    if unknown_arguments:
        raise ValueError(
            f"Unsupported arguments for capability "
            f"'{capability.name}': {sorted(unknown_arguments)}"
        )

    for name, expected_type in capability.arguments.items():
        if expected_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported type '{expected_type}' "
                f"for argument '{name}' in capability "
                f"'{capability.name}'"
            )

        if name not in arguments:
            raise ValueError(
                f"Missing required argument '{name}' for capability '{capability.name}'"
            )

        value = arguments[name]
        python_type = SUPPORTED_TYPES[expected_type]

        # bool is a subclass of int in Python, so check it explicitly.
        if expected_type == "integer" and isinstance(value, bool):
            raise ValueError(f"Argument '{name}' must be an integer")

        if expected_type == "number" and isinstance(value, bool):
            raise ValueError(f"Argument '{name}' must be a number")

        if not isinstance(value, python_type):
            raise TypeError(f"Argument '{name}' must be of type '{expected_type}'")
