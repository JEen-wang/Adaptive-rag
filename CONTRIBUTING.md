# 贡献指南

## 依赖管理

依赖的唯一来源是 `pyproject.toml`：运行时依赖写在 `[project.dependencies]`，可选组写在 `[project.optional-dependencies]`（`dev`、`rerank`、`docs`）。仓库不再维护单独的 `requirements.txt`，避免两份版本清单漂移。

```bash
pip install -e ".[dev]"      # 开发（含 pytest、ruff）
pip install -e ".[rerank]"   # 本地 bge 召回 + Cross-Encoder 精排
pip install -e ".[docs]"     # Unstructured 解析 PDF/Office/HTML/图片
```

## 代码规范

项目使用 Python 3.11+，统一采用 Ruff 进行格式化、导入排序和静态检查。新增模块应包含模块级文档字符串；公开的类、函数和异步接口应使用 Google 风格 docstring，说明用途、参数、返回值及异常。

```bash
ruff format .
ruff check .
python -m compileall -q app eval
pytest -q
```

提交前请确保不提交 `.env`、密钥、数据库文件和评测生成物。业务逻辑应放在分层目录中，通过 schema 传递数据，避免在路由层直接访问基础设施。
