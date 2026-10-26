from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    evidence_id: str = Field(min_length=1)


class SupportedClaim(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class Synthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[SupportedClaim] = Field(min_length=1)
    limitations: list[str]
