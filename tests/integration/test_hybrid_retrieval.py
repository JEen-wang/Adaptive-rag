import pytest

from app.config.settings import clear_settings_cache, get_settings
from app.core.exceptions import RetrievalError
from app.providers.embeddings import HashEmbeddingProvider
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.ingest import ingest_to_memory
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever


@pytest.mark.asyncio
async def test_hybrid_retrieves_return_policy() -> None:
    clear_settings_cache()
    embedder = HashEmbeddingProvider(dim=get_settings().embedding_dim)
    bm25, store, chunks = await ingest_to_memory("knowledge", embedder)
    assert chunks
    retriever = HybridRetriever(bm25, VectorRetriever(store, embedder), rrf_k=60)
    hits = await retriever.retrieve("定制商品能不能七天无理由退货", top_k=5)
    assert hits
    blob = " ".join(hit.content for hit in hits)
    assert "定制" in blob or "无理由" in blob


@pytest.mark.asyncio
async def test_empty_knowledge_base_returns_no_hits() -> None:
    retriever = HybridRetriever(
        BM25Retriever(),
        VectorRetriever(InMemoryVectorStore(), HashEmbeddingProvider()),
        rrf_k=60,
    )
    assert await retriever.retrieve("尚未收录的问题", top_k=5) == []


@pytest.mark.asyncio
async def test_both_retrievers_failing_raises_service_error(monkeypatch) -> None:
    bm25 = BM25Retriever()
    vector = VectorRetriever(InMemoryVectorStore(), HashEmbeddingProvider())

    def fail_bm25(query: str, *, top_k: int):
        raise RuntimeError("bm25 unavailable")

    async def fail_vector(query: str, *, top_k: int):
        raise RuntimeError("vector unavailable")

    monkeypatch.setattr(bm25, "search", fail_bm25)
    monkeypatch.setattr(vector, "search", fail_vector)
    retriever = HybridRetriever(bm25, vector, rrf_k=60)
    with pytest.raises(RetrievalError):
        await retriever.retrieve("问题", top_k=5)
