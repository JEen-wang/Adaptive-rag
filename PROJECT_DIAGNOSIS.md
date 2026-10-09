# 项目结构诊断

诊断范围：`app/`、`tests/`、`eval/`、`docs/`、部署文件和 Python 打包配置。

## 1. 总体结构

项目采用 FastAPI + LangGraph 的分层结构，当前规模为：

- `app/`：117 个 Python 文件，按 agents、api、core、guardrails、providers、repositories、retrieval、services、tools 等职责拆分。
- `tests/`：24 个 Python 文件，包含 unit、integration、e2e 三层测试。
- `eval/`：离线评测数据、指标和运行器。
- `knowledge/`：39 篇知识库文档。
- `docs/`：22 个文档文件，覆盖架构、部署、检索、安全和评测。

总体判断：业务分层完整，测试和文档意识较好，已经接近一个可维护的工程型 RAG 项目。

## 2. 高优先级问题

### P0：Git 根目录不正确

压缩包被解压为 `rag/Adaptive-rag-main/`，而外层 `rag/` 才是当前 Git 根目录，外层没有项目文件和提交记录。这样会导致：

- Git diff 显示整个项目为一个未跟踪目录。
- CI、Docker 构建和 IDE 项目根目录容易选错。
- `pyproject.toml`、README 和 `.gitignore` 不在 Git 根目录。

建议将 `Adaptive-rag-main` 设为实际仓库根目录（在该目录初始化/关联远程），或把其内容提升到 `rag/` 根目录后再提交。

### P1：依赖定义存在双重来源

依赖同时维护在 `pyproject.toml` 和 `requirements.txt`。前者使用范围版本，后者使用锁定版本，长期容易发生漂移。建议选择一种主来源：

- 用 `pyproject.toml` 管理依赖和 optional groups；
- 用 uv/poetry/pip-tools 生成锁文件；
- `requirements.txt` 只保留生成产物，并在 README 写明生成方式。

### P1：应用启动职责偏重

`app/services/container.py` 的 `build_container()` 同时负责数据库 schema 初始化、Redis、向量库、知识库 ingest、工具注册、MCP 合并和演示数据 seed。启动链较长，任一外部依赖或知识库问题都可能影响 API 启动。

建议拆成：

- `build_infrastructure()`：数据库、缓存、向量客户端；
- `build_retrieval()`：知识库 ingest、BM25、向量检索、reranker；
- `build_agent_runtime()`：Graph、工具和服务；
- `seed_demo_data` 改为显式 CLI/迁移步骤，生产启动默认关闭。

### P1：外部依赖的降级策略分散

Redis、Qdrant、embedding、reranker 都有 fallback，但策略分布在多个 provider/retrieval/infra 文件中。建议统一定义 `DependencyHealth` 或 capability 状态，在 health/readiness 中报告 backend、fallback 原因和是否为降级模式。

## 3. 中优先级问题

### P2：领域边界仍有交叉

`agents` 节点直接依赖 retrieval、tools、memory、providers 和 repositories 的具体实现。当前可读性尚可，但图节点会逐渐成为“总线层”。建议让节点只依赖面向用例的接口，例如 `RetrievalService`、`ToolExecutor`、`ConversationMemory`。

### P2：错误处理过宽

多个模块使用 `except Exception`。这适合隔离可选基础设施，但应保证：

- 记录结构化日志和异常类型；
- 只在明确的 fallback 边界捕获；
- 数据库写入、权限判断和工具执行不要静默降级；
- 为 fallback 增加指标或测试。

### P2：公共接口注释仍不完整

模块级 docstring 已统一，但公开类、函数和 API handler 仍缺少系统性的参数、返回值和异常说明。优先补充 `build_container`、`create_app`、检索器、工具基类、provider 协议和路由函数。

### P2：配置与环境校验可前置

`.env.example`、Docker Compose、文档中的默认值基本一致，但建议在启动阶段输出脱敏后的运行模式：数据库 backend、缓存 backend、向量 backend、LLM backend、reranker backend。避免只在首次请求时才发现配置错误。

## 4. 低优先级问题

- `app/cli.py` 同时承担命令解析、HTTP/SSE 交互、渲染和本地启动，建议拆为 `cli/commands.py`、`cli/client.py`、`cli/render.py`。
- `app/__init__.py` 和多个子包的 `__init__.py` 暴露较多重导出，可能增加导入链和循环依赖风险；建议只暴露稳定公共 API。
- 文档数量较多，且存在中文面试稿与正式文档内容重复。可将面试材料移到 `docs/archive/` 或单独的 `notes/`。
- 评测报告中包含固定日期和固定指标，建议在报告顶部标注数据生成命令、模型版本和知识库版本。
- Dockerfile 未复制 `alembic/`、`eval/`、`tests/`，这对运行镜像是合理的，但迁移应明确由独立命令或部署步骤负责。

## 5. 推荐重构顺序

1. 修正 Git 仓库根目录并建立首个干净提交。
2. 统一依赖来源并生成锁文件。
3. 拆分 `build_container()`，把 seed 和 ingest 改为显式生命周期任务。
4. 统一基础设施健康状态和 fallback 可观测性。
5. 为核心公共接口补充 Google 风格 docstring 和类型别名。
6. 再处理 CLI 拆分、`__init__` 重导出和文档归档。

## 6. 当前结论

项目不是“目录混乱”型代码库，主要风险集中在启动编排过重、依赖来源双轨、Git 根目录错误和边界层缺少统一接口。先处理 P0/P1 项，收益会明显高于一次性重命名全部文件。
