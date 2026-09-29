# 02 · 快速开始

> 目标：本机 5 分钟内 `POST /api/v1/chat` 成功。默认 **SQLite + 内存向量**，不强制 Docker。

## 本章目录

1. [环境与安装](#环境与安装)
2. [启动时发生了什么](#启动时发生了什么)
3. [探活与第一问](#探活与第一问)
4. [演示订单与 HITL](#演示订单与-hitl)
5. [测试](#测试)

## 环境与安装

- Python **3.11+**（验证过 3.12）
- 可选 `DEEPSEEK_API_KEY`（没有则 `FakeLLMProvider`，流程通，回答是占位 JSON）

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# 本地 bge-small 召回 + Cross-Encoder 精排：pip install -e ".[rerank]"
# Unstructured 解析 PDF/Office/HTML/图片：pip install -e ".[docs]"
# 系统包：poppler、tesseract（含 chi_sim）、Office 还需 libreoffice
# 首次请求会加载 BAAI/bge-small-zh-v1.5（~90MB）与 BAAI/bge-reranker-base（国内可设 HF_ENDPOINT）
cp .env.example .env
```

`.env` 最小集：

```bash
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./data/local/app.db
DEEPSEEK_API_KEY=sk-...   # 可选，演示质量依赖它
```

不要提交 `.env`。

```bash
uvicorn app.asgi:app --reload --port 8000
python -m app.cli
```

入口：`app/asgi.py` → `create_app()`。CLI 连已启动的 API 做终端一问一答（`/y` 确认 HITL，`/quit` 退出），不重复加载模型。

## 启动时发生了什么

### 要点

`lifespan` 调用 `build_container`：建表、ingest `knowledge/`、seed 演示订单、编译 Graph。

### 代码摘要

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container(get_settings())  # ingest + seed + 编译图
    app.state.container = container
    try:
        yield
    finally:
        await container.aclose()
```

```python
# app/services/seed.py
async def seed_demo_data(session: AsyncSession) -> None:
    exists = await session.get(OrderRow, "ORD10001")
    if exists is not None:
        return
    # 写入 SKU-HEADSET / SKU-MUG-CUSTOM / SKU-TEE 与三张订单
```

## 探活与第一问

```bash
curl -s localhost:8000/api/v1/health
curl -s localhost:8000/api/v1/ready
curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"定制马克杯过了7天但是有质量问题能退吗","user_id":"u_demo"}'
```

- `/health`：进程活着  
- `/ready`：数据库硬依赖；Redis/Qdrant/LLM 只报告  

期望：`trace_id`、`strategy`（多为 `multi` 或 `single`）、回答提到定制/质量。

## 演示订单与 HITL

| 订单号 | 状态 | 商品 |
|---|---|---|
| `ORD10001` | 已发货 | 降噪耳机 |
| `ORD10002` | 已签收 | 定制马克杯 |
| `ORD10003` | 已支付未发货 | T 恤 |

用户 `u_demo`。取消未发货会返回 `pending_action`：

```bash
curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"取消订单ORD10003","user_id":"u_demo"}'
# 把 pending_action.action_id 填回：
curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"确认取消","user_id":"u_demo","confirm_action_id":"act_..."}'
```

机制见 [05 · HITL](05-agents-and-tools.md#hitl-与幂等)。

## 测试

```bash
pytest -q
python -m eval.runner --task retrieval
```

`tests/conftest.py` 会清空 `DEEPSEEK_API_KEY`，避免误打真实接口。

下一步：[11 · 部署](11-deployment.md)、[06 · API](06-api-reference.md)。

---

上一章 [01](01-overview.md) · 下一章 [03 · 架构](03-architecture.md)
