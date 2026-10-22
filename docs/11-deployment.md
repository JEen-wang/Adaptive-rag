# 11 · 部署与运维

> 一句话：默认 Compose 使用 SQLite 和内置检索，单个容器即可启动 API 与 Web；Redis、Qdrant、Postgres 仍可按需接入；`.env` 不进镜像。

## 本章目录

1. [本地](#本地)
2. [Docker Compose](#docker-compose)
3. [生产检查清单](#生产检查清单)
4. [扩容、知识库、回滚](#扩容知识库回滚)

## 本地

SQLite + 内存向量，见 [02](02-getting-started.md)。

## Docker Compose

```bash
docker compose up --build -d
```

启动后访问 `http://127.0.0.1:8000`，停止服务使用 `docker compose down`。数据保存在 Compose volume `adaptive-rag-data` 中。

### 三种运行模式

| 模式 | Compose 文件 | 组件 | 适用场景 |
|---|---|---|---|
| 默认演示 | `docker-compose.yml` | API、前端、SQLite | 最少依赖，自动降级 |
| 单机生产 | `docker-compose.single.yml` | API、前端、PostgreSQL、Redis | 单节点长期运行 |
| 多实例生产 | `docker-compose.multi.yml` | Nginx、双 API、PostgreSQL、Redis、Qdrant | 扩容和共享状态 |

```bash
# 单机和多实例模式先设置数据库密码
export POSTGRES_PASSWORD='change-this-password'
docker compose -f docker-compose.single.yml up --build -d
docker compose -f docker-compose.multi.yml up --build -d
```

单机和多实例镜像会安装 `.[rerank]`。启用本地 Embedding / Cross-Encoder 时，首次启动可能下载模型；没有 LLM 密钥时仍会使用离线证据回答。

| 容器 | 作用 | API 依赖 |
|---|---|---|
| `api` | FastAPI | 8000 |

### 代码摘要

```yaml
# docker-compose.yml
api:
  environment:
    DATABASE_URL: sqlite+aiosqlite:///./data/local/app.db
    REDIS_URL: ""
    QDRANT_URL: ""
    APP_ENV: production
```

健康检查打 `http://127.0.0.1:8000/api/v1/health`。镜像非 root，先 COPY 再 `pip install .`。

## 生产检查清单

- [ ] `APP_ENV=production`，`LOG_LEVEL=INFO`
- [ ] `ADMIN_API_TOKEN` 已设
- [ ] `DATABASE_URL` 指向 Postgres，连接池已看过
- [ ] 真实 embedding 网关（否则对外以 BM25 为准）
- [ ] `pip install -e ".[rerank]"` 后重跑 retrieval，报告含 `hybrid+cross-encoder`
- [ ] `pip install -e ".[docs]"` 后用真实 PDF/扫描件验证 ingest；换切分后重跑 `--task retrieval`
- [x] `u_demo` / `anonymous` 全局读单已关闭
- [ ] 在可信网关认证用户并绑定 `user_id`；当前请求体仍可伪造身份，不可直接对公网开放
- [ ] liveness / readiness 分开（见 [08](08-reliability.md#探活)）
- [ ] 密钥不在日志、镜像、README
- [ ] 长期 Postgres 用 Alembic（现在启动仍 `create_all`）

## 扩容、知识库、回滚

API 无粘滞：session 在 DB。进程内限流多副本不共享 → 生产配 Redis。Graph 每进程编译一次。

改 `knowledge/` 文档后重启 API。`chunk_id` 在同一切分结果下稳定，Qdrant upsert 覆盖。无 CMS。生产 ingest 走 Unstructured；系统包需要 poppler、tesseract（`chi_sim`）、处理 Office 时的 libreoffice。换解析器后重跑 `--task retrieval`。

应用无状态（除 DB）。回滚镜像即可。Alembic `0002` 退货表，schema 回滚需显式 `downgrade`。

---

上一章 [10](10-evaluation.md) · 下一章 [12 · 限制](12-limitations.md)
