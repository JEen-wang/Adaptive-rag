"""Liveness and readiness probes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.schemas.health import (
    CapabilitiesResponse,
    DependencyStatus,
    LivenessResponse,
    ReadinessResponse,
)
from app.services.container import AppContainer

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(
    container: AppContainer = Depends(get_container),
) -> ReadinessResponse:
    """Hard dependency: database. Redis / Qdrant / LLM key are reported but optional."""
    deps: list[DependencyStatus] = []
    try:
        from sqlalchemy import text

        async with container.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        deps.append(DependencyStatus(name="database", ready=True))
    except Exception as exc:
        deps.append(DependencyStatus(name="database", ready=False, detail=type(exc).__name__))

    llm_ok = await container.llm.ping()
    deps.append(
        DependencyStatus(
            name="llm",
            ready=llm_ok,
            detail="configured" if llm_ok else "missing_api_key_using_fake",
        )
    )
    if container.redis is not None:
        try:
            await container.redis.ping()
            deps.append(DependencyStatus(name="redis", ready=True))
        except Exception as exc:
            deps.append(DependencyStatus(name="redis", ready=False, detail=type(exc).__name__))
    else:
        deps.append(DependencyStatus(name="redis", ready=True, detail="not_configured"))

    store = container.vector_store
    if store is not None:
        try:
            vector_ok = bool(store.ping())
            deps.append(
                DependencyStatus(
                    name="vector_store",
                    ready=vector_ok,
                    detail=type(store).__name__,
                )
            )
        except Exception as exc:
            deps.append(
                DependencyStatus(name="vector_store", ready=False, detail=type(exc).__name__)
            )

    ready = all(item.ready for item in deps if item.name == "database")
    return ReadinessResponse(ready=ready, dependencies=deps)


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities(
    container: AppContainer = Depends(get_container),
) -> CapabilitiesResponse:
    """Report the concrete backends selected after startup and fallbacks."""
    reranker_provider = getattr(container.chat_service, "_reranker", None)
    provider = getattr(reranker_provider, "_provider", None)
    reranker = getattr(provider, "backend", "unknown")
    llm = "deepseek" if container.settings.llm_configured else "offline"
    cache = "redis" if container.redis is not None else "memory"
    vector_store_type = type(container.vector_store).__name__ if container.vector_store else "none"
    vector_store = "memory" if vector_store_type == "InMemoryVectorStore" else vector_store_type
    retriever = "hybrid" if container.settings.embedding_configured or container.settings.local_embedding_configured else "bm25"
    degraded = any(
        value in {"offline", "memory", "none", "lexical", "bm25"}
        for value in (llm, cache, vector_store, reranker, retriever)
    )
    return CapabilitiesResponse(
        database="sqlite" if container.settings.use_sqlite else "postgresql",
        cache=cache,
        vector_store=vector_store,
        retriever=retriever,
        reranker=reranker,
        llm=llm,
        degraded=degraded,
    )
