from dataclasses import dataclass


@dataclass
class Settings:
    app_name: str = "agentic-rag"
    environment: str = "local"
