# Adaptive-RAG 多智能体电商客服

按问题复杂度选择 Direct / Single / Multi / Agent，而不是对所有 query 做一次向量检索。

工程约束：分层、Schema、超时与退避、工具权限、HITL、评测集、可观测性。README 与 [技术文档](docs/README.md) 只写仓库里真实存在的能力。

每章重点固定三块：**要点 → 代码摘要（带文件路径）→ 为什么**。从 [docs/README.md](docs/README.md) 按问题跳转。

## 文档

生产向分章手册（结构参考常见开源项目的 Docs 首页：先 Quickstart，再 Concepts / Reference / Operations）：

**[docs/README.md](docs/README.md)**

1. [产品与问题](docs/01-overview.md) · 2. [快速开始](docs/02-getting-started.md) · 3. [架构](docs/03-architecture.md)  
4. [检索](docs/04-adaptive-rag.md) · 5. [智能体与工具](docs/05-agents-and-tools.md) · 6. [API](docs/06-api-reference.md)  
7. [配置](docs/07-configuration.md) · 8. [可靠性](docs/08-reliability.md) · 9. [安全](docs/09-security.md)  
10. [评测](docs/10-evaluation.md) · 11. [部署](docs/11-deployment.md) · 12. [限制](docs/12-limitations.md)  
13. [面试稿：玩具 RAG vs 工程化](docs/13-interview-engineering-rag.md) · 14. [测评报告](docs/14-evaluation-report.md)  
15. [解析、切块、向量化与检索](docs/15-ingest-and-retrieval.md)  
16. [八股对照本仓库](docs/16-interview-bagu-map.md)

实测口径：[`eval/MEASURED.md`](eval/MEASURED.md)；完整测评：[14 · 测评报告](docs/14-evaluation-report.md)。

## 快速开始

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# 本地 bge-small 召回 + Cross-Encoder 精排（可选）：pip install -e ".[rerank]"
# Unstructured 解析 PDF/Office/HTML/图片（可选）：pip install -e ".[docs]"
cp .env.example .env    # 填 DEEPSEEK_API_KEY，勿提交
uvicorn app.asgi:app --reload --port 8000
python -m app.cli    # 同一终端连续对话（API 已启动则直接连上）
```

```bash
curl -s localhost:8000/api/v1/health
curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"定制马克杯过了7天但是有质量问题能退吗","user_id":"u_demo"}'
```

演示订单：`ORD10001` 已发货耳机，`ORD10002` 已签收定制杯，`ORD10003` 已支付未发货 T 恤。  
写操作返回 `pending_action`，带回 `confirm_action_id` 才执行。

完整步骤与 Docker：[02 · 快速开始](docs/02-getting-started.md)、[11 · 部署](docs/11-deployment.md)。

```bash
pytest -q
python -m eval.runner --task retrieval
```

## 实测摘要

DeepSeek `deepseek-chat`。意图 100 条；检索 65 条 / 39 篇文档。稠密召回 `BAAI/bge-small-zh-v1.5`，精排 `BAAI/bge-reranker-base`（2026-08-22 12:13Z）。

| 指标 | 数字 |
|---|---|
| 意图 | 规则 51% → intent_v3+覆盖 **100%** |
| 仅 bge-small P@1 / R@3 / MRR | **83.1% / 94.6% / 0.89** |
| Hybrid+CE Precision@1 / Recall@3 / MRR | **89.2% / 97.7% / 0.94** |
| BM25（对照） | 76.9% / 90% / 0.84 |
| 无检索→RAG+自纠错幻觉率 | 20% → **0%**（65 条，同模型裁判） |
| E2E P50 / P95 | 4.9s / 5.8s（关键词 9/11） |

细节见 [14 · 测评报告](docs/14-evaluation-report.md)、[10 · 评测](docs/10-evaluation.md)、[`eval/MEASURED.md`](eval/MEASURED.md)。
