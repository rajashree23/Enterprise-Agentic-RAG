from pydantic import BaseModel, ConfigDict, Field


class DirectAnswer(BaseModel):
    """Answer for questions that do not require registered tools or evidence."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
