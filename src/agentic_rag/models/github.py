from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GitHubIssueArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    issue_number: int = Field(gt=0)

    @field_validator("owner", "repo")
    @classmethod
    def validate_path_component(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("Must not contain leading or trailing whitespace")

        if value in {".", ".."}:
            raise ValueError("Must not be a relative path component")

        if not all(
            character.isascii() and (character.isalnum() or character in "-_.")
            for character in value
        ):
            raise ValueError(
                "Use only ASCII letters, digits, hyphens, underscores, or dots"
            )

        return value


class GitHubSearchArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must contain non-whitespace characters")

        return value


class GitHubIssueRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    repository: str
    number: int
    record_type: Literal["issue", "pull_request"]
    title: str
    body: str | None
    state: Literal["open", "closed"]
    url: str
    author: str | None
    created_at: datetime
    updated_at: datetime


class GitHubSearchResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(ge=0)
    incomplete_results: bool
    items: list[GitHubIssueRecord]


class GitHubCommentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    repository: str
    issue_number: int
    record_type: Literal["issue_comment"] = "issue_comment"
    body: str | None
    url: str
    author: str | None
    created_at: datetime
    updated_at: datetime
