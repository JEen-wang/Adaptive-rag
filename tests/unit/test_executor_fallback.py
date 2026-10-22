import pytest
from pydantic import BaseModel, Field

from app.agents.nodes.executor import execute_with_fallback
from app.core.enums import ToolRisk
from app.core.exceptions import ToolExecutionError
from app.schemas.agent import PlanStep, ToolResult
from app.tools.base import Tool, ToolContext
from app.tools.registry import ToolRegistry


class _Query(BaseModel):
    query: str = Field(default="")


class _FailingOrder(Tool):
    name = "get_order"
    description = "fail"
    risk = ToolRisk.READ
    input_model = _Query

    async def execute(self, parsed: BaseModel, context: ToolContext) -> ToolResult:
        raise ToolExecutionError("order lookup failed")


class _Knowledge(Tool):
    name = "search_knowledge"
    description = "kb"
    risk = ToolRisk.READ
    input_model = _Query

    async def execute(self, parsed: BaseModel, context: ToolContext) -> ToolResult:
        return ToolResult(name=self.name, success=True, output={"chunks": [{"content": "政策"}]})


@pytest.mark.asyncio
async def test_order_lookup_failure_does_not_fall_back_to_policy() -> None:
    registry = ToolRegistry()
    registry.register(_FailingOrder())
    registry.register(_Knowledge())
    with pytest.raises(ToolExecutionError, match="get_order failed"):
        await execute_with_fallback(
            registry.get("get_order"),
            PlanStep(step_id=1, goal="order", tool_name="get_order", arguments={"query": "x"}),
            ToolContext(user_id="u", session_id="s", trace_id="t"),
            registry,
            "定制杯还能退吗",
        )


class _FailingShipment(_FailingOrder):
    name = "track_shipment"


class _Order(_Knowledge):
    name = "get_order"


@pytest.mark.asyncio
async def test_shipment_failure_uses_order_status_fallback() -> None:
    registry = ToolRegistry()
    registry.register(_FailingShipment())
    registry.register(_Order())
    result = await execute_with_fallback(
        registry.get("track_shipment"),
        PlanStep(step_id=1, goal="shipment", tool_name="track_shipment", arguments={"query": "x"}),
        ToolContext(user_id="u", session_id="s", trace_id="t"),
        registry,
        "物流到哪了",
    )
    assert result.name == "get_order"
    assert result.output["fallback_from"] == "track_shipment"
