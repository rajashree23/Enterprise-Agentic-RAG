from pydantic import BaseModel, ConfigDict, Field


class CapabilityDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    arguments: dict[str, str] = Field(default_factory=dict)
