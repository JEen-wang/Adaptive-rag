

<h1 align="center">Adaptive RAG · 电商客服工作流</h1>

<p align="center"><strong>让简单问题直接回答，让复杂问题找到证据，让业务操作停在确认之前。</strong></p>
<p align="center">FastAPI × LangGraph × 混合检索 · API、流式对话与 ChatGPT 风格 Web 工作台</p>

<p align="center">
  <a href="https://github.com/JEen-wang/Adaptive-rag/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/JEen-wang/Adaptive-rag/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-22c55e"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="React and TypeScript" src="https://img.shields.io/badge/Web-React%20%2B%20TypeScript-149eca?logo=react&logoColor=white">
</p>

<p align="center">
  <a href="#overview">项目亮点</a> · <a href="#quickstart">快速开始</a> ·
  <a href="#architecture">系统架构</a> · <a href="#evaluation">实测结果</a> ·
  <a href="#resume">简历写法</a> ·
  <a href="#docs">完整文档</a> · <a href="#limitations">使用边界</a>
</p>

---

<a id="overview"></a>

## ✨ 一眼看懂

> **Adaptive RAG** 的核心决策是：这个问题需要直接回答、检索一条证据、交叉核对多条证据、调用业务工具，还是拒绝处理？

电商客服里的问题跨度很大。「你好」无需查知识库；退货政策需要可靠出处；「定制商品超过七天但有质量问题」要同时判断定制、时效与质量例外；取消订单则必须检查订单状态、权限与确认。项目用明确的路由策略处理这些差异，避免把所有输入都塞进同一条向量检索链路。

| 能力 | 你能看到什么 | 关键实现 |
|:---|:---|:---|
| 🧭 **按复杂度路由** | 每次回答带有 `strategy`，便于追踪实际路径 | [Graph 与节点](app/agents/graph.py) · [策略枚举](app/core/enums.py) |
| 🔎 **有出处的检索** | BM25、稠密向量、RRF 融合与精排；回答可带 `citations` | [检索模块](app/retrieval/) |
| 🧩 **多跳与自纠错** | 复合问题拆分检索，答案经过忠实度检查 | [智能体节点](app/agents/nodes/) |
| 🛡️ **人工确认** | 高风险写操作先返回 `pending_action`，确认后才执行 | [工具与权限](app/tools/) |
| 💬 **Web 对话工作台** | 流式显示、引用、本地会话搜索、深色模式与确认卡片 | [前端](frontend/) |
| 📈 **可测可观测** | 离线评测、回归测试、结构化日志与 Prometheus 指标 | [评测](eval/) · [可观测性](app/observability/) |

### 五条处理路径

| 策略 | 适合的问题 | 处理方式 |
|:---:|:---|:---|
| `DIRECT` | 问候、闲聊 | 直接生成，不做知识检索 |
| `SINGLE` | 单一政策问题 | 一轮混合检索与精排 |
| `MULTI` | 多条件、跨条款问题 | 查询改写、多路检索与自纠错 |
| `AGENT` | 查询订单、物流或发起业务操作 | 规划后调用受权限约束的工具 |
| `REFUSE` | 越权、注入或证据不足 | 拒答或引导人工处理 |

> [!TIP]
> 第一次了解项目，可以先看[架构图](#architecture)，再按[快速开始](#quickstart)提问。想看每条路径怎样落到代码，读[智能体与工具](docs/05-agents-and-tools.md)。

<a id="quickstart"></a>

## 🚀 快速开始

默认使用 SQLite 和内存检索组件，不要求先部署 Redis 或 Qdrant。需要 **Python 3.11+**；Web 开发另需满足[前端 Node.js 要求](frontend/README.md)。

### 1. 安装并启动 API

```bash
git clone https://github.com/JEen-wang/Adaptive-rag.git
cd Adaptive-rag
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.asgi:app --reload --port 8000
```

Windows PowerShell 激活虚拟环境可使用 `.venv\Scripts\Activate.ps1`。首次启用本地 Embedding / Cross-Encoder 时可能需要下载模型；需要完整的本地精排依赖可安装 `pip install -e ".[rerank]"`。更多选项见[配置参考](docs/07-configuration.md)。

`.env` 中的 `DEEPSEEK_API_KEY` 可留空：此时使用 `FakeLLMProvider` 验证链路，回答是占位内容。要体验真实生成回答，需要配置可用的 DeepSeek 密钥。**不要提交 `.env` 或密钥。**

### 2. 发送第一条消息

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"定制马克杯过了七天，但有质量问题还能退吗？","user_id":"u_demo"}'
```

响应包含 `answer`、`strategy`、`trace_id`，需要检索时还会带 `citations`。也可以运行 `python -m app.cli` 进入终端对话；流式接口为 `POST /api/v1/chat/stream`，完整字段见 [API 参考](docs/06-api-reference.md)。

### 3. 打开 Web 工作台

保持 API 运行，另开终端：

```bash
cd frontend
npm ci
npm run dev
```

访问 **http://127.0.0.1:5173**。开发服务器会把 `/api` 代理到本地 FastAPI。执行 `npm run build` 后，FastAPI 检测到 `frontend/dist` 也会在根路径提供页面；Docker 镜像会自动构建前端。前端会话列表存于浏览器本地，详见[前端 README](frontend/README.md)。

<details>
<summary><strong>🧪 想体验订单工具与人工确认？展开查看演示数据步骤</strong></summary>

<br>

当前分支默认启动**不会自动写入**演示订单。先停止 API，在仓库根目录、已激活虚拟环境的终端执行：

```bash
python - <<'PY'
import asyncio
from app.config.settings import get_settings
from app.services.container import build_container

async def main():
    container = await build_container(get_settings(), seed=True)
    await container.aclose()

asyncio.run(main())
PY
```

然后重新启动 API。种子会为 `u_demo` 写入 `ORD10001`（已发货）、`ORD10002`（已签收）和 `ORD10003`（已支付未发货）。例如询问“取消订单 ORD10003”，系统先给出 `pending_action.action_id`；确认请求携带该 ID 后才执行。详见 [HITL 与幂等](docs/05-agents-and-tools.md)。

</details>

<a id="architecture"></a>

## 🏗️ 系统架构

```mermaid
flowchart TD
    START["🚀 启动服务"] --> INIT["⚙️ 加载配置并装配 ChatService"]
    INIT --> INGEST["📚 全量构建知识索引"]
    INGEST --> READY["✅ API 就绪"]

    subgraph KB["知识库准备 · 启动时"]
        DOCS["FAQ / 退货 / 配送等文档"] --> PARSE["解析 · 清洗 · 切分 · 去重"]
        PARSE --> BM25["BM25 索引"]
        PARSE --> EMBED["Embedding 向量化"] --> VECTOR["Qdrant / 内存向量索引"]
    end
    INGEST -.-> DOCS

    READY --> USER["👤 Web / CLI / HTTP 提问"]
    USER --> API["FastAPI · JSON / SSE"]
    API --> GUARD["🛡️ 输入护栏与查询边界"]
    GUARD -->|通过| INTENT["🧠 DeepSeek 意图识别 + 歧义规则覆盖"]
    GUARD -->|拒绝| REFUSE["拒答 / 转人工提示"]
    INTENT --> ROUTE{"🎯 Adaptive 路由<br/>意图 + 问题复杂度"}
    ROUTE -->|DIRECT| DIRECT["直接生成"]
    ROUTE -->|SINGLE| SINGLE["查询改写 · 单轮检索"]
    ROUTE -->|MULTI| MULTI["Self-RAG 式循环<br/>改写 · 检索 · 证据评估"]
    ROUTE -->|AGENT| PLAN["规划器 · Skill 选择 · 子任务分解"]
    ROUTE -->|REFUSE| REFUSE

    subgraph RETRIEVAL["混合检索 · 证据链"]
        SEARCH["BM25 + 向量召回"] --> FUSE["RRF 融合去重"] --> RERANK["Cross-Encoder 精排"]
    end
    BM25 -.-> SEARCH
    VECTOR -.-> SEARCH
    SINGLE --> SEARCH
    RERANK -->|单轮结果| GEN["📝 生成回答"]
    MULTI -->|逐轮调用| SEARCH
    RERANK -->|多轮结果| MULTI
    MULTI -->|证据充分或达到跳数上限| GEN

    PLAN --> EXEC["执行器 · 统一工具注册表"]
    EXEC -->|只读工具失败| FALLBACK["备用工具 / 知识检索"] --> GEN
    EXEC -->|查询成功| GEN
    EXEC -->|写操作| CONFIRM["权限校验 · 待用户确认"] --> GEN
    EXEC -.-> TOOLS["订单 / 物流 / 商品 / MCP 工具"]

    DIRECT --> GEN
    GEN --> CHECK["🔍 忠实度检查 · 必要时自纠错"]
    CHECK --> MEMORY["🧠 128k 预算 · 滑动窗口 · 动态摘要"]
    REFUSE --> MEMORY
    MEMORY --> OUTPUT["📤 回答 / 引用 / 待确认动作 / trace_id"]
    OUTPUT --> USER

    classDef setup fill:#e8f5e9,stroke:#2e7d32,color:#173b1b
    classDef routing fill:#e3f2fd,stroke:#1565c0,color:#123a63
    classDef retrieve fill:#f3e5f5,stroke:#7b1fa2,color:#442051
    classDef tool fill:#fff3e0,stroke:#ef6c00,color:#613600
    classDef output fill:#e0f7fa,stroke:#00838f,color:#12494d
    classDef fallback fill:#ffebee,stroke:#c62828,color:#63272a
    class START,INIT,INGEST,READY,DOCS,PARSE,BM25,EMBED,VECTOR setup
    class INTENT,ROUTE,DIRECT,SINGLE,MULTI routing
    class SEARCH,FUSE,RERANK,GEN,CHECK retrieve
    class PLAN,EXEC,CONFIRM,TOOLS tool
    class API,USER,MEMORY,OUTPUT output
    class GUARD,REFUSE,FALLBACK fallback
```

图按“启动与索引准备 → 查询分析与路由 → 检索或工具执行 → 生成、校验与记忆”展开，结构组织参考 [Datawhale《图 RAG 系统架构》3.1 节](https://github.com/datawhalechina/all-in-rag/blob/main/docs/chapter9/01_graph_rag_architecture.md#31-%E6%95%B4%E4%BD%93%E6%9E%B6%E6%9E%84)。本项目的多跳路径基于文本检索和证据评估；默认数据库为 SQLite，Redis、Qdrant 和远程模型按配置接入。完整节点与降级路径见[架构与运行流程](docs/17-architecture-flow.md)。

<a id="evaluation"></a>

## 📊 实测结果与口径

下面的**检索与生成指标**来自 2026-08-22 的离线评测，具体数据集、模型与运行命令见 [`eval/MEASURED.md`](eval/MEASURED.md) 和[完整报告](docs/14-evaluation-report.md)。报告原始 JSON 未随仓库分发，复现时应以当前环境重新运行。

| 环节 | 样本与设置 | 结果 |
|:---|:---|:---|
| 意图识别 | 100 条，`intent_v3` + 歧义规则覆盖 | **100%**；纯模型结果并非 100% |
| BM25 稀疏检索 | 65 条政策问题 / 39 篇文档 | P@1 **76.9%** · R@3 **90.0%** |
| bge-small 稠密检索 | 同一检索集 | P@1 **83.1%** · R@3 **94.6%** |
| Hybrid + Cross-Encoder | 同一检索集 | P@1 **89.2%** · R@3 **97.7%** · MRR **0.94** |
| RAG + 自纠错生成 | 65 条，同模型裁判 | 忠实度 **100%** · 幻觉率 **0%** |
| 端到端 | 16 条 | 关键词命中 **9/11** · P50 **4.9s** · P95 **5.8s** |

> [!IMPORTANT]
> 这些是**指定离线集合与模型配置**下的测量值，不代表生产环境承诺。该集合上 RRF 与单独使用 bge-small 的检索数字相同，主要增益来自 Cross-Encoder；生成忠实度使用同模型裁判，可能偏乐观。不要把 `0%` 幻觉率理解为真实场景零错误。

CI 在 Python 3.11 / 3.12 上检查锁文件、Ruff、mypy 和 pytest；[查看工作流](.github/workflows/ci.yml)。本地可运行：

```bash
python -m pytest -q
python -m eval.runner --task retrieval
cd frontend && npm test && npm run build
```

<a id="resume"></a>

## 📝 简历写法

**项目名称：基于 Adaptive-RAG 的电商客服系统**

**项目概述：** 针对传统 FAQ 客服对长尾问题命中率低、复杂政策问题需要人工介入，以及常规 RAG 多条件推理和答案溯源不足的问题，设计并实现支持复杂度路由、多轮检索、业务工具和人工确认的客服系统。

- **架构与意图：** 基于 LangGraph 构建护栏、意图识别、复杂度路由、规划器与执行器状态机，接入 DeepSeek-V3、流式输出及指数退避加抖动重试；在自建 100 条测试 query 上，`intent_v3` 加歧义规则覆盖层的意图准确率为 **100%**（纯模型结果不能按此数字表述）。
- **检索与多跳：** 对 FAQ、退货和配送等 39 篇政策文档进行清洗、切分与索引，按问题复杂度选择直接回答、单轮检索、多轮检索或工具执行；结合查询改写、BM25 与 `bge-small-zh-v1.5` 向量召回、RRF 融合及 Self-RAG 式证据评估处理复合问题。
- **检索质量：** 使用本地 Cross-Encoder `BAAI/bge-reranker-base` 精排；在 65 条政策查询上，相比 BM25 基线，Precision@1 从 **76.9% 提升至 89.2%**，Recall@3 从 **90.0% 提升至 97.7%**。该评测集上 RRF 相对单独向量召回没有额外增益，主要提升来自精排。
- **记忆与扩展：** 实现 128k Token 预算的滑动窗口和动态摘要，在上下文利用率达到 50%、70%、85% 时逐级收紧工具结果并触发自动压缩；通过 Skill 定义按需选择退货、订单跟踪和推荐流程，将本地与 MCP 工具接入统一的工具注册表。
- **兜底与护栏：** 在规划和只读工具执行层设置降级路径，并加入查询边界、权限校验、写操作人工确认、答案忠实度检查及自纠错。65 条生成评测中，无检索基线的忠实度为 **80%**、幻觉率为 **20%**；RAG 加自纠错后分别为 **100%** 和 **0%**（同模型裁判的离线结果，不代表线上零幻觉）。

数字来自 [2026-08-22 离线评测记录](eval/MEASURED.md)。如需压缩成 3 条投递版，可优先保留“架构与意图”“检索质量”“兜底与护栏”；更多数字核对见[简历写法详解](docs/tutorial/01-项目总览/chapter4-简历写法.md)。

<a id="docs"></a>

## 🗺️ 从哪里继续阅读

| 目标 | 推荐入口 |
|:---|:---|
| 跑通 API、CLI、Web 与 Docker | [快速开始](docs/02-getting-started.md) · [部署](docs/11-deployment.md) |
| 理解分层、Graph 与路由 | [架构](docs/03-architecture.md) · [Adaptive RAG](docs/04-adaptive-rag.md) |
| 看检索、精排、工具与 HITL | [解析与检索](docs/15-ingest-and-retrieval.md) · [智能体与工具](docs/05-agents-and-tools.md) |
| 查接口、配置、安全与可靠性 | [API](docs/06-api-reference.md) · [配置](docs/07-configuration.md) · [安全](docs/09-security.md) · [可靠性](docs/08-reliability.md) |
| 核对实验口径与数字 | [评测方法](docs/10-evaluation.md) · [原始数字说明](eval/MEASURED.md) |
| 系统学习 RAG 工程实践 | [12 部分教学文档](docs/tutorial/README.md) |
| 准备 Agent/RAG 面试 | [Chapter 1](docs/interview/chapter1.md) · [Chapter 2](docs/interview/chapter2.md) · [Chapter 3](docs/interview/chapter3.md) · [17 维度索引](docs/16-interview-bagu-map.md) |

### 项目教程 · Chapter 对照表

每行对应一篇独立文档；`chapter` 编号在各部分内从 1 开始。完整阅读顺序见[教学文档首页](docs/tutorial/README.md)。

| 阶段 | 部分 | Chapter | 对应内容 |
|:---|:---|:---|:---|
| 总览 | 01 · 项目总览 | [chapter1 · 说明](docs/tutorial/01-项目总览/chapter1-说明.md) | 本部分导读与阅读顺序 |
| 总览 | 01 · 项目总览 | [chapter2 · 项目速览](docs/tutorial/01-项目总览/chapter2-项目速览.md) | 项目背景、方案与结果速览 |
| 总览 | 01 · 项目总览 | [chapter3 · 三分钟自述](docs/tutorial/01-项目总览/chapter3-三分钟自述.md) | 项目三分钟口播稿 |
| 总览 | 01 · 项目总览 | [chapter4 · 简历写法](docs/tutorial/01-项目总览/chapter4-简历写法.md) | 简历条目与指标口径核对 |
| 打基础 | 02 · 向量表示 | [chapter1 · 说明](docs/tutorial/02-向量表示/chapter1-说明.md) | 本部分导读与学习目标 |
| 打基础 | 02 · 向量表示 | [chapter2 · 向量与相似度](docs/tutorial/02-向量表示/chapter2-向量与相似度.md) | 文本向量、相似度及语义匹配 |
| 打基础 | 03 · 索引构建 | [chapter1 · 说明](docs/tutorial/03-索引构建/chapter1-说明.md) | 本部分导读与索引流程 |
| 打基础 | 03 · 索引构建 | [chapter2 · 解析与清洗](docs/tutorial/03-索引构建/chapter2-解析与清洗.md) | 多格式文档解析与文本清洗 |
| 打基础 | 03 · 索引构建 | [chapter3 · 切块与稳定标识](docs/tutorial/03-索引构建/chapter3-切块与稳定标识.md) | 切块策略、元数据与稳定标识 |
| 打基础 | 04 · 召回 | [chapter1 · 说明](docs/tutorial/04-召回/chapter1-说明.md) | 本部分导读与召回路径 |
| 打基础 | 04 · 召回 | [chapter2 · 稀疏召回BM25](docs/tutorial/04-召回/chapter2-稀疏召回BM25.md) | BM25 稀疏召回与分词 |
| 打基础 | 04 · 召回 | [chapter3 · 稠密召回与向量库](docs/tutorial/04-召回/chapter3-稠密召回与向量库.md) | Embedding、稠密召回与向量库 |
| 提质量 | 05 · 融合精排 | [chapter1 · 说明](docs/tutorial/05-融合精排/chapter1-说明.md) | 本部分导读与排序流程 |
| 提质量 | 05 · 融合精排 | [chapter2 · RRF融合](docs/tutorial/05-融合精排/chapter2-RRF融合.md) | RRF 融合多路召回结果 |
| 提质量 | 05 · 融合精排 | [chapter3 · Cross-Encoder精排](docs/tutorial/05-融合精排/chapter3-Cross-Encoder精排.md) | Cross-Encoder 候选精排 |
| 提质量 | 06 · 查询改写 | [chapter1 · 说明](docs/tutorial/06-查询改写/chapter1-说明.md) | 本部分导读与复杂查询 |
| 提质量 | 06 · 查询改写 | [chapter2 · 查询改写与自适应](docs/tutorial/06-查询改写/chapter2-查询改写与自适应.md) | 查询改写与自适应检索 |
| 提质量 | 06 · 查询改写 | [chapter3 · Self-RAG自纠错](docs/tutorial/06-查询改写/chapter3-Self-RAG自纠错.md) | Self-RAG 证据评估与补检索 |
| 管上下文 | 07 · 上下文与记忆 | [chapter1 · 说明](docs/tutorial/07-上下文与记忆/chapter1-说明.md) | 本部分导读与上下文管理 |
| 管上下文 | 07 · 上下文与记忆 | [chapter2 · 上下文组织与引用](docs/tutorial/07-上下文与记忆/chapter2-上下文组织与引用.md) | 证据组织、引用与生成输入 |
| 管上下文 | 07 · 上下文与记忆 | [chapter3 · 会话记忆与三级压缩](docs/tutorial/07-上下文与记忆/chapter3-会话记忆与三级压缩.md) | 滑动窗口、摘要与三级压缩 |
| 做决策 | 08 · 意图与路由 | [chapter1 · 说明](docs/tutorial/08-意图与路由/chapter1-说明.md) | 本部分导读与路由策略 |
| 做决策 | 08 · 意图与路由 | [chapter2 · 意图识别](docs/tutorial/08-意图与路由/chapter2-意图识别.md) | 客服意图识别与歧义处理 |
| 做决策 | 08 · 意图与路由 | [chapter3 · 复杂度路由与五策略](docs/tutorial/08-意图与路由/chapter3-复杂度路由与五策略.md) | 复杂度判定与五种处理策略 |
| 做决策 | 09 · 工作流与工具 | [chapter1 · 说明](docs/tutorial/09-工作流与工具/chapter1-说明.md) | 本部分导读与执行流程 |
| 做决策 | 09 · 工作流与工具 | [chapter2 · LangGraph工作流与状态](docs/tutorial/09-工作流与工具/chapter2-LangGraph工作流与状态.md) | LangGraph 状态、节点与条件边 |
| 做决策 | 09 · 工作流与工具 | [chapter3 · 工具调用权限与幂等](docs/tutorial/09-工作流与工具/chapter3-工具调用权限与幂等.md) | 工具调用、权限校验与幂等 |
| 控风险 | 10 · 安全护栏 | [chapter1 · 说明](docs/tutorial/10-安全护栏/chapter1-说明.md) | 本部分导读与风险边界 |
| 控风险 | 10 · 安全护栏 | [chapter2 · 人工确认HITL](docs/tutorial/10-安全护栏/chapter2-人工确认HITL.md) | 高风险写操作的人工确认 |
| 控风险 | 10 · 安全护栏 | [chapter3 · 护栏与安全](docs/tutorial/10-安全护栏/chapter3-护栏与安全.md) | 输入护栏、拒答与答案校验 |
| 拿证据 | 11 · 评测体系 | [chapter1 · 说明](docs/tutorial/11-评测体系/chapter1-说明.md) | 本部分导读与评测口径 |
| 拿证据 | 11 · 评测体系 | [chapter2 · 数据集与指标](docs/tutorial/11-评测体系/chapter2-数据集与指标.md) | 评测数据集、指标及计算方法 |
| 拿证据 | 11 · 评测体系 | [chapter3 · 消融与口径陷阱](docs/tutorial/11-评测体系/chapter3-消融与口径陷阱.md) | 消融实验与常见指标误读 |
| 上生产 | 12 · 工程化与上线 | [chapter1 · 说明](docs/tutorial/12-工程化与上线/chapter1-说明.md) | 本部分导读与上线准备 |
| 上生产 | 12 · 工程化与上线 | [chapter2 · 可靠性与降级](docs/tutorial/12-工程化与上线/chapter2-可靠性与降级.md) | 超时重试、错误语义与降级 |
| 上生产 | 12 · 工程化与上线 | [chapter3 · 可观测性](docs/tutorial/12-工程化与上线/chapter3-可观测性.md) | 日志、追踪、指标与排障 |
| 上生产 | 12 · 工程化与上线 | [chapter4 · 部署与上线](docs/tutorial/12-工程化与上线/chapter4-部署与上线.md) | 容器部署、依赖与上线检查 |
| 速查 | 附录 | [chapter1 · 说明](docs/tutorial/13-附录/chapter1-说明.md) | 附录导读 |
| 速查 | 附录 | [chapter2 · 术语表](docs/tutorial/13-附录/chapter2-术语表.md) | 常用术语速查 |
| 速查 | 附录 | [chapter3 · 环境变量](docs/tutorial/13-附录/chapter3-环境变量.md) | 环境变量说明 |
| 速查 | 附录 | [chapter4 · 练习答案](docs/tutorial/13-附录/chapter4-练习答案.md) | 教程练习答案 |
| 速查 | 附录 | [chapter5 · 源码阅读顺序](docs/tutorial/13-附录/chapter5-源码阅读顺序.md) | 源码阅读路线 |
| 速查 | 附录 | [chapter6 · 完整测评数据表](docs/tutorial/13-附录/chapter6-完整测评数据表.md) | 完整评测数据表 |

完整索引见 [`docs/README.md`](docs/README.md)。源码可从 `app/asgi.py` → `app/services/chat_service.py` → `app/agents/graph.py` 开始读；Web 代码在 `frontend/src/`。

<details>
<summary><strong>📁 展开项目目录</strong></summary>

```text
app/
  api/            HTTP 路由、校验、SSE
  services/       ChatService、依赖容器、演示数据
  agents/         LangGraph 状态机与节点
  retrieval/      解析、切块、混合检索、精排与自纠错
  tools/          业务工具、注册表与权限
  repositories/   订单、会话与幂等
  providers/      生成、Embedding 与 Rerank
  guardrails/     注入、边界与忠实度检查
  memory/         上下文预算与压缩
  observability/  日志、指标与请求上下文
frontend/         React + TypeScript Web 工作台
knowledge/        政策文档
eval/             离线评测与口径
tests/            单元、集成与端到端测试
docs/             技术手册与教学文档
```

</details>

<a id="limitations"></a>

## ⚠️ 使用边界

这是可运行的工程示例，**目前不应直接面向不可信用户开放**：

- API 尚未认证请求中的 `user_id`；前端默认 `u_demo` 仅供本地演示。部署前应由可信服务端认证并绑定身份。
- 订单与物流来自本地仓储演示数据，没有连接真实承运商或支付网关。
- Web 会话列表保存在当前浏览器的 `localStorage`，清除站点数据或换设备后不会恢复。
- 知识库启动时全量 ingest，尚无增量删除接口；Embedding / 精排权重不可用时会降级，降级后的效果未单独评测。

更多实现边界与后续方向见[限制与路线图](docs/12-limitations.md)。

## ⭐ Star 统计

[![Star History Chart](https://api.star-history.com/svg?repos=JEen-wang/Adaptive-rag&type=Date)](https://www.star-history.com/?repos=JEen-wang%2FAdaptive-rag&type=date)

## 🤝 参与贡献

欢迎提交问题与改进。修改前建议先读[贡献指南](CONTRIBUTING.md)；提交代码时运行 Ruff、mypy、pytest，修改前端时运行 `npm test` 与 `npm run build`。请勿提交 `.env`、密钥、本地数据库或生成的评测报告。

## 📄 许可证

项目采用 [MIT License](LICENSE)。可在保留许可与版权声明的前提下使用、修改和分发。

---

<p align="center">
  <sub>从一个问题开始，沿着策略、证据、工具与指标追到代码。<br>
  指标口径以 <a href="eval/MEASURED.md">eval/MEASURED.md</a> 为准。</sub>
</p>
