# 面试问答材料

这一目录存放与本仓库对应的面试问答稿。所有答案都以仓库里的真实代码和 [`eval/MEASURED.md`](../../eval/MEASURED.md) 的数字口径为准，不写仓库里不存在的能力。

## 目录

| 文件 | 主题 | 对应代码 |
|---|---|---|
| [01-langgraph-planning-intent.md](01-langgraph-planning-intent.md) | LangGraph 状态机、规划执行、意图识别与评测 | `app/agents/`、`app/tools/` |
| [02-adaptive-rag-chunking-hybrid.md](02-adaptive-rag-chunking-hybrid.md) | Adaptive-RAG、切分索引、查询改写、Hybrid 与多跳 | `app/retrieval/` |
| [03-rerank-memory-skill-mcp.md](03-rerank-memory-skill-mcp.md) | 精排口径、记忆压缩、Skill/MCP 与护栏 | `app/retrieval/reranker.py`、`app/memory/`、`app/mcp/`、`app/guardrails/` |
| [04-full-collection.md](04-full-collection.md) | 以上三篇合并全集 | 全部 |

## 与手册的关系

- 正式工程手册从 [`docs/README.md`](../README.md) 进入，按 Diátaxis 组织（Quickstart → Concepts → Reference → Operations）。
- 本目录是**答辩视角**的补充材料，逐题给出「30 秒开口 + 对照代码的详细答案」，不重复手册的章节结构。
- 数字口径只有一处基准：[`eval/MEASURED.md`](../../eval/MEASURED.md) 与 [`docs/14-evaluation-report.md`](../14-evaluation-report.md)。
