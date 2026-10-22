"""Health and readiness response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyStatus(BaseModel):
    name: str
    ready: bool
    detail: str = ""


class ReadinessResponse(BaseModel):
    ready: bool
    dependencies: list[DependencyStatus] = Field(default_factory=list)


class CapabilitiesResponse(BaseModel):
    """Resolved runtime backends and whether the process is degraded."""

    database: str
    cache: str
    vector_store: str
    retriever: str
    reranker: str
    llm: str
    degraded: bool
