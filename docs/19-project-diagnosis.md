# 项目结构诊断

> 本文是项目自身的结构体检记录，供维护者使用。
> **最近一次复检：2026-10-10**，在隔离环境里实际跑过 `ruff check .` 与 `pytest -q`。
> 逐项结论见下方「0. 处理结果」，仍未处理的保留在对应章节作为待办。

## 0. 处理结果

### 2026-10-09 集中整理

- **P0 Git 根目录**：仓库已在正确根目录初始化并关联远程 `origin`，建立了首个正式提交。
- **P1 依赖双轨**：移除已过期的 `requirements.txt`，依赖唯一来源统一为 `pyproject.toml`（含 `dev` / `rerank` / `docs` 可选组），并在 `CONTRIBUTING.md` 写明安装方式。
- **P1 应用启动职责**：`build_container()` 已拆分为 `build_infrastructure()` / `build_retrieval()` / `build_container()`，且 `seed` 默认关闭（`seed: bool = False`）。
- **P2 模块级 docstring**：全仓库 98 处无信息量的样板 docstring 已替换为逐模块的准确描述。
- **P2 公共接口注释**：已为 provider 协议、工具基类、`create_app`、chat 路由等核心公共接口补充 Google 风格 docstring。
- **低优先级 CLI 拆分**：`app/cli.py` 已拆分为 `app/cli/{render,client,commands}` 包。
- **低优先级文档归档**：面试材料已归入 `docs/interview/`，并补齐 `.md` 扩展名与索引。
- **工程卫生**：统一换行符为 LF 并新增 `.gitattributes`；`.gitignore` 补齐本地工作目录；`ruff format` + `ruff check` 全仓库清零。

### 2026-10-10 复检（新发现并已处理）

- **ruff 已不再「全仓库清零」**：`alembic/env.py`、`alembic/versions/0001_initial.py`、`alembic/versions/0002_returns.py` 各有 1 处 I001 导入未排序，`scripts/build_interview_pack.py` 有 1 处 F841 未使用变量且需要 reformat。根因是日常只检查 `app/`，漏掉了 `alembic/` 与 `scripts/`。**已全部修复**，现在 `ruff check .` 与 `ruff format --check .` 均通过。
- **测试数过期**：文档多处写 `49 passed`，实测为 **75 passed**。原因是 2026-08-22 之后补了 cleaning / unstructured_parser / reranker / embeddings 等测试，数字没跟着更新。已在 `eval/MEASURED.md`、`docs/13`、`docs/14`（2 处）与根 README（徽章 + 实测表）共 6 处改为 75，并注明这是 2026-10-10 单独复测、与 8-22 的评测指标不是同一次运行。
- **没有 CI**：已新增 `.github/workflows/ci.yml`，在 Python 3.11 / 3.12 上依次跑 `ruff format --check`、`ruff check`、`pytest`。
- **没有许可证**：已补 `LICENSE`（MIT，`Copyright (c) 2026 JEen-wang`）。
- **`.env.example` 漏字段**：补上 `KNOWLEDGE_DIR` 与 `DB_POOL_TIMEOUT`，现在与 `app/config/settings.py` 的 50 个字段完全对齐。
- **文档口径打架**：`docs/README.md` 说教学文档「共 13 个部分」，与 `docs/tutorial/README.md` 的「12 个部分」冲突，已统一为「12 个部分、43 篇正文」。
- **本文原先的位置**：`PROJECT_DIAGNOSIS.md` 放在仓库根目录，对外展示时会直接暴露内部弱点清单，已移入 `docs/19-project-diagnosis.md`。

### 仍未处理

- **评测原始数据缺失（当前最高优先级）**：`eval/reports/` 里只有 `.gitkeep`，而 `all_20260822T121308Z.json`、`all_20260822T042748Z.json`、`latest.json` 在仓库、本地磁盘与 git 历史中**都不存在**，却被 `eval/MEASURED.md`（2 处）、`docs/14-evaluation-report.md`（3 处）、`docs/04-adaptive-rag.md`、`docs/15-ingest-and-retrieval.md`、`docs/tutorial/13-附录/05-完整测评数据表.md` 当作「来源」引用。整个项目的立论是数字可追溯，这条证据链是断的。修法二选一：重跑 `python -m eval.runner --task all --llm` 生成 JSON 并在 `.gitignore` 里放开；或把文档措辞改为「本轮报告未保留」。
- **没有锁文件**：`pyproject.toml` 全部是范围版本，但实测数字绑定在具体依赖与模型版本上，建议补 `uv.lock` 或锁定版 `requirements.txt`。
- **P1 降级策略分散**：`DependencyHealth` / capability 状态尚未统一，健康检查的 backend 报告仍需集中化。
- **P2 领域边界交叉**：`agents` 节点仍直接依赖 retrieval / tools / memory / providers 的具体实现。
- **P2 配置校验前置**：启动阶段尚未统一输出脱敏后的 backend 运行模式。

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

### P2：错误处理过宽（2026-10-10 复检后已降级）

原先的判断偏重，逐处核对后大部分是合理的。全仓库 `except Exception` 共 23 处、**裸 `except:` 0 处**，且关键位置的处理方式都是正确的：

- `app/repositories/order_repository.py` 的 4 处均为 `raise DatabaseError(...) from exc`，属于正确的异常包装而非静默降级；
- `app/agents/nodes/generate.py` 捕的是 `(LLMProviderError, LLMOutputError)` 这样的窄元组，降级到抽取式回答；
- `app/api/routes/health.py` 把 `type(exc).__name__` 写进了响应体，不是无声吞掉。

仍值得做的只剩一件事：在 fallback 路径上补指标或测试，让「降级发生了」这件事可观测。

### P2：公共接口注释仍不完整

模块级 docstring 已统一，但公开类、函数和 API handler 仍缺少系统性的参数、返回值和异常说明。优先补充 `build_container`、`create_app`、检索器、工具基类、provider 协议和路由函数。

### P2：配置与环境校验可前置

`.env.example`、Docker Compose、文档中的默认值基本一致，但建议在启动阶段输出脱敏后的运行模式：数据库 backend、缓存 backend、向量 backend、LLM backend、reranker backend。避免只在首次请求时才发现配置错误。

## 4. 低优先级问题

- ~~`app/cli.py` 同时承担命令解析、HTTP/SSE 交互、渲染和本地启动~~ **已完成**：现已拆为 `app/cli/{render,client,commands}` 包。
- ~~`app/__init__.py` 和多个子包的 `__init__.py` 暴露较多重导出~~ **已完成**：`app/__init__.py` 现在只保留 docstring 与 `__version__`；各子包 `__init__.py` 均为 6–26 行并显式声明 `__all__`（共 19 个），不存在无约束的批量重导出。
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
