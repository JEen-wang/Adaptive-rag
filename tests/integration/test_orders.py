import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.request_scope import request_session
from app.repositories.db import init_schema
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.order_repository import OrderRepository
from app.services.seed import seed_demo_data
from app.tools.aftersale_tools import CreateRefundRequestTool
from app.tools.base import ToolContext
from app.tools.order_tools import GetOrderTool


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_schema(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await seed_demo_data(session)
        await session.commit()
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_refund_is_idempotent_and_transactional(session_factory) -> None:
    async with request_session(session_factory) as session:
        repo = OrderRepository(session)
        first = await repo.create_refund(order_id="ORD10003", reason="不想要了", trace_id="tr_1")
        keys = IdempotencyRepository(session)
        await keys.put("act_1", "fp-refund", first)
        again = await keys.get_if_matches("act_1", "fp-refund")
        assert again == first
        await session.commit()

    async with request_session(session_factory) as session:
        refunds = await OrderRepository(session).get_refunds("ORD10003")
        assert len(refunds) == 1


@pytest.mark.asyncio
async def test_order_is_scoped_to_owner(session_factory) -> None:
    async with request_session(session_factory) as session:
        tool = GetOrderTool(OrderRepository(session))
        ctx = ToolContext(user_id="someone_else", session_id="s", trace_id="t")
        with pytest.raises(Exception, match="order not found"):
            await tool.execute(tool.parse({"order_id": "ORD10001"}), ctx)


@pytest.mark.asyncio
async def test_refund_tool_persists_via_repository(session_factory) -> None:
    async with request_session(session_factory) as session:
        tool = CreateRefundRequestTool(OrderRepository(session))
        ctx = ToolContext(user_id="u_demo", session_id="s", trace_id="t")
        result = await tool.run({"order_id": "ORD10003", "reason": "质量问题"}, ctx)
        assert result.success
        await session.commit()
    async with request_session(session_factory) as session:
        refunds = await OrderRepository(session).get_refunds("ORD10003")
        assert refunds[0].status == "requested"
