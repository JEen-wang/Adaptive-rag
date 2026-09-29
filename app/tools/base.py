from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.core.enums import ToolRisk
from app.core.exceptions import InvalidRequestError, ToolExecutionError
from app.schemas.agent import ToolResult


class ToolContext(BaseModel):
    user_id: str
    session_id: str
    trace_id: str
    confirmed_action_id: str | None = None
    idempotency_key: str | None = None


class BaseTool(Protocol):
    name: str
    description: str
    risk: ToolRisk
    input_model: type[BaseModel]

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult: ...


class Tool:
    name: str
    description: str
    risk: ToolRisk = ToolRisk.READ
    input_model: type[BaseModel]

    def parse(self, arguments: dict[str, Any]) -> BaseModel:
        try:
            return self.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise InvalidRequestError(f"invalid arguments for {self.name}: {exc}") from exc

    async def run(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        parsed = self.parse(arguments)
        try:
            return await self.execute(parsed, context)
        except InvalidRequestError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"{self.name} failed") from exc

    async def execute(self, parsed: BaseModel, context: ToolContext) -> ToolResult:
        raise NotImplementedError

    def openai_schema(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }
